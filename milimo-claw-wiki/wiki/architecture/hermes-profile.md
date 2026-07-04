# Hermes Profile — Dual-Track Integration

**Summary**: Hermes profile architecture for MilimoClaw — web dashboard (port 18790), OpenAI-compatible API (port 8642), native `delegate_task` + `cronjob` parallelism, binary-scoped network policy.

**Sources**:
- `implementation-plan.md`
- `milimo-hermes-plugin/`
- `milimo-blueprint/milimo-compatibility.json`
- `milimo-hermes-sandbox/`
- `docs/adr/001-subagent-isolation.md` through `005-delegation-asymmetry.md`

**Last updated**: 2026-07-04

**Tags**: #architecture #hermes #profile #dual-track

---

## Overview

| Aspect | OpenClaw Profile | Hermes Profile |
|--------|------------------|----------------|
| **Interface** | TUI + Bridge Server | Web Dashboard + OpenAI-compatible API |
| **Parallelism** | `sessions_spawn` (fire-and-forget, depth ≤ 2) | Native `delegate_task` (structured, no depth limit) |
| **Scheduling** | Python `threading.Timer` | Native `cronjob` (durable, survives interrupts) |
| **Network Policy** | Hostname allowlist | Binary-scoped (hostname + `/opt/hermes/.venv/bin/python`) |
| **Sandbox Name** | `milimo-openclaw-sandbox` | `milimo-hermes` |
| **Credential Model** | OpenShell L7 proxy | GitHub: `gh auth token`; Others: OpenShell placeholders |
| **Model Routing** | Build Claw scheduler | `delegation.model_overrides` per claw |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      NemoClaw Hermes Sandbox                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Hermes Agent Runtime                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │  │ delegate_task│  │   cronjob   │  │  OpenShell  │      │   │
│  │  │  (parallel)  │  │ (scheduled) │  │    L7       │      │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │   │
│  └─────────┼────────────────┼────────────────┼─────────────┘   │
│            │                │                │                 │
│            ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Milimo Hermes Plugin                        │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │   │
│  │  │ Build  │ │Content │ │  Ops   │ │Analytics│ │Finance │  │   │
│  │  │ Claw   │ │ Claw   │ │ Claw   │ │ Claw    │ │ Claw   │  │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘  │   │
│  │  ┌────────┐                                             │   │
│  │  │Assistant│ (Lucy)                                     │   │
│  │  └────────┘                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │ milimo_core_primitives (shared)                      │ │   │
│  │  │  DelegationAdapter • SchedulerInterface • Credentials │ │   │
│  │  │  ToolGenerator • ToolValidator • ToolSandbox         │ │   │
│  │  │  GitHub • Vercel • Sentry • Stripe clients           │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Delegation Layer (`milimo-core/protocols/delegation.py`)
| Component | Purpose |
|-----------|---------|
| `ClawTask` | Task descriptor: `claw`, `goal`, `context`, `priority` |
| `ClawResult` | Result: `claw`, `output`, `success`, `error` |
| `DelegationAdapter` | ABC with `delegate(tasks)` and `delegate_single(task)` |
| `CLAW_TOOLSETS` | Per-claw toolsets: `build: [file, shell]`, `content: [web, file]`, etc. |
| `CLAW_CONTEXTS` | Per-claw system prompts |

### 2. Hermes Delegate Adapter (`milimo-hermes-plugin/delegation.py`)
- Implements `DelegationAdapter` using native `delegate_task`
- `DELEGATION_MAX_CONCURRENT_CHILDREN=6`
- Converts `ClawTask[]` → Hermes format with toolsets/context

### 3. Scheduling Layer (`milimo-core/protocols/scheduling.py`)
| Component | Purpose |
|-----------|---------|
| `ScheduledJob` | `name`, `cron_expression`, `handler`, `enabled`, `last_run`, `next_run` |
| `SchedulerInterface` | ABC: `schedule_job`, `unschedule_job`, `get_due_jobs`, `start`, `stop` |

### 4. Hermes Cron Scheduler (`milimo-hermes-plugin/hermes_scheduler.py`)
- Uses native `cronjob` (durable, survives interrupts)
- Jobs registered:
  - `evolution_cycle` — `0 2 * * 0` (Sunday 2AM)
  - `tool_backtest` — `0 */6 * * *` (every 6h)
  - `hold_queue_review` — `0 */4 * * *` (every 4h)

