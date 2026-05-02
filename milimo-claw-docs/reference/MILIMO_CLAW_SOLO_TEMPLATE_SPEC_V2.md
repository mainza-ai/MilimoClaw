# MILIMO CLAW — SOLO FOUNDER TEMPLATE FUNCTIONAL SPECIFICATION v2

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
# exactly how the solo-founder template is supposed to work — for
# debugging, feature implementation, testing, or documentation.
#
# This is the authoritative version. It supersedes all previous solo
# template specifications and incorporates the complete six-claw specs.
#
# DEVELOPMENT NOTE: This implementation is in active development and testing.
# All inference currently routes to cloud (the configured NEMOCLAW_MODEL via NVIDIA Cloud API)
# regardless of data sensitivity. The privacy routing rules documented here
# represent the production target architecture. Do not implement privacy
# routing enforcement during this phase — route everything to cloud.
# Log the data_type field on every inference call so routing can be enforced
# later without touching call sites.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug the **solo-founder template** for Milimo Claw
— a multi-agent autonomous hustle platform built on NVIDIA NemoClaw. Read
this entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation deviates
from it, the implementation is wrong — not this spec.

---

## WHAT THE SOLO-FOUNDER TEMPLATE IS

The solo-founder template is Milimo Claw configured for a single operator
running all six claws simultaneously on one machine. It is the primary
template for development, testing, and early deployment.

In a standard squad deployment, each person runs one claw on their own
laptop and the claws coordinate across machines through the OpenShell
inter-sandbox gateway. In the solo template, all six claws run on one
machine. The mesh coordination logic is identical — only the physical
topology differs.

**The solo-founder template is not a simplified version of Milimo Claw.
It is the full product, running on one machine, operated by one person.**

The tagline is the spec: *The milimo never stops. Work. Without working.*

---

## THE SIX CLAWS — SOLO CONFIGURATION

All six claws run simultaneously. Each has its own isolated NemoClaw
sandbox, its own filesystem mount, its own network egress policy, and
its own self-evolution cycle. They coordinate through the OpenShell
inter-sandbox gateway exactly as they would across multiple machines.

| Claw | Mount | Primary Function |
|---|---|---|
| CONTENT CLAW | `/sandbox/content` | All creative output — drafts, posts, campaigns |
| OPS CLAW | `/sandbox/clients` | Full client lifecycle — intake through delivery |
| ANALYTICS CLAW | `/sandbox/analytics` | Intelligence layer — reports, signals, projections |
| FINANCE CLAW | `/sandbox/finance` | Revenue, invoicing, pricing, expenses |
| BUILD CLAW | `/sandbox/build` | Engineering — issues, PRs, deploys, monitoring |
| ASSISTANT CLAW | `/sandbox/assistant` | Conversational interface — operator queries, claw coordination |

**For the full specification of each claw, refer to:**
- `milimo-claw-docs/reference/MILIMO_CLAW_CONTENT_CLAW_SPEC.md`
- `milimo-claw-docs/reference/MILIMO_CLAW_OPS_CLAW_SPEC.md`
- `milimo-claw-docs/reference/MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md`
- `milimo-claw-docs/reference/MILIMO_CLAW_FINANCE_CLAW_SPEC.md`
- `milimo-claw-docs/reference/MILIMO_CLAW_BUILD_CLAW_SPEC.md`

This document defines how those six claws behave **specifically in the
solo-founder template context** — approval thresholds tuned for one
operator, scheduling tuned for one machine, and the War Room tuned for
a single-person review cadence.

---

## FILESYSTEM TOPOLOGY

All six sandboxes on one machine. Each claw reads only its own mount.

```
/sandbox/
├── content/                    CONTENT CLAW — owns this, reads only here
│   ├── brand/
│   ├── drafts/
│   ├── briefs/
│   ├── calendar/
│   ├── intelligence/           ← read-only mount of Analytics report
│   ├── tools/
│   └── logs/
│
├── clients/                    OPS CLAW — owns this, reads only here
│   ├── active/
│   ├── prospects/
│   ├── completed/
│   ├── contracts/
│   ├── templates/
│   └── logs/
│
├── analytics/                  ANALYTICS CLAW — owns this
│   ├── reports/
│   │   └── weekly-intelligence.json   ← SHARED READ: all claws can read this
│   ├── signals/
│   ├── data/
│   ├── baselines/
│   ├── tools/
│   └── logs/
│
├── finance/                    FINANCE CLAW — owns this, reads only here
│   ├── revenue/
│   ├── invoices/
│   ├── expenses/
│   ├── pricing/
│   ├── tax/
│   └── logs/
│
└── build/ BUILD CLAW — owns this, reads only here
├── repo/
├── context/
├── prs/
├── deployments/
├── docs/
└── logs/
│
└── assistant/ ASSISTANT CLAW — owns this, reads only here
├── sessions/
├── context/
└── logs/
```

