# Link-CLI Install + Auth UX — Production-Readiness Report

**Summary**: Post-rebuild testing revealed that the live sandbox cannot install `@stripe/link-cli` at runtime because npm global installs run as the `sandbox` user and hit `/usr/local/lib/node_modules` with EACCES. This report documents the immediate fix, remaining production gaps, and a phased implementation plan.

**Sources**:
- `milimo-hermes-sandbox/Dockerfile`
- `milimo-hermes-sandbox/install-hermes.sh`
- `milimo-hermes-plugin/milimo_hermes_plugin/tools.py`
- `milimo-core/src/milimo_core/finance/spend_handler.py`
- `milimo-hermes-sandbox/milimo-blueprint/policies/presets/`

**Last updated**: 2026-07-04

**Tags**: #development #finance #link-cli #production #install

---

## 1. Immediate Fix

**Commit**: `029a624` — `fix: run npm global install as root in Dockerfile`

| Problem | Fix |
|---------|-----|
| `npm install -g @stripe/link-cli@0.8.2` ran as `sandbox` user after `USER sandbox` | Explicit `USER root` for the npm install layer, then `USER sandbox` after |
| Silent `|| echo "deferred to runtime"` masked npm/registry failures | Removed fallback; Docker build now fails fast on npm errors |

This ensures `link-cli` is baked into the image and world-readable at runtime.

---

## 2. Confirmed Gaps / Missing Functionality

### 2.1 Runtime npm policy is not in shipped presets
`nemohermes ... policy-add npm --yes` was required during testing to allow npm egress. The `milimo-hermes-sandbox/milimo-blueprint/policies/presets/` directory does not include an `npm.yaml` preset.

**Impact**: Any post-deploy runtime npm install is blocked by default policy.

### 2.2 No runtime fallback if baked binary is missing
If the image build silently skips npm (network outage, registry down), the binary is absent and Finance Claw spend fails. There is no recovery path documented in `install-hermes.sh` or `tools.py`.

### 2.3 Non-interactive mode can never complete link-cli auth
`setup_link_cli_auth()` explicitly skips when `NON_INTERACTIVE=true`. Production automated deploys have no operator to run `link-cli auth login`. The agent will permanently return `link_cli_not_authenticated`.

### 2.4 No early health check for link-cli
`_check_link_cli_auth()` only runs on spend requests. Missing binary, expired session, or network policy changes are not surfaced until first use.

### 2.5 Editable-install mirror drift
`milimo-hermes-plugin/` is copied to both repo root and `milimo-hermes-sandbox/`. A contributor can edit one copy and miss the other. There is no CI guard.

---

## 3. Improvement / Enhancement Areas

| # | Area | Benefit | Effort |
|---|------|---------|--------|
| I1 | Add `npm.yaml` preset to `milimo-blueprint/policies/presets/` | Runtime npm egress available out of the box | Low |
| I2 | Runtime fallback: try `npm install -g --prefix /sandbox/.npm-global` if `link-cli` missing | Self-healing without rebuild | Medium |
| I3 | Headless auth mode (`MILIMO_LINK_CLI_AUTH_MODE=headless_service_account`) | CI/CD compatible | Medium |
| I4 | Startup health check in `FinanceClaw.startup()` | Early warning instead of first-failure | Low |
| I5 | CI guard for root vs sandbox plugin copy drift | Prevent silent divergence | Low |

---

## 4. Implementation Plan

### P1 — npm preset (Low, ~15 min) ✅
**File**: `milimo-hermes-sandbox/milimo-blueprint/policies/presets/npm.yaml`

Created preset enabling npm registry egress (`registry.npmjs.org`, `registry.yarnpkg.com`) and whitelisting `/usr/local/bin/node` and `/usr/local/bin/npm` binaries. Picked up automatically by `install-hermes.sh`'s `policy-add --from-dir` block on onboarding.

**Also applied**: `install-hermes.sh` gains `--skip-sync-check` flag and a root/sandbox plugin/core sync guard via `scripts/check-plugin-sync.sh`, which runs before `prepare_build_context` and is fatal in `NON_INTERACTIVE=true`.

### P2 — Runtime fallback for missing binary (Medium, ~45 min) ✅
**Files**: both `tools.py` copies + `spend_handler.py`

Added module-level helper `_ensure_link_cli()`:
1. Calls `shutil.which("link-cli")` — cache hit is free
2. On miss: runs `npm install -g @stripe/link-cli@0.8.2 --prefix /sandbox/.npm-global`
3. Prepends `/sandbox/.npm-global/bin` to `PATH`, re-checks
4. Result cached in `_HAVE_LINK_CLI: bool | None` so subsequent spend calls are O(1)

Updated `handle_milimo_spend()` to call `_ensure_link_cli()` before `_check_link_cli_auth()`. The spend handler's `FileNotFoundError` path now returns a structured `link_cli_not_available` error dict with a one-shot recover command string.

### P3 — Headless auth mode (Medium, ~30 min) ✅
**File**: both `tools.py` copies

`_check_link_cli_auth()` now reads `MILIMO_LINK_CLI_AUTH_MODE` before running `link-cli auth status`:

| Value | Behavior |
|-------|----------|
| `ci` | Runs `link-cli auth status`; on failure returns `link_cli_not_authenticated` with `[CI environment]` label — never blocks for interactive login |
| `headless_service_account` | Same but label reads `[headless service account]` |
| unset / `environment` | Legacy interactive path preserved — surfaces `approval_url` when available |

Production-ready error: `"[ci] link-cli is not authenticated. Set up service-account credentials or set MILIMO_LINK_CLI_AUTH_MODE=environment to skip."`

### P4 — Startup health check (Low, ~15 min) ✅
**File**: both `finance_claw.py` copies

In `FinanceClaw.startup()`, after `set_spend_handler(spend_handler)`:
- Calls `_check_link_cli_auth()` (defensive `ImportError` guard)
- On auth error: fires `warroom_notifier.notify_generic(title="Finance Claw: link-cli auth required", message=<action_required>, level="warning")`
- Does not crash startup — Finance Claw starts but surfaces the auth gap via War Room

### P5 — CI drift guard (Low, ~10 min) ✅
**Files**: `scripts/check-plugin-sync.sh` + `install-hermes.sh`

New script `scripts/check-plugin-sync.sh` diffs root ↔ sandbox copies of both `milimo-hermes-plugin/` and `milimo-core/`, ignoring `__pycache__`, `.pyc`, `.pth`, `.egg-info`. Describes each drift entry with a suggested `rsync` command. Exits 1 with full diff in CI mode.

`install-hermes.sh`:
- Adds `--skip-sync-check` flag and `MILIMO_SKIP_SYNC_CHECK` env var
- Runs `check-plugin-sync.sh` automatically before `prepare_build_context`
- Fatal in `NON_INTERACTIVE=true`; warns-but-continues in interactive mode

### P6 — Production test matrix (High, ~30 min) ✅
**File**: `milimo-hermes-sandbox/milimo-blueprint/tests/test_spend_flow.py`

Added `TestLinkCliProductionReadiness` class with 6 new tests:

| Test | What it proves |
|------|----------------|
| `test_ensure_link_cli_cache_hit` | Cached miss returns immediately without running npm |
| `test_ensure_link_cli_installs_to_writable_prefix` | Fallback calls `npm install -g --prefix /sandbox/.npm-global` |
| `test_ensure_link_cli_returns_error_on_install_failure` | Failed install produces actionable `link_cli_not_available` error |
| `test_check_link_cli_auth_headless_ci_mode` | `MILIMO_LINK_CLI_AUTH_MODE=ci` → non-interactive error (no device URL) |
| `test_check_link_cli_auth_headless_service_account_mode` | `...=headless_service_account` → service-account error |
| `test_handle_milimo_spend_returns_install_error_when_binary_missing` | `_ensure_link_cli` intercept called before any subprocess; error surfaced at tool layer |

**Test result**: 12 passed, 0 failed, 1 deprecation warning (`asyncio_default_fixture_loop_scope` — unrelated).


---

## 5. Resumption Point

**Last completed**: All six enhancement phases implemented and verified (2026-07-04):

| Phase | Status | Commit/File |
|-------|--------|-------------|
| P1 — npm preset | ✅ merged | `milimo-hermes-sandbox/milimo-blueprint/policies/presets/npm.yaml` |
| P2 — runtime fallback | ✅ merged | `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py` `_ensure_link_cli()` |
| P3 — headless auth mode | ✅ merged | `_check_link_cli_auth()`, env var `MILIMO_LINK_CLI_AUTH_MODE` |
| P4 — startup health check | ✅ merged | `FinanceClaw.startup()` in `finance_claw.py` (both copies) |
| P5 — CI drift guard | ✅ added | `scripts/check-plugin-sync.sh` + `install-hermes.sh --skip-sync-check` |
| P6 — production test matrix | ✅ 12/12 tests pass | `milimo-blueprint/tests/test_spend_flow.py::TestLinkCliProductionReadiness` |

**Next**: None — all work is local and verified. Future work:
- Live-sandbox rebuild + end-to-end spend flow with npm preset applied
- Real headless service account credentials in CI environment

---

## 6. Related Pages

- [[hermes-skill-factory-remediation-2026-07-04]] — original auth UX fix phases 4/5
- [[test-spend-flow]] — Stripe Link spend flow tests
- [[common-issues]] — troubleshooting for Finance Claw
- [[link-cli-setup]] — operator auth and payment method setup

## See Also

- `milimo-hermes-sandbox/milimo-blueprint/policies/presets/npm.yaml` — P1 npm policy preset
- `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py` — `_ensure_link_cli()`, `_check_link_cli_auth()` (P2/P3)
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/finance_claw.py` — startup health check (P4)
- `scripts/check-plugin-sync.sh` — P5 CI drift guard
- `milimo-hermes-sandbox/install-hermes.sh` — `--skip-sync-check`, `setup_link_cli_auth()` (P5/P1)
- `milimo-hermes-sandbox/milimo-blueprint/tests/test_spend_flow.py` — `TestLinkCliProductionReadiness` (P6)
