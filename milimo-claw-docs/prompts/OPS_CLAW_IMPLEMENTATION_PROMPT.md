# MILIMO CLAW — OPS CLAW IMPLEMENTATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. OPS_CLAW_AUDIT_REPORT.md               (the gap analysis)
#   2. MILIMO_CLAW_OPS_CLAW_SPEC.md           (the ground truth spec)
#   3. ops-claw.yaml                           (role blueprint — EXISTS)
#   4. ops-sandbox.yaml                        (sandbox policy — EXISTS)
#   5. contracts.py                            (message types — PARTIAL)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert Python engineer building the Ops Claw for Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw.

The audit confirms the Ops Claw is 0% implemented. The configuration files
exist (ops-claw.yaml, ops-sandbox.yaml) and contracts.py has partial
message type definitions — but no Python orchestration code exists.
You are building everything from scratch.

The spec document is the ground truth. The audit defines what must be built
and identifies three contract gaps to fix first. This prompt defines
exactly how to build it.

---

## CONTEXT — THE SYSTEM YOU ARE BUILDING INTO

The Ops Claw is the account manager and project manager of the Milimo Claw
mesh. It owns the full client lifecycle — from the first inquiry to final
delivery and invoice. It is the coordination hub of the entire operation:
it receives work from Finance, coordinates with Content and Build, and
reports to Analytics.

**Existing integrations that depend on Ops Claw:**
  - `contracts.py` has partial Ops message type definitions — handlers missing
  - Finance Claw expects `pricing_query` from Ops — schema missing from contracts
  - Analytics Claw expects `client_health_signal` from Ops — schema incomplete
  - Content Claw expects `project_brief` from Ops — schema exists, no sender
  - Build Claw expects `feature_brief` from Ops — schema exists, no sender

**Reference implementation:** Use the Finance Claw (`orchestrator/finance/`)
as your structural pattern — it was built first and follows the correct
conventions for filesystem init, log management, signal dispatch, approval
handlers, and scheduler design.

**Plugin structure:**
  - Python orchestrator:  `milimo-blueprint/orchestrator/`
  - New Ops files:        `milimo-blueprint/orchestrator/ops/`
  - Role blueprint:       `milimo-blueprint/roles/ops-claw.yaml`
  - Sandbox policy:       `milimo-blueprint/policies/ops-sandbox.yaml`
  - Operator config:      `~/.milimo/config.json`

**Operator:** Mainza Kangombe — senior systems architect, Python 3.11+.
Production-quality code only. No stubs. No TODOs. No placeholder comments.
Every function must be complete and runnable.

---

## DEVELOPMENT PHASE CONSTRAINTS

**Inference:** ALL inference routes to cloud (Nemotron 120B via NVIDIA
Cloud API). Do NOT implement local NIM routing. DO log `data_type` as
a field on every single inference call — mandatory, not optional.

```python
# Every inference call must follow this pattern:
response = self.inference_client.complete(
    prompt=prompt,
    data_type="client_triage_scoring",  # ALWAYS INCLUDE
    max_tokens=600
)
```

**Sandbox isolation applies.** Ops Claw must only write to
`/sandbox/clients/` and only receive other claws' data via typed
inter-claw messages. The Landlock restriction is kernel-level.

**Critical sequencing rule (non-negotiable):**
`pricing_query` must be sent and `pricing_response` received BEFORE
`project_brief` is sent to any creative claw. No code path may send
a `project_brief` without a confirmed `pricing_response`. This is the
single most important sequencing constraint in the Ops Claw.

**Standards (non-negotiable):**
  - Python 3.11+, full type hints, docstrings on every class and method
  - pathlib.Path only — never os.path string concatenation
  - PyYAML safe_load only — never yaml.load()
  - Append-only log files using fcntl file locking for thread safety
  - Atomic file writes for JSON summaries: write temp → rename on success
  - Never silently swallow exceptions — log and re-raise or typed error
  - Tests: pytest, full coverage for every class and method

---

## PHASE 0 — FIX CONTRACTS FIRST
## Must be done before writing any Ops Claw handler code.
## The audit identified three gaps in contracts.py.

---

### TASK 0.1 — Add Missing Message Type Schemas to contracts.py

**File to modify:** `milimo-blueprint/orchestrator/contracts.py`

The audit identified three missing or incomplete schemas.
Add all three before writing any other code.

**Gap 1: Add `pricing_query` (Ops → Finance)**
```python
"pricing_query": {
    "sender_roles": ["ops"],
    "recipient_roles": ["finance"],
    "required_payload": [
        "project_id",
        "scope_description",
        "complexity_estimate",
        "deadline"
    ],
    "optional_payload": ["client_id", "urgency"],
    "frequency": "on_event",
    "priority": "AUTO",
    "sla_minutes": 10,   # Finance must respond within 10 minutes
},
```

**Gap 2: Add `client_onboarded` (Ops → Analytics)**
```python
"client_onboarded": {
    "sender_roles": ["ops"],
    "recipient_roles": ["analytics"],
    "required_payload": [
        "client_id",
        "niche",
        "project_type",
        "estimated_value"
    ],
    "frequency": "on_event",
    "priority": "AUTO",
},
```