**The one shared-read file:**
`/sandbox/.openclaw/milimo/claws/analytics/reports/weekly-intelligence.json`
This is the only file in the entire mesh that all six claws can read
directly without a message contract. It is written by the Analytics Claw
every Sunday and mounted as read-only in every other claw's sandbox policy.
**Verify this mount is configured in every claw's sandbox policy file.**
This is the most critical single configuration item in the solo template.

---

## OPERATOR POLICY — SOLO APPROVAL THRESHOLDS

In a squad deployment, four to six people share the War Room review load.
In solo mode, one operator reviews everything. The approval thresholds
are tuned accordingly — higher AUTO tolerance for low-stakes actions,
strict REVIEW and HOLD for anything client-facing or financially consequential.

The solo operator should be able to process their full War Room queue
in under 15 minutes every morning.

### CONTENT CLAW — Solo Approval Modes

| Action | Mode | Notes |
|---|---|---|
| Social post draft | REVIEW | Always surfaced — operator approves before scheduling |
| Client proposal draft | REVIEW | High-stakes — never auto |
| Email campaign draft | REVIEW | Operator approves before send |
| Brand asset usage | AUTO | Logged, morning digest |
| Content calendar update | AUTO | Operator can override anytime |
| A/B variant | REVIEW | Both variants shown for selection |
| Trend-reactive post | REVIEW | Operator confirms relevance |

### OPS CLAW — Solo Approval Modes

| Action | Mode | Notes |
|---|---|---|
| New client welcome message | REVIEW | Ops drafts, operator approves |
| Intake questionnaire | REVIEW | Ops drafts, operator approves |
| Client proposal | REVIEW | Every proposal surfaces |
| Project brief to creative claws | REVIEW | Operator confirms before work begins |
| Routine client update | AUTO | Logged, morning digest |
| Deadline risk flag | REVIEW | Operator sees risk + recommendation |
| Deadline critical (24 hours) | HOLD | Explicit action required |
| Scope creep change order | HOLD | Never auto-handled |
| Client delivery message | REVIEW | Ops drafts, operator approves |
| Deep Work auto-response | AUTO | Sends automatically when active |

### ANALYTICS CLAW — Solo Approval Modes

| Action | Mode | Notes |
|---|---|---|
| Weekly intelligence report published | AUTO | Morning digest |
| Opportunity detected (>0.85 confidence) | REVIEW | Time-sensitive signal |
| Client health alert (score < 6.0) | REVIEW | Operator informed |
| Revenue anomaly detected | REVIEW | Operator informed |
| Baseline recalculated | AUTO | Background maintenance |

### FINANCE CLAW — Solo Approval Modes

| Action | Mode | Notes |
|---|---|---|
| Invoice generation (review content) | REVIEW | Stage 1 — content review |
| Invoice send (trigger transmission) | HOLD | Stage 2 — explicit release |
| Expense log entry | AUTO | Logged, morning digest |
| Overdue payment alert (first) | REVIEW | Operator decides follow-up |
| Overdue payment alert (repeat) | HOLD | Escalation — must act |
| Margin compression alert | REVIEW | Operator informed |
| Rate optimization advisory | REVIEW | Recommendation only |
| Tax quarterly summary | AUTO | Morning digest |

### BUILD CLAW — Solo Approval Modes (Tech squads only)

| Action | Mode | Notes |
|---|---|---|
| Sprint plan | REVIEW | Operator approves before work begins |
| PR open | REVIEW | Operator reviews code diff |
| PR merge | HOLD | Explicit HOLD release triggers GitHub merge |
| Production deploy | HOLD | Separate HOLD — independent of PR HOLD |
| Issue triage and scoring | AUTO | Morning digest |
| Dependency audit | AUTO | Security PRs queue as REVIEW |
| Error pattern detection | REVIEW | Operator sees new error class |
| Cost alert | REVIEW | Operator informed |
| Devlog draft | AUTO | Draft ready for Content Claw |
| Changelog update | AUTO | Appended on every merged PR |

