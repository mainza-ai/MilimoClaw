> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — MASTER CODEBASE AUDIT AND COMPLETION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Give this prompt to any AI coding assistant to perform a systematic audit
# of the Milimo Claw codebase, identify all gaps against the spec documents
# and implementation prompts, and fix every gap found.
#
# This prompt is self-contained. The AI does not need prior context about
# Milimo Claw — everything it needs to understand the system is either in
# this prompt or referenced from the attached documents.
#
# ATTACH THESE DOCUMENTS (in this order):
#   1.  AGENTS.md                                    (quick reference — read first)
#   2.  MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md         (solo template ground truth)
#   3.  MILIMO_CLAW_CONTENT_CLAW_SPEC.md             (Content Claw ground truth)
#   4.  MILIMO_CLAW_OPS_CLAW_SPEC.md                 (Ops Claw ground truth)
#   5.  MILIMO_CLAW_ANALYTICS_CLAW_SPEC.md           (Analytics Claw ground truth)
#   6.  MILIMO_CLAW_FINANCE_CLAW_SPEC.md             (Finance Claw ground truth)
#   7.  MILIMO_CLAW_BUILD_CLAW_SPEC.md               (Build Claw ground truth)
#   8.  CONTENT_CLAW_IMPLEMENTATION_PROMPT.md        (Content implementation guide)
#   9.  OPS_CLAW_IMPLEMENTATION_PROMPT.md            (Ops implementation guide)
#   10. ANALYTICS_CLAW_IMPLEMENTATION_PROMPT.md      (Analytics implementation guide)
#   11. FINANCE_CLAW_IMPLEMENTATION_PROMPT.md        (Finance implementation guide)
#   12. BUILD_CLAW_IMPLEMENTATION_PROMPT.md          (Build implementation guide)
#   13. SOLO_TEMPLATE_V2_REMEDIATION_PROMPT.md       (Solo template fixes)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert Python and TypeScript engineer performing a systematic
audit and completion pass on the Milimo Claw codebase. Your job is to
find every gap between the current implementation and the spec documents,
then fix each gap completely — no stubs, no TODOs, no placeholders.

Read this entire prompt before doing anything else. The order of operations
matters. Do not skip ahead.

---

## WHAT THIS SYSTEM IS

Milimo Claw is a multi-agent autonomous hustle platform built as a plugin
on NVIDIA NemoClaw. Six specialized AI agents (claws) run in isolated
sandboxes and coordinate through a typed inter-sandbox message gateway.
In the solo-founder template, one operator manages all six claws through
a single War Room TUI, spending under 15 minutes per day. The operator
is whoever deployed the template — a student, a solo founder, or any
single person running their own squad. The platform is built for anyone.

The six claws:
- CONTENT CLAW — generates all creative output autonomously
- OPS CLAW — manages the full client lifecycle
- ANALYTICS CLAW — intelligence layer, weekly reports, signals
- FINANCE CLAW — invoicing, pricing, revenue, expenses
- BUILD CLAW — GitHub issues, PRs, deploys, monitoring
- ASSISTANT CLAW — conversational interface, operator queries, claw coordination

Everything you need to understand each claw is in the attached spec
documents. Read them. They are the ground truth.

---

## GROUND TRUTH HIERARCHY

When documents conflict, this order applies:

1. Individual claw spec documents — internal claw behavior
2. MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md — cross-claw coordination
3. solo-founder.yaml — configuration values
4. AGENTS.md — quick reference only, not authoritative

If this prompt conflicts with a claw spec: the spec wins.

---

## DEVELOPMENT PHASE CONSTRAINTS

Apply these to every fix you make. No exceptions.

**Inference:** ALL inference routes to cloud (the configured NEMOCLAW_MODEL).
No local NIM routing. No privacy routing enforcement.
Log `data_type` on every inference call — mandatory.

```python
# Every inference call must follow this pattern:
response = inference_client.complete(
    prompt=prompt,
    data_type="source_code_generation",  # ALWAYS INCLUDE
    max_tokens=800
)
```

**External APIs:**
  - Stripe: test mode only (`sk_test_*`) — never live credentials
  - GitHub: test repository only — never a live production repo
  - All credentials from environment variables only

