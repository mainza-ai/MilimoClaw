# Common Issues

**Summary**: Frequently encountered problems and their solutions.

**Sources**:
- `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`

**Last updated**: 2026-05-06

**Tags**: #troubleshooting #issues #fixes

---

## Cross-Claw Issues

### weekly-intelligence.json Unreadable

**Symptom**: Analytics report not accessible by other claws.

**Cause**: Missing shared mount in claw's sandbox policy.

**Fix**: Add entry to `policies/{role}-sandbox.yaml`:
```yaml
filesystem_policy:
  read_only:
    - /sandbox/.openclaw/milimo/claws/analytics/reports
```

Run: `pytest -m phase_a`

---

### project_brief Before pricing_response

**Symptom**: Brief sent without pricing.

**Cause**: Rule 1 violated — sequencing not enforced.

**Fix**: Check `intake_manager.py` — verify pricing awaited before brief.

---

### Invoice Sent at Stage 1 REVIEW

**Symptom**: Invoice transmitted on REVIEW approval.

**Cause**: Rule 2 violated — critical bug.

**Fix**: Check `finance/approval_handler.py` — ensure two-stage separation.

---

### PR Merged at REVIEW Approve

**Symptom**: PR merged without HOLD release.

**Cause**: Rule 3 violated — critical bug.

**Fix**: Check `build/approval_handler.py` — ensure two-stage separation.

---

## Content Claw Issues

### BrandVoiceManager Init Error

**Symptom**:
```
BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

**Cause**: Wrong parameters passed to BrandVoiceManager.

**Fix**: Pass correct parameters:
```python
self._voice_manager = BrandVoiceManager(
    fs=self._fs,
    operational_log=self._operational_log,
    privacy_router=self._privacy_router,
)
```

---

### Draft Not in War Room

**Symptom**: Draft generated but not appearing in War Room.

**Cause**: `draft_ready` message not sent.

**Fix**: Verify Content Claw sends `draft_ready` after generation.

---

## Ops Claw Issues

### Welcome Sent Without Approval

**Symptom**: Client welcome sent automatically.

**Cause**: REVIEW mode misconfigured.

**Fix**: Check approval thresholds in `solo-founder.yaml`.

---

### Deadline Critical is REVIEW not HOLD

**Symptom**: 24-hour deadline shows as REVIEW.

**Cause**: `check_all_deadlines()` not setting HOLD at ≤1 day.

**Fix**: Update deadline checker to use HOLD for critical deadlines.

---

## Analytics Claw Issues

### Query Response > 2 Minutes

**Symptom**: Analytics response exceeds SLA.

**Cause**: SLA not measured in `query_handler.handle()`.

**Fix**: Add timing to query handler, log violations.

---

### No Mid-Week Opportunity Dispatch

**Symptom**: High-confidence opportunities not sent mid-week.

**Cause**: Confidence threshold check not in `opportunity_scorer`.

**Fix**: Verify opportunity scorer dispatches at >0.85 confidence.

---

## Finance Claw Issues

### revenue_summary Has Client Names

**Symptom**: Revenue summary contains identifying information.

**Cause**: Privacy leak — totals only allowed.

**Fix**: Ensure `revenue_summary` only includes aggregate totals.

---

### Overdue Not Firing

**Symptom**: Payment overdue alerts not triggering.

**Cause**: `payment_monitor` schedule not initialized.

**Fix**: Verify FinanceScheduler initializes payment monitor.

---

## Build Claw Issues

### Sprint Plan Blocked on Analytics

**Symptom**: Sprint planning waits indefinitely for Analytics.

**Cause**: 5-min timeout not implemented.

**Fix**: Add `ANALYTICS_WAIT_SECONDS` timeout in `issue_manager.py`.

---

### Deploy Auto-Triggers on PR Merge

**Symptom**: Deployment starts without HOLD release.

**Cause**: Deploy HOLD missing.

**Fix**: Ensure `deploy_manager.py` has separate HOLD queue.

---

## Assistant (Lucy) Issues

### Bridge CLI ImportError on send_to_claw (FIXED)

**Symptom**:
```
ModuleNotFoundError: No module named 'milimo_paths'
ImportError: attempted relative import with no known parent package
```

**Cause** (before 2026-05-06 fix): `bridge_cli.py` used bare `import milimo_paths` and relative `from .contracts import ...` imports. These fail when the script is executed directly (`python3 path/to/bridge_cli.py`) because Python cannot resolve relative imports without a package context, and bare imports only work if CWD happens to be `orchestrator/`.

**Fix** (2026-05-06):
- Converted all 22 relative imports to absolute: `from orchestrator.contracts import ...`
- Converted all 26 `milimo_paths.X` references to direct imports
- Added `PYTHONPATH: options.blueprintDir` to spawn env in `python-bridge.ts`

**See also**: [[bridge-cli]] — Import architecture documentation

---

### mesh_config.yaml message_matrix Parsed as None (FIXED)

**Symptom**:
```
AttributeError: 'NoneType' object has no attribute 'get'
```
at `contracts.py:669` in `ContractValidator.validate()`.

**Cause** (before 2026-05-06 fix): The `message_matrix` sub-keys (`content:`, `ops:`, etc.) were at YAML root level instead of indented under `message_matrix:`. PyYAML parsed the key as `message_matrix: null`, causing `self._matrix` to be `None` in `ContractValidator.__init__`.

**Fix** (2026-05-06): Indented all message_matrix sub-keys with 2 spaces under `message_matrix:`.

**Verification**: `python3 -c "import yaml; d=yaml.safe_load(open('mesh_config.yaml')); print(type(d.get('message_matrix')))"` should return `<class 'dict'>`, not `<class 'NoneType'>`.

**See also**: [[mesh-config]] — YAML indentation note

---

### Node.js Network Policy Blocked

**Symptom**:
```
NET:OPEN DENIED /usr/local/bin/node -> api.github.com:443
```

**Cause**: Node.js not in allowed binaries.

**Fix**: Add to `assistant-sandbox.yaml` (with `protocol: rest` on the endpoint):
```yaml
endpoints:
- host: api.github.com
  port: 443
  protocol: rest
  enforcement: enforce
  access: read-write
