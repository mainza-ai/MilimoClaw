# Analytics Scheduler

**Summary**: Orchestrates all scheduled autonomous actions for the Analytics Claw.

**Sources**:
- `milimo-blueprint/orchestrator/analytics/analytics_scheduler.py`

**Last updated**: 2026-04-15

**Tags**: #module #analytics #scheduler

---

## Overview

The Analytics Scheduler manages all scheduled jobs for the [[analytics-claw]]. Uses only Python stdlib (threading.Timer) — no cron or APScheduler dependency.

---

## Schedule

| Job | Schedule | Description |
|-----|----------|-------------|
| Baseline recalculation | Sunday 01:00 | Recalculates 30-day rolling baselines |
| Weekly intelligence report | Sunday 02:00 | Generates comprehensive weekly report |
| Opportunity scoring | Daily 06:00 | Scores new opportunities from data |

All times are local timezone.

---

## Key Class

### `AnalyticsScheduler`

```python
class AnalyticsScheduler:
    def __init__(
        self,
        baseline_manager: Any,
        report_generator: Any,
        opportunity_scorer: Any,
        operational_log: AnalyticsOperationalLog,
        signal_dispatcher: Any = None,
    ) -> None:
        ...
```

**Dependencies**:
- [[baseline-manager]] — 30-day baseline calculator
- [[report-generator]] — Intelligence report generator
- [[opportunity-scorer]] — Opportunity scoring engine
- [[signal-dispatcher-pattern]] — Inter-claw messaging

---

## Behavior

### Startup

1. Checks if any scheduled jobs were missed during downtime
2. If missed, runs the job immediately
3. Logs "missed job recovered" for audit trail

### Self-Rescheduling

After each job execution:
1. Calculates delay to next occurrence
2. Schedules next timer
3. Logs completion

### No Duplicate Start

Calling `start()` twice logs a warning and returns early.

---

## Methods

| Method | Purpose |
|--------|---------|
| `start()` | Initialize all scheduled jobs |
| `stop()` | Cancel all pending timers |
| `_schedule_next()` | Calculate delay and set timer |
| `_check_missed_jobs()` | Recover missed jobs from downtime |
| `_run_baseline_recalculation()` | Execute baseline job |
| `_run_weekly_report()` | Execute report job |
| `_run_opportunity_scoring()` | Execute scoring job |

---

## Integration

### With AnalyticsClaw

```python
# In analytics_claw.py
from .analytics_scheduler import AnalyticsScheduler

self.scheduler = AnalyticsScheduler(
    baseline_manager=self.baseline_manager,
    report_generator=self.report_generator,
    opportunity_scorer=self.opportunity_scorer,
    operational_log=self.operational_log,
    signal_dispatcher=self.signal_dispatcher,
)
self.scheduler.start()
```

### With Signal Dispatcher

After job completion, can send signals to other claws:

```python
if self.signal_dispatcher:
    self.signal_dispatcher.dispatch(
        Signal.WEEKLY_REPORT_READY,
        {"report_path": report_path}
    )
```

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/analytics/logs/operational.json` | Job execution log |
| `/sandbox/analytics/reports/weekly/` | Generated reports |
| `/sandbox/analytics/baselines/` | Baseline data |

---

## Related Pages

- [[analytics-claw]] — Parent claw
- [[baseline-manager]] — Baseline management
- [[report-generator]] — Report generation
- [[opportunity-scorer]] — Opportunity scoring
- [[signal-dispatcher-pattern]] — Inter-claw messaging