**Standards:**
  - Python 3.11+, full type hints, docstrings on every class and method
  - pathlib.Path only — never os.path
  - yaml.safe_load() only — never yaml.load()
  - Append-only JSONL for all log files with fcntl file locking
  - Atomic writes for all JSON summaries: temp file → Path.rename()
  - Never silently swallow exceptions
  - Tests: pytest (Python), Jest (TypeScript), full coverage

---

## HOW TO WORK THROUGH THIS PROMPT

### Step 1 — Read the documents

Read the attached documents in this order:
1. AGENTS.md — understand the system, message matrix, sequencing rules
2. MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md — understand solo configuration
3. Each claw spec in full before auditing that claw

Do not begin auditing until you have read the documents.

### Step 2 — Audit phase (before touching any code)

For each component below, audit the codebase against the spec.
Produce a structured gap report before writing a single line of fix code.

Gap report format for each component:
```
COMPONENT: [name]
STATUS: ✅ Complete | ⚠️ Partial | ❌ Missing
GAPS:
  - [specific gap description, file location if known]
PRIORITY: HIGH | MEDIUM | LOW
```

### Step 3 — Fix phase (in priority order)

Fix all HIGH gaps before any MEDIUM gaps.
Fix all MEDIUM gaps before any LOW gaps.
Within a priority level, fix in the order listed below.

For each fix:
  - State the file being modified (UPDATE) or created (NEW)
  - Write the complete implementation — no stubs, no TODOs
  - Write the complete test immediately after
  - Do not proceed to the next fix until the current fix's tests pass

### Step 4 — Integration verification

After all fixes, run the full verification suite in the order listed at
the bottom of this prompt. Every item in the Final Verification Checklist
must pass before the session is complete.

---

## AUDIT AND FIX SCOPE

Work through each component below. For each one: audit first, then fix.

---

### COMPONENT A — contracts.py (Message Schemas)

**What to check:**
Read every message type in the Complete Message Matrix from AGENTS.md.
For each message type, verify that `contracts.py` contains:
  - Correct `sender_roles` list
  - Correct `recipient_roles` list
  - All `required_payload` fields from the spec
  - SLA fields where the spec defines them (e.g. sla_minutes)

**Known gaps (from previous audits — verify and fix):**
  - `pricing_query` schema (Ops → Finance) — was missing
  - `client_onboarded` schema (Ops → Analytics) — was missing
  - `client_health_signal` sender_roles must include "ops"
  - `feature_brief_acknowledged` schema (Build → Ops) — was missing

**Fix:** Add all missing schemas. Follow the exact pattern of existing
entries. Do not modify schemas that are already correct.

**Test:** pytest covering: each new/updated schema validates correctly,
missing required fields raise validation errors, incorrect sender_role
raises, SLA field present where spec requires it.

---

### COMPONENT B — Sandbox Policy Files (Shared Mount)

**What to check:**
Open each of the five sandbox policy files:
  - `milimo-blueprint/policies/content-sandbox.yaml`
  - `milimo-blueprint/policies/ops-sandbox.yaml`
  - `milimo-blueprint/policies/analytics-sandbox.yaml`
  - `milimo-blueprint/policies/finance-sandbox.yaml`
  - `milimo-blueprint/policies/build-sandbox.yaml`

Every file except analytics-sandbox.yaml must contain a read-only mount
for `/sandbox/analytics/reports/weekly-intelligence.json`. This is the
most critical configuration item in the system. If any claw is missing
this mount, its intelligence feed is silently broken.

The analytics-sandbox.yaml itself must define this path as read_write
(the Analytics Claw owns and writes it).

**Fix:** Add the missing mount entry to any policy file that lacks it.
Follow the exact pattern of content-sandbox.yaml line 23.

**Test:** Run `pytest -m phase_a` — the Phase A isolation test suite.
All 8 tests (A1–A8) plus bonus isolation tests must pass.
If `tests/test_phase_a_isolation.py` does not exist, create it first
using the Phase A test suite from SOLO_TEMPLATE_V2_REMEDIATION_PROMPT.md.

---

### COMPONENT C — solo-founder.yaml

**What to check:**