**Gap 3: Add Ops → Analytics variant of `client_health_signal`**
The existing `client_health_signal` schema has Analytics and Ops as
senders but is missing Ops as the originating sender for weekly
health reports. Update the `sender_roles` list:
```python
"client_health_signal": {
    "sender_roles": ["ops", "analytics"],  # ADD "ops" — was missing
    "recipient_roles": ["analytics", "content", "ops"],
    ...existing fields unchanged...
}
```

After all three changes, print the complete updated MESSAGE_TYPE_SCHEMAS
dict so all entries are visible.

Write pytest tests: all three new/updated schemas validate correctly,
pricing_query schema requires all four payload fields, client_onboarded
requires all four fields, client_health_signal accepts "ops" as sender.

---

## PHASE 1 — CORE INFRASTRUCTURE
## Build in exact task order. Do not proceed to Phase 2 until all
## Phase 1 tests pass.

---

### TASK 1.1 — Ops Filesystem Initialization

**New file:** `milimo-blueprint/orchestrator/ops/ops_init.py`

```python
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal
import json

BASE = Path("/sandbox/clients")

REQUIRED_DIRS = [
    "active",
    "prospects",
    "completed",
    "contracts",
    "templates",
    "logs",
]

REQUIRED_TEMPLATE_FILES = {
    "templates/welcome-message.md": (
        "Hi {{client_name}},\n\nThank you for reaching out to {{squad_name}}. "
        "We'd love to learn more about your project.\n\n"
        "Could you tell us a bit more about what you're looking for?\n\n"
        "Best,\n{{squad_name}}"
    ),
    "templates/intake-questionnaire.md": (
        "## Project Brief\n\n"
        "1. What is the goal of this project?\n"
        "2. What is your target timeline/deadline?\n"
        "3. What does success look like to you?\n"
        "4. Do you have any existing brand guidelines or references?\n"
        "5. What is your approximate budget range?"
    ),
    "templates/proposal-template.md": (
        "## Proposal for {{project_name}}\n\n"
        "**Scope:** {{scope_description}}\n\n"
        "**Timeline:** {{timeline}}\n\n"
        "**Investment:** {{price_range}}\n\n"
        "**Deliverables:**\n{{deliverables}}"
    ),
    "templates/change-order-template.md": (
        "## Change Order Request\n\n"
        "**Original Scope:** {{original_scope}}\n\n"
        "**Requested Addition:** {{new_request}}\n\n"
        "**Additional Investment:** {{additional_cost}}\n\n"
        "**Revised Timeline:** {{revised_timeline}}"
    ),
    "templates/delivery-message.md": (
        "Hi {{client_name}},\n\n"
        "Your project is complete! Here's what we delivered:\n\n"
        "{{deliverables_summary}}\n\n"
        "Please review and let us know if you have any questions.\n\n"
        "Best,\n{{squad_name}}"
    ),
    "templates/deep-work-response.md": (
        "Hey {{client_name}}, I'm heads-down on a focused sprint until "
        "{{resume_date}}. Your project is on track — I'll be back in "
        "full swing then. 🙏"
    ),
}

REQUIRED_LOG_FILES = [
    "logs/operational.log",
    "logs/comms.log",
    "logs/decisions.log",
]

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

class OpsFilesystemInit:
    """
    Creates and validates the full /sandbox/clients/ filesystem structure.
    Idempotent — safe to call on every claw startup.
    """

    def initialize(self) -> InitResult: ...
    # Create REQUIRED_DIRS, REQUIRED_TEMPLATE_FILES, REQUIRED_LOG_FILES
    # Never overwrite existing files
    # Return full accounting in InitResult

    def validate(self) -> ValidationResult: ...

    def get_client_path(
        self,
        status: Literal["active", "completed"],
        client_id: str
    ) -> Path: ...

    def get_project_path(
        self,
        client_id: str,
        project_id: str
    ) -> Path: ...

    def get_prospect_path(self, inquiry_id: str) -> Path: ...

    def get_template(self, template_name: str) -> str: ...
    # Read and return template content from templates/
    # Raise FileNotFoundError if template missing

    def create_client_dirs(self, client_id: str) -> None: ...
    # Create: active/{client_id}/
    #         active/{client_id}/projects/
    #         active/{client_id}/comms/
    # Called when a new client is onboarded

    def create_project_dirs(
        self,
        client_id: str,
        project_id: str
    ) -> None: ...
    # Create: active/{client_id}/projects/{project_id}/
    #         active/{client_id}/projects/{project_id}/comms/
    # Called when a new project is scoped
```

Also implement `OpsOperationalLog` and `OpsCommsLog`:

```python
@dataclass
class OpsLogEntry:
    timestamp: str
    action_type: str   # inquiry_received, welcome_drafted, brief_sent, etc.
    entity_id: str     # client_id, project_id, inquiry_id
    outcome: str       # success, failed, pending, escalated, approved, blocked
    details: dict

class OpsOperationalLog:
    """Append-only structured log. Thread-safe via fcntl file locking."""

    def __init__(self, log_path: Path): ...
    def append(self, entry: OpsLogEntry) -> None: ...
    def read_recent(
        self,
        days: int = 30,
        action_type: str | None = None
    ) -> list[OpsLogEntry]: ...
    def count_by_type(self, action_type: str, days: int = 30) -> int: ...

@dataclass
class CommsLogEntry:
    timestamp: str
    direction: str      # "sent" | "received"
    client_id: str
    project_id: str | None
    channel: str        # "email" | "platform_dm" | "auto_response"
    content_preview: str  # first 100 chars only — never full message
    approved_by: str | None   # operator action_id if sent via War Room

class OpsCommsLog:
    """Log of all client communications. Append-only. Thread-safe."""

    def __init__(self, log_path: Path): ...
    def append(self, entry: CommsLogEntry) -> None: ...
    def get_client_history(
        self,
        client_id: str,
        days: int = 90
    ) -> list[CommsLogEntry]: ...
    def get_response_times(self, client_id: str) -> list[float]: ...
    # Returns list of hours between client message and squad response
    # Used by health scorer for communication pattern analysis
```

