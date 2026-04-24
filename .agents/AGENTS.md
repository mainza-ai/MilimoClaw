# AGENTS.md — Milimo Claw

> *Milimo* (mi-LEE-mo) · Tonga, Zambia · **"works. tasks. labour."**

Milimo Claw is a multi-agent autonomous hustle platform built on NVIDIA NemoClaw.
This file defines the agents in the system — their roles, responsibilities, boundaries,
coordination rules, and the conventions that govern how they behave and are built.

**Any AI coding assistant working on this codebase must read this file in full
before writing or modifying any agent-related code.**

---

## Ground Truth Hierarchy

When documents conflict, this order determines which is authoritative:

1. **Individual claw spec documents** — ground truth for each claw's internal
   behavior, filesystem layout, network egress, and inference routing
2. **MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md** — ground truth for cross-claw
   coordination, approval thresholds, and scheduling in solo mode
3. **solo-founder.yaml** — configuration values that implement the above
4. **This file (AGENTS.md)** — quick reference summary, not ground truth

If this file conflicts with a claw spec: the claw spec wins on internal
claw behavior. The solo template spec wins on coordination and scheduling.
This file is never the tiebreaker.

---

## Architecture Overview

Milimo Claw is a NemoClaw plugin. Each agent (called a **claw**) runs inside an
isolated NemoClaw sandbox on an operator's RTX laptop. The sandboxes are connected
through the NVIDIA OpenShell inter-sandbox gateway — a policy-enforced communication
layer where every message between claws is typed, logged, and validated.

```
┌──────────────────────────────────────────────────────────────────────┐
│ MILIMO CLAW MESH │
│ │
│ CONTENT CLAW OPS CLAW ANALYTICS CLAW FINANCE CLAW │
│ /sandbox/ /sandbox/ /sandbox/ /sandbox/ │
│ content clients analytics finance │
│ OpenShell GW ── OpenShell GW── OpenShell GW ── OpenShell GW │
│ │ │ │ │ │
│ └───────────────┴───────────────┴───────────────┘ │
│ INTER-SANDBOX CHANNEL │
│ (typed contracts · logged · policy-enforced) │
│ │
│ BUILD CLAW (tech squads) ASSISTANT CLAW (operator bridge) │
│ /sandbox/build /sandbox/.milimo/assistant │
│ OpenShell GW ──────────────────────────┘ │
│ │ ════════════════════════════════════════════════════════════════ │
│ WAR ROOM (TUI) │
│ Every pending action · every claw · one view │
└──────────────────────────────────────────────────────────────────────┘
```

**Plugin namespace:** `openclaw milimo`
**Blueprint location:** `milimo-blueprint/`
**TypeScript CLI:** `milimo/src/`
**Python orchestrator:** `milimo-blueprint/orchestrator/`

---

## The Six Claws

### 1. Content Claw

**Role:** Creative department. Generates all content autonomously.

**Sandbox:** `content-claw`
**Filesystem mount:** `/sandbox/content`
**Blueprint:** `milimo-blueprint/roles/content-claw.yaml`
**Policy:** `milimo-blueprint/policies/content-sandbox.yaml`
**Orchestrator:** `milimo-blueprint/orchestrator/content/`

**What it does:**
- Generates social posts, copy, campaigns, proposals, and content calendars
- Applies a pipeline of self-evolved tools to every draft before surfacing it
- Queries the Analytics Claw weekly for top-performing content patterns
- Schedules approved content via platform publishing APIs
- Monitors post-publication performance and sends signals to Analytics Claw
- Sends `brief_acknowledged` within 5 minutes of every project brief received

**What it cannot do:**
- Read `/sandbox/clients`, `/sandbox/finance`, `/sandbox/build`, or `/sandbox/.milimo/assistant`
- Publish anything without operator REVIEW approval in the War Room
- Make inference calls that bypass the privacy router

**Approval thresholds:**
| Action | Mode |
|---|---|
| Social post draft | REVIEW |
| Client proposal | REVIEW |
| Email campaign | REVIEW |
| Brand asset usage | AUTO |
| Content calendar update | AUTO |
| A/B variant | REVIEW |
| Trend-reactive post | REVIEW |

**Inter-claw messages sent:**
- `draft_ready` → War Room
- `content_performance_query` → Analytics Claw (Monday 06:00 + on demand)
- `performance_signal` → Analytics Claw (after every published post)
- `brief_acknowledged` → Ops Claw (within 5 min of project_brief received)
- `deliverable_complete` → Ops Claw (when all deliverables published)

**Inter-claw messages received:**
- `project_brief` from Ops Claw
- `performance_intel` from Analytics Claw
- `client_health_signal` from Analytics Claw
- `revision_request` from Ops Claw

**Evolution tools (emerge autonomously over time):**
Style descriptor → Tone classifier → Approval predictor →
Platform calibrator → Timing optimizer → A/B variant engine →
Client voice adapter → Trend injector

**Spec document:** `milimo-claw-docs/reference/MILIMO_CLAW_CONTENT_CLAW_SPEC.md`
**Implementation prompt:** `milimo-claw-docs/prompts/CONTENT_CLAW_IMPLEMENTATION_PROMPT.md`

---

### 2. Ops Claw

**Role:** Account manager and project manager. Owns the full client lifecycle.

**Sandbox:** `ops-claw`
**Filesystem mount:** `/sandbox/clients`
**Blueprint:** `milimo-blueprint/roles/ops-claw.yaml`
**Policy:** `milimo-blueprint/policies/ops-sandbox.yaml`
**Orchestrator:** `milimo-blueprint/orchestrator/ops/`

