# MILIMO CLAW — OPS CLAW FUNCTIONAL SPECIFICATION
# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI assistant when you need it to understand
# exactly how the Ops Claw is supposed to work — for debugging,
# feature implementation, testing, or documentation.
#
# DEVELOPMENT NOTE: This implementation is in active development and testing.
# All inference currently routes to cloud (Nemotron 120B via NVIDIA Cloud API)
# regardless of data sensitivity. The privacy routing rules documented here
# represent the production target architecture. Do not implement privacy
# routing enforcement during this phase — route everything to cloud.
# Log the data_type field on every inference call so routing can be enforced
# later without touching call sites.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug the **Ops Claw** inside Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw. Read
this entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation deviates
from it, the implementation is wrong — not this spec.

---

## WHAT THE OPS CLAW IS

The Ops Claw is the account manager, project manager, and client
communications director of a Milimo Claw squad. It runs 24/7 inside an
isolated NemoClaw sandbox, managing the full client lifecycle — from the
moment an inquiry arrives to the moment a project is delivered and closed.

It handles the work that most solo operators and student squads drown in:
chasing inquiries, scoping projects, tracking deadlines, managing client
communication, flagging scope creep, and ensuring nothing falls through
the cracks. Every action it takes is logged. Every significant decision
escalates to the War Room.

The Ops Claw is not a CRM. It is an autonomous account manager that
knows every active client, every open project, every approaching deadline,
and every risk — and acts on that knowledge without being told to.

---

## IDENTITY AND ISOLATION

**Sandbox name:** ops-claw
**Plugin namespace:** openclaw milimo ops
**Blueprint file:** milimo-blueprint/roles/ops-claw.yaml
**Sandbox policy:** milimo-blueprint/policies/ops-sandbox.yaml
**Filesystem mount:** /sandbox/clients

The Ops Claw owns the most sensitive data in the entire squad: client
contact details, project histories, communication logs, and contract terms.
This data is isolated at the kernel level via NVIDIA OpenShell Landlock
filesystem restrictions. No other claw can read /sandbox/clients directly.
Data is shared only through typed inter-claw messages.

---

## FILESYSTEM LAYOUT

Everything the Ops Claw owns lives under /sandbox/clients:

```
/sandbox/clients/
├── active/
│   └── {client_id}/
│       ├── profile.json          # contact details, preferences, history
│       ├── projects/
│       │   └── {project_id}/
│       │       ├── brief.json    # original brief and requirements
│       │       ├── status.json   # current project state
│       │       ├── timeline.json # milestones, deadlines, risks
│       │       └── comms/        # communication log for this project
│       └── comms/                # client-level communication history
│
├── prospects/
│   └── {inquiry_id}/
│       ├── inquiry.json          # raw inquiry data
│       ├── triage.json           # triage score and recommendation
│       └── comms/                # prospect communication log
│
├── completed/
│   └── {client_id}/              # archived after all projects closed
│
├── contracts/
│   └── {client_id}/
│       └── {contract_id}.json    # contract terms, scope, pricing
│
├── templates/
│   ├── welcome-message.md
│   ├── intake-questionnaire.md
│   ├── proposal-template.md
│   ├── change-order-template.md
│   ├── delivery-message.md
│   └── deep-work-response.md     # auto-response for Deep Work Mode
│
└── logs/
    ├── operational.log           # every action taken, timestamped
    ├── comms.log                 # all client communications sent/received
    └── decisions.log             # all War Room escalations and decisions
```

What the Ops Claw can read:
- Everything under /sandbox/clients/
- /sandbox/analytics/reports/weekly-intelligence.json (read-only mount)

What the Ops Claw cannot read under any circumstances:
- /sandbox/content/  — creative drafts and brand assets
- /sandbox/finance/  — financial records and invoices
- /sandbox/build/    — source code and secrets

---

## NETWORK EGRESS POLICY

Approved client communication channels:
  api.gmail.com           — email send/receive for client comms
  api.sendgrid.com        — transactional email alternative
  api.calendly.com        — scheduling links
  api.notion.com          — project management sync (optional)
  api.airtable.com        — CRM data sync (optional)

Approved read-only:
  api.linkedin.com        — prospect research (read-only)

Blocked:
  api.stripe.com          — Finance Claw only
  api.twitter.com         — Content Claw only
  api.github.com          — Build Claw only
  All other endpoints     — strict default-deny

Critical rule: The Ops Claw handles client communication but never
touches financial systems. Invoicing is triggered by sending a message
to Finance Claw — never generated by Ops directly.

