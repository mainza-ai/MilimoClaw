# Sandbox Security Audit — 2026-04-25

**Summary**: Critical audit of NemoClaw sandbox security violations caused by MilimoClaw's `install.sh` directly modifying the NemoClaw-managed sandbox. Documents root causes, all identified violations, and the corrective path.

**Sources**:
- Live sandbox inspection (2026-04-25)
- `install.sh` — MilimoClaw installer script
- `Dockerfile` — Docker-based deployment
- NemoClaw documentation (architecture, sandbox-hardening, network-policies, best-practices)
- NemoClaw sandbox policy (`openclaw-sandbox.yaml`)

**Last updated**: 2026-04-25

**Tags**: #troubleshooting #security #sandbox #critical

---

## Executive Summary

MilimoClaw's `install.sh` script **directly manipulates the NemoClaw-managed sandbox**, bypassing the security model that NemoClaw provides. This has resulted in a **broken sandbox** where:

1. `openclaw.json` is owned by `root:root` with mode `600`, unreadable by the `sandbox` user (uid 998)
2. The OpenClaw gateway cannot start because it cannot read its own config
3. Multiple directories inside `/sandbox/` are owned by `root` instead of `sandbox`
4. The Landlock filesystem policy is violated by files created outside the allowed writable paths
5. API keys and tokens are hardcoded into `.bashrc` inside the sandbox

> **Impact**: The sandbox is currently **non-functional**. `openclaw tui`, `openclaw agent`, and all Milimo Claw commands fail with `EACCES: permission denied`.

---

## Root Cause Analysis

### The Fundamental Problem

NemoClaw creates and manages the sandbox with a strict security model:

```
NemoClaw Sandbox Security Model:
┌─────────────────────────────────────────────────┐
│  /sandbox/.openclaw/          → READ-ONLY       │
│  /sandbox/.openclaw/openclaw.json → IMMUTABLE   │
│  /sandbox/                    → READ-ONLY       │
│  /sandbox/.openclaw-data/     → READ-WRITE      │
│  /sandbox/.nemoclaw/          → READ-WRITE      │
│  /tmp/                        → READ-WRITE      │
└─────────────────────────────────────────────────┘
Process runs as: sandbox:sandbox (uid 998:gid 998)
```

MilimoClaw's `install.sh` runs commands via `docker exec ... kubectl exec` which executes as **root** inside the sandbox, bypassing Landlock and filesystem protections. It then writes files, changes ownership, and modifies config files in paths that NemoClaw designates as **read-only and immutable**.

### What NemoClaw Expects

Per NemoClaw documentation:
- `/sandbox/.openclaw/openclaw.json` is **gateway-managed** — written by the onboarding wizard and locked down. Plugins should NOT modify it directly.
- `/sandbox/.openclaw/` is **read-only** via Landlock. The `include_workdir: false` setting ensures the home directory is not auto-writable.
- `/sandbox/.openclaw-data/` is the **only writable path** for agent state, plugins, workspace, etc.
- Extensions are installed via `openclaw plugins install <path>` which handles registration through the proper OpenClaw APIs.

### What `install.sh` Does Wrong

The installer uses `kubectl exec` (running as root) to:

1. **Write directly to `/sandbox/.openclaw/openclaw.json`** (line 703) — modifying the immutable config
2. **`chown -R sandbox:sandbox /sandbox/.openclaw`** (line 605) — changing ownership of the read-only config dir
3. **`chmod -R 755 /sandbox/.openclaw`** (line 606) — weakening permissions on the immutable config
4. **Creates files in `/sandbox/.local/`** as root (line 472-492) — `gh` CLI, `milimo` wrapper
5. **Creates files in `/sandbox/extensions/`** as root (line 288-293) — outside writable paths
6. **Injects secrets into `/sandbox/.bashrc`** (line 536-558) — API keys in plaintext
7. **Deletes agent sessions and memory** (line 862-866) — destructive operations on agent state
8. **Creates `/sandbox/.milimo/`** directory tree — outside NemoClaw's writable paths

---

## Detailed Violation Registry

### CRITICAL — Config File Ownership

| Issue | Details |
|-------|---------|
| **File** | `/sandbox/.openclaw/openclaw.json` |
| **Expected** | Owned by `sandbox:sandbox` with mode `600` (NemoClaw default) OR locked `root:root` with `444` (Dockerfile model) |
| **Actual** | Owned by `root:root` with mode `600` — **unreadable by sandbox user** |
| **Cause** | `install.sh` line 703 writes to the file via Python as root; subsequent operations leave it root-owned |
| **Impact** | OpenClaw gateway fails to start, `openclaw tui` fails, all CLI commands fail |
| **Error** | `EACCES: permission denied, open '/sandbox/.openclaw/openclaw.json'` |

