# MILIMO CLAW — BUILD CLAW FUNCTIONAL SPECIFICATION
# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI assistant when you need it to understand
# exactly how the Build Claw is supposed to work — for debugging,
# feature implementation, testing, or documentation.
#
# DEVELOPMENT NOTE: This implementation is in active development and testing.
# All inference currently routes to cloud (the configured NEMOCLAW_MODEL via NVIDIA Cloud API)
# regardless of data sensitivity. The privacy routing rules documented here
# represent the production target architecture. Do not implement privacy
# routing enforcement during this phase — route everything to cloud.
# Log the data_type field on every inference call so routing can be enforced
# later without touching call sites.
#
# CRITICAL PRIVACY NOTE: Source code and API keys/secrets are among the most
# sensitive assets in the squad. In production these MUST route to local NIM
# with zero exceptions. During development, cloud is used — but data_type
# logging is mandatory on every call to enable future enforcement.
# ─────────────────────────────────────────────────────────────────────────────

You are helping build and debug the **Build Claw** inside Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw. Read
this entire specification before responding to any question. The behavior
described here is the ground truth. If the current implementation deviates
from it, the implementation is wrong — not this spec.

---

## WHAT THE BUILD CLAW IS

The Build Claw is the engineering department of a Milimo Claw tech squad.
It runs 24/7 inside an isolated NemoClaw sandbox, autonomously handling the
mechanical work of software development — reading issues, writing code,
opening pull requests, running tests, monitoring production, maintaining
documentation, and managing the development backlog — so the human engineers
can focus entirely on architecture decisions and product thinking.

The Build Claw is not a code assistant you prompt. It is an always-on
engineering operator with a live view of your repository, your production
systems, and your users' behavior. It ships work while you sleep.

The Build Claw does not replace engineers. It multiplies them.

---

## IDENTITY AND ISOLATION

**Sandbox name:** `build-claw`
**Plugin namespace:** `openclaw milimo build`
**Blueprint file:** `milimo-blueprint/roles/build-claw.yaml`
**Sandbox policy:** `milimo-blueprint/policies/build-sandbox.yaml`
**Filesystem mount:** `/sandbox/build`

The Build Claw holds the most technically sensitive assets in the squad:
the codebase, environment configurations, deployment credentials, API keys,
and production secrets. These are isolated at the kernel level via NVIDIA
OpenShell Landlock filesystem restrictions.

**No other claw can read `/sandbox/build` directly.**
Secrets are encrypted at rest and never appear in any inter-claw message.
The Build Claw shares data only through typed messages — and only
summary-level data at that. The Content Claw receives shipping summaries
for devlog posts, never code. The Ops Claw receives deploy completion
signals, never repository details.

This isolation is architectural, not policy-based. It cannot be bypassed
by any instruction the claw receives.

---

## FILESYSTEM LAYOUT

Everything the Build Claw owns lives under `/sandbox/build`:

```
/sandbox/build/
├── repo/                                # codebase (GitHub repository mount)
│   └── {configured repository}
│
├── context/
│   ├── sprint/
│   │   ├── current-plan.json           # approved sprint plan
│   │   ├── backlog-scored.json         # issue backlog with complexity scores
│   │   └── velocity.json               # squad velocity history
│   ├── errors/
│   │   ├── patterns/                   # identified recurring error classes
│   │   │   └── {pattern_id}.json
│   │   └── active/                     # open error investigations
│   │       └── {error_id}.json
│   └── costs/
│       ├── inference-weekly.json       # weekly inference API cost tracking
│       └── inference-history.jsonl     # historical cost records
│
├── prs/
│   ├── drafted/                        # PRs drafted, awaiting REVIEW
│   │   └── {pr_id}.json
│   ├── approved/                       # PRs approved, awaiting HOLD merge
│   │   └── {pr_id}.json
│   └── merged/                         # merge history
│       └── {pr_id}.json
│
├── deployments/
│   ├── pending/                        # deploys approved, awaiting HOLD release
│   │   └── {deploy_id}.json
│   └── history/                        # deployment history
│       └── {deploy_id}.json
│
├── docs/
│   ├── changelog.md                    # maintained by Build Claw
│   ├── api-reference/                  # generated from code changes
│   └── devlog/                         # weekly shipping summaries (draft)
│
└── logs/
    ├── operational.log                 # every action taken, timestamped
    ├── pr-activity.log                 # PR open, review, merge history
    ├── deploy-activity.log             # deploy attempts and outcomes
    └── cost-alerts.log                 # inference cost anomalies
```

