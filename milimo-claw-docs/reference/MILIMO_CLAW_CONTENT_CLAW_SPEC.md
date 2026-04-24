# MILIMO CLAW — CONTENT CLAW FUNCTIONAL SPECIFICATION
# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI assistant when you need it to understand
# exactly how the Content Claw is supposed to work — for debugging,
# feature implementation, testing, or documentation.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug the **Content Claw** inside Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw. Read
this entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation deviates
from it, the implementation is wrong — not this spec.

---

## WHAT THE CONTENT CLAW IS

The Content Claw is the creative department of a Milimo Claw squad. It runs
24/7 inside an isolated NemoClaw sandbox, autonomously generating all
creative output — social posts, long-form copy, email campaigns, pitch
decks, proposals, content calendars, and brand voice documentation — for
the squad's clients and the squad's own presence.

It does not wait to be prompted. It observes what performed well, it studies
what the squad approved, it listens to signals from the Analytics Claw, and
it gets measurably better at its job every week — without anyone telling it
to improve.

The Content Claw is not an AI writing assistant. It is an autonomous
creative operator with a memory, a style, and a track record.

---

## IDENTITY AND ISOLATION

**Sandbox name:** `content-claw`
**Plugin namespace:** `openclaw milimo content`
**Blueprint file:** `milimo-blueprint/roles/content-claw.yaml`
**Sandbox policy:** `milimo-blueprint/policies/content-claw.yaml`
**Filesystem mount:** `/sandbox/content`

The Content Claw exists entirely within its sandbox. It cannot read files
outside `/sandbox/content` unless they are explicitly mounted as approved
read-only sources. It cannot write to any other claw's filesystem. It
cannot reach any network endpoint not in its egress allowlist.

These are not software guardrails. They are kernel-level Landlock
filesystem restrictions and network namespace isolation enforced by
NVIDIA OpenShell. The Content Claw cannot circumvent them regardless
of what instructions it receives.

---

## FILESYSTEM LAYOUT

Everything the Content Claw owns lives under `/sandbox/content`:

```
/sandbox/content/
├── brand/
│   ├── style-guides/           # brand voice docs, tone references
│   ├── assets/                 # approved images, logos, templates
│   └── voice-profiles/         # per-client voice adapter models
│
├── drafts/
│   ├── pending/                # drafts awaiting operator approval
│   ├── approved/               # approved drafts ready to schedule
│   ├── rejected/               # rejected drafts (kept for learning)
│   └── published/              # post-publication archive
│
├── briefs/
│   ├── active/                 # current project briefs from Ops Claw
│   └── completed/              # closed project brief archive
│
├── calendar/
│   ├── scheduled/              # approved content scheduled for publish
│   └── published/              # publish confirmation records
│
├── intelligence/
│   └── analytics-feed/         # read-only mount of Analytics weekly report
│       └── weekly-intelligence.json
│
├── tools/                      # autonomously built evolution tools
│   ├── style-descriptor/
│   ├── tone-classifier/
│   ├── approval-predictor/
│   ├── timing-optimizer/
│   ├── ab-variant-engine/
│   ├── platform-calibrator/
│   ├── client-voice-adapter/
│   └── trend-injector/
│
└── logs/
    ├── operational.log         # every action taken, timestamped
    ├── approvals.log           # operator approve/edit/reject decisions
    └── performance.log         # post-publication engagement data
```

**What the Content Claw can read:**
- Everything under `/sandbox/content/`
- `/sandbox/analytics/reports/weekly-intelligence.json` (read-only mount)

**What the Content Claw cannot read under any circumstances:**
- `/sandbox/clients/` — client contact data (Ops Claw only)
- `/sandbox/finance/` — financial records (Finance Claw only)
- `/sandbox/build/` — source code and secrets (Build Claw only)
- `/sandbox/assistant/` — session data and context (Assistant Claw only)
- Any path outside the above

The Assistant Claw (`/sandbox/assistant`) likewise cannot read the Content
Claw's primary mount or any other claw's primary mount — isolation is mutual.

---

## NETWORK EGRESS POLICY

The Content Claw can only reach the following external endpoints.
All other outbound connections are blocked at the network namespace level.

**Approved publishing endpoints (write access):**
```
api.twitter.com          # post scheduling and publishing
graph.facebook.com       # Facebook and Instagram publishing
api.instagram.com        # Instagram direct API
api.linkedin.com         # LinkedIn post publishing
api.tiktok.com           # TikTok content publishing
api.buffer.com           # optional scheduling layer
```

