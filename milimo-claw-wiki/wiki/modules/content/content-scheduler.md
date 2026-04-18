# content-scheduler

**Summary**: Schedules approved content for optimal publish times.

**Sources**: `milimo-blueprint/orchestrator/content/content_scheduler.py`

**Last updated**: 2026-04-14

**Tags**: #module #content-claw

---

## Purpose

Manages content scheduling based on timing optimizer recommendations and platform-specific peak windows.

## Location

**File**: `milimo-blueprint/orchestrator/content/content_scheduler.py`

## Key Classes

### ContentScheduler

Handles content scheduling and calendar management.

```python
class ContentScheduler:
    def __init__(
        self,
        fs: ContentFilesystemInit,
        timing_optimizer: TimingOptimizer,
    ):
        self._fs = fs
        self._optimizer = timing_optimizer

    def schedule_draft(self, draft: Draft) -> ScheduledPost:
        """Schedule draft for optimal publish time."""
        pass

    def get_optimal_time(self, platform: str, client_id: str) -> datetime:
        """Get optimal publish time for platform/client."""
        pass

    def cancel_scheduled(self, post_id: str) -> None:
        """Cancel scheduled post."""
        pass
```

## Calendar Storage

```
/sandbox/content/calendar/
├── scheduled/    # approved, awaiting publish
└── published/    # publish confirmation records
```

## Timing Optimization

Uses timing optimizer evolution tool (week 14+):
- Platform-specific peak windows
- Audience-specific timing
- Historical engagement data

## Approval Mode

Calendar updates are **AUTO**:
- Logged, visible in morning digest
- Operator can override anytime

## Dependencies

- [[timing-optimizer]] — Optimal time calculation
- [[platform-publisher]] — Publishing trigger

## Related Pages

- [[content-claw]] — Parent claw
- [[evolution-cycle]] — Timing optimizer tool
- [[platform-publisher]] — Publishing