### CRITICAL — Gateway Not Running

| Issue | Details |
|-------|---------|
| **Symptom** | `nemoclaw my-assistant connect` reports "OpenClaw gateway is not running inside the sandbox" |
| **Cause** | Gateway process (running as `sandbox` user) cannot read `openclaw.json` |
| **Impact** | No inference routing, no agent communication, sandbox is non-functional |

### HIGH — Root-Owned Files in Sandbox

Files that should be owned by `sandbox:sandbox` but are owned by `root:root`:

| Path | Created By |
|------|-----------|
| `/sandbox/.local/` (entire tree) | `install.sh` — gh CLI + milimo wrapper |
| `/sandbox/.local/bin/gh` | `install.sh` line 461 |
| `/sandbox/.local/bin/milimo` | `install.sh` line 474 |
| `/sandbox/.local/lib/python3.11/` | `install.sh` line 438 |
| `/sandbox/extensions/` | `install.sh` line 289 |
| `/sandbox/.openclaw-data/extensions/milimo/` | `install.sh` line 314 |
| `/sandbox/milimo-blueprint/.venv/` | `install.sh` line 497-514 |
| `/sandbox/.openclaw/tasks/` | OpenClaw gateway (runs as root) |
| `/sandbox/.openclaw-data/devices/` files | OpenClaw device pairing |
| `/sandbox/.openclaw-data/memory/` | OpenClaw memory |
| `/sandbox/.openclaw-data/telegram/` | Telegram bridge |

### HIGH — Secrets in Shell Profile

| Issue | Details |
|-------|---------|
| **File** | `/sandbox/.bashrc` (lines 42-56) |
| **Content** | NVIDIA_API_KEY, STRIPE_SECRET_KEY, GITHUB_TOKEN, SENTRY_AUTH_TOKEN, BUILD_CLAW_NVIDIA_API_KEY |
| **Risk** | Any process in the sandbox can read these secrets. Landlock protects files but not environment variables. Any agent-generated code that runs `env` or reads `.bashrc` leaks credentials. |
| **NemoClaw approach** | NemoClaw uses OpenShell's inference routing — the API key is in the **gateway container**, not the sandbox. The sandbox talks to `https://inference.local/v1` and OpenShell proxies to NVIDIA with the real key. |

### HIGH — Model Mismatch

| Issue | Details |
|-------|---------|
| **openclaw.json model** | `inference/minimaxai/minimax-m2.7` |
| **NemoClaw blueprint model** | `nvidia/nemotron-3-super-120b-a12b` |
| **API key in openclaw.json** | `nvapi-D3gAp...` (different from .env key) |
| **Risk** | The model was manually changed in openclaw.json, bypassing NemoClaw's inference routing. This means inference calls go directly from the sandbox to NVIDIA's API, circumventing OpenShell's security proxy. |

### MEDIUM — Landlock Policy Violations

The sandbox Landlock policy designates `/sandbox/` as **read-only** with explicit `read_write` exceptions for:
- `/tmp/`
- `/sandbox/.openclaw-data/`
- `/sandbox/.nemoclaw/`

The following MilimoClaw paths exist **outside** these writable zones:

| Path | Violation |
|------|-----------|
| `/sandbox/.milimo/` | Not in Landlock read_write list |
| `/sandbox/extensions/` | Not in Landlock read_write list |
| `/sandbox/milimo-blueprint/` | Not in Landlock read_write list |
| `/sandbox/content/`, `/sandbox/clients/`, etc. | Not in Landlock read_write list |
| `/sandbox/.local/` | Not in Landlock read_write list |

> **Note**: These files were written via `kubectl exec` (as root), which bypasses Landlock. But the `sandbox` user (uid 998) running OpenClaw processes **cannot write** to these paths at runtime. This creates a read-only deployment that can't be updated without root access.

### MEDIUM — Backup File Accumulation

| Issue | Details |
|-------|---------|
| **Files** | `openclaw.json.bak`, `.bak.1`, `.bak.2`, `.bak.3`, `.bak.4` |
| **Cause** | Repeated manual modifications creating backup copies |
| **Risk** | Old configs with different auth tokens and API keys persisted on disk |

