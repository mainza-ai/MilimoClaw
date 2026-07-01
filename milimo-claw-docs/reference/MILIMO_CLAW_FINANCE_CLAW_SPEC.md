# MILIMO CLAW — FINANCE CLAW FUNCTIONAL SPECIFICATION

> **NemoClaw Path Notice (2026-05-01)**
>
> This spec uses `/sandbox/.openclaw/milimo/` as the canonical base directory. The older `/sandbox/.openclaw/milimo/` path is deprecated.
>
> **Key paths:**
>
> - **Claw data**: `/sandbox/.openclaw/milimo/claws/<role>/` — each claw's sandbox, tools, and operational data
> - **Bridge CLI**: `python3 /sandbox/.openclaw/milimo/milimo-blueprint/orchestrator/bridge_cli.py --command <name> --args '{...}'`
> - **Mesh**: `/sandbox/.openclaw/milimo/mesh/` — heartbeats, inbox, outbox, topology
> - **State**: `/sandbox/.openclaw/milimo/state/` — evolution history, deep work sessions
> - **Health**: `/sandbox/.openclaw/milimo/health/` — per-squad health metrics
> - **Evolution tools**: registered at `/sandbox/.openclaw/milimo/claws/<role>/sandbox/tools/` after evolution cycle runs
>
> **Evolution cycle**: Tools are NOT pre-installed. The weekly evolution cycle (observe → identify → propose → build → deploy) registers tools automatically. If `tool_count = 0`, that means the evolution cycle has not yet run — this is expected for fresh installs.
>
> If this spec conflicts with the official NemoClaw/OpenShell docs, the official docs win.

# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI assistant when you need it to understand
# exactly how the Finance Claw is supposed to work — for debugging,
# feature implementation, testing, or documentation.
#
# DEVELOPMENT NOTE: This implementation is in active development and testing.
# All inference currently routes to cloud (the configured NEMOCLAW_MODEL via NVIDIA Cloud API)
# regardless of data sensitivity. The privacy routing rules documented here
# represent the production target architecture — in production, ALL financial
# data must be routed to local NIM with zero exceptions. This is the most
# sensitive claw in the entire mesh. Do not implement privacy routing
# enforcement during this phase — route everything to cloud.
# Log the data_type field on every inference call so routing can be enforced
# later without touching call sites.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug the **Finance Claw** inside Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw. Read
this entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation deviates
from it, the implementation is wrong — not this spec.

---

## WHAT THE FINANCE CLAW IS

The Finance Claw is the financial nervous system of a Milimo Claw squad.
It tracks every dollar that moves through the operation — revenue, invoices,
expenses, margins, and tax categories — and ensures the squad never
undercharges, never misses a payment, and always knows exactly where it
stands financially.

It does not communicate with clients. It does not write code. It does not
create content. It does one thing: manage money with precision and surface
financial intelligence that protects the squad's operation.

The Finance Claw is not an accounting app. It is an autonomous financial
operator that monitors every transaction, predicts payment risk before
invoices are sent, flags margin compression before it becomes a problem,
and surfaces rate optimization recommendations before the squad leaves
money on the table — all without being asked.

---

## IDENTITY AND ISOLATION

**Sandbox name:** `finance-claw`
**Plugin namespace:** `openclaw milimo finance`
**Blueprint file:** `milimo-blueprint/roles/finance-claw.yaml`
**Sandbox policy:** `milimo-blueprint/policies/finance-sandbox.yaml`
**Filesystem mount:** `/sandbox/finance`

The Finance Claw holds the most financially sensitive data in the squad:
revenue records, invoice history, payment details, pricing rules, expense
logs, and tax categories. This data is isolated at the kernel level via
NVIDIA OpenShell Landlock filesystem restrictions.

**No other claw can read `/sandbox/finance` directly.**
Finance shares data only through typed inter-claw messages — and only
summary-level data at that. The Analytics Claw receives revenue totals,
never line-item records. The Ops Claw receives pricing floor and ceiling
for a specific project, never the full pricing ruleset.

This isolation is architectural, not policy-based. It cannot be bypassed
by any instruction the claw receives.

---

## FILESYSTEM LAYOUT

Everything the Finance Claw owns lives under `/sandbox/finance`:

```
/sandbox/finance/
├── revenue/
│   ├── weekly-summary.json          # current week totals (read by War Room)
│   ├── monthly-summary.json         # current month rollup
│   ├── annual-summary.json          # YTD totals
│   └── history/
│       └── {YYYY-MM-DD}.json        # daily revenue snapshots
│
├── invoices/
│   ├── pending/
│   │   └── {invoice_id}.json        # generated, awaiting operator approval
│   ├── approved/
│   │   └── {invoice_id}.json        # approved, awaiting send
│   ├── sent/
│   │   └── {invoice_id}.json        # sent to client, awaiting payment
│   ├── paid/
│   │   └── {invoice_id}.json        # payment confirmed
│   └── overdue/
│       └── {invoice_id}.json        # past due date, unpaid
│
├── expenses/
│   ├── log.jsonl                    # append-only expense log
│   └── categories/
│       └── {category}.json          # categorized expense summaries
│
├── pricing/
│   ├── rules.json                   # pricing floors, ceilings, scope weights
│   ├── estimates/
│   │   └── {project_id}.json        # cost estimates per project
│   └── history/
│       └── {project_id}.json        # actual vs estimated cost tracking
│
├── tax/
│   ├── categories.json              # income and expense tax categories
│   ├── quarterly/
│   │   └── {YYYY-Q}.json            # quarterly tax prep summaries
│   └── annual/
│       └── {YYYY}.json              # annual tax summary
│
└── logs/
    ├── operational.log              # every action taken, timestamped
    ├── decisions.log                # War Room escalations and decisions
    └── payment-events.log           # all payment status changes
```

**What the Finance Claw can read:**
- Everything under `/sandbox/finance/`
- `/sandbox/.openclaw/milimo/claws/analytics/reports/weekly-intelligence.json` (read-only mount)
  — used for revenue anomaly context and market rate benchmarking

**What the Finance Claw cannot read under any circumstances:**
- `/sandbox/clients/` — client contact data (Ops Claw only)
- `/sandbox/content/` — creative assets (Content Claw only)
- `/sandbox/build/` — source code and secrets (Build Claw only)
- `/sandbox/assistant/` — session data and context (Assistant Claw only)

The Assistant Claw (`/sandbox/assistant`) likewise cannot read the Finance
Claw's primary mount or any other claw's primary mount — isolation is mutual.

---

## NETWORK EGRESS POLICY

The Finance Claw has the most restricted network access in the squad.

**Approved read-only endpoints:**
```
api.stripe.com                   # payment status checks — GET only
                                 # invoice send via Stripe API
api.paypal.com                   # PayPal payment status — GET only
api.wise.com                     # international transfer status — GET only
api.mercury.com                  # banking API — read-only balance checks
```

**Approved write endpoints (invoice send only):**
```
api.stripe.com                   # POST to create and send invoice
                                 # Requires HOLD operator approval first
```

**Blocked — everything else:**
```
api.gmail.com                    # Finance Claw never communicates
api.twitter.com                  # Finance Claw never publishes
api.github.com                   # Finance Claw never touches code
All other endpoints              # strict default-deny
```

**Approved write endpoints (agent spend via stripe-link-cli):**
```
link-cli spend-request create          # Agent-initiated purchases
                                       # Requires double-gate: War Room
                                       # HOLD release + Link app approval
```

**Critical rules:**
1. The Finance Claw never communicates directly with clients.
   All client-facing invoice delivery happens via Stripe's invoice system
   after operator HOLD approval — not via email or any other channel.
2. The Finance Claw never initiates outbound financial transfers.
   It reads payment status only. It does not initiate payments.
3. **Agent spend** via stripe-link-cli requires **two independent human gates**:
   Gate 1: War Room HOLD release (operator explicitly releases the spend hold)
   Gate 2: Stripe Link app (user taps approve on their phone — no agent can self-approve)
4. Every external API call is logged to payment-events.log.

---

## INFERENCE ROUTING

**Development / testing phase:** All inference routes to cloud.
Log `data_type` on every inference call. This is mandatory even during
dev — the data_type field is what enables future routing enforcement
without changing call sites.

**Production target routes (reference only — NOT enforced during dev):**

