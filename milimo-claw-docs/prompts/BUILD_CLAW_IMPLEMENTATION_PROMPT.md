> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — BUILD CLAW IMPLEMENTATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. BUILD_CLAW_AUDIT_REPORT.md             (the gap analysis)
#   2. MILIMO_CLAW_BUILD_CLAW_SPEC.md         (the ground truth spec)
#   3. build-claw.yaml                         (role blueprint — EXISTS)
#   4. build-sandbox.yaml                      (sandbox policy — EXISTS)
#   5. contracts.py                            (message types — EXISTS)
# ─────────────────────────────────────────────────────────────────────────────

You are an expert Python engineer building the Build Claw for Milimo Claw —
a multi-agent autonomous hustle platform built on NVIDIA NemoClaw.

The audit confirms the Build Claw is 0% implemented. The configuration files
exist (build-claw.yaml, build-sandbox.yaml, contracts.py) but no Python
orchestration code has been written. You are building all 13 modules
from scratch.

The spec document is the ground truth. The audit defines what must be built.
This prompt defines exactly how to build it.

---

## CONTEXT — THE SYSTEM YOU ARE BUILDING INTO

The Build Claw is the engineering department of a Milimo Claw tech squad.
It autonomously handles GitHub issues, generates code, opens PRs, manages
deployments, monitors production errors, tracks inference costs, runs
dependency audits, and maintains project documentation — all while
coordinating with the Ops, Analytics, and Content claws.

**Existing integrations that depend on Build Claw:**
  - `contracts.py` — all five Build Claw message types are defined
  - Ops Claw sends `feature_brief` → Build Claw must handle it
  - Analytics Claw sends `retention_signals` → Build Claw uses for sprint planning
  - Ops Claw expects `deploy_complete` → Build Claw must send after every deploy
  - Content Claw expects `shipping_summary` → Build Claw must send every Friday

**Reference implementations — use these as structural patterns:**
  - Finance Claw (`orchestrator/finance/`) — filesystem init, log management,
    signal dispatch, approval handler, atomic writes
  - Analytics Claw (`orchestrator/analytics/`) — scheduler design, signal
    processing, shared filesystem output

**Plugin structure:**
  - Python orchestrator:  `milimo-blueprint/orchestrator/`
  - New Build files:      `milimo-blueprint/orchestrator/build/`
  - Role blueprint:       `milimo-blueprint/roles/build-claw.yaml`
  - Sandbox policy:       `milimo-blueprint/policies/build-sandbox.yaml`
  - Operator config:      `~/.milimo/config.json`

**Operator:** Mainza Kangombe — senior systems architect, Python 3.11+,
Apple Silicon dev machine, RTX GPU for NIM. Production-quality code only.
No stubs. No TODOs. No placeholder comments. Every function complete.

---

## DEVELOPMENT PHASE CONSTRAINTS

**Inference:** ALL inference routes to cloud (the configured NEMOCLAW_MODEL via NVIDIA
Cloud API). Do NOT implement local NIM routing. DO log `data_type` on
every inference call — mandatory, not optional.

```python
# Every inference call must follow this pattern:
response = self.inference_client.complete(
    prompt=prompt,
    data_type="source_code_generation",  # ALWAYS INCLUDE
    max_tokens=2000
)
```

**Required data_type values per module:**

| data_type | Module | Notes |
|---|---|---|
| `issue_complexity_scoring` | issue_manager.py | Routes cloud in prod too |
| `source_code_generation` | code_generator.py | Routes local NIM in prod |
| `code_review` | code_generator.py | Routes local NIM in prod |
| `pr_description_generation` | pr_manager.py | Routes cloud in prod |
| `changelog_generation` | doc_maintainer.py | Routes cloud in prod |
| `api_documentation_generation` | doc_maintainer.py | Routes cloud in prod |
| `devlog_draft_generation` | doc_maintainer.py | Routes cloud in prod |

**Sandbox isolation applies.** Build Claw must only write to
`/sandbox/build/` and only receive other claws' data via typed
inter-claw messages. Source code and secrets never leave the sandbox.

**GitHub API test repository mandatory.** Do not point the Build Claw
at a live production repository during development. All GitHub API calls
use a dedicated test repository. Read GitHub credentials from environment:
  `GITHUB_TOKEN` — personal access token
  `GITHUB_REPO` — owner/repository-name (test repo)
  `GITHUB_DEFAULT_BRANCH` — default branch (usually "main")

**Two critical approval rules (non-negotiable):**
1. REVIEW approval on a PR does NOT merge it — queues HOLD only
2. Production deploy requires its OWN separate HOLD — independent of PR HOLD
If Step 9 of MVR (REVIEW approve) triggers a merge: CRITICAL BUG.
If PR merge automatically deploys without a deploy HOLD: CRITICAL BUG.

**No Analytics Claw timeout:** If `behavior_query_response` does not arrive
within 5 minutes of sending `behavior_query`, proceed with sprint planning
using only complexity scores. Log: "Sprint plan generated without Analytics
retention signals — no response received within 5-minute window."

**Standards (non-negotiable):**
  - Python 3.11+, full type hints, docstrings on every class and method
  - pathlib.Path only — never os.path string concatenation
  - PyYAML safe_load only — never yaml.load()
  - Append-only log files using fcntl file locking for thread safety
  - Atomic writes for JSON files: write temp → Path.rename() on success
  - Never silently swallow exceptions — log and re-raise or typed error
  - Tests: pytest, full coverage for every class and method

---

## PHASE 1 — CORE INFRASTRUCTURE
## Build in exact task order. Do not proceed to Phase 2 until all
## Phase 1 tests pass.

---

### TASK 1.1 — Build Filesystem Initialization

**New file:** `milimo-blueprint/orchestrator/build/build_init.py`

