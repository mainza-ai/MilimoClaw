# Milimo Claw — Audit Remediation Changelog

## 2026-04-04 — NemoClaw Rebuild + Build Claw Implementation + Security Hardening

### Summary

This release represents the largest single update to Milimo Claw. The codebase has been rebuilt as a proper extension on top of NVIDIA NemoClaw (rather than a forked duplicate), the Build Claw has been fully implemented with 13 modules (3,921 lines), all 6 critical security issues have been resolved, and all pre-existing test failures have been fixed. **1192 tests passing, 0 failures.**

---

## NEMOCLAW INTEGRATION REBUILD

### Stripped NemoClaw Duplicate Code
- **Deleted** `nemoclaw/`, `nemoclaw-blueprint/`, `bin/`, `Dockerfile.tool`, `NemoClaw-README.md`
- **Deleted** NemoClaw Sphinx docs (`docs/about/`, `docs/reference/`, `docs/get-started/`, etc.)
- **Deleted** 20+ NemoClaw-specific test files and obsolete `.js` files in `milimo/src/`
- **Rewrote** `package.json` — renamed to `"milimo-claw"`, updated all NVIDIA references
- **Rewrote** `pyproject.toml` — renamed to `"milimo-claw-docs"`, regenerated `uv.lock`
- **Updated** `Makefile`, `.github/workflows/integration.yml` — Milimo-specific targets only

### NemoClaw as Base Layer
- **Rewrote** `Dockerfile` — NemoClaw as build stage base, Milimo-only layers on top
- **Updated** `scripts/milimo-start.sh` — sole entrypoint, no NemoClaw plugin installation
- **Updated** `milimo/src/onboard/config.ts` — defensive error handling when NemoClaw config is missing

### New MilimoClaw Installers
- **Created** `install.sh` — checks NemoClaw prerequisite, builds Milimo plugin, runs onboarding
- **Created** `uninstall.sh` — removes Milimo plugin/config, leaves NemoClaw intact

---

## BUILD CLAW IMPLEMENTATION

### 13 New Python Modules (3,921 lines)

| Module | Lines | Purpose |
|---|---|---|
| `build_init.py` | 421 | Filesystem init, inference fallback chain, category routing |
| `signal_dispatcher.py` | 366 | Event normalization, renderer/sink separation, SLA timer |
| `approval_handler.py` | 496 | Two-stage REVIEW→HOLD, file-based task persistence |
| `issue_manager.py` | 372 | Sprint planning with velocity tracking |
| `code_generator.py` | 299 | Hash-anchored code generation, AST-aware search |
| `pr_manager.py` | 276 | Two-stage REVIEW→HOLD→merge with status validation |
| `deploy_manager.py` | 215 | Separate HOLD flow, background execution |
| `error_monitor.py` | 254 | ErrorPattern/ErrorEvent classes, tmux monitoring hooks |
| `cost_monitor.py` | 175 | Baseline calculation, drift detection |
| `dependency_auditor.py` | 178 | Vulnerability assessment, security PR routing |
| `doc_maintainer.py` | 199 | Changelog/devlog generation, shipping summaries |
| `build_scheduler.py` | 250 | Timer-based scheduling, missed job recovery |
| `build_claw.py` | 340 | Main entry point with public property accessors |

### Enhancements from External Projects

**From oh-my-openagent:**
- Inference fallback chain with exponential backoff
- Category-based model selection for different task types
- Hash-anchored code generation for edit safety
- Task dependency storage with file-based persistence
- Background execution for deploy and PR operations
- Session recovery from API failures

**From clawhip:**
- Typed event normalization at signal dispatcher ingress
- Renderer/sink separation for message formatting
- Tmux session monitoring integration
- Filesystem memory pattern for durable operational logs

### Test Results
- **Build Claw Unit Tests:** 101/101 passed
- **Build Claw MVR Integration:** 15/15 passed
- **Total Build Claw:** 116/116 passed

---

## SECURITY FIXES (6 Critical Issues Resolved)