**C1 — Evolution schedule:**
The `evolution:` block must use per-claw `schedule:` not a single `time:`.
Required schedule:
```yaml
evolution:
  cycle_day: sunday
  schedule:
    analytics_baseline:  "01:00"
    analytics_report:    "02:00"
    content:             "02:05"
    ops:                 "02:15"
    analytics_evolution: "02:25"
    build:               "02:35"
    finance:             "03:00"
```

**C2 — Cost guard:**
```yaml
cost_guard:
  daily_cloud_token_budget: 50000
  alert_at_percent: 80
  fallback_on_exceed: lighter_prompt
  never_block_claw_action: true
```

**C3 — Approval modes:**
Ops Claw deadline modes must be two separate entries:
  - `deadline_risk: REVIEW` (5+ days)
  - `deadline_critical: HOLD` (24 hours)
Not a single `deadline_flag: REVIEW`.

**C4 — Min thresholds:**
Every claw's min_thresholds must be present in the schedule block.
See MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md for exact values.

**Fix:** Update solo-founder.yaml for each gap found.

---

### COMPONENT D — solo_evolution.py

**What to check:**
The scheduler must parse the per-claw `schedule:` block from
solo-founder.yaml (not a single `time:` value) and create one
independent threading.Timer for each active claw's evolution cycle.

Required functions:
  - `parse_evolution_schedule(evolution_config: dict) -> dict[str, str]`
    Handles both new `schedule:` format and legacy `time:` fallback.
  - `_init_evolution_timers(evolution_config, claw_schedulers) -> None`
    Creates one timer per active claw at its spec-defined time.

**Fix:** Implement both functions if missing or incorrect.

**Test:** parse_evolution_schedule handles both formats, each claw gets
its own timer, Finance at 03:00 and Content at 02:05 verified separately,
inactive claw skipped without error.

---

### COMPONENT E — solo_sandbox.py

**What to check:**
Three helper functions must exist for the Phase A tests:
  - `load_sandbox_policy(claw_role: str) -> dict`
  - `get_read_only_mounts(policy: dict) -> list[Path]`
  - `get_all_accessible_mounts(policy: dict) -> list[Path]`

**Fix:** Add any missing functions.

---

### COMPONENT F — solo_privacy.py (Cost Guard)

**What to check:**
The `lighter_prompt` fallback strategy must be implemented:
  - Triggered when daily token budget (50,000) is exceeded
  - Reduces max_tokens by 50%
  - Trims enrichment context sections from prompts
  - Logs `action_type="cost_guard_fallback_active"` on every call
  - Never blocks a claw action — always completes the inference call

Required method: `_apply_lighter_prompt_strategy(prompt, max_tokens, data_type)`

**Fix:** Implement if missing.

**Test:** Budget at 100% triggers fallback, max_tokens reduced 50%,
fallback never raises, fallback logged, budget below 80% uses normal strategy.

---

### COMPONENT G — Content Claw (`orchestrator/content/`)

**What to check:**
Compare the current state of `orchestrator/content/` against the full
Content Claw spec and CONTENT_CLAW_IMPLEMENTATION_PROMPT.md.

Required files:
  - `content_init.py` — filesystem init + operational/approvals/performance logs
  - `content_generator.py` — ContentGenerator with full tool pipeline
  - `brief_manager.py` — brief receipt, acknowledgment (5-min SLA), revisions
  - `approval_handler.py` — APPROVE/EDIT/BLOCK handlers
  - `platform_publisher.py` — per-platform publishers + retry logic
  - `performance_monitor.py` — post-publish monitoring, anomaly detection
  - `publish_scheduler.py` — scheduling + missed publish recovery
  - `brand_voice.py` — voice profiles, local NIM routing for voice adapter
  - `content_scheduler.py` — daily 06:00 planning + Monday analytics query
  - `content_claw.py` — main entry point

**Critical behaviors to verify:**
  - Tool pipeline order: tone → platform → voice → predictor → timing → A/B
  - Tool failure does not crash generation — logged, skipped, continues
  - brief_acknowledged sent within 5 minutes of project_brief received
  - All final drafts route to cloud, internal ideation to local NIM
    (in production; cloud for all during dev — verify data_type logged)
  - performance_signal sent within 1 hour of publish
  - Atomic write for weekly-intelligence.json equivalent outputs
  - No publishing without REVIEW approval