**What it does:**
- Intercepts and triages all incoming client inquiries (budget 40%, scope 30%, fit 30%)
- Manages the full project lifecycle: intake → scoping → delivery → close
- Runs deadline risk prediction daily for all active projects
- Detects scope creep and drafts change orders (always HOLD — never auto)
- Scores client relationship health weekly and sends signals to Analytics Claw
- Always queries Finance Claw for pricing before sending any proposal

**What it cannot do:**
- Read `/sandbox/finance`, `/sandbox/content`, `/sandbox/build`, or `/sandbox/.milimo/assistant`
- Send any client-facing message without operator REVIEW approval
- Send a `project_brief` before receiving a `pricing_response` from Finance Claw
- Generate or send invoices — Finance Claw only
- Send `project_complete` before client confirms receipt of deliverables

**Approval thresholds:**
| Action | Mode |
|---|---|
| New client welcome message | REVIEW |
| Intake questionnaire | REVIEW |
| Client proposal | REVIEW |
| Project brief to creative claws | REVIEW |
| Routine client update | AUTO |
| Deadline risk flag (5+ days) | REVIEW |
| Deadline critical (24 hours) | HOLD |
| Scope creep change order | HOLD |
| Client delivery message | REVIEW |
| Deep Work auto-response | AUTO |

**Sequencing rule (non-negotiable):**
`pricing_query` must be sent and `pricing_response` received before
`project_brief` is sent to any creative claw. No exceptions.
`project_complete` fires only after client confirms receipt — not on
internal completion, not on deploy.

**Inter-claw messages sent:**
- `project_brief` → Content Claw or Build Claw
- `feature_brief` → Build Claw
- `pricing_query` → Finance Claw (before any proposal)
- `project_complete` → Finance Claw (triggers invoice, client confirmed only)
- `client_health_signal` → Analytics Claw (weekly)
- `client_onboarded` → Analytics Claw

**Inter-claw messages received:**
- `deliverable_complete` from Content Claw
- `deploy_complete` from Build Claw
- `pricing_response` from Finance Claw
- `invoice_ready` from Finance Claw
- `payment_overdue` from Finance Claw
- `feature_brief_acknowledged` from Build Claw

**Evolution tools (emerge autonomously over time):**
Client triage scorer → Brief quality checker → Deadline risk predictor →
Communication tone calibrator → Scope creep detector v2 →
Relationship health scorer v2

**Spec document:** `milimo-claw-docs/reference/MILIMO_CLAW_OPS_CLAW_SPEC.md`
**Implementation prompt:** `milimo-claw-docs/prompts/OPS_CLAW_IMPLEMENTATION_PROMPT.md`

---

### 3. Analytics Claw

**Role:** Intelligence layer. Observes everything, acts on nothing.

**Sandbox:** `analytics-claw`
**Filesystem mount:** `/sandbox/analytics`
**Blueprint:** `milimo-blueprint/roles/analytics-claw.yaml`
**Policy:** `milimo-blueprint/policies/analytics-sandbox.yaml`
**Orchestrator:** `milimo-blueprint/orchestrator/analytics/`

**What it does:**
- Collects and stores performance signals from all other claws
- Generates the weekly intelligence report every Sunday at 02:00
- Runs continuous anomaly detection against 30-day rolling baselines
- Scores opportunities daily at 06:00 — dispatches immediately at >0.85 confidence
- Responds to on-demand queries from Content and Build Claws within 2 minutes
- Maintains forward projections for revenue, engagement, and delivery velocity

**What it cannot do:**
- Write to any external platform — read-only network access only
- Read `/sandbox/clients`, `/sandbox/finance`, `/sandbox/build`, or `/sandbox/.milimo/assistant` raw records
- Queue HOLD actions in the War Room — it observes, never blocks
- Perform any write operation to external APIs

**Primary output — shared filesystem (CRITICAL):**
```
/sandbox/analytics/reports/weekly-intelligence.json
```
This is the only file in the entire mesh that all six claws can read
directly without a message contract. It must be configured as a
read-only mount in **every** claw's sandbox policy file.
**If any claw cannot read this file, the intelligence layer is silently broken.**
Verify all six sandbox policies contain this mount. Run Phase A tests first.

**Anomaly thresholds:**
- Positive anomaly: current value > 2× baseline
- Negative anomaly: current value < 0.5× baseline

**Query response SLA: 2 minutes maximum. Log violations. Never timeout silently.**

**Scheduling:**
| Time | Action |
|---|---|
| Sunday 01:00 | Baseline recalculation |
| Sunday 02:00 | Weekly intelligence report generation |
| Daily 06:00 | Opportunity scoring |
| On signal receipt | Anomaly detection |
| On query receipt | Query response (2-min SLA) |

**Inter-claw messages sent:**
- `performance_intel` → Content Claw (weekly + high-confidence opportunity)
- `retention_signals` → Build Claw (weekly + churn anomaly)
- `client_health_alert` → Ops Claw (immediately when health < 6.0)
- `revenue_anomaly` → Finance Claw (immediately on anomaly detection)
- `content_performance_response` → Content Claw (query response)
- `behavior_query_response` → Build Claw (query response)

**Inter-claw messages received:**
- `performance_signal` from Content Claw
- `client_health_signal` from Ops Claw
- `client_onboarded` from Ops Claw
- `revenue_summary` from Finance Claw
- `shipping_summary` from Build Claw
- `content_performance_query` from Content Claw
- `behavior_query` from Build Claw

