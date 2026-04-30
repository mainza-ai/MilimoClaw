# Solo War Room

**Summary**: Single-operator action queue with prioritized processing and VETO > HOLD > REVIEW > AUTO ordering.

**Sources**: `milimo-blueprint/orchestrator/solo_warroom.py`

**Last updated**: 2026-04-28

**Tags**: #solo #warroom #queue #approval

---

## Purpose

Manages a unified action queue for all six claws. Merges all claw queues into one view with VETO > HOLD > REVIEW > AUTO priority ordering.

## Priority Ordering

| Priority | Value | Meaning |
|----------|-------|---------|
| VETO | 0 | Any squad member can block; requires unanimous approval |
| HOLD | 1 | Requires immediate attention |
| REVIEW | 2 | Needs operator decision |
| AUTO | 3 | Executed automatically |

## Action Statuses

| Status | Meaning |
|--------|---------|
| `PENDING` | Awaiting decision |
| `APPROVED` | Approved by operator |
| `BLOCKED` | Vetoed by operator or squad member |
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

Reads from `/sandbox/.openclaw-data/milimo/claws/finance/revenue/weekly_summary.json`:
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