```python
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal
import json

BASE = Path("/sandbox/build")

REQUIRED_DIRS = [
    "repo",
    "context/sprint",
    "context/errors/patterns",
    "context/errors/active",
    "context/costs",
    "prs/drafted",
    "prs/approved",
    "prs/merged",
    "deployments/pending",
    "deployments/history",
    "docs/api-reference",
    "docs/devlog",
    "logs",
]

REQUIRED_FILES = {
    "context/sprint/current-plan.json": {
        "plan_id": None,
        "generated_at": None,
        "approved_at": None,
        "issues": [],
        "total_estimated_hours": 0,
        "status": "empty"
    },
    "context/sprint/backlog-scored.json": {
        "last_updated": None,
        "issues": []
    },
    "context/sprint/velocity.json": {
        "sprints": [],
        "avg_hours_per_week": 0,
        "estimation_accuracy_pct": 0
    },
    "context/costs/inference-weekly.json": {
        "week_of": None,
        "total_cost_usd": 0.0,
        "cost_per_user": 0.0,
        "baseline_cost_usd": 0.0,
        "drift_pct": 0.0,
        "last_updated": None
    },
    "docs/changelog.md": "# Changelog

All notable changes documented here.
",
    "logs/operational.log": None,      # JSONL — create empty
    "logs/pr-activity.log": None,
    "logs/deploy-activity.log": None,
    "logs/cost-alerts.log": None,
}

@dataclass
class InitResult:
    created_dirs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0

@dataclass
class ValidationResult:
    missing_dirs: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_dirs and not self.missing_files

class BuildFilesystemInit:
    """
    Creates and validates the full /sandbox/build/ filesystem structure.
    Idempotent — safe to call on every claw startup.
    """

    def initialize(self) -> InitResult: ...
    # Create all REQUIRED_DIRS and REQUIRED_FILES
    # Never overwrite existing files
    # Return full accounting in InitResult

    def validate(self) -> ValidationResult: ...

    def get_pr_path(
        self,
        status: Literal["drafted", "approved", "merged"],
        pr_id: str
    ) -> Path: ...

    def get_deploy_path(
        self,
        status: Literal["pending", "history"],
        deploy_id: str
    ) -> Path: ...

    def get_error_pattern_path(self, pattern_id: str) -> Path: ...
    def get_active_error_path(self, error_id: str) -> Path: ...

    def atomic_write_json(self, path: Path, data: dict) -> None: ...
    # Write to temp file in same directory, rename on success
    # Never overwrites good file with partial write
```

Also implement `BuildOperationalLog`:

```python
@dataclass
class BuildLogEntry:
    timestamp: str
    action_type: str   # sprint_plan_generated, pr_opened, pr_merged,
                       # deployed, error_detected, cost_alert, etc.
    entity_id: str     # pr_id, deploy_id, issue_number, error_id
    outcome: str       # success, failed, pending, escalated, blocked
    details: dict

class BuildOperationalLog:
    """Append-only structured log. Thread-safe via fcntl file locking."""

    def __init__(self, log_path: Path): ...
    def append(self, entry: BuildLogEntry) -> None: ...
    def read_recent(
        self,
        days: int = 30,
        action_type: str | None = None
    ) -> list[BuildLogEntry]: ...
    def count_by_type(self, action_type: str, days: int = 30) -> int: ...
    def get_last_run_time(self, action_type: str) -> str | None: ...
    # Returns ISO timestamp of most recent entry with this action_type
    # Used by scheduler for missed job detection
```

Write pytest tests: directory creation, idempotent re-run, validation
pass/fail, JSONL log append and read, atomic_write_json (verify temp
file cleaned up on success and failure), get_last_run_time returns
correct timestamp, concurrent write safety.

---

### TASK 1.2 — Signal Dispatcher

**New file:** `milimo-blueprint/orchestrator/build/signal_dispatcher.py`

```python
from dataclasses import dataclass

class BuildSignalDispatcher:
    """
    Sends all outbound messages from the Build Claw to other claws.
    Receives and routes inbound messages from other claws.
    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to operational.log.
    Never raises on dispatch failure — logs error and continues.
    """

    def send_deploy_complete(
        self,
        project_id: str,
        deploy_url: str,
        version: str,
        deployed_at: str
    ) -> None: ...
    # Send deploy_complete to Ops Claw
    # Ops Claw uses this to notify the client their feature is live
    # Log: action_type="deploy_complete_sent"

    def send_shipping_summary(
        self,
        week_of: str,
        prs_merged: int,
        issues_resolved: int,
        features_shipped: list[str],
        notable_changes: list[str]
    ) -> None: ...
    # Send shipping_summary to Content Claw — every Friday 17:00
    # Content Claw uses this to draft build-in-public posts
    # ONE message per week accumulating the week's activity
    # Log: action_type="shipping_summary_sent"

    def send_behavior_query(
        self,
        query: str,
        lookback_days: int = 7,
        feature_ids: list[str] | None = None
    ) -> str: ...
    # Send behavior_query to Analytics Claw
    # Returns message_id so response can be correlated
    # Log: action_type="behavior_query_sent"

    def handle_feature_brief(self, message: dict) -> None: ...
    # Receives feature_brief from Ops Claw
    # Validates schema against contracts.py
    # Routes to issue_manager for GitHub issue creation
    # Must send feature_brief_acknowledged within 10 minutes
    # Log: action_type="feature_brief_received"

    def send_feature_brief_acknowledged(
        self,
        project_id: str,
        estimated_start: str,   # ISO timestamp
        clarity_score: str      # "clear" | "low" — flags missing acceptance criteria
    ) -> None: ...
    # Send acknowledgment back to Ops Claw within 10 minutes
    # Log: action_type="feature_brief_acknowledged"

    def handle_retention_signals(self, message: dict) -> None: ...
    # Receives retention_signals from Analytics Claw
    # Stores signal data for sprint planning use
    # Writes to context/sprint/ for IssueManager to read
    # Log: action_type="retention_signals_received"

    def _send(
        self,
        message_type: str,
        recipient_role: str,
        payload: dict
    ) -> None: ...
    # Core send via mesh gateway
    # Includes message_id (UUID), timestamp, sender_role="build"
    # On exception: log error, do not raise
```

Write pytest tests: each send method produces correct message_type and
recipient, feature_brief triggers acknowledged within 10 min timer,
retention_signals stored to sprint context, dispatch failure logged
but not raised, every send logged to operational.log.

---

### TASK 1.3 — Approval Handler

**New file:** `milimo-blueprint/orchestrator/build/approval_handler.py`