### 4b. Evolution Scheduler (`milimo-core/evolution_scheduler.py`)
- Implements `SchedulerInterface` from `milimo-core/protocols/scheduling.py`
- Uses existing `EvolutionCycle` logic for the 5-stage evolution pipeline:
  1. **OBSERVE** — Read operation log for past 7 days
  2. **IDENTIFY** — Detect recurring patterns
  3. **PROPOSE** — Generate tool proposal for strongest pattern
  4. **BUILD** — Generate tool code and backtest in sandbox
  5. **DEPLOY** — Activate, version blueprint, notify War Room
- Additional handlers:
  - `tool_backtest`: Backtests deployed evolved tools every 6 hours
  - `hold_queue_review`: Reviews HOLD queue items every 4 hours
- Synchronous wrappers for Hermes cronjob handlers:
  - `run_evolution_cycle_handler()` — Called by Hermes cronjob
  - `run_tool_backtest_handler()` — Called by Hermes cronjob
  - `run_hold_queue_review_handler()` — Called by Hermes cronjob

### 5. SSRF Validator (`milimo-core/ssrf_validator.py`)
- Validates egress endpoints in `milimo-blueprint/policies/milimo-mcp.yaml` against NemoClaw's SSRF policy
- Blocks private networks (RFC 1918, RFC 3927, RFC 4193), loopback, metadata services (169.254.169.254)
- Validates DNS resolution to public IPs only
- CLI: `python -m milimo_core.ssrf_validator --policy milimo-blueprint/policies/milimo-mcp.yaml --allow-local-nim`
- JSON output for CI integration

### 6. Credential Adapter (`milimo-core/hermes_credential_adapter.py`)
| Service | Resolution |
|---------|------------|
| GitHub | `gh auth token` (reads from GitHub CLI store) |
| Stripe | OpenShell placeholder: `STRIPE_API_KEY` |
| Vercel | OpenShell placeholder: `VERCEL_TOKEN` |
| Sentry | OpenShell placeholder: `SENTRY_AUTH_TOKEN` |
| NVIDIA | OpenShell placeholder: `NVIDIA_API_KEY` |

### 7. Core Tools (`milimo-hermes-plugin/tools.py`)
| Tool | Purpose |
|------|---------|
| `milimo_status` | All 6 claws status |
| `milimo_warroom` | HOLD queue, cost guard, approve/veto |
| `milimo_approve` | Approve HOLD item, optionally delegate |
| `milimo_veto` | Veto/reject HOLD item |
| `delegate_task` | Native Hermes delegation wrapper |

### 8. War Room (`milimo-hermes-plugin/warroom/warroom.html`)
- Standalone HTML served at `/warroom`
- htmx for auto-refresh (every 5s), zero build step
- Calls tool endpoints for live data

---

## Configuration

### `milimo-compatibility.json`
```json
{
  "delegation": {
    "max_concurrent_children": 6,
    "model_overrides": {
      "build": "nvidia/nemotron-3-ultra-550b-a55b",
      "content": "google/gemini-flash-2.0",
      "ops": "nvidia/nemotron-3-ultra-550b-a55b",
      "analytics": "google/gemini-flash-2.0",
      "finance": "nvidia/nemotron-3-ultra-550b-a55b",
      "assistant": "nvidia/nemotron-3-ultra-550b-a55b"
    }
  },
  "cron": { "jobs": [...] },
  "warroom": { "endpoint": "/warroom" },
  "cost_guard": { "daily_token_limit": 50000, "alert_threshold_percent": 80 },
  "auth": { "default_mode": "api_key", "nous_oauth": { "enabled": false } }
}
```
> Note: The default model for the sandbox is `stepfun-ai/step-3.7-flash` via NVIDIA NIM provider (`nvidia-nim`), set at runtime via `nemohermes inference set`. The `model_overrides` in `milimo-compatibility.json` define per-claw model preferences for delegation, not the sandbox default.

### Network Policy (`milimo-blueprint/policies/milimo-mcp.yaml`)
Binary-scoped egress — each rule specifies:
- Host + port + protocol
- Binary: `/opt/hermes/.venv/bin/python`

Hosts: GitHub, npm, PyPI, Stripe, Vercel, Sentry, Twitter/X, LinkedIn, TikTok, NVIDIA, IP geolocation

### Known Issues & Fixes