**What the Build Claw can read:**
- Everything under `/sandbox/build/`
- `/sandbox/analytics/reports/weekly-intelligence.json` (read-only mount)
  — used for retention signal context during sprint planning

**What the Build Claw cannot read under any circumstances:**
- `/sandbox/clients/` — client contact data (Ops Claw only)
- `/sandbox/finance/` — financial records (Finance Claw only)
- `/sandbox/content/` — creative assets and brand data (Content Claw only)
- `/sandbox/assistant/` — session data and context (Assistant Claw only)

The Assistant Claw (`/sandbox/assistant`) likewise cannot read the Build
Claw's primary mount or any other claw's primary mount — isolation is mutual.

---

## NETWORK EGRESS POLICY

The Build Claw has the broadest network access of all claws — because
software development requires access to the developer tool ecosystem.
Every endpoint is restricted to the development infrastructure only.

**Approved endpoints:**
```
api.github.com                   # GitHub API — issues, PRs, commits, branches
api.vercel.com                   # Vercel deployment API
api.railway.app                  # Railway deployment API
api.cloudflare.com               # Cloudflare API — DNS, Workers, Pages
api.stripe.com                   # Stripe API — integration testing only
api.sentry.io                    # Sentry error monitoring — read + event ingest
api.datadoghq.com                # Datadog — metrics and log read
registry.npmjs.org               # npm package registry
pypi.org                         # Python package index
api.github.com/repos/.../releases # GitHub Releases API
docs.nvidia.com                  # NVIDIA NIM API documentation
integrate.api.nvidia.com         # NVIDIA inference API
api.anthropic.com                # Claude API (if used in the product)
api.openai.com                   # OpenAI API (if used in the product)
```

**Blocked (representative examples):**
```
api.gmail.com                    # Build Claw never communicates with clients
api.twitter.com                  # Build Claw never publishes content
api.stripe.com (live keys)       # Stripe live credentials blocked in dev
Any IP not in allowlist          # strict default-deny egress
```

**Critical rules:**
1. The Build Claw never communicates with clients directly.
   All client-facing communication about deployments goes through Ops Claw
   via the `deploy_complete` message — never direct from Build Claw.
2. Production deployments require HOLD operator approval.
   The Build Claw can stage a deployment but cannot trigger it without
   explicit HOLD release.
3. No secret or API key ever appears in an inter-claw message.
   Secrets live in `/sandbox/build` encrypted at rest. They are used
   by the Build Claw internally but never shared.

---

## INFERENCE ROUTING

**Development / testing phase:** All inference routes to cloud.
Log `data_type` on every inference call. Mandatory, not optional.

**Production target routes (reference only — NOT enforced during dev):**

| Data Type | Production Route | Reason |
|---|---|---|
| Proprietary source code | Local NIM | Code is IP — never cloud |
| API keys and env vars | Local NIM | Secrets — never cloud |
| Architecture decisions | Local NIM | Sensitive design decisions |
| Code review and analysis | Local NIM | Contains proprietary code |
| Boilerplate and test generation | Cloud (NEMOCLAW_MODEL) | Non-sensitive, quality preferred |
| Public documentation drafts | Cloud (NEMOCLAW_MODEL) | Public-facing, quality matters |
| Public changelogs and release notes | Cloud (NEMOCLAW_MODEL) | Community will read these |
| Production log analysis with user data | Local NIM | User privacy non-negotiable |
| Dependency vulnerability analysis | Cloud (NEMOCLAW_MODEL) | Public CVE data |
| Issue complexity scoring | Cloud (NEMOCLAW_MODEL) | Non-sensitive task estimation |
| Devlog and shipping summary drafts | Cloud (NEMOCLAW_MODEL) | Public build-in-public content |

