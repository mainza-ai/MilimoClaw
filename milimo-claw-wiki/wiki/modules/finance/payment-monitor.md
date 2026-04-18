# payment-monitor

**Summary**: Payment status checking and overdue detection.

**Sources**: `milimo-blueprint/orchestrator/finance/payment_monitor.py`

**Last updated**: 2026-04-14

**Tags**: #module #finance-claw

---

## Purpose

Monitors payment status via Stripe API and detects overdue invoices.

## Location

**File**: `milimo-blueprint/orchestrator/finance/payment_monitor.py`

## Key Classes

### PaymentMonitor

Monitors payment status and detects overdue.

```python
class PaymentMonitor:
    def __init__(
        self,
        fs: FinanceFilesystemInit,
        mesh: MeshClient,
        war_room: WarRoomClient,
    ):
        self._fs = fs
        self._mesh = mesh
        self._war_room = war_room

    def check_payment_status(self, invoice_id: str) -> PaymentStatus:
        """Check payment status via Stripe API."""
        pass

    def detect_overdue(self) -> List[OverdueInvoice]:
        """Find all overdue invoices."""
        pass

    def escalate_overdue(self, invoice: Invoice) -> None:
        """Escalate overdue to War Room and Ops Claw."""
        pass
```

## Payment Status Check

Runs every 24 hours for sent invoices:
1. Call Stripe API (GET only)
2. Check payment status
3. Update invoice location if needed
4. Send notifications if overdue

## Invoice Lifecycle

```
pending/ → approved/ → sent/ → paid/ or overdue/
```

## Overdue Detection

On payment overdue:
1. Move invoice: `sent/` → `overdue/`
2. Escalate War Room: REVIEW
3. Send `payment_overdue` to Ops Claw
4. Log to payment-events.log

## Repeat Overdue

If 2+ invoices overdue for same client:
- Escalate War Room: **HOLD**
- Flag client as high-risk in payment model

## Approved Endpoints

- `api.stripe.com` — GET for status checks
- `api.paypal.com` — GET for PayPal status
- `api.wise.com` — GET for transfer status

## Dependencies

- [[invoice-manager]] — Invoice lifecycle
- [[finance-claw]] — Parent coordination

## Related Pages

- [[finance-claw]] — Parent claw
- [[message-contracts]] — payment_overdue schema
- [[network-egress]] — Egress policy
