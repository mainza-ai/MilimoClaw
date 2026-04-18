# Quarterly Tax Prep

**Summary**: Generates quarterly tax preparation summaries for Finance Claw.

**Sources**:
- `milimo-blueprint/orchestrator/finance/finance_scheduler.py`
- `milimo-blueprint/orchestrator/finance/expense_tracker.py`

**Last updated**: 2026-04-15

**Tags**: #module #finance #tax

---

## Overview

Quarterly Tax Prep generates tax preparation documents on the first day of each quarter (Jan 1, Apr 1, Jul 1, Oct 1) to support tax filing.

---

## Schedule

| Quarter | Generation Date | Tax Due Date |
|---------|-----------------|--------------|
| Q1 | January 1 | April 15 |
| Q2 | April 1 | June 15 |
| Q3 | July 1 | September 15 |
| Q4 | October 1 | January 15 (next year) |

---

## Generated Documents

### Income Summary

```json
{
  "quarter": "Q1",
  "year": 2026,
  "total_income": 45000.00,
  "income_by_client": {...},
  "income_by_project": {...}
}
```

### Expense Summary

```json
{
  "quarter": "Q1",
  "year": 2026,
  "total_expenses": 12500.00,
  "by_category": {
    "software": 3000.00,
    "marketing": 2000.00,
    "travel": 1500.00,
    "office": 1000.00,
    "other": 5000.00
  },
  "deductible": 12000.00,
  "non_deductible": 500.00
}
```

### Tax Categories

| Category | Deductible | Notes |
|----------|------------|-------|
| Software subscriptions | Yes | SaaS, cloud services |
| Marketing | Yes | Ads, content |
| Travel | Yes | Client meetings |
| Office expenses | Yes | Equipment, supplies |
| Meals (50%) | Partial | Business meals |
| Personal | No | Non-business |

---

## Integration

### With FinanceScheduler

```python
def _schedule_quarterly_tax_prep(self):
    """Schedule tax prep for quarter start."""
    # Runs on Jan 1, Apr 1, Jul 1, Oct 1
```

### With ExpenseTracker

```python
def generate_tax_summary(self, quarter: str, year: int) -> dict:
    """Generate tax preparation summary."""
    expenses = self.get_quarterly_expenses(quarter, year)
    return self._categorize_for_tax(expenses)
```

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/finance/tax/{year}/Q{N}/income.json` | Income summary |
| `/sandbox/finance/tax/{year}/Q{N}/expenses.json` | Expense summary |
| `/sandbox/finance/tax/{year}/Q{N}/tax-prep.pdf` | Full report |

---

## Workflow

1. Scheduler triggers quarterly on quarter start
2. ExpenseTracker generates expense summary
3. RevenueTracker generates income summary
4. ApprovalHandler queues for REVIEW
5. Operator reviews and exports for accountant

---

## Related Pages

- [[finance-claw]] — Parent claw
- [[finance-scheduler]] — Scheduling
- [[expense-tracker]] — Expense tracking
- [[revenue-tracker]] — Revenue tracking
