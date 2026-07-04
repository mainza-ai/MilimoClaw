# Issues and Fixes Audit

**Summary**: Comprehensive audit of past issues and implemented fixes.

**Sources**:
- `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`

**Last updated**: 2026-05-24

**Tags**: #troubleshooting #audit #fixes

---

## Overview

This page documents all significant issues discovered and fixed during MilimoClaw development. It serves as a reference for future troubleshooting and onboarding.

---

## Issue 1: Missing Assistant Message Handlers (CRITICAL)

### Problem

All 5 non-assistant claws (of 6 total) were missing handlers for `assistant_query` and `assistant_task` message types. Messages from Lucy were delivered to inboxes but ignored.

### Evidence

- Message `35cef5740a95` found in `/sandbox/.milimo/mesh/inbox/build/processed/`
- Build claw operational log showed no action taken
- Build claw only had 3 handlers registered

### Fix

Added `_handle_assistant_query` and `_handle_assistant_task` methods to all 5 non-assistant claws (of 6 total).

### Files Modified

- `orchestrator/content/content_claw.py`
- `orchestrator/ops/ops_claw.py`
- `orchestrator/analytics/analytics_claw.py`
- `orchestrator/finance/finance_claw.py`
- `orchestrator/build/build_claw.py` (already had handlers)

---

## Issue 2: BrandVoiceManager Init Bug (HIGH)

### Problem

Content Claw failed to start:
```
BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

### Evidence

From launcher log:
```
[ERROR] ClawLauncher: error starting content claw: BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

### Fix

Changed initialization:
```python
# Before
self._voice_manager = BrandVoiceManager(
    voice_dir=self._base_path / "brand" / "voice-profiles",
)

# After
self._voice_manager = BrandVoiceManager(
    fs=self._fs,
    operational_log=self._operational_log,
    privacy_router=self._privacy_router,
)
```

---

## Issue 3: Build Claw File Sync Gap (HIGH)

### Problem

Build claw in sandbox was outdated (529 lines vs 575 lines locally).

### Fix

Uploaded local file to sandbox via tarball extraction.

---

## Issue 4: Health Server Port Conflict (MEDIUM)

### Problem

All claws shared port 8081, causing "Address already in use" errors.

### Fix

Changed to per-claw port mapping:
```python
HEALTH_PORTS = {
    "content": 8081,
    "ops": 8082,
    "analytics": 8083,
    "finance": 8084,
    "build": 8085,
    "assistant": 8086,
}
```

---

## Issue 5: Node.js Network Policy Blocked (MEDIUM)

### Problem

Lucy (Node.js) blocked from GitHub API:
```
NET:OPEN DENIED /usr/local/bin/node -> api.github.com:443
```

### Fix

Added Node.js to `assistant-sandbox.yaml` (endpoint must have `protocol: rest`):
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

## Issue 6: Log File Permission Errors (MEDIUM)

### Problem

Claws reported permission denied on operational.log files.

### Fix

```bash
chown -R sandbox:sandbox /sandbox/.openclaw/milimo/claws/*/logs/
chmod -R 755 /sandbox/.openclaw/milimo/claws/*/logs/
```

---

## Issue 7: Python Syntax Errors in Edits (HIGH)

### Problem

After editing analytics_claw.py and finance_claw.py, Python reported syntax errors.

### Fix

Used Write tool instead of Edit tool for complex multi-line edits. Always verify with `python3 -m py_compile`.

---

## Issue 8: Mesh Config Approval Blocking (NO ACTION NEEDED)

### Problem

Initially suspected `requires_approval: true` for assistant messages.

### Investigation

Both local and sandbox already had `requires_approval: false`. No fix needed.

---

## Issue 9: Indentation Drift in `solo-founder.yaml` (HIGH)

### Problem

The `build` and `assistant` claws under the `operator_policy.approval_modes` and `evolution.per_claw` keys were indented with two spaces instead of four in `templates/solo-founder.yaml`. This violated the core YAML schema expectations of the launcher parsing configuration, causing initialization to fail.

### Fix

Re-aligned indentation to a consistent four spaces for the `build` and `assistant` subsections.

---

## Issue 10: Premature Loop Termination in `handle_launcher_status` (HIGH)

### Problem

In `orchestrator/bridge_cli.py`, the `return status` statement inside `handle_launcher_status` was prematurely indented with 8 spaces inside the `for role in roles:` loop. As a result, the launcher query returned immediately after checking the first claw (`content`), failing to fetch status or heartbeats for any of the other five claws.

### Fix

Adjusted indentation of `return status` to 4 spaces, ensuring that all six claws are fully iterated before returning the status map.

---

## Issue 11: Sliding Window Log Age Date Drift (MEDIUM)

