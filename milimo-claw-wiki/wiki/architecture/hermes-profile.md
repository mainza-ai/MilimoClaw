# Hermes Profile — Dual-Track Integration

**Summary**: Hermes profile architecture for MilimoClaw — web dashboard (port 18789), OpenAI-compatible API (port 8642), native `delegate_task` + `cronjob` parallelism, binary-scoped network policy.

**Sources**:
- `implementation-plan.md`
- `milimo-hermes-plugin/`
- `milimo-blueprint/milimo-compatibility.json`
- `milimo-hermes-sandbox/`
- `docs/adr/001-subagent-isolation.md` through `005-delegation-asymmetry.md`

**Last updated**: 2026-06-27

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

### Network Policy (`milimo-blueprint/policies/milimo-mcp.yaml`)
Binary-scoped egress — each rule specifies:
- Host + port + protocol
- Binary: `/opt/hermes/.venv/bin/python`

Hosts: GitHub, npm, PyPI, Stripe, Vercel, Sentry, Twitter/X, LinkedIn, TikTok, NVIDIA, IP geolocation

### Dockerfile (`milimo-hermes-sandbox/Dockerfile`)
- Base: `ghcr.io/nvidia/nemoclaw/hermes-sandbox-base:latest`
- COPY plugin, milimo-core, warroom HTML
- Preserves NemoClaw Hermes plugin at `/sandbox/.hermes/plugins/nemoclaw`
- `ENV NEMOCLAW_SANDBOX_NAME=milimo-hermes`
- `ENV NEMOCLAW_POLICY_PRESETS=restricted,github`

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
- Dashboard: `http://127.0.0.1:18789/`
- OpenAI-compatible API: `http://127.0.0.1:8642/v1`
- War Room: `http://127.0.0.1:8642/warroom`
- Headless: SSH tunnel `ssh -L 18789:127.0.0.1:18789 user@host` or set `CHAT_UI_URL`

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
| E3 | CLAUDE.md updates | 📋 Planned |

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

## See Also

- `milimo-claw-docs/reports/milimoclaw-hermes-integration-report.md` — Full gap analysis
- `milimo-core/CHANGELOG.md` — v0.1.0 scope and deferred items
- `milimo-hermes-plugin/` — Plugin source code
- `milimo-hermes-sandbox/` — Dockerfile and install script