---

## THE WAR ROOM — SOLO CONFIGURATION

The War Room is the single interface through which the solo operator
manages all six claws. In solo mode, all six claw queues are merged
into one prioritized action feed.

### Queue Priority (HOLD first, then REVIEW, then AUTO)

```
🔴 HOLD   — requires explicit operator release before any action executes
🟡 REVIEW — requires operator decision (approve/edit/block) before execution
✓  AUTO   — already executed, logged for morning digest awareness
```

### Morning Brief (07:00 daily)

A digest of everything that ran on AUTO overnight:
- How many actions each claw executed autonomously
- Any anomalies or signals detected
- Evolution log entries if Sunday
- Revenue snapshot
- Queue summary: how many items await decision

The solo operator's target: review the morning brief + clear the REVIEW
queue in under 15 minutes. The claws should handle the rest.

### Evening Wrap (20:00 daily)

Summary of what ran today and what is queued for tomorrow. No decisions
required — awareness only.

### War Room Layout (Two-Panel)

**Left panel — Action Queue:**
Priority-ordered feed of all pending actions from all six claws.
Each action card shows: claw source, mode badge, summary, key metadata,
and available decisions.

**Right panel — Claw Health:**
Six claw status rows. Per row: claw name in accent color, status dot
(active/idle/processing), tool count, last evolution timestamp, this
week's activity count.

Below claw health: Revenue widget showing week total, week-over-week
change, invoices paid, invoices pending.

Below revenue: Evolution log — any tools autonomously built this week,
with performance delta.

### Keyboard Shortcuts

| Key | Action |
|---|---|
| A | Approve current REVIEW item |
| B | Block current item |
| E | Edit current item inline |
| R | Release current HOLD |
| D | Toggle morning digest / evening wrap panel |
| F | Activate/deactivate Deep Work Mode |
| H | Help overlay |
| Q | Quit |

---

## INFERENCE ROUTING — SOLO DEVELOPMENT PHASE

**Current phase: ALL inference routes to cloud.**
the configured NEMOCLAW_MODEL via NVIDIA Cloud API for every call, every claw, every
data type — regardless of sensitivity.

**The `data_type` field must be logged on every single inference call.**
This is mandatory. It is the only thing that enables future local NIM
routing without rewriting call sites.

```python
# Required pattern — every inference call in every claw:
response = inference_client.complete(
    prompt=prompt,
    data_type="client_triage_scoring",  # ALWAYS INCLUDE
    max_tokens=600
)
```

**Cost guard (active even in dev):**
- Daily cloud token budget: 50,000 tokens
- Alert at 80% of daily budget
- Automatic fallback to a lighter prompt strategy if budget exceeded
- Never block a claw action — always fallback, never fail

**Production routing targets (for reference — not enforced during dev):**

| Claw | Sensitive data types → Local NIM |
|---|---|
| Content | Internal ideation, draft iterations, voice adapter calibration |
| Ops | Contract review, internal project summaries, scope analysis |
| Analytics | Performance synthesis, predictive models, opportunity scoring |
| Finance | ALL financial data — invoices, pricing, expenses, tax (locked) |
| Build | Source code, API keys, architecture decisions, code review |

---

## THE SELF-EVOLUTION CYCLE — SOLO SCHEDULE

Each claw runs its Evolution Cycle on Sunday. The order matters — report
first, then evolutions, so each claw has the latest Analytics intelligence
when it runs its cycle.

```
Sunday 01:00 — Analytics Claw: baseline recalculation
Sunday 02:00 — Analytics Claw: weekly intelligence report generated
Sunday 02:05 — Content Claw: evolution cycle begins (reads fresh report)
Sunday 02:15 — Ops Claw: evolution cycle begins
Sunday 02:25 — Analytics Claw: evolution cycle begins
Sunday 02:35 — Build Claw: evolution cycle begins (tech squads only)
Sunday 03:00 — Finance Claw: weekly revenue summary + evolution cycle
```

**Minimum data thresholds before first evolution runs per claw:**