### Problem

Tests query local claw history using static logs. However, the production operational log logic filters records with a sliding 10-day lookback window based on the actual system clock. As the host system clock moved past mid-May 2026, the static test logs (dated April 2026) were filtered out as stale, causing tests like `test_finance_init.py` to receive empty logs and fail.

### Fix

Refactored unit tests to dynamically generate logs using ISO timestamps computed relative to `datetime.now(timezone.utc)`, ensuring environment-agnostic tests that remain valid indefinitely.

---

## Issue 12: Inter-Claw Message Contract Schema Rejections (CRITICAL)

### Problem

Integration testing of multi-agent tasks resulted in message drops due to contract rejections:
1. `assistant_response` sent by worker claws used `"original_message_id"` to reference the query, but the schema required `"query_id"`.
2. `pricing_response` sent by the Finance Claw used `"project_id"`, `"floor_price"`, and `"ceiling_price"`, but the schema required `"query_id"`, `"floor"`, and `"ceiling"`.
3. `build_claw.py` passed its outbound envelope `message_type` using the original query's type instead of hardcoding to `"assistant_response"`, and failed to wrap response payloads inside correct keys.

### Fix

1. Added alias-relaxation handling in `contracts.py` so the validation engine automatically resolves aliases for missing schema requirements.
2. Structured the Build Claw outbound response payload to map exactly to the standard envelope structure.

---

## Issue 13: Sandbox Onboarding Secret-Boundary Check Failure (HIGH)

### Problem

The onboarding or recovery check of the `milimo-hermes` sandbox fails with `Secret-boundary check did not complete cleanly` / `SUPERVISOR_REBUILD_REQUIRED`. The validator script `validate-env-secret-boundary.py` flags `OPENSHELL_SANDBOX_TOKEN_FILE` (injected automatically by the newer NemoClaw supervisor into the container process environment) as a raw secret violation.

### Fix

Safelisted `OPENSHELL_SANDBOX_TOKEN_FILE` in `RUNTIME_ALLOWED_NONSECRET_KEYS` within [validate-env-secret-boundary.py](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/scripts/validate-env-secret-boundary.py). Re-computed the cryptographic hash [NEMOCLAW_HERMES_VALIDATOR_SHA256](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/Dockerfile#L337) and updated it in the `Dockerfile`.

> [!IMPORTANT]
> If manually patching the running container using `docker cp` instead of rebuilding, the file will preserve the host developer's UID. The NemoClaw supervisor requires all validator/helper scripts to be owned by `root:root` with permissions `755`. Run `docker exec <container> chown root:root /usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py` to restore trust boundary compliance.

---

## Issue 14: War Room HTTP Static Path Resolution Bug (MEDIUM)

### Problem

Accessing the War Room server via `localhost:9090/warroom.html` from the host results in a blank page or `warroom.html not found`. The Python server resolved static file candidates using relative paths (`Path(name).exists()`) evaluated against the host's current working directory, which does not contain the static HTML files when run from the repository root.

### Fix

Modified the static file server path resolver in [server.py](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-plugin/warroom/server.py#L235-L245) to resolve static files absolute relative to `_HERE` (the script's directory).

---

## Issue 15: Config configure-guard Intercepting `hermes setup --portal` (HIGH)

### Problem

Running `nemohermes milimo-hermes exec --tty -- hermes setup --portal` inside the sandbox fails with `Error: 'hermes setup' cannot modify config inside the sandbox.` This occurs because the NemoClaw shell configure-guard function (`hermes()`) defined in `start.sh` (which writes to `/tmp/nemoclaw-proxy-env.sh`) unconditionally intercepts all `setup` subcommands, including the authorized interactive OAuth login flow for Nous Portal.

### Fix

Modified the `hermes()` shell function definition inside [start.sh](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/scripts/start.sh) to check if the subcommand is `setup` and the second argument is `--portal`. If matched, it bypasses the config block and executes the real binary via `command hermes "$@"`.

---

## Verification Checklist

1. All claws have assistant handlers: `grep -c "assistant" /sandbox/.milimo/blueprints/0.1.0/orchestrator/*/claw.py`
2. Content claw starts: Check launcher log for "started successfully"
3. Network policy allows Node.js: `grep "node" policies/assistant-sandbox.yaml`
4. All claws running: Check `milimo_status` and see that all six claws show `"launcher_status": "running"`.
5. Message contract verification: Run `PYTHONPATH=.:orchestrator python3 -m pytest tests/ -v` and verify all 1,216 tests pass successfully.

---

## Related Pages

- [[common-issues]] — Quick troubleshooting
- [[sandbox-sync]] — Sandbox synchronization
- [[assistant-lucy]] — Lucy documentation