**Evolution tools (emerge autonomously over time):**
Engagement baseline model → Anomaly detector v2 → Opportunity scorer v2 →
Retention correlator → Competitor signal tracker → Forward projection engine v2

**Spec document:** `milimo-claw-docs/reference/MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md`
**Implementation prompt:** `milimo-claw-docs/prompts/ANALYTICS_CLAW_IMPLEMENTATION_PROMPT.md`

---

### 4. Finance Claw

**Role:** Financial nervous system. Tracks every dollar, protects every margin.

**Sandbox:** `finance-claw`
**Filesystem mount:** `/sandbox/finance`
**Blueprint:** `milimo-blueprint/roles/finance-claw.yaml`
**Policy:** `milimo-blueprint/policies/finance-sandbox.yaml`
**Orchestrator:** `milimo-blueprint/orchestrator/finance/`

**What it does:**
- Responds to pricing queries from Ops Claw within 10 minutes
- Generates invoices when projects complete (two-stage approval — see below)
- Monitors payment status via Stripe API every 24 hours
- Detects and escalates overdue payments immediately
- Logs and tax-categorizes all expenses
- Generates weekly revenue summaries and sends totals to Analytics Claw
- Prepares quarterly tax summaries on quarter start dates

**What it cannot do:**
- Communicate with clients directly — ever
- Read `/sandbox/clients`, `/sandbox/content`, `/sandbox/build`, or `/sandbox/.milimo/assistant`
- Initiate financial transfers — payment status checks only
- Send any invoice without two-stage operator approval (see below)
- Include line items, client names, or invoice IDs in `revenue_summary` — totals only

**Two-stage invoice approval — non-negotiable:**
```
Stage 1 — REVIEW:
  Operator sees full invoice. Approving Stage 1 does NOT send the invoice.
  It moves the invoice to the HOLD queue only.

Stage 2 — HOLD release:
  The only trigger for Stripe invoice transmission.
  No code path may send an invoice without an explicit HOLD release.

If Stage 1 approval triggers transmission: CRITICAL BUG.
```

**Approval thresholds:**
| Action | Mode |
|---|---|
| Invoice generation (review content) | REVIEW |
| Invoice send (trigger transmission) | HOLD |
| Expense log entry | AUTO |
| Overdue payment alert (first) | REVIEW |
| Overdue payment alert (repeat) | HOLD |
| Margin compression alert | REVIEW |
| Rate optimization advisory | REVIEW |
| Tax quarterly summary | AUTO |

**Scheduling:**
| Time | Action |
|---|---|
| Daily 09:00 | Payment status check + overdue detection |
| Sunday 03:00 | Weekly revenue summary + evolution cycle |
| Quarter start (Jan 1, Apr 1, Jul 1, Oct 1) | Tax prep summary |

**Inter-claw messages sent:**
- `pricing_response` → Ops Claw (within 10 min of query)
- `invoice_ready` → Ops Claw (after Stage 1 REVIEW approve)
- `payment_overdue` → Ops Claw (immediately on overdue detection)
- `revenue_summary` → Analytics Claw (totals only — no line items ever)

**Inter-claw messages received:**
- `pricing_query` from Ops Claw
- `project_complete` from Ops Claw

**Evolution tools (emerge autonomously over time):**
Scope cost estimator v2 → Pricing floor guardian → Payment risk scorer v2 →
Margin tracker v2 → Tax category classifier v2 → Rate optimization advisor v2

**Spec document:** `milimo-claw-docs/reference/MILIMO_CLAW_FINANCE_CLAW_SPEC.md`
**Implementation prompt:** `milimo-claw-docs/prompts/FINANCE_CLAW_IMPLEMENTATION_PROMPT.md`

---

### 5. Build Claw *(Tech squads only)*

**Role:** Engineering department. Ships code autonomously.

**Sandbox:** `build-claw`
**Filesystem mount:** `/sandbox/build`
**Blueprint:** `milimo-blueprint/roles/build-claw.yaml`
**Policy:** `milimo-blueprint/policies/build-sandbox.yaml`
**Orchestrator:** `milimo-blueprint/orchestrator/build/`

**What it does:**
- Reads open GitHub issues, scores by complexity, proposes sprint plans
- Queries Analytics Claw before sprint planning (5-min timeout then proceeds)
- Writes code from approved issues, opens PRs, runs test suites
- Monitors production error logs and auto-drafts patches for recurring errors
- Runs weekly dependency audits and queues security PRs
- Tracks inference API costs daily and alerts on drift > 15%
- Sends shipping summaries to Content Claw for devlog posts (Friday 17:00)
- Sends deploy completion signals to Ops Claw after every production deploy
- Acknowledges every feature_brief from Ops Claw within 10 minutes

**What it cannot do:**
- Merge any PR without operator HOLD clearance
- Deploy to production without operator HOLD clearance (separate from PR HOLD)
- Share source code or API keys with any other claw via inter-sandbox message
- Read `/sandbox/clients`, `/sandbox/finance`, `/sandbox/content`, or `/sandbox/.milimo/assistant`