#### Gateway Fails to Start: `API_SERVER_KEY` Required
Hermes v2026.5.16+ requires a non-empty `API_SERVER_KEY` even for loopback-only binds.

**Fix** (`milimo-hermes-sandbox/generate-config.ts`):
The config generator now falls back to `crypto.randomBytes(32).toString("hex")` when `API_SERVER_KEY` is not provided as a build arg.

**Manual recovery** on a running sandbox:
```bash
# Generate a key and update .env:
nemohermes milimo-hermes exec -- sh -c 'API_KEY=$(head -c 32 /dev/urandom | xxd -p | head -c 64) && sed -i "s/^API_SERVER_KEY=$/API_SERVER_KEY=$API_KEY/" /sandbox/.hermes/.env'

# Restart gateway:
nemohermes milimo-hermes exec -- hermes gateway run --replace
```

#### Hermes Has No Context About MilimoClaw
The default `SOUL.md` (system prompt) doesn't describe MilimoClaw.

**Fix** (`milimo-hermes-sandbox/Dockerfile`):
The SOUL.md now includes a description of the six-claw mesh, environment paths, and the agent's role as the MilimoClaw gateway.

**Manual update** on a running sandbox:
```bash
# Apply new SOUL.md:
nemohermes milimo-hermes exec -- sh -c 'cat > /sandbox/.hermes/SOUL.md' < /tmp/milimo-soul.md
```

**Note:** After updating SOUL.md, start a new chat session (`hermes`) to see the context — existing sessions cache the old prompt.

#### Socat Forwarder Fails in `start.sh` (start_socat_forwarder)
The `start_socat_forwarder` function in the default `start.sh` (`/usr/local/bin/nemoclaw-start`) exits immediately without creating the port bridge. The health probe at `http://localhost:8642/health` times out, causing `nemohermes recover` to fail with a 90-second provisioning timeout.

**Fix** (baked in `milimo-hermes-sandbox/Dockerfile`):
`gateway-daemon.sh` runs its own socat forwarder (`0.0.0.0:8642 → 127.0.0.1:18642`) alongside the gateway, monitored every 30 seconds. This is the authoritative socat instance — the one in `start.sh` is redundant and its failure is harmless.

**Verification**: `curl -s http://localhost:8642/health` returns `200` within seconds of sandbox boot.

#### Version Mismatch Warning
```
⚠ Sandbox 'milimo-hermes' is running Hermes Agent 0.17.0 (current: 2026.5.16)
```
This is cosmetic. The Hermes binary reports `v0.17.0` (Python package version) while `nemohermes` compares against the release tag `2026.5.16`. The actual code is from the correct release (`hermes --version` shows `2026.6.19` git date). No impact on functionality.

#### Gateway Not Running After Sandbox Restart
```
Hermes Agent gateway is not running inside the sandbox (sandbox likely restarted).
  Recovering...
```
The gateway was started manually (not as a supervised service), so it doesn't survive container restarts.

**Root cause**: `openshell sandbox create --from` overrides the Dockerfile's `ENTRYPOINT`, so SysV init (`/etc/rcS.d/`) does not fire. The entrypoint binary (`openshell-sandbox`) does not source init scripts — it launches the sandbox user's shell.

**Fix** (baked in `milimo-hermes-sandbox/Dockerfile`):
The Dockerfile appends to `/sandbox/.bashrc` and `/sandbox/.profile` to launch `gateway-daemon.sh` in the background when the sandbox user logs in. SysV init fallback (`/etc/init.d/hermes-gateway` with rcS.d symlink) is also provided for environments where openshell-sandbox honours it.

`gateway-daemon.sh` supervises two processes:
- **Hermes gateway** (`hermes gateway run --replace`) — the API server on `127.0.0.1:18642`
- **Socat forwarder** (`0.0.0.0:8642 → 127.0.0.1:18642`) — bridges the nemohermes health probe port to the internal listener

Both processes are polled every 30 seconds and restarted if either exits.

**Manual fix** on an existing sandbox (if rebuilding is not an option):
```bash
# Upload the daemon scripts:
nemohermes milimo-hermes exec -- mkdir -p /opt/hermes/scripts
# (Use heredoc to write gateway-daemon.sh to /opt/hermes/scripts/)
# Install the .bashrc hook:
nemohermes milimo-hermes exec -- sh -c '
  echo "if [ -x /opt/hermes/scripts/gateway-daemon.sh ] && ! pgrep -f gateway-daemon.sh >/dev/null 2>&1; then" >> /sandbox/.bashrc
  echo "  /opt/hermes/scripts/gateway-daemon.sh >/dev/null 2>&1 &" >> /sandbox/.bashrc
  echo "fi" >> /sandbox/.bashrc
'
# Start the daemon manually:
nemohermes milimo-hermes exec -- nohup /opt/hermes/scripts/gateway-daemon.sh >/dev/null 2>&1 &
```

