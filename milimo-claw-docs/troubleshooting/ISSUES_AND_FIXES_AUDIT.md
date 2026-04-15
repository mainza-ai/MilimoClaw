# MilimoClaw Issues and Fixes Audit Document

**Date:** April 11, 2026 (created) · April 14, 2026 (updated)
**Purpose:** Comprehensive record of issues discovered and fixes implemented for external audit

---

## Overview

This document catalogs all issues identified during the MilimoClaw production readiness investigation and the fixes applied. An AI model can use this to audit the correctness and completeness of our work.

**Audit phases:**
- **Phase 1 (April 11):** Initial sandbox deployment debugging — Issues 1–8
- **Phase 2 (April 14):** Comprehensive code logic audit — Issues 9–16

---

## Issue 1: Missing Assistant Message Handlers (CRITICAL)

### Problem Description

All 5 claws were missing handlers for `assistant_query` and `assistant_task` message types. When Lucy (the assistant) sent messages to claws via the mesh messaging system, the messages were delivered to the inbox but ignored because no handler was registered to process them.

### Evidence

- Message `35cef5740a95` (assistant_task) was found in `/sandbox/.milimo/mesh/inbox/build/processed/` but the build claw operational log showed no action taken
- Build claw only had 3 handlers registered: `feature_brief`, `retention_signals`, `behavior_query_response`
- Content, Ops, Analytics, Finance claws similarly lacked assistant handlers

### Root Cause

The assistant message types were added to `mesh_config.yaml` but the corresponding handler methods were never implemented in the claw code.

### Fix Applied

Added `_handle_assistant_query` and `_handle_assistant_task` methods to all 5 claws:

| Claw | Implementation Location | Method Used |
|------|------------------------|-------------|
| Build | `_inbound_handlers` dict (lines 220-221) | Handler registration dict |
| Content | `_inbound_handlers` dict (lines 322-323) | Handler registration dict |
| Ops | `_inbound_handlers` dict (lines 361-362) | Handler registration dict |
| Analytics | `handler_map` dict (lines 236-237) | Handler map in `handle_inbound` |
| Finance | `elif` branches (lines 401-413) | Direct if/elif chain |

### Files Modified

- `milimo-blueprint/orchestrator/build/build_claw.py` (already had handlers)
- `milimo-blueprint/orchestrator/content/content_claw.py`
- `milimo-blueprint/orchestrator/ops/ops_claw.py`
- `milimo-blueprint/orchestrator/analytics/analytics_claw.py`
- `milimo-blueprint/orchestrator/finance/finance_claw.py`

### Verification Method

```bash
grep -c "assistant" /sandbox/.milimo/blueprints/0.1.0/orchestrator/*/claw.py
# Expected: >0 for all claws
```

---

## Issue 2: BrandVoiceManager Initialization Bug (HIGH)

### Problem Description

Content Claw failed to start with error:
```
BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

### Evidence

From launcher log:
```
2026-04-11 03:50:36,811 [ERROR] milimo.claw_launcher: ClawLauncher: error starting content claw: BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

### Root Cause

`content_claw.py` was passing `voice_dir` parameter to `BrandVoiceManager.__init__()`:
```python
self._voice_manager = BrandVoiceManager(
    voice_dir=self._base_path / "brand" / "voice-profiles",
)
```

But `BrandVoiceManager.__init__` signature was:
```python
def __init__(
    self,
    fs: ContentFilesystemInit,
    operational_log: ContentOperationalLog,
    privacy_router: Any | None = None,
) -> None:
```

### Fix Applied

Changed the initialization to pass correct parameters:
```python
self._voice_manager = BrandVoiceManager(
    fs=self._fs,
    operational_log=self._operational_log,
    privacy_router=self._privacy_router,
)
```

### Files Modified

- `milimo-blueprint/orchestrator/content/content_claw.py` (line 135-138)

---

## Issue 3: Build Claw File Sync Gap (HIGH)

### Problem Description

The build_claw.py in the sandbox was outdated compared to the local version.

### Evidence

- Sandbox version: 529 lines
- Local version: 575 lines
- Local version had handler methods implemented (lines 243-297) but sandbox didn't

### Root Cause

Previous session's changes to `build_claw.py` were made locally but never uploaded to the sandbox.

### Fix Applied