**For any missing file:** Implement it in full using
CONTENT_CLAW_IMPLEMENTATION_PROMPT.md as the implementation guide.
Write tests immediately after each file.

---

### COMPONENT H — Ops Claw (`orchestrator/ops/`)

**What to check:**
Compare current state against OPS_CLAW_IMPLEMENTATION_PROMPT.md.

Required files:
  - `ops_init.py` — filesystem + template files + both log classes
  - `signal_dispatcher.py` — all 6 outbound messages, PricingNotConfirmedError
  - `approval_handler.py` — REVIEW/HOLD/AUTO, urgency flags at 24h and 48h
  - `intake_manager.py` — triage scoring (budget 0.4, scope 0.3, fit 0.3),
    handle_pricing_response, project_brief only after pricing confirmed
  - `health_scorer.py` — combined score weights, at_risk threshold 6.0
  - `project_manager.py` — deadline HOLD at ≤1 day, REVIEW at ≤5 days
  - `scope_monitor.py` — HOLD for scope creep (never REVIEW)
  - `comms_manager.py` — deep work detection, pricing question detection
  - `ops_scheduler.py` — daily 09:00 deadline check, Sunday health scoring
  - `ops_claw.py` — main entry point, both handlers for pricing_response

**Critical behaviors to verify:**
  - project_brief raises PricingNotConfirmedError without pricing_response
  - project_complete fires ONLY after client_confirmed = True
  - Deadline critical (≤24h) queues HOLD, not REVIEW
  - Scope creep always queues HOLD — never REVIEW, never AUTO
  - brief_acknowledged within 5 minutes
  - 30-minute message grouping window for rapid client messages
  - Urgency flags at 24h and 48h on stale REVIEW items

**For any missing file:** Implement using OPS_CLAW_IMPLEMENTATION_PROMPT.md.

---

### COMPONENT I — Analytics Claw (`orchestrator/analytics/`)

**What to check:**
Compare current state against ANALYTICS_CLAW_IMPLEMENTATION_PROMPT.md.

Required files:
  - `analytics_init.py` — filesystem + operational/queries/signals logs
  - `signal_processor.py` — all 5 inbound handlers, immediate health alert
  - `report_generator.py` — atomic write, archive, empty report on no data
  - `anomaly_detector.py` — 2× and 0.5× thresholds, per-claw dispatch
  - `opportunity_scorer.py` — daily 06:00, immediate dispatch at >0.85
  - `baseline_manager.py` — 30-day rolling, min 5 samples, None on low data
  - `query_handler.py` — 2-min SLA enforced and logged, never silent timeout
  - `forward_projector.py` — low confidence at <8 weeks, confidence intervals
  - `signal_dispatcher.py` — all 6 outbound messages
  - `analytics_scheduler.py` — Sunday 01:00 baselines, 02:00 report, daily 06:00
  - `analytics_claw.py` — main entry point, all 7 inbound handlers wired

**Critical behaviors to verify:**
  - weekly-intelligence.json written atomically (temp → rename)
  - Previous report preserved if new generation fails
  - Query response SLA: 2 minutes enforced, violations logged to
    both operational.log and signals.log
  - client_health_alert fires IMMEDIATELY when score < 6.0 — not weekly
  - revenue_anomaly fires IMMEDIATELY — not weekly
  - High-confidence opportunity dispatched mid-week (not only in weekly report)
  - Analytics Claw never queues HOLD actions
  - Query response always returns — never times out silently

**For any missing file:** Implement using ANALYTICS_CLAW_IMPLEMENTATION_PROMPT.md.

---

### COMPONENT J — Finance Claw (`orchestrator/finance/`)

**What to check:**
Compare current state against FINANCE_CLAW_IMPLEMENTATION_PROMPT.md.