---

## INFERENCE ROUTING

DEVELOPMENT / TESTING PHASE: All inference routes to cloud.
Log data_type on every call for future routing enforcement.

Production target routes (reference only — not enforced during dev):

  Data Type                  | Route
  ─────────────────────────────────────────────────────
  Client-facing messages     | Cloud  (quality matters)
  Proposals and pitches      | Cloud  (high-stakes)
  Internal project summaries | Local  (sensitive business context)
  Contract review/risk       | Local  (legal-adjacent)
  Scheduling optimization    | Cloud  (non-sensitive)
  Client triage scoring      | Cloud  (pattern matching)
  Scope creep detection      | Local  (contains client IP)

---

## WHAT THE OPS CLAW DOES AUTONOMOUSLY

All actions are logged to /sandbox/clients/logs/operational.log
with ISO timestamp, action_type, entity_id, and outcome.

---

### CLIENT INQUIRY INTAKE

When a new inquiry arrives via an approved ingress channel:

STEP 1 — TRIAGE SCORING
  Score the inquiry on three dimensions (0–10 each):
  - Budget signal:   keywords, numbers, context suggesting budget range
  - Scope clarity:   how well-defined the request is
  - Niche fit:       how well prospect matches squad's focus areas
  Triage score = (budget × 0.4) + (scope × 0.3) + (fit × 0.3)

STEP 2 — DECISION ROUTING by triage score:
  Score ≥ 80:  Draft welcome message + intake questionnaire → queue REVIEW
  Score 50–79: Flag inquiry for operator review with triage summary → queue REVIEW
               Do NOT draft message without operator approval
  Score < 50:  Log as low-priority → queue AUTO (morning digest only)

STEP 3 — BRIEF QUALITY CHECK (after client responds to questionnaire)
  Check for: missing deadline, undefined scope, unclear deliverables,
  contradictory requirements.
  - If gaps found: draft clarifying question → queue REVIEW
  - If clear: write brief.json, send project_brief to Content or Build Claw
  Always send pricing_query to Finance Claw BEFORE sending project_brief.
  Never send project_brief without receiving pricing_response first.

---

### ACTIVE PROJECT MANAGEMENT

DEADLINE RISK PREDICTION (daily check):
  If deadline within 5+ days and deliverable shows risk:
    → flag War Room REVIEW with risk summary
  If deadline within 24 hours and deliverable not received:
    → escalate War Room HOLD

SCOPE CREEP DETECTION (on every client communication):
  Scan for requests outside original brief.json scope.
  If detected: draft change order → queue HOLD
  Change order includes: original scope reference, new request,
  Finance Claw pricing estimate (must await pricing_response).
  Nothing additional delivered until operator approves change order
  AND client accepts.

CLIENT COMMUNICATION MANAGEMENT:
  - Routine updates: AUTO (logged, morning digest)
  - Non-routine communications: REVIEW (drafted, operator approves)
  - Never reference pricing without Finance Claw pricing_response confirmed
  - Log every communication to /sandbox/clients/{id}/comms/

CLIENT HEALTH SCORING (weekly):
  Score each active client 0–10 based on:
  - Response time to messages
  - Revision request frequency
  - Communication sentiment
  - Scope adherence
  If health score < 6.0: flag War Room with recommended action
  Send client_health_signal to Analytics Claw weekly regardless of score

---

### PROJECT DELIVERY

When Content or Build Claw sends deliverable_complete:
  1. Receive message
  2. Draft delivery message to client → queue REVIEW
  3. After operator approves and delivery confirmed by client:
     a. Send project_complete to Finance Claw → triggers invoice
     b. Move project to completed status
     c. Update client health record
     d. Log delivery to operational.log

---

## INTER-CLAW COORDINATION

All communication via typed message contracts through OpenShell gateway.

MESSAGES OPS CLAW RECEIVES:

  deliverable_complete  | Content Claw  | On publish
    project_id, published_urls, performance_baseline

  deploy_complete       | Build Claw    | On production deploy
    project_id, deploy_url, version

  pricing_response      | Finance Claw  | Response to query
    project_id, floor_price, ceiling_price, scope_notes

  invoice_ready         | Finance Claw  | Invoice generated
    project_id, client_id, amount, invoice_id

  payment_overdue       | Finance Claw  | Payment late
    client_id, invoice_id, days_overdue, amount

