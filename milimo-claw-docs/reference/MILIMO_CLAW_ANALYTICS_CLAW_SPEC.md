# MILIMO CLAW — ANALYTICS CLAW FUNCTIONAL SPECIFICATION

> **NemoClaw Compliance Notice (2026-04-28)**
>
> This spec has been updated to comply with NVIDIA NemoClaw v0.0.28 and OpenShell v0.0.26 as documented at [docs.nvidia.com/nemoclaw/latest/](https://docs.nvidia.com/nemoclaw/latest/) and [docs.nvidia.com/openshell/latest/](https://docs.nvidia.com/openshell/latest/).
>
> **Key changes applied:**
>
> - **Filesystem paths migrated** from `/sandbox/<role>/` to `/sandbox/.openclaw-data/milimo/claws/<role>/` — NemoClaw's Landlock LSM makes `/sandbox/` root read-only; only `/sandbox/.openclaw-data/`, `/sandbox/.nemoclaw/`, and `/tmp/` are writable (see [Sandbox Hardening](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html)).
> - **Shared analytics report path** updated from `/sandbox/analytics/reports/` to `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` — same Landlock compliance reason.
> - **`/sandbox/.openclaw/`** is read-only — contains immutable gateway config (auth tokens, CORS); agents cannot modify it.
> - **`/sandbox/.openclaw/workspace/`** is the canonical workspace files location (SOUL.md, USER.md, AGENTS.md, MEMORY.md, etc.) — persisted via symlink into `.openclaw-data/`.
> - **`/sandbox/.local/bin/milimo` does NOT exist** — was referenced in old policy YAMLs; Milimo bridge CLI is at `python3 /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py`.
> - **Credentials** are stored in the OpenShell gateway store only — NOT in `~/.nemoclaw/credentials.json` (which is legacy, auto-migrated and deleted on `nemoclaw onboard`). See [Credential Storage](https://docs.nvidia.com/nemoclaw/latest/security/credential-storage.html).
> - **Network policy** uses `protocol: rest` with `enforcement` and `access`/`rules`/`deny_rules` for L7 HTTP inspection — see [OpenShell Policy Schema](https://docs.nvidia.com/openshell/latest/reference/policy-schema.html).
> - **GitHub is NOT in the baseline policy** — it's a preset only, applied via `nemoclaw <name> policy-add github` or during onboarding tier selection.
> - **`include_workdir: false`** in filesystem_policy — NemoClaw default; `/sandbox/` root is read-only.
> - **Policy tiers**: Restricted / Balanced (default) / Open — determine which presets are included at onboarding.
> - **`openshell policy set` REPLACES** the live policy (does NOT merge) — use `nemoclaw <name> policy-add` for non-destructive merging.
> - **Sandbox process** runs as `sandbox:sandbox` (UID 999), not root — `run_as_user: root` is rejected by OpenShell.
> - **`/sandbox/.openclaw/openclaw.json`** is read-only at runtime — `openclaw channels remove` cannot modify it from inside the sandbox; use `nemoclaw <name> channels remove` from the host.
>
> If this spec conflicts with the official NemoClaw/OpenShell docs, the official docs win. See the [Ground Truth Hierarchy](../../.agents/AGENTS.md) for resolution rules.

# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI assistant when you need it to understand
# exactly how the Analytics Claw is supposed to work — for debugging,
# feature implementation, testing, or documentation.
#
# DEVELOPMENT NOTE: This implementation is in active development and testing.
# All inference currently routes to cloud (the configured NEMOCLAW_MODEL via NVIDIA Cloud API)
# regardless of data sensitivity. The privacy routing rules documented here
# represent the production target architecture. Do not implement privacy
# routing enforcement during this phase — route everything to cloud.
# Log the data_type field on every inference call so routing can be enforced
# later without touching call sites.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug the **Analytics Claw** inside Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw. Read
this entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation deviates
from it, the implementation is wrong — not this spec.

---

## WHAT THE ANALYTICS CLAW IS

The Analytics Claw is the intelligence layer of a Milimo Claw squad. It
watches everything — content performance, client satisfaction signals,
revenue trends, delivery velocity, platform algorithm shifts, and
competitive opportunities — and synthesizes raw operational data into
actionable intelligence that every other claw consumes.

It does not take action in the world. It does not publish, communicate
with clients, write code, or move money. Its entire output is intelligence:
reports, signals, alerts, and answers to queries from other claws. It is
the claw that makes every other claw smarter.

The Analytics Claw is not a dashboard. It is an autonomous intelligence
analyst that runs continuously, detects what matters, and surfaces it to
the right place at the right time — without being asked.

---

## IDENTITY AND ISOLATION

**Sandbox name:** `analytics-claw`
**Plugin namespace:** `openclaw milimo analytics`
**Blueprint file:** `milimo-blueprint/roles/analytics-claw.yaml`
**Sandbox policy:** `milimo-blueprint/policies/analytics-sandbox.yaml`
**Filesystem mount:** `/sandbox/analytics`

The Analytics Claw has read-only visibility into aggregated data from
other claws — never raw client records or source code. It receives data
through typed inter-claw messages and writes its intelligence outputs
to a shared-read directory that all other claws can access.

This is the only claw whose primary output is designed to be read by
every other claw in the mesh.

---

## FILESYSTEM LAYOUT

Everything the Analytics Claw owns lives under `/sandbox/analytics`:

```
/sandbox/analytics/
├── reports/
│   ├── weekly-intelligence.json      # PRIMARY OUTPUT — read by all claws
│   ├── weekly-intelligence-archive/  # Previous weekly reports (90-day retention)
│   │   └── {YYYY-MM-DD}.json
│   ├── monthly-summary.json          # Monthly rollup
│   └── opportunity-scores.json       # Live opportunity scoring
│
├── signals/
│   ├── anomalies/                    # Detected performance anomalies
│   │   └── {signal_id}.json
│   ├── opportunities/                # Identified growth opportunities
│   │   └── {signal_id}.json
│   └── alerts/                       # Urgent signals requiring attention
│       └── {signal_id}.json
│
├── data/
│   ├── content-performance/          # Aggregated from Content Claw signals
│   │   └── {platform}/
│   │       └── {YYYY-MM}/
│   │           └── performance.jsonl
│   ├── client-health/               # Aggregated from Ops Claw signals
│   │   └── {client_id}/
│   │       └── health-history.jsonl
│   ├── revenue/                     # Aggregated from Finance Claw signals
│   │   └── weekly-revenue.jsonl
│   └── delivery-velocity/           # Aggregated from Build Claw signals
│       └── velocity.jsonl
│
├── baselines/
│   ├── content-baselines.json       # 30-day rolling baselines per platform
│   ├── revenue-baseline.json        # Revenue baseline and seasonality
│   └── delivery-baseline.json       # Delivery velocity baseline
│
├── tools/                           # Autonomously built evolution tools
│   ├── engagement-baseline-model/
│   ├── anomaly-detector/
│   ├── opportunity-scorer/
│   ├── retention-correlator/
│   ├── competitor-signal-tracker/
│   └── forward-projection-engine/
│
└── logs/
    ├── operational.log              # every action taken, timestamped
    ├── queries.log                  # all inter-claw queries received and answered
    └── signals.log                  # all signals detected and dispatched
```

**Shared-read output (readable by ALL claws):**
```
/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence.json
```
This is the only file in the entire Milimo Claw mesh that all claws
can read directly without a message contract. It is written by the
Analytics Claw every Sunday and is the primary intelligence feed
for the Content, Ops, Finance, Build, and Assistant Claws.

**What the Analytics Claw can read:**
- Everything under `/sandbox/analytics/`
- `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` (owns and writes this)

**What the Analytics Claw CANNOT read under any circumstances:**
- `/sandbox/clients/` — raw client contact data (Ops Claw only)
- `/sandbox/finance/` — raw financial records (Finance Claw only)
- `/sandbox/build/` — source code and secrets (Build Claw only)
- `/sandbox/content/` — draft content and brand assets (Content Claw only)
- `/sandbox/assistant/` — session data and context (Assistant Claw only)

The Assistant Claw (`/sandbox/assistant`) likewise cannot read the Analytics
Claw's primary mount or any other claw's primary mount — isolation is mutual.

The Analytics Claw only receives aggregated, anonymized data signals
from other claws via typed messages — never raw records.

---

## NETWORK EGRESS POLICY

The Analytics Claw has READ-ONLY network access. It cannot write to
any external platform. No exceptions.

**Approved read-only endpoints:**
```
api.twitter.com                  # read analytics (OAuth read-only scope)
api.instagram.com                # read insights (read-only scope)
api.linkedin.com                 # read analytics (read-only scope)
api.tiktok.com                   # read analytics (read-only scope)
api.google-analytics.com         # Google Analytics read access
trends.google.com                # trend signal data
api.semrush.com                  # competitor signal data (optional)
api.similarweb.com               # competitor traffic data (optional)
```

**Blocked — ALL write operations:**
```
No POST, PUT, PATCH, or DELETE to any endpoint.
Analytics Claw may only make GET requests.
This is enforced at the network namespace level — not by policy alone.
```

**Critical rule:** The Analytics Claw collects and synthesizes. It never
publishes, never communicates, never acts. If a proposed implementation
involves the Analytics Claw writing to any external service, it is wrong.

---

## INFERENCE ROUTING

**Development / testing phase:** All inference routes to cloud.
Log `data_type` on every inference call for future routing enforcement.

**Production target routes (reference only — not enforced during dev):**

| Data Type | Production Route | Reason |
|---|---|---|
| Public trend and market analysis | Cloud (NEMOCLAW_MODEL) | Public data, max reasoning quality |
| Internal performance synthesis | Local NIM | Squad's operational data is sensitive |
| Predictive model generation | Local NIM | Trained on proprietary squad data |
| Anomaly characterization | Local NIM | Contains operational intelligence |
| Competitor signal analysis | Cloud (NEMOCLAW_MODEL) | Public market data |
| Opportunity scoring | Local NIM | Based on private revenue and client data |
| Report narrative generation | Local NIM | Contains squad's full operational picture |

**Current implementation:** Route all to cloud. Log data_type always.

---

## WHAT THE ANALYTICS CLAW DOES AUTONOMOUSLY

All actions are logged to `/sandbox/analytics/logs/operational.log`
with ISO timestamp, action_type, entity_id, and outcome.

---

### WEEKLY INTELLIGENCE REPORT

**The single most important output of the Analytics Claw.**

Every Sunday at 02:00 (immediately before the Evolution Cycle runs at
the same time — report first, then evolution), the Analytics Claw
generates the weekly intelligence report.

**Report generation sequence:**
1. Aggregate all `performance_signal` messages received from Content Claw
   during the past 7 days
2. Aggregate all `client_health_signal` messages received from Ops Claw
3. Aggregate all `revenue_summary` messages received from Finance Claw
4. Aggregate all `shipping_summary` messages received from Build Claw
5. Pull external trend data from approved read-only endpoints
6. Generate anomaly detection pass against all baselines
7. Generate opportunity scoring pass
8. Synthesize narrative summary via inference
9. Write complete report to `/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence.json`
10. Archive previous report to `/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence-archive/{date}.json`

**Report schema:**
```json
{
  "generated_at": "ISO timestamp",
  "week_of": "YYYY-MM-DD",
  "squad_id": "milimoquantum",

  "content_performance": {
    "top_formats": [
      { "format": "tutorial", "avg_engagement": 0.087, "vs_baseline": "+41%" }
    ],
    "top_platforms": [ ... ],
    "top_publish_times": [ ... ],
    "worst_performing": [ ... ],
    "platform_algorithm_notes": "string — detected shifts this week"
  },

  "client_health": {
    "overall_score": 8.2,
    "at_risk_clients": [ { "client_id": "...", "score": 5.1, "risk_factor": "..." } ],
    "healthy_clients": [ ... ],
    "new_signals": [ ... ]
  },

  "revenue": {
    "week_total": 4240.00,
    "week_over_week_pct": 18.0,
    "invoices_paid": 3,
    "invoices_pending": 1,
    "pipeline_value": 12000.00,
    "anomalies": [ ... ]
  },

  "delivery": {
    "prs_merged": 12,
    "deploys": 3,
    "avg_pr_cycle_hours": 4.2,
    "open_issues": 8,
    "velocity_vs_baseline": "+15%"
  },

  "opportunities": [
    {
      "type": "content_format",
      "description": "Carousel posts on LinkedIn showing 3x engagement — squad not using this format",
      "confidence": 0.87,
      "recommended_action": "Test 2 carousel posts next week"
    }
  ],

  "anomalies": [
    {
      "type": "revenue_spike",
      "description": "Invoice volume 2.3x above 30-day baseline",
      "severity": "positive",
      "requires_attention": false
    }
  ],

  "forward_projections": {
    "next_week_revenue_estimate": 4800.00,
    "confidence_interval": [3900, 5700],
    "next_week_risk_flags": [ ... ]
  },

  "summary_narrative": "string — 3-4 sentence plain English summary"
}
```

---

### CONTINUOUS SIGNAL PROCESSING

Between weekly reports, the Analytics Claw processes incoming signals
in near-real-time and dispatches alerts when thresholds are crossed.

**Anomaly detection (triggered by every incoming signal):**
- Compare incoming data point against 30-day rolling baseline
- Thresholds: >2x baseline = positive anomaly, <0.5x baseline = negative anomaly
- If anomaly detected:
  - Write signal to `/sandbox/analytics/signals/anomalies/{signal_id}.json`
  - Dispatch appropriate alert message to relevant claw
  - Log to `/sandbox/analytics/logs/signals.log`

**Opportunity scoring (runs daily at 06:00):**
- Pull latest trend data from approved external endpoints
- Compare against squad's content and product portfolio
- Score opportunities on: potential impact, squad readiness, timing
- Update `/sandbox/.openclaw-data/milimo/claws/analytics/reports/opportunity-scores.json`
- If high-confidence opportunity (>0.85): dispatch immediately to
  relevant claw — do not wait for weekly report

**Baseline maintenance (runs weekly, Sunday 01:00 — before report):**
- Recalculate 30-day rolling baselines for all tracked metrics
- Update `/sandbox/analytics/baselines/` files
- Log baseline updates to operational.log

---

### ON-DEMAND QUERY HANDLING

Any claw can query the Analytics Claw via the `content_performance_query`
or `behavior_query` message types. The Analytics Claw must respond within
2 minutes.

**Query handling sequence:**
1. Receive query message via inter-sandbox gateway
2. Log query to `/sandbox/analytics/logs/queries.log`
3. Identify query type and required data sources
4. Aggregate relevant data from `/sandbox/analytics/data/`
5. Generate response via inference if narrative required
6. Send response message back to requesting claw
7. Log response to queries.log

**Response SLA:** 2 minutes maximum. If data unavailable, respond with
best available approximation and a `data_quality: "estimated"` flag.
Never timeout silently — always respond.

---

## INTER-CLAW COORDINATION

All communication via typed message contracts through OpenShell gateway.

### Messages the Analytics Claw RECEIVES:

| Message Type | From | When | Payload |
|---|---|---|---|
| `performance_signal` | Content Claw | After every published post | post_id, platform, engagement_data, publish_time, content_type, client_id |
| `client_health_signal` | Ops Claw | Weekly + on significant change | client_id, health_score, health_factors, recommended_action |
| `client_onboarded` | Ops Claw | New client fully onboarded | client_id, niche, project_type, estimated_value |
| `revenue_summary` | Finance Claw | Weekly revenue totals | week_total, invoices_paid, invoices_pending, week_over_week_pct |
| `shipping_summary` | Build Claw | Weekly engineering summary | prs_merged, deploys, issues_closed, velocity_delta |
| `content_performance_query` | Content Claw | Monday 06:00 + on demand | query, lookback_days, platform |
| `behavior_query` | Build Claw | Before sprint planning | query, feature_id, lookback_days |

### Messages the Analytics Claw SENDS:

| Message Type | To | When | Payload |
|---|---|---|---|
| `performance_intel` | Content Claw | Weekly + on high-confidence opportunity | top_formats, top_times, engagement_trends, audience_signals |
| `retention_signals` | Build Claw | Weekly + on churn anomaly | feature_adoption_rates, churn_correlation, recommended_features |
| `client_health_alert` | Ops Claw | When client health < 6.0 | client_id, health_score, risk_factors, recommended_action |
| `revenue_anomaly` | Finance Claw | When revenue metric crosses threshold | anomaly_type, current_value, baseline_value, severity |
| `content_performance_response` | Content Claw | In response to query | top_formats, top_times, performance_breakdown, data_quality |
| `behavior_query_response` | Build Claw | In response to query | feature_data, retention_correlation, recommendations, data_quality |

### Message handling rules:
- `performance_intel` goes to Content Claw weekly AND immediately when
  a high-confidence opportunity (>0.85) is detected mid-week
- `client_health_alert` fires immediately when health score drops below
  6.0 — does not wait for weekly cycle
- `revenue_anomaly` fires immediately when anomaly detected — does not
  wait for weekly report
- All query responses must arrive within 2 minutes
- Every sent message is logged to signals.log

---

## WAR ROOM INTERACTION

The Analytics Claw does not queue REVIEW or HOLD actions in the War Room.
Its outputs are either:

1. **AUTO actions** — intelligence delivered to War Room passively:
   - Weekly intelligence report published
   - Opportunity score updated
   - Baseline recalculated

2. **REVIEW alerts** — surfaced when the operator should be aware:
   - Client health below threshold
   - Revenue anomaly detected
   - High-confidence opportunity found
   - Delivery velocity dropping significantly

3. **Signals dispatched to other claws** — the other claw surfaces
   the relevant War Room action (e.g. Ops Claw gets client_health_alert
   and decides how to respond to the client)

**The Analytics Claw never surfaces HOLD actions.** It observes and
informs. It never blocks or requires an immediate operator decision.

**War Room card format for Analytics alerts:**

```
┌─────────────────────────────────────────────────────────┐
│ ✓ AUTO    ANALYTICS CLAW               Sunday 02:04     │
│                                                         │
│ Weekly intelligence report published                    │
│ Week of Mar 16 · 12 signals processed                   │
│ 2 opportunities · 1 anomaly · 0 alerts                  │
│                                                         │
│ [View Report]                                           │
└─────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────┐
│ 🟡 REVIEW   ANALYTICS CLAW             Tuesday 14:22    │
│                                                         │
│ High-confidence opportunity detected                    │
│ LinkedIn carousel posts: +3x engagement potential       │
│ Confidence: 91% · Squad not currently using format      │
│                                                         │
│ Dispatched to Content Claw                             │
│ [View Full Analysis]                                    │
└─────────────────────────────────────────────────────────┘
```

---

## THE SELF-EVOLUTION CYCLE

Runs every Sunday at 02:00, immediately after the weekly intelligence
report is generated. The report feeds the evolution cycle — the cycle
runs on fresh weekly data.

### What the Analytics Claw observes:

```
STAGE 1 — OBSERVE
  Read query history: which queries came from which claws, response quality
  Read anomaly detection history: what was caught, what was missed
  Read opportunity scores: which scored high, which were acted on
  Read forward projection accuracy: predicted vs actual outcomes
  Read baseline drift: which baselines are shifting and how fast
```

### Patterns the Analytics Claw identifies:

- Which metric combinations best predict client churn?
- Which content format signals appear before virality, not after?
- Which delivery velocity patterns predict missed deadlines?
- Which revenue patterns predict invoice non-payment?
- Which query types arrive repeatedly — indicating a gap in proactive reporting?

### Evolution tools that emerge over time:

| Week | Tool | What It Does | Target Metric |
|---|---|---|---|
| 2 | Engagement baseline model | Establishes rolling baselines per platform and content type | Anomaly detection accuracy |
| 5 | Anomaly detector v2 | Platform-specific anomaly thresholds calibrated to squad's audience | False positive rate |
| 9 | Opportunity scorer v2 | Scores opportunities by squad-specific readiness, not generic potential | Opportunity-to-action conversion rate |
| 14 | Retention correlator | Identifies which content types and product features correlate with client retention | Client retention prediction accuracy |
| 22 | Competitor signal tracker | Monitors squad's competitive set for strategy shifts worth responding to | Competitive response timeliness |
| 30 | Forward projection engine v2 | Generates 4-week projections with confidence intervals based on squad's historical patterns | Forecast accuracy (MAPE) |

### Minimum thresholds before first evolution:
- 3 weeks of `performance_signal` data from Content Claw
- At least 1 `client_health_signal` from Ops Claw
- At least 1 `revenue_summary` from Finance Claw
- 2 complete weeks of operational.log data

### Critical evolution constraint:
No evolved tool can send messages to external services, write to other
claws' filesystems, or exceed the Analytics Claw's read-only network
access. Evolution cannot grant write access to any endpoint.

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE

**Day 1–7 (baseline establishment):**
- Analytics Claw receives first performance_signal from Content Claw
- Begins building baseline data in `/sandbox/analytics/data/`
- No weekly report yet — insufficient data
- Responds to any direct queries with "insufficient data — {n} days
  of data collected, {needed} days needed for reliable analysis"
- Operator sees Analytics Claw status: "Collecting — 7/21 days to
  first report"

**Week 3 (first weekly report):**
- First weekly intelligence report generated and published
- Other claws read it from the shared filesystem mount
- Content Claw incorporates top formats into Monday planning
- Operator sees report summary in War Room morning digest
- Report is simple — limited data, modest insights

**Month 2 (compound intelligence):**
- Engagement baseline model active — anomaly detection live
- Opportunity scorer calibrated to squad's platform mix
- First meaningful `performance_intel` sent to Content Claw
  changes what it generates the following week
- First `client_health_alert` sent to Ops Claw proactively

**Month 6+ (mature intelligence layer):**
- Retention correlator active — Build Claw receives weekly signals
  that directly inform sprint prioritization
- Forward projection engine active — 4-week revenue estimates
  appear in War Room with confidence intervals
- Opportunity detection fires mid-week for time-sensitive signals
- Every other claw is measurably better because of what Analytics
  Claw tells them each week

---

## WHAT FAILURE LOOKS LIKE (DEBUGGING REFERENCE)

| Symptom | Likely Cause |
|---|---|
| Weekly report not generated | Evolution scheduler not initialized, or report generator erroring silently |
| weekly-intelligence.json not readable by other claws | Shared filesystem mount not configured — check analytics-sandbox.yaml |
| performance_signal messages not being stored | Data ingestion handler not wired to incoming message queue |
| Anomaly detection never fires | Baselines not calculated yet — check baselines/ directory for files |
| Query response taking > 2 minutes | Data aggregation too slow — check data/ directory size and indexing |
| performance_intel not sent to Content Claw | Outbound message handler not connected to report generation |
| client_health_alert not firing below 6.0 | Health threshold check not running continuously — check signal processor |
| revenue_anomaly not firing | Finance Claw not sending revenue_summary — check Finance Claw mesh config |
| Baselines showing 0 for all metrics | No performance_signal data received — check Content Claw signal sending |
| Forward projections wildly inaccurate | Insufficient historical data — projections need 8+ weeks to calibrate |
| Opportunity scores always 0 | Trend data endpoint blocked — check egress policy for trends.google.com |
| Competitor tracker not detecting signals | Competitor URLs not configured — requires setup in analytics-claw.yaml |

---

## DEVELOPMENT AND TESTING NOTES

**Current phase:** All inference routes to cloud. Log data_type on every call.

**Most important thing to test first:** The shared filesystem mount.
The weekly-intelligence.json file must be readable by ALL claws. Before
building any intelligence generation, verify that:
- Content Claw can read `/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence.json`
- Ops Claw can read the same path
- Finance Claw can read the same path
- Build Claw can read the same path
- Assistant Claw can read the same path
If any claw cannot read the file, the Analytics Claw's primary output
channel is broken. Fix the mount configuration before anything else.

**Minimum viable first run sequence:**
1. Inject a mock `performance_signal` from Content Claw
2. Confirm data written to `/sandbox/analytics/data/content-performance/`
3. Inject a mock `content_performance_query` from Content Claw
4. Confirm response sent within 2 minutes with best available data
5. Inject 7 days of mock performance_signal messages
6. Trigger manual report generation (bypass Sunday schedule for testing)
7. Confirm weekly-intelligence.json written and well-formed
8. Confirm Content Claw can read the file from its sandbox
9. Confirm Ops Claw can read the file from its sandbox
10. Inject a mock `client_health_signal` with score 5.0 (below threshold)
11. Confirm `client_health_alert` sent to Ops Claw immediately

All 11 steps must pass before scheduled autonomy is enabled.

---

## FILES TO BUILD

```
orchestrator/analytics/analytics_init.py       — Filesystem structure init
orchestrator/analytics/signal_processor.py     — Inbound signal ingestion and storage
orchestrator/analytics/report_generator.py     — Weekly intelligence report generation
orchestrator/analytics/anomaly_detector.py     — Continuous anomaly detection
orchestrator/analytics/opportunity_scorer.py   — Opportunity identification and scoring
orchestrator/analytics/baseline_manager.py     — Rolling baseline calculation and maintenance
orchestrator/analytics/query_handler.py        — On-demand query processing and response
orchestrator/analytics/forward_projector.py    — Forward projection engine
orchestrator/analytics/analytics_scheduler.py  — Scheduled autonomous actions
milimo-blueprint/roles/analytics-claw.yaml     — Role blueprint
milimo-blueprint/policies/analytics-sandbox.yaml — Sandbox policy
```

---

## SPEC EDGE CASES

**What if a signal arrives with invalid or missing data?**
Log the malformed signal to operational.log with error details.
Do not crash. Do not store malformed data. Send no response if the
signal requires none. If a response is expected (query), respond with:
`{ "data_quality": "error", "reason": "malformed payload", "data": null }`

**What if the Content Claw sends 100 performance_signals in one day?**
Process and store all of them. No rate limiting on inbound signals.
Aggregate efficiently — do not hold them in memory. Write each to disk
as it arrives. The weekly report reads from disk, not from memory.

**What if a claw queries for data that doesn't exist yet?**
Always respond. Never timeout. Return:
`{ "data_quality": "insufficient", "days_collected": N, "days_needed": M, "data": null }`
The requesting claw can handle the insufficiency in its own logic.

**What if two claws query simultaneously?**
Handle concurrently. Each query is independent. File reads are safe
for concurrent access. If inference is needed for both responses,
queue the inference calls sequentially — do not make parallel inference
calls that could hit rate limits.

**What if the weekly report generation fails mid-way?**
Write a partial report to a temp file first. Only atomically replace
`weekly-intelligence.json` on successful completion. If generation fails,
leave the previous week's report in place and log the failure. Surface
a REVIEW alert in the War Room: "Weekly report generation failed —
previous report from {date} still active." Never overwrite a good report
with a failed one.

**What if external trend APIs are rate-limited or unavailable?**
Generate the report without external data. Mark affected sections with
`"data_quality": "internal_only"`. The internal signal data (from other
claws) is always available and is the primary intelligence source.
External trend data is supplementary — the report must never fail
because an external API is unavailable.

**What if a high-confidence opportunity is detected on a Friday?**
Dispatch `performance_intel` to Content Claw immediately — do not wait
for Sunday. Content Claw will queue a REVIEW in the War Room for the
operator. Time-sensitive opportunities must not wait for the weekly cycle.
Threshold for immediate dispatch: opportunity confidence > 0.85.

---

*This specification is the ground truth for the Analytics Claw.
If behavior in the codebase deviates from this document, the code is wrong.*

*Development note: All inference routes to cloud during testing.
Log data_type on every inference call. The shared filesystem mount
for weekly-intelligence.json must be the first thing verified.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
