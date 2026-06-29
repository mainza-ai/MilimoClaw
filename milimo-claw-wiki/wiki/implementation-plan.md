# MilimoClaw × NemoClaw Hermes — Dual-Track Implementation Plan

**Summary**: Complete implementation plan for dual-track Hermes profile integration, preserving OpenClaw while adding web dashboard + OpenAI-compatible API via shared `milimo-core` library.

**Sources**:
- `milimo-claw-docs/reports/milimoclaw-hermes-integration-report.md`
- `docs/adr/001-subagent-isolation.md` through `005-delegation-asymmetry.md`
- `milimo-core/CHANGELOG.md`
- Phase A completion commit (v0.1.0)

**Last updated**: 2026-06-29

**Tags**: #architecture #implementation #hermes #dual-track #plan

---

## Overview

MilimoClaw runs six autonomous claws (Build, Content, Ops, Analytics, Finance, Assistant) across two NemoClaw profiles:

| Profile | Interface | Inference | Status |
|---------|-----------|-----------|--------|
| **OpenClaw** | TUI + Bridge Server | NVIDIA NIM / Local | ✅ Production |
| **Hermes** | Web Dashboard (port 18789) + OpenAI-compatible API (port 8642) | Native `delegate_task` + `cronjob` | 🚧 Phase A complete, Phase B in progress |

**Core principle**: OpenClaw stays unchanged. Hermes is additive via shared `milimo-core` library.

---

## Phase A: Critical Blockers (COMPLETE — v0.1.0)

### A0. Delegation Protocol — `milimo-core/protocols/delegation.py`
**Written first** — defines the shared contract for claw parallelism.

| Type | Purpose |
|------|---------|
| `ClawTask` | Profile-agnostic task descriptor (claw, goal, context, priority) |
| `ClawResult` | Profile-agnostic result (claw, output, success, error) |
| `DelegationAdapter` | ABC with `delegate(tasks)` and `delegate_single(task)` |

**Business logic in ABC** (profile-agnostic):
- `CLAW_TOOLSETS` — per-claw toolset mappings
- `CLAW_CONTEXTS` — per-claw system prompt context strings

### A1. Core Tool Registration — `milimo-hermes-plugin/tools.py`
| Tool | Purpose | Schema |
|------|---------|--------|
| `milimo_status` | All 6 claws status | `detailed?: boolean` |
| `milimo_warroom` | HOLD queue, cost guard, approve/veto | `action: enum(status|hold_queue|approve|veto|cost_guard)` |
| `milimo_approve` | Approve HOLD item, optionally delegate | `item_id, reason?, delegate_to_claw?, delegation_goal?` |
| `milimo_veto` | Veto/reject HOLD item | `item_id, reason` |
| `delegate_task` | Native Hermes delegation wrapper | `tasks: ClawTask[]` |

All schemas use shared `ClawTask`/`ClawResult` types from A0.

### A2. Hermes Credential Adapter — `milimo-core/hermes_credential_adapter.py`
| Service | Resolution Method |
|---------|-------------------|
| GitHub | `gh auth token` (not OpenShell gateway) |
| Stripe | OpenShell L7 proxy placeholder: `STRIPE_API_KEY` |
| Vercel | OpenShell L7 proxy placeholder: `VERCEL_TOKEN` |
| Sentry | OpenShell L7 proxy placeholder: `SENTRY_AUTH_TOKEN` |
| NVIDIA | OpenShell L7 proxy placeholder: `NVIDIA_API_KEY` |

**Key finding from docs**: NemoClaw never persists `GITHUB_TOKEN`; it calls `gh auth token` which reads from GitHub CLI's credential store (macOS Keychain, Windows Credential Manager, Linux Secret Service, `~/.config/gh/`).

### A3. Hermes Delegate Adapter — `milimo-hermes-plugin/delegation.py`
- Implements `DelegationAdapter` using native `delegate_task`
- Converts `ClawTask[]` → Hermes delegation format with per-claw toolsets/context
- `DELEGATION_MAX_CONCURRENT_CHILDREN=6` (one per claw)

### Bonus: Scheduling Protocol
- `milimo-core/protocols/scheduling.py` — `SchedulerInterface` ABC + `ScheduledJob`
- `milimo-hermes-plugin/hermes_scheduler.py` — `HermesCronScheduler` using native `cronjob`

