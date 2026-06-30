---
title: NemoClaw Blueprint Implementation
tags: [reference, nemoclaw, sandboxing, policy, configuration]
created: 2026-05-25
updated: 2026-05-25
---

# NemoClaw Blueprint Implementation

> **Authoritative Specification**: NVIDIA NemoClaw v0.0.38 & OpenClaw v2026.3.0 Standard integration for the Milimo Squad.

---

## 1. Sandbox Blueprint Model

Under the Milimo architecture, all active agents (known as [[claws]]) run inside isolated Linux containers managed by the [[NemoClaw Reference]] runtime. The squad is configured via the declarative `blueprint.yaml` configuration manifest, defining image origins, ports, and runtime inference profiles.

### Core Blueprint Configuration (`blueprint.yaml`)
The manifest registers the environment constraints and maps how models are resolved across edge and cloud backends:

```yaml
version: "0.1.0"
min_openshell_version: "0.0.24"
min_openclaw_version: "2026.3.0"

profiles:
  - default      # Cloud hosted NVIDIA NIM (Nemotron 3 Super 120B)
  - ncp          # NVIDIA Partner Cloud (Nemotron Ultra 253B)
  - nim-local    # Local NVIDIA NIM (Edge GPU compute)
  - vllm         # Local vLLM (Mac Silicon / Local CPU/GPU server)
  - routed       # Private Local Failover Router

components:
  sandbox:
    image: "ghcr.io/nvidia/openshell-community/sandboxes/openclaw:latest"
    name: "milimo-openclaw-sandbox"
    forward_ports:
      - 18790

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

## 2. Filesystem Mounts & Directory Isolation

NemoClaw sandboxes use Linux **Landlock LSM** to enforce directory isolation. Under this system, filesystem access outside designated workspace directories is strictly read-only.

### Shared Intelligence Layer Mount
A critical mount is established for multi-claw analytics. The [[analytics-claw]] generates a weekly report and saves it to a shared directory. To allow other claws to query this intel without inter-claw message overhead, the directories are mounted inside each sandbox as **read-only**:

```
/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence.json
```

### Mount Matrix & Permissions

| Claw Role | Mount Target (Writable) | Read-Only Access Paths |
| :--- | :--- | :--- |
| **[[content-claw]]** | `/sandbox/.openclaw-data/milimo/claws/content` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **[[ops-claw]]** | `/sandbox/.openclaw-data/milimo/claws/ops` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **[[analytics-claw]]** | `/sandbox/.openclaw-data/milimo/claws/analytics` | None |
| **[[finance-claw]]** | `/sandbox/.openclaw-data/milimo/claws/finance` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **[[build-claw]]** | `/sandbox/.openclaw-data/milimo/claws/build` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |
| **[[assistant-lucy]]**| `/sandbox/.openclaw-data/milimo/claws/assistant` | `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` |

---

## 3. L7 HTTP Network Policies (`protocol: rest`)

Egress network traffic inside the sandbox is blocked by default. Layer 7 inspection is configured on allowed endpoints to limit operations by HTTP method and path pattern.

### Advanced Egress Guardrails
* **Deny Rules Overriding**: Deny rules are evaluated last and take absolute precedence over allow lists to prevent malicious operations.
* **Process Scoping (`binaries` field)**: Endpoint permissions are bounded strictly to specific executable paths (e.g. Node, NPM, Pyenv). OpenShell computes and verifies SHA256 hashes of running binaries dynamically.
* **SSRF Protection**: Custom allowed CIDR networks are declared under `allowed_ips` while system interfaces are strictly blocked.

### Example Github Rest Policy Configuration
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
            path: "/repos/*/pulls/*/reviews" # Deny auto-merging PR reviews
          - method: PUT
            path: "/repos/*/branches/*/protection" # Protect branch security policies
          - method: "*"
            path: "/repos/*/rulesets" # Protect repo rule sets
    binaries:
      - path: /usr/local/bin/claude
      - path: /usr/bin/node
      - path: /usr/bin/gh
```

---

## 4. CLI Integrations & Credentials Lifecycle

Administrative tasks and sandbox management are handled through the `nemoclaw` CLI.

### Automatic Credential Migration
Raw API credentials are kept exclusively in the in-memory **OpenShell Gateway Store**.
* Direct filesystem persistence (`~/.nemoclaw/credentials.json`) is **fully deprecated** and unsupported.
* On the first run of `nemoclaw onboard` after upgrading, NemoClaw migrates existing values to the gateway store and **permanently deletes** the legacy file.

### Dynamic Policy Modification
* **The Merge Way (`policy-add`)**:
  Merges dynamic presets without breaking currently active layers.
  ```bash
  nemoclaw my-assistant policy-add stripe --yes
  ```
* **The Replacement Way (`openshell policy set`)**:
  *WARNING*: Overwrites the running policy in its entirety instead of merging.
  To apply changes safely, first snapshot the running state:
  ```bash
  openshell policy get --full my-assistant > live-policy.yaml
  # Edit live-policy.yaml to append new presets under network_policies:
  openshell policy set --policy live-policy.yaml my-assistant
  ```

---

## 5. Strategic Enhancements

Milimo implements advanced architectural proxies to bridge security and local-first requirements:

### Failover Inference Broker
Enables dynamic routing heartbeats inside the [[privacy-router]]. If local edge NIM latency benchmarks are breached, the broker updates standard environment parameters (`NEMOCLAW_MODEL`) to seamlessly route request structures to remote high-performance cloud backups.

### Zero-Knowledge Token Injection Proxy
Secrets (Stripe, Vercel, Github API tokens) are never mounted inside worker sandboxes. The OpenShell proxy intercepts external HTTP calls, extracts tokens from the in-memory store, appends authorization headers at L7, and securely strips credentials from outgoing logging scopes.

---

## See Also
* [[NemoClaw-Reference]]
* [[NemoClaw-x-Milimo-Integration-Map]]
* [[system-overview]]
* [[sandbox-isolation]]
* [[inter-claw-communication]]
