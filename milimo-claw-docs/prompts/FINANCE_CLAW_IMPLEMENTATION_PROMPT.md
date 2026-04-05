> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — FINANCE CLAW IMPLEMENTATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. FINANCE_CLAW_AUDIT_REPORT.md           (the gap analysis)
#   2. MILIMO_CLAW_FINANCE_CLAW_SPEC.md       (the ground truth spec)
#   3. finance-claw.yaml                       (role blueprint — EXISTS)
#   4. finance-sandbox.yaml                    (sandbox policy — EXISTS)
#   5. contracts.py                            (message types — EXISTS)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert Python engineer building the Finance Claw for Milimo Claw
— a multi-agent autonomous hustle platform built on NVIDIA NemoClaw.

The audit confirms the Finance Claw is 0% implemented. The configuration
files exist (finance-claw.yaml, finance-sandbox.yaml, contracts.py) but
no Python orchestration code has been written. You are building everything
from scratch.

The spec document is the ground truth. The audit defines what must be built.
This prompt defines exactly how to build it.

---

## CONTEXT — THE SYSTEM YOU ARE BUILDING INTO

The Finance Claw is the financial nervous system of the Milimo Claw mesh.
It receives project completion signals from the Ops Claw, generates and
manages invoices, monitors payments, tracks expenses, and publishes weekly
revenue intelligence to the Analytics Claw.

**This is the most financially sensitive claw in the entire system.**
Every design decision must reflect that.

**Existing integrations that depend on Finance Claw:**
  - `contracts.py` defines Finance Claw message types — handlers missing
  - `analytics/signal_processor.py` expects `revenue_summary` from Finance
  - `analytics/anomaly_detector.py` sends `revenue_anomaly` to Finance
  - Ops Claw (when built) will send `pricing_query` and `project_complete`

**Plugin structure:**
  - Python orchestrator:  `milimo-blueprint/orchestrator/`
  - New Finance files:    `milimo-blueprint/orchestrator/finance/`
  - Role blueprint:       `milimo-blueprint/roles/finance-claw.yaml`
  - Sandbox policy:       `milimo-blueprint/policies/finance-sandbox.yaml`
  - Operator config:      `~/.milimo/config.json`

**Operator:** Mainza Kangombe — senior systems architect, Python 3.11+.
Production-quality code only. No stubs. No TODOs. No placeholder comments.
Every function must be complete and runnable.

---

## DEVELOPMENT PHASE CONSTRAINTS

**Inference:** ALL inference routes to cloud (Nemotron 120B via NVIDIA
Cloud API). Do NOT implement local NIM routing. Do NOT enforce privacy
routing. DO log `data_type` as a field on every single inference call —
this is mandatory, not optional. The data_type field is the only thing
that enables future routing enforcement without rewriting call sites.

```python
# Every inference call must follow this pattern:
response = self.inference_client.complete(
    prompt=prompt,
    data_type="scope_cost_estimation",  # ALWAYS INCLUDE — never omit
    max_tokens=800
)
```

**Sandbox isolation applies in development.** Finance Claw must only
write to `/sandbox/finance/` and only receive other claws' data via
typed inter-claw messages. The Landlock restriction is kernel-level.

**Stripe test mode mandatory.** All Stripe API calls during development
must use Stripe test credentials. No live Stripe API calls during dev.
The implementation must read Stripe credentials from environment variables:
  `STRIPE_API_KEY` — use test key (starts with sk_test_)
  `STRIPE_WEBHOOK_SECRET` — test webhook secret

**Standards (non-negotiable):**
  - Python 3.11+, full type hints, docstrings on every class and method
  - pathlib.Path only — never os.path string concatenation
  - PyYAML safe_load only — never yaml.load()
  - Append-only log files using file locking for thread safety
  - Atomic file writes for summaries: write temp → rename on success
  - Never silently swallow exceptions — log and re-raise or typed error
  - Tests: pytest, full coverage for every class and method

---

## THE MOST CRITICAL REQUIREMENT — READ THIS FIRST

**The two-stage invoice approval is non-negotiable.**

An invoice must NEVER transmit to a client without two separate,
explicit operator actions:

```
Stage 1 — REVIEW:
  Operator sees full invoice in War Room.
  Approving Stage 1 does NOT send the invoice.
  Approving Stage 1 moves the invoice to the HOLD queue only.

Stage 2 — HOLD release:
  A separate, explicit HOLD release is the trigger for transmission.
  This is the only action that causes an invoice to be sent via Stripe.

If Stage 1 approval causes invoice transmission: CRITICAL BUG.
If any code path sends an invoice without both stages: CRITICAL BUG.
```

Test this before anything else. Every other Finance Claw feature is
secondary to the correctness of the two-stage approval flow.

---

## PHASE 1 — CORE INFRASTRUCTURE
## Build in exact task order. Do not proceed to Phase 2 until all
## Phase 1 tests pass.

---

### TASK 1.1 — Finance Filesystem Initialization

**New file:** `milimo-blueprint/orchestrator/finance/finance_init.py`