binaries:
- { path: /usr/local/bin/node }
```

---

### Assistant Handlers Missing in Claws

**Symptom**: Messages to claws ignored.

**Cause**: `_handle_assistant_query` and `_handle_assistant_task` not implemented.

**Fix**: Add handlers to all claws.

---

## Plugin and Config Issues

### Plugin Not Registered After Install (FIXED)

**Symptom**: `openclaw plugins list` shows no `milimo` entry; `openclaw milimo --help` returns "unknown command".

**Cause** (before 2026-05-02 fix): Install flow transferred full plugin source to `.openclaw/extensions/milimo/` and attempted `npm install` + `npx tsc` inside the sandbox. This failed silently because: (1) sandbox network restrictions blocked npm package downloads, (2) build errors were swallowed by `|| true`, (3) staging directory was cleaned before verification could confirm install.

**Fix** (2026-05-02):
- Build TypeScript + production `node_modules` on host (`npm install --omit=dev` on host)
- Transfer only deployable artifacts: `openclaw.plugin.json`, `package.json`, `dist/`, `node_modules/`
- Stage at `/tmp/milimo-plugin-install/` (not `.openclaw/extensions/`) to avoid Landlock path restrictions
- Use `openclaw plugins install --force /tmp/milimo-plugin-install/`
- Retry with `--dangerously-force-unsafe-install` on exit code 1
- Verify: `openclaw plugins list | grep milimo` must show `loaded` before continuing
- Clean up staging dir only after successful verification

**See also**: [[installation-scripts]] — Full install flow documentation

---

### Destructive `plugins.allow` Override (FIXED)

**Symptom**: After install, all other OpenClaw plugins (telegram, github-copilot, etc.) disappear from `openclaw plugins list` or appear disabled.

**Cause**: Previous install script ran `openclaw config set plugins.allow '["milimo"]'` which sets a flat whitelist — only the listed plugins are enabled, all others are disabled.

**Fix** (2026-05-02): Removed entirely. `openclaw plugins install` already registers the plugin correctly without needing a plugins.allow override. The proper way to register a plugin is `openclaw plugins install --force <path>` — this adds the plugin to `plugins.entries` with default enabled state.

**See also**: [[openclaw-controls]] — Plugin system security controls

---

### Gateway Restart Without Health Check (FIXED)

**Symptom**: `openclaw plugins install` returns success but plugin not loaded; `openclaw milimo --help` still returns "unknown command".

**Cause**: Gateway restart (`pkill openclaw; sleep 8`) was unreliable — `sleep 8` was a blind wait that didn't confirm the gateway actually restarted. If the gateway took longer than 8s, subsequent commands ran against a gateway that hadn't fully reloaded plugins.

**Fix** (2026-05-02): `openclaw gateway restart` (graceful) followed by health check loop polling `openclaw doctor` for up to 30s until gateway is confirmed ready.

---

### acpx Plugin Config Warning (BENIGN)

**Symptom**:
```
plugins.entries.acpx: plugin disabled (bundled (disabled by default)) but config is present
```

**Cause**: `acpx` is a bundled OpenClaw plugin providing the Agent Client Protocol (ACP) runtime — used to launch external coding harnesses (Claude Code, Codex, Gemini CLI) through ACP sessions. It is disabled by default in NemoClaw sandboxes because ACP sessions run on the **host runtime, not inside the sandbox**, bypassing sandbox policy. The warning simply notes that `openclaw.json` contains an `acpx` config entry while the plugin itself is disabled.

**Impact**: None. The config is inert. ACP sessions cannot run inside NemoClaw sandboxes (`Sandboxed sessions cannot spawn ACP sessions`), so the disabled state is correct and expected.

**Fix**: No action needed. The warning is purely informational. If you want to suppress it, remove the `plugins.entries.acpx` config block from `openclaw.json` (or run `openclaw doctor --fix` which can quarantine unused plugin config). Do **not** enable `acpx` in a NemoClaw sandbox — it would not function and is flagged by `openclaw security audit` as a dangerous flag when `permissionMode=approve-all`.

**See also**: [[openclaw-controls]] — Plugin system security controls

---

### `kubectl not found in $PATH` during `--solo` deploy

**Symptom**: Running `./install.sh --solo` produces:
```
OCI runtime exec failed: exec failed: unable to start container process: exec: "kubectl": executable file not found in $PATH
```

**Cause**: `install.sh` helper functions (`sandbox_exec`, `sandbox_exec_root`, `sandbox_cp`) and direct `docker exec "$gateway" kubectl exec` calls assumed a K8s-in-Docker architecture where `kubectl` exists inside the gateway container. In `--solo` local deploy mode, the sandbox is a plain Docker container with no kubectl.

**Fix** (2026-05-15, BUG 16): Helpers now auto-detect whether `kubectl` exists inside the gateway container. If not found, they fall back to direct `docker exec "$SANDBOX_NAME"` — the correct path for `--solo` local deploy. All raw kubectl invocations replaced with helper calls.

---

### `requests` Module Not Found (Deprecated Dependency)

**Symptom**: Python import errors for `requests` module inside the sandbox.

**Cause**: The `requests` library was removed as a dependency (commit `b2741c5`). All HTTP calls now route through NemoClaw's L7 inference proxy via `httpx`.

**Fix**: Ensure no code imports `requests` directly. Use `httpx` for any HTTP calls that bypass the proxy. The `install.sh` venv setup (`pip install ... httpx ...`) includes `httpx` as a replacement.

---

## Related Pages

- [[issues-and-fixes]] — Complete audit
- [[sandbox-sync]] — Sandbox synchronization
- [[sequencing-rules]] — Rule violations