#### Nous Portal 403 (Sandbox Blocks portal.nousresearch.com)
`hermes setup --portal` fails with HTTP 403 because `portal.nousresearch.com:443` is not in the sandbox network policy. The OpenShell proxy at `10.200.0.1:3128` blocks unlisted hosts.

**Fix** (baked in `install-hermes.sh`): Post-onboarding step runs `nemohermes milimo-hermes policy-add --from-dir .../presets/ --yes`, which loads the `nous-portal` preset. The preset file is at `milimo-blueprint/policies/presets/nous-portal.yaml`.

**Root cause (v7 fix)**: The preset and `milimo-mcp.yaml` both used `access: full` (L4 tunnel) but were missing `tls: skip`. Without `tls: skip`, the proxy attempts to terminate TLS at L7 instead of passing raw bytes through — the CONNECT tunnel is rejected with 403. `tls: skip` tells the proxy to pass encrypted bytes unmodified, which is required for OAuth flows and the `hermes` CLI binary's raw TLS connections.

**Correct OpenShell policy preset format** (`nous-portal.yaml`):
```yaml
preset:
  name: nous-portal
  description: "Nous Portal OAuth login, inference API, and managed Tool Gateway setup"

network_policies:
  nous-portal:
    name: nous-portal
    endpoints:
      - host: portal.nousresearch.com
        port: 443
        access: full
        tls: skip          # REQUIRED — pass raw TLS through L4 tunnel
      - host: inference-api.nousresearch.com
        port: 443
        access: full
        tls: skip          # REQUIRED — chat completions after portal login
    binaries:
      - { path: /usr/local/bin/hermes }
      - { path: /opt/hermes/.venv/bin/python }
```

**Correct `milimo-mcp.yaml` entries** (base policy, loaded at build time):
```yaml
# Nous Portal - OAuth login and Tool Gateway (hermes setup --portal)
# Uses access: full (L4 tunnel) because the hermes CLI binary makes raw
# TLS connections that the L7 proxy cannot terminate or inspect.
# tls: skip is required so the proxy passes encrypted bytes through
# unmodified — OAuth redirects and inference API calls require E2E TLS.
- host: "portal.nousresearch.com"
  port: 443
  access: full
  tls: skip
  binaries:
    - "/usr/local/bin/hermes"
    - "/opt/hermes/.venv/bin/python"

# Nous Inference API - chat completions after portal login
- host: "inference-api.nousresearch.com"
  port: 443
  access: full
  tls: skip
  binaries:
    - "/usr/local/bin/hermes"
    - "/opt/hermes/.venv/bin/python"
```

Key rules:
- `preset:` wrapper at top level (not raw `name:`/`endpoints:`)
- Use `access: full` + `tls: skip` for raw TCP/HTTPS tunnels (NOT `protocol: https`)
- Valid protocols: `rest`, `websocket`, `graphql`, `sql` (not `https`)
- Endpoint field `methods` is not valid — use `access` or `rules` instead
- `--from-file <path>` uses the file path as the preset label, not the `preset.name` from YAML
- `--from-dir <dir>` loads all YAML files in the directory as presets (each must have valid `preset.name`)
- Built-in presets (brew, github, telegram, etc.) are compiled into the nemohermes binary, not file-based

#### `--fresh` Does Not Recreate the Sandbox Container
`nemohermes onboard --fresh` only clears saved state (config, credentials) but does NOT destroy and recreate the sandbox container. The old container's restored policy files (from backup) override any policy changes in the new Docker image.

**Fix**: Always pass both `--fresh` AND `--recreate-sandbox`:
```bash
nemohermes onboard --name milimo-hermes --from ./Dockerfile --fresh --recreate-sandbox
```

Even with `--recreate-sandbox`, nemohermes restores policy from backup. The reliable approach is to apply presets at runtime via `policy-add --from-dir`.

