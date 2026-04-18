# Payment Events Log

**Summary**: Audit trail for all payment-related events in Finance Claw.

**Sources**:
- `milimo-blueprint/orchestrator/finance/`

**Last updated**: 2026-04-15

**Tags**: #module #finance #audit #payments

---

## Overview

Payment Events Log maintains an immutable audit trail of all payment events including invoices sent, payments received, overdue warnings, and collection actions.

---

## Event Types

| Event | Description | Trigger |
|-------|-------------|---------|
| `invoice_sent` | Invoice dispatched to client | Stripe send |
| `payment_received` | Payment confirmed | Stripe webhook |
| `payment_failed` | Payment attempt failed | Stripe webhook |
| `overdue_detected` | Invoice past due date | Daily check |
| `reminder_sent` | Payment reminder sent | Scheduler |
| `collection_started` | Collection process initiated | Overdue > 30 days |
| `dispute_opened` | Chargeback or dispute | Stripe webhook |
| `refund_issued` | Refund processed | Manual |

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/finance/logs/payment-events.jsonl` | Event log (append-only) |
| `/sandbox/finance/logs/payment-events-summary.json` | Daily summary |

---

## Event Structure

```json
{
  "event_id": "evt_abc123",
  "event_type": "payment_received",
  "timestamp": "2026-04-15T10:30:00Z",
  "invoice_id": "inv_123",
  "client_id": "cli_456",
  "amount_usd": 1500.00,
  "stripe_event_id": "evt_stripe_xyz",
  "metadata": {
    "payment_method": "card",
    "card_last4": "4242"
  }
}
```

---

## Integration

### With PaymentMonitor

```python
def log_payment_event(self, event_type: str, payload: dict):
    """Log payment event to audit trail."""
    event = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload
    }
    self._events_log.write(event)
```

### With PaymentRiskScorer

```python
# Uses event history for risk assessment
event_history = payment_events_log.get_client_events(client_id)
risk_score = scorer.calculate_risk(event_history)
```

---

## Querying

```python
def get_client_events(self, client_id: str) -> list[dict]:
    """Get all events for a client."""

def get_invoice_events(self, invoice_id: str) -> list[dict]:
    """Get all events for an invoice."""

def get_events_in_range(self, start: datetime, end: datetime) -> list[dict]:
    """Get events in date range."""
```

---

## Retention

- Events retained for 7 years (tax compliance)
- Summary data retained indefinitely
- Raw events archived quarterly

---

## Related Pages

- [[finance-claw]] — Parent claw
- [[payment-monitor]] — Payment tracking
- [[payment-risk-scorer]] — Risk assessment
- [[stripe-client]] — Stripe integration
