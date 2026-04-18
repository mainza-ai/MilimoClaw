# revenue-tracker

**Summary**: Revenue aggregation and weekly summary generation.

**Sources**: `milimo-blueprint/orchestrator/finance/revenue_tracker.py`

**Last updated**: 2026-04-14

**Tags**: #module #finance-claw

---

## Purpose

Aggregates revenue data and generates weekly summaries for Analytics Claw.

## Location

**File**: `milimo-blueprint/orchestrator/finance/revenue_tracker.py`

## Key Classes

### RevenueTracker

Tracks and aggregates revenue.

```python
class RevenueTracker:
    def __init__(
        self,
        fs: FinanceFilesystemInit,
        mesh: MeshClient,
    ):
        self._fs = fs
        self._mesh = mesh

    def record_payment(self, invoice: Invoice) -> None:
        """Record payment and update totals."""
        pass

    def generate_weekly_summary(self) -> RevenueSummary:
        """Generate weekly revenue summary."""
        pass

    def send_to_analytics(self, summary: RevenueSummary) -> None:
        """Send revenue_summary to Analytics Claw."""
        pass
```

## Revenue Storage

```
/sandbox/finance/revenue/
├── weekly-summary.json
├── monthly-summary.json
├── annual-summary.json
└── history/{YYYY-MM-DD}.json
```

## Weekly Summary Generation

Every Sunday at 03:00:
1. Aggregate all `paid/` invoices from past 7 days
2. Calculate week_total, invoices_paid, invoices_pending
3. Calculate week-over-week change
4. Update `weekly-summary.json`
5. Send `revenue_summary` to Analytics Claw

## Summary Payload

Sent to Analytics Claw (totals ONLY):
```json
{
  "week_total": 4240.00,
  "week_over_week_pct": 18.0,
  "invoices_paid": 3,
  "invoices_pending": 1
}
```

**Never includes line items, client names, or individual amounts.**

## Dependencies

- [[payment-monitor]] — Payment detection
- [[analytics-claw]] — Summary recipient

## Related Pages

- [[finance-claw]] — Parent claw
- [[analytics-claw]] — Summary recipient
- [[message-contracts]] — revenue_summary schema