**Two separate two-stage approval flows:**
```
PR Flow:
  Stage 1 — REVIEW: operator reviews code diff and test results
  REVIEW approve → PR moves to HOLD queue (does NOT merge)
  Stage 2 — HOLD: operator releases to trigger GitHub merge

Deploy Flow (independent of PR flow):
  PR merged → deployment staged automatically
  Deploy queued as its own separate HOLD
  HOLD release → production deployment triggered
  A merged PR that has not been deployed waits in deploy HOLD indefinitely.

If REVIEW approve triggers merge: CRITICAL BUG.
If PR merge auto-deploys without deploy HOLD: CRITICAL BUG.
```

**Approval thresholds:**
| Action | Mode |
|---|---|
| Sprint plan | REVIEW |
| PR open | REVIEW |
| PR merge | HOLD |
| Production deploy | HOLD (separate from PR HOLD) |
| Issue triage and scoring | AUTO |
| Dependency audit | AUTO |
| Error pattern detection | REVIEW |
| Auto-drafted patch PR | REVIEW |
| Cost alert | REVIEW |
| Devlog draft | AUTO |
| Changelog update | AUTO |

**Scheduling:**
| Time | Action |
|---|---|
| Every 30 min | Error monitoring pass |
| Daily | Inference cost monitoring |
| Monday 08:00 | Dependency security audit |
| Friday 17:00 | Weekly devlog + shipping_summary to Content |
| Sunday 02:35 | Evolution cycle |

**Inter-claw messages sent:**
- `deploy_complete` → Ops Claw (after every production deploy)
- `feature_brief_acknowledged` → Ops Claw (within 10 min of feature_brief)
- `shipping_summary` → Content Claw (Friday 17:00 — accumulated weekly)
- `behavior_query` → Analytics Claw (before sprint planning)

**Inter-claw messages received:**
- `feature_brief` from Ops Claw
- `retention_signals` from Analytics Claw
- `behavior_query_response` from Analytics Claw

**Evolution tools (emerge autonomously over time):**
PR style enforcer → Issue complexity scorer v2 → Prompt regression tester →
Cost anomaly detector v2 → Dependency audit runner v2 →
Error pattern classifier v2 → Churn signal correlator → Auto-roadmap drafter

**Spec document:** `milimo-claw-docs/reference/MILIMO_CLAW_BUILD_CLAW_SPEC.md`
**Implementation prompt:** `milimo-claw-docs/prompts/BUILD_CLAW_IMPLEMENTATION_PROMPT.md`

---

### 6. Assistant Claw

**Role:** Operator bridge and cross-claw coordinator. Lucy.

**Sandbox:** `assistant-claw`
**Filesystem mount:** `/sandbox/.milimo/assistant`
**Blueprint:** `milimo-blueprint/roles/assistant-claw.yaml`
**Policy:** `milimo-blueprint/policies/assistant-sandbox.yaml`
**Orchestrator:** `milimo-blueprint/orchestrator/assistant/`

**What it does:**
- Serves as the operator's primary interface to the claw mesh
- Routes natural-language requests to the appropriate claw via typed contracts
- Aggregates cross-claw status into a single digest for the operator
- Can query any worker claw and relay responses back to the operator
- Monitors all `assistant_response` messages from worker claws
- Maintains conversation context with the operator across sessions

**What it cannot do:**
- Read `/sandbox/content`, `/sandbox/clients`, `/sandbox/analytics`, `/sandbox/finance`, or `/sandbox/build`
- Send any client-facing message — operator communication only
- Execute financial transactions, merge PRs, or publish content
- Modify any other claw's filesystem or configuration
- Bypass approval thresholds — always defers to War Room

**Approval thresholds:**
| Action | Mode |
|---|---|
| Cross-claw query dispatch | AUTO |
| Operator digest generation | AUTO |
| Claw response relay to operator | AUTO |
| Policy change proposal | REVIEW |
| Sandbox rebuild request | HOLD |

**Inter-claw messages sent:**
- `assistant_query` → Any worker claw (on operator request)
- `assistant_task` → Any worker claw (delegated task from operator)

**Inter-claw messages received:**
- `assistant_response` from any worker claw (response to query/task)

**Evolution schedule:**
| Time | Action |
|---|---|
| Sunday 03:15 | Evolution cycle |

**Evolution tools (emerge autonomously over time):**
Query router optimizer → Response summarizer → Context window manager →
Operator preference adapter → Cross-claw priority sorter v2

**Spec document:** `milimo-claw-docs/reference/MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md`

---

## Coordination Rules

### Typed Message Contracts

All inter-claw communication uses typed message contracts enforced by the
OpenShell gateway. Every message must conform to its schema in `contracts.py`.

**Every message includes:**
```python
{
    "message_id": str,      # UUID
    "message_type": str,    # must match a key in contracts.py
    "sender_role": str,     # must match contract sender_roles
    "recipient_role": str,  # must match contract recipient_roles
    "timestamp": str,       # ISO 8601
    "payload": dict         # must match contract payload schema
}
```

**Contracts file:** `milimo-blueprint/orchestrator/contracts.py`
Currently defines 27 message type schemas.

### Complete Message Matrix

