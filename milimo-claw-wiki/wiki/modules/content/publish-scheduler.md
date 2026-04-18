# Publish Scheduler

**Summary**: Scheduled content publishing system that reads calendar/scheduled/ and publishes at correct times with restart recovery.

**Sources**: `milimo-blueprint/orchestrator/content/publish_scheduler.py`

**Last updated**: 2026-04-15

**Tags**: #module #content #scheduling #publishing

---

## Overview

`PublishScheduler` runs continuously, checking for due items every 60 seconds. It never misses a scheduled publish — it handles restart recovery by detecting missed items on startup.

**Claw**: [[content-claw]]

**File**: `orchestrator/content/publish_scheduler.py`

---

## Key Classes

### `ScheduledItem`

A scheduled publish item.

| Field | Type | Description |
|-------|------|-------------|
| schedule_id | str | Unique schedule ID |
| draft_id | str | Draft to publish |
| platform | str | Target platform |
| client_id | str \| None | Client identifier |
| publish_time | str | ISO timestamp for publish |
| content_preview | str | Preview text |
| status | str | scheduled, completed, failed |

---

### `MissedPublish`

Record of a missed scheduled publish.

| Field | Type | Description |
|-------|------|-------------|
| schedule_id | str | Schedule ID |
| draft_id | str | Draft ID |
| platform | str | Platform |
| scheduled_time | str | Original publish time |
| detected_at | str | Detection timestamp |
| hours_late | float | Hours past scheduled |

---

### `PublishScheduler`

Main scheduler class.

```python
scheduler = PublishScheduler(
    fs=content_filesystem,
    operational_log=log,
    publisher=platform_publisher,
    war_room=war_room,
    credentials_provider=get_platform_creds
)
scheduler.start()
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `start()` | Begin continuous scheduling loop |
| `stop()` | Stop the scheduling loop |
| `check_due_items()` | Find items due for publishing |
| `recover_missed_publishes()` | Find missed items on startup |

---

## Scheduling Loop

```
start() → recover_missed_publishes()
         ↓
    _run_loop() (every 60s)
         ↓
    check_due_items()
         ↓
    _publish_item() for each due
         ↓
    _mark_schedule_complete() or _mark_schedule_failed()
```

---

## File Structure

```
content/
├── calendar/
│   ├── scheduled/
│   │   └── schedule-001.json  # Pending schedules
│   └── published/
│       └── draft-abc.json     # Published records
└── drafts/
    └── approved/
        └── draft-abc.json     # Content to publish
```

---

## Schedule File Format

```json
{
  "schedule_id": "schedule-001",
  "draft_id": "draft-abc",
  "platform": "twitter",
  "client_id": "client-123",
  "publish_time": "2026-04-15T09:00:00Z",
  "content_preview": "Check out our latest...",
  "status": "scheduled",
  "scheduled_at": "2026-04-14T10:00:00Z"
}
```

---

## Missed Publish Handling

On startup, the scheduler checks for missed publishes:

1. Load all items from `calendar/scheduled/`
2. Check if `publish_time` is in the past
3. Check if published record exists in `calendar/published/`
4. If missed, escalate to War Room

```python
missed = scheduler.recover_missed_publishes()
# Returns items that should have been published
```

---

## War Room Escalation

Missed publishes are queued to the War Room:

```python
war_room.queue_action(
    claw="content",
    action_type="missed_publish",
    payload={
        "schedule_id": "...",
        "draft_id": "...",
        "hours_late": 2.5,
        "message": "Missed scheduled publish — publish now?"
    }
)
```

---

## Check Interval

Default: 60 seconds

```python
CHECK_INTERVAL_SECONDS = 60
```

---

## Integration Points

- **Input**: `calendar/scheduled/*.json`
- **Output**: [[platform-publisher]] for actual publishing
- **Credentials**: `credentials_provider(platform)` callback
- **Escalation**: [[war-room]] for missed items

---

## Related Pages

- [[platform-publisher]] — Actual publishing logic
- [[content-claw]] — Parent claw
- [[war-room]] — Approval queue for missed items
- [[content-scheduler]] — Schedule creation

---

## See Also

- `orchestrator/content/platform_publisher.py` — Publishing implementation
- `orchestrator/content/content_scheduler.py` — Schedule creation
