# Sandbox Hardening and Stabilization

This document summarizes the solutions implemented to resolve sandbox creation failures and ensure the MilimoClaw environment is production-ready.

## 1. Network Namespace Failures (macOS / Docker)

### Issue
The sandbox pod would enter a `CrashLoopBackOff` with logs showing:
`Fatal error: failed to initialize network environment: failed to create network namespace`

### Solution
Ensured that `iproute2` and `iptables` binaries are installed in the sandbox image. These are required by the OpenClaw agent to manage its internal traffic routing, even if some capabilities are limited on macOS.

```dockerfile
# Added to Dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iptables \
    && rm -rf /var/lib/apt/lists/*
```

## 2. Secure Configuration Management

### Issue
Secrets like authentication tokens were being generated at build time, baking them into immutable Docker image layers. Additionally, supervisor and gateway access shared the same root token.

### Solution
1.  **Split Tokens**: Separate `supervisor_token` and `gateway_auth_token` were implemented in `generate_openclaw_config.py`.
2.  **Init Container Pattern**: The `Dockerfile` was refactored into a multi-stage build. An `init` stage generates the config at runtime (in a Kubernetes context, this represents an init container).
3.  **Root Locking**: The configuration is owned by `root:root` and set to `444` (read-only), while the agent runs as the unprivileged `sandbox` user.

## 3. Onboarding Build Optimization

### Issue
The `nemoclaw onboard` process was slow or failing due to the entire local directory (including large `.venv` and `node_modules`) being sent to the Docker daemon.

### Solution
Updated `onboard.js` to dynamically exclude common heavy directories and ensure only necessary source files are included in the build context.

```javascript
// Updated in bin/lib/onboard.js
const EXCLUDES = ['.venv', 'node_modules', '__pycache__', '.git', 'dist'];
```

## 4. Production-Ready Flags

The following flags are strictly enforced in the production configuration:

-   `allowInsecureAuth: False`: Prevents unauthenticated access to the gateway.
-   `dangerouslyDisableDeviceAuth: False`: Ensures device-level authentication is active.
-   `configWrites: False`: Prevents runtime modification of the agent configuration.
-   `os.chmod(path, 0o444)`: Enforces read-only status for the configuration file.

## Verification
The sandbox is now successfully marked as `Ready` by the OpenShell gateway, and the `nemoclaw onboard` process completes successfully with a secure, hardened agent.