Uploaded the complete local file to sandbox via tarball extraction.

### Files Modified

- Uploaded to: `/sandbox/.milimo/blueprints/0.1.0/orchestrator/build/build_claw.py`

---

## Issue 4: Health Server Port Conflict (MEDIUM)

### Problem Description

All claws shared the same health server port (8081), causing "Address already in use" errors.

### Evidence

From launcher log:
```
Exception in thread Thread-1 (run_server): OSError: [Errno 98] Address already in use
2026-04-11 03:50:36,818 [ERROR] milimo.claw_launcher: ClawLauncher: error starting ops claw: [Errno 98] Address already in use
```

### Root Cause

Single `HEALTH_PORT = 8081` constant was used for all claws. When multiple claw launcher processes started, only the first could bind to the port.

### Fix Applied

Changed from single port to per-claw port mapping:
```python
HEALTH_PORTS = {
    "content": 8081,
    "ops": 8082,
    "analytics": 8083,
    "finance": 8084,
    "build": 8085,
}
DEFAULT_HEALTH_PORT = 8081
```

### Files Modified

- `milimo-blueprint/orchestrator/claw_launcher.py` (lines 71-80)

### Note

The claw_launcher runs a single instance that manages all claws, so the port conflict was actually from stale processes. The per-claw port mapping is a defensive improvement for future scenarios where claws might run separately.

---

## Issue 5: Node.js Binary Not in Network Policy (MEDIUM)

### Problem Description

Lucy (running as Node.js process) was blocked from making GitHub API calls.

### Evidence

From sandbox logs:
```
[1775918173.425] [sandbox] [OCSF] [ocsf] NET:OPEN [MED] DENIED /usr/local/bin/node(54545) -> api.github.com:443 [policy:- engine:opa]
```

### Root Cause

The assistant-sandbox.yaml policy only allowed specific binaries for GitHub API access:
- `/usr/bin/gh`
- `/usr/bin/git`
- `/sandbox/.local/bin/gh`
- `/usr/bin/python3`
- `/sandbox/.local/bin/milimo`

The Node.js binary (`/usr/local/bin/node`) was not in this list.

### Fix Applied

Added Node.js to the github_api policy binaries:
```yaml
binaries:
  - { path: /usr/bin/gh }
  - { path: /usr/bin/git }
  - { path: /sandbox/.local/bin/gh }
  - { path: /usr/local/bin/node }
  - { path: /usr/bin/python3 }
  - { path: /sandbox/.local/bin/milimo }
```

### Files Modified

- `milimo-blueprint/policies/assistant-sandbox.yaml` (line 83)

---

## Issue 6: Log File Permission Errors (MEDIUM)

### Problem Description

Claws reported permission denied errors when trying to write to operational.log files.

### Evidence

```
2026-04-11 16:56:02,333 [ERROR] milimo.claw_launcher: ClawLauncher: error starting content claw: [Errno 13] Permission denied: '/sandbox/content/logs/operational.log'
```

### Root Cause

Log files were owned by `root` instead of `sandbox` user, likely created during a previous run with different permissions.

### Fix Applied

```bash
chown -R sandbox:sandbox /sandbox/*/logs
chmod -R 755 /sandbox/*/logs
```

### Files Modified

No code changes - runtime fix applied via shell command.

### Note for install.sh

The install.sh should include a step to fix permissions on log directories during deployment.

---

## Issue 7: Python Syntax Errors in Edited Files (HIGH)

### Problem Description

After editing analytics_claw.py and finance_claw.py, Python reported syntax errors.

### Evidence

```
IndentationError: expected an indented block after 'try' statement on line 227 (analytics_claw.py, line 228)
SyntaxError: expected 'except' or 'finally' block (finance_claw.py, line 379)
```

### Root Cause

The Edit tool sometimes had issues with whitespace/indentation preservation, particularly:
1. Missing newline between closing brace and `try:` statement
2. `elif` statements losing their indentation level

### Fix Applied

1. For analytics_claw.py: Ensured proper newline before `try:` statement
2. For finance_claw.py: Rewrote the entire file using Write tool to ensure correct indentation

### Lessons Learned

- Complex multi-line edits should use Write tool instead of Edit tool
- Always verify Python syntax with `python3 -m py_compile` after edits

---

