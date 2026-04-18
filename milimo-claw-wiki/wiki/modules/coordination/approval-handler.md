# Approval Handler

**Summary**: Per-claw approval queue management for War Room actions.

**Sources**:
- `milimo-blueprint/orchestrator/content/approval_handler.py`
- `milimo-blueprint/orchestrator/ops/approval_handler.py`
- `milimo-blueprint/orchestrator/analytics/approval_handler.py`
- `milimo-blueprint/orchestrator/finance/approval_handler.py`
- `milimo-blueprint/orchestrator/build/approval_handler.py`

**Last updated**: 2026-04-15

**Tags**: #module #coordination #approval

---

## Overview

Each claw has its own Approval Handler that manages pending actions requiring operator review. Approval handlers queue, track, and process actions through the [[war-room]] TUI.

---

## Per-Claw Implementations

| Claw | Class | Primary Actions |
|------|-------|-----------------|
| Content | `ContentApprovalHandler` | Post publication, content edits |
| Ops | `OpsApprovalHandler` | Client communications, scope changes |
| Analytics | `AnalyticsApprovalHandler` | Report sharing, data queries |
| Finance | `FinanceApprovalHandler` | Invoice approvals, payment holds |
| Build | `BuildApprovalHandler` | PR merges, deployments |

---

## Core Functionality

### Queue Actions

```python
# Queue for REVIEW
handler.queue_review(
    action_type="post_publication",
    payload={"post_id": "abc123", "platform": "twitter"},
    summary="Ready to publish: 'Weekly Update'",
)

# Queue for HOLD (blocks until released)
handler.queue_hold(
    action_type="large_invoice",
    payload={"invoice_id": "inv_123", "amount": 5000},
    summary="Invoice over $5000 requires approval",
)
```

### Process Decisions

```python
# Approve action
result = handler.handle_approve(action_id, send_fn)

# Edit payload before approval
result = handler.handle_edit(action_id, edits, send_fn)

# Block action
result = handler.handle_block(action_id, reason)

# Release hold
result = handler.handle_hold_release(action_id, execute_fn)
```

---

## Action Lifecycle

```
1. Claw generates action → queue_review() or queue_hold()
2. Action appears in War Room TUI
3. Operator reviews → approve/edit/block/release
4. Handler executes callback
5. Action logged to operational log
```

---

## Approval Modes

See [[approval-thresholds]] for mode definitions.

| Mode | Behavior | Example |
|------|----------|---------|
| AUTO | Execute immediately, log only | Low-risk posts |
| REVIEW | Queue for approval, execute when approved | Client emails |
| HOLD | Block until explicit release | Deployments, payments >$500 |

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/{claw}/queue/pending.json` | Pending actions |
| `/sandbox/{claw}/queue/processed.json` | Completed actions |
| `/sandbox/{claw}/logs/approvals.json` | Audit trail |

---

## Integration

### With War Room

War Room polls all approval handlers:

```python
# In war_room.py
for claw in claws:
    handler = claw.approval_handler
    pending = handler.get_pending_actions()
    display_in_tui(pending)
```

### With Signal Dispatcher

After approval, send signal to other claws:

```python
def send_fn(payload):
    signal_dispatcher.dispatch(
        Signal.ACTION_APPROVED,
        {"action_id": action_id, "approved_by": "operator"}
    )
```

---

## Related Pages

- [[war-room]] — TUI for pending actions
- [[approval-thresholds]] — REVIEW/HOLD/AUTO rules
- [[message-contracts]] — Message types
- [[signal-dispatcher-pattern]] — Inter-claw messaging