| From | To | Message Type | Trigger |
|---|---|---|---|
| Content | War Room | `draft_ready` | Draft ready for review |
| Content | Analytics | `content_performance_query` | Monday 06:00 + on demand |
| Content | Analytics | `performance_signal` | After every published post |
| Content | Ops | `brief_acknowledged` | Within 5 min of project_brief |
| Content | Ops | `deliverable_complete` | All deliverables published |
| Ops | Content or Build | `project_brief` | New project scoped + pricing confirmed |
| Ops | Build | `feature_brief` | New technical feature requested |
| Ops | Finance | `pricing_query` | Before any proposal |
| Ops | Finance | `project_complete` | Client confirms delivery |
| Ops | Analytics | `client_health_signal` | Weekly |
| Ops | Analytics | `client_onboarded` | New client onboarded |
| Analytics | Content | `performance_intel` | Weekly + high-confidence opportunity |
| Analytics | Build | `retention_signals` | Weekly + churn anomaly |
| Analytics | Ops | `client_health_alert` | When client health < 6.0 |
| Analytics | Finance | `revenue_anomaly` | On anomaly detection |
| Analytics | Content | `content_performance_response` | Query response |
| Analytics | Build | `behavior_query_response` | Query response |
| Finance | Ops | `pricing_response` | Within 10 min of query |
| Finance | Ops | `invoice_ready` | After Stage 1 approval |
| Finance | Ops | `payment_overdue` | Immediately on overdue |
| Finance | Analytics | `revenue_summary` | Weekly + on payment |
| Build | Ops | `deploy_complete` | Production deploy |
| Build | Ops | `feature_brief_acknowledged` | Within 10 min of feature_brief |
| Build | Content | `shipping_summary` | Friday 17:00 (weekly accumulated) |
| Build | Analytics | `behavior_query` | Before sprint planning |
| Assistant | Any worker | `assistant_query` | On operator request |
| Assistant | Any worker | `assistant_task` | Delegated task from operator |
| Any worker | Assistant | `assistant_response` | Response to query/task |

### Non-Negotiable Sequencing Rules

These ten rules apply in every deployment — solo or squad:

1. **OPS → FINANCE sequencing:** `pricing_query` sent and `pricing_response`
   received BEFORE `project_brief` sent to any creative claw. No exceptions.

2. **FINANCE two-stage invoice:** Stage 1 REVIEW approve → HOLD queue only.
   Stage 2 HOLD release → only trigger for Stripe transmission.
   If REVIEW approve sends invoice: critical bug.

3. **BUILD two-stage PR + deploy:** PR REVIEW approve → HOLD (not merge).
   PR HOLD release → GitHub merge. Deploy stages after merge.
   Deploy HOLD release → production deployment. Two independent HOLD queues.
   PR merge does NOT auto-deploy.

4. **FINANCE project_complete:** Fires only after client confirms receipt.
   Not on internal completion. Not on deploy. Never earlier.

5. **CONTENT brief_acknowledged:** Must send within 5 minutes of every
   `project_brief` received from Ops Claw.

6. **BUILD feature_brief_acknowledged:** Must send within 10 minutes of every
   `feature_brief` received from Ops Claw.

7. **ANALYTICS query response SLA:** Must respond to
   `content_performance_query` and `behavior_query` within 2 minutes.
   Log SLA violations. Never timeout silently.

8. **BUILD sprint planning timeout:** If `behavior_query_response` does not
arrive within 5 minutes, proceed with complexity scores only. Log. Never block.

9. **ASSISTANT query routing:** `assistant_query` must specify a single
recipient claw. Broadcast queries are not permitted — use per-claw queries.

10. **ASSISTANT task delegation:** `assistant_task` requires operator REVIEW
approval before dispatch if the task involves financial, client, or deploy actions.

### Filesystem Isolation

Each claw owns exactly one filesystem mount. No claw can read another
claw's mount directly. Cross-claw data sharing happens exclusively through
typed messages.

**One exception — the Analytics Claw's shared read export:**
```
/sandbox/analytics/reports/weekly-intelligence.json
```
This file must be configured as a read-only mount in **all six** claw
sandbox policies. Verify with Phase A isolation tests before anything else.

### Privacy Router

Every inference call is intercepted by the privacy router.
**Development phase:** All inference routes to cloud (NEMOCLAW_MODEL).
The `data_type` field must be logged on every inference call.

```python
# Required pattern — every inference call in every claw:
response = inference_client.complete(
    prompt=prompt,
    data_type="scope_cost_estimation",  # ALWAYS INCLUDE — never omit
    max_tokens=800
)
```

**Production routing targets (not enforced during dev):**

| Claw | Sensitive data types → Local NIM (NEMOCLAW_MODEL) |
|---|---|
| Content | Internal ideation, draft iterations, voice adapter calibration |
| Ops | Contract review, internal summaries, scope analysis |
| Analytics | Performance synthesis, predictive models, opportunity scoring |
| Finance | ALL financial data — locked, no exceptions in production |
| Build | Source code, API keys, architecture decisions, code review |
| Assistant | Operator conversation history, cross-claw query context |

---

## The War Room

The War Room surfaces every pending action from every claw in one
prioritized queue. HOLD always appears above REVIEW. REVIEW above AUTO.

**Queue priority:**
```
🔴 HOLD   — requires explicit operator release
🟡 REVIEW — requires operator decision before execution
✓  AUTO   — executed, logged for morning digest
```

**Keyboard shortcuts:**
| Key | Action |
|---|---|
| A | Approve current REVIEW |
| B | Block current item |
| E | Edit inline |
| R | Release current HOLD |
| D | Toggle morning digest / evening wrap |
| F | Toggle Deep Work Mode |
| H | Help overlay |
| Q | Quit |

**Daily schedule:**
- 07:00 — Morning brief: overnight AUTO log + pending queue summary
- 20:00 — Evening wrap: today's activity + tomorrow's queue preview

**Solo operator target:** Full War Room review in under 15 minutes per day.

**War Room TUI:** `milimo/src/warroom/warroom-tui.ts`
**Approval engine:** `milimo/src/warroom/approval.ts`

