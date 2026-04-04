# Build Claw Implementation Plan

## Objective

Implement the complete Build Claw Python module (`orchestrator/build/`) — 13 modules totaling approximately 4,500–5,500 lines — following the spec in `MILIMO_CLAW_BUILD_CLAW_SPEC.md`. Also fix the Finance Claw's empty `__init__.py`. The Build Claw is the engineering department of the Milimo Claw squad: it fetches GitHub issues, generates code, opens PRs, manages a two-stage approval flow (REVIEW → HOLD for both PRs and deploys), monitors production errors, tracks inference costs, audits dependencies, maintains documentation, and runs a self-evolution cycle.

---

## Implementation Plan

### Phase 1: Finance Claw `__init__.py` Fix (Quick Win)

- [ ] **1.1 Populate `orchestrator/finance/__init__.py`** — Export all 11 public classes from the Finance Claw modules, following the same pattern used by Content, Ops, and Analytics `__init__.py` files. Classes to export: `FinanceClaw`, `FinanceFilesystemInit`, `FinanceLogEntry`, `InitResult`, `ValidationResult`, `PricingEngine`, `InvoiceManager`, `FinanceApprovalHandler`, `PaymentRiskScorer`, `PaymentMonitor`, `RevenueTracker`, `ExpenseTracker`, `FinanceScheduler`, `FinanceSignalDispatcher`

### Phase 2: Build Claw Foundation (3 modules)

- [ ] **2.1 `orchestrator/build/__init__.py`** — Package exports for all Build Claw public classes, following the pattern from `content/__init__.py` (123 lines), `ops/__init__.py` (92 lines), `analytics/__init__.py` (61 lines)
- [ ] **2.2 `orchestrator/build/build_init.py`** — Filesystem initialization for `/sandbox/build`. Creates the full directory tree: `repo/`, `context/sprint/`, `context/errors/patterns/`, `context/errors/active/`, `context/costs/`, `prs/drafted/`, `prs/approved/`, `prs/merged/`, `deployments/pending/`, `deployments/history/`, `docs/api-reference/`, `docs/devlog/`, `logs/`. Includes `InitResult`, `ValidationResult`, `BuildLogEntry`, `BuildOperationalLog` dataclasses. Must be idempotent (safe to run twice). Must include `atomic_write_json()` for safe file writes. Must include `get_pr_path(status, pr_id)` and `get_deploy_path(status, deploy_id)` helpers. Tests already exist in `test_build_unit.py` — the implementation must match the test expectations (imports: `BuildFilesystemInit`, `BuildLogEntry`, `BuildOperationalLog`, `InitResult`, `ValidationResult`, `BASE`, `REQUIRED_DIRS`, `REQUIRED_FILES`)
- [ ] **2.3 `orchestrator/build/signal_dispatcher.py`** — Outbound message sending via mesh gateway. Sends: `deploy_complete` → Ops Claw, `shipping_summary` → Content Claw, `behavior_query` → Analytics Claw, `feature_brief_acknowledged` → Ops Claw. Must handle the `behavior_query` → `behavior_query_response` async pattern (send query, track pending, match response). Must accumulate `shipping_summary` data throughout the week for Friday 17:00 dispatch. Tests already exist in `test_build_unit.py` — imports: `BuildSignalDispatcher`, `PendingBehaviorQuery`, `ANALYTICS_WAIT_SECONDS`

### Phase 3: Build Claw Approval Flow (1 module)

- [ ] **3.1 `orchestrator/build/approval_handler.py`** — Two-stage War Room approval flow. Critical: this is the most important module for correctness. Must implement:
  - **PR Flow**: Stage 1 REVIEW → Stage 2 HOLD release → merge. REVIEW approval must NOT merge — it only moves to HOLD queue.
  - **Deploy Flow**: Separate HOLD from PR merge. Merged PR that hasn't been deployed sits in deploy HOLD queue indefinitely.
  - **Approval modes**: REVIEW (draft → operator reviews), HOLD (explicit release required), AUTO (logged only)
  - Data types: `BuildApprovalAction` (action_id, action_type, mode, content, context, created_at), `ApprovalResult`
  - Log types: `PRActivityLog`, `DeployActivityLog`
  - Methods: `queue_review()`, `queue_hold()`, `handle_approve()`, `handle_block()`, `handle_hold_release()`, `get_action()`, `move_pr_to_approved()`, `move_pr_to_merged()`, `move_deploy_to_history()`
  - Tests already exist in `test_build_unit.py` — imports: `ApprovalResult`, `BuildApprovalAction`, `BuildApprovalHandler`, `DeployActivityLog`, `PRActivityLog`