---

## Correct Architecture

### How NemoClaw Expects Plugins to Work

```
Host Machine                         NemoClaw Sandbox
┌──────────────┐                    ┌──────────────────────────┐
│ nemoclaw CLI │──── onboard ──────▶│ OpenShell creates sandbox │
│              │                    │ with blueprint image       │
│              │                    │                            │
│              │                    │ OpenClaw gateway manages:  │
│              │                    │  - openclaw.json (immutable)│
│              │                    │  - inference routing        │
│              │                    │  - auth tokens              │
│              │                    │                            │
│              │                    │ Plugins installed via:      │
│              │                    │  openclaw plugins install   │
│              │                    │  → writes to .openclaw-data │
│              │                    │                            │
└──────────────┘                    └──────────────────────────┘
```

### What MilimoClaw Should Do Instead

1. **NemoClaw must be installed independently first** — clean sandbox, no modifications
2. **MilimoClaw installs as an OpenClaw plugin** via `openclaw plugins install` — writes only to `.openclaw-data/extensions/`
3. **Blueprint files go into `/sandbox/.openclaw-data/`** or `/sandbox/.nemoclaw/` — the only writable paths
4. **API keys stay on the host** — NemoClaw's OpenShell inference routing handles key management
5. **No direct `openclaw.json` modification** — model selection goes through `nemoclaw` CLI or `openclaw configure` (from host)
6. **No root-level operations** — all sandbox operations run as the `sandbox` user

---

## Corrective Action Plan

### Phase 1: Clean Slate — Nuke & Rebuild NemoClaw

```bash
# 1. Uninstall existing NemoClaw (from host)
curl -fsSL https://raw.githubusercontent.com/NVIDIA/NemoClaw/refs/heads/main/uninstall.sh | bash -s -- --yes

# 2. Reinstall NemoClaw fresh
export NVIDIA_API_KEY=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
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash

# 3. Verify clean sandbox
nemoclaw my-assistant connect
openclaw tui  # Should work without errors
```

### Phase 2: Rewrite `install.sh` to Respect NemoClaw Boundaries

The installer has been successfully rewritten and tested on the fresh NemoClaw sandbox. The following architectural boundaries are now strictly enforced:

1. **Plugin Registration:** Direct modification of `openclaw.json` was removed. The script now correctly registers the plugin using `openclaw plugins install /sandbox/.openclaw-data/extensions/milimo`.
2. **Writable State:** All Milimo files (blueprints, extensions, templates, configs, mesh data) have been migrated to `/sandbox/.openclaw-data/milimo/` which is fully writable under the NemoClaw Landlock policy.
3. **No Root Operations:** All `sandbox_exec` operations now run securely as the unprivileged `sandbox:sandbox` user (UID 998) instead of root, ensuring isolation.
4. **Secrets Management:** Environment variable injection (e.g. `NVIDIA_API_KEY`) into `.bashrc` and `.profile` was stripped out, as NemoClaw manages credentials out-of-band via inference routing on `https://inference.local/v1`.
5. **Backwards Compatibility:** A harmless symlink from `/sandbox/.milimo` to `/sandbox/.openclaw-data/milimo` was implemented to ensure unmodified python scripts within the Milimo blueprint continue working seamlessly.

### Phase 3: Verify Security Posture

Following the execution of the new `install.sh --solo --operator-name "Mainza" --squad-name "zulu"`, a comprehensive security and integrity check was performed on the active sandbox:

| Check | Result | Verification |
|-------|---------|----------|
| Config readable | **PASS** | `cat /sandbox/.openclaw/openclaw.json` succeeded for unprivileged sandbox user. |
| Gateway running | **PASS** | `openclaw-gateway` process actively proxying plugin actions. |
| TUI works | **PASS** | Milimo assistant is fully responsive. |
| No root files | **PASS** | `find /sandbox -user root` returned zero unauthorized files (only NemoClaw system `.workspace-initialized`). |
| No secrets in env | **PASS** | `env \| grep -i api_key` returned empty. |

The MilimoClaw plugin is now 100% natively compliant with the NemoClaw sandbox container runtime security model.

---

## Related Pages

- [[common-issues]] — Quick troubleshooting
- [[issues-and-fixes]] — Previous issues audit
- [[sandbox-sync]] — Sandbox synchronization
- [[sandbox-isolation]] — Sandbox security model
- [[privacy-router]] — Inference routing architecture