Write pytest tests: directory creation, idempotent re-run, template
loading, client/project dir creation, log append and read, comms log
response time calculation, concurrent write safety.

---

### TASK 1.2 — Signal Dispatcher

**New file:** `milimo-blueprint/orchestrator/ops/signal_dispatcher.py`

Build outbound messaging first — every other component needs it.

```python
class OpsSignalDispatcher:
    """
    Sends all outbound messages from the Ops Claw to other claws.
    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to operational.log.
    Never raises on dispatch failure — logs error and continues.
    """

    def send_project_brief(
        self,
        client_id: str,
        project_id: str,
        brief_text: str,
        deadline: str,
        tone_requirements: str,
        platform_targets: list[str],
        recipient_role: str   # "content" or "build"
    ) -> None: ...
    # ONLY callable after pricing_response has been received
    # Raises PricingNotConfirmedError if no pricing_response on file
    # Log: action_type="project_brief_sent"

    def send_feature_brief(
        self,
        client_id: str,
        project_id: str,
        feature_description: str,
        deadline: str,
        acceptance_criteria: str
    ) -> None: ...
    # Send feature_brief to Build Claw
    # Log: action_type="feature_brief_sent"

    def send_pricing_query(
        self,
        project_id: str,
        scope_description: str,
        complexity_estimate: str,
        deadline: str,
        client_id: str | None = None
    ) -> None: ...
    # Send pricing_query to Finance Claw
    # Start 10-minute SLA timer for pricing_response
    # Log: action_type="pricing_query_sent"

    def send_project_complete(
        self,
        project_id: str,
        client_id: str,
        delivered_at: str
    ) -> None: ...
    # Send project_complete to Finance Claw → triggers invoice
    # ONLY callable after client confirms delivery receipt
    # Log: action_type="project_complete_sent"

    def send_client_health_signal(
        self,
        client_id: str,
        health_score: float,
        health_factors: list[str],
        recommended_action: str
    ) -> None: ...
    # Send client_health_signal to Analytics Claw
    # Send weekly regardless of score value
    # Log: action_type="client_health_signal_sent"

    def send_client_onboarded(
        self,
        client_id: str,
        niche: str,
        project_type: str,
        estimated_value: float
    ) -> None: ...
    # Send client_onboarded to Analytics Claw
    # Log: action_type="client_onboarded_sent"

    def _send(
        self,
        message_type: str,
        recipient_role: str,
        payload: dict
    ) -> None: ...
    # Core send via mesh gateway
    # Includes message_id (UUID), timestamp, sender_role="ops"
    # On exception: log error, do not raise
```

Write pytest tests: each send method produces correct message_type and
recipient, project_brief raises PricingNotConfirmedError when no
pricing_response on file, dispatch failure logged but not raised,
every send logged to operational.log.

---

### TASK 1.3 — Approval Handler

**New file:** `milimo-blueprint/orchestrator/ops/approval_handler.py`

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class OpsApprovalAction:
    action_id: str
    action_type: str    # welcome_message, proposal, project_brief,
                        # delivery_message, deadline_risk, scope_change,
                        # routine_update
    entity_id: str      # client_id or project_id
    mode: str           # REVIEW | HOLD | AUTO
    content: str        # the draft content to be sent or acted on
    context: dict       # metadata for War Room display
    timestamp: str
    outcome: str | None = None   # approved | edited | blocked | released

class OpsApprovalHandler:
    """
    Handles all War Room approval interactions for Ops Claw actions.

    No client-facing message leaves the Ops Claw without operator approval.
    REVIEW: drafted, operator approves before sending.
    HOLD: fully paused, operator explicitly releases.
    AUTO: runs and logs, visible in morning digest.
    Every decision logged to decisions.log.
    """

    def queue_review(
        self,
        action_type: str,
        entity_id: str,
        content: str,
        context: dict
    ) -> str: ...
    # Add to War Room REVIEW queue
    # Returns action_id

    def queue_hold(
        self,
        action_type: str,
        entity_id: str,
        content: str,
        context: dict
    ) -> str: ...
    # Add to War Room HOLD queue
    # Returns action_id

    def log_auto(
        self,
        action_type: str,
        entity_id: str,
        content_preview: str
    ) -> None: ...
    # Log AUTO action — no queue, no approval needed
    # Appears in morning digest only

    def handle_approve(
        self,
        action_id: str,
        send_fn: callable
    ) -> None: ...
    # Execute the approved action via send_fn
    # Log to decisions.log: APPROVED
    # Log to comms.log if action sends a client-facing message

    def handle_edit(
        self,
        action_id: str,
        edited_content: str,
        send_fn: callable
    ) -> None: ...
    # Preserve original as training signal
    # Send edited version
    # Log edit delta to decisions.log

    def handle_block(
        self,
        action_id: str,
        reason: str | None
    ) -> None: ...
    # Do not send — discard draft
    # Log to decisions.log: BLOCKED with reason
    # For blocked welcome messages: log inquiry as declined

    def handle_hold_release(
        self,
        action_id: str,
        execute_fn: callable
    ) -> None: ...
    # Execute held action
    # Log to decisions.log: HOLD_RELEASED

    def add_urgency_flag(
        self,
        action_id: str,
        hours_waiting: int
    ) -> None: ...
    # Add urgency text to existing War Room card
    # 24h: "No decision in 24h — client may disengage"
    # 48h: "Response window closing"

    def log_decision(self, action: OpsApprovalAction) -> None: ...
    # Append to logs/decisions.log