**Approved read-only endpoints:**
```
unsplash.com             # stock image assets
api.pexels.com           # stock video and image assets
trends.google.com        # trend signal data
api.buzzsumo.com         # content performance benchmarks
```

**Blocked (representative examples — all others blocked too):**
```
api.stripe.com           # no financial access
api.gmail.com            # no client communications
api.github.com           # no code repositories
Any IP not in allowlist  # strict default-deny egress
```

**Critical rule:** The Content Claw can publish to platforms but cannot
read DMs, private messages, or follower data. Publishing is outbound only.
The egress policy has no inbound read permissions for any social platform.

---

## INFERENCE ROUTING

The Content Claw never decides which inference backend to use. Every
model call is intercepted by the Privacy Router, which routes based on
data sensitivity.

| Data Type | Route | Reason |
|---|---|---|
| Public-facing drafts (final) | Cloud (NEMOCLAW_MODEL) | Quality matters — clients and audiences see this |
| Client proposals and pitches | Cloud (NEMOCLAW_MODEL) | High-stakes, client-facing |
| Internal ideation and brainstorming | Local NIM | Private creative process — stays on device |
| Draft iterations and revisions | Local NIM | Intermediate work — not client-facing |
| Trend research queries | Cloud (NEMOCLAW_MODEL) | Public data, speed and quality preferred |
| Analytics report synthesis | Local NIM | Operational data is proprietary |
| Style calibration (voice adapter) | Local NIM | Trained on client data — never cloud |
| A/B variant generation | Cloud (NEMOCLAW_MODEL) | Final variants — quality matters |

The Content Claw does not know which backend was used. It submits
inference requests and receives responses. The Privacy Router handles
routing transparently.

---

## WHAT THE CONTENT CLAW DOES AUTONOMOUSLY

The following actions run without operator input, subject to the
configured approval thresholds. Everything the Content Claw does
is logged to `/sandbox/content/logs/operational.log`.

### Daily Autonomous Actions

**Morning content planning (06:00 daily):**
1. Queries Analytics Claw via inter-sandbox message:
   `content_performance_query` — "what content types performed best
   in the last 7 days?"
2. Reads current project briefs from `/sandbox/content/briefs/active/`
3. Reads the Analytics weekly intelligence report if available
4. Generates a daily content plan: which platforms, which formats,
   which clients, estimated publish times
5. Begins draft generation based on the plan

**Draft generation (continuous):**
1. Generates raw draft using Nemotron (cloud for finals, local for iterations)
2. Applies all active evolution tools in sequence:
   - Tone classifier: categorize by emotional register
   - Platform calibrator: adjust format, length, register per platform
   - Approval predictor: estimate operator approval probability
   - Client voice adapter: rewrite in client's brand voice if applicable
   - Timing optimizer: assign optimal publish time from historical data
3. If A/B engine is active: generate two variants automatically
4. Write processed draft to `/sandbox/content/drafts/pending/`
5. Queue draft in War Room: `REVIEW` mode action
6. Operator reviews, approves, edits, or rejects

**Post-publication monitoring:**
1. After content publishes, Content Claw polls approved analytics
   endpoints for engagement data (likes, shares, reach, click-through)
2. Writes performance record to `/sandbox/content/logs/performance.log`
3. Sends `performance_signal` message to Analytics Claw with results
4. If a post significantly outperforms or underperforms baseline,
   flags the anomaly in the War Room evolution log

**Weekly analytics query (Monday 06:00):**
Before generating the week's first drafts, sends a structured query
to Analytics Claw: "top 3 content patterns from last week."
Analytics Claw responds with a ranked performance summary.
Content Claw incorporates the top patterns into the week's drafts.

---

## INTER-CLAW COORDINATION

The Content Claw communicates exclusively through typed message contracts
via the OpenShell inter-sandbox gateway. It cannot communicate with other
claws through shared files, shared memory, or any direct API call.

### Messages the Content Claw RECEIVES:

| Message Type | From | When | Payload |
|---|---|---|---|
| `project_brief` | Ops Claw | New client project opened | client_id, project_id, brief_text, deadline, tone_requirements, platform_targets |
| `performance_intel` | Analytics Claw | Weekly intelligence report ready | top_formats, top_times, engagement_trends, audience_signals |
| `client_health_signal` | Analytics Claw | Client satisfaction drops | client_id, health_score, recommended_action |
| `revision_request` | Ops Claw | Client requests changes to delivered content | project_id, draft_id, revision_notes, deadline |

