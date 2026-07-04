# Link-CLI Install + Auth UX — Production-Readiness Report

**Summary**: Post-rebuild testing revealed that the live sandbox cannot install `@stripe/link-cli` at runtime because npm global installs run as the `sandbox` user and hit `/usr/local/lib/node_modules` with EACCES. This report documents the immediate fix, remaining production gaps, and a phased implementation plan.

**Sources**:
- `milimo-hermes-sandbox/Dockerfile`
- `milimo-hermes-sandbox/install-hermes.sh`
- `milimo-hermes-plugin/milimo_hermes_plugin/tools.py`
- `milimo-core/src/milimo_core/finance/spend_handler.py`
- `milimo-hermes-sandbox/milimo-blueprint/policies/presets/`

**Last updated**: 2026-07-04

**Tags**: #development #finance #link-cli #production #install #hermes #editable-install #policy

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

Created preset enabling npm registry egress (`registry.npmjs.org`, `registry.yarnpkg.com`) and whitelisting `/usr/local/bin/node` and `/usr/local/bin/npm` binaries. Picked up by `install-hermes.sh`'s `policy-add --from-dir` block on onboarding — runtime application depends on the external `nemohermes` CLI honoring the preset schema.

**Also applied**: `install-hermes.sh` gains `--skip-sync-check` flag and a root/sandbox plugin/core sync guard via `scripts/check-plugin-sync.sh`, which runs before `prepare_build_context` and is fatal in `NON_INTERACTIVE=true`.

### P2 — Runtime fallback for missing binary (Medium, ~45 min) ✅
**Files**: both `tools.py` copies

Added module-level helper `_ensure_link_cli()`:
1. Calls `shutil.which("link-cli")` — cache hit is free
2. On miss: runs `npm install -g @stripe/link-cli@0.8.2 --prefix /sandbox/.npm-global`
3. Prepends `/sandbox/.npm-global/bin` to `PATH`, re-checks
4. Result cached in `_HAVE_LINK_CLI: bool | None` so subsequent spend calls are O(1)

Updated `handle_milimo_spend()` to call `_ensure_link_cli()` before `_check_link_cli_auth()`. If the binary cannot be resolved or installed, `_ensure_link_cli()` returns a structured `link_cli_not_available` error dict with a one-shot recover command string; `handle_milimo_spend` surfaces it before any subprocess is attempted. The spend handler's own pre-existing `FileNotFoundError` path in `_poll_spend_request()` (not added by this plan) sets `terminal_status = "release_failed"` rather than returning an error dict — that path is different from the tool-layer intercept.

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
- Calls `_check_link_cli_auth()` (defensive `try`/`except` guard — catches `ImportError` and any runtime errors from the lazy import)
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

**Test result**: 12 passed, 1 warning (deprecation warning for `asyncio_default_fixture_loop_scope` — unrelated). The 6 new tests verify structural behavior with mocked subprocesses; actual CLI behavior is not exercised in CI.


---

### P7 — Editable-install path fix (Critical, ~30 min) ✅
**Files**: `milimo-hermes-sandbox/Dockerfile`, `milimo-hermes-plugin/milimo_hermes_plugin/__init__.py`

**Incident**: After P1–P6 rebuild, `milimo_status` and every other tool declared by the plugin did not appear in Hermes chat. Agent fell back to shell and surfaced `plugin dependency milimo_core is not installed`. Investigation traced this to a permissions wall around `/opt/` for the sandbox user inside `nemohermes exec` and the agent's Python process:

- `__editable__.milimo_hermes_plugin-0.2.0.pth` installed by `uv pip install -e` created `_EditableFinder.MAPPING['milimo_hermes_plugin'] = '/opt/milimo-hermes-plugin/milimo_hermes_plugin'`.
- A parallel `/opt/milimo-core/src` `.pth` entry suffered the same root-owned access restriction.
- `chmod -R a+rX` on `/opt/milimo-hermes-plugin/` alone is not sufficient because `/opt/` inheritance interacts badly with the seccomp/Landlock/LSM stack in the Hermes runtime: `namei -l` reported sane `drwxr-xr-x` mode bits, but `open()` on files under `/opt/milimo-*` returned `EACCES` for the sandbox uid.

**Fix**: `Dockerfile` now performs, in this order:
1. `chown -R sandbox:sandbox /opt/milimo-core /opt/milimo-hermes-plugin`
2. `chmod -R a+rX /opt/milimo-core /opt/milimo-hermes-plugin`
3. Removes the stale editable-registration files for `milimo_hermes_plugin` from `/opt/hermes/.venv/lib/python3.13/site-packages/`
4. Reinstalls the editable package from the sandbox-readable source tree: `uv pip install -e /sandbox/.hermes/plugins/milimo-hermes/`

After reinstall, `_EditableFinder.MAPPING['milimo_hermes_plugin']` points to `/sandbox/.hermes/plugins/milimo-hermes/milimo_hermes_plugin`, which is owned by `sandbox:sandbox`, readable by all along the path, and registered as a read-only Landlock rule in the policy.

