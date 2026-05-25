# NemoClaw Blueprint Implementation Specification

> **Status**: Approved & Integrated (NemoClaw v0.0.38 / OpenClaw v2026.3.0 Standard)
> **Author**: Antigravity Harness
> **Last Updated**: 2026-05-25

---

## 1. Executive Summary & Sandboxed Extension Model

Milimo Claw is architected strictly as an **extension plugin running on top of the NVIDIA NemoClaw sandboxing runtime**. Rather than replacing or duplicating NemoClaw, Milimo leverages the native OpenShell sandboxing layer, Landlock LSM filesystem mounts, seccomp filters, and L7 http gateways to coordinate secure, multi-agent workspaces.

### Local-First Default Philosophy
To align with edge workloads and maintain **zero cloud token costs**, the default configuration routes inference to local edge endpoints:
* **Local RTX PCs / Servers**: Native `nvidia-nim` local service endpoint configuration (`nim-local`).
* **Apple Silicon / CPU Platforms**: OpenAI-compatible local vLLM endpoints (`vllm`) executing high-efficiency open models like `nvidia/nemotron-3-nano-30b-a3b` on unified memory.
* **Hybrid Backup**: Cloud hosted NIM endpoints are strictly configured as **high-resilience failover routes** utilized only when local hardware thresholds are breached.

---

## 2. Blueprint Manifest Anatomy (`blueprint.yaml`)

The blueprint manifest orchestrates all OpenShell resources, declaring dependencies, inference profiles, and layered network policy overrides.

```yaml
version: "0.1.0"
min_openshell_version: "0.0.24"
min_openclaw_version: "2026.3.0"

profiles:
  - default
  - ncp
  - nim-local
  - vllm
  - routed

components:
  sandbox:
    image: "ghcr.io/nvidia/openshell-community/sandboxes/openclaw:latest"
    name: "milimo-openclaw-sandbox"
    forward_ports:
      - 18789

  inference:
    profiles:
      default:
        provider_type: "nvidia"
        provider_name: "nvidia-inference"
        endpoint: "https://integrate.api.nvidia.com/v1"
        model: "nvidia/nemotron-3-super-120b-a12b"
        timeout_secs: 120

      nim-local:
        provider_type: "openai"
        provider_name: "nim-local"
        endpoint: "http://nim-service.local:8000/v1"
        model: "nvidia/nemotron-3-super-120b-a12b"
        credential_env: "NIM_API_KEY"
        timeout_secs: 180

      vllm:
        provider_type: "openai"
        provider_name: "vllm-local"
        endpoint: "http://localhost:8000/v1"
        model: "nvidia/nemotron-3-nano-30b-a3b"
        credential_env: "OPENAI_API_KEY"
        credential_default: "dummy"
        timeout_secs: 180

  policy:
    base: "sandboxes/openclaw/policy.yaml"
    additions:
      nim_service:
        name: nim_service
        endpoints:
          - host: "nim-service.local"
            port: 8000
            protocol: rest
```

---

## 3. Filesystem Hardening & Volume Isolation Rules

NemoClaw enforces strict file boundary constraints inside the container via Linux **Landlock LSM** policies. Under this isolation hierarchy, the `/sandbox` root is **strictly read-only**, except for explicitly allowed writable subdirectories.

### Milimo Filesystem Layout & Mount Boundaries
Each of the 6 claws runs inside an isolated sandbox mounted with highly restricted directories:

| Claw Role | Sandbox Volume Path (Writable) | Read-Only Mounts |
| :--- | :--- | :--- |
| **Content Claw** | `/sandbox/.openclaw-data/milimo/claws/content` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **Ops Claw** | `/sandbox/.openclaw-data/milimo/claws/ops` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **Analytics Claw** | `/sandbox/.openclaw-data/milimo/claws/analytics` | None |
| **Finance Claw** | `/sandbox/.openclaw-data/milimo/claws/finance` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **Build Claw** | `/sandbox/.openclaw-data/milimo/claws/build` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **Assistant Claw** | `/sandbox/.openclaw-data/milimo/claws/assistant` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |

### The Critical Shared Intelligence Mount
The Analytics Claw outputs the weekly intelligence report directly to:
```
/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence.json
```
To avoid inter-claw message overhead, every worker sandbox policy defines a **read-only cross-mount** targeting this directory. If the mount is removed, the intelligence layer fails silently. The Landlock sandbox configuration strictly prevents write attempts from other claws to this directory.

---

## 4. Advanced Network Policy & L7 HTTP Inspection