| Claw | Threshold |
|---|---|
| Content | 10 approved posts + 3 rejected drafts + 1 week of performance data |
| Ops | 5 completed client interactions + 3 active/completed projects + 2 weeks of comms data |
| Analytics | 3 weeks of performance_signal data + 1 revenue_summary + 1 client_health_signal |
| Finance | 3 invoices generated + 2 completed projects with estimate vs actual + 4 weeks expense data |
| Build | 5 merged PRs + 3 completed sprints + 2 production deploys + 4 weeks cost data |

If thresholds are not met, the claw logs "evolution skipped — insufficient
{data_type} data (have {n}, need {minimum})" and tries again next Sunday.

---

## INTER-CLAW COORDINATION — SOLO TOPOLOGY

In solo mode, all six claws are on the same machine. The OpenShell
inter-sandbox gateway handles inter-claw messaging exactly as it would
across machines — typed contracts, policy validation, audit logging.

The topology is the same. The latency is near-zero. The guarantees are identical.

### Complete Message Flow

```
CONTENT ──draft_ready──────────────────────────────→ War Room
CONTENT ──content_performance_query────────────────→ ANALYTICS
CONTENT ──performance_signal (after publish)────────→ ANALYTICS
CONTENT ──brief_acknowledged (within 5 min)─────────→ OPS
CONTENT ──deliverable_complete (after publish)───────→ OPS

OPS ─────project_brief ────────────────────────────→ CONTENT or BUILD
OPS ─────feature_brief ────────────────────────────→ BUILD
OPS ─────pricing_query (before every proposal)──────→ FINANCE
OPS ─────project_complete (client confirmed)─────────→ FINANCE
OPS ─────client_health_signal (weekly)──────────────→ ANALYTICS
OPS ─────client_onboarded ─────────────────────────→ ANALYTICS

ANALYTICS ──performance_intel (weekly + opportunity)→ CONTENT
ANALYTICS ──retention_signals (weekly + churn)──────→ BUILD
ANALYTICS ──client_health_alert (score < 6.0)────────→ OPS
ANALYTICS ──revenue_anomaly (immediate)──────────────→ FINANCE
ANALYTICS ──content_performance_response────────────→ CONTENT (query reply)
ANALYTICS ──behavior_query_response─────────────────→ BUILD (query reply)

FINANCE ─────pricing_response (within 10 min)───────→ OPS
FINANCE ─────invoice_ready (after Stage 1 approve)───→ OPS
FINANCE ─────payment_overdue (immediately)───────────→ OPS
FINANCE ─────revenue_summary (weekly + on payment)───→ ANALYTICS

BUILD ───────deploy_complete (after production deploy)→ OPS
BUILD ───────shipping_summary (Friday 17:00)──────────→ CONTENT
BUILD ───────behavior_query (before sprint planning)──→ ANALYTICS
```

### Non-Negotiable Sequencing Rules

These rules apply in solo mode exactly as they do in squad mode:

1. **OPS → FINANCE sequencing:** `pricing_query` must be sent and
   `pricing_response` received BEFORE `project_brief` is sent to any
   creative claw. No proposal goes out without confirmed pricing.

2. **FINANCE two-stage invoice:** Stage 1 REVIEW approve moves invoice
   to HOLD queue only. Stage 2 HOLD release is the only trigger for
   Stripe transmission. If REVIEW approve sends the invoice: critical bug.

3. **BUILD two-stage PR + deploy:** PR REVIEW approve → HOLD (not merge).
   PR HOLD release → GitHub merge. Deploy stages automatically after merge.
   Deploy HOLD release → production deployment. PR merge does NOT auto-deploy.
   Two separate, independent HOLD queues.

4. **FINANCE project_complete:** `project_complete` to Finance Claw fires
   ONLY after client confirms receipt of deliverables. Not on internal
   completion. Not on deploy. Only on client confirmation.

5. **CONTENT brief_acknowledged:** Must be sent within 5 minutes of every
   `project_brief` received from Ops Claw.

6. **BUILD feature_brief_acknowledged:** Must be sent within 10 minutes of
   every `feature_brief` received from Ops Claw.

7. **ANALYTICS query response SLA:** Must respond to
   `content_performance_query` and `behavior_query` within 2 minutes.