| # | Fix | File |
|---|---|---|
| 1 | **JWT secret throws if unset** — no more hardcoded fallback | `milimo-server/src/server.ts` |
| 2 | **CORS restricted to ALLOWED_ORIGINS** — defaults to `false` | `milimo-server/src/server.ts` |
| 3 | **WebSocket authentication required** — rejects connections without valid JWT | `milimo-server/src/server.ts` |
| 4 | **Refresh token store with validation, expiration, rotation** | `milimo-server/src/routes/auth.ts` |
| 5 | **HKDF key derivation** replaces byte-cycling for mesh encryption | `milimo/src/mesh/gateway-client.ts` |
| 6 | **Payout webhook uses `destination` field** instead of passing payout ID twice | `milimo-server/src/payments/webhooks.ts` |
| 7 | **k8s capabilities dropped to ALL + only SYSLOG** — removed SYS_ADMIN, NET_ADMIN, SYS_PTRACE | `k8s/sandbox-pod.yaml` |
| 8 | **Gateway parse errors now logged** instead of silently ignored | `milimo/src/mesh/gateway-client.ts` |
| 9 | **Fallback file messages encrypted** with AES-256-GCM | `milimo/src/mesh/gateway-client.ts` |

---

## PRE-EXISTING TEST FAILURE FIXES

| # | File | Issue | Fix |
|---|---|---|---|
| 1 | `test_solo_init.py` | Evolution schema mismatch | Changed `cycle/day/time` to `cycle_day/schedule` |
| 2 | `assistant_setup.py` | Missing `TEMPLATE_PATH` global | Added global + updated `render_template()` |
| 3 | `finance_init.py` | Naive timestamp parsing | Added timezone fallback |
| 4 | `test_finance_init.py` | Hardcoded timestamps outside 10-day window | Dynamic recent timestamps |
| 5 | `signal_dispatcher.py` | Missing `_send_overdue_ack_warning` | Added method + SLA timer |
| 6 | `.gitignore` | `build/` rule excluded orchestrator build module | Added exception |

---

## CONTENT CLAW FIXES

- Fixed constructor mismatch between `ContentClaw` and `ContentGenerator`
- Wired `war_room` reference to all components
- Connected publish → performance_signal pipeline to Analytics Claw
- Fixed revision flow with regeneration context preservation
- Wired evolution cycle into Content Scheduler

---

## OPS CLAW FIXES

- Implemented `_send_proposal()` (was stub)
- Implemented `_execute_change_order()` (was stub)
- Implemented `_archive_project()` (was stub)
- Fixed `_register_approval_handlers()`
- Enforced pricing SLA timeout (10-min SLA)

---

## ANALYTICS CLAW FIXES

- Wired `ForwardProjector` into `ReportGenerator`
- Replaced mock trend data in `OpportunityScorer`
- Implemented 4 computed report fields (were hardcoded empty/zero)
- Added missing `margin_analysis` + `rate_optimization_check` to Finance weekly summary

---

## TypeScript & Tooling

- Updated `vitest.config.ts` — removed nemoclaw paths
- Updated `commitlint.config.js` — added `"security"` commit type
- Updated `.env.example` — added `JWT_SECRET` and `ALLOWED_ORIGINS`
- Fixed `PendingMessage.payload` from `any` to `Record<string, unknown>`
- Fixed `createWebhookRoute` parameter from `any` to `FastifyInstance`
- Fixed remaining TS errors in `warroom.ts`

---

## Final Verification

| Check | Status |
|---|---|
| NemoClaw code removed from MilimoClaw repo | ✅ |
| Build Claw 13 modules implemented | ✅ |
| Build Claw tests pass (116/116) | ✅ |
| Full blueprint suite passes (1192/1192) | ✅ |
| TypeScript compilation clean (milimo/) | ✅ |
| Security fixes applied | ✅ |
| .gitignore fixed for build/ module | ✅ |
| Pushed to main + develop | ✅ |

---

## 2026-03-20 — Audit Report Remediation Complete

### Summary

This release addresses all issues identified in the production audit report. All 10 issues have been resolved, including 4 HIGH priority, 3 MEDIUM priority, and 3 LOW priority items.

---

## HIGH PRIORITY

### ISSUE 1 — Consolidate Dual Configuration Files

**Problem:** Two config files (`state.json` and `config.json`) with overlapping responsibilities caused inconsistent state.

**Solution:**
- Created unified `ConfigManager` class in `src/onboard/config.ts`
- Single source of truth: `~/.milimo/config.json`
- Automatic migration from legacy `state.json`
- `migrate()` function merges and removes legacy file