MESSAGES OPS CLAW SENDS:

  project_brief         | Content or Build Claw  | New project confirmed
    client_id, project_id, brief_text, deadline,
    tone_requirements, platform_targets

  feature_brief         | Build Claw             | New technical feature
    client_id, project_id, feature_description,
    deadline, acceptance_criteria

  pricing_query         | Finance Claw           | Before any proposal
    project_id, scope_description, complexity_estimate, deadline

  project_complete      | Finance Claw           | Delivery confirmed
    project_id, client_id, delivered_at

  client_health_signal  | Analytics Claw         | Weekly
    client_id, health_score, health_factors, recommended_action

  client_onboarded      | Analytics Claw         | New client onboarded
    client_id, niche, project_type, estimated_value

SEQUENCING RULES (non-negotiable):
  - pricing_query MUST be sent and pricing_response received BEFORE
    project_brief is sent to any creative claw
  - project_complete MUST only be sent after client confirms receipt
    of deliverables — not on internal completion
  - client_health_signal MUST be sent weekly regardless of score value

---

## WAR ROOM APPROVAL FLOW

No client-facing message leaves the Ops Claw without operator approval.

APPROVAL MODES:

  Action                     | Mode   | Behavior
  ───────────────────────────────────────────────────────────────────
  New client welcome message | REVIEW | Ops drafts, operator approves
  Intake questionnaire       | REVIEW | Ops drafts, operator approves
  Client proposal            | REVIEW | Always surfaced — every proposal
  Project brief to claws     | REVIEW | Operator confirms before work begins
  Routine client update      | AUTO   | Logged, visible in morning digest
  Deadline risk flag         | REVIEW | Operator sees risk + recommendation
  Deadline critical (24hr)   | HOLD   | Explicit operator action required
  Scope creep change order   | HOLD   | Never auto-handled
  Client delivery message    | REVIEW | Ops drafts, operator approves
  Deep Work auto-response    | AUTO   | Sends automatically in Deep Work Mode

War Room card format for Ops actions:

  🟡 REVIEW   OPS CLAW                    4 mins ago
  ─────────────────────────────────────────────────────
  New client inquiry — @PulseMedia
  Triage score: 94/100
  Budget signal: 9  ·  Scope clarity: 9  ·  Niche fit: 9

  Welcome message + intake questionnaire drafted

  [View Message]  [APPROVE]  [EDIT]  [BLOCK]

AFTER OPERATOR DECISION:

  APPROVE:
    Send message via approved channel API
    Log to comms.log and decisions.log
    Queue next step automatically (await response, track deadline)

  EDIT:
    Preserve original draft for training signal
    Send edited version (no re-review unless operator requests)
    Log edit delta to decisions.log as training signal

  BLOCK:
    Discard draft — do not send
    Log block reason to decisions.log
    For blocked welcome messages: log inquiry as declined
    Do not retry — wait for operator to initiate

---

## THE SELF-EVOLUTION CYCLE

Runs every Sunday at 02:00. Same 5-stage pipeline as all claws.
(Observe → Identify → Propose → Build → Deploy)

WHAT THE OPS CLAW OBSERVES:
  - decisions.log: every APPROVE/EDIT/BLOCK and edit patterns
  - comms.log: client response times and communication outcomes
  - Project status files: on-time vs late delivery rates
  - Triage history: which scores led to good/bad client relationships
  - Scope creep log: which project types triggered changes

PATTERNS IDENTIFIED:
  - Which triage thresholds correlate with successful projects?
  - Which communication styles generate faster client responses?
  - Which project types consistently run over scope?
  - Which deadlines are systematically underestimated?
  - Which brief gaps cause the most revision cycles?

EVOLUTION TOOLS THAT EMERGE:

  Week 3   | Client triage scorer v2       | Calibrated to squad's actual client outcomes
  Week 6   | Brief quality checker         | Flags ambiguous briefs before work begins
  Week 10  | Deadline risk predictor       | Predicts delivery risk 5+ days out
  Week 15  | Communication tone calibrator | Learns each client's preferred comms style
  Week 20  | Scope creep detector v2       | Detects subtle expansion patterns
  Week 28  | Relationship health scorer v2 | Predicts churn from early-stage signals

MINIMUM THRESHOLDS BEFORE FIRST EVOLUTION:
  - 5 completed client interactions (inquiries handled, any outcome)
  - 3 active or completed projects
  - 2 weeks of communication log data

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE

Day 1–7 (baseline):
  Ops Claw intercepts inquiries, runs basic triage scoring.
  Every outbound communication surfaces in War Room.
  Operator spends 15–25 minutes/day on Ops War Room actions.