8. **BUILD sprint planning timeout:** If `behavior_query_response` does
   not arrive within 5 minutes, proceed without Analytics retention signals.

---

## DEEP WORK MODE

`milimo squad finals-mode` activates Deep Work Mode — simultaneously
hot-reloads all six claw policies to a reduced-autonomy configuration.

```bash
milimo squad finals-mode --duration 2weeks --resume-date 2026-05-12
milimo squad finals-resume
```

**Per-claw behavior during Deep Work Mode:**

| Claw | Active behavior | Paused behavior |
|---|---|---|
| Content | Nothing | Draft generation, publishing |
| Ops | Auto-responses to active clients | New client intake |
| Analytics | Passive data collection | New experiments, opportunity scoring |
| Finance | Invoice sends continue | New project initiations |
| Build | Issue triage only | New PRs, deploys, code generation |

**Auto-response template (Ops Claw sends automatically):**
> "Hey [client_name], I'm heads-down on a focused sprint until [resume_date].
> Your project is on track — I'll be back in full swing then. 🙏"

**What Deep Work Mode does NOT pause:**
- Payment monitoring (Finance Claw keeps checking for payments)
- Error monitoring (Build Claw keeps watching production)
- Analytics data collection (ingests signals, does not generate new ones)
- War Room HOLD items (existing HOLDs remain — operator can still release)

**Resume:** `milimo squad finals-resume`
Scheduled resume hot-reloads all policies back and sends reactivation
messages to paused clients.

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE — SOLO

### Day 1–7 (baseline establishment)

- All six claws initialize their filesystem structures
- Content Claw generates basic drafts using cloud Nemotron with style instructions
- Ops Claw intercepts first inquiry — triage score appears in War Room
- Analytics Claw begins collecting signals — no report yet (insufficient data)
- Finance Claw responds to first pricing query within 10 minutes
- Build Claw fetches open GitHub issues and generates first sprint plan
- Operator spends 20–30 minutes per day in War Room
- No evolution cycles run yet — data thresholds not met

### Week 3–4 (first tools emerge)

- Content: Style descriptor and tone classifier active — drafts arrive
  pre-calibrated, fewer edits required
- Ops: Client triage scorer active — low-quality inquiries filtered
- Finance: Scope cost estimator calibrated from first two projects
- Build: PR style enforcer and issue complexity scorer active
- Analytics: First weekly intelligence report generated
- Operator time: 15–20 minutes per day

### Month 2–3 (compound intelligence)

- Content: Timing optimizer active — content auto-scheduled for
  audience-specific peak windows
- Ops: Deadline risk predictor active — no surprise late deliveries
- Analytics: Anomaly detector calibrated — real anomalies surfacing
- Finance: Payment risk scorer active — high-risk clients flagged before invoice
- Build: Error pattern classifier active — recurring bugs auto-patched
- Operator time: 10–15 minutes per day

### Month 6+ (mature solo operation)

- All evolution tools active across all six claws
- Content generates drafts in each client's voice without re-prompting
- Ops handles 80%+ of routine client management autonomously
- Analytics reports are predictive, not just descriptive
- Finance has never sent an underpriced proposal in months
- Build's churn signal correlator driving sprint priorities
- Auto-roadmap drafter publishing Monday morning roadmap to War Room
- Operator time: 8–10 minutes per day
- The milimo never stops.

---

## WHAT FAILURE LOOKS LIKE — DEBUGGING REFERENCE

### Cross-claw failures (solo-specific)

| Symptom | Likely Cause |
|---|---|
| weekly-intelligence.json not readable by Content/Ops/Finance/Build/Assistant | Shared filesystem mount not configured in one or more claw sandbox policies |
| project_brief sent before pricing_response | OPS → FINANCE sequencing rule violated — check intake_manager |
| Invoice sent at Stage 1 REVIEW approve | Two-stage approval bypassed in Finance approval_handler — critical bug |
| PR merged at REVIEW approve | Two-stage approval bypassed in Build approval_handler — critical bug |
| Deploy triggered on PR merge | Deploy has no separate HOLD — check deploy_manager wiring |
| project_complete sent before client confirms | Delivery flow short-circuited — check project_manager |
| Evolution not running for any claw | Scheduler not initialized — check each claw's scheduler startup |
| All claws showing cloud routing | Expected during dev — verify data_type is logged on every call |
| War Room queue growing unbounded | Approval thresholds misconfigured as HOLD when should be REVIEW or AUTO |
| Morning brief not arriving at 07:00 | DigestScheduler not initialized in warroom-tui.ts |