### Phase 4: Build Claw Core Logic (4 modules)

- [ ] **4.1 `orchestrator/build/issue_manager.py`** — GitHub issue fetch, complexity scoring, sprint planning. Implements:
  - Fetch open issues from GitHub API (with exponential backoff: 1min, 2min, 4min, max 30min)
  - Score issues by complexity via inference (data_type: "issue_complexity_scoring")
  - Query Analytics Claw via `behavior_query` before sprint planning
  - Generate sprint plan ranked by complexity + retention impact
  - Write plan to `context/sprint/current-plan.json`
  - Queue sprint plan in War Room as REVIEW
  - Handle `feature_brief` from Ops Claw: create GitHub issue, score, add to backlog, acknowledge within 10 minutes
  - Handle impossible deadlines: flag with `deadline_risk: "high"`, queue War Room REVIEW
- [ ] **4.2 `orchestrator/build/code_generator.py`** — Autonomous issue resolution. Implements:
  - Read issue details from GitHub API
  - Read codebase context from `/sandbox/build/repo/`
  - Generate implementation via inference (data_type: "source_code_generation" → local NIM in production)
  - Write code to working branch
  - Run test suite, capture output
  - Auto-fix on test failure (max 3 attempts, then escalate to War Room REVIEW)
  - Generate PR description via inference (data_type: "pr_description_generation")
  - Open PR on GitHub
  - Write PR draft to `prs/drafted/{pr_id}.json`
  - Queue PR in War Room as REVIEW
  - Detect PR conflicts on same file → flag in War Room
- [ ] **4.3 `orchestrator/build/pr_manager.py`** — PR lifecycle management. Implements:
  - Track PRs through drafted → approved → merged states
  - Handle REVIEW approval → move to HOLD queue (NOT merge)
  - Handle HOLD release → merge via GitHub API
  - Handle REVIEW block → preserve draft with reason, return issue to backlog
  - Log all PR activity to `logs/pr-activity.log`
  - Detect merge conflicts between concurrent PRs
  - Update `context/sprint/velocity.json` after each merge (estimated vs actual hours)
- [ ] **4.4 `orchestrator/build/deploy_manager.py`** — Deployment pipeline. Implements:
  - Stage deployment after PR merge (no live traffic)
  - Run pre-deploy checks
  - Write deploy record to `deployments/pending/{deploy_id}.json`
  - Queue in War Room as HOLD with warning: "This will deploy to production"
  - On HOLD release: trigger deploy via Vercel/Railway API, monitor progress
  - On success: write to `deployments/history/`, log to `deploy-activity.log`, send `deploy_complete` to Ops, add to `shipping_summary` for Content
  - On failure: log to `deploy-activity.log`, queue War Room REVIEW, do NOT auto-retry or rollback
  - Deploy targets: Vercel, Railway, Cloudflare (from network egress policy)

### Phase 5: Build Claw Monitoring (3 modules)

- [ ] **5.1 `orchestrator/build/error_monitor.py`** — Production error monitoring. Implements:
  - Fetch recent error events from Sentry/Datadog API (every 30 minutes)
  - Group errors by root cause (stack trace clustering)
  - Check against known patterns in `context/errors/patterns/`
  - Known pattern → auto-draft patch PR, queue as REVIEW
  - New pattern → write to `context/errors/active/`, queue War Room REVIEW
  - Log: action_type="error_monitoring_pass"
- [ ] **5.2 `orchestrator/build/cost_monitor.py`** — Inference API cost tracking. Implements:
  - Read current week's API usage from inference provider APIs (daily)
  - Calculate cost per user (if available from Analytics Claw)
  - Compare against target margin from previous week's baseline
  - If cost drift > 15% above baseline → queue War Room REVIEW, log to `cost-alerts.log`
  - Update `context/costs/inference-weekly.json`
  - Append to `context/costs/inference-history.jsonl`
  - Log: action_type="cost_monitoring_pass"