### Messages the Content Claw SENDS:

| Message Type | To | When | Payload |
|---|---|---|---|
| `draft_ready` | War Room | Any draft ready for operator review | draft_id, platform, client_id (if applicable), approval_probability, variants_count |
| `content_performance_query` | Analytics Claw | Weekly Monday 06:00 | query: "top_performing_formats", lookback_days: 7 |
| `performance_signal` | Analytics Claw | After every published piece | post_id, platform, engagement_data, publish_time, content_type |
| `brief_acknowledged` | Ops Claw | Within 5 minutes of receiving project_brief | project_id, estimated_first_draft_time |
| `deliverable_complete` | Ops Claw | When all deliverables for a project are approved and published | project_id, published_urls, performance_baseline |

### Message handling rules:
- Every received `project_brief` must get a `brief_acknowledged`
  response within 5 minutes — even if no draft is ready yet
- `draft_ready` must be sent before any draft appears in the War Room
  queue — the War Room reads from the message, not the filesystem
- `performance_signal` must be sent within 1 hour of publish confirmation
- All messages include a `timestamp` and `message_id` field
- The gateway logs every message — nothing is untracked

---

## WAR ROOM APPROVAL FLOW

No content reaches any external platform without explicit operator approval.
The approval flow is the contract between the Content Claw and the operator.

### Approval modes for Content Claw actions:

| Action | Mode | Behavior |
|---|---|---|
| Social post draft | REVIEW | Draft queued, operator approves before scheduling |
| Client proposal draft | REVIEW | Always surfaced — never auto-approved |
| Email campaign draft | REVIEW | Operator sees and approves before any send |
| Brand asset usage | AUTO | Logged, visible in morning digest |
| Content calendar update | AUTO | Logged, operator can override anytime |
| A/B test variant | REVIEW | Both variants shown side-by-side for selection |
| Trend-reactive post | REVIEW | Flagged as trend-triggered — operator confirms relevance |

### What the operator sees in War Room for a content action:

```
┌─────────────────────────────────────────────────────────┐
│ 🟡 REVIEW   CONTENT CLAW                    2 mins ago  │
│                                                         │
│ Draft ready: LinkedIn post for @NovaBrand               │
│ Platform: LinkedIn  ·  Tone: Educational                │
│ Approval probability: 87%  ·  Timing: Thu 8:12pm        │
│                                                         │
│ [View Draft]  [APPROVE]  [EDIT]  [BLOCK]               │
│                                                         │
│ Variant B also available  ·  [Compare A/B]             │
└─────────────────────────────────────────────────────────┘
```

### What happens after operator decision:

**APPROVE:**
- Draft moves from `/sandbox/content/drafts/pending/` to `approved/`
- If scheduling is configured: added to `/sandbox/content/calendar/scheduled/`
- Content Claw publishes at the optimized time via approved platform API
- After publish: `performance_signal` sent to Analytics Claw
- Approval logged to `/sandbox/content/logs/approvals.log`

**EDIT:**
- Operator edits inline in War Room
- Edited version saved as new draft — original preserved for learning
- Content Claw applies the edit as a training signal for its style tools
- Draft queued for re-review if significant changes were made

**BLOCK:**
- Draft moved to `/sandbox/content/drafts/rejected/`
- Block reason logged (if provided)
- Content Claw treats the block as a negative training signal
- Rejection logged — Evolution Cycle uses rejections to build better
  approval prediction and style calibration tools

---

## THE SELF-EVOLUTION CYCLE

Every Sunday at 02:00, the Content Claw runs its Evolution Cycle.
This is the process by which it gets measurably better over time —
autonomously, without prompting, without reconfiguration.

### The 5-Stage Cycle:

```
STAGE 1 — OBSERVE
  Read the week's approval log: every draft, every decision, every edit
  Read the performance log: every post, every engagement outcome
  Read the Analytics Claw intel feed: audience trends, platform signals
  Read rejected drafts: what consistently fails and why

STAGE 2 — IDENTIFY
  Surface recurring patterns:
    - Which content types get approved vs rejected most often?
    - Which editing patterns repeat? (operator always changes X to Y)
    - Which publish times correlate with highest engagement?
    - Which client briefs produce the most revision cycles?
    - What format patterns correlate with platform algorithm favor?

STAGE 3 — PROPOSE
  Nominate one new tool to address the strongest identified pattern.
  Example proposals:
    - "37% of Tuesday drafts were edited for tone — build a tone calibrator"
    - "Educational posts get 2x engagement — build a format detector"
    - "Thursday 8pm posts outperform others by 34% — build a timing optimizer"
  One tool proposed per cycle. Quality over quantity.

STAGE 4 — BUILD & TEST
  Build the proposed tool as a Python module inside the sandbox.
  Inference used for generation routes to Local NIM (source code is
  proprietary — PrivacyPolicyViolationError if cloud routing attempted).
  Test against 4 weeks of historical operational data.
  Must outperform current baseline by minimum 5% on target metric.
  Failed tools are discarded — never deployed.
  Passed tools are staged for deployment.

STAGE 5 — DEPLOY
  Tool activates in the Content Claw's live toolkit.
  Blueprint is versioned: new tool appears in blueprint snapshot.
  War Room evolution log entry is written:
    - Tool name and description
    - The pattern that triggered it
    - Performance delta vs baseline (e.g. "approval rate: 63% → 81%")
  Operator can disable the tool at any time from War Room.
```

### Critical evolution constraint:
No tool built by the Evolution Cycle can access data outside the Content
Claw's existing permissions. A proposed tool that would require reading
`/sandbox/clients` is rejected at Stage 4 — the Landlock policy makes
this architecturally impossible, not just policy-prohibited.

### Minimum thresholds before first evolution:
- 10 approved posts (enough signal to detect style patterns)
- 3 rejected drafts (enough negative signal for calibration)
- 1 complete week of performance data (enough for timing analysis)

If thresholds are not met, the cycle logs "insufficient data" and
tries again next Sunday. It never evolves prematurely on thin signal.

### Evolution timeline — what emerges over time:

| Week | Tool | What It Does | Target Metric |
|---|---|---|---|
| 2 | Style descriptor | Characterizes squad's brand voice from approved posts | Style consistency score |
| 4 | Tone classifier | Auto-categorizes drafts: hype / educational / soft sell / community / humor | Approval rate by tone |
| 7 | Approval predictor | Estimates operator approval probability before surfacing — reduces War Room noise | War Room queue efficiency |
| 10 | Platform calibrator | Adjusts format, length, register automatically per platform | Platform-specific engagement rate |
| 14 | Timing optimizer | Identifies audience-specific peak windows — not generic advice, actual data | Engagement rate by publish time |
| 18 | A/B variant engine | Generates two variants per post, tracks winner, folds patterns forward | Overall engagement uplift |
| 24 | Client voice adapter | Writes in each client's brand voice without re-prompting | Client revision request rate |
| 32 | Trend injector | Identifies rising content formats before saturation — not after | Content relevance score |

By week 32 — 8 months — the Content Claw has 8 specialized tools
trained entirely on this squad's operational history. No competing tool
has seen this data. No generic AI produces this output. The moat is
deep and entirely non-replicable.

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE

If the Content Claw is functioning as designed, the operator experiences
the following:

**Day 1–7 (baseline):**
- Content Claw generates basic drafts using Nemotron with style instructions
- Operator spends 20–30 minutes per day in War Room reviewing drafts
- Many edits required — the claw doesn't know the brand voice yet
- Every approval and edit is training signal for the Evolution Cycle

**Week 3–4 (first tools emerge):**
- Style descriptor active — drafts arrive pre-calibrated to brand voice
- Tone classifier active — each draft labeled by emotional register
- Operator review time drops to 15–20 minutes per day
- Fewer tone-related edits required

**Month 2–3 (compound tools):**
- Approval predictor active — low-probability drafts are refined before
  surfacing, reducing War Room noise
- Platform calibrator active — LinkedIn drafts arrive in long-form,
  Twitter drafts arrive crisp, TikTok scripts arrive punchy
- Timing optimizer active — content auto-scheduled for audience-specific
  peak windows without operator input
- Operator review time drops to 10–15 minutes per day

**Month 6+ (mature operation):**
- A/B variant engine active — every post ships with two tested variants,
  operator selects winner
- Client voice adapter active — @NovaBrand drafts sound like NovaBrand,
  @PulseMedia drafts sound like PulseMedia, without re-prompting
- Operator review time: 10 minutes per day
- Rejection rate: under 10% (vs ~35% in week 1)
- Client revision requests: rare

---

## WHAT FAILURE LOOKS LIKE (DEBUGGING REFERENCE)