```

Write pytest tests: queue_review and queue_hold return valid action_ids,
handle_approve calls send_fn, handle_edit preserves original and sends
edited, handle_block does not call send_fn, urgency flags added at
correct thresholds, all decisions logged to decisions.log.

---

## PHASE 2 — INTAKE AND TRIAGE
## Complete all Phase 1 tests before starting Phase 2.

---

### TASK 2.1 — Intake Manager

**New file:** `milimo-blueprint/orchestrator/ops/intake_manager.py`

The intake manager is the front door of the Ops Claw. Every client
relationship begins here.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import uuid
import json
from datetime import datetime

@dataclass
class TriageScore:
    inquiry_id: str
    budget_signal: float     # 0–10
    scope_clarity: float     # 0–10
    niche_fit: float         # 0–10
    combined_score: float    # (budget * 0.4) + (scope * 0.3) + (fit * 0.3)
    routing: str             # "draft_welcome" | "flag_for_review" | "auto_low"
    scored_at: str

@dataclass
class ClientBrief:
    brief_id: str
    inquiry_id: str
    client_id: str
    project_id: str
    raw_text: str
    deadline: str | None
    scope_description: str
    deliverables: list[str]
    clarity_score: float     # 0–10
    gaps: list[str]          # missing or ambiguous elements
    created_at: str

class IntakeManager:
    """
    Manages the full client inquiry intake pipeline.

    Entry point: receive_inquiry()
    Pipeline: triage → welcome draft → questionnaire → brief quality check
             → pricing query → project brief to creative claw

    Sequencing rule: pricing_response must be received before
    project_brief can be sent. Never bypass this.
    """

    WELCOME_DRAFT_THRESHOLD = 80    # score >= 80: auto-draft welcome
    REVIEW_THRESHOLD = 50           # score 50–79: flag for operator

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        dispatcher: OpsSignalDispatcher,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog
    ): ...

    def receive_inquiry(self, raw_inquiry: dict) -> TriageScore: ...
    # 1. Assign inquiry_id (UUID)
    # 2. Write inquiry.json to prospects/{inquiry_id}/
    # 3. Run triage scoring
    # 4. Write triage.json to prospects/{inquiry_id}/
    # 5. Route based on combined_score:
    #    ≥ 80: draft welcome + questionnaire → queue REVIEW
    #    50–79: queue REVIEW with triage summary (no draft)
    #    < 50: log_auto (morning digest only)
    # 6. Log: action_type="inquiry_received"
    # 7. Return TriageScore

    def score_inquiry(
        self,
        inquiry_text: str,
        squad_niche: str
    ) -> TriageScore: ...
    # Inference call: data_type="client_triage_scoring"
    # Prompt: inquiry text + squad niche context
    # Parse: budget_signal (0–10), scope_clarity (0–10), niche_fit (0–10)
    # Calculate: combined_score = (budget*0.4) + (scope*0.3) + (fit*0.3)
    # Set routing based on combined_score thresholds
    # Fallback if inference fails: score all dimensions 5.0,
    #   routing="flag_for_review", log warning

    def draft_welcome_message(
        self,
        inquiry_id: str,
        client_name: str | None
    ) -> str: ...
    # Load template from templates/welcome-message.md
    # Personalize via inference: data_type="welcome_message_drafting"
    # Incorporate inquiry context for relevance
    # Return personalized welcome message draft

    def draft_intake_questionnaire(
        self,
        inquiry_id: str,
        inquiry_context: str
    ) -> str: ...
    # Load template from templates/intake-questionnaire.md
    # Optionally customize questions for inquiry type
    # Return questionnaire draft

    def handle_client_response(
        self,
        inquiry_id: str,
        response_text: str
    ) -> ClientBrief: ...
    # Called when client responds to intake questionnaire
    # 1. Run brief quality check via inference:
    #    data_type="brief_quality_check"
    #    Check: missing deadline, undefined scope, unclear deliverables
    # 2. If gaps found: draft clarifying question → queue REVIEW
    # 3. If brief is clear: create ClientBrief, write to filesystem
    # 4. Send pricing_query to Finance Claw
    # 5. Log: action_type="brief_received"
    # 6. Return ClientBrief
    # NOTE: project_brief to creative claw is sent AFTER pricing_response
    #       arrives — not here

    def onboard_client(
        self,
        inquiry_id: str,
        client_name: str,
        contact_details: dict
    ) -> str: ...
    # Convert prospect to active client
    # 1. Assign client_id (UUID)
    # 2. Create client dirs via fs.create_client_dirs()
    # 3. Write profile.json to active/{client_id}/
    # 4. Move from prospects/ to active/ context
    # 5. Send client_onboarded to Analytics Claw
    # 6. Log: action_type="client_onboarded"
    # 7. Return client_id

    def handle_pricing_response(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float,
        scope_notes: str
    ) -> None: ...
    # Called when Finance Claw sends pricing_response
    # 1. Store pricing in pricing/estimates context for this project
    # 2. Draft proposal using pricing data:
    #    data_type="proposal_drafting"
    # 3. Queue proposal as REVIEW (includes pricing range)
    # 4. Mark pricing as confirmed for this project_id
    # 5. Log: action_type="pricing_response_received"
    # NOTE: project_brief is sent only after operator approves proposal

    def send_project_brief_after_proposal_approved(
        self,
        project_id: str,
        client_id: str,
        brief: ClientBrief,
        recipient_role: str  # "content" or "build"
    ) -> None: ...
    # Called by approval_handler after proposal REVIEW is approved
    # Verify pricing is confirmed — raise if not
    # Send project_brief via dispatcher
    # Create project dirs via fs.create_project_dirs()
    # Write brief.json to project directory
    # Log: action_type="project_brief_sent"

    def _group_rapid_messages(
        self,
        client_id: str,
        new_message: dict,
        window_minutes: int = 30
    ) -> bool: ...
    # Check if a message from this client arrived within the last 30 min
    # If yes: append to existing grouped action card, return True
    # If no: create new action card, return False

    def _check_inquiry_staleness(self) -> None: ...
    # Run daily — check all REVIEW-queued inquiries
    # If no operator decision in 24h: add urgency flag
    # If no operator decision in 48h: "Response window closing"
```