---

## The Self-Evolution Cycle

Every claw runs an Evolution Cycle every Sunday. The schedule is staggered
so each claw runs on fresh Analytics intelligence.

**Solo-founder template schedule:**
| Time | Action |
|---|---|
| Sunday 01:00 | Analytics: baseline recalculation |
| Sunday 02:00 | Analytics: weekly intelligence report |
| Sunday 02:05 | Content: evolution cycle |
| Sunday 02:15 | Ops: evolution cycle |
| Sunday 02:25 | Analytics: evolution cycle |
| Sunday 02:35 | Build: evolution cycle |
| Sunday 03:00 | Finance: weekly revenue summary + evolution cycle |
| Sunday 03:15 | Assistant: evolution cycle |

Analytics runs first. Every other claw's cycle reads the fresh report.
Finance runs last — its evolution uses the revenue summary it just generated.

**The 5-stage cycle:**
```
1. OBSERVE   — Review week's logs, approval decisions, outcomes
2. IDENTIFY  — Surface recurring patterns from operational history
3. PROPOSE   — Nominate one new tool for the strongest pattern
4. BUILD     — Generate via inference, test against 4 weeks of history
               Must outperform baseline by minimum 5% to qualify
5. DEPLOY    — Activate, version blueprint, log to War Room evolution panel
```

**Evolution engine:** `milimo-blueprint/orchestrator/evolution_cycle.py`
**Solo scheduler:** `milimo-blueprint/orchestrator/solo_evolution.py`
Config key: `evolution.schedule` (per-claw times, not single `time`)

**Minimum data thresholds before first evolution:**
| Claw | Threshold |
|---|---|
| Content | 10 approved posts + 3 rejected drafts + 1 week performance data |
| Ops | 5 client interactions + 3 projects + 2 weeks comms data |
| Analytics | 3 weeks signal data + 1 revenue_summary + 1 health_signal |
| Finance | 3 invoices + 2 completed projects + 4 weeks expense data |
| Build | 5 merged PRs + 3 sprints + 2 deploys + 4 weeks cost data |
| Assistant | 20 cross-claw queries + 10 operator sessions + 2 weeks routing data |

---

## Blueprint System

Every claw's configuration is a versioned, SHA-256 signed blueprint.

```bash
milimo blueprint fork @squadname/blueprint-name --into my-claw
milimo blueprint diff v2.1 v8.3
milimo blueprint publish --name "description" --price 0.05eth
milimo blueprint rollback --to v3.0 --reason "reason"
```

---

## Squad Templates

| Template | Claws | Category |
|---|---|---|
| `solo-founder` | All 6 | Founder |
| `content-agency` | Content + Ops + Analytics | Creative |
| `design-studio` | Content + Ops + Finance | Creative |
| `event-promotion` | Content + Ops + Analytics | Creative |
| `freelance-collective` | Ops + Analytics + Finance | Commerce |
| `ai-micro-saas` | Build + Ops + Analytics + Finance | Tech |
| `campus-ai-tool` | Build + Content + Ops | Tech |

**Templates directory:** `milimo-blueprint/templates/`

**Solo founder template:** `milimo-blueprint/templates/solo-founder.yaml`
Primary template for development and testing. All six claws, one operator,
one machine. Evolution schedule uses per-claw `schedule:` block (not `time:`).
Cost guard: 50,000 daily token budget, `lighter_prompt` fallback, never block.

**Solo template spec:** `milimo-claw-docs/reference/MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md`

---

## Deep Work Mode

```bash
milimo squad finals-mode --duration 2weeks --resume-date 2026-05-12
milimo squad finals-resume
```

**Per-claw behavior:**
| Claw | Still runs | Paused |
|---|---|---|
| Content | Nothing | Draft generation, publishing |
| Ops | Auto-responses to active clients | New client intake |
| Analytics | Passive data collection | New experiments, opportunity scoring |
| Finance | Invoice sends, payment monitoring | New project initiations |
| Build | Issue triage, error monitoring | New PRs, deploys, code generation |
| Assistant | Passive status monitoring | Cross-claw queries, active task routing |

**Auto-response (Ops Claw, AUTO mode):**
> "Hey [client_name], I'm heads-down on a focused sprint until [resume_date].
> Your project is on track — I'll be back in full swing then. 🙏"

**CLI:** `milimo/src/commands/finals-mode.ts`
**Handler:** `milimo-blueprint/orchestrator/solo_deep_work.py`

---

## Development Conventions

**Inference calls** — `data_type` is mandatory on every call. No exceptions.
All routes cloud during dev. `data_type` enables future NIM routing without
changing call sites.

**Filesystem** — `pathlib.Path` exclusively. Never `os.path`.

**YAML parsing** — `yaml.safe_load()` exclusively. Never `yaml.load()`.

**Log files** — Append-only JSONL. `fcntl` file locking for thread safety.
Never truncate or overwrite.

**Atomic writes** — All summary JSON files: write temp file first, then
`Path.rename()`. Never overwrite good data with a partial write.

**Shell commands (TypeScript)** — `child_process.spawn` with array args.
Never template literal shell strings — injection risk.

**Config** — `~/.milimo/config.json` is the single source of truth.
No separate `state.json`. All commands read from and write to one file.

**Cost guard** — Daily cloud token budget: 50,000. Alert at 80%.
Fallback strategy: `lighter_prompt` (reduce max_tokens 50%, trim enrichment
context). Never block a claw action — always fallback, never fail.