**In production, source code and secrets MUST route to local NIM.**
During development, cloud is used — but `data_type` must be logged
on every call so routing can be enforced with a flag change only.

---

## WHAT THE BUILD CLAW DOES AUTONOMOUSLY

All actions are logged to `/sandbox/build/logs/operational.log`
with ISO timestamp, action_type, entity_id, and outcome.

---

### SPRINT PLANNING

When the Analytics Claw sends `retention_signals` or when triggered by
the operator, the Build Claw generates a sprint plan:

1. Fetch all open GitHub issues via GitHub API
2. Score each issue by complexity via inference:
   - data_type: "issue_complexity_scoring"
   - Inputs: issue title, description, labels, linked PRs
   - Output: estimated hours, complexity tier (S/M/L/XL)
3. Query Analytics Claw via `behavior_query`:
   - "Which features have lowest retention correlation this week?"
4. Receive `behavior_query_response` from Analytics Claw
5. Generate sprint plan: top issues ranked by complexity score +
   retention impact signal from Analytics Claw
6. Write plan to `/sandbox/build/context/sprint/current-plan.json`
7. Queue sprint plan in War Room: REVIEW
   - Shows: issue list, estimated hours total, retention rationale
8. Log: action_type="sprint_plan_generated"

Operator approves or modifies the sprint plan. Build Claw begins
autonomous work on the first approved issue.

---

### AUTONOMOUS ISSUE RESOLUTION

For each approved issue in the sprint plan:

1. Read issue details from GitHub API
2. Read relevant codebase context from `/sandbox/build/repo/`
3. Generate implementation via inference:
   - data_type: "source_code_generation" ← routes to local NIM in production
   - Inputs: issue description, relevant code context, acceptance criteria
4. Write code to working branch
5. Run test suite — capture all output
6. If tests fail:
   - Analyze failure via inference: data_type: "code_review"
   - Attempt fix (max 3 attempts before escalating to War Room)
   - After 3 failed attempts: queue War Room REVIEW with failure context
7. If tests pass:
   - Generate PR description via inference: data_type: "pr_description_generation"
   - Open PR on GitHub
   - Write PR draft to `/sandbox/build/prs/drafted/{pr_id}.json`
   - Queue PR in War Room: REVIEW
8. Log: action_type="pr_opened"

---

### PR LIFECYCLE

**After PR is opened and queued as REVIEW:**

War Room card shows:
- PR title and description
- Issue it resolves
- Files changed (count and paths)
- Test results summary
- Link to GitHub PR

**Operator approves (Stage 1 — REVIEW):**
- PR moves to `/sandbox/build/prs/approved/{pr_id}.json`
- PR queued in War Room as HOLD

**Operator releases HOLD (Stage 2):**
- Build Claw merges PR via GitHub API
- PR moves to `/sandbox/build/prs/merged/{pr_id}.json`
- Log to pr-activity.log: merged
- Log: action_type="pr_merged"
- Trigger: deployment staging if auto-deploy is configured

**Operator blocks at REVIEW:**
- PR draft preserved with block reason
- Build Claw logs block as negative signal for future PR quality improvement
- Issue returned to backlog for re-scoping

---

### DEPLOYMENT PIPELINE

After a PR is merged, if the project has a deployment configuration:

1. Build Claw stages the deployment (no live traffic yet)
2. Run any configured pre-deploy checks
3. Write deploy record to `/sandbox/build/deployments/pending/{deploy_id}.json`
4. Queue in War Room: HOLD
   - Shows: what changed, version number, deploy target (Vercel/Railway/etc.)
   - Warning: "This will deploy to production"

**Operator releases HOLD:**
- Build Claw triggers deployment via Vercel/Railway API
- Monitor deployment progress
- On success:
  - Write to `/sandbox/build/deployments/history/{deploy_id}.json`
  - Log to deploy-activity.log: deployed
  - Send `deploy_complete` to Ops Claw
  - Send shipping summary to Content Claw (weekly accumulation)
  - Log: action_type="deployed_to_production"