Required files:
  - `finance_init.py` — filesystem + all three log classes
  - `signal_dispatcher.py` — all 4 outbound messages, revenue_summary totals only
  - `pricing_engine.py` — 10-min SLA, rule-based fallback, historical calibration
  - `invoice_manager.py` — TWO-STAGE APPROVAL, handle_stage1_approve never calls Stripe
  - `payment_risk_scorer.py` — neutral score (5.0) for new clients
  - `payment_monitor.py` — 24-hour checks, first overdue REVIEW, repeat HOLD
  - `revenue_tracker.py` — atomic write, WoW calculation, margin analysis
  - `expense_tracker.py` — tax classification, "uncategorized" on failure
  - `approval_handler.py` — queue_invoice_review and queue_invoice_hold separate
  - `signal_dispatcher.py` — revenue_summary payload: totals only, no line items
  - `finance_scheduler.py` — daily 09:00 payment check, Sunday 03:00 summary
  - `finance_claw.py` — main entry point

**Critical behaviors to verify (the most important in the system):**
  - handle_stage1_approve NEVER calls Stripe API — HOLD queue only
  - handle_stage2_hold_release is the ONLY path that calls Stripe
  - This must be verified by a test that mocks the Stripe client and
    asserts stripe_client.create_invoice.call_count == 0 after Stage 1
  - revenue_summary payload contains ZERO client names, invoice IDs, or
    line items — totals only (week_total, invoices_paid, invoices_pending)
  - payment_overdue fires IMMEDIATELY — not on a weekly cycle
  - HOLD staleness: urgency at 48h, escalation at 7 days
  - Stripe retry: every 30 min for 24h, then War Room REVIEW (never auto-retry)

**For any missing file:** Implement using FINANCE_CLAW_IMPLEMENTATION_PROMPT.md.

---

### COMPONENT K — Build Claw (`orchestrator/build/`)

**What to check:**
Compare current state against BUILD_CLAW_IMPLEMENTATION_PROMPT.md.

Required files:
  - `build_init.py` — filesystem + operational/pr-activity/deploy-activity/cost-alerts logs
  - `signal_dispatcher.py` — all 4 outbound messages + feature_brief_acknowledged
  - `approval_handler.py` — TWO SEPARATE two-stage flows (PR and deploy)
  - `issue_manager.py` — 5-min Analytics timeout, feature_brief handling
  - `code_generator.py` — max 3 fix attempts, escalate after 3rd failure
  - `pr_manager.py` — handle_review_approved NEVER merges, conflict detection
  - `deploy_manager.py` — deploy is independent HOLD from PR merge
  - `error_monitor.py` — 30-min cycle, known patterns auto-patch as REVIEW
  - `cost_monitor.py` — 15% drift threshold, cost-per-user calculation
  - `dependency_auditor.py` — simple fixes batch-PR, complex ones REVIEW
  - `doc_maintainer.py` — changelog APPENDS (never overwrites), Friday dispatch
  - `build_scheduler.py` — 30-min error, daily cost, Monday audit, Friday devlog
  - `build_claw.py` — main entry point, feature_brief and retention_signals wired

**Critical behaviors to verify:**
  - PR REVIEW approve → HOLD queue only — GitHub merge NOT called
    (test: mock github_client, assert merge call_count == 0 at Stage 1)
  - PR HOLD release → GitHub merge (assert call_count == 1)
  - PR merge → deploy STAGED but not triggered (deploy has its own HOLD)
  - Deploy HOLD release → Vercel/Railway API called
  - feature_brief_acknowledged sent within 10 minutes of feature_brief
    (10-min timer in signal_dispatcher.handle_feature_brief)
  - Sprint planning proceeds after 5-min Analytics timeout (ANALYTICS_WAIT_SECONDS = 300)
  - Changelog: append-only — doc_maintainer.update_changelog() must append
  - shipping_summary: one message per week accumulated, not one per PR
  - Test failures after 3rd attempt escalate to War Room REVIEW — no 4th attempt

**For any missing file:** Implement using BUILD_CLAW_IMPLEMENTATION_PROMPT.md.

---

### COMPONENT L — War Room (TypeScript)

**What to check:**
  - `milimo/src/warroom/warroom-tui.ts` — five-claw health panel renders
  - `milimo/src/warroom/approval.ts` — queue sorts HOLD above REVIEW above AUTO
  - `milimo/src/warroom/digest.ts` — morning brief at 07:00, evening at 20:00
  - Keyboard shortcuts registered: A, B, E, R, D, F, H, Q