**Tests:**
- Python: `pytest`, full coverage per class and method
- TypeScript: `Jest`, mocked filesystem and subprocess
- Stripe: test mode only (`sk_test_*`) — no live keys ever
- GitHub: test repository only — never a live production repo
- **Phase A isolation tests must pass before any other MVR tests run**
- Phase A tests are in `tests/test_phase_a_isolation.py`, marked `phase_a`

---

## File Structure Reference

```
milimo-claw/
├── AGENTS.md                            THIS FILE — quick reference
│
├── milimo/                              TypeScript plugin
│   └── src/
│       ├── index.ts                     Plugin entry point
│       ├── cli.ts                       Command registration
│       ├── commands/
│       │   ├── onboard.ts
│       │   ├── init.ts
│       │   ├── squad.ts
│       │   ├── warroom.ts
│       │   ├── blueprint.ts
│       │   ├── finals-mode.ts           Deep Work Mode CLI
│       │   ├── action.ts
│       │   ├── health.ts
│       │   ├── payment.ts
│       │   ├── verify.ts
│       │   ├── badge.ts
│       │   └── slash.ts
│       ├── warroom/
│       │   ├── warroom-tui.ts           War Room TUI (blessed)
│       │   ├── approval.ts              HOLD/REVIEW/AUTO/VETO engine
│       │   ├── audit.ts
│       │   ├── evolution.ts             Evolution log display
│       │   ├── health-dashboard.ts
│       │   ├── health-collector.ts
│       │   ├── digest.ts                Morning/evening brief
│       │   ├── notifier.ts
│       │   ├── realtime-bridge.ts
│       │   └── rate-limiter.ts
│       ├── mesh/
│       │   ├── gateway-client.ts        OpenShell gateway connection
│       │   └── message-encryption.ts   AES-256-GCM message encryption
│       └── onboard/
│           ├── config.ts                Config persistence (~/.milimo/config.json)
│           ├── template.ts
│           ├── validate.ts
│           └── prompt.ts
│
├── milimo-blueprint/                    Python orchestrator
│   ├── blueprint.yaml
│   ├── orchestrator/
│   │   ├── contracts.py                 24 inter-claw message schemas
│   │   ├── mesh.py
│   │   ├── privacy_router.py
│   │   ├── evolution_cycle.py           5-stage evolution pipeline
│   │   ├── pattern_detector.py
│   │   ├── tool_proposal.py
│   │   ├── tool_builder.py
│   │   ├── tool_registry.py
│   │   ├── blueprint_manager.py
│   │   ├── marketplace_manager.py
│   │   ├── bridge_cli.py                TypeScript ↔ Python bridge
│   │   ├── solo_init.py
│   │   ├── solo_warroom.py
│   │   ├── solo_privacy.py              Cost guard + lighter_prompt fallback
│   │   ├── solo_deep_work.py
│   │   ├── solo_evolution.py            Staggered per-claw evolution scheduler
│   │   ├── solo_sandbox.py              Policy generator + mount helpers
│   │   ├── health_collector.py
│   │   ├── content/
│   │   │   ├── content_init.py
│   │   │   ├── content_generator.py
│   │   │   ├── brief_manager.py
│   │   │   ├── approval_handler.py
│   │   │   ├── platform_publisher.py
│   │   │   ├── performance_monitor.py
│   │   │   ├── publish_scheduler.py
│   │   │   ├── brand_voice.py
│   │   │   ├── content_scheduler.py
│   │   │   └── content_claw.py
│   │   ├── ops/
│   │   │   ├── ops_init.py
│   │   │   ├── intake_manager.py
│   │   │   ├── project_manager.py
│   │   │   ├── comms_manager.py
│   │   │   ├── scope_monitor.py
│   │   │   ├── health_scorer.py
│   │   │   ├── approval_handler.py
│   │   │   ├── signal_dispatcher.py
│   │   │   ├── ops_scheduler.py
│   │   │   └── ops_claw.py
│   │   ├── analytics/
│   │   │   ├── analytics_init.py
│   │   │   ├── signal_processor.py
│   │   │   ├── report_generator.py
│   │   │   ├── anomaly_detector.py
│   │   │   ├── opportunity_scorer.py
│   │   │   ├── baseline_manager.py
│   │   │   ├── query_handler.py         2-min SLA enforced + logged
│   │   │   ├── forward_projector.py
│   │   │   ├── signal_dispatcher.py
│   │   │   ├── analytics_scheduler.py
│   │   │   └── analytics_claw.py
│   │   ├── finance/
│   │   │   ├── finance_init.py
│   │   │   ├── pricing_engine.py
│   │   │   ├── invoice_manager.py
│   │   │   ├── payment_monitor.py
│   │   │   ├── payment_risk_scorer.py
│   │   │   ├── expense_tracker.py
│   │   │   ├── revenue_tracker.py
│   │   │   ├── approval_handler.py
│   │   │   ├── signal_dispatcher.py
│   │   │   ├── finance_scheduler.py
│   │   │   └── finance_claw.py
│   │   └── build/
│   │       ├── build_init.py
│   │       ├── issue_manager.py         5-min Analytics timeout
│   │       ├── code_generator.py
│   │       ├── pr_manager.py
│   │       ├── deploy_manager.py
│   │       ├── error_monitor.py
│   │       ├── cost_monitor.py
│   │       ├── dependency_auditor.py
│   │       ├── doc_maintainer.py
│   │       ├── approval_handler.py
│   │       ├── signal_dispatcher.py     10-min feature_brief_acknowledged
│   │       ├── build_scheduler.py
│ │ └── build_claw.py
│ │ ├── assistant/
│ │ │ ├── lucy.py Operator bridge · cross-claw coordinator
│ │ │ ├── assistant_init.py
│ │ │ ├── query_router.py
│ │ │ ├── response_relay.py
│ │ │ └── assistant_claw.py
│ ├── roles/ 6 role blueprints
│ ├── policies/ 6 sandbox policies
│   │                                    ALL must include weekly-intelligence.json mount
│   ├── templates/                       7 squad templates
│   └── tests/
│       ├── test_phase_a_isolation.py    ← RUN THIS FIRST (pytest -m phase_a)
│       ├── test_phase_b_warroom.py
│       ├── test_ops_mvr_integration.py
│       ├── test_finance_mvr_integration.py
│       ├── test_build_mvr_integration.py
│       └── test_analytics_integration.py
│
└── milimo-claw-docs/
    ├── reference/                       Spec documents (ground truth)
    │   ├── MILIMO_CLAW_CONTENT_CLAW_SPEC.md
    │   ├── MILIMO_CLAW_OPS_CLAW_SPEC.md
    │   ├── MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md
    │   ├── MILIMO_CLAW_FINANCE_CLAW_SPEC.md
│ ├── MILIMO_CLAW_BUILD_CLAW_SPEC.md
│ ├── MILIMO_CLAW_ASSISTANT_SYSTEM_PROMPT_TEMPLATE.md
│ └── MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md
    └── prompts/                         AI implementation prompts
        ├── CONTENT_CLAW_IMPLEMENTATION_PROMPT.md
        ├── OPS_CLAW_IMPLEMENTATION_PROMPT.md
        ├── ANALYTICS_CLAW_IMPLEMENTATION_PROMPT.md
        ├── FINANCE_CLAW_IMPLEMENTATION_PROMPT.md
├── BUILD_CLAW_IMPLEMENTATION_PROMPT.md
├── ASSISTANT_CLAW_IMPLEMENTATION_PROMPT.md
└── SOLO_TEMPLATE_V2_REMEDIATION_PROMPT.md
```