| Symptom | Likely Cause |
|---|---|
| Drafts not appearing in War Room | draft_ready message not sent — check message contract validation |
| Content publishing without approval | Approval mode misconfigured — REVIEW should block until operator acts |
| Platform calibrator not adjusting format | Tool not active — check tool registry for deployment status |
| Client voice adapter writing wrong voice | Voice profile not loaded — check /sandbox/content/brand/voice-profiles/ |
| Evolution cycle not running | Minimum thresholds not met — check operational.log for data counts |
| Analytics intel not incorporated | analytics-feed mount not connected — check filesystem mount config |
| Timing optimizer using generic times | Historical performance data insufficient — check performance.log |
| Trend injector acting on stale trends | Trend API endpoint blocked — check egress policy allowlist |
| A/B variants not generating | A/B engine not yet evolved (requires week 18+) or tool disabled |
| brief_acknowledged not sent | Ops Claw briefs not reaching Content Claw — check message contracts |
| performance_signal not sent | Post-publish monitoring not wired — check calendar/published/ handler |
| Privacy router routing style work to cloud | Routing rule misconfigured — voice adapter must use Local NIM |

---

## FILES THAT IMPLEMENT THIS BEHAVIOR

### Blueprint and Policy
| File | Purpose |
|---|---|
| `milimo-blueprint/roles/content-claw.yaml` | Claw definition: filesystem mounts, egress policy, inference routing, inter-claw message policy |
| `milimo-blueprint/policies/content-claw.yaml` | OpenShell sandbox policy: Landlock paths, seccomp filters, network namespace rules |

### Python Orchestrator
| File | Purpose |
|---|---|
| `orchestrator/evolution_cycle.py` | 5-stage evolution cycle — shared across all claws |
| `orchestrator/pattern_detector.py` | Stage 2 pattern identification from operational logs |
| `orchestrator/tool_proposal.py` | Stage 3 tool nomination with permission validation |
| `orchestrator/tool_builder.py` | Stage 4 build and backtest in sandbox isolation |
| `orchestrator/tool_registry.py` | Deployed tool inventory, enable/disable, provenance |
| `orchestrator/privacy_router.py` | Inference routing by data sensitivity |
| `orchestrator/contracts.py` | All inter-claw message type schemas |
| `orchestrator/mesh.py` | Message routing and gateway coordination |

### TypeScript Plugin
| File | Purpose |
|---|---|
| `milimo/src/warroom/approval.ts` | REVIEW/HOLD/AUTO/VETO logic for content actions |
| `milimo/src/warroom/warroom-tui.ts` | War Room rendering — content draft cards, A/B comparison view |
| `milimo/src/warroom/evolution.ts` | Evolution log display — new tool announcements |

### Configuration
| File | Purpose |
|---|---|
| `milimo-blueprint/templates/solo-founder.yaml` | Operator policy for content claw in solo mode |
| `~/.milimo/config.json` | Live squad config — claw role assignments |

---

## SPEC EDGE CASES

**What if the operator never approves anything?**
The Content Claw keeps generating and queuing. The War Room queue grows.
The Evolution Cycle still runs but produces weak tools — approval rate
signal is 0%, so the approval predictor cannot calibrate. The claw will
correctly identify "low approval signal" as a pattern and may propose
a tool to generate more conservative drafts. It does not stop working.

**What if a client brief arrives mid-week with a tight deadline?**
The Ops Claw sends a `project_brief` message. The Content Claw must
acknowledge with `brief_acknowledged` within 5 minutes and include
an estimated first draft time. It deprioritizes other work to generate
the urgent brief first. Deadline is visible in the War Room queue card.

**What if the Analytics Claw is offline or unavailable?**
Content Claw falls back to its most recent cached intelligence report.
If no cache exists, it proceeds with baseline generation without
performance signal. It logs the unavailability but does not fail.
It retries the analytics query on the next scheduled cycle.

**What if the operator rejects the same draft multiple times?**
Each rejection is logged with reason (if provided). After 3 rejections
of the same brief type, the Content Claw flags the brief in the War
Room: "Repeated rejections detected — brief may need clarification."
It also uses the rejection pattern as a strong negative training signal
in the next Evolution Cycle.

**What if a platform API is unavailable at publish time?**
The scheduled publish is held. Content Claw retries every 15 minutes
for 2 hours. If still unavailable after 2 hours, it escalates to the
War Room: "Publish failed — @platform unavailable. Approve retry or
reschedule?" The content is never silently dropped.

---

*This specification is the ground truth for the Content Claw.
If behavior in the codebase deviates from this document, the code is wrong.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
