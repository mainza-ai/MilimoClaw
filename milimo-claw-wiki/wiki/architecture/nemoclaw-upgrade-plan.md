# NemoClaw Upstream Upgrade Plan

Date: 2026-07-24
Author: opencode agent
Status: Draft / Ready for Review

---

## 1  Version Gap Summary

| Component | MilimoClaw Current | Upstream Latest | Gap |
|---|---|---|---|
| **NemoClaw sandbox-base** | `:latest` (unpinned) | `@sha256:5052a448...` | No pin → drifts |
| **NemoClaw hermes-sandbox-base** | `@sha256:8dad3b989...` | `@sha256:e94586474...` | ~30 releases behind |
| **OpenClaw** (package.json) | `2026.3.11` | `2026.7.1` | +4 minor |
| **Node.js** (sandbox) | `22-slim` | `22.23.1` | Patch-only |
| **OpenShell** (min declared) | `0.0.24` | `v0.0.85` | +0.61 major |
| **Hermes** (min declared) | `2026.6.0` | `2026.7.1` (OpenClaw ships it) | +1 minor |
| **NemoClaw inference selector** | `NEMOCLAW_MODEL` (legacy) | `NEMOCLAW_INFERENCE_PROVIDER_ID` | Migration needed |
| **Hermes config version** | `_config_version: 12` | Possibly 13+ | Needs verification |

---

## 2  Image SHA Baseline

### Current Pins

| Image | Current SHA | File |
|---|---|---|
| `sandbox-base` | `:latest` (no pin) | `Dockerfile` line 33 |
| `hermes-sandbox-base` | `sha256:8dad3b989a9ed1e601743310b97be21be5f59f89f7913a47d04f3ec3c40b8ce6` | `milimo-hermes-sandbox/Dockerfile` line 18, `.hermes-base-digest` |
| `hermes-sandbox-base` (CI) | `:latest` (no pin) | `.github/workflows/hermes-ci.yml` line 102 |

### Latest Upstream SHAs (pulled 2026-07-24)

| Image | SHA |
|---|---|
| `sandbox-base` | `sha256:5052a4489004534a33aab79c5612112e62deb1ee1c38224809e43be7de17083a` |
| `hermes-sandbox-base` | `sha256:e94586474de3b5782d60435fd6422e28d864ce9a34513a7de5a54f7358b3dffc` |

---

## 3  Upstream Changes Affecting MilimoClaw

### 3.1  P0 — Must address before rebuild

| Upstream Change | Version | MilimoClaw Impact | File(s) Affected |
|---|---|---|---|
| **Hermes tool schema envelope — single function-schema** | v0.0.87 | `ctx.register_tool()` schema format must match; verify with strict providers (Gemini) | `tools.py` line 1306 |
| **Inference provider selector — `NEMOCLAW_INFERENCE_PROVIDER_ID`** | v0.0.90 | Legacy `NEMOCLAW_MODEL` selector compat will be removed in future release | `.env`, `Dockerfile` ARGs, `install-hermes.sh`, `generate-config.ts` |
| **OpenClaw 2026.7.1** | v0.0.92 | `package.json` pins `2026.3.11` — library API may have changed | `package.json` line 12 |
| **hermes-sandbox-base SHA stale** | All | Missing 30 releases of security patches, bug fixes, OpenClaw 2026.7.1, Node.js 22.23.1 | `Dockerfile` line 18, `.hermes-base-digest`, CI |
| **sandbox-base unpinned** | All | Each build picks up whatever `latest` resolved to — breaks reproducibility | `Dockerfile` line 33 |

### 3.2  P1 — Security / Hygiene

| Upstream Change | Version | MilimoClaw Impact | File(s) Affected |
|---|---|---|---|
| **Axios + OpenTelemetry Jaeger vuln remediated** | v0.0.92 | OpenClaw runtime inside sandbox is patched | `package.json` (absorbed by base image) |
| **`node-tar` remediation** | v0.0.91 | Completed image security scanning | Absorbed by base image |
| **npm, Perl, libexpat, jq updates** | v0.0.95 | Base image package updates | Absorbed by base image |
| **OpenClaw dependency vuln remediation** | v0.0.90 | OpenClaw 2026.6.10 remediations | `package.json` |

