# NemoClaw vs. MilimoClaw: Deep Comparison Analysis

## Executive Summary

MilimoClaw extends NemoClaw, but there are key differences that affect onboarding. The original NemoClaw has TWO onboarding paths:
1. **Host-side onboarding** (`bin/lib/onboard.js`) - 7-step wizard run on HOST
2. **Sandbox-side onboarding** (`nemoclaw/src/commands/onboard.ts`) - Plugin command run INSIDE sandbox

MilimoClaw's `run-milimo-docker.sh` bypasses the host-side onboarding entirely, creating a "naked" container.

---

## Critical Discovery: Two Onboarding Systems

### 1. Host-Side Onboarding (`bin/nemoclaw.js` + `bin/lib/onboard.js`)

**Location:** `NemoClaw-original-repo/bin/lib/onboard.js` (967 lines)

**Purpose:** Run on the HOST machine to:
- Check prerequisites (Docker, openshell CLI)
- Start OpenShell gateway (`openshell gateway start --name nemoclaw`)
- Create sandbox via `openshell sandbox create`
- Configure inference providers (`openshell provider create`)
- Set inference route (`openshell inference set`)
- Apply policy presets
- Register sandbox in `~/.nemoclaw/registry.json`

**Key Functions:**
```javascript
async function onboard(opts = {}) {
  const gpu = await preflight();           // Step 1: Check Docker, openshell, ports
  await startGateway(gpu);                 // Step 2: Start OpenShell gateway
  const sandboxName = await createSandbox(gpu); // Step 3: Create sandbox
  const { model, provider } = await setupNim(sandboxName, gpu); // Step 4: Choose inference
  await setupInference(sandboxName, model, provider); // Step 5: Create provider
  await setupOpenclaw(sandboxName, model, provider); // Step 6: Configure OpenClaw
  await setupPolicies(sandboxName);        // Step 7: Apply policies
}
```

**This is the PRIMARY onboarding path.** It runs `openshell sandbox create --from Dockerfile --name <name> --provider nvidia-nim`.

### 2. Sandbox-Side Onboarding (`nemoclaw/src/commands/onboard.ts`)

**Location:** `nemoclaw/src/commands/onboard.ts`

**Purpose:** Run INSIDE the sandbox to:
- Configure inference endpoint (build, ncp, ollama, vllm, nim-local, custom)
- Validate API key against endpoint
- Select model
- Call `openshell provider create` and `openshell inference set`
- Save config to `~/.nemoclaw/config.json`

**This is a SECONDARY path** used for:
- Reconfiguring inference after initial setup
- Non-interactive configuration changes
- CI/CD pipelines

---

## Key Differences Between MilimoClaw and Original

### 1. `nemoclaw/src/commands/onboard.ts` Changes

| Feature | Original | MilimoClaw |
|---------|----------|------------|
| Supported endpoint types | `["build", "ncp", "ollama"]` (vllm/nim-local experimental) | All 6 types enabled |
| Experimental flag | `NEMOCLAW_EXPERIMENTAL=1` required for vllm/nim-local | No experimental check |
| Model defaults | `DEFAULT_OLLAMA_MODEL`, diverse cloud models | Nemotron-only |
| Ollama detection | Lists available models via `ollama list` | Just checks if running |
| Endpoint prompt | `promptEndpoint()` helper with hints | Inline `promptSelect()` |
| Config display | Uses `describeOnboardEndpoint()`/`describeOnboardProvider()` | Inline strings |

### 2. `scripts/setup.sh` Changes

| Feature | Original | MilimoClaw |
|---------|----------|------------|
| Runtime library | Sources `scripts/lib/runtime.sh` | Inline Docker host detection |
| Container runtime check | Detects Colima/Docker Desktop/Podman | Only checks Colima socket |
| Podman on macOS | Explicitly fails with error | No check |
| Sandbox name | Configurable via argument | Hardcoded to `nemoclaw` |
| Provider base URL | Uses `get_local_provider_base_url()` | Hardcoded `host.openshell.internal` |

### 3. Scripts Directory

**Original has:** `scripts/lib/runtime.sh` (229 lines)
- `detect_docker_host()`
- `docker_host_runtime()`
- `get_local_provider_base_url()`
- `check_local_provider_health()`
- CoreDNS utilities