```python
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal
import json

BASE = Path("/sandbox/finance")

REQUIRED_DIRS = [
    "revenue/history",
    "invoices/pending",
    "invoices/approved",
    "invoices/sent",
    "invoices/paid",
    "invoices/overdue",
    "expenses/categories",
    "pricing/estimates",
    "pricing/history",
    "tax/quarterly",
    "tax/annual",
    "logs",
]

REQUIRED_FILES = {
    "revenue/weekly-summary.json":  {"week_total": 0, "invoices_paid": 0,
                                     "invoices_pending": 0,
                                     "week_over_week_pct": 0.0,
                                     "last_updated": None},
    "revenue/monthly-summary.json": {"month_total": 0, "invoices_paid": 0,
                                     "last_updated": None},
    "revenue/annual-summary.json":  {"year_total": 0, "invoices_paid": 0,
                                     "last_updated": None},
    "pricing/rules.json":           {"default_hourly_rate": 0,
                                     "floor_multiplier": 0.8,
                                     "ceiling_multiplier": 1.5,
                                     "scope_weights": {},
                                     "last_updated": None},
    "tax/categories.json":          {"income_categories": [],
                                     "expense_categories": [],
                                     "last_updated": None},
    "expenses/log.jsonl":           None,   # JSONL — create empty
    "logs/operational.log":         None,
    "logs/decisions.log":           None,
    "logs/payment-events.log":      None,
}

@dataclass
class InitResult:
    created_dirs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0

@dataclass
class ValidationResult:
    missing_dirs: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_dirs and not self.missing_files

class FinanceFilesystemInit:
    """
    Creates and validates the full /sandbox/finance/ filesystem structure.
    Idempotent — safe to call on every claw startup.
    """

    def initialize(self) -> InitResult: ...
    # Create all REQUIRED_DIRS
    # Create all REQUIRED_FILES with initial JSON content
    # Never overwrite existing files
    # Return full accounting in InitResult

    def validate(self) -> ValidationResult: ...
    # Check all required paths exist
    # Return ValidationResult — never raise, never create

    def get_invoice_path(
        self,
        status: Literal["pending","approved","sent","paid","overdue"],
        invoice_id: str
    ) -> Path: ...

    def get_pricing_estimate_path(self, project_id: str) -> Path: ...
    def get_tax_quarterly_path(self, year: int, quarter: int) -> Path: ...
```

Also implement `FinanceOperationalLog`:

```python
from dataclasses import dataclass
import fcntl

@dataclass
class FinanceLogEntry:
    timestamp: str       # ISO 8601
    action_type: str     # pricing_query_answered, invoice_generated, etc.
    entity_id: str       # invoice_id, project_id, expense_id
    amount: float | None # financial amount if relevant
    outcome: str         # success, failed, pending, escalated
    details: dict

class FinanceOperationalLog:
    """Append-only structured log. Thread-safe via file locking."""

    def __init__(self, log_path: Path): ...

    def append(self, entry: FinanceLogEntry) -> None: ...
    # JSON line append with fcntl file locking

    def read_recent(
        self,
        days: int = 30,
        action_type: str | None = None
    ) -> list[FinanceLogEntry]: ...

    def count_by_type(self, action_type: str, days: int = 30) -> int: ...
```

Also implement `PaymentEventsLog`:

```python
@dataclass
class PaymentEvent:
    timestamp: str
    event_type: str     # invoice_sent, payment_received, payment_overdue,
                        # repeat_overdue_flagged, retry_attempted
    invoice_id: str
    client_id: str
    amount: float
    details: dict

class PaymentEventsLog:
    """Append-only payment event log. Separate from operational log."""

    def __init__(self, log_path: Path): ...
    def append(self, event: PaymentEvent) -> None: ...
    def read_recent(self, days: int = 90) -> list[PaymentEvent]: ...
    def get_client_history(self, client_id: str) -> list[PaymentEvent]: ...
    def count_overdue_by_client(self, client_id: str) -> int: ...
```

Write pytest tests: directory creation, idempotent re-run, validation
pass/fail, log append and read, payment events client history query,
concurrent write safety for both logs.

---

### TASK 1.2 — Signal Dispatcher

**New file:** `milimo-blueprint/orchestrator/finance/signal_dispatcher.py`

Build the outbound message system first — every other component needs it.

```python
class FinanceSignalDispatcher:
    """
    Sends all outbound messages from the Finance Claw to other claws.
    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to operational.log.
    Never raises on dispatch failure — logs error and continues.
    """

    def send_pricing_response(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float,
        scope_notes: str,
        data_quality: str = "complete"   # "complete" | "estimated"
    ) -> None: ...
    # Send pricing_response to Ops Claw
    # data_quality="estimated" when no historical data exists
    # Log: action_type="pricing_response_sent"

    def send_invoice_ready(
        self,
        project_id: str,
        client_id: str,
        amount: float,
        invoice_id: str,
        due_date: str       # ISO date
    ) -> None: ...
    # Send invoice_ready to Ops Claw
    # Fired AFTER Stage 1 REVIEW approval — before Stage 2 HOLD
    # Ops Claw uses this to update client record
    # Log: action_type="invoice_ready_sent"

    def send_payment_overdue(
        self,
        client_id: str,
        invoice_id: str,
        days_overdue: int,
        amount: float,
        risk_level: str     # "low" | "medium" | "high"
    ) -> None: ...
    # Send payment_overdue to Ops Claw
    # Fired IMMEDIATELY when due date passes — no weekly wait
    # Log: action_type="payment_overdue_sent"

    def send_revenue_summary(
        self,
        week_total: float,
        week_over_week_pct: float,
        invoices_paid: int,
        invoices_pending: int
    ) -> None: ...
    # Send revenue_summary to Analytics Claw
    # TOTALS ONLY — never include line items, client names, invoice IDs
    # Log: action_type="revenue_summary_sent"

    def _send(
        self,
        message_type: str,
        recipient_role: str,
        payload: dict
    ) -> None: ...
    # Core send via mesh gateway
    # Includes message_id (UUID), timestamp, sender_role="finance"
    # On exception: log error, do not raise
```

Write pytest tests: each send method produces correct message_type and
recipient, revenue_summary payload contains no line items or client names,
dispatch failure logged but not raised, every send logged to operational.log.

---

### TASK 1.3 — Pricing Engine

**New file:** `milimo-blueprint/orchestrator/finance/pricing_engine.py`

The pricing engine handles the 10-minute SLA for pricing queries.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import time