### 3.3  P2 — Consistency (Milimo-internal)

| Issue | File(s) | Fix |
|---|---|---|
| `plugin.yaml` version `0.1.0` vs `pyproject.toml` `0.2.0` | `milimo-hermes-plugin/plugin.yaml` | Bump `plugin.yaml` to `0.2.0` |
| `README.md` badge claims `v0.2.1` | `README.md` line 15 | Correct to `v0.2.0` |
| `NEMOCLAW_MESSAGING_PLAN_B64` defined but never consumed | `Dockerfile` lines 110, 127 | Remove or implement |
| `plugin.yaml` has stale `claude_model: "claude-3-5-sonnet"` default | `plugin.yaml` | Remove stale default |
| `blueprint.yaml` `SLACK_ALLOWED_CHANNELS: ""` overrides Dockerfile default | `blueprint.yaml` | Align default or remove |

### 3.4  P3 — Newly Discovered Fragile Integration Points (high risk, not version-specific)

| # | Finding | File(s) | Risk | Remediation |
|---|---|---|---|---|
| F1 | `from tools.registry import registry` + `registry._tools` — Hermes **private internal API** | `delegation.py:369-370` | HIGH — any Hermes refactor of tool registry breaks delegation | Replace with documented Hermes plugin API (`ctx.get_tools()`) or add unit test that breaks loudly if API changes |
| F2 | `ctx.dispatch_tool("delegate_task", ...)` — Hermes **internal method**, not part of documented plugin API | `delegation.py:390` | HIGH — if renamed/removed, delegation fails silently | Wrap in try/except with fallback; add integration test |
| F3 | Hardcoded OpenShell binary path `/opt/openshell/bin/openshell-sandbox` — if OpenShell 0.0.85 moved it, PID-1 detection breaks | `managed-gateway-control.py:69`, `runtime-config-guard.py:49` | HIGH — gateway guard fails to identify supervisor | Make path configurable via env var with fallback |
| F4 | `_config_version: 12` hardcoded — if upstream Hermes config format bumped to 13+, generated `config.yaml` may be rejected | `generate-config.ts:142` | MEDIUM — config validation could fail | Detect upstream config version from base image or make it an ARG |
| F5 | `/usr/local/lib/nemoclaw/openclaw-config-guard.py` referenced but **NOT copied by Dockerfile** — relies on base image presence | `managed-gateway-control.py:68` | MEDIUM — if base image removes it, guard fails | Add explicit COPY in Dockerfile |
| F6 | `min_openshell_version: "0.0.24"` — 3.5x behind actual OpenShell 0.0.85 | `blueprint.yaml` (both copies) line 16 | MEDIUM — floor value does not reflect reality | Bump to `0.0.85` or minimum supported version |
| F7 | Hermes wrapper/validator SHA hashes verify **local copies**, not upstream — upstream drift not detected | `Dockerfile` lines 360-373 | LOW — local copies diverge silently | Add CI step to diff with upstream copies |
| F8 | Hardcoded gateway socket paths `/var/run/openshell/gateway.sock`, `/tmp/openshell-gateway.sock` | `gateway-client.ts:39-40`, `gateway_adapter.py:17` | LOW — long-standing standard paths, unlikely to change | Monitor upstream for socket path changes |

---

## 4  Execution Plan (4 Phases)

### Phase 1 — Base Image + Dependency Update (P0)

**Goal**: Update sandbox base images to latest upstream, bump OpenClaw, add inference provider ID.

**Steps:**

1. **Pin `sandbox-base` to latest SHA**
   - File: `Dockerfile` line 33
   - Change: `ARG SANDBOX_BASE=ghcr.io/nvidia/nemoclaw/sandbox-base:latest` → `@sha256:5052a4489004534a33aab79c5612112e62deb1ee1c38224809e43be7de17083a`
   - Verify: `docker pull` succeeds, image builds

