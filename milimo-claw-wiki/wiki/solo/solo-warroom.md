# Solo War Room

Single-operator action queue with prioritized processing.

## Purpose

Manages a unified action queue for all five claws. Merges all claw queues into one view with HOLD > REVIEW > AUTO priority ordering.

## Priority Ordering

| Priority | Value | Meaning |
|----------|-------|---------|
| HOLD | 1 | Requires immediate attention |
| REVIEW | 2 | Needs operator decision |
| AUTO | 3 | Executed automatically |

## Action Statuses

| Status | Meaning |
|--------|---------|
| `PENDING` | Awaiting decision |
| `APPROVED` | Approved by operator |
| `BLOCKED` | Vetoed by operator |
| `AUTO_EXECUTED` | Executed automatically |

## Main Functions

| Function | Purpose |
|----------|---------|
| `queue_action()` | Add action to queue |
| `approve()` | Approve pending action |
| `block()` | Veto (block) pending action |
| `auto_execute()` | Execute AUTO action |
| `get_pending()` | Get pending actions |
| `get_stats()` | Queue statistics |

## Digest Schedule

- **Morning brief**: 07:00 (configurable)
- **Evening wrap**: 20:00 (configurable)

## WarRoomAction Data Class

```python
@dataclass
class WarRoomAction:
    id: str
    claw: str
    action_type: str
    priority: ActionPriority
    status: ActionStatus
    payload: dict
    created_at: datetime
    decided_at: datetime | None
    operator_decision: str | None
```

## Revenue Summary Widget

Reads from `/sandbox/finance/revenue/weekly_summary.json`:
- `week_revenue` — Current week total
- `week_over_week_pct` — WoW change percentage
- `invoices_paid` — Paid invoice count
- `invoices_pending` — Pending invoice count

## Event Emission

Writes events to `~/.milimo/events/` for WebSocket bridge:
```python
{
    "type": "action_queued",
    "data": {
        "action_id": "...",
        "claw": "content",
        "action_type": "draft",
        "priority": "REVIEW"
    }
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| A | Approve |
| B | Block |
| E | Edit |
| R | Release (HOLD) |
| D | Digest |
| F | Deep work toggle |
| H | Help |
| Q | Quit |

## Relationships

- Uses: [[solo-init]] — Configuration loading
- Receives from: All claws — Action queueing
- Emits to: WebSocket bridge — Real-time updates

## Source

`milimo-blueprint/orchestrator/solo_warroom.py`