@dataclass
class PricingEstimate:
    project_id: str
    scope_description: str
    complexity_estimate: str    # "low" | "medium" | "high" | "complex"
    deadline: str               # ISO date
    estimated_hours: float
    recommended_rate: float
    floor_price: float
    ceiling_price: float
    scope_notes: str
    data_quality: str           # "complete" | "estimated"
    history_projects_used: int  # how many past projects calibrated this
    generated_at: str           # ISO timestamp

class PricingEngine:
    """
    Handles pricing queries from the Ops Claw.

    SLA: Must respond within 10 minutes.
    If estimation takes longer: respond with rough estimate flagged
    data_quality="estimated". Never timeout silently.

    Calibrates estimates against historical project data from
    /sandbox/finance/pricing/history/.
    """

    RESPONSE_TIMEOUT_SECONDS = 540   # 9 minutes — gives 1 min margin

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        inference_client: Any,
        dispatcher: FinanceSignalDispatcher,
        operational_log: FinanceOperationalLog
    ): ...

    def handle_pricing_query(self, message: dict) -> PricingEstimate: ...
    # 1. Extract: project_id, scope_description, complexity_estimate, deadline
    # 2. Load pricing rules from /sandbox/finance/pricing/rules.json
    # 3. Load historical estimates from pricing/history/ (filter similar scope)
    # 4. Generate estimate via inference:
    #    data_type="scope_cost_estimation"
    #    Prompt includes: scope, complexity, deadline, historical calibration data
    # 5. Apply floor/ceiling from rules.json
    # 6. Write estimate to pricing/estimates/{project_id}.json
    # 7. Send pricing_response via dispatcher (floor, ceiling, scope_notes)
    # 8. Log: action_type="pricing_query_answered"
    # 9. Return PricingEstimate
    #
    # If inference fails or times out:
    #   Use rule-based fallback estimate
    #   Set data_quality="estimated"
    #   Still respond — never miss the SLA

    def load_pricing_rules(self) -> dict: ...
    # Read pricing/rules.json
    # Return dict with default_hourly_rate, floor_multiplier,
    # ceiling_multiplier, scope_weights
    # Return defaults if file is empty or missing keys

    def load_historical_calibration(
        self,
        complexity: str,
        max_projects: int = 10
    ) -> list[dict]: ...
    # Read pricing/history/*.json
    # Filter to similar complexity
    # Return list of {estimated_hours, actual_hours, accuracy_pct}
    # Used to calibrate current estimate

    def _rule_based_fallback(
        self,
        scope_description: str,
        complexity_estimate: str,
        rules: dict
    ) -> PricingEstimate: ...
    # Pure rule-based estimate when inference unavailable
    # complexity_to_hours = {low: 8, medium: 20, high: 40, complex: 80}
    # Multiply by default_hourly_rate
    # Apply floor/ceiling multipliers
    # data_quality = "estimated"

    def _build_estimation_prompt(
        self,
        scope: str,
        complexity: str,
        deadline: str,
        calibration_data: list[dict],
        rules: dict
    ) -> str: ...
    # Structured prompt for scope cost estimation
    # Include calibration data as examples if available

    def update_actual_cost(
        self,
        project_id: str,
        actual_hours: float,
        actual_cost: float
    ) -> None: ...
    # Write actual vs estimated to pricing/history/{project_id}.json
    # Called when project delivers — used for future calibration