| Data Type | Production Route | Reason |
|---|---|---|
| Scope cost estimation | Local NIM | Contains project and client context |
| Invoice generation | Local NIM | Financial records — never cloud |
| Pricing analysis | Local NIM | Proprietary pricing strategy |
| Payment risk scoring | Local NIM | Contains client payment history |
| Tax category classification | Local NIM | Financial records |
| Margin analysis | Local NIM | Core business intelligence |
| Rate benchmarking narrative | Local NIM | Competitive pricing data |
| Market rate research | Cloud (NEMOCLAW_MODEL) | Public market data only |

**In production, ALL inference involving financial data routes to local
NIM. There are no exceptions. This is the most strictly enforced privacy
rule in the entire Milimo Claw system. During development, cloud is
used — but the data_type field must be logged on every single call.**

---

## WHAT THE FINANCE CLAW DOES AUTONOMOUSLY

All actions are logged to `/sandbox/finance/logs/operational.log`
with ISO timestamp, action_type, entity_id, and outcome.

---

### PRICING QUERIES

When the Ops Claw sends a `pricing_query` before any proposal:

1. Read the project scope from the query payload
2. Load pricing rules from `/sandbox/finance/pricing/rules.json`
3. Run scope cost estimation via inference:
   - data_type: "scope_cost_estimation"
   - Inputs: scope_description, complexity_estimate, deadline
   - Output: estimated hours, rate recommendation, floor, ceiling
4. Check historical estimates vs actuals from `pricing/history/`
   to calibrate the current estimate
5. Respond with `pricing_response` message to Ops Claw within 10 minutes
6. Write estimate to `/sandbox/finance/pricing/estimates/{project_id}.json`
7. Log to operational.log: action_type="pricing_query_answered"

**Pricing response SLA: 10 minutes maximum.**
If estimation takes longer, respond with best available approximation
and a `data_quality: "estimated"` flag. Never timeout silently.

---

### INVOICE GENERATION

When the Ops Claw sends a `project_complete` message:

1. Load project record and pricing estimate from
   `/sandbox/finance/pricing/estimates/{project_id}.json`
2. Cross-reference with actual delivery scope (from Ops message payload)
3. Generate invoice via inference:
   - data_type: "invoice_generation"
   - Includes: line items, payment terms, due date (net 14 default),
     payment instructions
4. Run payment risk score on this client (from payment history)
5. Write invoice to `/sandbox/finance/invoices/pending/{invoice_id}.json`
6. Queue in War Room: REVIEW mode
   - Shows: client, amount, line items, payment risk score, due date
7. Log to operational.log: action_type="invoice_generated"

**Invoice never sends without two-stage operator approval:**
- Stage 1 (REVIEW): Operator reviews the invoice content and amount
- Stage 2 (HOLD release): Operator explicitly triggers the send

This two-stage requirement is non-negotiable. A single approval is
not sufficient for invoice send.

---

### PAYMENT MONITORING

After an invoice is sent (moved to `invoices/sent/`):

1. Check payment status via Stripe API every 24 hours
2. On payment confirmed:
   - Move invoice: `sent/` → `paid/`
   - Update `revenue/weekly-summary.json`
   - Update `revenue/history/{today}.json`
   - Log to payment-events.log: payment_received
   - Send `revenue_summary` to Analytics Claw (weekly totals update)
   - Log to operational.log: action_type="payment_received"

3. On payment overdue (due date passed, unpaid):
   - Move invoice: `sent/` → `overdue/`
   - Escalate to War Room: REVIEW
   - Log to payment-events.log: payment_overdue
   - Send `payment_overdue` message to Ops Claw
   - Log to operational.log: action_type="payment_overdue"

4. On repeat overdue from same client (2+ invoices):
   - Escalate to War Room: HOLD
   - Flag client in payment risk model as high-risk
   - Log to payment-events.log: repeat_overdue_flagged

---

### EXPENSE LOGGING

Expenses are logged by the Finance Claw when:
- A platform subscription cost is detected from connected accounts
- The operator manually logs an expense via War Room or CLI
- An AI inference cost is detected from API usage tracking

For each expense:
1. Append to `/sandbox/finance/expenses/log.jsonl`
2. Run tax category classification via inference:
   - data_type: "tax_category_classification"
   - Classify as: software, contractor, marketing, equipment, etc.