- On failure:
  - Log failure details to deploy-activity.log
  - Queue War Room REVIEW: "Deployment failed — {error summary}"
  - Do NOT retry automatically — operator decides

---

### PRODUCTION MONITORING

The Build Claw continuously monitors production systems:

**Error log monitoring (Sentry/Datadog — runs every 30 minutes):**
1. Fetch recent error events from Sentry API
2. Group errors by root cause (stack trace clustering)
3. For each error group:
   - Check if a known pattern exists in `/sandbox/build/context/errors/patterns/`
   - If known pattern: auto-draft patch, queue as REVIEW
   - If new pattern: write to `/sandbox/build/context/errors/active/`
     Queue War Room REVIEW: "New error pattern detected — {summary}"
4. Log: action_type="error_monitoring_pass"

**Inference cost monitoring (runs daily):**
1. Read current week's API usage from inference provider APIs
2. Calculate cost per user (if user count available from Analytics Claw)
3. Compare against target margin from previous week's baseline
4. If cost drift > 15% above baseline:
   - Queue War Room REVIEW: "Inference cost drift detected"
   - Log to cost-alerts.log
5. Update `/sandbox/build/context/costs/inference-weekly.json`
6. Log: action_type="cost_monitoring_pass"

**Dependency security audit (runs weekly, Monday 08:00):**
1. Run dependency audit against npm/PyPI vulnerability databases
2. Identify packages with known CVEs
3. For well-understood vulnerabilities with clear fix paths:
   - Generate patch PR automatically
   - Queue as REVIEW
4. For complex or breaking-change vulnerabilities:
   - Queue War Room REVIEW with manual investigation recommendation
5. Log: action_type="dependency_audit_complete"

---

### DOCUMENTATION MAINTENANCE

The Build Claw autonomously maintains project documentation:

**Changelog maintenance (on every merged PR):**
1. Extract change summary from PR description and commit messages
2. Generate changelog entry via inference:
   - data_type: "changelog_generation"
3. Append to `/sandbox/build/docs/changelog.md`
4. Queue as AUTO — logged, operator sees in morning digest

**API documentation (on every PR that touches API routes):**
1. Detect API route changes from PR diff
2. Generate updated API reference docs via inference:
   - data_type: "api_documentation_generation"
3. Write to `/sandbox/build/docs/api-reference/`
4. Open a documentation PR (separate from code PR)
5. Queue as REVIEW

**Weekly devlog draft (Friday 17:00):**
1. Aggregate all merged PRs, deploys, and resolved issues for the week
2. Generate devlog draft via inference:
   - data_type: "devlog_draft_generation"
3. Write to `/sandbox/build/docs/devlog/week-{date}.md`
4. Send `shipping_summary` to Content Claw via inter-sandbox message
   — Content Claw uses this to draft build-in-public posts
5. Log: action_type="devlog_drafted"

---

## INTER-CLAW COORDINATION

All communication via typed message contracts through OpenShell gateway.

### Messages the Build Claw RECEIVES:

| Message Type | From | When | Payload |
|---|---|---|---|
| `feature_brief` | Ops Claw | New technical feature requested | client_id, project_id, feature_description, deadline, acceptance_criteria |
| `retention_signals` | Analytics Claw | Weekly + on churn anomaly | feature_adoption_rates, churn_correlation, recommended_features |
| `behavior_query_response` | Analytics Claw | Response to sprint planning query | feature_data, retention_correlation, recommendations, data_quality |

### Messages the Build Claw SENDS:

| Message Type | To | When | Payload |
|---|---|---|---|
| `deploy_complete` | Ops Claw | Production deploy succeeds | project_id, deploy_url, version, deployed_at |
| `shipping_summary` | Content Claw | Weekly (Friday 17:00) | week_of, prs_merged, issues_resolved, features_shipped, notable_changes |
| `behavior_query` | Analytics Claw | Before sprint planning | query, lookback_days, feature_ids (optional) |

### Message handling rules:
- `deploy_complete` fires immediately after a successful production deploy —
  Ops Claw uses this to notify the client that their feature is live
