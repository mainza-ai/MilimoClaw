# Finance Claw

**Summary**: Financial nervous system that tracks every dollar and protects every margin — invoicing, pricing, and payment monitoring.

**Sources**:
- `raw/FINANCE_CLAW_SPEC.md`
- `milimo-blueprint/roles/finance-claw.yaml`

**Last updated**: 2026-06-30

**Tags**: #claw #finance

---

## Role

The Finance Claw is the **financial nervous system** of MilimoClaw. It tracks every dollar, protects margins, handles invoicing, and monitors payments.

## Sandbox

**Mount**: `/sandbox/.openclaw/milimo/claws/finance`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/.openclaw/milimo/claws/finance/` | Invoices, revenue, pricing | Read-write |
| `/sandbox/.openclaw/milimo/claws/analytics/reports/` | Intelligence reports | Read-only |

## What It Does

- Responds to pricing queries from Ops Claw within 10 minutes
- Generates invoices when projects complete (two-stage approval)
- Monitors payment status via Stripe API every 24 hours
- Detects and escalates overdue payments immediately
- Logs and tax-categorizes all expenses
- Generates weekly revenue summaries and sends totals to Analytics Claw
- Prepares quarterly tax summaries on quarter start dates
- **Manages agent-initiated purchases** via Stripe Link CLI (double-gated: War Room release → Link app approval)

## What It Cannot Do

- Communicate with clients directly — ever
- Read `/sandbox/.openclaw/milimo/claws/ops`, `/sandbox/.openclaw/milimo/claws/content`, or `/sandbox/.openclaw/milimo/claws/build`
- Spend money without **two independent human gates** (War Room HOLD release + Stripe Link app approval)
- Send any invoice without two-stage operator approval
- Include line items, client names, or invoice IDs in `revenue_summary` — totals only

## Two-Stage Invoice Approval

**NON-NEGOTIABLE**:

```
Stage 1 — REVIEW:
  Operator sees full invoice. Approving Stage 1 does NOT send the invoice.
  It moves the invoice to the HOLD queue only.

Stage 2 — HOLD release:
  The ONLY trigger for Stripe invoice transmission.
  No code path may send an invoice without an explicit HOLD release.

If Stage 1 approval triggers transmission: CRITICAL BUG.
```

## Approval Thresholds

| Action | Mode | Notes |
|--------|------|-------|
| Invoice generation (review content) | REVIEW | Stage 1: Review content |
| Invoice send (trigger transmission) | HOLD | Stage 2: Only trigger for transmission |
| Expense log entry | AUTO | Routine logging |
| Overdue payment alert (first) | REVIEW | First escalation |
| Overdue payment alert (repeat) | HOLD | Repeated escalation |
| Margin compression alert | REVIEW | Profitability warning |
| Rate optimization advisory | REVIEW | Pricing suggestions |
| Tax quarterly summary | AUTO | Routine reporting |
| Spend request (agent purchase) | REVIEW | Stage 1: Review purchase justification |
| Spend release (charge card) | HOLD | Stage 2: Release → link-cli → Link app |

## Scheduling

| Time | Action |
|------|--------|
| Daily 09:00 | Payment status check + overdue detection |
| Sunday 03:00 | Weekly revenue summary + evolution cycle |
| Quarter start | Tax prep summary (Jan 1, Apr 1, Jul 1, Oct 1) |

## Inter-Claw Messages

### Sent

| Message Type | To | Trigger | SLA |
|--------------|-----|---------|-----|
| `pricing_response` | Ops | Within 10 min of query | 10 minutes |
| `invoice_ready` | Ops | After Stage 1 REVIEW approve | Immediate |
| `payment_overdue` | Ops | Immediately on overdue detection | Immediate |
| `revenue_summary` | Analytics | Weekly + on payment | Sunday 03:00 |

### Received

| Message Type | From | Handler |
|--------------|------|---------|
| `pricing_query` | Ops | Generate pricing based on scope |
| `project_complete` | Ops | Initiate invoice generation |
| `revenue_anomaly` | Analytics | Investigate revenue patterns |
| `spend_request` | Any claw | Agent wants to buy something |
| `spend_review_decision` | War Room | Approve/edit/block a spend request |
| `spend_hold_decision` | War Room | Release/cancel a held spend |
| `assistant_query` | Assistant | Return status and state |
| `assistant_task` | Assistant | Execute finance-related tasks |

## Privacy Considerations

**ALL financial data is sensitive**. In production:
- All inference calls route to local NIM (NEMOCLAW_MODEL)
- No financial data sent to cloud APIs
- `revenue_summary` contains totals only — no line items, client names, or invoice IDs

## Key Modules

- [[finance-init]] — Filesystem initialization
- [[pricing-engine]] — Pricing calculation
- [[invoice-manager]] — Invoice generation (two-stage)
- [[payment-monitor]] — Stripe payment monitoring
- [[payment-risk-scorer]] — Payment risk assessment
- [[expense-tracker]] — Expense logging and categorization
- [[revenue-tracker]] — Revenue tracking
- [[approval-handler]] — Two-stage approval processing
- [[spend-handler]] — Agent-initiated purchase approval
- [[signal-dispatcher]] — Inter-claw message sending
- [[finance-scheduler]] — Scheduled tasks

## Evolution Tools

Tools that emerge autonomously over time:

```
Scope cost estimator v2 → Pricing floor guardian → Payment risk scorer v2 →
Margin tracker v2 → Tax category classifier v2 → Rate optimization advisor v2
```

## Evolution Schedule

**Sunday 03:00** — Finance Claw evolution cycle

Runs last — uses revenue summary just generated.

## Spec Document

Full specification: `raw/FINANCE_CLAW_SPEC.md`

## Related Pages

- [[message-contracts]] — Message schemas
- [[sequencing-rules]] — Pricing before brief rule
- [[approval-thresholds]] — Two-stage approval
- [[ops-claw]] — Pricing queries and invoice coordination
- [[analytics-claw]] — Revenue summaries
- [[privacy-router]] — All data routed locally

## See Also

- Implementation prompt: `milimo-claw-docs/prompts/FINANCE_CLAW_IMPLEMENTATION_PROMPT.md`
- Policy: `milimo-blueprint/policies/finance-sandbox.yaml`
- Tests: `milimo-blueprint/tests/test_finance_claw*.py`