### Bonus: War Room HTML (htmx)
- `milimo-hermes-plugin/warroom/warroom.html` — standalone, served at `/warroom`
- Auto-refreshes via `hx-trigger="every 5s"`, no build step, CDN htmx

### Bonus: Configuration
- `milimo-blueprint/milimo-compatibility.json` — delegation, cron, warroom, cost_guard, auth config

### Bonus: Mock Infrastructure
- `milimo-core/tests/mocks/mock_delegation.py` — `MockDelegationAdapter` for cross-profile unit testing

---

## Phase B: Core Functionality (COMPLETE)

### B1. Evolution Cycle Cron + `EvolutionScheduler` ✅ COMPLETE
| Component | Location | Description |
|-----------|----------|-------------|
| `EvolutionScheduler` | `milimo-core` | Shared evolution logic using `SchedulerInterface` |
| `HermesCronScheduler` | `milimo-hermes-plugin` | Native `cronjob` implementation (durable, survives interrupts) |

**Jobs registered**:
| Job | Schedule | Description |
|-----|----------|-------------|
| `evolution_cycle` | `0 2 * * 0` (Sunday 2AM) | Weekly 5-stage evolution pipeline |
| `tool_backtest` | `0 */6 * * *` (every 6h) | Backtest new tools in sandbox |
| `hold_queue_review` | `0 */4 * * *` (every 4h) | Review HOLD queue items |

**Key distinction from docs**: `cronjob` (durable, managed by Hermes runtime) ≠ `delegate_task` (fire-and-forget). Evolution cycle MUST use `cronjob` for durability.

**Implementation files**:
- `milimo-core/src/milimo_core/evolution_scheduler.py` — Shared `EvolutionScheduler` implementing `SchedulerInterface`
- `milimo-hermes-plugin/milimo_hermes_plugin/hermes_scheduler.py` — Updated `HermesCronScheduler` using EvolutionScheduler
- Synchronous handlers for Hermes cronjob:
  - `run_evolution_cycle_handler()`
  - `run_tool_backtest_handler()`
  - `run_hold_queue_review_handler()`

### B2. War Room Tool Integration ✅ COMPLETE
- Connect `milimo_warroom` tool to actual claw status APIs (`claw_launcher.status()`)
- HOLD queue persistence and polling via `OpsApprovalHandler` (from `milimo-core`)
- Cost guard token tracking via `CostGuard` (from `milimo-core`)
- Connect `milimo_approve`/`milimo_veto` to `HermesDelegateAdapter.delegate_single()` for delegation

**Implementation files**:
- `milimo-core/src/milimo_core/ops/approval_handler.py` — `OpsApprovalHandler` for HOLD/REVIEW queue
- `milimo-core/src/milimo_core/cost_guard.py` — `CostGuard` for token tracking
- `milimo-hermes-plugin/milimo_hermes_plugin/tools.py` — Updated tool handlers

### B3. `milimo-compatibility.json` (Already created)
- Delegation config: `max_concurrent_children=6`, per-claw model overrides
- Cron job definitions
- War Room endpoint config
- Cost guard: 50K daily tokens, 80% alert threshold
- Auth: API key default, Nous OAuth opt-in
- Connect `milimo_warroom` tool to actual claw status APIs
- HOLD queue persistence and polling
- Cost guard token tracking (50K daily limit)
- Approve/veto delegation to claws via `HermesDelegateAdapter`

### B3. `milimo-compatibility.json` (Already created)
- Delegation config: `max_concurrent_children=6`, per-claw model overrides
- Cron job definitions
- War Room endpoint config
- Cost guard: 50K daily tokens, 80% alert threshold
- Auth: API key default, Nous OAuth opt-in

---

## Phase C: Operational Excellence (PLANNED)

### C1. SSRF Validation for Egress Hosts ✅ COMPLETE
- Validate all hosts in `milimo-blueprint/policies/milimo-mcp.yaml` against NemoClaw's `ssrf.ts` (RFC 1918, RFC 3927, RFC 4193, metadata services, localhost)
- Automated check in CI pipeline via `python -m milimo_core.ssrf_validator --policy milimo-blueprint/policies/milimo-mcp.yaml --allow-local-nim`