- `shipping_summary` accumulates the full week's activity — not one message
  per PR. One message per week, sent Friday 17:00
- `behavior_query` is sent before sprint planning so the Build Claw has
  Analytics intelligence before scoring issues. Wait for
  `behavior_query_response` before generating the sprint plan.
- `feature_brief` from Ops Claw is the entry point for client-requested
  features — Build Claw converts it into a GitHub issue and adds it to
  the scored backlog

### Handling feature_brief:
When a `feature_brief` arrives from Ops Claw:
1. Create a GitHub issue from the feature description
2. Score the issue for complexity and estimated hours
3. Add to `/sandbox/build/context/sprint/backlog-scored.json`
4. Send acknowledgment to Ops Claw via `feature_brief_acknowledged`
   within 10 minutes
5. Log: action_type="feature_brief_received"

---

## WAR ROOM APPROVAL FLOW

The Build Claw requires operator approval for every action that changes
production state. The two-stage model applies to both PR merges and
production deploys.

### Approval modes for Build Claw actions:

| Action | Mode | Behavior |
|---|---|---|
| PR open (from issue) | REVIEW | Operator reviews code diff before merging |
| PR merge | HOLD | Explicit HOLD release triggers GitHub merge |
| Production deploy | HOLD | Explicit HOLD release triggers deployment |
| Issue triage and scoring | AUTO | Logged, visible in morning digest |
| Dependency audit | AUTO | Audit runs, security PRs queue as REVIEW |
| Error pattern detection | REVIEW | Operator sees new error class |
| Auto-drafted patch PR | REVIEW | Operator reviews before queuing HOLD |
| Changelog update | AUTO | Logged, morning digest |
| API docs update | REVIEW | Operator confirms accuracy |
| Devlog draft | AUTO | Draft ready for Content Claw to use |
| Inference cost alert | REVIEW | Operator informed, decides on action |
| Sprint plan | REVIEW | Operator approves before work begins |
| Feature brief acknowledged | AUTO | Logged, morning digest |

### Two-stage PR and Deploy approval:

```
PR FLOW:
Stage 1 — REVIEW:
  Operator reviews: PR title, description, files changed, test results.
  Approving Stage 1 does NOT merge the PR.
  Approving Stage 1 queues the PR in the HOLD queue.

Stage 2 — HOLD release:
  The only trigger for GitHub PR merge.
  No code path may merge a PR without explicit HOLD release.

DEPLOY FLOW:
Stage 1 — (implied by PR merge):
  Deploy staging happens automatically after PR merge.

Stage 2 — HOLD:
  Separate HOLD for production deploy.
  Even if PR is merged, production deploy requires its own HOLD release.
  This means a merged PR that has not been deployed to production
  sits in the deploy HOLD queue indefinitely until operator acts.
```

### War Room card format for Build Claw actions:

```
┌─────────────────────────────────────────────────────────┐
│ 🟡 REVIEW   BUILD CLAW                     8 mins ago   │
│                                                         │
│ PR #52 ready — Fix: user retention bug in onboarding    │
│ Branch: fix/onboarding-retention                        │
│ Resolves: Issue #48                                     │
│                                                         │
│ 3 files changed  ·  +47 lines  ·  -12 lines            │
│ Tests: ✓ 94 passing  ·  0 failing                       │
│                                                         │
│ [View on GitHub]  [APPROVE]  [BLOCK]                    │
└─────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────┐
│ 🔴 HOLD     BUILD CLAW                     just now     │
│                                                         │
│ Deploy ready — v1.4.2 to production                     │
│ Target: Vercel (api.milimoclaw.com)                     │
│                                                         │
│ Includes: Fix #48, Fix #51, Feature #44                 │
│ Build: passing  ·  Preview: verified                    │
│                                                         │
│ This will deploy to production.                         │
│                                                         │
│ [RELEASE HOLD — DEPLOY]  [CANCEL]                       │
└─────────────────────────────────────────────────────────┘
```

---

## THE SELF-EVOLUTION CYCLE

Runs every Sunday at 02:00 — same time as Analytics Claw report generation,
same 5-stage pipeline as all claws (Observe → Identify → Propose →
Build → Deploy).