#### `build_onboard_command()` Was Dead Code in `install-hermes.sh`
The `build_onboard_command()` function defined the correct onboard flags with `--fresh`, but `main()` was constructing the command inline without calling it, so `--fresh` was never passed in non-interactive mode. Same for `--recreate-sandbox`.

**Fix**: `main()` now calls `build_onboard_command()` and passes its output to `eval`. Both flags are now included in non-interactive mode.

#### `sandbox_dir` Unbound Variable in `install-hermes.sh`
`prepare_build_context()` declared `sandbox_dir` as `local` (line 377). Bash `local` variables are function-scoped, so `main()` could not see `sandbox_dir` at line 581 when applying policy presets post-onboarding.

**Error**: `./install-hermes.sh: line 581: sandbox_dir: unbound variable`

**Fix**: Removed `local` keyword from line 377 so `sandbox_dir` is in `main()`'s scope. Same issue existed in `build_docker_image()` at line 416 but that function uses its own copy — only the `main()` reference needed fixing.

#### Two Copies of `milimo-mcp.yaml` Must Stay in Sync
There are two copies of the policy file:
- `milimo-blueprint/policies/milimo-mcp.yaml` (repo root — authoritative)
- `milimo-hermes-sandbox/milimo-blueprint/policies/milimo-mcp.yaml` (build context copy)

`prepare_build_context()` in `install-hermes.sh` copies from repo root into the build context, so the sandbox copy is overwritten at build time. However, both copies should be kept in sync in git to avoid confusion.

#### `ARG NEMOCLAW_MESSAGING_PLAN_B64` Is Required for Onboarding
NemoClaw's setup manager patches the staged Dockerfile during onboarding to inject messaging channel config. It expects:
```dockerfile
ARG NEMOCLAW_MESSAGING_PLAN_B64=
ENV NEMOCLAW_MESSAGING_PLAN_B64=${NEMOCLAW_MESSAGING_PLAN_B64}
```
Without this declaration, onboarding fails with: `Error: Dockerfile is missing ARG NEMOCLAW_MESSAGING_PLAN_B64; cannot apply messaging plan.`

#### Dockerfile Requires `ARG NEMOCLAW_MESSAGING_PLAN_B64` for Onboarding
NemoClaw's setup manager patches the staged Dockerfile during onboarding to inject messaging channel config. It expects:
```dockerfile
ARG NEMOCLAW_MESSAGING_PLAN_B64=
ENV NEMOCLAW_MESSAGING_PLAN_B64=${NEMOCLAW_MESSAGING_PLAN_B64}
```
Without this declaration, onboarding fails with: `Error: Dockerfile is missing ARG NEMOCLAW_MESSAGING_PLAN_B64; cannot apply messaging plan.`

The `milimo-hermes-sandbox/install-hermes.sh` `build_docker_image()` function passes this through automatically (defaults to empty if no messaging plan is configured).

#### Post-Rebuild Fixes: link-cli, PyYAML, orchestrator import, test-mode default
Live rebuild investigation of `milimo-hermes` sandbox identified 5 root-cause fixes baked into `milimo-hermes-sandbox/Dockerfile`:

| Symptom | Root cause | Fix |
|---|---|---|
| `link-cli: command not found` | Hermes skill only installs `SKILL.md` wrapper; actual Node binary needs `npm install -g` | `RUN npm install -g @stripe/link-cli@0.8.2` in Dockerfile |
| `ModuleNotFoundError: No module named 'yaml'` | System Python lacks PyYAML; `milimo_core.bridge_cli` imports `yaml` at top-level | `RUN /usr/bin/python3 -m pip install --break-system-packages pyyaml` for system Python |
| `No module named 'orchestrator'` | `bridge_cli.py` imports `orchestrator.milimo_paths`; `/opt/nemoclaw-blueprint` not on sys.path | `RUN /usr/bin/python3 -c "import site; ..."` writes `/opt/nemoclaw-blueprint.pth` to system site-packages |
| `MILIMO_SPEND_TEST_MODE` unset | Dockerfile ARG defaulted to `false`; install script didn't read user's `.env` | `ARG MILIMO_SPEND_TEST_MODE=true` (was `false`); `install-hermes.sh` exports from env |
| `hermes skills install` hangs in CI | Interactive TTY prompt for skill confirmation | Added `--yes` flag: `hermes skills install --yes official/payments/stripe-link-cli` |

