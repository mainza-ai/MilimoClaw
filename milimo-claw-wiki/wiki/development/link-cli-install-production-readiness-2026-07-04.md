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

### P1 — npm preset (Low, ~15 min)
**File**: `milimo-hermes-sandbox/milimo-blueprint/policies/presets/npm.yaml`
```yaml
preset:
  name: npm
  description: "npm registry access for runtime dependency installs"

network_policies:
  npm_registry:
    name: npm_registry
    endpoints:
      - host: registry.npmjs.org
        port: 443
        access: full
        tls: skip
      - host: registry.yarnpkg.com
        port: 443
        access: full
        tls: skip

    binaries:
      - { path: /usr/local/bin/node }
      - { path: /usr/local/bin/npm }
```

**Also update**: `install-hermes.sh` to apply `npm` preset during onboarding alongside existing presets.

### P2 — Runtime fallback for missing binary (Medium, ~45 min)
**File**: `milimo-core/src/milimo_core/finance/spend_handler.py`

In `_check_link_cli_auth()` or a new helper:
1. `which link-cli` / command lookup
2. If missing: run `npm install -g @stripe/link-cli@0.8.2 --prefix /sandbox/.npm-global`
3. Prepend `/sandbox/.npm-global/bin` to PATH
4. Cache result in module-level var so we don’t retry every spend

**File**: `milimo-hermes-plugin/milimo_hermes_plugin/tools.py`
Same logic in `_check_link_cli_auth()` so the tool layer also recovers.

### P3 — Headless auth support (Medium, ~30 min)
**File**: `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py`

```python
HEADLESS_AUTH_MODES = ("headless_service_account", "ci")

def _check_link_cli_auth() -> dict | None:
    headless = os.environ.get("MILIMO_LINK_CLI_AUTH_MODE", "").lower()
    if headless in HEADLESS_AUTH_MODES:
        # For headless: require existing session, fail clearly if not authenticated
        ...
```

Document in `wiki/modules/finance/link-cli-setup.md` and `wiki/troubleshooting/common-issues.md`.

### P4 — Startup health check (Low, ~15 min)
**File**: `milimo-core/src/milimo_core/finance/finance_claw.py`

In `FinanceClaw.startup()`:
```python
if self.spend_handler:
    error = _check_link_cli_auth()
    if error:
        self._warroom_notifier.notify_generic(
            title="Finance Claw: link-cli auth required",
            message=error.get("action_required", ""),
            level="warning",
        )
```

### P5 — CI drift guard (Low, ~10 min)
**File**: `.github/workflows/hermes-ci.yml` or new `scripts/check-plugin-sync.sh`

Add a step:
```bash
diff -ru milimo-hermes-plugin milimo-hermes-sandbox/milimo-hermes-plugin
```

Fail CI if copies diverge.

---

## 5. Resumption Point

**Last completed**: Dockerfile fix committed as `029a624`. Auth UX (Phase 4/5 from `hermes-skill-factory-remediation-2026-07-04.md`) is functionally complete but not yet verified live because npm global install needs a writable path at runtime.

**Next**: Implement P1 (npm preset) to ensure runtime npm egress is available by default in new sandboxes.

**Blocking**: None — all work is local and can proceed without live sandbox.

---

## 6. Related Pages

- [[hermes-skill-factory-remediation-2026-07-04]] — original auth UX fix phases 4/5
- [[test-spend-flow]] — Stripe Link spend flow tests
- [[common-issues]] — troubleshooting for Finance Claw
- [[link-cli-setup]] — operator auth and payment method setup

## See Also

- `milimo-hermes-sandbox/Dockerfile` — npm install user context
- `milimo-hermes-sandbox/install-hermes.sh` — post-onboarding setup_link_cli_auth()
- `milimo-hermes-plugin/milimo_hermes_plugin/tools.py` — _check_link_cli_auth()
- `milimo-core/src/milimo_core/finance/spend_handler.py` — handle_hold_release subprocess calls