```

Write pytest tests: pricing query within 10 minutes (mock inference),
rule-based fallback when inference unavailable, floor/ceiling applied
correctly, historical calibration loaded and used in prompt, estimate
written to correct path, pricing_response dispatched, 10-minute SLA
enforced (mock slow inference to trigger fallback).

---

### TASK 1.4 — Invoice Manager

**New file:** `milimo-blueprint/orchestrator/finance/invoice_manager.py`

The invoice manager handles the full invoice lifecycle.
The two-stage approval is implemented here.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Any
import uuid
import json
from datetime import datetime, timedelta

@dataclass
class InvoiceLineItem:
    description: str
    quantity: float
    unit_price: float
    total: float

@dataclass
class Invoice:
    invoice_id: str
    project_id: str
    client_id: str
    line_items: list[InvoiceLineItem]
    subtotal: float
    total: float
    currency: str = "USD"
    payment_terms: str = "Net 14"
    due_date: str = ""            # ISO date — set on generation
    payment_risk_score: float = 0.0   # 0–10, higher = safer
    payment_risk_level: str = "unknown"  # low | medium | high
    status: str = "pending"       # pending | approved | sent | paid | overdue
    stripe_invoice_id: str | None = None
    generated_at: str = ""
    approved_at: str | None = None
    sent_at: str | None = None
    paid_at: str | None = None

class InvoiceManager:
    """
    Manages the full invoice lifecycle.

    CRITICAL: Two-stage approval is non-negotiable.
    Stage 1 (REVIEW approve) → moves to approved/ — does NOT send
    Stage 2 (HOLD release)   → transmits via Stripe — only send trigger

    Any code path that sends an invoice without HOLD release is a bug.
    """

    DEFAULT_PAYMENT_TERMS_DAYS = 14

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        inference_client: Any,
        dispatcher: FinanceSignalDispatcher,
        payment_risk_scorer,      # PaymentRiskScorer instance
        operational_log: FinanceOperationalLog,
        payment_events_log: PaymentEventsLog
    ): ...

    def generate_invoice(
        self,
        project_id: str,
        client_id: str,
        delivered_at: str
    ) -> Invoice: ...
    # 1. Load pricing estimate from pricing/estimates/{project_id}.json
    # 2. Load any scope notes from the estimate
    # 3. Generate invoice line items via inference:
    #    data_type="invoice_generation"
    #    Prompt: project scope, estimated cost, delivery confirmation
    #    Output: structured line items with descriptions
    # 4. Calculate: subtotal, total, due_date (today + 14 days)
    # 5. Score payment risk for this client
    # 6. Assign invoice_id (UUID)
    # 7. Write to invoices/pending/{invoice_id}.json
    # 8. Queue War Room REVIEW action via approval_handler
    # 9. Log: action_type="invoice_generated"
    # 10. Return Invoice

    def handle_stage1_approve(self, invoice_id: str) -> Invoice: ...
    # Called when operator approves Stage 1 REVIEW
    # 1. Load invoice from invoices/pending/{invoice_id}.json
    # 2. Update status to "approved", approved_at = now
    # 3. Move file: pending/ → approved/{invoice_id}.json
    # 4. Remove from pending/
    # 5. Queue War Room HOLD action (Stage 2)
    # 6. Send invoice_ready to Ops Claw via dispatcher
    # 7. Log: action_type="invoice_stage1_approved"
    # DO NOT SEND INVOICE HERE. HOLD QUEUE ONLY.

    def handle_stage1_edit(
        self,
        invoice_id: str,
        edited_line_items: list[dict],
        edited_total: float
    ) -> Invoice: ...
    # Load from pending/, apply edits, recalculate total
    # Save edited version back to pending/ (re-queue REVIEW)
    # Log: action_type="invoice_edited"

    def handle_stage1_block(self, invoice_id: str, reason: str) -> None: ...
    # Move invoice from pending/ to a discarded state
    # Do not delete — archive with blocked status
    # Log: action_type="invoice_blocked", details={reason}

    def handle_stage2_hold_release(
        self,
        invoice_id: str,
        stripe_client: Any
    ) -> Invoice: ...
    # THIS IS THE ONLY PLACE AN INVOICE IS TRANSMITTED.
    # 1. Load invoice from invoices/approved/{invoice_id}.json
    # 2. Verify status == "approved" — raise if not
    # 3. Create Stripe invoice via Stripe API
    # 4. Send Stripe invoice to client
    # 5. Update invoice: status="sent", sent_at=now,
    #    stripe_invoice_id=stripe_id
    # 6. Move file: approved/ → sent/{invoice_id}.json
    # 7. Log to payment-events.log: invoice_sent
    # 8. Log: action_type="invoice_sent"
    # On Stripe API failure: keep in approved/, retry logic in payment_monitor

    def _build_invoice_prompt(
        self,
        project_id: str,
        scope_description: str,
        total_amount: float,
        delivered_at: str
    ) -> str: ...
    # Structured prompt for invoice line item generation
    # Output must be parseable as structured line items

    def _parse_invoice_line_items(
        self,
        inference_output: str
    ) -> list[InvoiceLineItem]: ...
    # Parse inference output into InvoiceLineItem list
    # Fallback: single line item "Services rendered: {scope}" if parse fails
    # Never return empty line items — always at least one item

    def get_pending_invoices(self) -> list[Invoice]: ...
    def get_approved_invoices(self) -> list[Invoice]: ...
    def get_sent_invoices(self) -> list[Invoice]: ...
    def load_invoice(self, invoice_id: str, status: str) -> Invoice: ...
```

Write pytest tests:
- generate_invoice writes to pending/ and queues REVIEW
- handle_stage1_approve moves to approved/ — DOES NOT SEND
- handle_stage2_hold_release calls Stripe API (mock) and moves to sent/
- handle_stage1_block archives with reason
- handle_stage2 raises if invoice not in approved/ status
- line item parsing fallback on malformed inference output
- invoice_id is always a valid UUID
- due_date always 14 days from generation
- Stage 1 approve then verify no Stripe call made (critical test)

---

### TASK 1.5 — Two-Stage Approval Handler

**New file:** `milimo-blueprint/orchestrator/finance/approval_handler.py`

The approval handler is the bridge between the War Room and the
Invoice Manager. It enforces the two-stage flow at the UI layer.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class ApprovalAction:
    action_id: str
    invoice_id: str
    stage: Literal["review", "hold"]
    action_type: Literal["approve", "edit", "block", "release", "cancel"]
    timestamp: str
    operator: str
    details: dict

class FinanceApprovalHandler:
    """
    Handles all War Room approval interactions for Finance Claw actions.

    Enforces two-stage invoice approval.
    Stage 1 (REVIEW): content review — approve moves to HOLD, never sends
    Stage 2 (HOLD): transmission gate — release triggers Stripe send

    Every decision logged to decisions.log.
    """

    def __init__(
        self,
        invoice_manager: InvoiceManager,
        operational_log: FinanceOperationalLog
    ): ...

    def queue_invoice_review(self, invoice: Invoice) -> str: ...
    # Add invoice to War Room REVIEW queue
    # Returns action_id
    # War Room card shows:
    #   Client, project description, line items, total,
    #   due date, payment risk score and level
    # Available actions: APPROVE, EDIT, BLOCK

    def queue_invoice_hold(self, invoice: Invoice) -> str: ...
    # Add approved invoice to War Room HOLD queue
    # Returns action_id
    # War Room card shows:
    #   "Invoice approved — ready to send to {client_id}"
    #   Amount and due date
    #   Warning: "This will transmit the invoice via Stripe"
    # Available actions: RELEASE HOLD (sends), CANCEL

    def handle_review_approve(self, action_id: str) -> None: ...
    # Called on REVIEW approve
    # Delegates to invoice_manager.handle_stage1_approve()
    # Queues HOLD action (Stage 2)
    # Logs to decisions.log: REVIEW_APPROVED

    def handle_review_edit(
        self,
        action_id: str,
        edited_line_items: list[dict],
        edited_total: float
    ) -> None: ...
    # Delegates to invoice_manager.handle_stage1_edit()
    # Re-queues REVIEW with edited invoice
    # Logs to decisions.log: REVIEW_EDITED

    def handle_review_block(self, action_id: str, reason: str) -> None: ...
    # Delegates to invoice_manager.handle_stage1_block()
    # Logs to decisions.log: REVIEW_BLOCKED

    def handle_hold_release(self, action_id: str) -> None: ...
    # Called on HOLD release — THIS SENDS THE INVOICE
    # Delegates to invoice_manager.handle_stage2_hold_release()
    # Logs to decisions.log: HOLD_RELEASED

    def handle_hold_cancel(self, action_id: str) -> None: ...
    # Cancel the HOLD — invoice stays in approved/ for future send
    # Does NOT delete — just removes from HOLD queue
    # Logs to decisions.log: HOLD_CANCELLED

    def queue_overdue_review(
        self,
        invoice: Invoice,
        days_overdue: int
    ) -> str: ...
    # REVIEW action for first overdue
    # Shows: client, invoice amount, days overdue, risk level
    # Suggested actions: send reminder, escalate, write off

    def queue_overdue_hold(
        self,
        invoice: Invoice,
        days_overdue: int,
        overdue_count: int
    ) -> str: ...
    # HOLD action for repeat overdue (2+ invoices)
    # Requires explicit operator action — cannot be auto-dismissed
    # Shows: client, total outstanding amount, overdue history

    def queue_margin_alert(
        self,
        project_id: str,
        expected_margin_pct: float,
        actual_margin_pct: float
    ) -> str: ...
    # REVIEW action for margin compression
    # Shows margin gap, no immediate action required

    def queue_rate_recommendation(
        self,
        recommendation: str,
        suggested_rate: float,
        current_rate: float
    ) -> str: ...
    # REVIEW action for rate optimization
    # Recommendation only — operator decides

    def log_decision(
        self,
        action: ApprovalAction
    ) -> None: ...
    # Append to logs/decisions.log
