# invoice-manager

**Summary**: Invoice generation with two-stage approval enforcement.

**Sources**: `milimo-blueprint/orchestrator/finance/invoice_manager.py`

**Last updated**: 2026-04-14

**Tags**: #module #finance-claw

---

## Purpose

Generates invoices when projects complete. Enforces two-stage approval — Stage 1 REVIEW does NOT send, only Stage 2 HOLD release triggers Stripe transmission.

## Location

**File**: `milimo-blueprint/orchestrator/finance/invoice_manager.py`

## Key Classes

### InvoiceManager

Generates and manages invoices.

```python
class InvoiceManager:
    def __init__(
        self,
        fs: FinanceFilesystemInit,
        inference_client: InferenceClient,
        dispatcher: FinanceSignalDispatcher,
        payment_risk_scorer: PaymentRiskScorer,
        operational_log: FinanceOperationalLog,
        payment_events_log: PaymentEventsLog,
    ):
        pass

    def generate_invoice(
        self,
        project_id: str,
        client_id: str,
        delivered_at: str,
    ) -> Invoice:
        """Generate invoice and queue for Stage 1 review."""
        pass
```

## ⚠️ Audit Findings — Verified Limitations

| Finding | Severity | Location | Gap |
|---|---|---|---|
| **SA3-5** | Medium | `invoice_manager.py:L444-463` | `send_invoice()` calls `stripe_client.create_invoice()` without first checking `invoice.stripe_invoice_id`. If the Stage 2 release handler crashes after writing the Stripe return ID but before the local file write, a retry creates a duplicate Stripe invoice. Fix: check `if invoice.stripe_invoice_id: return` before calling Stripe create APIs. |

## Two-Stage Approval

**CRITICAL**: Two-stage approval is NON-NEGOTIABLE.

```
Stage 1 — REVIEW (queue_invoice_review):
  - Operator sees full invoice content
  - Approving moves to HOLD queue only
  - Does NOT send to Stripe

Stage 2 — HOLD release:
  - Only trigger for Stripe transmission
  - No other code path can send invoice

BUG: If Stage 1 approve sends to Stripe
```

## Invoice Generation Flow

```python
def generate_invoice(self, project_id, client_id, delivered_at):
    # 1. Calculate invoice amount
    amount = self._calculate_amount(project_id)

    # 2. Create invoice object
    invoice = Invoice(
        invoice_id=str(uuid4()),
        project_id=project_id,
        client_id=client_id,
        amount=amount,
        status="stage_1_pending",
    )

    # 3. Save to invoices directory
    self._save_invoice(invoice)

    # 4. Queue for Stage 1 review (NOT sent)
    self._approval_handler.queue_invoice_review(invoice)

    return invoice
```

## Invoice States

| State | Description |
|-------|-------------|
| `stage_1_pending` | Awaiting REVIEW approval |
| `stage_1_approved` | REVIEW approved, in HOLD queue |
| `hold_released` | HOLD released, sent to Stripe |
| `sent` | Transmitted to Stripe |
| `paid` | Payment confirmed |

## Dependencies

- [[pricing-engine]] — Invoice amount calculation
- [[payment-risk-scorer]] — Payment risk assessment
- [[approval-handler]] — Two-stage approval

## Related Pages

- [[finance-claw]] — Parent claw
- [[approval-thresholds]] — Two-stage rules
- [[payment-monitor]] — Payment tracking