3. Update category summary in `expenses/categories/{category}.json`
4. Log to operational.log: action_type="expense_logged" (AUTO — no approval)

---

### WEEKLY REVENUE SUMMARY

Every Sunday at 03:00 (after Analytics report at 02:00):

1. Aggregate all `paid/` invoices from the past 7 days
2. Calculate: week_total, invoices_paid count, invoices_pending count
3. Calculate week-over-week change vs previous Sunday snapshot
4. Update `/sandbox/finance/revenue/weekly-summary.json`
5. Send `revenue_summary` to Analytics Claw
6. Run margin analysis via inference:
   - data_type: "margin_analysis"
   - Inputs: revenue, expenses, estimated hours, actual hours
7. If margin compression detected (actual margin < target by >10%):
   Flag War Room: REVIEW
8. Run rate optimization check:
   - Compare current rates against squad's delivery quality metrics
   - If consistently undercharging: queue rate recommendation as REVIEW
9. Log to operational.log: action_type="weekly_summary_generated"

---

### QUARTERLY TAX PREP

On the first day of each new quarter (Jan 1, Apr 1, Jul 1, Oct 1):

1. Aggregate all income from `invoices/paid/` for the quarter
2. Aggregate all expenses from `expenses/log.jsonl` for the quarter
3. Verify all expenses are tax-categorized (re-run classification on any
   uncategorized items)
4. Write quarterly summary to `/sandbox/finance/tax/quarterly/{YYYY-Q}.json`
5. Queue in War Room: AUTO (morning digest — no immediate action required)
6. Log to operational.log: action_type="quarterly_tax_prep"

---

## INTER-CLAW COORDINATION

All communication via typed message contracts through OpenShell gateway.

### Messages the Finance Claw RECEIVES:

| Message Type | From | When | Payload |
|---|---|---|---|
| `pricing_query` | Ops Claw | Before any proposal is sent | project_id, scope_description, complexity_estimate, deadline |
| `project_complete` | Ops Claw | Client confirms delivery | project_id, client_id, delivered_at |
| `spend_request` | Any claw | Agent wants to buy something | merchant_name, merchant_url, amount_cents, justification |
| `spend_review_decision` | War Room | Operator reviews spend | action_id, decision (approve/edit/block) |
| `spend_hold_decision` | War Room | Operator releases/cancels | action_id, decision (release/cancel) |

### Messages the Finance Claw SENDS:

| Message Type | To | When | Payload |
|---|---|---|---|
| `pricing_response` | Ops Claw | Within 10 min of pricing_query | project_id, floor_price, ceiling_price, scope_notes, data_quality |
| `invoice_ready` | Ops Claw | After operator approves invoice (Stage 1) | project_id, client_id, amount, invoice_id, due_date |
| `payment_overdue` | Ops Claw | When invoice passes due date unpaid | client_id, invoice_id, days_overdue, amount, risk_level |
| `revenue_summary` | Analytics Claw | Weekly Sunday + on payment received | week_total, week_over_week_pct, invoices_paid, invoices_pending |

### Message handling rules:
- `pricing_response` must be sent within 10 minutes of receiving
  `pricing_query` — even if the estimate is rough. Never leave Ops Claw
  waiting for a proposal it cannot send.
- `invoice_ready` is sent to Ops Claw to notify that an invoice has
  been approved and is ready to send — Ops Claw updates the client
  record accordingly. Finance Claw sends the actual invoice via Stripe.
- `revenue_summary` payload contains totals ONLY. Never include
  line-item invoice details, client names, or individual amounts.
  Analytics Claw receives aggregate data only.
- `payment_overdue` fires immediately when due date passes — does not
  wait for a weekly cycle or any other trigger.

---

## WAR ROOM APPROVAL FLOW

The Finance Claw has the strictest approval requirements of all six claws.
Money never moves without explicit human authorization.

### Approval modes for Finance Claw actions:

| Action | Mode | Behavior |
|---|---|---|
| Invoice generation (review content) | REVIEW | Operator reviews amount, line items, due date |
| Invoice send (trigger actual send) | HOLD | Explicit HOLD release required — second approval |
| Payment follow-up message | REVIEW | Drafted by Ops Claw — Finance just triggers |
| Expense log entry | AUTO | Logged, visible in morning digest |
| Overdue payment alert (first) | REVIEW | Operator sees, decides on follow-up action |
| Overdue payment alert (repeat) | HOLD | Escalation — operator must act |
| Pricing recommendation | REVIEW | Rate adjustment suggestion for operator decision |
| Margin compression alert | REVIEW | Operator informed — no immediate action required |
| Tax quarterly summary | AUTO | Logged, visible in morning digest |
| Rate optimization advisory | REVIEW | Recommendation only — operator decides |
| Spend request (agent purchase) | REVIEW | Stage 1: Review why agent wants to spend |
| Spend release (charge via Link) | HOLD | Stage 2: Release → link-cli → Stripe Link app approval |

### Two-stage invoice approval (non-negotiable):

```
Stage 1 — REVIEW:
  Operator sees the full invoice in War Room:
    Client name, project description, line items,
    total amount, payment terms, due date,
    payment risk score for this client.
  Operator can: APPROVE (proceed to Stage 2), EDIT, BLOCK

Stage 2 — HOLD:
  After Stage 1 APPROVE, invoice moves to HOLD queue.
  Operator explicitly releases HOLD to trigger send.
  HOLD release is the moment the invoice is transmitted.
  This two-stage design prevents accidental sends.
```

### War Room card format for Finance actions:

```
┌─────────────────────────────────────────────────────────┐
│ 🟡 REVIEW   FINANCE CLAW                    3 mins ago  │
│                                                         │
│ Invoice ready — @NovaBrand                              │
│ Project: Social media content — March                   │
│                                                         │
│ Amount:     $2,400.00                                   │
│ Due date:   Apr 4, 2026 (Net 14)                        │
│ Risk score: Low (8/10 payment history)                  │
│                                                         │
│ [View Full Invoice]  [APPROVE]  [EDIT]  [BLOCK]        │
└─────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────┐
│ 🔴 HOLD     FINANCE CLAW                   just now     │
│                                                         │
│ Invoice approved — ready to send to @NovaBrand          │
│ $2,400.00 due Apr 4, 2026                               │
│                                                         │
│ This will transmit the invoice via Stripe.              │
│                                                         │
│ [RELEASE HOLD — SEND INVOICE]  [CANCEL]                │
└─────────────────────────────────────────────────────────┘
```

---

## THE SELF-EVOLUTION CYCLE

Runs every Sunday at 03:00 — after the weekly revenue summary (also at
03:00, run summary first then evolution). Same 5-stage pipeline as all
claws (Observe → Identify → Propose → Build → Deploy).

### What the Finance Claw observes:

```
STAGE 1 — OBSERVE
  Read decisions.log: every APPROVE/EDIT/BLOCK on invoices and pricing
  Read payment-events.log: all payment timings, overdue events
  Read pricing/history/: estimated vs actual costs per project
  Read invoices/paid/ and invoices/overdue/: payment outcomes
  Read expenses/log.jsonl: expense patterns and categories
```

### Patterns the Finance Claw identifies:

- Which project types consistently result in late payment?
- Which scope estimates are most inaccurate (over/under)?
- Which client types generate the healthiest margins?
- Are current rates drifting below the squad's cost basis?
- Which expense categories are growing fastest?

### Evolution tools that emerge over time:

| Week | Tool | What It Does | Target Metric |
|---|---|---|---|
| 3 | Scope cost estimator v2 | Estimates project cost from brief keywords, calibrated to squad's actual delivery velocity | Estimate accuracy (% error vs actual) |
| 7 | Pricing floor guardian | Automatically flags proposals below the squad's profitable rate threshold — calibrated from actual margin data | Proposals below floor rate (should trend to 0) |
| 12 | Payment risk scorer v2 | Predicts likelihood of late payment from client type, project type, and communication patterns | Payment risk prediction accuracy |
| 18 | Margin tracker v2 | Monitors actual hours/effort vs estimated and surfaces compression early — before it's too late to address | Margin compression detection lead time |
| 25 | Tax category classifier v2 | Auto-categorizes all income and expenses with squad-specific patterns — reduces manual tax prep | Miscategorization rate |
| 35 | Rate optimization advisor v2 | Identifies when the squad is systematically undercharging relative to delivery quality — with specific rate adjustment recommendations | Revenue per hour delivered |