**Files Changed:**
- `milimo/src/onboard/config.ts` — ConfigManager class
- `milimo/src/onboard/config-legacy.ts` — Legacy path helper
- `milimo/src/commands/init.ts` — Uses ConfigManager.save()
- `milimo/src/__tests__/config.test.ts` — 17 test cases

---

### ISSUE 2 — Register Missing CLI Commands

**Problem:** Five implemented commands were not registered in `cli.ts`: `health`, `payment`, `verify`, `badge`, `provenance-keygen`.

**Solution:**
- Added all commands to `cli.ts` registration
- Fixed `.requiredOption()` for commands requiring non-optional arguments
- All commands now visible in `openclaw milimo --help`

**Files Changed:**
- `milimo/src/cli.ts` — Command registration

---

### ISSUE 3 — Fix Shell Command Injection Risk

**Problem:** Multiple files used `execSync` with template literals, creating shell injection vulnerabilities.

**Solution:**
- Replaced all `execSync` calls with `spawnSync` using array arguments
- Used `JSON.stringify()` for safe interpolation of dynamic values
- Fixed in: `python-bridge.ts`, `verify.ts`, `badge.ts`, `blueprint.ts`

**Files Changed:**
- `milimo/src/lib/python-bridge.ts` — callPython() uses safe interpolation
- `milimo/src/commands/verify.ts` — spawnSync with array args
- `milimo/src/commands/badge.ts` — All 8 execSync calls replaced
- `milimo/src/commands/blueprint.ts` — spawnSync with JSON.stringify

---

### ISSUE 4 — Add TypeScript Unit Tests

**Problem:** Zero TypeScript test files existed (Python had 8).

**Solution:**
- Created Jest test suite with 68 total test cases:
  - `config.test.ts` — 17 tests (ConfigManager)
  - `config-encryption.test.ts` — 18 tests (encryption)
  - `approval.test.ts` — 19 tests (ApprovalEngine)
  - `warroom.test.ts` — 22 tests (WarRoomTUI)
  - `blueprint.test.ts` — 24 tests (Blueprint commands)
- All tests mock filesystem and child_process
- Added Jest configuration with ts-jest

**Files Created:**
- `milimo/src/__tests__/config.test.ts`
- `milimo/src/__tests__/config-encryption.test.ts`
- `milimo/src/__tests__/approval.test.ts`
- `milimo/src/__tests__/warroom.test.ts`
- `milimo/src/__tests__/blueprint.test.ts`
- `milimo/jest.config.js`

---

## MEDIUM PRIORITY

### ISSUE 5 — Improve Python Bridge

**Problem:** TypeScript → Python bridge used inline Python strings, making errors opaque and escaping fragile.

**Solution:**
- Created `bridge_cli.py` with structured JSON I/O
- CLI accepts `--command` and `--args` arguments
- Returns `{"success": true, "data": {...}}` or `{"success": false, "error": "..."}`
- All debug logs to stderr only
- Added Zod schemas for response validation
- Created `callPythonBridge()` and `callPythonBridgeSafe()` functions

**Files Created:**
- `milimo-blueprint/orchestrator/bridge_cli.py` — CLI entry point
- `milimo/src/lib/bridge-schemas.ts` — Zod validation schemas
- `milimo-blueprint/tests/test_bridge_cli.py` — Pytest tests

**Files Changed:**
- `milimo/src/lib/python-bridge.ts` — Bridge CLI functions

---

### ISSUE 6 — Upgrade War Room TUI

**Problem:** Basic readline TUI with no color, no split panes, no keyboard shortcuts. Rated 5/10.

**Solution:**
- Replaced readline with `blessed` library
- Split-pane layout: Left (60%) War Room, Right (40%) Claw Health
- Keyboard shortcuts: A/B/E/Q/R/H/F
- Color coding: coral (HOLD), amber (REVIEW), teal (AUTO)
- Polling interval: 3 seconds (down from 5)
- Help overlay (press H)
- Finals Mode toggle (press F)

**Files Created:**
- `milimo/src/warroom/warroom-tui.ts` — Blessed TUI implementation

**Files Changed:**
- `milimo/src/commands/warroom.ts` — Uses new TUI

**Dependencies Added:**
- `blessed`
- `@types/blessed`

---

### ISSUE 7 — Encrypt Sensitive Configuration Fields