Write pytest tests: triage score calculation correct (budget 0.4, scope
0.3, fit 0.3), routing thresholds (≥80 / 50-79 / <50), fallback scoring
on inference failure, brief quality check detects missing deadline,
handle_pricing_response stores pricing and drafts proposal, project_brief
raises without confirmed pricing, rapid message grouping (30-min window),
staleness flags at 24h and 48h.

---

### TASK 2.2 — Client Health Scorer

**New file:** `milimo-blueprint/orchestrator/ops/health_scorer.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class ClientHealthScore:
    client_id: str
    score: float              # 0–10
    health_level: str         # "healthy" (≥8) | "monitor" (6–8) | "at_risk" (<6)
    factors: list[str]        # plain English health factors
    response_time_avg_hrs: float
    revision_request_rate: float
    scope_adherence_score: float
    communication_sentiment: float
    scored_at: str

class ClientHealthScorer:
    """
    Scores client relationship health weekly.

    Inputs: comms.log (response times), decisions.log (revision requests),
    project status files (scope adherence), inference sentiment analysis.
    Sends client_health_signal to Analytics Claw for all clients.
    Flags at_risk clients (score < 6.0) in War Room immediately.
    """

    AT_RISK_THRESHOLD = 6.0
    HEALTHY_THRESHOLD = 8.0

    def score_client(
        self,
        client_id: str
    ) -> ClientHealthScore: ...
    # 1. Load comms history from comms.log — calculate avg response time
    # 2. Load decisions.log — count revision requests for this client
    # 3. Load project status files — assess scope adherence
    # 4. Run sentiment analysis on recent comms:
    #    data_type="communication_sentiment_analysis"
    # 5. Combine into weighted score
    # 6. If score < AT_RISK_THRESHOLD: queue War Room REVIEW immediately
    # 7. Log: action_type="client_scored"
    # 8. Return ClientHealthScore

    def score_all_active_clients(self) -> list[ClientHealthScore]: ...
    # Score every client in active/
    # Send client_health_signal for each via dispatcher
    # Return all scores

    def _calculate_response_time_score(
        self,
        client_id: str
    ) -> float: ...
    # Read comms.log response times for this client
    # Fast responses (< 4h): 10. Moderate (4–24h): 7. Slow (>24h): 4

    def _calculate_revision_rate_score(
        self,
        client_id: str
    ) -> float: ...
    # Count revision requests vs total deliverables
    # Low revision rate: 10. High revision rate: 4

    def _calculate_scope_adherence_score(
        self,
        client_id: str
    ) -> float: ...
    # Check projects for scope creep events
    # No scope creep: 10. One event: 7. Multiple: 4

    def _combine_scores(
        self,
        response_time: float,
        revision_rate: float,
        scope_adherence: float,
        sentiment: float
    ) -> float: ...
    # Weighted average:
    # response_time * 0.3 + revision_rate * 0.25 +
    # scope_adherence * 0.25 + sentiment * 0.2
```

Write pytest tests: score calculation from mock comms/decisions logs,
at_risk threshold triggers War Room REVIEW, healthy threshold correct,
score_all_active_clients returns one score per client in active/,
response time scoring at boundary values, combined score weighting correct.

---

## PHASE 3 — PROJECT MANAGEMENT
## Complete all Phase 2 tests before starting Phase 3.

---

### TASK 3.1 — Project Manager

**New file:** `milimo-blueprint/orchestrator/ops/project_manager.py`

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Any
import json
from datetime import datetime, timedelta