### Minimum thresholds before first evolution:
- 3 invoices generated and sent
- 2 completed projects with estimate vs actual data
- 4 weeks of expense log data

### Critical evolution constraint:
No evolved tool can access client contact data, source code, or send
messages to external services. A tool that would require reading
`/sandbox/clients/` is rejected at Stage 4 — Landlock enforcement
makes this architecturally impossible. No evolved tool can initiate
financial transfers or send invoices autonomously — every financial
action requires the two-stage human approval flow regardless of what
evolved tools suggest.

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE

**Day 1–7 (baseline):**
- Finance Claw responds to pricing queries within 10 minutes
- Invoices generated when projects complete, queued as REVIEW
- Two-stage approval works correctly — no invoice sends without HOLD release
- Expense logging works for any expenses that arrive
- Operator spends 5–10 minutes per day on Finance War Room actions

**Week 3–4 (first tools emerge):**
- Scope cost estimator calibrated to first few projects
- Estimates noticeably more accurate than generic inference
- Pricing floor guardian active — first below-floor proposal flagged

**Month 2–3 (compound tools):**
- Payment risk scorer active — high-risk clients flagged before invoice sent
- Margin tracker active — compression surfaces days before it becomes critical
- Operator rarely sees surprise financial situations

**Month 6+ (mature operation):**
- Rate optimization advisor active — specific rate adjustment recommendations
  based on 6 months of delivery quality data
- Tax category classifier fully calibrated — quarterly prep takes minutes
- Finance Claw handles all routine financial monitoring autonomously
- Operator Finance time: 3–5 minutes per day (review and release invoices)

---

## WHAT FAILURE LOOKS LIKE (DEBUGGING REFERENCE)

| Symptom | Likely Cause |
|---|---|
| pricing_response not sent within 10 min | Inference call failing or timing out — check cloud API connectivity |
| Invoice generated with wrong amount | Pricing estimate not loaded correctly — check pricing/estimates/{project_id}.json |
| Invoice sent without HOLD approval | Two-stage approval bypassed — critical bug in approval_handler |
| payment_overdue not firing | Payment status check not scheduled — check payment monitor schedule |
| revenue_summary payload contains line items | Privacy leak — summary must contain totals only |
| Analytics Claw not receiving revenue_summary | Message contract misconfigured — check contracts.py |
| Expense not tax-categorized | Inference call failing on classification — check data_type log |
| Margin compression not detected | Weekly summary running but margin analysis inference failing |
| Pricing floor not flagging | Pricing rules.json not loaded or floor value not set |
| Repeat overdue not escalating to HOLD | Decision logic only checking single invoice — check repeat detection |
| Tax quarterly prep not triggered | Quarterly scheduler not initialized — check finance_scheduler |
| Spend request auto-blocked | Over daily spend cap — check MILIMO_DAILY_SPEND_CAP_CENTS |
| Spend release fails after operator approval | Link app denied or timed out — check agent-spend.log |
| link-cli not found | stripe-link-cli skill not installed — run `hermes skills install official/payments/stripe-link-cli` |

---

## DEVELOPMENT AND TESTING NOTES

**Current phase:** All inference routes to cloud. Log data_type on every call.

**The two-stage invoice approval is the most important thing to get right.**
Test this first, before anything else. The sequence:
1. Ops Claw sends project_complete
2. Finance Claw generates invoice → queues REVIEW
3. Operator approves in War Room (Stage 1)
4. Invoice appears in HOLD queue
5. Operator releases HOLD (Stage 2)
6. Invoice transmits via Stripe API
7. Invoice moves: pending/ → approved/ → sent/

If Step 4 is missing (invoice sends immediately on Stage 1 REVIEW approve),
that is a critical bug. An accidental invoice send to a real client is not
recoverable in the same way a content post is. The two-stage requirement
exists precisely because invoice sends are irreversible.