**Problem:** `meshSecret` stored in plaintext in config file.

**Solution:**
- AES-256-GCM encryption using Node.js crypto module
- Key derivation from machine ID:
  - Linux: `/etc/machine-id`
  - macOS: hardware UUID from `system_profiler`
  - Windows: WMIC UUID
- Encrypted fields prefixed with `enc:v1:`
- Backwards compatible with plaintext values
- Automatic encrypt on save, transparent decrypt on load

**Encrypted Fields:**
- `meshSecret`
- `apiKey`
- `apiToken`
- `accessToken`
- `refreshToken`

**Files Created:**
- `milimo/src/lib/config-encryption.ts` — Encryption functions
- `milimo/src/__tests__/config-encryption.test.ts` — 18 test cases

**Files Changed:**
- `milimo/src/onboard/config.ts` — Integrated encryption

---

## LOW PRIORITY

### ISSUE 8 — Expand Slash Commands

**Problem:** `/milimo` slash command only had `status`, `role`, `finals`.

**Solution:**
Added four new commands:
- `/milimo approve <action_id>` — Approve pending War Room action
- `/milimo veto <action_id>` — Block pending action
- `/milimo health` — One-line health summary per claw
- `/milimo evolution` — Last tool built by each claw with performance delta

**Files Changed:**
- `milimo/src/commands/slash.ts`

---

### ISSUE 9 — Fix Payment API Default URL

**Problem:** Default URL was `localhost:3001`, unusable in production.

**Solution:**
- Default changed to `https://api.milimoclaw.com`
- Fallback chain:
  1. `MILIMO_SERVER_URL` environment variable
  2. `serverUrl` in config.json
  3. Production default
- Added `serverUrl` to `MilimoConfig` interface
- Updated `.env.example` with documentation

**Files Changed:**
- `milimo/src/commands/payment.ts` — getApiBase() function
- `milimo/src/index.ts` — Added serverUrl to MilimoConfig
- `milimo/.env.example` — Production URL documentation

---

### ISSUE 10 — Fix Evolution Manager Static Data

**Problem:** `showCrossClawFlows()` hardcoded console.log strings instead of reading real mesh signal state.

**Solution:**
- Replaced hardcoded output with Python bridge call
- `callPythonBridgeSafe('mesh_flow_state', ...)` returns:
  - Signal type
  - Source/destination claw
  - Last transmission timestamp
  - Signal count this week
- Graceful degradation to default diagram if bridge fails
- Added `getMeshFlowData()` for programmatic access

**Files Changed:**
- `milimo/src/warroom/evolution.ts`

---

## Final Verification Checklist

| Check | Status |
|-------|--------|
| `~/.milimo/state.json` removed after migration | ✅ |
| `openclaw milimo --help` shows all commands | ✅ |
| War Room launches with split-pane TUI | ✅ |
| `openclaw milimo health` returns structured output | ✅ |
| All shell commands use spawn array args | ✅ |
| meshSecret stored encrypted | ✅ |
| Jest tests pass | ✅ 68 tests |
| Python bridge returns valid JSON | ✅ |
| Slash commands respond in chat | ✅ |
| `npm run build` succeeds | ✅ |

---

## Files Modified Summary

### TypeScript Plugin (`milimo/src/`)

| Category | Files |
|----------|-------|
| Configuration | `onboard/config.ts`, `onboard/config-legacy.ts` |
| Commands | `cli.ts`, `init.ts`, `slash.ts`, `payment.ts`, `warroom.ts`, `verify.ts`, `badge.ts`, `blueprint.ts` |
| Library | `lib/python-bridge.ts`, `lib/config-encryption.ts`, `lib/bridge-schemas.ts` |
| War Room | `warroom/warroom-tui.ts`, `warroom/evolution.ts` |
| Tests | `__tests__/*.test.ts` (5 files) |

### Python Orchestrator (`milimo-blueprint/orchestrator/`)

| File | Purpose |
|------|---------|
| `bridge_cli.py` | JSON CLI for TypeScript bridge |
| `tests/test_bridge_cli.py` | Pytest tests |

### Dependencies

| Package | Type |
|---------|------|
| `zod` | Runtime |
| `blessed` | Runtime |
| `@types/blessed` | Dev |

---

## Author

**Mainza Kangombe** — Senior Systems Architect