@dataclass
class ProjectStatus:
    project_id: str
    client_id: str
    status: Literal[
        "briefing", "pricing_pending", "proposal_sent",
        "active", "review", "delivered", "completed"
    ]
    deadline: str           # ISO date
    deliverable_received: bool = False
    client_confirmed: bool = False
    risk_level: str = "normal"   # "normal" | "elevated" | "critical"
    last_updated: str = ""

@dataclass
class DeadlineRisk:
    project_id: str
    client_id: str
    deadline: str
    days_remaining: int
    risk_level: str      # "elevated" (≤5 days) | "critical" (≤24 hrs)
    recommended_action: str

class ProjectManager:
    """
    Manages the full project lifecycle from brief to delivery.

    Tracks: project status, deadline risk, deliverable receipt,
    client confirmation, and project completion.
    Coordinates: with Content/Build on brief sending, with Finance
    on project_complete, with Analytics on client health.
    """

    def __init__(
        self,
        fs: OpsFilesystemInit,
        dispatcher: OpsSignalDispatcher,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog
    ): ...

    def create_project(
        self,
        client_id: str,
        brief: "ClientBrief",
        deadline: str
    ) -> ProjectStatus: ...
    # 1. Assign project_id (UUID)
    # 2. Create project dirs via fs.create_project_dirs()
    # 3. Write brief.json, status.json, timeline.json
    # 4. Status: "pricing_pending"
    # 5. Log: action_type="project_created"
    # 6. Return ProjectStatus

    def handle_deliverable_complete(
        self,
        message: dict
    ) -> None: ...
    # Receives deliverable_complete from Content or Build Claw
    # 1. Load project status
    # 2. Update: deliverable_received = True
    # 3. Draft delivery message using template + delivery context:
    #    data_type="delivery_message_drafting"
    # 4. Queue delivery message as REVIEW
    # 5. Log: action_type="deliverable_received"

    def handle_deploy_complete(self, message: dict) -> None: ...
    # Receives deploy_complete from Build Claw
    # 1. Update project status with deploy URL and version
    # 2. Draft client notification of deploy
    # 3. Queue as REVIEW
    # 4. Log: action_type="deploy_received"

    def confirm_client_receipt(self, project_id: str) -> None: ...
    # Called after client confirms delivery
    # 1. Update: client_confirmed = True, status = "completed"
    # 2. Send project_complete to Finance Claw via dispatcher
    # 3. Update client health record
    # 4. Archive project: move to completed context
    # 5. Log: action_type="project_completed"
    # NOTE: project_complete to Finance only fires here — never earlier

    def check_all_deadlines(self) -> list[DeadlineRisk]: ...
    # Daily 09:00 check
    # Load all active project status files
    # For each: calculate days_remaining
    # ≤ 5 days: elevated risk → queue REVIEW
    # ≤ 24 hrs: critical risk → queue HOLD
    # Return list of all risks found

    def update_project_status(
        self,
        project_id: str,
        new_status: str
    ) -> None: ...
    # Write updated status.json atomically
    # Log: action_type="project_status_updated"

    def get_active_projects(self) -> list[ProjectStatus]: ...
    # Read all active/{client_id}/projects/{project_id}/status.json
    # Return list of ProjectStatus objects

    def handle_pricing_response(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float
    ) -> None: ...
    # Update project status: "pricing_pending" → "proposal_sent"
    # Pricing is now confirmed for this project_id
    # Store pricing confirmation in project context
```

Write pytest tests: create_project writes all three JSON files,
handle_deliverable_complete queues REVIEW (not AUTO), confirm_client_receipt
sends project_complete (verify via dispatcher mock), check_all_deadlines
returns elevated at day 5 and critical at day 1, deadline HOLD fires at
24h boundary, project_complete not sent before client_confirmed=True.

---

### TASK 3.2 — Scope Monitor

**New file:** `milimo-blueprint/orchestrator/ops/scope_monitor.py`

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ScopeCreepDetection:
    project_id: str
    client_id: str
    original_scope: str
    new_request: str
    confidence: float        # 0.0–1.0 — how confident the detection is
    detected_at: str

class ScopeMonitor:
    """
    Detects scope creep in client communications.

    Runs on every client message received.
    High-confidence detections (>0.7) immediately queue a HOLD
    change order — never auto-handled.
    All detections logged to operational.log.
    """

    DETECTION_THRESHOLD = 0.7

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        approval_handler: OpsApprovalHandler,
        dispatcher: OpsSignalDispatcher,
        operational_log: OpsOperationalLog
    ): ...

    def check_message(
        self,
        client_id: str,
        project_id: str,
        message_text: str
    ) -> ScopeCreepDetection | None: ...
    # 1. Load original brief from project directory
    # 2. Inference: data_type="scope_creep_detection"
    #    Compare message_text against original scope
    #    Output: is_scope_creep (bool), confidence (0–1), new_request (str)
    # 3. If confidence > DETECTION_THRESHOLD:
    #    a. Write detection to project context
    #    b. Query Finance Claw for additional scope pricing:
    #       send pricing_query for new_request
    #    c. Draft change order: data_type="change_order_drafting"
    #       (draft without pricing first — pricing fills in on response)
    #    d. Queue as HOLD — never auto-handle scope creep
    # 4. Log: action_type="scope_creep_detected" if found
    # 5. Return detection or None

    def draft_change_order(
        self,
        project_id: str,
        original_scope: str,
        new_request: str,
        additional_cost: float | None = None   # None until pricing arrives
    ) -> str: ...
    # Load template from templates/change-order-template.md
    # Personalize via inference: data_type="change_order_drafting"
    # Return change order draft

    def handle_scope_pricing_response(
        self,
        project_id: str,
        additional_cost: float
    ) -> None: ...
    # Called when Finance Claw responds to scope creep pricing query
    # Update pending change order draft with confirmed pricing
    # Re-queue HOLD with complete change order
    # Log: action_type="scope_change_order_priced"
```

