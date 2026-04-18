# Invoice Generator

**Summary**: Generates invoices from time tracking and project data.

**Sources**:
- `milimo-blueprint/orchestrator/finance/`

**Last updated**: 2026-04-15

**Tags**: #module #finance #invoices

---

## Overview

Invoice Generator creates client invoices based on:
- Tracked time from Ops Claw
- Project billing configuration
- Rate cards and discounts

---

## Key Functionality

### Generate Invoice

```python
invoice = invoice_generator.generate(
    project_id="proj_123",
    period_start="2026-04-01",
    period_end="2026-04-30",
    billing_type="hourly",  # or "fixed", "milestone"
)
```

### Invoice Structure

```python
@dataclass
class Invoice:
    invoice_id: str
    client_id: str
    project_id: str
    period_start: str
    period_end: str
    line_items: List[LineItem]
    subtotal: float
    tax: float
    total: float
    due_date: str
    status: str  # draft, sent, paid, overdue
```

---

## Billing Types

| Type | Description | Line Items |
|------|-------------|------------|
| Hourly | Time-based billing | Hours × Rate |
| Fixed | Project flat fee | Single line item |
| Milestone | Progress-based | Per milestone |

---

## Integration

### With Ops Claw

```python
# Ops sends time entries
signal_dispatcher.dispatch(
    Signal.TIME_ENTRIES_READY,
    {"project_id": project_id, "entries": entries}
)

# Finance receives and generates invoice
```

### With Stripe

```python
# After invoice generation
stripe_client.create_invoice(invoice)
stripe_client.send_invoice(invoice.invoice_id)
```

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/finance/invoices/drafts/` | Draft invoices |
| `/sandbox/finance/invoices/sent/` | Sent invoices |
| `/sandbox/finance/invoices/paid/` | Paid invoices |

---

## Related Pages

- [[finance-claw]] — Parent claw
- [[stripe-client]] — Stripe integration
- [[payment-risk-scorer]] — Payment risk assessment