### Per-claw failures (refer to individual claw specs for full tables)

- Content Claw failures: see `MILIMO_CLAW_CONTENT_CLAW_SPEC.md`
- Ops Claw failures: see `MILIMO_CLAW_OPS_CLAW_SPEC.md`
- Analytics Claw failures: see `MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md`
- Finance Claw failures: see `MILIMO_CLAW_FINANCE_CLAW_SPEC.md`
- Build Claw failures: see `MILIMO_CLAW_BUILD_CLAW_SPEC.md`

---

## MINIMUM VIABLE FIRST RUN — SOLO TESTING SEQUENCE

This sequence tests the full solo template end-to-end. All six claws
must be running. Use test credentials for all external APIs.

### Phase A — Verify Isolation and Shared Mount (before anything else)

```
A1. Confirm all six sandbox filesystem mounts exist and are isolated:
/sandbox/content, /sandbox/clients, /sandbox/analytics,
/sandbox/finance, /sandbox/build, /sandbox/assistant

A2. Write a test file to /sandbox/.openclaw/milimo/claws/analytics/reports/weekly-intelligence.json

A3. Confirm Content Claw can read the file from its sandbox
A4. Confirm Ops Claw can read the file from its sandbox
A5. Confirm Finance Claw can read the file from its sandbox
A6. Confirm Build Claw can read the file from its sandbox

A7. Confirm Content Claw CANNOT read /sandbox/clients (should fail)
A8. Confirm Finance Claw CANNOT read /sandbox/build (should fail)

Stop here if any of A1–A6 fails. Fix the mount configuration before
proceeding. Nothing else works correctly without this foundation.
```

### Phase B — War Room and Approval Flow

```
B1. Open War Room TUI — confirm six-claw health panel renders
B2. Confirm morning brief scheduling initialized (07:00 target)
B3. Inject a mock REVIEW action manually
B4. Confirm it appears in the queue with correct priority
B5. Approve it — confirm action executes and moves to AUTO log
B6. Inject a mock HOLD action
B7. Confirm it appears at the top of the queue above REVIEW items
B8. Release the HOLD — confirm execution
```

### Phase C — OPS → FINANCE → OPS Sequencing

```
C1. Inject a test inquiry into Ops Claw
C2. Confirm triage score appears in War Room (94/100 format)
C3. Approve welcome message
C4. Inject mock client brief response
C5. Confirm pricing_query sent to Finance Claw
C6. Inject mock pricing_response from Finance Claw
C7. Confirm project_brief queued for operator REVIEW
C8. Approve project_brief
C9. Confirm Content or Build Claw receives the message
```

### Phase D — FINANCE Invoice Two-Stage Flow

```
D1. Inject mock project_complete to Finance Claw
D2. Confirm invoice appears in War Room as REVIEW (not HOLD, not sent)
D3. Approve REVIEW — confirm invoice moves to HOLD queue
D4. Verify no Stripe call made at Stage 1 (critical check)
D5. Release HOLD — confirm Stripe test API called
D6. Confirm invoice moves to sent/
D7. Simulate payment in Stripe test dashboard
D8. Confirm invoice moves to paid/ within 24-hour check window
D9. Confirm revenue_summary sent to Analytics Claw
```

### Phase E — BUILD PR and Deploy Two-Stage Flow

```
E1. Confirm GitHub test repository configured
E2. Generate sprint plan — confirm REVIEW (not AUTO, not HOLD)
E3. Approve sprint plan
E4. Confirm PR opened on GitHub test repo
E5. Confirm PR in War Room as REVIEW
E6. Approve REVIEW — confirm PR moves to HOLD (not merged)
E7. Verify zero GitHub merge calls after E6 (critical check)
E8. Release HOLD — confirm PR merged on GitHub
E9. Confirm deploy staged in deployments/pending/
E10. Confirm deploy appears as its OWN separate HOLD
E11. Release deploy HOLD — confirm Vercel/Railway test deploy triggers
E12. Confirm deploy_complete sent to Ops Claw
```

### Phase F — Analytics Intelligence Flow