### What the Build Claw observes:

```
STAGE 1 — OBSERVE
  Read pr-activity.log: PR open/review/merge/block history
  Read deploy-activity.log: deploy success/failure/rollback history
  Read operational.log: all Build Claw actions and outcomes
  Read context/sprint/velocity.json: estimated vs actual hours history
  Read context/errors/patterns/: recurring error class history
  Read context/costs/inference-weekly.json: cost trend data
  Read analytics feed: retention signals and feature adoption data
```

### Patterns the Build Claw identifies:

- Which issue types have the largest estimation error (hours off)?
- Which PR types are most frequently blocked or heavily edited?
- Which error classes recur most frequently in production?
- Which inference API calls drift highest in cost over time?
- Which feature types generate the strongest retention improvement?
- Which deployment configurations have the highest failure rate?

### Evolution tools that emerge over time:

| Week | Tool | What It Does | Target Metric |
|---|---|---|---|
| 2 | PR style enforcer | Flags PRs that don't meet the squad's code conventions before REVIEW queue — reduces editing cycles | PR edit rate |
| 5 | Issue complexity scorer v2 | Estimates hours from issue descriptions calibrated to squad's actual velocity — not generic estimates | Estimation accuracy (% error) |
| 9 | Prompt regression tester | Runs baseline prompts against each new model version and surfaces quality deltas automatically | Output quality consistency |
| 14 | Cost anomaly detector v2 | Alerts when per-user or per-feature inference cost drifts above target margin — calibrated to squad's pricing | Cost-per-feature accuracy |
| 18 | Dependency audit runner v2 | Identifies fix patterns for the squad's specific dependency stack — auto-drafts patches for the most common CVE types | Security patch lead time |
| 22 | Error pattern classifier v2 | Groups production errors by root cause calibrated to the squad's actual codebase — auto-drafts patches for recurring classes | Mean time to patch |
| 28 | Churn signal correlator | Cross-references Analytics Claw retention signals with feature shipping dates — predicts which backlog items will most improve retention | Retention improvement per sprint |
| 36 | Auto-roadmap drafter | Synthesizes user feedback, churn signals, error patterns, cost data, and backlog into a prioritized roadmap draft — published to War Room every Monday morning | Sprint-to-retention impact ratio |

By week 36 — 9 months — the Build Claw has 8 engineering-specific tools
trained entirely on the squad's actual codebase, velocity history, and
user behavior data. The churn signal correlator (week 28) is a cross-claw
tool — it could not exist without the Analytics Claw's retention signals.
This is the compound intelligence that makes the mesh more than the sum
of its parts.

### Critical evolution constraint:
No evolved tool can access client contact data, financial records, source
code outside the Build Claw's own mount, or send messages to external
services. No evolved tool may initiate deployments or merges autonomously —
every production action still requires the two-stage human approval flow
regardless of what evolved tools recommend.

### Minimum thresholds before first evolution:
- 5 merged PRs (enough signal to detect code style patterns)
- 3 completed sprints (enough velocity data for estimation calibration)
- 2 production deploys (enough deployment history for risk assessment)
- 4 weeks of cost tracking data

---

## WHAT "WORKING CORRECTLY" LOOKS LIKE

**Day 1–7 (baseline):**
- Build Claw fetches and scores open GitHub issues
- Sprint plan generated from scored backlog, queued as REVIEW
- Operator approves first sprint plan
- Build Claw begins autonomous work on Issue #1
- First PR opened and queued as REVIEW
- Two-stage approval works correctly — no merges without HOLD release
- Operator spends 15–25 minutes per day on Build War Room actions

**Week 3–4 (first tools emerge):**
- PR style enforcer active — PRs arrive pre-validated to code conventions
- Fewer editorial edits required before REVIEW approve
- Issue complexity scorer calibrating to squad's actual velocity
- Estimates becoming more accurate (early calibration)