**Implementation files**:
- `milimo-core/src/milimo_core/ssrf_validator.py` — SSRFValidator with CLI
  - Validates against private networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16)
  - Blocks metadata service (169.254.169.254)
  - Blocks RFC 2544 benchmark range (198.18.0.0/15)
  - Validates DNS resolution to public IPs only
  - Handles optional endpoints (ncp.api.nvidia.com, nim-service.local)
  - CLI with `--allow-local-nim`, `--allow-private`, `--skip-dns` flags
  - JSON output for CI integration

### C2. Slack/Telegram Push in War Room ✅ COMPLETE
- `SLACK_ALLOWED_CHANNELS` baked at image build time (cannot change without rebuild)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ALLOWED_IDS` runtime
- HOLD alerts, Analytics weekly summaries pushed to channels
- Cost guard threshold notifications (warning at 60%, alert at 80%, critical at 95%+)

**Implementation files**:
- `milimo-core/src/milimo_core/notifications.py` — `WarRoomNotifier`, `SlackNotifier`, `TelegramNotifier`
  - `WarRoomNotifier.notify_hold_alert()` — HOLD queue alerts with urgency
  - `WarRoomNotifier.notify_cost_guard()` — Token usage warnings/alerts
  - `WarRoomNotifier.notify_analytics_summary()` — Weekly analytics reports
  - `WarRoomNotifier.notify_generic()` — Custom notifications
- Slack: supports incoming webhook and Bot API (`chat.postMessage`)
- Telegram: Bot API with markdown formatting
- Config via environment variables: `SLACK_WEBHOOK_URL`, `SLACK_BOT_TOKEN`, `SLACK_ALLOWED_CHANNELS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_IDS`
- Plugin integration in `milimo-hermes-plugin/milimo_hermes_plugin/__init__.py`

### C3. Install Script Polish
- `--auth-mode [api_key|nous_oauth]` flag (default: `api_key`)
- Document OAuth as "Step 2" for managed tool gateways (web search, browser automation, image gen, audio, managed code execution)
- Headless detection + `CHAT_UI_URL` prompt

---

## Phase D: CI/CD & Testing (COMPLETE)

### D1. Hermes Test Pyramid ✅ COMPLETE
| Layer | Tests | Tools |
|-------|-------|-------|
| Unit | Plugin registration, tool schemas, credential adapter, `MockDelegationAdapter` | pytest, pytest-mock |
| Integration | Mock Hermes gateway, `HermesDelegateAdapter` invocation, cron scheduler | pytest-mock, nemoclaw CLI |
| Smoke | `NEMOCLAW_POLICY_TIER=restricted` onboarding (CI pending) | GitHub Actions |

**Results**: 58 integration tests pass (18 delegation, 20 scheduler, 20 tools)

**CI Environment**:
```yaml
env:
  NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE: 1
  NEMOCLAW_POLICY_TIER: restricted
  NEMOCLAW_NON_INTERACTIVE: 1
  NEMOCLAW_SANDBOX_NAME: milimo-hermes-ci
