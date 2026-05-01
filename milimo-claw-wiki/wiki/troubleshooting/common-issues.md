# Common Issues

**Summary**: Frequently encountered problems and their solutions.

**Sources**:
- `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`

**Last updated**: 2026-04-29

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

## Related Pages

- [[issues-and-fixes]] — Complete audit
- [[sandbox-sync]] — Sandbox synchronization
- [[sequencing-rules]] — Rule violations
