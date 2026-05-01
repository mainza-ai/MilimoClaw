# Issues and Fixes Audit

**Summary**: Comprehensive audit of past issues and implemented fixes.

**Sources**:
- `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`

**Last updated**: 2026-04-29

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

## Verification Checklist

1. All claws have assistant handlers: `grep -c "assistant" /sandbox/.milimo/blueprints/0.1.0/orchestrator/*/claw.py`
2. Content claw starts: Check launcher log for "started successfully"
3. Network policy allows Node.js: `grep "node" policies/assistant-sandbox.yaml`
4. All claws running: `grep "started successfully" logs/launcher.log`

---

## Related Pages

- [[common-issues]] — Quick troubleshooting
- [[sandbox-sync]] — Sandbox synchronization
- [[assistant-lucy]] — Lucy documentation
