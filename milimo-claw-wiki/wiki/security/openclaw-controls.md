# OpenClaw Security Controls Beyond NemoClaw's Scope

**Summary**: Application-layer security controls implemented by OpenClaw that operate independently of the NemoClaw sandbox infrastructure.

**Sources**:
- [NemoClaw OpenClaw Controls Reference](https://docs.nvidia.com/nemoclaw/latest/security/openclaw-controls.html)
- [OpenShell Security Documentation](https://docs.nvidia.com/openshell/latest/security/)

**Last updated**: 2026-04-29

**Tags**: #security #openclaw #controls #application-layer

---

> **NemoClaw Compliance Notice**: This page documents security controls as implemented by NVIDIA NemoClaw and OpenShell. MilimoClaw operates within the NemoClaw sandbox and inherits all controls described here. Any discrepancy between this page and the [official NemoClaw documentation](https://docs.nvidia.com/nemoclaw/latest/security/openclaw-controls.html) should be reported and resolved in favor of the official docs. Tested against NemoClaw v0.0.29.

## Scope Boundary

NemoClaw provides **infrastructure-layer** security: network egress control, filesystem isolation, process containment, and inference routing. It delegates all **application-layer** security to OpenClaw. The controls documented on this page are implemented by OpenClaw itself and operate independently of the NemoClaw sandbox.

---

## Prompt Injection Detection and Prevention

OpenClaw implements a multi-stage prompt injection defense:

- **Regex detection**: Pattern-based identification of known injection techniques
- **Boundary wrapping**: Injected content is wrapped in delimiters to separate it from agent instructions
- **Unicode folding**: Normalizes Unicode characters to prevent homoglyph and encoding attacks
- **Invisible character stripping**: Removes zero-width characters, direction overrides, and other invisible Unicode used to hide injection payloads
- **Boundary sanitization**: Cleans input boundaries to prevent instruction leakage
- **Auto-wrapping of web fetch/search results**: Content retrieved from the internet is automatically wrapped in boundary markers before being presented to the agent

---

## Tool Access Control and Policy Pipeline

OpenClaw enforces tool access through a multi-layer policy pipeline:

- **Deny list**: High-risk tools are blocked by default
- **Multi-layer policy pipeline**: Requests pass through multiple policy evaluation stages before being approved or denied
- **Fail-closed semantics**: If any policy layer cannot evaluate a request, the request is denied
- **Loop detection** (opt-in): Detects and breaks tool-call loops where an agent repeatedly calls the same tool with identical or cycling parameters
- **Plugin approval**: Third-party plugins require explicit approval; if the approval process times out, the plugin is denied by default

---

## Authentication Rate Limiting

OpenClaw implements multiple rate limiting layers to protect against brute-force and denial-of-service attacks:

- **Sliding-window rate limiter**: Tracks request counts over a rolling time window for authenticated operations
- **Control plane limiter**: Limits the rate of control plane API calls (e.g., configuration changes, policy updates)
- **WebSocket flood guard**: Prevents WebSocket connection exhaustion by limiting connection rate and concurrent connections per client
- **Pre-auth budget**: Limits the number of unauthenticated requests before requiring a full authentication cycle

---

## Environment Variable Security Policy

OpenClaw enforces a security policy on environment variable access to prevent privilege escalation and injection attacks:

- **Always-blocked keys**: Variables like `NODE_OPTIONS`, `LD_PRELOAD`, and similar are always blocked regardless of configuration. These can be used to inject code or alter runtime behavior.
- **Override-blocked keys**: Additional keys blocked by operator configuration
- **Blocked prefixes**: Key prefixes that are denied (e.g., `npm_config_` to prevent package manager manipulation)
- **Universal blocked prefixes**: Prefixes blocked across all contexts, including development

---

## Security Audit Framework

OpenClaw includes a built-in security audit framework:

```bash
openclaw security audit
```

The audit runs **50+ distinct check types**, including:

- Synced-folder leak detection
- Plaintext secrets scanning
- Hooks hardening validation
- Gateway no-auth detection
- Sandbox misconfiguration checks
- Weak-model susceptibility analysis
- Multi-user exposure matrix evaluation
- Node command policy validation
- Dangerous config flag scanning

Run the audit regularly and before any production deployment.

---

## Skill and Extension Supply Chain Scanning

OpenClaw scans skills and extensions before installation using a static analysis scanner. Critical findings **block** installation entirely.

The scanner checks for:

- Direct process execution (e.g., `child_process.exec`)
- Dynamic code execution (e.g., `eval`, `Function()`)
- Crypto mining patterns
- Unexpected network activity
- Data exfiltration patterns
- Obfuscated code
- Environment variable harvesting combined with network calls

---

## DM and Group Messaging Access Policy

OpenClaw provides granular control over direct message and group messaging access:

### DM Policy Modes

| Mode | Behavior |
|---|---|
| `open` | Any user can DM the agent |
| `disabled` | DMs are completely blocked |
| `pairing` | Users must complete a pairing flow before DM access is granted |
| `allowlist` | Only users on an explicit allowlist can DM the agent |

### Additional Controls

- **Per-group rules**: Different groups can have different messaging policies
- **Per-sender authorization**: Individual senders can be authorized or revoked independently
- **Command authorization**: Specific commands within DMs can be restricted
- **Multi-user detection**: Detects and handles scenarios where multiple users share a single DM channel

---

## Context Visibility and Output Controls

OpenClaw provides controls for managing what context is visible to the agent and what output is delivered to users. These controls prevent sensitive information from leaking through agent responses and ensure that agents only access the context they need for a given operation.

---

## Safe Regex (ReDoS Prevention)

OpenClaw implements safe regex evaluation to prevent Regular Expression Denial of Service (ReDoS) attacks. All regex patterns used in policy evaluation, prompt injection detection, and other security-critical paths are evaluated with safeguards against catastrophic backtracking. This prevents a maliciously crafted input from causing exponential evaluation time and resource exhaustion.