```python
from dataclasses import dataclass
from typing import Callable, Literal

@dataclass
class BuildApprovalAction:
    action_id: str
    action_type: str    # sprint_plan, pr_review, pr_merge_hold,
                        # deploy_hold, error_pattern, cost_alert,
                        # security_pr, api_docs, impossible_deadline
    entity_id: str      # pr_id, deploy_id, issue_number, sprint_plan_id
    mode: str           # REVIEW | HOLD | AUTO
    content: dict       # structured context for War Room display
    timestamp: str
    outcome: str | None = None

class BuildApprovalHandler:
    """
    Handles all War Room approval interactions for Build Claw actions.

    TWO SEPARATE TWO-STAGE FLOWS:

    PR Flow:
      Stage 1 — REVIEW: operator reviews PR diff and test results
      REVIEW approve → moves PR to HOLD queue only (does NOT merge)
      Stage 2 — HOLD: operator releases to trigger GitHub merge

    Deploy Flow (independent of PR flow):
      After PR merge, deploy is staged
      Deploy queues its own separate HOLD
      Operator releases deploy HOLD to trigger production deployment
      A merged PR that has not been deployed sits in deploy HOLD
      indefinitely until operator acts — no auto-deploy ever

    If REVIEW approve triggers merge: CRITICAL BUG.
    If PR merge auto-deploys without deploy HOLD: CRITICAL BUG.

    Every decision logged to pr-activity.log or deploy-activity.log.
    """

    def queue_sprint_plan_review(
        self,
        plan_id: str,
        issues: list[dict],
        total_hours: float,
        retention_context: str | None
    ) -> str: ...
    # War Room card shows: issue list, estimated hours, retention rationale
    # Returns action_id

    def queue_pr_review(
        self,
        pr_id: str,
        pr_title: str,
        branch: str,
        issue_number: int,
        files_changed: int,
        lines_added: int,
        lines_removed: int,
        test_result: str,        # "passing" | "failing" | "no_tests"
        tests_count: int,
        github_pr_url: str
    ) -> str: ...
    # War Room card shows full PR summary with test results
    # REVIEW only — does NOT merge on approve

    def queue_pr_merge_hold(
        self,
        pr_id: str,
        pr_title: str,
        github_pr_url: str
    ) -> str: ...
    # Queued ONLY after REVIEW is approved
    # HOLD release triggers GitHub merge
    # War Room card: "Approve REVIEW first" if called without prior REVIEW approve

    def queue_deploy_hold(
        self,
        deploy_id: str,
        version: str,
        deploy_target: str,      # "vercel" | "railway" | "cloudflare"
        changes_summary: list[str]
    ) -> str: ...
    # SEPARATE from PR HOLD — queued after PR is merged
    # War Room card warns: "This will deploy to production"
    # HOLD release triggers deployment API call

    def queue_error_pattern_review(
        self,
        error_id: str,
        error_summary: str,
        occurrence_count: int,
        is_known_pattern: bool,
        auto_patch_available: bool
    ) -> str: ...

    def queue_cost_alert_review(
        self,
        drift_pct: float,
        current_cost: float,
        baseline_cost: float,
        cost_per_user: float
    ) -> str: ...

    def queue_security_pr_review(
        self,
        vuln_id: str,
        package: str,
        severity: str,
        fix_description: str
    ) -> str: ...

    def queue_impossible_deadline_review(
        self,
        project_id: str,
        feature_description: str,
        deadline: str,
        estimated_hours: float,
        available_hours: float
    ) -> str: ...

    def handle_approve(
        self,
        action_id: str,
        next_step_fn: Callable | None = None
    ) -> None: ...
    # For REVIEW approve: call next_step_fn (e.g. queue_pr_merge_hold)
    # For HOLD release: next_step_fn is the actual execution (merge/deploy)
    # Log decision

    def handle_block(self, action_id: str, reason: str | None) -> None: ...
    def handle_hold_release(
        self,
        action_id: str,
        execute_fn: Callable
    ) -> None: ...
    def handle_hold_cancel(self, action_id: str) -> None: ...
    def log_auto(self, action_type: str, entity_id: str, details: dict) -> None: ...
    def log_decision(self, action: BuildApprovalAction, log_path: Path) -> None: ...
```

Write pytest tests: queue_pr_review creates REVIEW (not HOLD),
handle_approve on PR REVIEW calls queue_pr_merge_hold (not merge),
handle_hold_release on PR HOLD calls merge function (not deploy),
queue_deploy_hold is separate from queue_pr_merge_hold,
handle_hold_release on deploy HOLD calls deploy function,
REVIEW approve — verify merge function NOT called (critical test),
all decisions logged, handle_block does not call execute_fn.

---

## PHASE 2 — ISSUE MANAGEMENT
## Complete all Phase 1 tests before starting Phase 2.

---

### TASK 2.1 — Issue Manager

**New file:** `milimo-blueprint/orchestrator/build/issue_manager.py`

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import uuid
import json
from datetime import datetime

@dataclass
class ComplexityScore:
    issue_number: int
    issue_title: str
    complexity_tier: str     # "S" | "M" | "L" | "XL"
    estimated_hours: float   # S=2, M=8, L=20, XL=40 (calibrated over time)
    clarity_score: str       # "clear" | "low"
    missing_elements: list[str]   # acceptance criteria, context, etc.
    scored_at: str

@dataclass
class SprintPlan:
    plan_id: str
    generated_at: str
    approved_at: str | None
    issues: list[ComplexityScore]
    total_estimated_hours: float
    retention_context: str | None    # from Analytics Claw signal
    velocity_calibrated: bool        # True if squad velocity data used
    status: str    # "pending_review" | "approved" | "active" | "completed"

class IssueManager:
    """
    Manages GitHub issue fetching, complexity scoring, and sprint planning.

    Sprint planning flow:
    1. Send behavior_query to Analytics Claw (wait up to 5 min)
    2. Fetch open GitHub issues via API
    3. Score each issue by complexity via inference
    4. Rank by complexity score + retention signal from Analytics
    5. Generate sprint plan and queue as REVIEW
    6. On approval: begin autonomous work on first issue

    No Analytics Claw timeout: after 5 minutes without behavior_query_response,
    proceed with complexity scores only.
    """

    ANALYTICS_WAIT_SECONDS = 300   # 5 minutes

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog
    ): ...

    def generate_sprint_plan(self) -> SprintPlan: ...
    # 1. Send behavior_query via dispatcher
    # 2. Wait up to ANALYTICS_WAIT_SECONDS for response
    # 3. Fetch open issues from GitHub API
    # 4. Score each issue: score_issue_complexity()
    # 5. Read velocity history for calibration
    # 6. Rank: combine complexity + retention signal (if available)
    # 7. Write to context/sprint/backlog-scored.json
    # 8. Build SprintPlan (top issues fitting within velocity estimate)
    # 9. Write to context/sprint/current-plan.json atomically
    # 10. Queue War Room REVIEW via approval_handler
    # 11. Log: action_type="sprint_plan_generated"
    # Return SprintPlan

    def fetch_open_issues(self) -> list[dict]: ...
    # GET /repos/{owner}/{repo}/issues?state=open
    # Filter out PRs (issues without "pull_request" key)
    # Return list of issue dicts from GitHub API
    # Handle rate limiting: exponential backoff 1m, 2m, 4m, max 30m

    def score_issue_complexity(self, issue: dict) -> ComplexityScore: ...
    # Inference call: data_type="issue_complexity_scoring"
    # Prompt: issue title, description, labels, linked PRs
    # Parse output: complexity_tier (S/M/L/XL), estimated_hours
    # Check for acceptance criteria — set clarity_score accordingly
    # Fallback if inference fails: tier="M", hours=8, clarity="low"
    # Log: action_type="issue_scored"

    def handle_feature_brief(
        self,
        client_id: str,
        project_id: str,
        feature_description: str,
        deadline: str,
        acceptance_criteria: str
    ) -> None: ...
    # 1. Create GitHub issue from feature_description + acceptance_criteria
    # 2. Score the new issue
    # 3. Check deadline feasibility against current velocity:
    #    If impossible: flag deadline_risk="high", queue REVIEW immediately
    # 4. Add to context/sprint/backlog-scored.json
    # 5. Send feature_brief_acknowledged via dispatcher (within 10 min)
    # 6. Log: action_type="feature_brief_handled"

    def handle_sprint_plan_approved(self, plan_id: str) -> ComplexityScore: ...
    # Load approved plan from context/sprint/current-plan.json
    # Update status to "active"
    # Return first issue in the plan for code_generator to begin
    # Log: action_type="sprint_plan_approved"

    def update_velocity(
        self,
        estimated_hours: float,
        actual_hours: float,
        sprint_id: str
    ) -> None: ...
    # Append to context/sprint/velocity.json
    # Recalculate avg_hours_per_week and estimation_accuracy_pct
    # Used for future sprint plan calibration

    def _check_deadline_feasibility(
        self,
        estimated_hours: float,
        deadline: str
    ) -> tuple[bool, float]: ...
    # Returns (is_feasible, available_hours)
    # Calculate available hours until deadline from velocity data
    # Feasible if estimated_hours <= available_hours * 0.8 (20% buffer)