- [ ] **5.3 `orchestrator/build/dependency_auditor.py`** — Dependency security audit. Implements:
  - Run dependency audit against npm/PyPI vulnerability databases (weekly, Monday 08:00)
  - Identify packages with known CVEs
  - Well-understood vulns → generate patch PR automatically, queue as REVIEW
  - Complex/breaking-change vulns → queue War Room REVIEW with manual investigation recommendation
  - Log: action_type="dependency_audit_complete"

### Phase 6: Build Claw Documentation & Scheduling (2 modules)

- [ ] **6.1 `orchestrator/build/doc_maintainer.py`** — Documentation maintenance. Implements:
  - **Changelog**: On every merged PR, extract change summary, generate entry via inference (data_type: "changelog_generation"), append to `docs/changelog.md`, queue as AUTO
  - **API docs**: On PRs touching API routes, detect changes from diff, generate updated docs via inference (data_type: "api_documentation_generation"), write to `docs/api-reference/`, open separate docs PR, queue as REVIEW
  - **Weekly devlog**: Friday 17:00, aggregate merged PRs/deploys/issues, generate devlog draft via inference (data_type: "devlog_draft_generation"), write to `docs/devlog/week-{date}.md`, send `shipping_summary` to Content Claw
- [ ] **6.2 `orchestrator/build/build_scheduler.py`** — Scheduled autonomous actions. Implements:
  - Error monitoring: every 30 minutes
  - Cost monitoring: daily
  - Dependency audit: weekly, Monday 08:00
  - Devlog draft: Friday 17:00
  - Sprint planning: Monday morning (or triggered by `retention_signals` from Analytics)
  - Shipping summary dispatch: Friday 17:00
  - Uses APScheduler or similar, same pattern as `ops_scheduler.py`, `finance_scheduler.py`

### Phase 7: Build Claw Entry Point (1 module)

- [ ] **7.1 `orchestrator/build/build_claw.py`** — Main entry point. Follows the exact pattern from `finance_claw.py`, `ops_claw.py`, `content_claw.py`:
  - Constructor: `squad_id`, `inference_client`, `github_client`, `mesh_gateway`, `base_path` (default `/sandbox/build`)
  - `startup()`: filesystem init → component wiring → register inbound handlers → register approval handlers → start scheduler → log `claw_started`
  - `shutdown()`: stop scheduler → log `claw_stopped`
  - `handle_inbound()`: route by `message_type` — `feature_brief`, `retention_signals`, `behavior_query_response`
  - `handle_approval_decision()`: route by decision — `approved`, `edited`, `blocked`, `released`
  - Inbound message types: `feature_brief` (from Ops), `retention_signals` (from Analytics), `behavior_query_response` (from Analytics)
  - Components wired: `build_init`, `issue_manager`, `code_generator`, `pr_manager`, `deploy_manager`, `error_monitor`, `cost_monitor`, `dependency_auditor`, `doc_maintainer`, `approval_handler`, `signal_dispatcher`, `build_scheduler`
  - Protocol classes: `InferenceClient`, `GitHubClient`, `MeshGateway`

### Phase 8: Verification

- [ ] **8.1 Run existing Build Claw tests** — `pytest milimo-blueprint/tests/test_build_unit.py -v` — all 2,292 lines of tests must pass against the new implementation
- [ ] **8.2 Run Build Claw MVR integration tests** — `pytest milimo-blueprint/tests/test_build_mvr_integration.py -v` — 544 lines of integration tests must pass
- [ ] **8.3 Run full test suite** — `pytest milimo-blueprint/tests/ -v --ignore=milimo-blueprint/tests/test_build_unit.py --ignore=milimo-blueprint/tests/test_build_mvr_integration.py` — verify no regressions
- [ ] **8.4 TypeScript compilation** — `cd milimo && npx tsc --noEmit` — must remain clean
- [ ] **8.5 Verify the 15-step MVR sequence** from the spec: GitHub fetch → sprint plan → REVIEW → approve → HOLD → release → deploy → `deploy_complete` → `shipping_summary`