## Issue 8: Mesh Config YAML Nesting (CRITICAL — was marked NO ACTION NEEDED)

### Problem Description

Initially suspected that `mesh_config.yaml` had `requires_approval: true` for assistant message types. The April 11 investigation concluded no action was needed.

### Phase 2 Re-investigation (April 14)

The April 14 code logic audit **found a different problem**: While `requires_approval` was indeed `false`, the three assistant message types had **incorrect YAML nesting**:

```yaml
# BEFORE (broken):
  client_health_signal_ops:
    description: "..."
    requires_approval: false
assistant_query:                    # ← ROOT level, NOT under message_types
  description: "..."
  requires_approval: false
assistant_task:                     # ← ROOT level
  description: "..."
  requires_approval: false
  assistant_response:               # ← Nested UNDER assistant_task!
    description: "..."
    requires_approval: false
```

Three structural problems:
1. `assistant_query` was at root level instead of under `message_types:`
2. `assistant_task` was at root level instead of under `message_types:`
3. `assistant_response` was accidentally nested under `assistant_task` instead of being a sibling

### Fix Applied (April 14)

Indented all three to be properly nested under `message_types:`:
```yaml
# AFTER (fixed):
  client_health_signal_ops:
    description: "..."
    requires_approval: false
  assistant_query:
    description: "..."
    requires_approval: false
  assistant_task:
    description: "..."
    requires_approval: false
  assistant_response:
    description: "..."
    requires_approval: false
```

### Verification

```python
import yaml
data = yaml.safe_load(open('mesh_config.yaml'))
mt = data['message_types']
assert 'assistant_query' in mt     # ✅ Now under message_types
assert 'assistant_task' in mt      # ✅ Now under message_types
assert 'assistant_response' in mt  # ✅ Now under message_types
# Total message_types: 33
```

### Files Modified

- `milimo-blueprint/mesh_config.yaml` (lines 128-139)

---

## Issue 9: Ops Claw `_send_assistant_response` Indentation Bug (CRITICAL)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

The `_send_assistant_response` method in `ops_claw.py` was defined at **module level** (zero indentation) instead of inside the `OpsClaw` class body. This caused:

1. `self._send_assistant_response(message, result)` called from `_handle_assistant_query` (line 580) would raise `AttributeError` because the method didn't exist on the class
2. Five `@property` decorators below it (`is_running`, `intake_manager`, `project_manager`, `health_scorer`, `approval_handler`, `dispatcher`) were trapped inside the module-level function body — **unreachable** as class properties
3. The `self.gateway.send()` call used keyword arguments (`role=`, `target=`) instead of a message dict

### Evidence

```python
# BEFORE (line 594 - module level, 0 indent):
def _send_assistant_response(
    self, message: dict[str, Any], result: dict[str, Any]
) -> None:
    """Send response back to assistant."""
    if self._mesh_gateway:
        self._mesh_gateway.send(
            role="ops",              # ← keyword args, wrong
            target="assistant",
            message_type="assistant_response",
            ...
        )

    @property                        # ← trapped inside function!
    def is_running(self) -> bool:
        return self._running
```

### Fix Applied

Re-indented `_send_assistant_response` and all 5 properties into the `OpsClaw` class body (4-space indent). Fixed `gateway.send()` to pass a single message dict:

```python
    def _send_assistant_response(
        self, message: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Send response back to assistant."""
        if self._mesh_gateway:
            self._mesh_gateway.send({
                "sender_role": "ops",
                "recipient_role": "assistant",
                "message_type": "assistant_response",
                "payload": {
                    "original_message_id": message.get("message_id"),
                    "response": result,
                },
            })

    @property
    def is_running(self) -> bool:
        return self._running
    # ... remaining properties
```

### Files Modified

- `milimo-blueprint/orchestrator/ops/ops_claw.py` (lines 591-631)

---

## Issue 10: Analytics Claw Unregistered Assistant Handlers (CRITICAL)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

The Analytics Claw had `_handle_assistant_query` (line 467) and `_handle_assistant_task` (line 480) methods implemented, but they were **NOT registered** in the `handler_map` dict inside `handle_inbound()`. All `assistant_query` and `assistant_task` messages were silently dropped with an "unknown_type" status.

### Evidence