```

Write pytest tests: queue_invoice_review creates REVIEW (not HOLD),
handle_review_approve creates HOLD — Stripe NOT called, handle_hold_release
calls Stripe (mock) — this is the ONLY test where Stripe fires,
handle_hold_cancel preserves invoice in approved/, all decisions logged,
overdue_hold queued on second overdue (count >= 2).

---

## PHASE 2 — PAYMENT AND REVENUE
## Complete all Phase 1 tests before starting Phase 2.

---

### TASK 2.1 — Payment Risk Scorer

**New file:** `milimo-blueprint/orchestrator/finance/payment_risk_scorer.py`

```python
from dataclasses import dataclass

@dataclass
class PaymentRiskScore:
    client_id: str
    score: float              # 0–10, higher = safer payer
    risk_level: str           # "low" (7–10) | "medium" (4–7) | "high" (0–4)
    factors: list[str]        # plain English risk factors
    invoices_analyzed: int
    on_time_rate: float        # 0.0–1.0
    avg_days_late: float
    overdue_count: int
    data_quality: str         # "complete" | "estimated" | "no_history"

class PaymentRiskScorer:
    """
    Scores client payment risk before invoice is shown to operator.

    Reads from payment-events.log — client's historical payment behavior.
    No external API calls — purely internal signal.
    New clients with no history get score=5.0 (neutral), data_quality="no_history".
    """

    def score(self, client_id: str) -> PaymentRiskScore: ...
    # 1. Load client payment history from payment-events.log
    # 2. If no history: return neutral score (5.0, "medium", "no_history")
    # 3. Calculate: on_time_rate, avg_days_late, overdue_count
    # 4. Generate score via inference:
    #    data_type="payment_risk_scoring"
    #    Prompt includes calculated metrics
    # 5. Classify risk_level from score
    # 6. Return PaymentRiskScore

    def _calculate_payment_metrics(
        self,
        payment_history: list
    ) -> dict: ...
    # Calculate: on_time_rate, avg_days_late, overdue_count
    # from payment-events.log records for this client

    def _classify_risk_level(self, score: float) -> str: ...
    # 7.0–10.0: "low"
    # 4.0–7.0:  "medium"
    # 0.0–4.0:  "high"
```

Write pytest tests: no history returns neutral score, on-time payer
scores high (8+), repeat late payer scores low (<4), risk_level
classified correctly at boundaries, data_quality="no_history" for
new clients.

---

### TASK 2.2 — Payment Monitor

**New file:** `milimo-blueprint/orchestrator/finance/payment_monitor.py`

```python
from dataclasses import dataclass
from typing import Any
import stripe
from datetime import datetime, timedelta

@dataclass
class PaymentStatus:
    invoice_id: str
    stripe_invoice_id: str
    status: str               # "open" | "paid" | "void" | "uncollectible"
    amount_paid: float
    amount_due: float
    due_date: str
    days_overdue: int