**Month 2–3 (compound tools):**
- Estimation accuracy measurably improved — sprints landing closer to plan
- Cost anomaly detector active — inference cost surprises eliminated
- Error pattern classifier active — first recurring error class auto-patched
- Dependency audit finding and patching vulnerabilities before they're exploited
- Operator Build time: 10–15 minutes per day

**Month 6+ (mature operation):**
- Churn signal correlator active — sprint priorities driven by retention data
  from Analytics Claw, not just issue labels
- Auto-roadmap drafter active — Monday morning roadmap draft in War Room
- Build Claw handles all mechanical engineering work autonomously
- Human engineers focus entirely on architecture and product decisions
- Operator Build time: 8–10 minutes per day (review PRs and release deploys)

---

## WHAT FAILURE LOOKS LIKE (DEBUGGING REFERENCE)

| Symptom | Likely Cause |
|---|---|
| Issues not fetched from GitHub | GitHub API credentials not configured or egress blocked |
| Sprint plan never generated | behavior_query not sent or behavior_query_response not awaited |
| PR opened without REVIEW queue | Approval mode misconfigured — should be REVIEW not AUTO |
| PR merged without HOLD | Two-stage approval bypassed — critical bug in approval_handler |
| Deploy triggered on PR merge | Deploy should require its own separate HOLD — check deploy pipeline |
| deploy_complete not sent to Ops | Signal dispatcher not wired to deployment success path |
| shipping_summary not sent to Content | Friday 17:00 scheduler not initialized |
| Error monitoring not running | Sentry credentials not configured or 30-minute schedule not started |
| Cost alerts not firing | Inference cost tracking not initialized — check costs/ directory |
| Source code routed to cloud | Privacy router data_type logged but not enforced — expected during dev |
| feature_brief not acknowledged | Acknowledgment timer not wired — must respond within 10 min |
| Churn signal correlator not building | Analytics Claw retention_signals not reaching Build Claw |
| Auto-roadmap not publishing Monday | Evolution tool evolved but scheduler not wired to War Room output |

---

## MINIMUM VIABLE FIRST RUN — TESTING SEQUENCE

Use this sequence to verify the Build Claw is working before enabling
full autonomous scheduling:

1. Configure GitHub API credentials in environment
2. Verify Build Claw can fetch open issues from the configured repository
3. Generate a sprint plan manually (bypass Monday schedule for testing)
4. Confirm sprint plan appears in War Room as REVIEW (not AUTO, not HOLD)
5. Approve the sprint plan
6. Confirm Build Claw begins working on Issue #1
7. Confirm PR is opened on GitHub
8. Confirm PR appears in War Room as REVIEW
9. Approve the REVIEW — confirm PR moves to HOLD queue (NOT merged yet)
10. Release the HOLD — confirm PR is merged on GitHub
11. Confirm deploy staging record created
12. Confirm deploy appears in War Room as HOLD (separate from PR HOLD)
13. Release the deploy HOLD — confirm deployment to Vercel/Railway
14. Confirm deploy_complete message sent to Ops Claw
15. Confirm shipping_summary accumulates PR data for Friday dispatch

All 15 steps must pass before autonomous scheduling is enabled.
Step 9 is the critical correctness test — REVIEW approval must not
trigger merge. Verify this explicitly.

---

## DEVELOPMENT AND TESTING NOTES

**Current phase:** All inference routes to cloud. Log data_type on every call.

**GitHub API is the primary dependency.** Without GitHub credentials and a
configured repository, the Build Claw cannot do its primary function. Configure
this first. Test the API connection before building any generation logic.

**Use a test repository during development.** Do not point the Build Claw at
a live production repository during testing. Create a dedicated test repository
with sample issues, a basic codebase, and a Vercel/Railway test deployment.
The Build Claw will open real PRs and trigger real deploys — use a sandbox.

**The two-stage deploy approval is as critical as the two-stage PR approval.**
A PR merge is reversible. A production deploy is not easily reversible.
Both require separate HOLD releases. Test both explicitly.

**Secrets management during development.** During development, store API keys
and credentials in environment variables only. Never commit credentials to the
repository. The Build Claw reads from environment variables; it does not store
credentials in `/sandbox/build` — it uses them transiently.

---

