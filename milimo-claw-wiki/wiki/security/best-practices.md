# Security Best Practices

> **NemoClaw Compliance Notice**: This page documents security controls as implemented by NVIDIA NemoClaw and OpenShell. MilimoClaw operates within the NemoClaw sandbox and inherits all controls described here. Any discrepancy between this page and the [official NemoClaw documentation](https://docs.nvidia.com/nemoclaw/latest/security/best-practices.html) should be reported and resolved in favor of the official docs.

## Protection Layers

NemoClaw implements four distinct protection layers, each with specific enforcement mechanisms and change requirements.

| Layer | Threats | Enforcement | Change Requirement |
|---|---|---|---|
| **Network** | Unauthorized outbound connections, data exfiltration | OpenShell gateway | Hot-reloadable at runtime via `openshell policy set` or operator approval |
| **Filesystem** | System binary tampering, credential theft, config manipulation | Landlock LSM + container mounts | Requires sandbox re-creation |
| **Process** | Privilege escalation, fork bombs, syscall abuse | Container runtime (Docker/K8s securityContext) | Requires sandbox re-creation |
| **Inference** | Credential exposure, unauthorized model access, cost overruns | OpenShell gateway | Hot-reloadable via `openshell inference set` |

---

## Network Controls

### Deny-by-Default Egress

All outbound network traffic is denied by default. Every connection must be explicitly authorized through policy rules or operator approval.

### Binary-Scoped Endpoint Rules

OpenShell enforces binary-scoped endpoint rules to ensure only intended processes can reach specific endpoints:

1. OpenShell reads `/proc/<pid>/exe` to identify the calling binary
2. Walks the process tree to trace ancestry
3. Computes a SHA256 hash on first use to fingerprint the binary
4. Subsequent calls verify the binary hash matches the registered value

This prevents substituted or tampered binaries from leveraging authorized network paths.

### Path-Scoped HTTP Rules

HTTP rules can be scoped to specific URL paths, allowing granular control over which REST endpoints an agent may access. A rule for `api.example.com/v2/data` does not grant access to `api.example.com/v2/admin`.

### L4-Only vs L7 Inspection

The `protocol` field in policy rules determines the inspection depth:

- **Without `protocol` field**: L4-only inspection. The gateway permits or denies connections based on host and port. It cannot inspect HTTP paths, headers, or request bodies.
- **With `protocol: rest`**: L7 inspection is enabled. The gateway parses HTTP traffic and enforces path-scoped `access` or `rules` constraints. Required for any REST API endpoint that needs path-level access control.

### Operator Approval Flow

When an agent attempts to reach a blocked endpoint:

1. The blocked request appears in the `openshell term` TUI
2. An operator reviews the request and approves or denies it
3. Approved endpoints persist within the current sandbox instance
4. Approved endpoints are **reset** when the sandbox is destroyed and recreated

### Policy Presets

NemoClaw ships with pre-built policy presets for common services:

| Preset | Service |
|---|---|
| `brave` | Brave Search API |
| `brew` | Homebrew |
| `discord` | Discord API |
| `github` | GitHub API |
| `huggingface` | Hugging Face Hub |
| `jira` | Jira Cloud API |
| `npm` | npm Registry |
| `outlook` | Microsoft Outlook |
| `pypi` | Python Package Index |
| `slack` | Slack API |
| `telegram` | Telegram Bot API |

Apply a preset with `nemoclaw <name> policy-add <preset>`. For dynamic full-policy replacement (destructive), use `openshell policy set --policy <file> <sandbox>` — see [[cli-commands]] for warnings.

---

## Filesystem Controls

### Read-Only System Paths

The following system paths are mounted read-only to prevent binary tampering, credential theft, and configuration manipulation:

- `/usr`
- `/lib`
- `/proc`
- `/dev/urandom`
- `/app`
- `/etc`
- `/var/log`

### Read-Only `.openclaw` Config

The `/sandbox/.openclaw` directory is protected with multiple layers:

- Root-owned with `chmod 444`
- Made immutable via `chattr +i`
- Symlink validation on all path resolutions
- Config integrity hash (SHA256) verified on access

This prevents agents from modifying gateway configuration, injecting malicious settings, or replacing config files via symlinks.

### Writable Paths

The NemoClaw sandbox applies filesystem access at two levels with different semantics:

| Level | `/sandbox` | `/sandbox/.openclaw` | `/sandbox/.nemoclaw` | `/tmp` |
|---|---|---|---|---|
| **Container mount** | Read-write | Read-only | Read-write | Read-write |
| **Landlock LSM** (5.13+) | Read-only | Read-only | Read-write | Read-write |
| **DAC / fallback** | Read-write | Read-only (root-owned, `chattr +i`) | Read-write (root-owned subdirs) | Read-write |

On kernels with Landlock support (5.13+), `/sandbox` is restricted to read-only at the kernel level. Only the explicitly declared subdirectories (`.openclaw/milimo/`, `.nemoclaw/`, `/tmp`) are writable. On older kernels or macOS Docker, Landlock is silently skipped and protection falls back to DAC (file ownership and permissions) only.

The official docs reflect this two-level design: [Security Best Practices](https://docs.nvidia.com/nemoclaw/latest/security/best-practices.html) lists `/sandbox` as read-write (mount level), while [Sandbox Hardening](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html) and [Architecture](https://docs.nvidia.com/nemoclaw/latest/reference/architecture.html) describe `/sandbox` as read-only (Landlock level).

Key writable paths under `/sandbox`:

- `/sandbox/.openclaw/milimo/` — MilimoClaw plugin data (blueprints, claws, config, mesh)
- `/sandbox/.openclaw/workspace/` — agent workspace files
- `/sandbox/.nemoclaw/` — plugin state and config (DAC-protected, root-owned blueprints)
- `/tmp` — temporary files and logs
- `/dev/null`

### Landlock LSM

Filesystem access control uses the Linux Landlock LSM:

- Configuration: `compatibility: best_effort`
- Requires kernel 5.13+
- On older kernels or macOS Docker: Landlock is silently skipped, falling back to DAC only

---

## Process Controls

### Capability Drops

The container entrypoint drops the following Linux capabilities via `capsh`:

- `cap_net_raw`
- `cap_dac_override`
- `cap_sys_chroot`
- `cap_fsetid`
- `cap_setfcap`
- `cap_mknod`
- `cap_audit_write`
- `cap_net_bind_service`

The following capabilities are **retained** for `gosu` user switching:

- `cap_chown`
- `cap_setuid`
- `cap_setgid`
- `cap_fowner`
- `cap_kill`

### Gateway Process Isolation

The OpenShell gateway runs as a separate `gateway` user via `gosu gateway`. This isolates the gateway process from the sandboxed agent process.

### No New Privileges

OpenShell sets `PR_SET_NO_NEW_PRIVS` using `prctl()` inside the sandbox process. This is a separate `prctl()` call, not part of a seccomp filter. NemoClaw does NOT add its own seccomp BPF filters. The Docker Compose configuration also specifies `security_opt: no-new-privileges:true`.

This prevents any child process from gaining more privileges than its parent, blocking `sudo`, `su`, and SUID-based escalation.

### Process Limit

The maximum number of processes is constrained with `ulimit -u 512` (best-effort). This mitigates fork bombs and resource exhaustion attacks.

### Non-Root User

The sandbox runs as the `sandbox` user and group. No process inside the container runs as root.

### PATH Hardening

The `PATH` is locked to:

```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

This prevents agents from executing binaries from writable directories.

### Build Toolchain Removal

The following tools are explicitly purged from the sandbox image:

- `gcc`, `gcc-12`
- `g++`, `g++-12`
- `cpp`, `cpp-12`
- `make`
- `netcat-openbsd`, `netcat-traditional`, `ncat`

Removing these prevents agents from compiling exploits or probing the network from within the sandbox.

### Image Digest Pinning

All container images are pinned by digest (SHA256) rather than by tag. This ensures immutable, reproducible builds and prevents supply chain attacks via tag mutation.

### Auth Profile Permissions

All `auth-profiles.json` files are set to `chmod 600`. Only the owning user can read or write credential profiles.

---

## Gateway Authentication Controls

### Device Authentication

Device authentication is **enabled by default**. The gateway verifies the identity of connecting clients before allowing any operations.

### Insecure Auth Derivation

Insecure auth mode is derived from the `CHAT_UI_URL` scheme. If `CHAT_UI_URL` uses `http://` instead of `https://`, the gateway enables insecure auth automatically. Use `https://` in production.

### Auto-Pair Client Allowlist

The gateway auto-pairs only the following clients:

- `openclaw-control-ui`
- `webchat`

Other clients must be explicitly authorized.

### CLI Secret Redaction

Secrets are redacted from CLI output. Displaying credentials via `openshell provider list` or similar commands shows provider names but never credential values.

### Memory Secret Scanner

The memory secret scanner intercepts Write and Edit tool calls targeting memory or workspace paths. It scans content against 14 high-confidence patterns before allowing the write. Matches are blocked to prevent credential leakage into agent-readable storage.

---

## Inference Controls

### Routed Inference

All inference requests are routed through `inference.local`. The agent **never** receives the API key directly. The gateway injects credentials at egress, and the agent only sees placeholders.

### Provider Trust Tiers

| Tier | Providers | Behavior |
|---|---|---|
| **Tested** | NVIDIA Endpoints, OpenAI, Anthropic, Google Gemini | Fully supported, tested during onboarding |
| **Compatible** | Other OpenAI-compatible, Other Anthropic-compatible | User-supplied base URL and model |
| **Local** | Ollama, NVIDIA NIM, vLLM | Self-hosted; NIM and vLLM require `NEMOCLAW_EXPERIMENTAL=1` |

### Experimental Providers

Experimental providers are blocked by default. To enable them, set the environment variable:

```bash
NEMOCLAW_EXPERIMENTAL=1
```

---

## Policy Tiers vs Posture Profiles

NemoClaw uses two distinct classification systems for security configuration. **Policy tiers** are selected during `nemoclaw onboard` and determine which network policy presets are applied. **Posture profiles** are operational guidance on which controls to keep tight or relax.

### Policy Tiers (selected during `nemoclaw onboard`)

| Tier | Presets Included | Description |
|---|---|---|
| **Restricted** | None | Base sandbox only. No third-party network access beyond inference and core agent tooling. |
| **Balanced** (default) | `npm`, `pypi`, `huggingface`, `brew`, `brave` | Full dev tooling and web search. No messaging platform access. |
| **Open** | `npm`, `pypi`, `huggingface`, `brew`, `brave`, `slack`, `discord`, `telegram`, `jira`, `outlook` | Broad access across third-party services including messaging and productivity. |

Set the tier non-interactively with `NEMOCLAW_POLICY_TIER`:

```bash
NEMOCLAW_POLICY_TIER=restricted nemoclaw onboard --non-interactive --yes-i-accept-third-party-software
```

After selecting a tier, a combined preset and access-mode screen lets you include or exclude individual presets and toggle each between read and read-write access.

### Posture Profiles (operational guidance)

Posture profiles are **not separate policy files** — they provide guidance on which controls to keep tight or relax for different use cases.

#### Locked-Down (Default)

- Keep all defaults. Do not add presets.
- Use operator approval for any endpoint the agent requests.
- Use NVIDIA Endpoints or local Ollama for inference.
- Monitor the TUI for unexpected network requests.

#### Development

- Apply the `pypi` and `npm` presets for package installation.
- Keep binary restrictions on all presets.
- Review the agent's network activity periodically with `openshell term`.
- Use operator approval for any endpoint not covered by a preset.

#### Integration Testing

- Add custom endpoint entries with tight path and method restrictions.
- Use `protocol: rest` for all HTTP APIs to maintain inspection.
- Use operator approval for unknown endpoints during test runs.
- Review and clean up the baseline policy after testing. Remove endpoints that are no longer needed.

---

## Common Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Omitting `protocol: rest` on REST API endpoints | Gateway cannot enforce path-level rules; agent may access unintended paths | Add `protocol: rest` to all HTTP API rules |
| Adding endpoints to baseline for one-off requests | Permanently widens attack surface for a temporary need | Use operator approval for one-off requests instead |
| Relying solely on entrypoint for capability drops | Capabilities can be re-acquired if entrypoint is bypassed | Use `--cap-drop=ALL` at the container runtime level |
| Granting write access to `/sandbox/.openclaw` | Agent can modify gateway config, disable security controls | Keep `.openclaw` read-only and immutable |
| Adding inference provider hosts to network policy | Agent may bypass gateway and send credentials directly to providers | Rely on `inference.local` routing; do not add provider hosts |
| Disabling device auth for remote deployments | Unauthorized clients can connect to the gateway | Keep device auth enabled; use `https://` for `CHAT_UI_URL` |

---

## Known Limitations

- **`openclaw agent --local` bypasses the gateway**: The `--local` flag runs the agent outside the sandbox, bypassing all network and inference controls. Do not use `--local` in production.
- **Direct filesystem writes bypass the secret scanner**: The memory secret scanner only intercepts Write/Edit tool calls. Writes initiated through other mechanisms (e.g., shell commands) are not scanned.
- **Base64/hex-encoded secrets are not detected**: The secret scanner matches plaintext patterns. Encoded secrets may pass through undetected.
