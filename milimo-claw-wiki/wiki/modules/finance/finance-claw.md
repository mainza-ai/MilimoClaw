# Finance Claw

**Summary**: Main entry point for the Finance Claw. Initializes all components (filesystem, signal dispatcher, pricing engine, invoice manager, approval handler, payment risk scorer, payment monitor, revenue tracker, expense tracker, finance scheduler), wires them together, and starts the scheduler.

**Sources**: `milimo-blueprint/orchestrator/finance/finance_claw.py`

**Last updated**: 2026-07-03

**Tags**: #claw #finance #entry-point

---

## Overview

`FinanceClaw` is the main entry point for the Finance Claw. Handles all financial operations including invoicing, payments, revenue tracking, and expense management.

**File**: `orchestrator/finance/finance_claw.py`

---

## Key Components

| Component | Type | Purpose |
|-----------|------|---------|
| `FinanceFilesystemInit` | Filesystem | Initialize claw directory structure |
| `FinanceOperationalLog` | Logging | Structured action logging |
| `PaymentEventsLog` | Logging | Payment audit trail |
| `FinanceSignalDispatcher` | Communication | Inter-claw message routing |
| `PricingEngine` | Finance | Pricing queries and calculations |
| `InvoiceManager` | Finance | Invoice generation and management |
| `FinanceApprovalHandler` | Coordination | Financial approval workflow |
| `PaymentRiskScorer` | Finance | Client payment risk assessment |
| `PaymentMonitor` | Finance | Payment monitoring and tracking |
| `RevenueTracker` | Finance | Revenue tracking |
| `ExpenseTracker` | Finance | Expense logging with tax classification |
| `FinanceScheduler` | Scheduler | Periodic task scheduling |

---

## Startup Sequence

```python
claw = FinanceClaw(
    squad_id="my-squad",
    inference_client=inference,
    stripe_client=stripe,
    gateway=mesh_gateway,
    base_path=Path("/sandbox/finance")
)
claw.startup()
```

**Steps:**
1. Initialize filesystem
2. Validate Stripe configuration
3. Create operational log and payment events log
4. Initialize `FinanceSignalDispatcher`
5. Initialize all financial components
6. Start `FinanceScheduler`
7. Log startup entry

---

## Stripe Configuration

```python
# Environment variables
STRIPE_SECRET_KEY=sk_...  # or
STRIPE_API_KEY=sk_...
```

If not configured, Finance Claw uses a mock Stripe client with a warning logged.

> [!WARNING]
> **Audit Finding F5-1 [Critical]**: `stripe_client.py:L84` passes the Stripe secret key as `--api-key` on the subprocess command line. The key is visible to all local users via `ps` and `/proc/*/cmdline`. Fix: pass via `STRIPE_API_KEY` environment variable. See [[stripe-client]] for details and remediation.

---

## ⚠️ Audit Finding SA-1.4 [Medium]: Copy-Drift Between Core and Sandbox — FIXED 2026-07-04

| File | `test_mode` prop passed to `SpendApprovalHandler`? |
|---|---|
| `milimo-core/src/milimo_core/finance/finance_claw.py:L197-198` | ✅ Yes: `test_mode=_os.environ.get("MILIMO_SPEND_TEST_MODE", "true").lower() == "true"` |
| `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/finance_claw.py:L190-197` | ✅ **Fixed**: now matches core — passes `test_mode` from `MILIMO_SPEND_TEST_MODE` env var |

**Impact (pre-fix)**: The sandbox copy forced `SpendApprovalHandler` to use its default (`test_mode=True`) regardless of the `MILIMO_SPEND_TEST_MODE` environment variable. Real-payment flows could never be enabled in the sandbox.

**Fix applied**: Synced `finance_claw.py` from `milimo-core/` to `milimo-hermes-sandbox/`. Both copies now read `test_mode` from the `MILIMO_SPEND_TEST_MODE` environment variable.

Source: `milimo-audit-report.md`, Finding SA-1.4. Verified at HEAD `0c86b7b`.

---

## ⚠️ Regression Fix F-19 [Medium]: `queue_overdue_review` undefined `invoice_id` — FIXED 2026-07-06

**Pages**: `wiki/modules/finance/finance-claw.md`, `wiki/modules/finance/spend-handler.md`, `wiki/log.md`

**Source**: CI failure — `NameError: name 'invoice_id' is not defined` at `approval_handler.py:273` inside `FinanceApprovalHandler.queue_overdue_review()`.

**Impact**: Any code path that called `queue_overdue_review()` (invoices, overdue alerts) would crash immediately with a `NameError`, preventing the action from being queued and breaking downstream War Room rendering.

**Fix applied**: Restored the correct attribute access `invoice.invoice_id` at line 273 in both root and sandbox copies of `milimo-core/src/milimo_core/finance/approval_handler.py`. Also confirmed lines 152, 184, 209, 232, 253, 303 already use the correct local variable or attribute form for their respective scopes.

**Verification**:
- `python -m pytest milimo-blueprint/tests/test_finance_approval_handler.py` → `15 passed`
- No other `invoice_id` references in the file remain unresolved

---

## Inbound Message Handlers

| Message Type | Handler | Action |
|--------------|---------|--------|
| `pricing_query` | `PricingEngine.handle_pricing_query()` | Handle pricing query |
| `project_complete` | `InvoiceManager.generate_invoice()` | Generate invoice |
| `hold_release` | `PaymentMonitor.release_hold()` | Release held payment |
| `review_approve` | `ApprovalHandler.process_approval()` | Approve financial action |
| `review_reject` | `ApprovalHandler.process_rejection()` | Reject financial action |
| `assistant_query` | `_handle_assistant_query()` | Return claw status |
| `assistant_task` | `_handle_assistant_task()` | Accept task |

---

## Message Flow

### Invoice Generation
```
project_complete message
       ↓
InvoiceManager.generate_invoice()
       ↓
ApprovalHandler.queue_invoice_review()
       ↓
War Room reviews → approve/reject
```

### Payment Monitoring
```
PaymentMonitor tracks due dates
       ↓
If overdue → queue_review() for operator action
       ↓
On hold_release → release_hold() processes payment
```

---

## Component Access

```python
# Get component by name
pricing_engine = claw.get_component("pricing_engine")
invoice_manager = claw.get_component("invoice_manager")
payment_monitor = claw.get_component("payment_monitor")
```

---

## Properties

| Property | Type | Access |
|----------|------|--------|
| `is_initialized` | `bool` | Read-only |
| `squad_id` | `str` | Read-only |

---

## Related Pages

- [[finance-claw]] — This page
- [[finance-scheduler]] — Periodic task scheduling
- [[invoice-manager]] — Invoice generation
- [[pricing-engine]] — Pricing calculations
- [[payment-monitor]] — Payment tracking
- [[expense-tracker]] — Expense management
- [[revenue-tracker]] — Revenue tracking

---

## See Also

- `orchestrator/finance/finance_init.py` — Filesystem initialization
- `orchestrator/finance/signal_dispatcher.py` — Message routing
- `orchestrator/finance/approval_handler.py` — Approval workflow