2. **Update `hermes-sandbox-base` SHA** (3 files)
   - Files: `milimo-hermes-sandbox/Dockerfile` line 18, `.hermes-base-digest`, `.github/workflows/hermes-ci.yml` line 102
   - Change: replace `sha256:8dad3b989...` → `sha256:e94586474de3b5782d60435fd6422e28d864ce9a34513a7de5a54f7358b3dffc`
   - CI: `:latest` → `@sha256:e94586474...`
   - Verify: sandbox image rebuild succeeds

3. **Add `NEMOCLAW_INFERENCE_PROVIDER_ID`** (4 files)
   - `milimo-hermes-sandbox/Dockerfile` — add ARG and ENV after existing `NEMOCLAW_MODEL`
   - `install-hermes.sh` — pass through to docker build args
   - `.env` / `.env.example` — add with default `custom` or appropriate value
   - `generate-config.ts` — read and use if set, fall back to `NEMOCLAW_MODEL`
   - Keep `NEMOCLAW_MODEL` as fallback until upstream removes legacy compat

4. **Bump OpenClaw pin**
   - File: `package.json` line 12
   - Change: `"openclaw": "2026.3.11"` → `"2026.7.1"`
   - Verify: `npm install` resolves, `openclaw plugins list` succeeds

5. **Rebuild sandbox image**
   ```bash
   NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 nemoclaw build-claw milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile
   ```

6. **Run test suite**
   ```bash
   python -m pytest tests/ -x -q   # 58 plugin tests
   ```
   Also verify: plugin loads (`openclaw plugins list`), core tools visible in Hermes session.

**Risk**: Schema envelope change (v0.0.87) could affect tool registration.
**Mitigation**: Step 6 includes integration test with a strict-provider-compatible inference call.

**Rollback**: Keep current SHA pins as git revert. Rebuild from old pins.

---

### Phase 2 — Security Patches (P1)

**Goal**: Absorb upstream security fixes. No direct code changes — these patches are in the base images updated in Phase 1.

**Steps:**

7. **Update `blueprint.yaml` min versions**
   - Files: `milimo-blueprint/blueprint.yaml`, `milimo-hermes-sandbox/milimo-blueprint/blueprint.yaml`
   - Changes:
     - `min_openshell_version: "0.0.24"` → `"0.0.85"`
     - `min_openclaw_version: "2026.3.0"` → `"2026.7.0"`
     - `min_hermes_version: "2026.6.0"` → `"2026.7.0"`
   - Risk: LOW — floor values, not ceilings

8. **Smoke test OpenShell compat**
   - Verify: `managed-gateway-control.py` PID-1 detection works after base image update
   - If `/opt/openshell/bin/openshell-sandbox` path changed, address F3 from Phase 4.

---

### Phase 3 — Consistency Fixes (P2)

**Goal**: Fix version skews and stale defaults.

**Steps:**

9. **Fix `plugin.yaml` version**
   - Files: `milimo-hermes-plugin/plugin.yaml`, `milimo-hermes-sandbox/milimo-hermes-plugin/plugin.yaml`
   - Change: `version: "0.1.0"` → `"0.2.0"` (matches `pyproject.toml`)

10. **Fix `README.md` badge**
    - File: `README.md` line 15
    - Change: `v0.2.1` → `v0.2.0`

11. **Remove or implement `NEMOCLAW_MESSAGING_PLAN_B64`**
    - File: `milimo-hermes-sandbox/Dockerfile` lines 110, 127
    - Option A: Remove if truly unused
    - Option B: Implement consumption in `generate-config.ts` if planned

12. **Remove stale `claude_model` default**
    - File: `milimo-hermes-plugin/plugin.yaml`
    - Remove or replace with Milimo-relevant model name

13. **Sync root ↔ sandbox**
    ```bash
    rsync -a --delete milimo-hermes-plugin/ milimo-hermes-sandbox/milimo-hermes-plugin/
    rsync -a --delete milimo-blueprint/ milimo-hermes-sandbox/milimo-blueprint/
    bash scripts/check-plugin-sync.sh
    ```

---

### Phase 4 — Fragile Integration Hardening (P3)

**Goal**: Replace Hermes private API usage with documented APIs; add guardrails against upstream drift.

**Steps:**