```

Write pytest tests: generate_sprint_plan proceeds after 5-min timeout
(mock no Analytics response), GitHub API rate limiting triggers backoff,
issue without acceptance criteria gets clarity_score="low",
feature_brief with impossible deadline queues REVIEW immediately,
velocity update recalculates avg correctly, sprint plan written
atomically to current-plan.json.

---

## PHASE 3 — CODE GENERATION AND PR MANAGEMENT
## Complete all Phase 2 tests before starting Phase 3.

---

### TASK 3.1 — Code Generator

**New file:** `milimo-blueprint/orchestrator/build/code_generator.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class ResolutionResult:
    issue_number: int
    branch_name: str
    files_changed: list[str]
    test_result: str            # "passing" | "failing" | "no_tests"
    tests_passing: int
    tests_failing: int
    attempts: int               # 1–3
    status: str                 # "ready_for_pr" | "failed_after_max_attempts"
    failure_summary: str | None # set if status is failed

@dataclass
class FixAttempt:
    attempt_number: int
    failure_output: str
    analysis: str               # inference analysis of failure
    fix_applied: str            # description of fix attempt

class CodeGenerator:
    """
    Autonomously resolves GitHub issues by generating and testing code.

    Resolution flow:
    1. Read issue details from GitHub API
    2. Read relevant codebase context
    3. Create working branch
    4. Generate implementation via inference (source_code_generation)
    5. Write code to working branch
    6. Run test suite
    7. If tests fail: analyze failure, attempt fix (max 3 attempts)
    8. After 3 failures: escalate to War Room REVIEW
    9. If tests pass: hand off to PRManager

    IMPORTANT: source code always uses data_type="source_code_generation"
    This routes to local NIM in production — never cloud for real code.
    """

    MAX_FIX_ATTEMPTS = 3

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog
    ): ...

    def resolve_issue(self, issue: "ComplexityScore") -> ResolutionResult: ...
    # Full resolution pipeline for one issue
    # Creates branch, generates code, runs tests, handles failures
    # Returns ResolutionResult with final status

    def read_codebase_context(self, issue: dict) -> str: ...
    # Read relevant files from /sandbox/build/repo/
    # Use file paths mentioned in issue, or infer from labels/description
    # Return concatenated context (max ~4000 tokens to fit in prompt)
    # Never read secrets or env files — skip those paths

    def generate_implementation(
        self,
        issue: dict,
        codebase_context: str
    ) -> str: ...
    # Inference: data_type="source_code_generation"
    # Prompt: issue description, acceptance criteria, codebase context
    # Parse: extract code blocks from response
    # Return: implementation as string

    def write_to_branch(
        self,
        branch_name: str,
        implementation: str,
        issue_number: int
    ) -> list[str]: ...
    # Create branch via GitHub API
    # Parse implementation into file changes
    # Apply changes to branch
    # Return list of changed file paths

    def run_tests(self) -> tuple[str, int, int]: ...
    # Run test suite in /sandbox/build/repo/
    # Execute: npm test or pytest depending on project type
    # Parse output: passing count, failing count, failure details
    # Returns: (status, passing_count, failing_count)
    # Timeout: 120 seconds — kill if exceeded

    def analyze_failure_and_fix(
        self,
        branch_name: str,
        failure_output: str,
        attempt_number: int
    ) -> FixAttempt: ...
    # Inference: data_type="code_review"
    # Analyze test failure output, propose fix
    # Apply fix to branch
    # Returns FixAttempt record

    def _create_branch_name(self, issue_number: int) -> str: ...
    # Format: "fix/issue-{number}" or "feature/issue-{number}"
    # Based on issue labels
```

Write pytest tests: resolve_issue returns "ready_for_pr" on passing tests,
resolve_issue returns "failed_after_max_attempts" after 3 failures and
queues REVIEW (not a 4th attempt), codebase_context excludes secret files,
test runner timeout enforced (mock slow test suite), branch name format
correct, inference called with data_type="source_code_generation".

---

### TASK 3.2 — PR Manager

**New file:** `milimo-blueprint/orchestrator/build/pr_manager.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid
from datetime import datetime

@dataclass
class PRRecord:
    pr_id: str
    issue_number: int
    branch_name: str
    title: str
    description: str
    github_pr_number: int | None
    github_pr_url: str | None
    files_changed: int
    lines_added: int
    lines_removed: int
    test_status: str            # "passing" | "failing"
    tests_count: int
    status: str                 # "drafted" | "approved" | "merged" | "blocked"
    review_action_id: str | None
    hold_action_id: str | None
    opened_at: str
    approved_at: str | None
    merged_at: str | None