---

## Verification Criteria

1. **All 13 Build Claw modules exist** under `orchestrator/build/` with correct imports and exports
2. **`test_build_unit.py` passes** — 2,292 lines of pre-written tests validate the implementation
3. **`test_build_mvr_integration.py` passes** — integration tests validate end-to-end flows
4. **Two-stage approval is correct** — REVIEW approval does NOT merge PR; separate HOLD required for deploy
5. **All 3 inbound message types handled** — `feature_brief`, `retention_signals`, `behavior_query_response`
6. **All 4 outbound message types implemented** — `deploy_complete`, `shipping_summary`, `behavior_query`, `feature_brief_acknowledged`
7. **Finance `__init__.py` exports all classes** — no longer empty
8. **No regressions** in Content, Ops, Analytics, or orchestrator core tests

---

## Potential Risks and Mitigations

1. **Test-implementation mismatch** — The existing tests were written before the implementation, so there may be subtle API mismatches (method names, parameter order, dataclass fields)
   - *Mitigation*: Read each test file carefully before writing the corresponding module. Match the exact class names, method signatures, and import paths the tests expect.

2. **GitHub API client complexity** — The spec requires GitHub API integration but there's no existing GitHub client in the codebase
   - *Mitigation*: Use a Protocol-based interface (like `StripeClient` in Finance Claw). The Build Claw receives a `GitHubClient` protocol that handles HTTP calls. This keeps the claw testable with mocks.

3. **Scheduler complexity** — Multiple scheduled tasks with different intervals (30min, daily, weekly, Friday 17:00, Monday morning)
   - *Mitigation*: Follow the exact pattern from `ops_scheduler.py` and `finance_scheduler.py`. Use APScheduler with `BlockingScheduler` or `BackgroundScheduler`.

4. **Two-stage approval correctness** — The most critical correctness requirement. A bug here could merge PRs or deploy to production without operator approval
   - *Mitigation*: Write the approval_handler first and verify it against tests before building anything that depends on it. Add explicit assertions: `assert action.mode == "HOLD"` before any merge/deploy action.

5. **Module shadowing with Python `build` package** — Python's standard `build` package may shadow `orchestrator/build/`
   - *Mitigation*: Use relative imports within the package (`from .build_init import ...`). In tests, ensure `sys.path` is set correctly so `from build import ...` resolves to the local package, not Python's `build`.

---

## Alternative Approaches

1. **Implement modules one at a time with test verification** — Build each module, run its specific tests, then move to the next. This is slower but catches issues early.

2. **Implement all foundation modules first, then core logic, then monitoring** — This is the approach in the plan above. It allows parallel verification and follows dependency order.

3. **Create a mock GitHub client first** — Before implementing real GitHub API calls, create a comprehensive mock that simulates GitHub's behavior (rate limiting, conflicts, PR states). This enables full testing without a real repository.

---

## Design Decisions & Assumptions

1. **GitHubClient Protocol** — Following the pattern of `StripeClient` in Finance Claw and `MeshGateway` in Ops Claw, the Build Claw will define a `GitHubClient` Protocol with methods: `fetch_issues()`, `create_issue()`, `open_pr()`, `merge_pr()`, `get_pr_status()`, `create_branch()`, `commit_files()`. The actual implementation can be a real GitHub API wrapper or a mock for testing.

2. **Inference routing** — During development, all inference routes to cloud. Every inference call must log `data_type`. The privacy router is NOT enforced during this phase (per the spec's development note).

3. **Filesystem paths** — All paths are relative to `base_path` (default `/sandbox/build`). The `build_init.py` module creates the full directory tree.

4. **Scheduler** — Uses the same pattern as other claws. The Build Claw's scheduler is more complex due to the variety of intervals (30min, daily, weekly, specific days/times).

5. **Error handling** — All inbound message handlers catch exceptions and log them. The claw never crashes on bad input.

6. **data_type logging** — Every inference call includes a `data_type` parameter for future privacy routing enforcement. Values: "source_code_generation", "code_review", "pr_description_generation", "issue_complexity_scoring", "changelog_generation", "api_documentation_generation", "devlog_draft_generation", "error_analysis", "cost_analysis".