class PaymentMonitor:
    """
    Monitors payment status for all sent invoices via Stripe API.

    Checks every 24 hours for each sent invoice.
    On payment: moves to paid/, updates revenue summaries, sends signal.
    On overdue: moves to overdue/, escalates to War Room, notifies Ops Claw.
    On repeat overdue: escalates to HOLD.

    All Stripe calls use test credentials during development.
    All external API calls logged to payment-events.log.
    """

    CHECK_INTERVAL_HOURS = 24
    STRIPE_RETRY_INTERVAL_MINUTES = 30
    STRIPE_MAX_RETRY_HOURS = 24

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        stripe_client: Any,
        approval_handler: FinanceApprovalHandler,
        dispatcher: FinanceSignalDispatcher,
        revenue_tracker,        # RevenueTracker instance
        operational_log: FinanceOperationalLog,
        payment_events_log: PaymentEventsLog
    ): ...

    def check_all_sent_invoices(self) -> list[PaymentStatus]: ...
    # Load all invoices from invoices/sent/
    # Check payment status for each via Stripe API
    # Process status changes
    # Log all API calls to payment-events.log
    # Return list of current statuses

    def check_invoice_status(
        self,
        invoice: Invoice
    ) -> PaymentStatus: ...
    # GET to Stripe API for stripe_invoice_id
    # Log API call to payment-events.log
    # Return PaymentStatus

    def process_payment_received(self, invoice: Invoice) -> None: ...
    # 1. Update invoice: status="paid", paid_at=now
    # 2. Move: sent/ → paid/{invoice_id}.json
    # 3. Log payment-events.log: payment_received
    # 4. Call revenue_tracker.record_payment(invoice)
    # 5. Log operational.log: action_type="payment_received"

    def process_payment_overdue(self, invoice: Invoice) -> None: ...
    # 1. Update invoice: status="overdue"
    # 2. Move: sent/ → overdue/{invoice_id}.json
    # 3. Log payment-events.log: payment_overdue
    # 4. Calculate days_overdue
    # 5. Calculate risk_level from overdue count for this client
    # 6. Send payment_overdue to Ops Claw via dispatcher
    # 7. Check overdue count for this client:
    #    First overdue (count=1): queue REVIEW in War Room
    #    Repeat overdue (count>=2): queue HOLD in War Room
    # 8. Log operational.log: action_type="payment_overdue"

    def check_and_flag_overdue(self) -> list[Invoice]: ...
    # Called daily — check all sent invoices for overdue
    # Invoice is overdue when: due_date < today AND status == "sent"
    # Process each overdue invoice

    def retry_failed_stripe_send(
        self,
        invoice: Invoice
    ) -> bool: ...
    # Called when initial Stripe send failed (invoice stuck in approved/)
    # Retry every 30 minutes for up to 24 hours
    # After 24 hours: escalate to War Room REVIEW
    # Returns True if send succeeded, False if still failing
    # Log every attempt to payment-events.log

    def _is_overdue(self, invoice: Invoice) -> bool: ...
    # due_date < today AND status == "sent"
```

Write pytest tests: payment received moves invoice to paid/ and triggers
revenue update, overdue detection fires on correct date, first overdue
queues REVIEW not HOLD, second overdue queues HOLD not REVIEW, Stripe
retry logic (mock API failures), 24-hour retry exhaustion escalates
to War Room, API calls logged to payment-events.log.

---

### TASK 2.3 — Revenue Tracker

**New file:** `milimo-blueprint/orchestrator/finance/revenue_tracker.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
from datetime import datetime, timedelta, date

@dataclass
class RevenueSummary:
    week_start: str           # ISO date (Monday)
    week_total: float
    week_over_week_pct: float
    invoices_paid: int
    invoices_pending: int
    pipeline_value: float     # sum of all sent invoices not yet paid
    last_updated: str         # ISO timestamp

class RevenueTracker:
    """
    Tracks all revenue and maintains summary files.

    Updates weekly-summary.json on every payment received.
    Generates full weekly summary every Sunday at 03:00.
    Sends revenue_summary to Analytics Claw after each update.
    Runs margin analysis and rate optimization checks weekly.
    All inference calls log data_type.
    """

    def record_payment(self, invoice: Invoice) -> None: ...
    # Called when payment_monitor detects a payment
    # 1. Load weekly-summary.json
    # 2. Add payment to week_total
    # 3. Increment invoices_paid
    # 4. Write daily snapshot to revenue/history/{today}.json
    # 5. Update weekly-summary.json atomically (temp → rename)
    # 6. Update monthly and annual summaries
    # 7. Send revenue_summary to Analytics Claw via dispatcher
    # 8. Log: action_type="payment_recorded"

    def generate_weekly_summary(self) -> RevenueSummary: ...
    # Full weekly aggregation — runs Sunday 03:00
    # 1. Aggregate all paid/ invoices from past 7 days
    # 2. Count pending invoices (pending/ + approved/ + sent/)
    # 3. Calculate pipeline_value (sum of sent/ invoices not yet paid)
    # 4. Calculate week-over-week vs previous week snapshot
    # 5. Write to revenue/weekly-summary.json atomically
    # 6. Archive previous week to revenue/history/{last-monday}.json
    # 7. Run margin_analysis()
    # 8. Run rate_optimization_check()
    # 9. Send revenue_summary to Analytics Claw
    # 10. Log: action_type="weekly_summary_generated"
    # Returns RevenueSummary

    def margin_analysis(self) -> None: ...
    # Compare revenue vs expenses and estimated project costs
    # Inference call: data_type="margin_analysis"
    # If margin < target by >10%: queue War Room REVIEW (margin alert)
    # Log: action_type="margin_analysis_complete"

    def rate_optimization_check(self) -> None: ...
    # Compare current rates against delivery quality data
    # Inference call: data_type="rate_benchmarking_narrative"
    # If systematically undercharging: queue War Room REVIEW
    # Log: action_type="rate_optimization_check"

    def get_current_week_summary(self) -> RevenueSummary: ...
    # Read revenue/weekly-summary.json
    # Return RevenueSummary

    def _load_week_invoices(self, days: int = 7) -> list[Invoice]: ...
    # Read all invoices/paid/ files
    # Filter to those paid within the last `days` days
    # Return list of Invoice objects

    def _atomic_write_summary(
        self,
        path: Path,
        data: dict
    ) -> None: ...
    # Write to temp file in same dir, rename on success
    # Never overwrite good data with partial write
```

Write pytest tests: record_payment updates week_total correctly,
week_over_week calculated correctly (including negative), pipeline_value
sums sent invoices correctly, atomic write verified (temp cleaned up),
margin alert queued when margin compressed >10%, rate check queued
when undercharging detected, weekly summary sends revenue_summary.

---

### TASK 2.4 — Expense Tracker

**New file:** `milimo-blueprint/orchestrator/finance/expense_tracker.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
from datetime import datetime