**Solo War Room specific:**
  - `solo_warroom.py` — `queue_action()`, `handle_approve()`,
    `handle_hold_release()`, `get_health_panel()`, `get_pending_queue()`,
    `get_auto_log()`, `get_digest_schedule()`, `get_registered_shortcuts()`
  - HOLD items always appear before REVIEW items in queue regardless of
    insertion order
  - Approved actions: removed from pending, added to AUTO log

**Fix:** Implement or correct any missing functionality.

**Test:** Run `pytest -m phase_b` — the Phase B War Room integration tests.
If `tests/test_phase_b_warroom.py` does not exist, create it using
the Phase B test suite from SOLO_TEMPLATE_V2_REMEDIATION_PROMPT.md.

---

### COMPONENT M — Integration Test Suites

**What to check and ensure exists:**

| File | Purpose | Status Check |
|---|---|---|
| `tests/test_phase_a_isolation.py` | Sandbox mount verification (MUST PASS FIRST) | Must exist, all A1-A8 pass |
| `tests/test_phase_b_warroom.py` | War Room approval flow | Must exist, all B1-B8 pass |
| `tests/test_ops_mvr_integration.py` | Ops 10-step MVR | Must exist, all 10 pass |
| `tests/test_finance_mvr_integration.py` | Finance 14-step MVR | Must exist, all 14 pass |
| `tests/test_build_mvr_integration.py` | Build 15-step MVR | Must exist, all 15 pass |
| `tests/test_analytics_integration.py` | Analytics 11-step MVR | Must exist, all 11 pass |

**For any missing test file:** Implement it from the corresponding
implementation prompt's MVR test suite section.

**Critical tests that must pass individually (run and verify each):**

Finance MVR Test 6:
```python
def test_mvr_06_stage1_approve_creates_hold_not_send():
    # Approving Stage 1 REVIEW must NOT send the invoice.
    # Assert stripe_client.create_invoice.call_count == 0
    # after handle_review_approve() is called.
```

Build MVR Test 8:
```python
def test_mvr_08_pr_review_approve_creates_hold_not_merge():
    # Approving PR REVIEW must NOT merge the PR.
    # Assert github_client.merge_pull_request.call_count == 0
    # after handle_review_approved() is called.
```

These two tests are the most important correctness tests in the codebase.
They must pass before anything else is considered complete.

---

## CROSS-CUTTING CONCERNS

After completing all component fixes, verify these cross-cutting items:

### XC1 — data_type logging completeness

Grep the entire codebase for `inference_client.complete(` calls.
Every call must have a `data_type=` argument. No exceptions.

If any call is missing data_type, add it. Use these values:

| Module | data_type |
|---|---|
| intake_manager.py — triage | `client_triage_scoring` |
| intake_manager.py — welcome | `welcome_message_drafting` |
| intake_manager.py — brief check | `brief_quality_check` |
| intake_manager.py — proposal | `proposal_drafting` |
| scope_monitor.py | `scope_creep_detection` |
| scope_monitor.py — change order | `change_order_drafting` |
| health_scorer.py | `communication_sentiment_analysis` |
| comms_manager.py | `message_classification` |
| comms_manager.py — response | `response_drafting` |
| pricing_engine.py | `scope_cost_estimation` |
| invoice_manager.py | `invoice_generation` |
| revenue_tracker.py — margin | `margin_analysis` |
| revenue_tracker.py — rate | `rate_benchmarking_narrative` |
| expense_tracker.py | `tax_category_classification` |
| payment_risk_scorer.py | `payment_risk_scoring` |
| content_generator.py | `client_facing_draft` or `internal_ideation` |
| brand_voice.py | `voice_adapter_calibration` |
| report_generator.py | `report_narrative_generation` |
| opportunity_scorer.py | `opportunity_scoring` |
| issue_manager.py | `issue_complexity_scoring` |
| code_generator.py — implementation | `source_code_generation` |
| code_generator.py — review | `code_review` |
| pr_manager.py | `pr_description_generation` |
| doc_maintainer.py — changelog | `changelog_generation` |
| doc_maintainer.py — api docs | `api_documentation_generation` |
| doc_maintainer.py — devlog | `devlog_draft_generation` |

