# MILIMO CLAW — SOLO FOUNDER TEMPLATE FUNCTIONAL SPECIFICATION
# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI assistant when you need it to understand
# exactly how the solo-founder template is supposed to work — for
# debugging, feature implementation, testing, or documentation.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug **Milimo Claw** — a multi-agent autonomous
hustle platform built as a plugin on top of NVIDIA NemoClaw. Read this
entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation
deviates from it, the implementation is wrong — not this spec.

---

## WHAT MILIMO CLAW IS

Milimo Claw turns a laptop into an autonomous AI-powered business operation.
Instead of a human coordinating every task, specialized AI agents — called
"claws" — handle specific business functions 24/7. Each claw runs inside a
NemoClaw sandbox: an isolated environment with its own filesystem, its own
network access rules, and its own inference routing policy.

The operator (human) does not prompt the claws continuously. The claws work
autonomously. The operator reviews and approves significant decisions through
a live dashboard called the War Room. Everything else runs without them.

The name *Milimo* comes from the Tonga people of Zambia and means
"works, tasks, labour." It is the most honest name a hustle platform
has ever had.

---

## WHAT THE SOLO FOUNDER TEMPLATE IS

The solo-founder template is a Milimo Claw configuration for a single
operator running all five claws simultaneously on one machine. It is
designed for:

- A solo founder stress-testing the platform before onboarding a squad
- An independent operator who wants the full five-claw company running
  on their own laptop
- A founder who wants to generate real operational data — evolved
  blueprints, client records, content history — before bringing
  partners in

In a standard squad deployment, each person runs one claw on their own
laptop and the claws coordinate across machines through the OpenShell
inter-sandbox gateway. In the solo template, all five claws run on one
machine. The mesh coordination logic is the same — only the physical
topology differs.

---

## THE FIVE CLAWS — WHAT EACH ONE DOES

### CONTENT CLAW
**Filesystem mount:** `/sandbox/content`
**What it owns:** Brand assets, style guides, approved post history,
content calendars, creative briefs received from Ops Claw.

**What it does autonomously:**
- Generates social posts, copy, email campaigns, proposals, and
  content calendars
- Applies its self-evolved style tools to every draft before surfacing
  it for review (tone classifier, platform calibrator, timing optimizer)
- Schedules approved content to platforms via the egress policy APIs
- Queries Analytics Claw weekly: "what performed best this week?"
  and incorporates the response into next week's drafts
- Receives new project briefs from Ops Claw via inter-sandbox message
  and generates initial creative concepts

**What it cannot do:**
- Read client contact data (lives in /sandbox/clients — Ops Claw only)
- Read financial records (lives in /sandbox/finance — Finance Claw only)
- Read source code (lives in /sandbox/build — Build Claw only)
- Post anything to any platform without operator APPROVE in War Room

**Inference routing:**
- Public-facing drafts → Cloud Nemotron 120B (quality matters — clients
  and audiences will see this)
- Internal ideation and draft iterations → Local NIM (private creative
  process, stays on device)
- Trend research → Cloud Nemotron 120B (public data, speed preferred)

---

### OPS CLAW
**Filesystem mount:** `/sandbox/clients`
**What it owns:** Client records, contact details, project histories,
communication logs, contract terms, brief documents.

**What it does autonomously:**
- Intercepts new client inquiries from approved ingress channels
- Runs triage scoring on every inquiry (budget signal, scope clarity,
  niche fit) before surfacing to War Room
- Drafts welcome messages, intake questionnaires, project briefs
- Tracks all active project deadlines and flags risk 5+ days in advance
- Detects scope creep and auto-drafts change orders for approval
- Coordinates client delivery when Content or Build Claw signals completion
- Sends brief summaries to Content Claw or Build Claw when new projects open

**What it cannot do:**
- Send any client-facing message without operator APPROVE in War Room
- Accept or reject a client without operator decision
- Access financial records or source code directly

**Inference routing:**
- Client-facing messages → Cloud Nemotron 120B (the client sees this)
- Internal project summaries and briefs → Local NIM (business context
  is sensitive)
- Contract review and risk flagging → Local NIM (legal-adjacent, never
  touches cloud)

---

### ANALYTICS CLAW
**Filesystem mount:** `/sandbox/analytics`
**What it owns:** Performance data, engagement metrics, revenue summaries,
trend datasets, weekly intelligence reports.