class PRManager:
    """
    Manages the full PR lifecycle from opening to merge.

    TWO-STAGE APPROVAL (non-negotiable):
    1. PR opened → queued as REVIEW
    2. REVIEW approved → queued as HOLD (NOT merged)
    3. HOLD released → GitHub merge triggered

    Stage 1 REVIEW approval MUST NOT trigger merge.
    Verify this with an explicit test.

    PR conflicts detected at open time and flagged in War Room REVIEW.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        pr_log: "PRActivityLog"
    ): ...

    def open_pr(
        self,
        resolution: "ResolutionResult"
    ) -> PRRecord: ...
    # 1. Generate PR description via inference:
    #    data_type="pr_description_generation"
    #    Prompt: issue details, changes made, test results
    # 2. Create PR on GitHub API
    # 3. Check for conflicts with other open PRs on same files
    # 4. If conflicts found: queue REVIEW with conflict warning
    # 5. Write PRRecord to prs/drafted/{pr_id}.json
    # 6. Queue REVIEW via approval_handler.queue_pr_review()
    # 7. Log to pr-activity.log: pr_opened
    # 8. Return PRRecord

    def handle_review_approved(self, pr_id: str) -> None: ...
    # Called when operator approves Stage 1 REVIEW
    # 1. Load PR from prs/drafted/{pr_id}.json
    # 2. Update status to "approved"
    # 3. Move file: drafted/ → approved/{pr_id}.json
    # 4. Queue HOLD via approval_handler.queue_pr_merge_hold()
    # 5. Log to pr-activity.log: pr_review_approved
    # DO NOT MERGE HERE — HOLD QUEUE ONLY

    def handle_merge_hold_released(self, pr_id: str) -> PRRecord: ...
    # Called when operator releases Stage 2 HOLD
    # THIS IS THE ONLY PLACE A PR IS MERGED
    # 1. Load PR from prs/approved/{pr_id}.json
    # 2. Verify status == "approved" — raise if not
    # 3. Merge PR on GitHub API
    # 4. Update status to "merged", merged_at = now
    # 5. Move file: approved/ → merged/{pr_id}.json
    # 6. Log to pr-activity.log: pr_merged
    # 7. Return merged PRRecord (deploy_manager uses this)

    def handle_review_blocked(self, pr_id: str, reason: str) -> None: ...
    # Move to drafted/ with status "blocked"
    # Log negative signal for future PR quality
    # Log to pr-activity.log: pr_blocked

    def detect_conflicts(
        self,
        branch_name: str,
        files_changed: list[str]
    ) -> list[str]: ...
    # Check all open PRs' changed files against this PR's files
    # Return list of conflicting PR ids

    def get_drafted_prs(self) -> list[PRRecord]: ...
    def get_approved_prs(self) -> list[PRRecord]: ...
    def load_pr(self, pr_id: str, status: str) -> PRRecord: ...
```

Also implement `PRActivityLog`:

```python
class PRActivityLog:
    """Append-only PR event log. Thread-safe."""
    def __init__(self, log_path: Path): ...
    def append(self, event_type: str, pr_id: str, details: dict) -> None: ...
    def get_pr_history(self, pr_id: str) -> list[dict]: ...
```

Write pytest tests: open_pr writes to drafted/ and queues REVIEW,
handle_review_approved moves to approved/ — GitHub merge NOT called
(mock github_client, assert merge not called — critical test),
handle_merge_hold_released calls GitHub merge (assert merge called),
conflict detection returns conflicting PR ids, blocked PR logged,
status validation raises if PR not in expected status.

---

## PHASE 4 — DEPLOYMENT PIPELINE
## Complete all Phase 3 tests before starting Phase 4.

---

### TASK 4.1 — Deploy Manager

**New file:** `milimo-blueprint/orchestrator/build/deploy_manager.py`

```python
from dataclasses import dataclass
from typing import Literal, Any
import uuid
from datetime import datetime

@dataclass
class DeployRecord:
    deploy_id: str
    pr_id: str
    version: str               # semantic version derived from PR + date
    deploy_target: str         # "vercel" | "railway" | "cloudflare"
    changes_summary: list[str] # derived from merged PR descriptions
    status: str                # "staged" | "deployed" | "failed" | "cancelled"
    hold_action_id: str | None
    staged_at: str
    deployed_at: str | None
    deploy_url: str | None
    failure_reason: str | None

class DeployManager:
    """
    Manages the deployment pipeline after PR merge.

    SEPARATE TWO-STAGE FLOW (independent of PR approval):
    1. PR merged → deployment staged automatically
    2. Deploy queued as its own HOLD
    3. HOLD released → deployment triggered via Vercel/Railway API
    4. On success: send deploy_complete to Ops, accumulate for shipping_summary
    5. On failure: queue REVIEW — do NOT retry automatically

    A merged PR that has not been deployed remains in deployments/pending/
    indefinitely until operator acts on the deploy HOLD.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        deploy_log: "DeployActivityLog"
    ): ...

    def stage_deployment(self, merged_pr: "PRRecord") -> DeployRecord: ...
    # Called automatically after PR merge
    # 1. Derive version number (e.g. v1.4.{pr_number})
    # 2. Detect deploy target from build config
    # 3. Collect changes_summary from PR description
    # 4. Create DeployRecord, write to deployments/pending/{deploy_id}.json
    # 5. Queue deploy HOLD via approval_handler.queue_deploy_hold()
    # 6. Log to deploy-activity.log: deploy_staged
    # 7. Return DeployRecord

    def handle_deploy_hold_released(
        self,
        deploy_id: str
    ) -> DeployRecord: ...
    # THIS IS THE ONLY PLACE DEPLOYMENT IS TRIGGERED
    # 1. Load from deployments/pending/{deploy_id}.json
    # 2. Verify status == "staged" — raise if not
    # 3. Call deployment API (Vercel/Railway based on deploy_target)
    # 4. Monitor deployment progress (poll with timeout)
    # 5. On success:
    #    a. Update status to "deployed", deployed_at = now
    #    b. Move: pending/ → history/{deploy_id}.json
    #    c. Send deploy_complete via dispatcher
    #    d. Log to deploy-activity.log: deployed
    # 6. On failure:
    #    a. Update status to "failed", failure_reason = error
    #    b. Keep in pending/ (not moved)
    #    c. Queue War Room REVIEW: "Deployment failed — manual investigation"
    #    d. Log to deploy-activity.log: deploy_failed
    #    e. Do NOT retry automatically
    # 7. Return updated DeployRecord

    def handle_deploy_hold_cancelled(self, deploy_id: str) -> None: ...
    # Keep in pending/ with status "cancelled"
    # No deployment triggered
    # Log: deploy_cancelled

    def _trigger_vercel_deploy(
        self,
        deploy_id: str
    ) -> tuple[bool, str]: ...
    # POST to Vercel deployment API
    # Poll deployment status until done or timeout (5 min)
    # Returns (success, deploy_url)

    def _trigger_railway_deploy(
        self,
        deploy_id: str
    ) -> tuple[bool, str]: ...
    # POST to Railway deployment API
    # Poll deployment status
    # Returns (success, deploy_url)

    def get_pending_deployments(self) -> list[DeployRecord]: ...
```

Also implement `DeployActivityLog`:

```python
class DeployActivityLog:
    """Append-only deploy event log. Thread-safe."""
    def __init__(self, log_path: Path): ...
    def append(self, event_type: str, deploy_id: str, details: dict) -> None: ...