Write pytest tests: high-confidence detection queues HOLD (not REVIEW),
detection below threshold returns None, change order includes original scope
and new request, pricing_query sent on detection, change order updated when
pricing response arrives, operational.log entry created.

---

### TASK 3.3 — Comms Manager

**New file:** `milimo-blueprint/orchestrator/ops/comms_manager.py`

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ClientMessage:
    message_id: str
    client_id: str
    project_id: str | None
    direction: str          # "inbound" | "outbound"
    channel: str
    content: str
    timestamp: str
    approved_action_id: str | None   # set for outbound messages

class CommsManager:
    """
    Manages all client communication.

    Routine updates: AUTO (logged, morning digest)
    Non-routine communications: REVIEW (drafted, operator approves)
    Never references pricing without confirmed pricing_response on file.
    Logs every communication to comms.log.
    Deep Work Mode auto-responses: AUTO (sends without approval).
    """

    ROUTINE_TYPES = [
        "project_update", "schedule_confirmation",
        "file_delivery_notification", "acknowledgment"
    ]

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog,
        comms_log: OpsCommsLog
    ): ...

    def handle_inbound(
        self,
        client_id: str,
        project_id: str | None,
        message_text: str,
        channel: str
    ) -> None: ...
    # 1. Log to comms.log: direction="received"
    # 2. Check for pricing question in message:
    #    data_type="pricing_question_detection"
    #    If detected: draft holding response + send pricing_query to Finance
    # 3. Check for scope creep via scope_monitor.check_message()
    # 4. Classify message type:
    #    data_type="message_classification"
    # 5. If routine: log_auto
    # 6. If non-routine: draft response → queue REVIEW
    # 7. Log: action_type="inbound_message_handled"

    def draft_response(
        self,
        client_id: str,
        project_id: str | None,
        inbound_message: str,
        response_type: str
    ) -> str: ...
    # Generate response via inference: data_type="response_drafting"
    # Load client communication history for tone context
    # Never include pricing unless pricing_response is confirmed
    # Return draft response text

    def send_auto_response(
        self,
        client_id: str,
        message_text: str
    ) -> None: ...
    # Send without War Room approval (AUTO mode)
    # Only for truly routine types: confirmations, acknowledgments
    # Log to comms.log: direction="sent"
    # Log: action_type="auto_response_sent"

    def send_deep_work_response(
        self,
        client_id: str,
        resume_date: str
    ) -> None: ...
    # Read template from templates/deep-work-response.md
    # Substitute resume_date
    # Send automatically (AUTO — Deep Work Mode)
    # Log to comms.log and operational.log

    def is_deep_work_active(self) -> bool: ...
    # Read ~/.milimo/config.json
    # Return config.deep_work.active if present, else False
```

Write pytest tests: inbound pricing question sends pricing_query to Finance,
scope creep check triggered on every inbound, routine messages auto-logged,
non-routine messages queue REVIEW, deep work response uses correct template
and substitutes resume_date, is_deep_work_active reads from config correctly.

---

## PHASE 4 — SCHEDULING AND ENTRY POINT
## Complete all Phase 3 tests before starting Phase 4.

---

### TASK 4.1 — Ops Scheduler

**New file:** `milimo-blueprint/orchestrator/ops/ops_scheduler.py`

```python
import threading
from datetime import datetime, timedelta
from typing import Callable

class OpsScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Ops Claw.

    Schedule:
      Daily  09:00 — Deadline risk check for all active projects
      Daily  09:00 — Inquiry staleness check (24h/48h urgency flags)
      Weekly Sunday 02:00 — Client health scoring for all active clients
      On startup — Check for missed jobs

    Uses threading.Timer. No cron. No APScheduler. Only stdlib.
    """

    def __init__(
        self,
        project_manager: "ProjectManager",
        intake_manager: "IntakeManager",
        health_scorer: ClientHealthScorer,
        comms_manager: CommsManager,
        operational_log: OpsOperationalLog
    ): ...

    def start(self) -> None: ...
    # Initialize all scheduled timers
    # Check for missed jobs since last shutdown
    # Log: action_type="scheduler_started"

    def stop(self) -> None: ...
    # Cancel all pending timers cleanly
    # Log: action_type="scheduler_stopped"

    def _run_daily_deadline_check(self) -> None: ...
    # project_manager.check_all_deadlines()
    # intake_manager._check_inquiry_staleness()
    # Log timing

    def _run_weekly_health_scoring(self) -> None: ...
    # health_scorer.score_all_active_clients()
    # Log timing

    def _check_missed_jobs(self) -> None: ...
    # Read last_run timestamps from operational.log
    # If weekly health scoring last ran > 8 days ago: run immediately
    # If daily deadline check last ran > 36 hours ago: run immediately
    # Log any recovered jobs

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None  # 0=Monday, 6=Sunday
    ) -> float: ...
```

Write pytest tests: scheduler starts and stops cleanly, missed health
scoring triggers on startup when last run > 8 days, missed deadline check
triggers when last run > 36 hours, self-rescheduling verified after
execution, _seconds_until returns positive float for any future target.

---

### TASK 4.2 — Ops Claw Main Entry Point

**New file:** `milimo-blueprint/orchestrator/ops/ops_claw.py`

```python
from typing import Any

class OpsClaw:
    """
    Main entry point for the Ops Claw.
    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(self, squad_id: str, inference_client: Any): ...

    def startup(self) -> None: ...
    # 1. Run filesystem init — validate structure
    # 2. Log startup to operational.log
    # 3. Initialize all components with shared dependencies
    # 4. Register inbound message handlers with mesh router:
    #    - deliverable_complete → project_manager.handle_deliverable_complete
    #    - deploy_complete → project_manager.handle_deploy_complete
    #    - pricing_response → intake_manager.handle_pricing_response
    #                         AND project_manager.handle_pricing_response
    #    - invoice_ready → log AUTO (Ops tracks for client record)
    #    - payment_overdue → queue War Room REVIEW for follow-up
    # 5. Register approval flow handlers with War Room
    # 6. Start ops_scheduler
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