### XC2 — Single config.json source of truth

Verify `~/.milimo/config.json` is the only config file.
No separate `state.json`. Every command reads from and writes to one file.

### XC3 — No silent exception swallowing

Grep for bare `except:` or `except Exception: pass` patterns.
Every exception must be logged before being swallowed.
If an action cannot complete, it must log and either re-raise or
return a typed error result. It must never silently disappear.

### XC4 — fcntl file locking on all log files

Every class that appends to a `.log` or `.jsonl` file must use
`fcntl.flock()` before writing. Grep for `.write(` and `.append(`
calls on log file paths and verify each has locking.

### XC5 — Atomic writes on all JSON summaries

Every JSON summary file must be written with the temp→rename pattern.
Grep for summary file paths (weekly-summary.json, weekly-intelligence.json,
current-plan.json, etc.) and verify each write goes through an atomic
write helper rather than direct `Path.write_text()`.

### XC6 — No os.path usage

Grep for `os.path` anywhere in the Python codebase. Replace every
occurrence with the pathlib.Path equivalent. None should remain.

### XC7 — No yaml.load() usage

Grep for `yaml.load(` anywhere. Replace every occurrence with
`yaml.safe_load(`. None should remain.

### XC8 — TypeScript shell commands use spawn with array args

Grep `milimo/src/` for `exec(`, `execSync(`, and template literal
strings containing shell commands. Replace with `spawn` using array args.
None of the unsafe patterns should remain.

---

## FINAL VERIFICATION CHECKLIST

Run through every item. Every box must be checked before the session ends.

### Phase A — Sandbox Isolation (run first, gate everything else)
```
pytest -m phase_a
```
□ A1: All 5 sandbox directories exist
□ A2: weekly-intelligence.json writable by Analytics Claw
□ A3: Content Claw can read weekly-intelligence.json (policy verified)
□ A4: Ops Claw can read weekly-intelligence.json (policy verified)
□ A5: Finance Claw can read weekly-intelligence.json (policy verified)
□ A6: Build Claw can read weekly-intelligence.json (policy verified)
□ A7: Content Claw CANNOT read /sandbox/clients
□ A8: Finance Claw CANNOT read /sandbox/build
□ All bonus isolation tests pass

### Phase B — War Room
```
pytest -m phase_b
```
□ B1: Five-claw health panel renders
□ B2: Morning brief scheduled at 07:00, evening wrap at 20:00
□ B3: Mock REVIEW action appears in queue with correct metadata
□ B4: HOLD items sort above REVIEW items regardless of insertion order
□ B5: REVIEW approve calls execute_fn, removes from pending, adds to AUTO log
□ B6: HOLD action queued after REVIEWs appears at queue position 0
□ B7: HOLD release calls execute_fn
□ B8: All 8 keyboard shortcuts registered (A, B, E, R, D, F, H, Q)

### Contracts
□ pricing_query schema: sender_roles=["ops"], recipient=["finance"]
□ client_onboarded schema: sender_roles=["ops"], recipient=["analytics"]
□ client_health_signal sender_roles includes "ops"
□ feature_brief_acknowledged schema: sender_roles=["build"], sla_minutes=10
□ All 24+ message types validate with correct payload

### solo-founder.yaml
□ evolution.schedule has all 7 entries (not single time:)
□ cost_guard.daily_cloud_token_budget = 50000
□ cost_guard.fallback_on_exceed = lighter_prompt
□ cost_guard.never_block_claw_action = true
□ ops deadline_risk = REVIEW, deadline_critical = HOLD (separate entries)

### solo_evolution.py
□ parse_evolution_schedule() handles both schedule: and legacy time: formats
□ _init_evolution_timers() creates one timer per active claw
□ Finance timer at 03:00 verified, Content at 02:05 verified

### Content Claw
□ All 10 orchestrator files exist
□ Tool pipeline: tone → platform → voice → predictor → timing → A/B
□ Tool failure logged, skipped, generation continues
□ brief_acknowledged within 5 minutes (SLA enforced)
□ performance_signal sent within 1 hour of publish
□ All final drafts use cloud data_type, voice adapter logs voice_adapter_calibration
□ No publishing without REVIEW approval