@dataclass
class ExpenseEntry:
    expense_id: str
    description: str
    amount: float
    currency: str
    expense_date: str          # ISO date
    tax_category: str          # or "uncategorized"
    source: str                # "manual" | "api_usage" | "subscription"
    logged_at: str             # ISO timestamp

class ExpenseTracker:
    """
    Logs expenses and classifies them for tax preparation.

    Expenses are logged as AUTO (no approval required).
    Uncategorized expenses are batched at quarterly tax prep.
    All inference calls log data_type.
    """

    def log_expense(
        self,
        description: str,
        amount: float,
        expense_date: str,
        source: str = "manual"
    ) -> ExpenseEntry: ...
    # 1. Assign expense_id (UUID)
    # 2. Classify tax category via inference:
    #    data_type="tax_category_classification"
    #    On failure: category = "uncategorized"
    # 3. Append to expenses/log.jsonl (thread-safe)
    # 4. Update category summary in expenses/categories/{category}.json
    # 5. Log operational.log: action_type="expense_logged" (AUTO)
    # 6. Return ExpenseEntry

    def get_uncategorized_expenses(self) -> list[ExpenseEntry]: ...
    # Read expenses/log.jsonl
    # Filter where tax_category == "uncategorized"
    # Used during quarterly tax prep batch review

    def recategorize_expense(
        self,
        expense_id: str,
        new_category: str
    ) -> None: ...
    # Update category in log.jsonl entry (find by expense_id)
    # Update category summary files
    # Log: action_type="expense_recategorized"

    def get_expenses_by_period(
        self,
        start_date: str,
        end_date: str
    ) -> list[ExpenseEntry]: ...
    # Read log.jsonl, filter by expense_date range
    # Used by quarterly tax prep

    def get_category_summary(self) -> dict[str, float]: ...
    # Return {category: total_amount} for current year
    # Read from expenses/categories/
```

Write pytest tests: expense logged to JSONL, tax category assigned via
inference (mock), uncategorized on inference failure, category summary
updated, get_expenses_by_period correct filtering, uncategorized expense
retrieval accurate.

---

## PHASE 3 — SCHEDULING AND QUARTERLY TAX
## Complete all Phase 2 tests before starting Phase 3.

---

### TASK 3.1 — Finance Scheduler

**New file:** `milimo-blueprint/orchestrator/finance/finance_scheduler.py`

```python
import threading
from datetime import datetime, timedelta, date
from typing import Callable

class FinanceScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Finance Claw.

    Schedule:
      Daily   09:00 — Payment status check for all sent invoices
      Daily   09:00 — Overdue detection pass
      Sunday  03:00 — Weekly revenue summary generation
      Quarterly Day 1 — Tax prep summary generation
        (Jan 1, Apr 1, Jul 1, Oct 1)

    Uses threading.Timer with recalculated delay.
    No cron. No APScheduler. Only stdlib.
    Checks for missed jobs on startup.
    """

    def __init__(
        self,
        payment_monitor: PaymentMonitor,
        revenue_tracker: RevenueTracker,
        expense_tracker: ExpenseTracker,
        approval_handler: FinanceApprovalHandler,
        operational_log: FinanceOperationalLog
    ): ...

    def start(self) -> None: ...
    # Initialize all scheduled timers
    # Check for missed jobs since last shutdown
    # Log: action_type="scheduler_started"

    def stop(self) -> None: ...
    # Cancel all pending timers
    # Log: action_type="scheduler_stopped"

    def _run_daily_payment_check(self) -> None: ...
    # payment_monitor.check_all_sent_invoices()
    # payment_monitor.check_and_flag_overdue()
    # Log timing

    def _run_weekly_summary(self) -> None: ...
    # revenue_tracker.generate_weekly_summary()
    # Log timing

    def _run_quarterly_tax_prep(self) -> None: ...
    # Aggregate income and expenses for the quarter
    # Verify all expenses are categorized
    # Batch uncategorized expenses → War Room REVIEW
    # Write tax/quarterly/{YYYY-Q}.json
    # Queue War Room AUTO: "Q{N} tax summary ready"
    # Log: action_type="quarterly_tax_prep"

    def _check_hold_staleness(self) -> None: ...
    # Runs daily
    # Check all invoices in approved/ (stuck in HOLD queue)
    # If in HOLD > 48 hours: add urgency flag to War Room card
    # If in HOLD > 7 days: escalate urgency flag

    def _check_missed_jobs(self) -> None: ...
    # Read last_run timestamps from operational.log
    # If weekly summary last ran > 8 days ago: run immediately
    # If daily payment check last ran > 36 hours ago: run immediately
    # Log any recovered jobs

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None
    ) -> float: ...

    def _is_quarter_start(self) -> bool: ...
    # True on Jan 1, Apr 1, Jul 1, Oct 1
    # Used to trigger quarterly tax prep
```

Write pytest tests: scheduler starts and stops cleanly, missed payment
check triggers on startup when last run > 36 hours, quarterly trigger
fires on quarter start dates only, HOLD staleness check flags at 48h
and 7d, self-rescheduling verified.

---

## PHASE 4 — MAIN ENTRY POINT AND INTEGRATION
## Complete all Phase 3 tests before starting Phase 4.

---

### TASK 4.1 — Finance Claw Main Entry Point

**New file:** `milimo-blueprint/orchestrator/finance/finance_claw.py`

```python
from typing import Any

class FinanceClaw:
    """
    Main entry point for the Finance Claw.
    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(self, squad_id: str, inference_client: Any,
                 stripe_client: Any): ...

    def startup(self) -> None: ...
    # 1. Run filesystem init — validate structure
    # 2. Log startup to operational.log
    # 3. Initialize all components with shared dependencies
    # 4. Register inbound message handlers with mesh router:
    #    - pricing_query → pricing_engine.handle_pricing_query
    #    - project_complete → invoice_manager.generate_invoice
    # 5. Register approval flow handlers with War Room:
    #    - review_approve → approval_handler.handle_review_approve
    #    - review_edit → approval_handler.handle_review_edit
    #    - review_block → approval_handler.handle_review_block
    #    - hold_release → approval_handler.handle_hold_release
    #    - hold_cancel → approval_handler.handle_hold_cancel
    # 6. Start finance_scheduler
    # 7. Log: action_type="claw_started"

    def shutdown(self) -> None: ...
    # Stop scheduler cleanly
    # Log: action_type="claw_stopped"

    def handle_inbound(self, raw_message: dict) -> None: ...
    # Route inbound message to correct handler
    # Log receipt to operational.log
    # Catch all exceptions — never crash on bad input