```

### D2. `milimo-core` Coverage Gate ✅ COMPLETE
```bash
pytest --cov=milimo_core --cov-fail-under=80
```

**All new modules achieve ≥80% coverage**:
| Module | Coverage |
|--------|----------|
| `cost_guard` | 98.90% |
| `evolution_scheduler` | 88.89% |
| `hermes_credential_adapter` | 100% |
| `milimo_paths` | 83.08% |
| `ssrf_validator` | 90.85% |
| `protocols/*` | 100% |
| `approval_handler` | 99.15% |
| `notifications` | 96.26% |

### D3. `uv` Workspace (Already in root `pyproject.toml`)
```toml
[tool.uv.workspace]
members = ["milimo-core", "milimo-blueprint", "milimo-hermes-plugin"]
```

---

## Phase E: Documentation & UX (PLANNED)

### E1. ADRs (Already created)
| ADR | Title | Key Decision |
|-----|-------|--------------|
| 001 | Subagent Isolation Model | Use native primitives; OpenClaw `maxSpawnDepth=2` = Hermes advantage |
| 002 | War Room for Hermes | Standalone HTML + htmx, not `/opt/hermes/ui-tui` bundle |
| 003 | Milimo-Core Packaging | Local editable → PyPI post-v0.2.0 |
| 004 | Sandbox Naming | Default `milimo-hermes` (not `hermes`) to avoid collision |
| 005 | Delegation Asymmetry | `DelegationAdapter` = Hermes contract; OpenClaw `mesh.py` = equivalent but different model |

### E2. README Decision Tree (To update)
```markdown
Do you want web search / browser automation inside Hermes?
  → Yes: Use Nous Portal OAuth at onboarding
  → No: API-key mode is sufficient

Are you on a headless remote host?
  → Yes: Set CHAT_UI_URL before onboarding, or use SSH port forwarding
  → No (local machine): Dashboard at http://127.0.0.1:18789/

Do you want a web dashboard UI?
  → Yes: nemohermes (Hermes profile)
  → No: nemoclaw (OpenClaw profile, default)
```

### E3. `CLAUDE.md` Updates
- Document "claw handlers" terminology (not "skills")
- Add `delegate_task` pattern for Hermes
- Update ground truth for dual-profile architecture

---

## Architecture Decision Records (Reference)

| ADR | File | Summary |
|-----|------|---------|
| 001 | `docs/adr/001-subagent-isolation.md` | Native primitives; OpenClaw depth constraint = Hermes advantage |
| 002 | `docs/adr/002-warroom-hermes.md` | Standalone HTML via htmx, not internal dashboard bundle |
| 003 | `docs/adr/003-milimo-core-packaging.md` | Local editable install; PyPI post-v0.2.0 |
| 004 | `docs/adr/004-sandbox-naming.md` | Default `milimo-hermes` to avoid collision with `hermes` |
| 005 | `docs/adr/005-delegation-asymmetry.md` | `DelegationAdapter` = Hermes contract; OpenClaw `mesh.py` left as-is |

---

## File Structure Summary

```
milimo-core/
├── src/milimo_core/
│   ├── protocols/
│   │   ├── delegation.py      ← DelegationAdapter ABC, ClawTask, ClawResult
│   │   └── scheduling.py      ← SchedulerInterface ABC, ScheduledJob
│   ├── hermes_credential_adapter.py
│   └── tests/mocks/mock_delegation.py
│
milimo-hermes-plugin/
├── milimo_hermes_plugin/
│   ├── delegation.py          ← HermesDelegateAdapter
│   ├── tools.py               ← Core tools (milimo_*, delegate_task)
│   ├── hermes_scheduler.py    ← HermesCronScheduler
│   └── skills/                ← 6 claw handlers + milimo_core_primitives
├── warroom/warroom.html       ← htmx standalone War Room
├── plugin.yaml                ← Hermes plugin manifest
└── requirements.txt
│
milimo-blueprint/
├── milimo-compatibility.json  ← Delegation/cron/warroom/cost_guard/auth
├── policies/milimo-mcp.yaml   ← Binary-scoped egress (hostname + /opt/hermes/.venv/bin/python)
├── router/pool-config.yaml    ← Model Router pool (deferred)
└── blueprint.yaml             ← Dual-track agent_profiles
│
milimo-hermes-sandbox/
├── Dockerfile                 ← COPY plugin, milimo-core, warroom; preserves nemoclaw plugin
└── install-hermes.sh          ← Interactive/non-interactive onboarding
│
docs/adr/
├── 001-subagent-isolation.md
├── 002-warroom-hermes.md
├── 003-milimo-core-packaging.md
├── 004-sandbox-naming.md
└── 005-delegation-asymmetry.md
```

---

## Verification Checklist

| Phase | Item | Status |
|-------|------|--------|
| A0 | `DelegationAdapter` ABC + types | ✅ |
| A1 | Core tools (status, warroom, approve, veto, delegate) | ✅ |
| A2 | `HermesCredentialAdapter` (gh auth token for GitHub) | ✅ |
| A3 | `HermesDelegateAdapter` (native delegate_task) | ✅ |
| A+ | Scheduling protocol + HermesCronScheduler | ✅ |
| A+ | War Room HTML (htmx) | ✅ |
| A+ | `milimo-compatibility.json` | ✅ |
| A+ | MockDelegationAdapter | ✅ |
| A+ | ADRs 001-005 | ✅ |
| A+ | CHANGELOG.md for v0.1.0 | ✅ |
| A+ | v0.1.0 tagged | ✅ |
| B1 | EvolutionScheduler + HermesCronScheduler | ✅ |
| B2 | War Room tool integration | ✅ |
| B3 | Config already done | ✅ |
| C1 | SSRF validation | ✅ |
| C2 | Slack/Telegram push | ✅ |
| C3 | Install script auth flag | ✅ |
| D1 | Test pyramid + integration tests | ✅ **Complete** (58 tests) |
| D2 | Coverage gate (80% on milimo-core) | ✅ **Complete** (all modules ≥80%) |
| D3 | uv workspace | ✅ Done |
| E1 | ADRs | ✅ Done |
| E2 | README decision tree | ✅ Done |
| E3 | CLAUDE.md terminology | ✅ Done |

---

## Next Steps (Immediate)

1. **E4**: ✅ **v0.2.0 tagged**
2. **GitHub Actions CI**: ✅ **Hermes CI workflow added** (`.github/workflows/hermes-ci.yml`)
3. **PyPI publish**: ⏸️ **Deferred** — `milimo-core` package publish post-v0.2.0 (manual step when ready)

---

## Phase E5: Hermes Base Image Fix (2026-06-29) — COMPLETE

### Problem
The Hermes CI smoke test was failing because `milimo-hermes-sandbox/Dockerfile` used `ghcr.io/nousresearch/hermes-agent:latest` as the base image, which is a **private image** returning 403 Forbidden.

### Root Cause
The original Dockerfile attempted to extend the NousResearch upstream image directly, but this image is not publicly available on GHCR. The correct pattern (used by NemoHermes onboarding) is to extend NVIDIA's public `ghcr.io/nvidia/nemoclaw/hermes-sandbox-base` image, which pre-bakes Hermes from GitHub releases.

### Fix Applied
1. **Updated base image** in `milimo-hermes-sandbox/Dockerfile`:
   - From: `ghcr.io/nousresearch/hermes-agent:latest` (private, 403)
   - To: `ghcr.io/nvidia/nemoclaw/hermes-sandbox-base@sha256:8dad3b989a9ed1e601743310b97be21be5f59f89f7913a47d04f3ec3c40b8ce6` (public)

2. **Rewrote Dockerfile** to follow NemoHermes pattern:
   - Install milimo-core and plugin via `uv pip` (base image provides uv globally)
   - Generate Hermes `config.yaml` and `.env` at build time via `generate-config.ts`
   - Install plugin to standard Hermes location `/sandbox/.hermes/plugins/milimo-hermes`
   - Set up blueprint at `/sandbox/.nemoclaw/blueprints/0.1.0/`
   - Proper permissions and config hash pinning per NemoHermes

3. **Refactored `install-hermes.sh`** to use `nemohermes onboard` correctly with build args

4. **Fixed CI workflow** (`.github/workflows/hermes-ci.yml`):
   - Pulls public NVIDIA base image (no fallback needed)
   - Uses correct build arg `BASE_IMAGE`
   - Smoke test validates correct paths

5. **Added config generation** files:
   - `milimo-hermes-sandbox/generate-config.ts` — adapted from NemoHermes
   - `milimo-hermes-sandbox/config/yaml.ts` — minimal YAML serializer

### Verification
- ✅ CI pipeline passes: `hermes-integration` (55s) + `hermes-smoke` (2m4s)
- ✅ Base image pulls successfully from public GHCR
- ✅ Docker build completes with uv pip installs
- ✅ Smoke test validates:
  - Milimo install stamp at `/opt/hermes/.milimo_install`
  - Plugin at `/sandbox/.hermes/plugins/milimo-hermes`
  - `milimo_core` importable in Hermes venv
  - `milimo_hermes_plugin` importable
  - War Room assets at `/opt/hermes/warroom`

---

## Related Pages

- [[hermes-credential-adapter]] — GitHub `gh auth token` path
- [[delegation-adapter]] — Profile-agnostic delegation contract
- [[hermes-delegate-adapter]] — Hermes native `delegate_task` implementation
- [[milimo-core-protocols]] — Extension points for third profiles
- [[warroom-hermes]] — Standalone HTML + htmx implementation
- [[adrs]] — All architectural decision records

---

## See Also

- `milimo-claw-docs/reports/milimoclaw-hermes-integration-report.md` — Full gap analysis & corrections
- `milimo-core/CHANGELOG.md` — Version history and deferred items
- `docs/adr/` — All 5 architectural decision records