14. **Fix F1 — Remove `tools.registry` private import**
    - File: `delegation.py:369-370`
    - Replace `from tools.registry import registry` / `registry._tools` with `ctx.get_tools()` (or equivalent documented Hermes plugin API)
    - If no public API exists, wrap in try/except with a loud warning log so we catch breakage early

15. **Fix F2 — Guard `ctx.dispatch_tool()`**
    - File: `delegation.py:390`
    - Wrap in try/except; log warning if method not found; fall back to a direct import or error message

16. **Fix F3 — Make OpenShell binary path configurable**
    - Files: `managed-gateway-control.py:69`, `runtime-config-guard.py:49`
    - Add `OPENSHELL_BINARY_PATH` env var with fallback to `/opt/openshell/bin/openshell-sandbox`
    - Add note to wiki if upstream changes this path

17. **Fix F4 — Make `_config_version` dynamic**
    - File: `generate-config.ts:142`
    - Option A: Read from environment (e.g., `NEMOCLAW_HERMES_CONFIG_VERSION` env var with fallback to 12)
    - Option B: Probe base image for expected version at build time

18. **Fix F5 — Add explicit COPY for `openclaw-config-guard.py`**
    - File: `milimo-hermes-sandbox/Dockerfile`
    - Add: `COPY scripts/openclaw-config-guard.py /usr/local/lib/nemoclaw/openclaw-config-guard.py`
    - If file doesn't exist in repo, create from upstream or document the dependency

19. **Fix F6 — Bump `min_openshell_version`** (already in Phase 2 step 7)

20. **Fix F7 — Add upstream drift detection for wrapper/validator scripts**
    - Add CI step: `diff` local `scripts/hermes-wrapper.py` and `scripts/validate-hermes-env-secret-boundary.py` against upstream copies (or SHA check)
    - Or document: run `scripts/sync-upstream-scripts.sh` periodically

21. **Verify Hermes tool schema with strict provider**
    - Add integration test that sends a tool call to a strict OpenAI-compatible provider (or Gemini) and confirms the schema envelope is accepted
    - This catches regressions from the v0.0.87 schema envelope change

---

## 5  Risk Register

| # | Risk | Likelihood | Impact | Phase | Mitigation |
|---|---|---|---|---|---|
| R1 | SHA-pinned base image introduces breaking Hermes tool schema change | Low (schema change is backward-compat per upstream) | HIGH (agent tools invisible) | P1 | Full test suite after rebuild; integration test with strict provider |
| R2 | `NEMOCLAW_INFERENCE_PROVIDER_ID` incompatible with existing `NEMOCLAW_MODEL` dual-set | Low (upstream supports both) | MEDIUM (inference routing fails) | P1 | Keep `NEMOCLAW_MODEL` fallback until legacy compat removed |
| R3 | OpenClaw 2026.7.1 breaks plugin manifest format | Low (schema unchanged) | MEDIUM (plugin fails to load) | P1 | `openclaw plugins list` after rebuild |
| R4 | `sandbox-base` SHA we pin differs from current `:latest` runtime | Medium (unknown drift) | MEDIUM (unexpected behavior) | P1 | Pin SHA immediately; rollback by reverting SHA commit |
| R5 | Hermes Agent removed `dispatch_tool` or `tools.registry` | Low (but possible) | HIGH (delegation breaks) | P4 | Wrap in try/except; add loud warning log |
| R6 | OpenShell 0.0.85 changed binary path | Low | HIGH (gateway guard fails) | P4 | Env var with fallback (F3 fix) |
| R7 | Generated config version mismatch (`_config_version: 12` vs upstream 13+) | Low | MEDIUM (config rejected or migrated) | P4 | Make version dynamic via env var (F4 fix) |

---

## 6  Verification Gates

Each phase must pass these checks before proceeding to the next:

| Gate | Command / Check | Expected |
|---|---|---|
| G1 | `python -m pytest tests/ -x -q` | 58 passed |
| G2 | `bash scripts/check-plugin-sync.sh` | `Sync check PASSED` |
| G3 | `openclaw plugins list` | `milimo-hermes-plugin` listed |
| G4 | `nemohermes milimo-hermes status --json` | `"status": "healthy"` |
| G5 | Agent calls `milimo_spend` in Hermes session | Tool visible, handler executes |
| G6 | Agent delegation (`delegate_task`) works | Task routed to correct claw |
| G7 | Gemini-compatible inference (if configured) | Tool list accepted by strict provider |