```python
# BEFORE — handler_map was missing assistant entries:
handler_map = {
    "performance_signal": self._handle_performance_signal,
    "client_health_signal": self._handle_client_health_signal,
    "client_onboarded": self._handle_client_onboarded,
    "revenue_summary": self._handle_revenue_summary,
    "shipping_summary": self._handle_shipping_summary,
    "content_performance_query": self._handle_content_performance_query,
    "behavior_query": self._handle_behavior_query,
    # ← assistant_query missing!
    # ← assistant_task missing!
}
```

### Fix Applied

Added both handlers to `handler_map`:
```python
handler_map = {
    # ... existing handlers ...
    "assistant_query": self._handle_assistant_query,
    "assistant_task": self._handle_assistant_task,
}
```

### Files Modified

- `milimo-blueprint/orchestrator/analytics/analytics_claw.py` (lines 228-238)

---

## Issue 11: Content Claw Mesh Sender Signature Mismatch (HIGH)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

`_log_and_respond()` called `self._mesh_sender()` with **keyword arguments** (`message_type=`, `target=`, `payload=`), but `_mesh_sender` was typed as `Callable[[dict[str, Any]], None]` — accepting a single dict argument. This would raise `TypeError` at runtime when assistant handlers tried to respond.

### Evidence

```python
# BEFORE (broken):
if self._mesh_sender:
    self._mesh_sender(
        message_type="assistant_response",   # ← keyword arg
        target="assistant",                   # ← keyword arg
        payload={...},                        # ← keyword arg
    )

# Constructor type:
mesh_sender: Callable[[dict[str, Any]], None]  # ← expects single dict
```

### Fix Applied

Changed to pass a single dict matching the constructor type and standard mesh protocol:
```python
if self._mesh_sender:
    self._mesh_sender({
        "sender_role": "content",
        "recipient_role": "assistant",
        "message_type": "assistant_response",
        "payload": {
            "original_message_id": message.get("message_id"),
            "response": result,
        },
    })
```

### Files Modified

- `milimo-blueprint/orchestrator/content/content_claw.py` (lines 544-552)

---

## Issue 12: Analytics Claw Missing Mesh Response Dispatch (HIGH)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

Even with handlers registered (Issue 10), the Analytics Claw's assistant handlers only **returned** result dicts. Unlike Ops Claw (which sends via `_send_assistant_response`) and Content Claw (which sends via `_log_and_respond`), Analytics had **no mechanism to send responses back** through the mesh to the assistant. The result was stored in a local dict that nobody read.

### Fix Applied

Added `_send_assistant_response()` method using `self.mesh_sender`, and updated both handler methods to call it:

```python
def _send_assistant_response(
    self, message: dict[str, Any], result: dict[str, Any]
) -> None:
    """Send response back to assistant via mesh."""
    if self.mesh_sender:
        self.mesh_sender({
            "sender_role": "analytics",
            "recipient_role": "assistant",
            "message_type": "assistant_response",
            "payload": {
                "original_message_id": message.get("message_id"),
                "response": result,
            },
        })
```

### Files Modified

- `milimo-blueprint/orchestrator/analytics/analytics_claw.py` (lines 467-505)

---

## Issue 13: Build Claw `_vercel` Alias Not Updated (MEDIUM)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

In Build Claw's `startup()`, MVR test aliases for `_github` and `_code_generator` were updated after component initialization, but `_vercel` was never updated. It stayed pointing at whatever value was set in `__init__`.

### Evidence

```python
# BEFORE:
# Update MVR test aliases after component initialization
self._github = self._github_client
self._code_generator = self._code_gen
# ← self._vercel never updated!
```

### Fix Applied

```python
# Update MVR test aliases after component initialization
self._github = self._github_client
self._code_generator = self._code_gen
self._vercel = self._vercel_client
```

### Files Modified

- `milimo-blueprint/orchestrator/build/build_claw.py` (line 227)

---

## Issue 14: `verify_setup()` Relative Path Bug (MEDIUM)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

`verify_setup()` in `assistant_setup.py` checked `bridge_cli_exists` using a relative path that only resolved correctly when the CWD was the project root:
```python
"bridge_cli_exists": Path("milimo-blueprint/orchestrator/bridge_cli.py").exists(),
```

This caused `test_returns_all_true_after_successful_setup` to fail when pytest ran from a different working directory.