---

## Debugging Quick Reference

**The spec documents are the ground truth.** Code deviates from spec — code is wrong.

### Cross-claw failures (check these first)

| Symptom | Cause | Fix |
|---|---|---|
| `weekly-intelligence.json` unreadable by any claw | Missing shared mount in that claw's sandbox policy | Add entry to `policies/{role}-sandbox.yaml`, run `pytest -m phase_a` |
| `project_brief` sent before `pricing_response` | Rule 1 violated | Check `intake_manager.py` — verify pricing awaited |
| Invoice sent at Stage 1 REVIEW approve | Rule 2 violated — critical bug | Check `finance/approval_handler.py` |
| PR merged at REVIEW approve | Rule 3 violated — critical bug | Check `build/approval_handler.py` |
| Deploy triggered on PR merge (no HOLD) | Rule 3 violated — critical bug | Check `deploy_manager.stage_deployment()` wiring |
| `project_complete` sent before client confirms | Rule 4 violated | Check `project_manager.confirm_client_receipt()` |
| Evolution all claws same time | `solo-founder.yaml` uses `time:` not `schedule:` | Replace with per-claw `schedule:` block |
| HOLD items not above REVIEW items in queue | Priority sorting broken | Queue must sort HOLD first always |
| Morning brief not at 07:00 | DigestScheduler not initialized | Check `warroom-tui.ts` digest scheduling |
| Cost guard blocking claw actions | Fallback is hard stop not lighter_prompt | Set `never_block_claw_action: true` |

### Per-claw failures

| Claw | Symptom | Check |
|---|---|---|
| Content | Draft not in War Room | `draft_ready` message not sent |
| Content | Publishing without approval | Approval mode AUTO instead of REVIEW |
| Ops | Welcome sent without approval | REVIEW mode misconfigured |
| Ops | Deadline critical is REVIEW not HOLD | `check_all_deadlines()` — HOLD at ≤1 day |
| Ops | `feature_brief` never acknowledged | 10-min timer not in `build/signal_dispatcher.py` |
| Analytics | Query response > 2 minutes | SLA not measured in `query_handler.handle()` |
| Analytics | No mid-week opportunity dispatch | Confidence threshold check not in `opportunity_scorer` |
| Finance | `revenue_summary` has client names | Privacy leak — totals only |
| Finance | Overdue not firing | `payment_monitor` schedule not initialized |
| Finance | HOLD invoice not escalated after 48h | Staleness check missing in `finance_scheduler.py` |
| Build | Sprint plan blocked on Analytics | 5-min `ANALYTICS_WAIT_SECONDS` not wired in `issue_manager.py` |
| Build | PR auto-merges on REVIEW approve | Two-stage approval bypassed — critical bug |
| Build | Deploy auto-triggers on PR merge | Separate deploy HOLD missing in `deploy_manager.py` |
| Build | Changelog overwritten not appended | `doc_maintainer.update_changelog()` writes instead of appends |
| Assistant | Cross-claw query not dispatched | `query_router.py` not routing to correct claw |
| Assistant | Operator not receiving claw responses | `assistant_response` not routed to assistant in `contracts.py` |
| Assistant | Sandbox rebuild stuck in HOLD | HOLD not released via War Room |

---

*Milimo Claw · built on NVIDIA NemoClaw*
*"The milimo never stops. Work. Without working."*