```

---

### TASK 4.2 — Integration Test Suite (14-Step MVR)

**New file:** `milimo-blueprint/tests/test_finance_integration.py`

Implement all 14 steps from the spec MVR sequence:

```python
import pytest
import stripe  # use stripe.testing or mock

class TestFinanceMVR:

    def test_mvr_01_stripe_test_mode_configured(self):
        """Stripe client uses test credentials (sk_test_*)."""

    def test_mvr_02_pricing_query_received(self):
        """Mock pricing_query from Ops — Finance Claw receives it."""

    def test_mvr_03_pricing_response_within_10_minutes(self):
        """pricing_response sent to Ops within 600 seconds."""

    def test_mvr_04_project_complete_triggers_invoice(self):
        """Mock project_complete — invoice generated in pending/."""

    def test_mvr_05_invoice_in_war_room_as_review_not_hold(self):
        """Invoice appears as REVIEW action — not HOLD, not sent."""

    def test_mvr_06_stage1_approve_creates_hold_not_send(self):
        """
        CRITICAL: Approving Stage 1 REVIEW must NOT send the invoice.
        Invoice must move to approved/ and HOLD queue only.
        No Stripe API call must occur at Stage 1 approve.
        """

    def test_mvr_07_hold_release_transmits_via_stripe(self):
        """HOLD release triggers Stripe invoice creation and send."""

    def test_mvr_08_invoice_moves_to_sent(self):
        """After HOLD release, invoice file moves approved/ → sent/."""

    def test_mvr_09_stripe_payment_simulation(self):
        """Simulate payment in Stripe test mode."""

    def test_mvr_10_payment_detected_moves_to_paid(self):
        """Payment monitor detects payment within 24h, moves to paid/."""

    def test_mvr_11_revenue_summary_sent_to_analytics(self):
        """After payment: revenue_summary dispatched to Analytics Claw."""

    def test_mvr_12_past_due_simulation(self):
        """Set invoice due_date to yesterday, trigger overdue check."""

    def test_mvr_13_overdue_invoice_moves_and_war_room_review(self):
        """Overdue: moves to overdue/, War Room REVIEW queued."""

    def test_mvr_14_payment_overdue_sent_to_ops(self):
        """payment_overdue message dispatched to Ops Claw."""
```

Test 6 is the most critical test in the entire Finance Claw test suite.
It must explicitly assert that no Stripe API call was made during
Stage 1 approval. Use a mock to capture Stripe calls and assert
call_count == 0 after Stage 1 approve.

---

## FINAL VERIFICATION CHECKLIST

□ /sandbox/finance/ full directory structure created on finance_init
□ All log files created on init (operational, decisions, payment-events)
□ pricing/rules.json created with default values on init
□ Filesystem init is idempotent — no errors on repeated calls
□ pricing_query receives pricing_response within 10 minutes
□ pricing_response data_quality="estimated" when no history available
□ Rule-based fallback fires when inference unavailable
□ pricing/estimates/{project_id}.json written on every query
□ project_complete triggers invoice generation in pending/
□ Invoice includes line items, total, due date, payment risk score
□ Invoice queued as REVIEW — not HOLD, not sent
□ Stage 1 REVIEW approve → invoice in approved/, HOLD queued, NO Stripe call
□ Stage 2 HOLD release → Stripe invoice created and sent
□ Invoice lifecycle: pending → approved → sent → paid (or overdue)
□ Payment detected within 24-hour check window
□ Payment received: invoice moves to paid/, revenue updated
□ revenue_summary sent to Analytics with totals only (no line items)
□ Overdue: fires immediately when due_date passes
□ First overdue → War Room REVIEW (not HOLD)
□ Second overdue → War Room HOLD (escalation)
□ payment_overdue sent to Ops Claw immediately (no weekly wait)
□ HOLD staleness: urgency flag at 48h, escalation at 7 days
□ Expense logged with tax category or "uncategorized" on failure
□ Weekly revenue summary generated Sunday 03:00
□ Margin compression alert queued when margin <10% of target
□ Rate optimization advisory queued when undercharging detected
□ Quarterly tax prep fires Jan 1, Apr 1, Jul 1, Oct 1
□ Uncategorized expenses batched to War Room at quarterly prep
□ Scheduler detects missed jobs on startup and recovers
□ All inbound message types wired to correct handlers
□ All approval flow handlers registered with War Room
□ data_type logged on every inference call (cloud during dev)
□ All 14 MVR integration tests pass
□ Test 6 explicitly asserts zero Stripe calls on Stage 1 approve
□ All unit tests pass: pytest milimo-blueprint/orchestrator/finance/

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  File: [exact path — NEW]
  Summary: [one sentence]

  [complete implementation — no TODOs, no stubs, no placeholders]

  Tests: [complete pytest file immediately after]
  -----------------------------------------

Begin with Task 1.1. Do not proceed to 1.2 until 1.1 tests pass.
The spec is ground truth. This prompt conflicts with spec → spec wins.
All inference to cloud during dev. Log data_type on every call.
Stripe test mode only — no live credentials.
Two-stage invoice approval is non-negotiable — test it first.