Week 3–4 (first tools):
  Triage scorer calibrated — fewer low-quality inquiries reaching operator.
  Operator time drops to 10–15 minutes/day.

Month 2–3 (compound tools):
  Brief quality checker active — revision cycles shorter.
  Deadline risk predictor active — no surprise late deliveries.
  Communication tone calibrator active — tone adapts per client automatically.
  Operator time: 8–12 minutes/day.

Month 6+ (mature operation):
  Scope creep detector v2 active — change orders before scope bleeds.
  Relationship health scorer v2 active — churn predicted 2 weeks early.
  Ops Claw handles 80%+ of routine client management autonomously.
  Operator Ops time: under 10 minutes/day.

---

## WHAT FAILURE LOOKS LIKE (DEBUGGING REFERENCE)

  Symptom                                | Likely Cause
  ─────────────────────────────────────────────────────────────────────
  Inquiry not in War Room                | Ingress channel not connected
  Triage scoring returns 0               | Inference call failure in triage
  Welcome message sent without approval  | Approval mode wrong — must be REVIEW
  project_brief sent before pricing      | Sequencing bug — await pricing_response
  Deadline risk not flagging             | Timeline monitor not scheduled
  Scope creep not detected               | Detector not evolved (week 20+) or off
  client_health_signal not sent          | Health scorer not scheduled
  Change order not drafted               | Scope creep threshold too high
  Delivery message sent without approval | Approval handler misconfigured
  Pricing query times out                | Finance Claw unavailable — check mesh
  Deep Work auto-response not sending    | Deep Work state not read from config
  comms.log not updating                 | File write permission on /sandbox/clients

---

## MINIMUM VIABLE FIRST RUN — TESTING SEQUENCE

Use this sequence to verify the Ops Claw is working before enabling
full autonomy:

  1. Inject a test inquiry manually via CLI or War Room
  2. Confirm triage score appears in War Room card (94/100 format)
  3. Approve welcome message — confirm it sends via email API
  4. Inject mock client response with a complete project brief
  5. Confirm brief quality check runs — flag or pass
  6. Confirm pricing_query sent to Finance Claw
  7. Inject mock pricing_response from Finance Claw
  8. Confirm project_brief queued for operator review
  9. Approve project_brief
  10. Confirm Content Claw or Build Claw receives the message via mesh

All 10 steps must work before any autonomous scheduling is enabled.

---

## FILES TO BUILD

  orchestrator/ops/ops_init.py           | Filesystem structure initialization
  orchestrator/ops/intake_manager.py     | Inquiry triage, welcome, intake flow
  orchestrator/ops/project_manager.py    | Project lifecycle, deadline tracking
  orchestrator/ops/comms_manager.py      | Communication log, tone calibration
  orchestrator/ops/scope_monitor.py      | Scope creep detection, change orders
  orchestrator/ops/health_scorer.py      | Client relationship health scoring
  orchestrator/ops/approval_handler.py   | War Room approve/edit/block handlers
  orchestrator/ops/ops_scheduler.py      | Scheduled autonomous actions
  milimo-blueprint/roles/ops-claw.yaml   | Role blueprint (may already exist)
  milimo-blueprint/policies/ops-sandbox.yaml | Sandbox policy (may already exist)

---

## SPEC EDGE CASES

Rapid-succession messages from same client:
  Group messages within 30-minute window into single War Room card.
  Last message in window triggers the card.

Pricing query timeout (no response in 10 minutes):
  Escalate War Room: "Finance Claw pricing query timed out for project
  {project_id} — proceed with manual pricing or retry?"
  Never send proposal without pricing confirmation.

Operator ignores inquiry for 24 hours:
  Add urgency flag: "No decision in 24h — client may disengage."
  After 48 hours: "Response window closing."
  Never send without approval. Ever.

Client asks about pricing directly:
  Send pricing_query to Finance Claw.
  Draft holding response: "Let me put together a proposal with exact
  figures and get back to you shortly." — queue REVIEW.
  When pricing_response arrives: draft full pricing response → REVIEW.

Scope creep detected during delivery:
  Draft change order → HOLD.
  Include: original brief scope reference, new request description,
  Finance Claw pricing estimate.
  Nothing additional delivered until operator approves AND client accepts.

---

*This specification is the ground truth for the Ops Claw.
If behavior in the codebase deviates from this document, the code is wrong.*

*Development note: All inference routes to cloud during testing.
Log data_type on every inference call for future routing enforcement.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