**MilimoClaw:** Missing `scripts/lib/` directory entirely

---

## The TLS CA Error Root Cause

The error "failed to read TLS CA from /sandbox/.config/openshell/gateways/nemoclaw-cluster/mtls/ca.crt" occurs because:

1. **MilimoClaw container was NOT created via `openshell sandbox create`**
   - `run-milimo-docker.sh` uses plain `docker run` which bypasses OpenShell's configuration injection
   - No gateway CA certificates are mounted
   - No `~/.config/openshell/` directory structure exists

2. **The `openshell` CLI inside the container has no active gateway**
   - When `openclaw nemoclaw onboard` runs `openshell provider create`, the CLI looks for an active gateway
   - Without gateway config, it falls back to a broken `nemoclaw-cluster` entry
   - The gateway entry exists but TLS certs are missing

3. **The original flow injects these during sandbox creation:**
   ```bash
   openshell sandbox create --from Dockerfile --name my-assistant --provider nvidia-nim
   ```
   This automatically:
   - Creates the gateway connection
   - Mounts CA certificates at `~/.config/openshell/gateways/<name>/mtls/`
   - Configures `OPENSHELL_GATEWAY` environment variable
   - Sets up `host.openshell.internal` DNS

---

## Architecture Flow Diagrams

### Original NemoClaw Flow (Working)

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOST MACHINE                              │
│                                                                  │
│  1. ./scripts/setup.sh                                          │
│     ├─ preflight: check Docker, openshell CLI, ports            │
│     ├─ startGateway: openshell gateway start --name nemoclaw    │
│     ├─ createSandbox: openshell sandbox create ...              │
│     │   └─ This injects:                                        │
│     │       - openshell binary                                  │
│     │       - Gateway CA certs                                  │
│     │       - host.openshell.internal DNS                       │
│     │       - OPENSHELL_GATEWAY env var                         │
│     ├─ setupInference: openshell provider create                │
│     └─ setupPolicies: Apply policy presets                      │
│                                                                  │
│  Result: Sandbox has working gateway connection                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SANDBOX CONTAINER                             │
│                                                                  │
│  ~/.config/openshell/                                           │
│  └── gateways/                                                  │
│      └── nemoclaw/                                              │
│          ├── gateway.json        ← Gateway metadata             │
│          └── mtls/                                              │
│              ├── ca.crt          ← Gateway CA certificate       │
│              ├── client.crt      ← Client certificate           │
│              └── client.key      ← Client key                   │
│                                                                  │
│  openshell CLI works because gateway is selected                │
└─────────────────────────────────────────────────────────────────┘
```

### MilimoClaw Flow (Broken)

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOST MACHINE                              │
│                                                                  │
│  1. ./scripts/run-milimo-docker.sh                              │
│     └─ docker run -d --name MilimoClaw \                        │
│          -e NVIDIA_API_KEY=... \                                │
│          -v /var/run/docker.sock:/var/run/docker.sock \         │
│          milimo-claw:latest                                     │
│                                                                  │
│  ❌ No gateway creation                                          │
│  ❌ No openshell sandbox create                                  │
│  ❌ No CA certificate injection                                  │
│  ❌ No host.openshell.internal DNS                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MilimoClaw CONTAINER                          │
│                                                                  │
│  ~/.config/openshell/                                           │
│  └── gateways/                                                  │
│      └── nemoclaw-cluster/       ← Broken/stale entry           │
│          └── mtls/                                              │
│              └── ca.crt          ← MISSING!                     │
│                                                                  │
│  openshell CLI FAILS because:                                   │
│  - No active gateway selected                                   │
│  - TLS CA cert doesn't exist                                    │
│  - No valid gateway connection                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Solutions

### Option A: Use Original NemoClaw Setup (Recommended)

Run the original host-side onboarding first:

```bash
cd /Users/mck/Desktop/MilimoClaw/NemoClaw-original-repo
export NVIDIA_API_KEY=nvapi-...
./scripts/setup.sh milimo
```

This creates a properly configured sandbox with gateway connection.

### Option B: Fix MilimoClaw Container Setup

Modify `run-milimo-docker.sh` to:

1. **Mount gateway config from host:**
   ```bash
   -v ~/.config/openshell:/root/.config/openshell
   ```

2. **Add host DNS entry:**
   ```bash
   --add-host host.openshell.internal:<gateway-ip>
   ```

3. **Or use existing sandbox:**
   ```bash
   # Instead of docker run, connect to existing sandbox
   openshell sandbox connect milimo
   ```

### Option C: Gateway-less Onboarding (For Cloud API Only)

Modify `onboard.ts` to use direct API calls without gateway:

```typescript
// For NVIDIA Build (cloud), use direct HTTP instead of openshell CLI
if (endpointType === "build") {
  // Write config directly without openshell provider create
  saveOnboardConfig({...});
  // Test with direct fetch
  const valid = await validateApiKey(apiKey, endpointUrl);
}
```

---

## File-by-File Changes Summary

### Identical Files (No Changes)
- `nemoclaw/src/cli.ts` ✓
- `nemoclaw/src/onboard/config.ts` ✓
- `nemoclaw/src/onboard/validate.ts` ✓
- `nemoclaw/src/onboard/prompt.ts` ✓
- `nemoclaw/src/commands/launch.ts` ✓
- `nemoclaw/src/commands/connect.ts` ✓
- `nemoclaw/src/commands/eject.ts` ✓
- `nemoclaw/src/commands/logs.ts` ✓
- `nemoclaw/src/commands/migrate.ts` ✓
- `nemoclaw/src/commands/status.ts` ✓

### Modified Files
- `nemoclaw/src/commands/onboard.ts` - Simplified (removed experimental checks, Ollama integration)

### Missing Files in MilimoClaw
- `scripts/lib/runtime.sh` - Runtime utilities for Docker host detection
- Proper sandbox creation flow

### Extra Files in MilimoClaw
- `scripts/run-milimo-docker.sh` - Custom container runner (bypasses OpenShell)
- `scripts/setup-existing-cluster.sh` - Custom cluster configuration
- `scripts/openshell-cli-helper.sh` - OpenShell CLI wrapper

---

## Recommendations

1. **Align `onboard.ts` with original** - Restore the experimental flag checks and Ollama model discovery
2. **Use original setup.sh flow** - Don't bypass `openshell sandbox create`
3. **If using existing cluster** - Mount gateway CA certs from host
4. **Add `scripts/lib/runtime.sh`** - Include runtime utilities for proper Docker host detection

---

## Actions Taken (March 19, 2026)

### Files Restored from Original

1. **`nemoclaw/src/commands/onboard.ts`** - Restored to match original:
   - Added `SUPPORTED_ENDPOINT_TYPES` with experimental flag check
   - Added `isExperimentalEnabled()` function
   - Added `parseOllamaList()`, `getOllamaModelOptions()`, `getDefaultOllamaModel()` functions
   - Added `promptEndpoint()` helper with proper endpoint options
   - Restored `DEFAULT_OLLAMA_MODEL` and diverse cloud models (Kimi, GLM-5, MiniMax, Qwen, GPT-OSS)
   - Uses `describeOnboardEndpoint()` and `describeOnboardProvider()` from config.ts

2. **`scripts/lib/runtime.sh`** - Added (229 lines):
   - `detect_docker_host()` - Finds Colima/Docker Desktop socket
   - `docker_host_runtime()` - Identifies runtime type
   - `get_local_provider_base_url()` - Returns `host.openshell.internal` URLs
   - `check_local_provider_health()` - Health checks for local providers
   - `infer_container_runtime_from_info()` - Parses `docker info` output
   - `is_unsupported_macos_runtime()` - Detects Podman on macOS

3. **`scripts/setup.sh`** - Restored to match original:
   - Sources `scripts/lib/runtime.sh`
   - Configurable sandbox name via argument
   - Podman on macOS detection with error
   - Uses `get_local_provider_base_url()` for provider URLs

4. **`nemoclaw/tsconfig.json`** - Fixed to exclude test files:
   - Added `"src/**/*.test.ts"` to exclude array

### Build Verification

- `npm run build` in `nemoclaw/` succeeds
- Output in `nemoclaw/dist/` generated

---

## Next Steps

1. ✅ ~~Restore `nemoclaw/src/commands/onboard.ts` to match original~~
2. ✅ ~~Add `scripts/lib/runtime.sh` from original~~
3. ✅ ~~Update `scripts/setup.sh` to match original~~
4. ❌ ~~Run `./scripts/setup.sh milimo` to create properly configured sandbox~~ **BLOCKED: macOS limitation**

---

## Critical Issue: macOS Cannot Run OpenShell Sandboxes (March 19, 2026)

### Root Cause

OpenShell requires Linux kernel capabilities (`CAP_NET_ADMIN`, `CAP_SYS_ADMIN`) for network namespace isolation. Neither Docker Desktop nor Colima on macOS can pass these capabilities through nested containers.

**Architecture**: Docker Desktop/Colima → Linux VM → k3s container → sandbox pod

The nested virtualization prevents kernel capabilities from being passed through to the sandbox pod.

**Error**: `Network namespace creation failed and proxy mode requires isolation. Ensure CAP_NET_ADMIN and CAP_SYS_ADMIN are available`

### Verified Working

- ✅ Gateway starts successfully
- ✅ Image builds and uploads
- ✅ Provider creation works
- ✅ Inference routing configured
- ❌ Sandbox pod crashes (capability issue)

### Solutions

1. **Deploy on native Linux server** (Recommended)
   - Use a VPS (DigitalOcean Droplet, AWS EC2, GCP Compute Engine)
   - Or use a local Linux machine
   - OpenShell works perfectly on native Linux

2. **Use existing OpenShell deployment**
   - If you have access to a Linux server running OpenShell
   - Connect remotely: `openshell gateway start --remote user@hostname`

3. **Development without full isolation**
   - Use the `MilimoClaw` container directly
   - Skip the k3s/gateway layer (reduced security)
   - Suitable for development and testing only

### What Was Fixed Today

- ✅ `nemoclaw/src/commands/onboard.ts` - Matched with original
- ✅ `scripts/lib/runtime.sh` - Added from original
- ✅ `scripts/setup.sh` - Matched with original
- ✅ `nemoclaw/tsconfig.json` - Fixed to exclude test files
- ✅ `.dockerignore` - Fixed to not exclude dist/ directories
- ✅ Gateway and providers created successfully on Docker Desktop
- ✅ Image build pipeline working
- ✅ **MilimoClaw container connected to gateway network**
- ✅ **OpenShell config created with correct gateway metadata**
- ✅ **TLS certificates copied from host to container**
- ✅ **DNS resolution added via /etc/hosts**
- ✅ **NemoClaw onboarding completed successfully!**

---

## Solution: MilimoClaw Container as Sandbox (March 20, 2026)

### Key Discovery

The MilimoClaw container CAN connect to the OpenShell gateway running in a separate container (`openshell-cluster-nemoclaw`). The container itself acts as the sandbox - no need for k3s to create sandbox pods.

### Connection Requirements

1. **Network**: Container must be on the same Docker network as gateway
2. **Gateway Config**: `metadata.json` with correct endpoint (DNS name + NodePort)
3. **TLS Certs**: Copied from host `~/.config/openshell/gateways/nemoclaw/mtls/`
4. **DNS**: `/etc/hosts` entry for `openshell.openshell.svc.cluster.local`
5. **Environment**: `HOME=/sandbox` required for OpenShell to find config

### Working Configuration

```json
// /sandbox/.config/openshell/gateways/nemoclaw/metadata.json
{
  "name": "nemoclaw",
  "gateway_endpoint": "https://openshell.openshell.svc.cluster.local:30051",
  "is_remote": false,
  "gateway_port": 30051
}
```

### Key Ports

- **Gateway NodePort**: 30051 (not 8080)
- **Gateway Internal**: 8080 (only inside k3s)

### TLS Certificate Valid Names

The gateway certificate is valid for:
- `openshell`
- `openshell.openshell.svc`
- `openshell.openshell.svc.cluster.local`
- `localhost`
- `host.docker.internal`

**NOT valid for IP addresses** (172.18.0.2, etc.)

### Documentation Created

- [Gateway Connection Troubleshooting](docs/troubleshooting/openshell-gateway-connection.md)
- [Setup Guide](docs/setup-guide.md)