## FILES TO BUILD

```
orchestrator/build/build_init.py          — Filesystem structure initialization
orchestrator/build/issue_manager.py       — GitHub issue fetch, score, sprint plan
orchestrator/build/code_generator.py      — Autonomous issue resolution and PR opening
orchestrator/build/pr_manager.py          — PR lifecycle: draft, review, merge
orchestrator/build/deploy_manager.py      — Deployment pipeline: stage, approve, deploy
orchestrator/build/error_monitor.py       — Production error monitoring and auto-patch
orchestrator/build/cost_monitor.py        — Inference API cost tracking and alerting
orchestrator/build/dependency_auditor.py  — Dependency security audit and patching
orchestrator/build/doc_maintainer.py      — Changelog, API docs, devlog generation
orchestrator/build/approval_handler.py    — Two-stage War Room approval flow
orchestrator/build/signal_dispatcher.py  — Outbound message sending
orchestrator/build/build_scheduler.py     — Scheduled autonomous actions
orchestrator/build/build_claw.py          — Main entry point
milimo-blueprint/roles/build-claw.yaml    — Role blueprint
milimo-blueprint/policies/build-sandbox.yaml — Sandbox policy
```

---

## SPEC EDGE CASES

**What if an issue has no acceptance criteria?**
Build Claw flags the issue in the scored backlog with
`clarity_score: "low"` and includes it in the sprint plan with a
note: "Acceptance criteria missing — operator should clarify before
approving this issue for development." It does not refuse to score it —
it surfaces the gap and lets the operator decide.

**What if a PR fails tests after 3 automated fix attempts?**
After 3 failed attempts, Build Claw queues a War Room REVIEW:
"PR for Issue #{n} — tests failing after 3 automated fix attempts.
Human investigation required." The failure context (test output,
attempted fixes, error analysis) is included in the card. The
Build Claw does not attempt a 4th fix autonomously.

**What if a production deployment fails?**
Build Claw logs the failure to deploy-activity.log and queues a War
Room REVIEW: "Deployment failed — {error summary} — manual investigation
required." It does NOT automatically retry or rollback. Those are
irreversible actions that require operator judgment. The previous
deployment remains live.

**What if the GitHub API is rate-limited?**
Build Claw backs off with exponential delay: 1 min, 2 min, 4 min,
max 30 min. All rate-limited actions are logged to operational.log.
The Build Claw does not fail or crash on rate limiting — it queues
work and retries. The War Room does not receive a notification for
rate limiting unless it persists for more than 2 hours.

**What if a feature_brief arrives with a deadline that is impossible
given the current sprint?**
Build Claw adds the feature to the scored backlog with a
`deadline_risk: "high"` flag and notifies the War Room immediately
as a REVIEW: "Feature brief from Ops Claw — deadline {date} appears
infeasible given current sprint velocity. Operator attention needed."
It acknowledges the brief to Ops Claw regardless (within 10 minutes)
so Ops Claw can manage client expectations.

**What if two PRs conflict on the same file?**
Build Claw detects the conflict when the second PR is opened and
flags it in the War Room: "PR #{n} conflicts with PR #{m} on
{filename} — cannot be merged until conflict is resolved."
It does not attempt to resolve merge conflicts autonomously —
conflict resolution requires human judgment about intent.

**What if the squad has no Analytics Claw (non-tech squad using
Build Claw as standalone)?**
Build Claw generates sprint plans without retention signal input,
using only issue complexity scores and operator-provided priorities.
It sends `behavior_query` messages but does not block on receiving
a response. If no response arrives within 5 minutes, it proceeds
with best available data and logs: "Sprint plan generated without
Analytics Claw retention signals — no response received."

---

*This specification is the ground truth for the Build Claw.
If behavior in the codebase deviates from this document, the code is wrong.*

*Development note: All inference routes to cloud during testing.
Log data_type on every inference call. Source code and secrets
are the most sensitive data this claw handles — treat them accordingly.
Use a test repository. Do not point the Build Claw at a live production
repository during development.*

*Milimo Claw · built on NVIDIA NemoClaw · March 2026*