**Verification** (inside rebuilt container):
- `link-cli --version` → `0.8.2`
- `python3 -c "import milimo_core"` → OK
- `python3 -c "from milimo_core.bridge_cli import handle_collect_health"` → OK
- `python3 -c "from milimo_core.finance.spend_handler import SpendApprovalHandler"` → OK
- `.env` contains `MILIMO_SPEND_TEST_MODE=true` and `MILIMO_DAILY_SPEND_CAP_CENTS=10000`

#### Two-Container Conflict: openshell + milimo-hermes
`nemohermes onboard` creates its own plain Hermes sandbox (`openshell` container) as a side effect of the Hermes profile onboarding flow. Running `install-hermes.sh` afterwards creates a second `milimo-hermes` container. Both containers may attempt to bind ports, causing bind-failures.

**How to avoid**:
1. If a plain Hermes sandbox was created accidentally, destroy it first:
   ```bash
   nemohermes openshell destroy   # or: nemohermes my-assistant destroy
   ```
2. Then run `install-hermes.sh` (or `nemohermes onboard`) to create only `milimo-hermes`.

**Port forwarding requirements** (host → sandbox):
| Port | Purpose |
|------|---------|
| `18789` | NemoClaw internal gateway/proxy (mapped automatically by `nemohermes`) |
| `18790` | Hermes web dashboard (mapped automatically by `nemohermes`) |
| `8642` | OpenAI-compatible API (mapped automatically by `nemohermes`) |

The `nemohermes` CLI handles port mapping automatically; no manual `-p` flags are needed when using `nemohermes onboard --from`.

#### `NEMOCLAW_RECREATE_WITHOUT_BACKUP=1` Required for Clean Rebuilds
When rebuilding the sandbox image, nemohermes attempts to backup sandbox state before destroying the container. If a shields-up seal is active on sandbox files, the backup fails and the build aborts.

**Workaround**: Set the env var before rebuilding:
```bash
NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 nemohermes milimo-hermes rebuild
```

**Root cause**: The `nemohermes` backup binary cannot read files protected by the shields-up seal. This is an upstream issue in `nemohermes`; the workaround skips backup entirely.

#### `pull_claw_files.sh` Is OpenClaw-Only
The sync script `scripts/pull_claw_files.sh` expects container names matching `openshell-my-assistant` and paths under `/sandbox/.openclaw/milimo/claws/<role>/`. Neither convention exists on the Hermes profile. The script should not be used with Hermes sandboxes.