```

Write pytest tests: stage_deployment creates HOLD (not deployed),
handle_deploy_hold_released calls Vercel/Railway API (mock),
successful deploy sends deploy_complete and moves to history/,
failed deploy queues REVIEW and stays in pending/ (no retry),
cancelled deploy stays in pending/ — no API call,
deploy is NOT triggered by PR merge (verify no deploy on PR HOLD release).

---

## PHASE 5 — MONITORING AND DOCUMENTATION
## Complete all Phase 4 tests before starting Phase 5.

---

### TASK 5.1 — Error Monitor

**New file:** `milimo-blueprint/orchestrator/build/error_monitor.py`

```python
from dataclasses import dataclass, field
from typing import Any
import uuid
from datetime import datetime

@dataclass
class ErrorEvent:
    event_id: str
    timestamp: str
    error_type: str
    message: str
    stack_trace: str
    occurrence_count: int
    affected_users: int

@dataclass
class ErrorGroup:
    group_id: str
    root_cause: str
    error_count: int
    events: list[ErrorEvent]
    first_seen: str
    last_seen: str

@dataclass
class ErrorPattern:
    pattern_id: str
    root_cause: str
    fix_template: str      # reusable fix approach
    times_applied: int
    success_rate: float

class ErrorMonitor:
    """
    Monitors production errors via Sentry API every 30 minutes.

    For known patterns: auto-draft patch PR, queue as REVIEW.
    For new patterns: write to context/errors/active/, queue REVIEW.
    Patterns accumulate in context/errors/patterns/ over time.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        sentry_client: Any,
        code_generator: "CodeGenerator",
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog
    ): ...

    def run_monitoring_pass(self) -> list[ErrorGroup]: ...
    # 1. Fetch recent errors from Sentry API (last 30 min)
    # 2. Group by root cause: group_by_root_cause()
    # 3. For each group: check_known_patterns()
    # 4. Known pattern: auto-draft patch → queue REVIEW
    # 5. New pattern: save to active/, queue REVIEW
    # 6. Log: action_type="error_monitoring_pass"
    # Return all groups found

    def fetch_recent_errors(self) -> list[ErrorEvent]: ...
    # GET from Sentry API
    # Filter to errors in last 30 minutes
    # Return list of ErrorEvent

    def group_by_root_cause(
        self,
        errors: list[ErrorEvent]
    ) -> list[ErrorGroup]: ...
    # Stack trace similarity clustering
    # Group errors that share root cause (same error type + location)
    # Return list of ErrorGroup

    def check_known_patterns(
        self,
        group: ErrorGroup
    ) -> ErrorPattern | None: ...
    # Scan context/errors/patterns/
    # Match by root_cause similarity
    # Return matching pattern or None

    def auto_draft_patch(
        self,
        group: ErrorGroup,
        pattern: ErrorPattern
    ) -> None: ...
    # Use fix_template from pattern
    # Generate patch via code_generator
    # Queue as REVIEW (not AUTO — patch must be reviewed)

    def save_new_pattern(self, group: ErrorGroup) -> str: ...
    # Write to context/errors/active/{group_id}.json
    # Queue War Room REVIEW: "New error pattern detected"
    # Return group_id

    def promote_to_known_pattern(
        self,
        group_id: str,
        fix_template: str
    ) -> None: ...
    # Called after operator confirms a fix
    # Move from active/ to patterns/
    # Increment times_applied
```

Write pytest tests: monitoring pass fetches and groups errors, known pattern
triggers auto-draft patch queued as REVIEW, new pattern saved to active/
and queued as REVIEW, grouping correctly clusters same root cause, pattern
file written to correct path.

---

### TASK 5.2 — Cost Monitor

**New file:** `milimo-blueprint/orchestrator/build/cost_monitor.py`

```python
from dataclasses import dataclass
from typing import Any
from datetime import datetime

@dataclass
class UsageData:
    week_of: str
    total_tokens: int
    total_cost_usd: float
    cost_by_model: dict[str, float]
    calls_by_data_type: dict[str, int]

@dataclass
class DriftResult:
    current_cost: float
    baseline_cost: float
    drift_pct: float
    is_alert: bool       # True if drift > 15%
    cost_per_user: float | None

class CostMonitor:
    """
    Tracks inference API costs daily and alerts on significant drift.

    Reads usage from inference provider APIs.
    Compares against 4-week rolling baseline.
    Queues War Room REVIEW if drift > 15%.
    Updates context/costs/inference-weekly.json.
    Appends to context/costs/inference-history.jsonl.
    """

    ALERT_DRIFT_THRESHOLD = 0.15   # 15%

    def run_daily_check(self) -> DriftResult: ...
    # 1. Fetch current week API usage
    # 2. Calculate total cost and cost_per_user
    # 3. Load baseline from inference-history.jsonl (4-week avg)
    # 4. Calculate drift
    # 5. If drift > 15%: queue War Room REVIEW
    # 6. Update inference-weekly.json
    # 7. Append to inference-history.jsonl
    # Return DriftResult

    def fetch_api_usage(self) -> UsageData: ...
    # Read from NVIDIA API usage endpoint
    # Or infer from local call logs (data_type tracking)
    # Return UsageData for current week

    def calculate_baseline(self) -> float: ...
    # Read last 4 weeks from inference-history.jsonl
    # Return average weekly cost
    # Return 0.0 if fewer than 2 weeks of history

    def queue_cost_alert(self, drift: DriftResult) -> None: ...
    # Queue War Room REVIEW with drift details
    # Log to cost-alerts.log

    def get_cost_per_user(
        self,
        total_cost: float
    ) -> float | None: ...
    # Try to get user count from Analytics Claw weekly report
    # Returns None if Analytics report not available
```

Write pytest tests: drift > 15% triggers alert, drift < 15% no alert,
baseline calculation from 4-week history, cost-per-user returns None
when Analytics data unavailable, cost-alerts.log written on alert.

---

### TASK 5.3 — Dependency Auditor

**New file:** `milimo-blueprint/orchestrator/build/dependency_auditor.py`

```python
from dataclasses import dataclass
from typing import Literal, Any

@dataclass
class Vulnerability:
    package: str
    ecosystem: str        # "npm" | "pypi"
    current_version: str
    vulnerable_versions: str
    patched_version: str | None
    severity: str         # "low" | "medium" | "high" | "critical"
    cve_id: str | None
    fix_complexity: str   # "simple" | "breaking_change" | "no_fix"

class DependencyAuditor:
    """
    Weekly dependency security audit (Monday 08:00).

    Simple fix path (non-breaking version bump): auto-draft PR → REVIEW
    Breaking change or no fix: queue REVIEW for manual investigation.
    All PRs from auditor are security-labelled — REVIEW, not AUTO.
    """

    def run_audit(self) -> list[Vulnerability]: ...
    # 1. Detect project type (npm, Python, or both)
    # 2. Run npm audit or pip-audit against package files
    # 3. Parse output into Vulnerability list
    # 4. For each: assess_fix_complexity()
    # 5. Simple fixes: auto_draft_security_pr() → queue REVIEW
    # 6. Complex/no-fix: queue_manual_investigation()
    # Log: action_type="dependency_audit_complete"

    def assess_fix_complexity(
        self,
        vuln: Vulnerability
    ) -> str: ...
    # "simple": patched_version exists, no breaking change in changelog
    # "breaking_change": major version bump required
    # "no_fix": no patched_version available

    def auto_draft_security_pr(
        self,
        vulns: list[Vulnerability]
    ) -> None: ...
    # Batch simple fixes into one PR
    # Bump versions in package.json or requirements.txt
    # Queue as REVIEW — never AUTO for security changes

    def queue_manual_investigation(
        self,
        vuln: Vulnerability
    ) -> None: ...
    # Queue War Room REVIEW with CVE details and manual steps
```

Write pytest tests: simple fix auto-drafts PR queued as REVIEW,
breaking change queues REVIEW for manual investigation, no-fix queues
REVIEW, multiple simple fixes batched into single PR, security PR
is REVIEW not AUTO.

---

### TASK 5.4 — Documentation Maintainer

**New file:** `milimo-blueprint/orchestrator/build/doc_maintainer.py`

```python
from typing import Any
from pathlib import Path
from datetime import datetime

class DocMaintainer:
    """
    Maintains project documentation autonomously.

    Changelog: updated on every merged PR (AUTO — no approval)
    API docs: updated on PRs touching API routes (REVIEW)
    Weekly devlog: generated Friday 17:00, sent to Content Claw
    All documentation inference logs data_type.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog
    ): ...

    def update_changelog(self, merged_pr: "PRRecord") -> None: ...
    # Generate changelog entry via inference:
    #   data_type="changelog_generation"
    # Append to docs/changelog.md
    # Log_auto (no approval needed)
    # Log: action_type="changelog_updated"

    def update_api_docs(self, merged_pr: "PRRecord") -> None: ...
    # Check if PR touches API route files
    # If yes: generate updated docs via inference:
    #   data_type="api_documentation_generation"
    # Write to docs/api-reference/
    # Queue REVIEW — operator confirms accuracy
    # Log: action_type="api_docs_updated"

    def generate_weekly_devlog(self) -> str: ...
    # Aggregate all merged PRs, deploys, resolved issues for the week
    # Generate devlog draft via inference:
    #   data_type="devlog_draft_generation"
    # Write to docs/devlog/week-{date}.md
    # Build shipping_summary for Content Claw
    # Send shipping_summary via dispatcher
    # Log: action_type="devlog_generated"
    # Return devlog draft text

    def _detect_api_routes_changed(
        self,
        files_changed: list[str]
    ) -> bool: ...
    # Check if any changed file is in api/, routes/, or handlers/ dirs
    # Or contains "router", "endpoint", "route" in filename

    def _build_shipping_summary(
        self,
        merged_prs: list["PRRecord"],
        deploys: list["DeployRecord"]
    ) -> dict: ...
    # Aggregate week's activity into shipping_summary payload
    # Including: prs_merged, issues_resolved, features_shipped, notable_changes