NemoClaw utilizes OpenShell L7 HTTP inspection (`protocol: rest`) to govern all external API integrations. Raw TCP traffic is intercepted by the OpenShell gateway, allowing fine-grained method and path restrictions.

### Policy Schema Constraints
1. **Deny Rules Take Precedence**: Deny rules are evaluated after allow rules. If a request matches any entry in `deny_rules`, it is blocked immediately.
2. **Binary-Scoped Enforcement**: Each network policy entry includes a `binaries` list of full paths. OpenShell reads `/proc/<pid>/exe` and walks the parent process tree to verify matching binary hashes. Mismatches trigger automatic connection rejection.
3. **SSRF Mitigation**: Unlisted hosts are blocked. Local loopback, link-local, and unspecified IPv4/IPv6 addresses are rejected unless explicitly declared in `allowed_ips`.

### REST Policy Configuration Example
The following preset governs secure, scoped access to the GitHub API for the Build Claw:

```yaml
network_policies:
  github_rest_api:
    name: github-rest-api
    endpoints:
      - host: api.github.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
        deny_rules:
          - method: POST
            path: "/repos/*/pulls/*/reviews" # Deny auto-approving reviews
          - method: PUT
            path: "/repos/*/branches/*/protection" # Deny branch protection overrides
          - method: "*"
            path: "/repos/*/rulesets" # Deny ruleset manipulation
    binaries:
      - path: /usr/local/bin/claude
      - path: /usr/bin/node
      - path: /usr/bin/gh
```

---

## 5. Command Integration & Credential Protection Lifecycle

All sandbox interactions, policy modifications, and credentials are governed by the `nemoclaw` CLI.

### Automatic Credential Migration
NemoClaw stores external credentials exclusively in the in-memory **OpenShell Gateway Store**.
* Legacy file storage (`~/.nemoclaw/credentials.json`) is completely **deprecated**.
* On execution of `nemoclaw onboard` after upgrading, NemoClaw auto-migrates credentials from the legacy file to the gateway memory and **securely deletes** the legacy file.
* Environment variables take precedence.

### Channels Management CLI (`telegram`, `discord`, `slack`)
The assistant's conversational interfaces are isolated in sandbox bridges and managed dynamically:
* **Pause a channel**:
  ```bash
  nemoclaw my-assistant channels stop telegram
  ```
  This marks the channel as disabled in the per-sandbox registry, rebuilds the sandbox, and skips registering the bridge with the gateway. Credentials remain secure in the gateway store.
* **Resume a channel**:
  ```bash
  nemoclaw my-assistant channels start telegram
  ```
  Restores registration utilizing existing credentials without requiring re-authentication.

### Dynamic Policy Management (`policy-add` vs `policy set`)
* **Recommended Merge Path (`policy-add`)**:
  Merges dynamic presets without breaking currently active layers.
  ```bash
  nemoclaw my-assistant policy-add pypi --yes
  ```
* **Advanced Raw Path (`openshell policy set`)**:
  *WARNING*: Replaces the sandbox's running policy in its entirety instead of merging.
  If used, the running configuration must be snapshotted first:
  ```bash
  openshell policy get --full my-assistant > live-policy.yaml
  # Edit live-policy.yaml to append new groups
  openshell policy set --policy live-policy.yaml my-assistant
  ```

---

## 6. Strategic Enhancements (The Path to v3.0)

To fully harness NemoClaw's capabilities under the hardware-agnostic local-first model, the following strategic modules are designed:

### A. Dynamic Failover Inference Broker
Monitors local inference latency and hot-swaps to fallback clouds dynamically.

```python
import os
import httpx
import logging

class FailoverInferenceBroker:
    def __init__(self, primary_url: str, fallback_url: str):
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.latency_threshold_ms = 800.0

    async def get_active_endpoint(self) -> str:
        # Fast local ping
        try:
            async with httpx.AsyncClient(timeout=0.5) as client:
                resp = await client.get(f"{self.primary_url}/health")
                if resp.status_code == 200:
                    return self.primary_url
        except Exception:
            pass
        # Fallback to cloud NIM if local is overloaded or unresponsive
        logging.warning("Primary edge NIM degraded. Routing to high-performance Cloud NIM.")
        os.environ["NEMOCLAW_MODEL"] = "nvidia/nemotron-3-super-120b-a12b"
        return self.fallback_url
```

### B. Zero-Knowledge (ZK) L7 Secret Proxy
The seccomp container has no direct filesystem access to API tokens. The OpenShell proxy intercepts outgoing HTTP requests, extracts secrets from the in-memory gateway store, appends authorization headers, and routes them to external APIs (Stripe, GitHub), redacting raw credentials from client-side execution logs.