### Ops Claw
□ All 10 orchestrator files exist
□ project_brief raises PricingNotConfirmedError without pricing_response
□ Deadline critical (≤1 day) → HOLD, deadline risk (≤5 days) → REVIEW
□ Scope creep → HOLD always (never REVIEW, never AUTO)
□ project_complete fires only when client_confirmed = True
□ 30-minute message grouping window active
□ Urgency flags at 24h and 48h on stale items

### Analytics Claw
□ All 11 orchestrator files exist
□ weekly-intelligence.json written atomically
□ Previous report preserved on generation failure
□ Query SLA: elapsed time measured, violations logged to both logs
□ client_health_alert fires IMMEDIATELY at score < 6.0
□ High-confidence opportunity dispatched mid-week (not only Sunday)
□ Analytics Claw never queues HOLD actions

### Finance Claw
□ All 11 orchestrator files exist
□ CRITICAL: handle_stage1_approve does NOT call Stripe
  (test asserts stripe_client.create_invoice.call_count == 0)
□ CRITICAL: handle_stage2_hold_released is the ONLY Stripe call path
□ revenue_summary payload: no client names, no invoice IDs, no line items
□ payment_overdue fires IMMEDIATELY (no weekly wait)
□ HOLD staleness: urgency at 48h, escalation at 7 days
□ Stripe retry: 30-min intervals for 24h, then War Room REVIEW

### Build Claw
□ All 13 orchestrator files exist
□ CRITICAL: PR REVIEW approve does NOT merge
  (test asserts github_client.merge_pull_request.call_count == 0)
□ CRITICAL: PR HOLD release triggers GitHub merge
□ CRITICAL: Deploy is staged after merge but requires its own HOLD
□ feature_brief_acknowledged sent within 10 minutes
□ Sprint planning proceeds after 5-min Analytics timeout
□ changelog.md appended (never overwritten)
□ shipping_summary: one accumulated message per week (Friday 17:00)
□ Max 3 fix attempts on failing tests — REVIEW after 3rd

### MVR Integration Suites
□ Finance MVR Test 6 passes (Stage 1 approve = zero Stripe calls)
□ Build MVR Test 8 passes (REVIEW approve = zero GitHub merge calls)
□ Build MVR Test 11 passes (deploy has its own separate HOLD)
□ All 10 Ops MVR steps pass
□ All 14 Finance MVR steps pass
□ All 15 Build MVR steps pass
□ All 11 Analytics MVR steps pass

### Cross-Cutting Concerns
□ XC1: data_type logged on every inference call (grep confirms)
□ XC2: Single config.json — no state.json exists
□ XC3: No bare except swallowing (grep confirms)
□ XC4: fcntl locking on all log file writes (grep confirms)
□ XC5: Atomic writes on all JSON summary files (grep confirms)
□ XC6: No os.path usage anywhere in Python codebase (grep confirms)
□ XC7: No yaml.load() anywhere (grep confirms)
□ XC8: No unsafe shell execution in TypeScript (grep confirms)

### Full test suite
```
pytest milimo-blueprint/ -v
```
□ All unit tests pass
□ All integration tests pass
□ No test relies on live Stripe API (sk_test_ only)
□ No test relies on live GitHub repository

---

## OUTPUT FORMAT

For each component audit:
```
=== AUDIT: [Component Name] ===
Status: [✅ Complete | ⚠️ Partial | ❌ Missing]
Gaps found: [N]
[Structured gap list]
```

For each fix:
```
--- FIX: [Component] — [File] ---
Type: [NEW | UPDATE]
Summary: [one sentence]

[complete implementation]

--- TESTS ---
[complete pytest or Jest test file]

--- VERIFICATION ---
[specific commands to run and expected output]
```

Do not move to the next component until the current component's
verification passes.

---

## STARTING INSTRUCTION

Begin with Component A (contracts.py). Read the Complete Message Matrix
from AGENTS.md, audit contracts.py against it, produce the gap report,
then fix. Do not proceed to Component B until Component A tests pass.

Work systematically. Every component. Every gap. Every test.

The milimo never stops. Work. Without working.