### Dockerfile (`milimo-hermes-sandbox/Dockerfile`)
- Base: `ghcr.io/nvidia/nemoclaw/hermes-sandbox-base@sha256:8dad3b989a9ed1e601743310b97be21be5f59f89f7913a47d04f3ec3c40b8ce6` (NVIDIA public base image, pre-bakes Hermes from GitHub releases)
- COPY milimo-core (including `milimo_core.build` subpackage), plugin, warroom HTML, blueprint
- Installs milimo-core and plugin into Hermes venv via `uv pip`
- Installs `gh` CLI (GitHub's apt repository)
- Generates Hermes `config.yaml` and `.env` at build time via `generate-config.ts`
- Installs plugin to standard Hermes location `/sandbox/.hermes/plugins/milimo-hermes`
- Sets up blueprint at `/sandbox/.nemoclaw/blueprints/0.1.0/`
- Bakes `MILIMO_PROFILE=hermes`, `MILIMO_PLUGIN_DIR=/sandbox/.hermes/plugins/milimo-hermes`
- Preserves NemoClaw Hermes plugin at `/sandbox/.hermes/plugins/nemoclaw`
- Adds `.bashrc`/`.profile` hooks to launch `gateway-daemon.sh` at sandbox login (primary mechanism; SysV init fallback at `/etc/init.d/hermes-gateway` with rcS.d symlink also provided)
- `gateway-daemon.sh` supervises both the Hermes gateway and a socat forwarder (`0.0.0.0:8642 → 127.0.0.1:18642`) for the health probe port
- `ENV NEMOCLAW_SANDBOX_NAME=milimo-hermes`
- `ENV NEMOCLAW_POLICY_PRESETS=restricted,github`
- **Post-rebuild Dockerfile additions** (2026-07-04):
  - `ARG NEMOCLAW_MESSAGING_PLAN_B64=` + `ENV NEMOCLAW_MESSAGING_PLAN_B64=...` — required for nemohermes onboarding patch
  - `ARG MILIMO_SPEND_TEST_MODE=true` — default to demo spend flow (was `false`)
  - `ARG MILIMO_DAILY_SPEND_CAP_CENTS=10000` — daily spend cap in cents
  - `ARG MILIMO_OPERATOR=` — operator name baked at build time
  - `RUN npm install -g @stripe/link-cli@0.8.2` — `link-cli` binary available in sandbox PATH
  - `RUN /usr/bin/python3 -m pip install --break-system-packages pyyaml` — satisfies `milimo_core.bridge_cli` top-level `import yaml` in system Python
  - `RUN /usr/bin/python3 -c "..."` — writes `/opt/nemoclaw-blueprint.pth` to system site-packages so `orchestrator` is importable from system Python subprocesses
  - `RUN hermes skills install --yes official/payments/stripe-link-cli` — non-interactive skill install for CI/Docker builds

### Install Script (`milimo-hermes-sandbox/install-hermes.sh`)
- Interactive + non-interactive modes
- `--auth-mode [api_key|nous_oauth]` (default: api_key)
  - `api_key` — Standard NVIDIA inference (default)
  - `nous_oauth` — Nous Portal OAuth; enables managed tool gateways (web search, browser automation, image generation, audio processing, managed code execution)
- Deprecated: `--nous-oauth` flag (use `--auth-mode nous_oauth`)
- Env var: `NEMOCLAW_AUTH_MODE` (preferred) or `NEMOCLAW_NOUS_OAUTH` (deprecated)
- Headless detection → prompts for `CHAT_UI_URL`
- `SLACK_ALLOWED_CHANNELS` baked at build time
- Probes Python 3.10–13 for Model Router (opt-in)
- Docker build uses `$sandbox_dir` as context (was `.` — fixed to resolve COPY path mismatches inside the sandbox build directory)
- `build_onboard_command()` now called by `main()` (was dead code — `main()` used inline command without `--fresh`/`--recreate-sandbox`)
- Post-onboarding: applies network policy presets from `milimo-blueprint/policies/presets/` via `nemohermes policy-add --from-dir`, including `nous-portal`
- Model default: `stepfun-ai/step-3.7-flash` (set via `NEMOCLAW_MODEL` env var, passed as Docker build arg)
- **Post-rebuild additions** (2026-07-04):
  - Passes `MILIMO_SPEND_TEST_MODE`, `MILIMO_DAILY_SPEND_CAP_CENTS`, `MILIMO_OPERATOR` as Docker build args
  - Exports defaults for `generate-config.ts` if not set in environment

---

## Onboarding

```bash
# Interactive
./milimo-hermes-sandbox/install-hermes.sh

# Non-interactive (CI)
export NVIDIA_API_KEY=...
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export NEMOCLAW_SANDBOX_NAME=milimo-hermes
./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

**Result**:
- Dashboard: `http://127.0.0.1:18790/`
- OpenAI-compatible API: `http://127.0.0.1:8642/v1`
- War Room: `/opt/hermes/warroom/warroom.html` inside sandbox
- Headless: SSH tunnel `ssh -L 18790:127.0.0.1:18790 user@host` or set `CHAT_UI_URL=http://localhost:18790`

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| A0 | `DelegationAdapter` ABC + types | ✅ v0.1.0 |
| A1 | Core tools (status, warroom, approve, veto, delegate) | ✅ v0.1.0 |
| A2 | `HermesCredentialAdapter` | ✅ v0.1.0 |
| A3 | `HermesDelegateAdapter` | ✅ v0.1.0 |
| A+ | Scheduling protocol + HermesCronScheduler | ✅ v0.1.0 |
| A+ | War Room HTML (htmx) | ✅ v0.1.0 |
| A+ | `milimo-compatibility.json` | ✅ v0.1.0 |
| A+ | MockDelegationAdapter | ✅ v0.1.0 |
| B1 | EvolutionScheduler + cron jobs | ✅ Done |
| B2 | War Room tool integration | ✅ Done |
| C1 | SSRF validation | ✅ Done |
| C2 | Slack/Telegram push | ✅ Done |
| C3 | Install script auth flag | ✅ Done |
| D1 | CI/CD test pyramid + integration tests | ✅ **Complete** (58 tests pass) |
| D2 | `milimo-core` coverage gate (80%) | ✅ **Complete** (all modules ≥80%) |
| D3 | `uv` workspace | ✅ Done |
| E1 | ADRs | ✅ Done |
| E2 | README decision tree | ✅ Done |
| E3 | CLAUDE.md terminology | ✅ Done |
| E4 | GitHub Actions CI + v0.2.0 tag | ✅ **Complete** |
| E5 | Fix Hermes base image (public NVIDIA GHCR) + CI smoke test | ✅ **Complete** (2026-06-29) |
| E6 | Fix API_SERVER_KEY + SOUL.md context + TypeScript build errors | ✅ **Complete** (2026-06-30) |
| E7 | Gateway daemon sandbox resilience: socat forwarder, `.bashrc`/`.profile` hooks for auto-start, CI build context path fixes | ✅ **Complete** (2026-06-30) |
| E8 | Model change (`stepfun-ai/step-3.7-flash`), Nous Portal network policy (`nous-portal` preset via `--from-dir`), `--recreate-sandbox` flag, `build_onboard_command()` fix, presets persisted to repo | ✅ **Complete** (2026-06-30) |

---

## Related Pages

- [[implementation-plan]] — Complete Phase A–E plan with checklists
- [[delegation-adapter]] — Profile-agnostic delegation contract
- [[hermes-delegate-adapter]] — Hermes native `delegate_task` implementation
- [[hermes-credential-adapter]] — GitHub `gh auth token` path
- [[warroom-hermes]] — Standalone HTML + htmx implementation
- [[adrs]] — All architectural decision records
- [[milimo-core-protocols]] — Extension points for third profiles

---

## Day-to-Day Operations

### Start a Chat Session
```bash
nemohermes milimo-hermes connect
# Inside sandbox, type: hermes
```

### Check Gateway Status
```bash
nemohermes milimo-hermes status
nemohermes milimo-hermes exec -- hermes gateway status
nemohermes milimo-hermes exec -- sudo /etc/init.d/hermes-gateway status
```

### View War Room
```bash
# Serve the warroom HTML via HTTP:
nemohermes milimo-hermes exec -- python3 -m http.server 8080 --directory /opt/hermes/warroom
# Open http://localhost:8080/warroom.html
```

### Change Model / Inference Provider
```bash
# Update model on the running sandbox (no rebuild needed):
nemohermes inference set --model stepfun-ai/step-3.7-flash --provider nvidia-nim --sandbox milimo-hermes
```
Note: `openshell inference set` is not available inside Hermes sandboxes. Always use `nemohermes inference set` from the host.

### Use Nous Portal Models (Managed Tool Gateways)

`hermes setup --portal` connects the sandbox to Nous Portal for 300+ models and managed tool gateways (web search, browser automation, image generation, TTS, audio processing, managed code execution):

```bash
# Run inside the sandbox with TTY for browser OAuth flow:
nemohermes milimo-hermes exec --tty -- hermes setup --portal
```

This opens an OAuth login flow. After success, the inference provider switches to Nous (use `nemohermes inference set` to switch back).

**Prerequisite**: The sandbox network policy must allow `portal.nousresearch.com:443`. The `nous-portal` preset (at `milimo-blueprint/policies/presets/nous-portal.yaml`) provides the rule. The install script applies it automatically post-onboarding. To apply manually:

```bash
nemohermes milimo-hermes policy-add --from-dir milimo-blueprint/policies/presets/ --yes
```

**Policy restore caveat**: `--fresh` clears saved state but does NOT recreate the sandbox container — the old policy is restored from backup. Always use `--fresh --recreate-sandbox` together to get a clean policy from the Docker image. Even then, nemohermes may restore saved policy from backup; applying the `nous-portal` preset at runtime is the reliable workaround.

### Run Ad-Hoc Commands
```bash
nemohermes milimo-hermes exec -- hermes skills list
nemohermes milimo-hermes logs -n 50
nemohermes milimo-hermes exec -- cat /tmp/gateway.log
```

---

## See Also

- `milimo-claw-docs/reports/milimoclaw-hermes-integration-report.md` — Full gap analysis
- `milimo-core/CHANGELOG.md` — v0.1.0 scope and deferred items
- `milimo-hermes-plugin/` — Plugin source code
- `milimo-hermes-sandbox/` — Dockerfile and install script
- `docs/adr/002-warroom-hermes.md` — War Room Hermes ADR
- `milimo-claw-docs/reports/hermes-integration-investigation-2026-06-29.md` — Deep dive investigation of Hermes integration