**What it does autonomously:**
- Tracks content performance across all approved platforms (read-only)
- Generates a weekly intelligence report every Sunday at 2am and writes
  it to `/sandbox/analytics/reports/weekly-intelligence.json`
- This file is readable by all other claws — it is the shared intelligence
  layer of the entire mesh
- Responds to on-demand queries from Content Claw and Build Claw
- Sends revenue anomaly alerts directly to Finance Claw
- Sends client health signals to Ops Claw when satisfaction drops
- Flags opportunities (content formats, client types, product features)
  with above-average growth signal

**What it cannot do:**
- Write to any external platform (read-only network egress)
- Access raw client contact data or source code
- Launch new experiments without operator awareness

**Inference routing:**
- Public trend analysis → Cloud Nemotron 120B (public data, max reasoning)
- Internal performance synthesis → Local NIM (squad's data is sensitive)
- Predictive models → Local NIM (trained on proprietary operational data)

---

### FINANCE CLAW
**Filesystem mount:** `/sandbox/finance`
**What it owns:** Revenue records, invoice history, expense logs,
pricing rules, payment status, tax categories.

**What it does autonomously:**
- Monitors all active invoices and flags overdue payments
- Responds to pricing queries from Ops Claw before proposals go out
- Receives project completion signals from Ops Claw and generates invoices
- Tracks actual project costs vs estimates and surfaces margin compression
- Auto-categorizes all income and expenses for tax prep
- Sends revenue summaries (totals only — no line-item detail) to Analytics

**What it cannot do:**
- Send any invoice without operator REVIEW in War Room
- Actually send an invoice without operator HOLD clearance
  (two-stage: REVIEW to see it, HOLD release to send it)
- Access client contact data or source code
- Route ANY data through cloud inference — financial data is locked
  to local NIM at all times, enforced by the privacy router, not
  just by policy preference. This cannot be overridden.

**Inference routing:**
- ALL financial data → Local NIM, always, no exceptions.
  This is an architectural constraint enforced by PrivacyPolicyViolationError
  if anything attempts to route financial data to cloud.

---

### BUILD CLAW
**Filesystem mount:** `/sandbox/build`
**What it owns:** Codebase (via approved GitHub repository mount),
environment configuration (secrets encrypted at rest), test suites,
deployment configs, error logs.

**What it does autonomously:**
- Reads open GitHub issues, scores them by complexity, and proposes
  a sprint plan for War Room approval
- Writes code from approved issue descriptions and opens PRs
- Runs test suites and surfaces failures with diagnosis
- Monitors production error logs (Sentry/Datadog) and auto-drafts
  patches for recurring error classes
- Runs weekly dependency audits and opens security PRs for
  well-understood vulnerabilities
- Sends weekly shipping summaries to Content Claw for devlog posts
- Sends deploy completion signals to Ops Claw for client notification

**What it cannot do:**
- Merge any PR without operator HOLD clearance
- Deploy to production without operator HOLD clearance
- Share source code or secrets with any other claw via inter-sandbox
  message (secrets are encrypted at rest and never appear in messages)
- Route source code through cloud inference — locked to local NIM

**Inference routing:**
- Source code, API keys, env vars → Local NIM, always, locked
- Architecture decisions and code review → Local NIM (sensitive IP)
- Boilerplate, tests, documentation → Cloud Nemotron 120B (non-sensitive)
- Public changelogs and release notes → Cloud Nemotron 120B
- Production logs with user data → Local NIM (user privacy, non-negotiable)

---

## HOW THE CLAWS COORDINATE

The claws do not share a filesystem. They do not call each other's APIs
directly. They communicate exclusively through typed message contracts
passed via the OpenShell inter-sandbox gateway.

Every message has:
- A declared sender (claw role)
- A declared recipient (claw role)
- A declared message type (e.g. "project_brief", "performance_signal",
  "pricing_query", "deploy_complete")
- A structured payload matching the message type schema

The gateway validates every message against the sending claw's outbound
policy and the receiving claw's inbound policy. A message type not defined
in both policies is dropped and logged. There is no freeform text passing
between claws.

### Message routing table (who sends what to whom):

| From         | To           | Message Type           | When                                      |
|--------------|--------------|------------------------|-------------------------------------------|
| Ops          | Content      | project_brief          | New client project opened                 |
| Ops          | Build        | feature_brief          | Client requests new feature               |
| Ops          | Finance      | pricing_query          | Before sending any proposal               |
| Ops          | Finance      | project_complete       | Deliverable sent to client                |
| Content      | War Room     | draft_ready            | Any content ready for review              |
| Content      | Analytics    | performance_query      | Weekly: "what worked best?"               |
| Build        | Content      | shipping_summary       | Weekly: what shipped, for devlog          |
| Build        | Ops          | deploy_complete        | Production deploy finished                |
| Build        | Analytics    | behavior_query         | Sprint planning: "what do users need?"    |
| Analytics    | Content      | performance_intel      | Weekly intelligence report summary        |
| Analytics    | Build        | retention_signals      | Feature adoption and churn correlation    |
| Analytics    | Ops          | client_health_signal   | Satisfaction score drops below threshold  |
| Analytics    | Finance      | revenue_anomaly        | Unusual revenue pattern detected          |
| Finance      | Ops          | pricing_response       | Floor and ceiling for the requested scope |
| Finance      | Ops          | invoice_ready          | Invoice generated, queued for approval    |
| Finance      | War Room     | overdue_alert          | Payment overdue by threshold days         |

---

## THE WAR ROOM — HOW IT WORKS FOR SOLO

In a squad deployment, all members share the War Room and can approve
actions. In solo mode, one operator sees and decides everything.

**The War Room does four things:**

1. **Shows the action queue** — every pending claw action that requires
   operator input, sorted by priority: HOLD first, then REVIEW, then AUTO

2. **Shows claw health** — real-time status of all five claws:
   active/idle/processing, tool count, last evolution timestamp,
   this week's activity

3. **Shows the evolution log** — every tool autonomously built by any
   claw this week, with the pattern that triggered it and the
   performance delta vs baseline

4. **Shows the squad revenue widget** — this week's revenue, invoices
   paid, invoices pending, week-over-week change

**Approval modes in solo:**

| Mode   | Color  | Behavior                                                        |
|--------|--------|-----------------------------------------------------------------|
| AUTO   | Teal   | Claw acts immediately, logs for morning review digest           |
| REVIEW | Amber  | Claw drafts action, queues for operator decision before sending |
| HOLD   | Coral  | Claw flags and fully pauses. Explicit operator release required |
| VETO   | Red    | Reserved for actions that should never auto-proceed             |

**Solo approval thresholds (from solo-founder.yaml):**

The solo template sets thresholds higher than squad mode to reduce
noise for a single operator. Low-stakes actions run on AUTO. Client-facing
actions run on REVIEW. Anything involving money or production code runs
on HOLD.

Key HOLD actions (require explicit operator release):
- Invoice send (Finance Claw)
- PR merge (Build Claw)
- Production deploy (Build Claw)
- Scope change handling (Ops Claw)

Key REVIEW actions (drafted, queued, operator approves before sending):
- New client welcome message (Ops Claw)
- Client proposal (Ops Claw)
- Invoice generation (Finance Claw)
- PR open (Build Claw)
- Any content draft (Content Claw)

Key AUTO actions (run autonomously, logged for morning digest):
- Analytics weekly report publication
- Issue triage and scoring (Build Claw)
- Dependency audit initiation (Build Claw)
- Brand asset usage (Content Claw)
- Expense logging (Finance Claw)

**Morning brief (07:00 daily):**
A digest of everything that ran on AUTO overnight — what the claws
did while the operator was asleep. No decision required, just awareness.

**Evening wrap (20:00 daily):**
What ran today, what's queued for tomorrow, any evolution log entries
from the week's cycle.

---

## THE SELF-EVOLUTION CYCLE — HOW IT WORKS

Every Sunday at 02:00 (while the operator is asleep), each claw runs
its Evolution Cycle — a 5-stage autonomous process:

```
1. OBSERVE   — Review the week's operational log:
               what actions ran, which were approved vs edited vs rejected,
               what outcomes were measured, what inter-claw signals came in

2. IDENTIFY  — Surface recurring patterns:
               approval rate by content type, client response by comms style,
               feature adoption by user segment, cost drift by provider

3. PROPOSE   — Nominate a new tool to address the pattern:
               a classifier, predictor, optimizer, or generator variant

4. BUILD & TEST — Build the tool inside the sandbox and validate it
                  against 4 weeks of historical data.
                  Must outperform baseline by 5% minimum to qualify.
                  Failed tools are discarded. Passed tools are staged.

5. DEPLOY    — Tool activates in the claw's live toolkit.
               Blueprint is versioned. War Room logs the new tool
               with its trigger pattern and performance delta.
               Operator can disable any tool at any time.
```

**Critical constraint:** Evolution cannot expand a claw's permissions.
A tool proposed by the Content Claw that would require access to
`/sandbox/clients` is rejected at the build stage. The privacy policy
is architectural, not instructional — the Evolution Cycle cannot work
around it.

**Minimum thresholds before first evolution (solo-founder.yaml):**
- Content Claw: 10 approved posts minimum
- Ops Claw: 5 client interactions minimum
- Analytics Claw: 3 weeks of data minimum
- Finance Claw: 3 invoices minimum
- Build Claw: 5 merged PRs minimum

These thresholds exist to prevent low-quality tools being built from
insufficient signal. A claw that hasn't done enough work yet will skip
its evolution cycle and try again next week.

---

## INFERENCE ROUTING — THE PRIVACY ROUTER

The privacy router sits between every claw and the inference providers.
It intercepts every model call and routes it based on data sensitivity —
not based on which claw is asking or what the claw thinks it wants.

**Three inference backends:**
- Cloud: `nvidia/nemotron-3-super-120b-a12b` via NVIDIA Cloud API
  (highest quality, requires API key, data leaves the machine)
- Local NIM: Nemotron on RTX GPU
  (high quality, private, data stays on device)
- vLLM: Nemotron Nano 30B
  (development/testing, lightweight, fully local)

**Routing rules (solo-founder.yaml — solo_mode: true):**

| Data Type                  | Route  | Reason                                    |
|----------------------------|--------|-------------------------------------------|
| Client-facing drafts       | Cloud  | Quality matters — external visibility     |
| Internal ideation          | Local/Cloud  | Private creative process                  |
| Financial data             | Local/Cloud  | LOCKED — PrivacyPolicyViolationError      |
| Source code                | Local/Cloud  | LOCKED — PrivacyPolicyViolationError      |
| Client records             | Local/Cloud  | Sensitive business data                   |
| Analytics synthesis        | Local/Cloud  | Proprietary operational data              |
| Public docs / changelogs   | Cloud  | Non-sensitive, quality preferred          |

**Locked routes** (financial_data, source_code) raise
`PrivacyPolicyViolationError` if anything attempts to override them.
This is enforced in `solo_privacy.py` and cannot be bypassed by any
claw instruction, Evolution Cycle tool, or operator command.

**Cost guard (solo-founder.yaml):**
- Daily cloud token budget: 100,000 tokens
- Warning alert at 80% of budget
- Automatic fallback to local inference if budget exceeded
- Never fails — always falls back, never blocks a claw action

---

## DEEP WORK MODE (SOLO EQUIVALENT OF FINALS MODE)

`milimo squad finals-mode` activates Deep Work Mode — a hot-reload
of all five claw policies simultaneously for periods when the operator
needs to go heads-down (sprint, travel, focused work block).

**What happens on activation:**

| Claw      | Behavior in Deep Work Mode                                      |
|-----------|-----------------------------------------------------------------|
| Content   | Pauses new draft generation. Queue only. No publishing.         |
| Ops       | Auto-response to all active clients via template. No new intake.|
| Analytics | Passive data collection only. No new experiments.               |
| Finance   | Invoice sends continue. No new project initiations.             |
| Build     | Issue triage only. No new PRs opened. No deploys.               |

**Auto-response template:**
"Hey [name], I'm heads-down on a focused sprint until [resume_date].
Your project is on track — I'll be back in full swing then. 🙏"

**Resume:** `milimo squad finals-mode --resume-date YYYY-MM-DD`
Scheduled resume hot-reloads all policies back to their pre-Deep-Work
state and sends a reactivation message to all paused clients.

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE

If the solo template is functioning as designed, the operator experiences
the following daily rhythm:

**Morning (07:00):**
- War Room morning brief arrives: digest of overnight autonomous activity
- Typically 3–8 items in the REVIEW queue from overnight claw work
- Morning review takes 10–15 minutes
- Operator approves, edits, or blocks each item
- Claws immediately execute approved actions

**Daytime (passive):**
- Claws continue running autonomously
- HOLD items (PR merge, invoice send, production deploy) arrive as
  War Room notifications requiring explicit release
- Operator handles HOLD items in under 2 minutes each
- No other operator input required

**Evening (20:00):**
- War Room evening wrap: what ran today, what's queued for tomorrow
- Evolution log summary if Sunday: what each claw built this week

**Sunday night (02:00):**
- All five Evolution Cycles run while operator sleeps
- New tools built, tested, deployed (or discarded)
- Monday morning brief includes evolution log with new tool summaries

**By month 3:**
- Content drafts arrive pre-styled, pre-timed, pre-calibrated to each
  client's voice — requiring minimal editing before approval
- Ops handles 80%+ of client intake without escalation
- Analytics weekly report is predictive, not just descriptive
- Finance has never sent an underpriced proposal in weeks
- Build Claw's evolved tools catch common bug classes before PRs open

---

## WHAT FAILURE LOOKS LIKE (DEBUGGING REFERENCE)

If something is wrong, these are the symptoms and their likely causes:

| Symptom | Likely Cause |
|---------|-------------|
| War Room shows "squadName not configured" | Config source mismatch — warroom.ts reading wrong config file |
| Claws not coordinating | Mesh using file-based queues instead of OpenShell gateway |
| Financial data routed to cloud | PrivacyPolicyViolationError not raised — privacy router bug |
| Evolution cycle not running | Minimum threshold not met, or scheduler not initialized |
| Build Claw deploys without HOLD clearance | Approval threshold misconfigured in solo-founder.yaml |
| War Room queue shows AUTO items as REVIEW | Approval mode mapping wrong in approval.ts |
| Morning brief not arriving | Digest schedule not initialized from war_room config |
| Claws reading each other's mounts | Landlock policy not applied — OpenShell not enforcing filesystem |
| Cost guard not triggering | Token counter not initialized, or daily_cloud_token_budget not read |
| Deep Work Mode not hot-reloading | Policy reload not propagating to running sandboxes |

---

## FILES THAT IMPLEMENT THIS BEHAVIOR

### TypeScript (milimo/src/)
| File | What it implements |
|------|--------------------|
| `commands/onboard.ts` | Template selection, squad naming, claw role assignment |
| `commands/warroom.ts` | War Room launcher |
| `warroom/warroom.ts` | War Room TUI — queue, health panel, evolution log |
| `warroom/approval.ts` | HOLD/REVIEW/AUTO/VETO logic, threshold enforcement |
| `warroom/audit.ts` | Audit logging for every operator decision |
| `warroom/evolution.ts` | Evolution log display in War Room |
| `warroom/health-dashboard.ts` | Claw health panel |
| `warroom/rate-limiter.ts` | AUTO action rate limiting |
| `onboard/config.ts` | Config persistence — single source of truth |
| `onboard/template.ts` | solo-founder.yaml loading and validation |

### Python (milimo-blueprint/orchestrator/)
| File | What it implements |
|------|--------------------|
| `solo_init.py` | Filesystem mount creation, sandbox policy generation |
| `solo_warroom.py` | SoloWarRoom class — prioritized queue, morning/evening digest |
| `solo_privacy.py` | SoloPrivacyRouter — routing rules, locked routes, cost guard |
| `evolution_cycle.py` | 5-stage evolution cycle |
| `pattern_detector.py` | Pattern identification from operational logs |
| `tool_proposal.py` | Tool nomination logic |
| `tool_builder.py` | Tool construction and sandbox testing |
| `tool_registry.py` | Deployed tool inventory per claw |
| `mesh.py` | Inter-claw message routing and contract validation |
| `contracts.py` | Message type schema definitions |
| `privacy_router.py` | Base privacy router (solo_privacy.py extends this) |

### Configuration
| File | What it contains |
|------|-----------------|
| `templates/solo-founder.yaml` | Full solo template: operator policy, filesystem, inference routing, evolution thresholds, deep work mode |
| `roles/content-claw.yaml` | Content Claw blueprint: mounts, egress, inference, inter-claw policy |
| `roles/ops-claw.yaml` | Ops Claw blueprint |
| `roles/analytics-claw.yaml` | Analytics Claw blueprint |
| `roles/finance-claw.yaml` | Finance Claw blueprint |
| `roles/build-claw.yaml` | Build Claw blueprint |
| `policies/{role}-claw.yaml` | OpenShell sandbox policies per role |
| `~/.milimo/config.json` | Live operator config — single source of truth |

---

*This specification is the ground truth for the solo-founder template.
If behavior in the codebase deviates from this document, the code is wrong.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