---

## 7  Files to Touch (Complete Inventory)

| File | Phase | Change |
|---|---|---|
| `Dockerfile` | P1 | Pin `sandbox-base` SHA |
| `milimo-hermes-sandbox/Dockerfile` | P1, P4 | Update `hermes-sandbox-base` SHA, add `NEMOCLAW_INFERENCE_PROVIDER_ID` ARG/ENV, add `openclaw-config-guard.py` COPY |
| `milimo-hermes-sandbox/.hermes-base-digest` | P1 | Update SHA digest |
| `.github/workflows/hermes-ci.yml` | P1 | Pin `hermes-sandbox-base` SHA |
| `package.json` | P1 | Bump `openclaw` to `2026.7.1` |
| `install-hermes.sh` | P1 | Add `NEMOCLAW_INFERENCE_PROVIDER_ID` build arg passthrough |
| `.env` / `.env.example` | P1 | Add `NEMOCLAW_INFERENCE_PROVIDER_ID` |
| `milimo-hermes-sandbox/generate-config.ts` | P1, P4 | Read `NEMOCLAW_INFERENCE_PROVIDER_ID`, make `_config_version` dynamic |
| `milimo-blueprint/blueprint.yaml` | P2 | Bump min versions |
| `milimo-hermes-sandbox/milimo-blueprint/blueprint.yaml` | P2 | Bump min versions |
| `milimo-hermes-plugin/plugin.yaml` | P2 | Fix version to `0.2.0`, remove stale defaults |
| `milimo-hermes-sandbox/milimo-hermes-plugin/plugin.yaml` | P2 | Fix version to `0.2.0`, remove stale defaults |
| `README.md` | P2 | Fix badge version |
| `delegation.py` | P4 | Replace `tools.registry` private import with public API; guard `dispatch_tool` |
| `managed-gateway-control.py` | P4 | Make OpenShell binary path configurable via env var |
| `runtime-config-guard.py` | P4 | Make OpenShell binary path configurable via env var |
| `milimo-claw-wiki/wiki/architecture/nemoclaw-upgrade-plan.md` | P0 | This document (remove after completion) |

---

## 8  Timeline

| Phase | Est. Effort | Dependencies | Verification |
|---|---|---|---|
| P1 — Base Image + Deps | 2–4 hours | Docker pull access, upstream SHAs | G1–G5 |
| P2 — Security / Versions | 30 min | P1 complete | G2 |
| P3 — Consistency | 30 min | P1 complete | G2 |
| P4 — Hardening | 2–3 hours | P1 complete, Hermes API investigation | G3–G7 |

**Total**: ~5–8 hours of work, can be parallelized per phase after P1.

---

## 9  Appendix: Upstream NemoClaw Release Coverage

| Release | Date | Relevant to Milimo? | Key Change |
|---|---|---|---|
| v0.0.95 | 2026-07-24 | YES | Gateway lifecycle, base-image security updates, Hermes restart recovery |
| v0.0.94 | 2026-07-23 | YES | Hermes image 2x faster (5 layers), snapshot restore fixes |
| v0.0.93 | 2026-07-22 | NO | DGX Station / macOS Intel reject |
| v0.0.92 | 2026-07-21 | **YES** | OpenClaw 2026.7.1, Node 22.23.1, security patches |
| v0.0.91 | 2026-07-20 | YES | Hermes token lifecycle, rebuild safety |
| v0.0.90 | 2026-07-18 | **YES** | `NEMOCLAW_INFERENCE_PROVIDER_ID` migration, vuln remediation |
| v0.0.89 | 2026-07-16 | LOW | Inference preservation, policy disclosure |
| v0.0.88 | 2026-07-15 | MEDIUM | Credential-aware rebuild, multi-gateway fix |
| v0.0.87 | 2026-07-14 | **CRITICAL** | Hermes tool schema envelope → single function-schema |
| v0.0.86 | 2026-07-13 | LOW | umask normalization during staging |
| v0.0.85 | 2026-07-12 | LOW | OpenShell v0.0.85 |