```

Write pytest tests: changelog appended (not overwritten) on each PR,
API docs update only when API routes changed, devlog sends
shipping_summary to Content Claw, shipping_summary contains correct
week's data, changelog inference uses data_type="changelog_generation".

---

## PHASE 6 — SCHEDULER AND ENTRY POINT
## Complete all Phase 5 tests before starting Phase 6.

---

### TASK 6.1 — Build Scheduler

**New file:** `milimo-blueprint/orchestrator/build/build_scheduler.py`

```python
import threading
from datetime import datetime, timedelta
from typing import Callable

class BuildScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Build Claw.

    Schedule:
      Every 30 min — Error monitoring pass
      Daily         — Cost monitoring check
      Monday 08:00  — Dependency security audit
      Friday 17:00  — Weekly devlog generation + shipping_summary
      Sunday 02:00  — Self-evolution cycle (shared evolution_cycle.py)

    Uses threading.Timer. No cron. No APScheduler. Only stdlib.
    Checks for missed jobs on startup.
    """

    def __init__(
        self,
        error_monitor: "ErrorMonitor",
        cost_monitor: "CostMonitor",
        dependency_auditor: "DependencyAuditor",
        doc_maintainer: "DocMaintainer",
        operational_log: BuildOperationalLog
    ): ...

    def start(self) -> None: ...
    # Initialize all scheduled timers
    # Check for missed jobs
    # Log: action_type="scheduler_started"

    def stop(self) -> None: ...
    # Cancel all pending timers
    # Log: action_type="scheduler_stopped"

    def _run_error_monitoring(self) -> None: ...
    # error_monitor.run_monitoring_pass()
    # Reschedule for 30 minutes from now

    def _run_cost_monitoring(self) -> None: ...
    def _run_dependency_audit(self) -> None: ...   # Monday 08:00 only
    def _run_devlog_generation(self) -> None: ...  # Friday 17:00 only

    def _check_missed_jobs(self) -> None: ...
    # error_monitoring: last run > 35 minutes ago → run immediately
    # cost_monitoring: last run > 25 hours ago → run immediately
    # dependency_audit: last run > 8 days ago → run immediately
    # devlog_generation: last run > 8 days ago → run immediately

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None
    ) -> float: ...
    # Returns seconds until next occurrence of target time
    # target_weekday: 0=Monday, 4=Friday, 6=Sunday

    def _is_monday(self) -> bool: ...
    def _is_friday(self) -> bool: ...
```

Write pytest tests: error monitoring runs every 30 min (verify via mock),
Monday audit fires only on Monday, Friday devlog fires only on Friday,
missed error monitoring triggers on startup, missed audit triggers on
startup when last run > 8 days, self-rescheduling verified.

---

### TASK 6.2 — Build Claw Main Entry Point

**New file:** `milimo-blueprint/orchestrator/build/build_claw.py`

```python
from typing import Any

class BuildClaw:
    """
    Main entry point for the Build Claw.
    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(
        self,
        squad_id: str,
        inference_client: Any,
        github_client: Any,
        sentry_client: Any | None = None,   # optional — monitoring only
        vercel_client: Any | None = None,    # optional — depends on deploy target
        railway_client: Any | None = None    # optional — depends on deploy target
    ): ...

    def startup(self) -> None: ...
    # 1. Run filesystem init — validate structure
    # 2. Log startup to operational.log
    # 3. Initialize all components with shared dependencies
    # 4. Register inbound message handlers with mesh router:
    #    - feature_brief → dispatcher.handle_feature_brief
    #    - retention_signals → dispatcher.handle_retention_signals
    #    - behavior_query_response → issue_manager (resume sprint planning)
    # 5. Register approval flow handlers with War Room:
    #    - sprint_plan REVIEW approve → issue_manager.handle_sprint_plan_approved
    #    - pr REVIEW approve → pr_manager.handle_review_approved
    #    - pr HOLD release → pr_manager.handle_merge_hold_released
    #      + deploy_manager.stage_deployment (chained after merge)
    #    - deploy HOLD release → deploy_manager.handle_deploy_hold_released
    #    - deploy HOLD cancel → deploy_manager.handle_deploy_hold_cancelled
    #    - pr REVIEW block → pr_manager.handle_review_blocked
    # 6. Start build_scheduler
    # 7. Log: action_type="claw_started"

    def shutdown(self) -> None: ...
    # Stop scheduler cleanly
    # Log: action_type="claw_stopped"

    def handle_inbound(self, raw_message: dict) -> None: ...
    # Route inbound message to correct handler
    # Log receipt to operational.log
    # Catch all exceptions — never crash on bad input