```
F1. Inject 7 days of mock performance_signal messages from Content Claw
F2. Inject mock client_health_signal from Ops Claw
F3. Inject mock revenue_summary from Finance Claw
F4. Trigger manual report generation (bypass Sunday schedule)
F5. Confirm weekly-intelligence.json written and valid JSON
F6. Confirm all six claws can read the file (from Phase A mount)
F7. Inject content_performance_query from Content Claw
F8. Confirm response arrives within 2 minutes
F9. Inject client_health_signal with score 5.0 (below threshold)
F10. Confirm client_health_alert sent to Ops Claw immediately
```

**All phases must pass before autonomous scheduling is enabled.**
Partial completion is not acceptable. Each phase builds on the previous.

---

## CONFIGURATION FILE

**Template location:** `milimo-blueprint/templates/solo-founder.yaml`

Key configuration values for solo mode:

```yaml
template:
  name: solo-founder
  squad_size: 1
  claws_active: [content, ops, analytics, finance, build, assistant]

operator_policy:
  squad_lead: mainza
  # approval modes per claw as documented above

inference:
  solo_mode: true
  all_routes: cloud           # development phase — override later
  data_type_logging: required  # mandatory on every call

  cost_guard:
    daily_cloud_token_budget: 50000
    alert_at_percent: 80
    fallback_on_exceed: lighter_prompt   # never block, always fallback

evolution:
  cycle_day: sunday
  schedule:
    analytics_baseline: "01:00"
    analytics_report:   "02:00"
    content:            "02:05"
    ops:                "02:15"
    analytics_evolution:"02:25"
    build:              "02:35"
    finance:            "03:00"

  min_thresholds:
    content:   { approved_posts: 10, rejected_drafts: 3, performance_weeks: 1 }
    ops:       { client_interactions: 5, projects: 3, comms_weeks: 2 }
    analytics: { signal_weeks: 3, revenue_summaries: 1, health_signals: 1 }
    finance:   { invoices: 3, completed_projects: 2, expense_weeks: 4 }
    build:     { merged_prs: 5, sprints: 3, deploys: 2, cost_weeks: 4 }

war_room:
  operator: mainza
  mode: solo
  morning_brief: "07:00"
  evening_wrap:  "20:00"
  target_review_minutes: 15

deep_work_mode:
  cli_command: "milimo squad finals-mode"
  resume_command: "milimo squad finals-resume"
```

---

## GROUND TRUTH HIERARCHY

When there is a conflict between documents, this hierarchy applies:

1. **Individual claw spec documents** — ground truth for each claw's
internal behavior, filesystem layout, network egress, and inference routing
2. **This document (solo template spec v2)** — ground truth for how the
six claws are configured, coordinated, and operated together in solo mode
3. **solo-founder.yaml** — configuration values that implement the above
4. **AGENTS.md** — quick reference summary (not ground truth)

If this document conflicts with an individual claw spec, the individual
claw spec wins on matters internal to that claw. This document wins on
matters of cross-claw coordination, approval thresholds, and scheduling.

---

## DEVELOPMENT CONVENTIONS — SOLO TEMPLATE SPECIFIC

**All inference to cloud.** Every claw. Every call. Log data_type always.

**Use test credentials for all external APIs:**
- Stripe: test key (`sk_test_*`) — no live API calls
- GitHub: test repository — not a live production repo
- Vercel/Railway: preview environment — not production
- Sentry: test project — not production monitoring

**Single `config.json` source of truth:**
`~/.milimo/config.json` is the only config file. There must not be a
separate `state.json`. All commands read from and write to this one file.

**Filesystem mounts during development:**
If `/sandbox/` paths require elevated permissions on the development
machine, use `~/.milimo/sandboxes/{role}/` as fallback. Auto-detect
at init time and log which path is in use. The sandbox policy files
must be updated to reflect whichever path is used.

**Python bridge pattern:**
TypeScript calls Python via `bridge_cli.py` with array arguments only.
Never template literal shell strings. The bridge returns structured JSON.

**Thread safety:**
All log files use fcntl file locking. All JSON summary files use atomic
writes (temp → rename). No log file is ever truncated or overwritten.

---

*This specification is the ground truth for the solo-founder template.*
*If behavior in the codebase deviates from this document, the code is wrong.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
*"The milimo never stops. Work. Without working."*