**Minimum viable first run testing sequence:**
1. Configure a Stripe test account (test mode — no real money)
2. Send a mock `pricing_query` from Ops Claw
3. Confirm `pricing_response` received within 10 minutes
4. Send a mock `project_complete` from Ops Claw
5. Confirm invoice appears in War Room as REVIEW (not HOLD yet)
6. Approve the REVIEW — confirm invoice moves to HOLD queue (not sent)
7. Release the HOLD — confirm invoice transmits via Stripe test API
8. Confirm invoice moves from `approved/` to `sent/`
9. Simulate payment via Stripe test dashboard
10. Confirm payment detected within 24 hours, invoice moves to `paid/`
11. Confirm `revenue_summary` sent to Analytics Claw
12. Simulate past-due date on a sent invoice
13. Confirm invoice moves to `overdue/`, War Room REVIEW raised
14. Confirm `payment_overdue` sent to Ops Claw

All 14 steps must pass before autonomous scheduling is enabled.

---

## FILES TO BUILD

```
orchestrator/finance/finance_init.py         — Filesystem structure init
orchestrator/finance/pricing_engine.py       — Scope estimation and pricing queries
orchestrator/finance/invoice_manager.py      — Invoice lifecycle management
orchestrator/finance/payment_monitor.py      — Payment status checking and overdue detection
orchestrator/finance/expense_tracker.py      — Expense logging and tax classification
orchestrator/finance/revenue_tracker.py      — Revenue aggregation and weekly summaries
orchestrator/finance/approval_handler.py     — Two-stage War Room approval flow
orchestrator/finance/spend_handler.py        — Two-stage spend approval (mirror of approval_handler)
orchestrator/finance/spend_warroom_bridge.py — Spend <-> War Room bridge
orchestrator/finance/signal_dispatcher.py   — Outbound message sending
orchestrator/finance/finance_scheduler.py    — Scheduled autonomous actions
orchestrator/finance/finance_claw.py         — Main entry point
milimo-blueprint/roles/finance-claw.yaml     — Role blueprint (may exist)
milimo-blueprint/policies/finance-sandbox.yaml — Sandbox policy (may exist)
```

---

## SPEC EDGE CASES

**What if a pricing query arrives for a project type the Finance Claw
has no history on?**
Respond with a generic market-rate estimate based on scope complexity,
flagged with `data_quality: "estimated"` and `history_available: false`.
Include a note: "No historical data for this project type — estimate
based on complexity scoring only." Never refuse to respond.

**What if the Stripe API is unavailable when an invoice needs to send?**
Hold the invoice in `approved/` status. Retry every 30 minutes for
up to 24 hours. After 24 hours without successful send, escalate to
War Room: REVIEW — "Invoice send failed after 24 hours of retries.
Manual send required." Log every retry attempt to payment-events.log.

**What if the operator approves Stage 1 but never releases the HOLD?**
The HOLD queue does not expire automatically. Invoices sit in HOLD
indefinitely until the operator acts. After 48 hours in HOLD, add
an urgency flag to the War Room card: "Invoice has been in HOLD for
48 hours — action required." After 7 days, escalate: "Invoice in HOLD
for 7 days — client payment window may be closing."

**What if a project's actual cost far exceeds the estimate?**
Log the variance to `pricing/history/{project_id}.json`. This is training
signal for the scope cost estimator evolution tool. Do not automatically
adjust the invoice — the invoice reflects the agreed scope and pricing.
Surface a margin alert to the War Room: "Project {id} delivered at
{X}% of estimated margin. Variance logged for estimator calibration."

**What if two projects complete on the same day and both trigger invoices?**
Generate both invoices independently. Each gets its own invoice_id, its
own pending/ entry, its own REVIEW action in the War Room. The operator
reviews and approves them separately. Batch processing of invoices is
explicitly not supported — each invoice requires individual human review.

**What if an expense cannot be tax-categorized by inference?**
Log it to expenses/log.jsonl with `tax_category: "uncategorized"`.
Do not block the expense log on categorization failure. At quarterly
tax prep, surface all uncategorized expenses to the War Room as a
batch REVIEW: "12 expenses require manual tax categorization before
quarterly summary can be finalized."

---

*This specification is the ground truth for the Finance Claw.
If behavior in the codebase deviates from this document, the code is wrong.*

*Development note: All inference routes to cloud during testing.
Log data_type on every inference call — mandatory, not optional.
The two-stage invoice approval is the most critical correctness
requirement. Test it first, with a Stripe test account, before
enabling any other Finance Claw functionality.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