### Fix Applied

Changed to use `BLUEPRINT_BASE` (already defined at line 32 from `Path(__file__).resolve().parent.parent`):
```python
"bridge_cli_exists": (BLUEPRINT_BASE / "orchestrator" / "bridge_cli.py").exists(),
```

### Files Modified

- `milimo-blueprint/orchestrator/assistant_setup.py` (line 464)

---

## Issue 15: Finance Claw Missing Assistant Mesh Response (LOW)

> **Discovered:** April 14, 2026 — Phase 2 code logic audit

### Problem Description

Finance Claw's `assistant_query` and `assistant_task` handlers set values in the `result` dict but **never sent** an `assistant_response` message back through the mesh. Unlike Ops, Content, and Build claws which explicitly dispatch responses, Finance just returned the dict from `handle_inbound()` — which the `InboxPoller` doesn't relay.

### Fix Applied

Added `_send_assistant_response()` method using `self.gateway` (the Finance Claw's `MeshGateway` protocol) and called it from both assistant handler branches.

### Files Modified

- `milimo-blueprint/orchestrator/finance/finance_claw.py` (lines 411, 417, 453-480)

---

## Issue 16: Finance Claw Missing Logger Definition (LOW)

> **Discovered:** April 14, 2026 — lint feedback on Issue 15 fix

### Problem Description

The `_send_assistant_response` method added in Issue 15 used `logger.warning(...)` but `finance_claw.py` never imported `logging` or defined a `logger` instance. This would crash with `NameError: name 'logger' is not defined` if the gateway send failed.

### Fix Applied

Added logging import and logger definition:
```python
import logging

logger = logging.getLogger("milimo.finance")
```

### Files Modified

- `milimo-blueprint/orchestrator/finance/finance_claw.py` (lines 13-15)

---

## Verification Checklist for Auditor

### Phase 1 Checks (April 11)

#### 1. All Claws Have Assistant Handlers

Run in sandbox:
```bash
for claw in build content ops analytics finance; do
  echo "=== $claw ==="
  grep -c "assistant" /sandbox/.milimo/blueprints/0.1.0/orchestrator/$claw/${claw}_claw.py
done
```
Expected: All claws should have count > 0

#### 2. BrandVoiceManager Initialization

Check content_claw.py line ~135:
```bash
grep -A3 "BrandVoiceManager(" /sandbox/.milimo/blueprints/0.1.0/orchestrator/content/content_claw.py
```
Expected: Should see `fs=self._fs`, `operational_log=self._operational_log`

#### 3. Health Ports Configuration

Check claw_launcher.py:
```bash
grep -A10 "HEALTH_PORTS" /sandbox/.milimo/blueprints/0.1.0/orchestrator/claw_launcher.py
```
Expected: Dictionary with unique ports for each claw

#### 4. Node.js in Policy

Check assistant-sandbox.yaml:
```bash
grep "node" /sandbox/.milimo/blueprints/0.1.0/policies/assistant-sandbox.yaml
```
Expected: `/usr/local/bin/node` should be in binaries list

#### 5. All Claws Running

Check launcher log:
```bash
grep "started successfully" /sandbox/.milimo/mesh/logs/launcher.log | tail -5
```
Expected: All 5 claws showing "started successfully"

### Phase 2 Checks (April 14)

#### 6. Ops Claw Properties Accessible

```python
from orchestrator.ops.ops_claw import OpsClaw
assert hasattr(OpsClaw, 'is_running')               # @property
assert hasattr(OpsClaw, 'intake_manager')            # @property
assert hasattr(OpsClaw, '_send_assistant_response')  # instance method
```

#### 7. Analytics Handler Map Complete

```python
# Inside handle_inbound(), handler_map should have 9 entries:
assert "assistant_query" in handler_map
assert "assistant_task" in handler_map
```

#### 8. Content Claw Mesh Sender Call

```bash
grep -A5 "_mesh_sender" orchestrator/content/content_claw.py | grep -c "message_type="
```
Expected: 0 — no keyword args used with `_mesh_sender`

#### 9. Mesh Config YAML Structure

```python
import yaml
data = yaml.safe_load(open('mesh_config.yaml'))
mt = data['message_types']
assert 'assistant_query' in mt
assert 'assistant_task' in mt
assert 'assistant_response' in mt
assert len(mt) == 33
```

#### 10. All Modified Files Compile

```bash
python3 -m py_compile orchestrator/ops/ops_claw.py
python3 -m py_compile orchestrator/analytics/analytics_claw.py
python3 -m py_compile orchestrator/content/content_claw.py
python3 -m py_compile orchestrator/build/build_claw.py
python3 -m py_compile orchestrator/finance/finance_claw.py
python3 -m py_compile orchestrator/assistant_setup.py
```
Expected: All pass with no output

---

## Files Changed Summary

### Phase 1 (April 11)

| File | Lines Changed | Description |
|------|--------------|-------------|
| `orchestrator/content/content_claw.py` | ~20 | Fixed BrandVoiceManager init, added assistant handlers |
| `orchestrator/ops/ops_claw.py` | ~40 | Added assistant handlers and response helper |
| `orchestrator/analytics/analytics_claw.py` | ~30 | Added assistant handlers to handler_map |
| `orchestrator/finance/finance_claw.py` | ~20 | Added assistant elif branches |
| `orchestrator/claw_launcher.py` | ~15 | Added HEALTH_PORTS dict |
| `policies/assistant-sandbox.yaml` | 1 | Added Node.js binary |

### Phase 2 (April 14)

| File | Lines Changed | Issues Fixed | Description |
|------|--------------|-------------|-------------|
| `orchestrator/ops/ops_claw.py` | ~40 | #9 | Re-indented `_send_assistant_response` + 5 properties into class, fixed gateway.send() call |
| `orchestrator/analytics/analytics_claw.py` | ~35 | #10, #12 | Registered handlers in handler_map, added mesh response dispatch |
| `orchestrator/content/content_claw.py` | ~10 | #11 | Fixed `_log_and_respond` mesh_sender call signature |
| `mesh_config.yaml` | ~12 | #8 (revised) | Moved assistant message types under `message_types:` with correct nesting |
| `orchestrator/build/build_claw.py` | 1 | #13 | Added `_vercel` alias update in startup() |
| `orchestrator/assistant_setup.py` | 1 | #14 | Changed bridge_cli check to absolute path |
| `orchestrator/finance/finance_claw.py` | ~30 | #15, #16 | Added mesh response dispatch + logger import |

### Phase 2 Test Results

```
249 passed, 4 failed (pre-existing environment issues)
```

The 4 failures are NOT caused by Phase 2 changes:
- 1 failure: `/sandbox` directory is read-only on macOS host
- 3 failures: Port already in use (webhook server tests — stale processes)

---

## Outstanding Items

1. **Log Permission Fix in install.sh**: Should add step to fix log directory permissions during fresh install
2. ~~**Handler Response Format**: Should standardize response format across all claws (some return None, some return dict)~~ — **Resolved in Phase 2:** All 5 claws now send `assistant_response` messages via mesh
3. **Error Handling for Unhandled Messages**: Should add logging when message type is not handled
4. **Standardize Assistant Response Pattern**: All 5 claws implement `_send_assistant_response` independently — consider extracting to a shared mixin or base class
5. **Pre-existing Test Failures**: 4 tests fail on macOS host due to read-only `/sandbox` and port conflicts — need test fixtures that use `tmp_path` instead

---

## Testing Recommendations

1. Send test `assistant_query` message to each claw and verify response arrives in assistant inbox
2. Send test `assistant_task` message and verify acceptance response
3. Test fresh install using `install.sh` and verify all fixes are applied
4. Verify Lucy can make GitHub API calls without network policy blocks
5. Run claw health check to ensure all components initialized correctly
6. **NEW:** Verify `OpsClaw.is_running`, `OpsClaw.intake_manager` etc. are accessible as properties (not trapped in function scope)
7. **NEW:** Verify `mesh_config.yaml` parses with all 33 message types under `message_types`
8. **NEW:** Run `python3 -m py_compile` on all 6 modified files after deployment

---

## References

- Mesh config: `/sandbox/.milimo/blueprints/0.1.0/mesh_config.yaml`
- Launcher log: `/sandbox/.milimo/mesh/logs/launcher.log`
- Policy files: `/sandbox/.milimo/blueprints/0.1.0/policies/`
- Install script: `/MilimoClaw/install.sh`
