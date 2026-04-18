# Finance Scheduler

**Summary**: Orchestrates all scheduled autonomous actions for the Finance Claw.

**Sources**:
- `milimo-blueprint/orchestrator/finance/finance_scheduler.py`

**Last updated**: 2026-04-15

**Tags**: #module #finance #scheduler

---

## Overview

FinanceScheduler manages all scheduled jobs for the [[finance-claw]]. Uses threading.Timer with self-rescheduling and missed-job recovery.

---

## Schedule

| Job | Schedule | Description |
|-----|----------|-------------|
| Payment check | Daily 09:00 | Check status of all sent invoices |
| Overdue detection | Daily 09:00 | Detect overdue invoices |
| Weekly summary | Sunday 03:00 | Generate revenue summary |
| Tax prep | Quarterly (Jan/Apr/Jul/Oct 1) | Generate tax prep summary |
| Hold staleness | Daily | Check for stale holds |

---

## Key Class

### `FinanceScheduler`

```python
class FinanceScheduler:
    def __init__(
        self,
        payment_monitor: Any,
        revenue_tracker: Any,
        expense_tracker: Any,
        approval_handler: Any,
        operational_log: FinanceOperationalLog,
        fs_path: Path,
    ):
        ...
```

**Dependencies**:
- [[payment-monitor]] — Payment status tracking
- [[revenue-tracker]] — Revenue analysis
- [[expense-tracker]] — Expense logging
- [[approval-handler]] — Approval queue

---

## Behavior

### Startup

1. Checks for missed jobs since last shutdown
2. Runs missed jobs immediately
3. Logs "scheduler_started"

### Self-Rescheduling

After each job:
1. Calculates delay to next occurrence
2. Schedules new timer
3. Logs completion

---

## Jobs

### Daily Payment Check

```python
def _run_daily_payment_check(self):
    """Check all sent invoices for payment status."""
    self.payment_monitor.check_all_sent()
```

### Weekly Summary

```python
def _run_weekly_summary(self):
    """Generate weekly revenue summary."""
    summary = self.revenue_tracker.generate_weekly_summary()
    self._save_summary(summary)
```

### Quarterly Tax Prep

```python
def _run_quarterly_tax_prep(self):
    """Generate tax preparation summary."""
    self.expense_tracker.generate_tax_summary()
```

---

## Integration

### With FinanceClaw

```python
# In finance_claw.py
from .finance_scheduler import FinanceScheduler

scheduler = FinanceScheduler(
    payment_monitor=self.payment_monitor,
    revenue_tracker=self.revenue_tracker,
    expense_tracker=self.expense_tracker,
    approval_handler=approval_handler,
    operational_log=self.operational_log,
    fs_path=self._base_path,
)
```

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/finance/logs/operational.json` | Job execution log |
| `/sandbox/finance/reports/weekly/` | Weekly summaries |
| `/sandbox/finance/tax/` | Tax prep documents |

---

## Related Pages

- [[finance-claw]] — Parent claw
- [[payment-monitor]] — Payment tracking
- [[revenue-tracker]] — Revenue analysis
- [[expense-tracker]] — Expense logging
- [[approval-handler]] — Approval queue