```

---

### TASK 6.3 — Integration Test Suite (15-Step MVR)

**New file:** `milimo-blueprint/tests/test_build_integration.py`

```python
class TestBuildMVR:

    def test_mvr_01_github_credentials_configured(self):
        """GitHub token and test repo configured from environment."""

    def test_mvr_02_fetch_open_issues(self):
        """Build Claw fetches open issues from configured test repo."""

    def test_mvr_03_sprint_plan_generated(self):
        """Sprint plan generated — proceeds without Analytics after 5 min."""

    def test_mvr_04_sprint_plan_in_war_room_as_review(self):
        """Sprint plan queued as REVIEW — not AUTO, not HOLD."""

    def test_mvr_05_approve_sprint_plan(self):
        """Sprint plan approved — Build Claw begins work on Issue #1."""

    def test_mvr_06_pr_opened_on_github(self):
        """Confirm PR is opened on GitHub test repository."""

    def test_mvr_07_pr_in_war_room_as_review(self):
        """PR queued as REVIEW in War Room."""

    def test_mvr_08_pr_review_approve_creates_hold_not_merge(self):
        """
        CRITICAL TEST: Approving PR REVIEW must NOT merge the PR.
        PR must move to HOLD queue only.
        Assert github_client.merge_pull_request call_count == 0
        after REVIEW approve.
        """

    def test_mvr_09_pr_hold_release_triggers_github_merge(self):
        """HOLD release triggers GitHub merge (not PR REVIEW approve)."""

    def test_mvr_10_deploy_staged_after_merge(self):
        """Deploy staging record created in deployments/pending/ after merge."""

    def test_mvr_11_deploy_in_war_room_as_hold(self):
        """Deploy queued as its OWN HOLD — separate from PR HOLD."""

    def test_mvr_12_deploy_hold_release_triggers_deployment(self):
        """Deploy HOLD release triggers Vercel/Railway API (mocked)."""

    def test_mvr_13_deploy_complete_sent_to_ops(self):
        """deploy_complete message dispatched to Ops Claw after success."""

    def test_mvr_14_deploy_failure_queues_review_no_retry(self):
        """Failed deploy queues REVIEW — deployment NOT retried automatically."""

    def test_mvr_15_shipping_summary_accumulates_for_friday(self):
        """Merged PR data accumulates in devlog context for Friday dispatch."""
```

Test 8 is the most critical test in the entire Build Claw suite.
It must explicitly assert that GitHub `merge_pull_request` was NOT
called after Stage 1 REVIEW approval. Use a mock github_client and
verify call_count == 0 at Stage 1, then > 0 at Stage 2 (Test 9).

---

## FINAL VERIFICATION CHECKLIST

□ /sandbox/build/ full directory structure created on build_init
□ All log files created (operational, pr-activity, deploy-activity, cost-alerts)
□ All context JSON files initialized with empty/default content
□ docs/changelog.md created with header
□ Filesystem init is idempotent — no errors on repeated calls
□ Sprint plan generated without Analytics after 5-minute timeout
□ Sprint plan queued as REVIEW (not AUTO, not HOLD)
□ Sprint plan approved → Build Claw begins working on Issue #1
□ Issue without acceptance criteria gets clarity_score="low"
□ Impossible deadline in feature_brief queues REVIEW immediately
□ feature_brief_acknowledged sent within 10 minutes
□ PR opened on GitHub and queued as REVIEW
□ REVIEW approve → PR moves to HOLD — GitHub merge NOT triggered
□ HOLD release → GitHub merge triggered (the only merge path)
□ Deploy staged in pending/ after PR merge
□ Deploy queued as its own separate HOLD
□ Deploy HOLD release → deployment API called
□ Successful deploy: deploy_complete sent to Ops, record in history/
□ Failed deploy: REVIEW queued, no auto-retry, stays in pending/
□ PR conflict detected and flagged in REVIEW card
□ GitHub rate limiting: exponential backoff (1, 2, 4, max 30 min)
□ Test failure after 3 attempts → REVIEW (no 4th attempt)
□ Error monitoring runs every 30 minutes
□ Known error pattern → auto-draft patch queued as REVIEW
□ New error pattern → saved to active/, queued as REVIEW
□ Cost drift > 15% → REVIEW alert queued
□ Cost drift ≤ 15% → no alert
□ Monday audit auto-drafts simple security PRs as REVIEW
□ Breaking change vulnerabilities queued for manual investigation
□ Changelog appended (not overwritten) on every merged PR
□ API docs update fires only when API routes changed
□ Friday devlog generates and sends shipping_summary to Content Claw
□ Shipping summary is one message per week (accumulated, not per PR)
□ All inbound message types wired to correct handlers
□ Scheduler detects missed jobs on startup and recovers
□ data_type logged on every inference call (cloud during dev)
□ All 15 MVR integration tests pass
□ Test 8 explicitly asserts zero GitHub merge calls on REVIEW approve
□ Test 9 asserts GitHub merge called on HOLD release
□ Test 11 confirms deploy HOLD is separate from PR HOLD
□ All unit tests pass: pytest milimo-blueprint/orchestrator/build/

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  File: [exact path — NEW]
  Summary: [one sentence]

  [complete implementation — no TODOs, no stubs, no placeholders]

  Tests: [complete pytest file immediately after]
  -----------------------------------------

Begin with Task 1.1. Do not proceed to 1.2 until 1.1 tests pass.
Do not proceed to Phase 2 until all Phase 1 tests pass.
The spec is ground truth. All inference to cloud. Log data_type on every call.
Use a GitHub test repository — never a live production repo.
Two separate two-stage approvals: PR merge and production deploy are
independent HOLD queues. This is the most critical correctness requirement.