**Live verification** (`docker run --rm milimo-hermes-sandbox:latest /opt/hermes/.venv/bin/python -c ...`):

```
milimo_core: /opt/milimo-core/src/milimo_core/__init__.py        # still on sys.path, importable
milimo_hermes_plugin: /sandbox/.hermes/plugins/milimo-hermes/...  # now via .pth finder → readable path
```

`milimo_hermes_plugin.on_load({})` prints `[milimo-hermes] Plugin loaded` with no traceback, confirming the plugin can be imported by the same Python the agent uses. Hermes-venv Python resolves to `/opt/hermes/.venv/bin/python3` (priority 1 in `hermes-wrapper.py`), so this is the same interpreter the agent uses at runtime.

**Note on `milimo_core`**: its editable `.pth` still points to `/opt/milimo-core/src`. Live `docker exec` confirms Python inside the running container can import `milimo_core` from that path (`__file__ == /opt/milimo-core/src/milimo_core/__init__.py`). If a future sandbox update restricts `/opt/milimo-core/`, apply the same chown-then-reinstall sequence.

### P8 — Policy preset collision fix (Critical, ~15 min) ✅
**Files**: `milimo-hermes-sandbox/milimo-blueprint/policies/presets/npm.yaml`, `milimo-hermes-sandbox/install-hermes.sh`

**Incident**: After P1–P7, multiple previously-working presets (`nous-portal`, `sentry`, `stripe`, `stripe-link`, `vercel`) appeared absent from the live sandbox and `hermes setup --portal` returned `403 Forbidden`. Investigation traced two bugs:

1. **Preset name collision (primary)**: `npm.yaml` used `preset.name: npm`. The nemohermes CLI ships a built-in preset with the same name. When `policy-add --from-dir` encountered our custom `npm.yaml`, it aborted with `Preset name 'npm' collides with a built-in preset. Aborting --from-dir`. Every preset after `npm.yaml` in directory order was silently skipped.
2. **Batch abort (secondary)**: `install-hermes.sh:666` wrapped the entire `--from-dir` call in a single `if ... then ... else`. One preset failure caused all remaining presets to be skipped.

**Fix**:
1. Renamed `preset.name` in `npm.yaml` from `npm` → `milimo-npm` (filename kept as `npm.yaml` for backward compat with any host scripts that reference it).
2. Replaced the single `policy-add --from-dir ... --yes` call in `install-hermes.sh` with a `for preset_file in "$preset_dir"/*.yaml` loop calling `policy-add --from-file "$preset_file" --yes` individually. Failures are logged as warnings; the loop continues.

**Live verification**: After applying all 5 missing presets individually to the running sandbox:
- `policy-list` shows all 6 custom presets as `● [user-added]` (`nous-portal`, `milimo-npm`, `sentry`, `stripe`, `stripe-link`, `vercel`)
- `policy-explain` shows all as `status: verified`
- `hermes setup --portal` logs: `ALLOWED ... -> portal.nousresearch.com:443 [policy:nous-portal engine:opa]` (replacing the previous `DENIED ... [reason:endpoint ... is not allowed by any policy]`)
- `npm` built-in preset remains active alongside `milimo-npm`; both cover the same hosts.


---


## 5. Resumption Point

**Last completed**: All seven phases implemented and verified (2026-07-04):

| Phase | Status | Commit/File |
|-------|--------|-------------|
| P1 — npm preset | ✅ merged | `milimo-hermes-sandbox/milimo-blueprint/policies/presets/npm.yaml` |
| P2 — runtime fallback | ✅ merged | `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py` `_ensure_link_cli()` |
| P3 — headless auth mode | ✅ merged | `_check_link_cli_auth()`, env var `MILIMO_LINK_CLI_AUTH_MODE` |
| P4 — startup health check | ✅ merged | `FinanceClaw.startup()` in `finance_claw.py` (both copies) |
| P5 — CI drift guard | ✅ added | `scripts/check-plugin-sync.sh` + `install-hermes.sh --skip-sync-check` |
| P6 — production test matrix | ✅ 6/6 new tests pass, 12/12 total in test_spend_flow.py | `milimo-blueprint/tests/test_spend_flow.py::TestLinkCliProductionReadiness` |
| P7 — editable-install path fix | ✅ rebuilt + verified via `docker run` | `Dockerfile` chown + editable reinstall from `/sandbox/.hermes/plugins/milimo-hermes/` |
| P8 — policy preset collision fix | ✅ live sandbox repaired | `presets/npm.yaml` preset.name → `milimo-npm`; `install-hermes.sh` per-file loop |

**Next**: None — all code changes are complete. Remaining work is live end-to-end verification in the Hermes agent (ask Hermes for `milimo_status` and confirm the tool is listed/usable without falling back to shell).

---

## 6. Related Pages

- [[hermes-skill-factory-remediation-2026-07-04]] — all 6 skill factories + 45 capability dispatch methods
- [[hermes-install]] — live Hermes profile install + verified endpoints
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