### TASK 4.3 — Integration Test Suite (10-Step MVR)

**New file:** `milimo-blueprint/tests/test_ops_integration.py`

```python
class TestOpsMVR:

    def test_mvr_01_inject_test_inquiry(self):
        """Manually inject a test inquiry — Ops Claw receives it."""

    def test_mvr_02_triage_score_in_war_room(self):
        """Triage score appears in War Room card format (94/100 style)."""

    def test_mvr_03_approve_welcome_message(self):
        """Approve welcome — confirm sent via email API (mocked)."""

    def test_mvr_04_inject_client_brief_response(self):
        """Inject mock client response with complete project brief."""

    def test_mvr_05_brief_quality_check_runs(self):
        """Brief quality check runs — flags or passes the brief."""

    def test_mvr_06_pricing_query_sent_to_finance(self):
        """Confirm pricing_query dispatched to Finance Claw."""

    def test_mvr_07_inject_pricing_response(self):
        """Inject mock pricing_response from Finance Claw."""

    def test_mvr_08_project_brief_queued_for_review(self):
        """After pricing confirmed, project_brief queued as REVIEW."""

    def test_mvr_09_approve_project_brief(self):
        """Operator approves project_brief in War Room."""

    def test_mvr_10_creative_claw_receives_brief(self):
        """Confirm Content or Build Claw receives project_brief via mesh."""
```

Step 6 is the critical sequencing test. Verify that no `project_brief`
is dispatched before `pricing_response` is received and stored. Use a
mock dispatcher and assert call_count == 0 on `send_project_brief`
until after `handle_pricing_response` is called.

---

## FINAL VERIFICATION CHECKLIST

□ /sandbox/clients/ full structure created on ops_init
□ All template files created with correct content
□ All log files created (operational, comms, decisions)
□ Filesystem init is idempotent — no errors on repeated calls
□ pricing_query schema added to contracts.py
□ client_onboarded schema added to contracts.py
□ client_health_signal sender_roles includes "ops"
□ Triage score: budget 0.4, scope 0.3, fit 0.3 — correct weights
□ Score ≥ 80 → auto-draft welcome + questionnaire
□ Score 50–79 → flag for review, no draft
□ Score < 50 → AUTO (morning digest only)
□ Triage fallback on inference failure — score 5.0, flag for review
□ Brief quality check detects missing deadline and unclear scope
□ pricing_query sent after brief quality check passes
□ NO project_brief sent before pricing_response received
□ project_brief dispatched after proposal REVIEW approved
□ Deliverable complete → delivery message queued as REVIEW (not AUTO)
□ project_complete sent ONLY after client_confirmed = True
□ project_complete NOT sent on deliverable receipt alone
□ Deadline: 5 days → REVIEW (elevated)
□ Deadline: 24 hours → HOLD (critical)
□ Scope creep confidence > 0.7 → HOLD change order (never REVIEW)
□ Change order pricing query sent to Finance Claw on detection
□ Client health scoring runs weekly Sunday 02:00
□ At_risk clients (< 6.0) flagged in War Room immediately
□ client_health_signal sent for ALL clients regardless of score
□ Rapid messages grouped within 30-minute window
□ Inquiry staleness: urgency flag at 24h, escalation text at 48h
□ Deep Work auto-response sends without approval when active
□ Pricing question detection drafts holding response
□ All inbound message types wired to correct handlers
□ Scheduler detects missed jobs on startup and recovers
□ data_type logged on every inference call
□ All 10 MVR integration tests pass
□ Step 6 explicitly asserts no project_brief before pricing confirmed
□ All unit tests pass: pytest milimo-blueprint/orchestrator/ops/

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  File: [exact path — NEW or UPDATE]
  Summary: [one sentence]

  [complete implementation — no TODOs, no stubs, no placeholders]

  Tests: [complete pytest file immediately after]
  -----------------------------------------

Begin with Task 0.1 (contracts fix). Do not proceed to Task 1.1 until
Task 0.1 tests pass. Do not proceed to Phase 2 until all Phase 1 tests
pass. The spec is ground truth. All inference to cloud. Log data_type
on every call. pricing_query before project_brief — always.
