# ops-scheduler

**Summary**: Scheduled autonomous actions for Ops Claw.

**Sources**: `milimo-blueprint/orchestrator/ops/ops_scheduler.py`

**Last updated**: 2026-04-14

**Tags**: #module #ops-claw

---

## Purpose

Manages scheduled autonomous actions including deadline checks, health scoring, and communication monitoring.

## Location

**File**: `milimo-blueprint/orchestrator/ops/ops_scheduler.py`

## Key Classes

### OpsScheduler

Manages scheduled Ops Claw actions.

```python
class OpsScheduler:
    def __init__(
        self,
        project_manager: ProjectManager,
        health_scorer: HealthScorer,
        scope_monitor: ScopeMonitor,
    ):
        self._pm = project_manager
        self._hs = health_scorer
        self._scope = scope_monitor

    def start(self) -> None:
        """Start scheduled actions."""
        pass

    def stop(self) -> None:
        """Stop all scheduled actions."""
        pass
```

## Scheduled Actions

| Action | Schedule | Description |
|--------|----------|-------------|
| Deadline risk check | Daily 08:00 | Check all active projects |
| Health scoring | Weekly Monday 06:00 | Score all clients |
| Health signal send | Weekly Monday 06:30 | Send to Analytics |
| Scope creep check | Continuous | Monitor client comms |

## Configuration

Schedules defined in:
- `milimo-blueprint/templates/solo-founder.yaml`

## Dependencies

- [[project-manager]] — Deadline checks
- [[health-scorer]] — Health scoring
- [[ops-claw]] — Parent coordination

## Related Pages

- [[ops-claw]] — Parent claw
- [[solo-founder]] — Template configuration
