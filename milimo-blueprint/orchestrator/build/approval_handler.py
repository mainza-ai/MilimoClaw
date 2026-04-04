"""
Build Claw approval handler.

Implements two-stage approval flow:
1. REVIEW — operator reviews PR, approves → queues HOLD (does NOT merge)
2. HOLD — operator releases HOLD → merge happens
3. Deploy HOLD — separate from PR HOLD, operator releases → deploy happens

Enhancement: File-based task dependency storage (from OmO).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from build.build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry

logger = logging.getLogger(__name__)


@dataclass
class BuildApprovalAction:
    action_id: str
    action_type: str
    mode: str  # "REVIEW" or "HOLD"
    entity_id: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    next_step_fn: Callable | None = field(default=None, repr=False)
    execute_fn: Callable | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ApprovalResult:
    executed: bool
    decision: str
    action_id: str
    details: dict[str, Any] = field(default_factory=dict)


class PRActivityLog:
    """Append-only PR event log."""

    def __init__(self, log_path: Any) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event_type: str, pr_id: str, details: dict) -> None:
        import fcntl
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "pr_id": pr_id,
            "details": details,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_pr_history(self, pr_id: str) -> list[dict]:
        if not self.log_path.exists():
            return []
        history: list[dict] = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("pr_id") == pr_id:
                        history.append(data)
                except (json.JSONDecodeError, KeyError):
                    continue
        return history


class DeployActivityLog:
    """Append-only deploy event log."""

    def __init__(self, log_path: Any) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event_type: str, deploy_id: str, details: dict) -> None:
        import fcntl
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "deploy_id": deploy_id,
            "details": details,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class BuildApprovalHandler:
    """Manages two-stage approval workflow for PRs and deployments."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        operational_log: BuildOperationalLog,
        pr_log: PRActivityLog,
        deploy_log: DeployActivityLog,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._pr_log = pr_log
        self._deploy_log = deploy_log
        self._pending_actions: dict[str, BuildApprovalAction] = {}

    # ------------------------------------------------------------------
    # PR REVIEW (Stage 1)
    # ------------------------------------------------------------------

    def queue_pr_review(
        self,
        pr_id: str,
        pr_title: str,
        branch: str,
        issue_number: int,
        files_changed: int,
        lines_added: int,
        lines_removed: int,
        test_result: str,
        tests_count: int,
        github_pr_url: str,
    ) -> str:
        action_id = f"pr-review-{pr_id}"
        action = BuildApprovalAction(
            action_id=action_id,
            action_type="pr_review",
            mode="REVIEW",
            entity_id=pr_id,
            summary=f"Review PR #{issue_number}: {pr_title}",
            metadata={
                "pr_id": pr_id,
                "pr_title": pr_title,
                "branch": branch,
                "issue_number": issue_number,
                "files_changed": files_changed,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "test_result": test_result,
                "tests_count": tests_count,
                "github_pr_url": github_pr_url,
            },
        )
        self._pending_actions[action_id] = action
        self._pr_log.append("review_queued", pr_id, {"title": pr_title})
        self._log.append(BuildLogEntry(
            timestamp=action.created_at,
            action_type="pr_review_queued",
            entity_id=pr_id,
            outcome="queued",
            details={"pr_id": pr_id, "mode": "REVIEW"},
        ))
        return action_id

    # ------------------------------------------------------------------
    # PR MERGE HOLD (Stage 2)
    # ------------------------------------------------------------------

    def queue_pr_merge_hold(
        self,
        pr_id: str,
        pr_title: str,
        github_pr_url: str,
    ) -> str:
        action_id = f"pr-merge-hold-{pr_id}"
        action = BuildApprovalAction(
            action_id=action_id,
            action_type="pr_merge_hold",
            mode="HOLD",
            entity_id=pr_id,
            summary=f"Hold merge for PR: {pr_title}",
            metadata={
                "pr_id": pr_id,
                "pr_title": pr_title,
                "github_pr_url": github_pr_url,
            },
        )
        self._pending_actions[action_id] = action
        self._pr_log.append("hold_queued", pr_id, {"title": pr_title})
        self._log.append(BuildLogEntry(
            timestamp=action.created_at,
            action_type="pr_merge_hold_queued",
            entity_id=pr_id,
            outcome="queued",
            details={"pr_id": pr_id, "mode": "HOLD"},
        ))
        return action_id

    # ------------------------------------------------------------------
    # Deploy HOLD (separate from PR HOLD)
    # ------------------------------------------------------------------

    def queue_deploy_hold(
        self,
        deploy_id: str,
        version: str,
        deploy_target: str,
        changes_summary: list[str],
    ) -> str:
        action_id = f"deploy-hold-{deploy_id}"
        action = BuildApprovalAction(
            action_id=action_id,
            action_type="deploy_hold",
            mode="HOLD",
            entity_id=deploy_id,
            summary=f"Hold deployment {version} to {deploy_target}",
            metadata={
                "deploy_id": deploy_id,
                "version": version,
                "deploy_target": deploy_target,
                "changes_summary": changes_summary,
            },
        )
        self._pending_actions[action_id] = action
        self._deploy_log.append("hold_queued", deploy_id, {"version": version})
        self._log.append(BuildLogEntry(
            timestamp=action.created_at,
            action_type="deploy_hold_queued",
            entity_id=deploy_id,
            outcome="queued",
            details={"deploy_id": deploy_id, "mode": "HOLD"},
        ))
        return action_id

    # ------------------------------------------------------------------
    # Sprint plan review
    # ------------------------------------------------------------------

    def queue_sprint_plan_review(
        self,
        plan_id: str,
        issues: list[dict],
        total_hours: float,
        retention_context: dict | None = None,
    ) -> str:
        action_id = f"sprint-plan-{plan_id}"
        action = BuildApprovalAction(
            action_id=action_id,
            action_type="sprint_plan",
            mode="REVIEW",
            entity_id=plan_id,
            summary=f"Review sprint plan: {len(issues)} issues, {total_hours}h",
            metadata={
                "plan_id": plan_id,
                "issues": issues,
                "total_hours": total_hours,
                "retention_context": retention_context,
            },
        )
        self._pending_actions[action_id] = action
        self._log.append(BuildLogEntry(
            timestamp=action.created_at,
            action_type="sprint_plan_queued",
            entity_id=plan_id,
            outcome="queued",
            details={"plan_id": plan_id, "total_hours": total_hours},
        ))
        return action_id

    # ------------------------------------------------------------------
    # Security PR review
    # ------------------------------------------------------------------

    def queue_security_pr(
        self,
        pr_id: str,
        vulns: list[dict],
        summary: str,
    ) -> str:
        action_id = f"security-pr-{pr_id}"
        action = BuildApprovalAction(
            action_id=action_id,
            action_type="security_pr",
            mode="REVIEW",
            entity_id=pr_id,
            summary=summary,
            metadata={"pr_id": pr_id, "vulns": vulns},
        )
        self._pending_actions[action_id] = action
        self._log.append(BuildLogEntry(
            timestamp=action.created_at,
            action_type="security_pr_queued",
            entity_id=pr_id,
            outcome="queued",
            details={"pr_id": pr_id},
        ))
        return action_id

    # ------------------------------------------------------------------
    # Dependency review
    # ------------------------------------------------------------------

    def queue_dependency_review(
        self,
        review_id: str,
        findings: list[dict],
        summary: str,
    ) -> str:
        action_id = f"dependency-review-{review_id}"
        action = BuildApprovalAction(
            action_id=action_id,
            action_type="dependency_review",
            mode="REVIEW",
            entity_id=review_id,
            summary=summary,
            metadata={"review_id": review_id, "findings": findings},
        )
        self._pending_actions[action_id] = action
        self._log.append(BuildLogEntry(
            timestamp=action.created_at,
            action_type="dependency_review_queued",
            entity_id=review_id,
            outcome="queued",
            details={"review_id": review_id},
        ))
        return action_id

    # ------------------------------------------------------------------
    # Decision handlers
    # ------------------------------------------------------------------

    def handle_approve(
        self,
        action_id: str,
        next_step_fn: Callable | None = None,
    ) -> ApprovalResult:
        action = self._pending_actions.get(action_id)
        if action is None:
            return ApprovalResult(
                executed=False,
                decision="error",
                action_id=action_id,
                details={"error": f"Action {action_id} not found"},
            )

        if action.mode == "REVIEW":
            if next_step_fn:
                next_step_fn()
            self._log.append(BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type=f"{action.action_type}_approved",
                entity_id=action.entity_id,
                outcome="approved",
                details={"action_id": action_id},
            ))
            del self._pending_actions[action_id]
            return ApprovalResult(
                executed=True,
                decision="approved",
                action_id=action_id,
                details={"mode": "REVIEW"},
            )

        elif action.mode == "HOLD":
            # HOLD approval means release the hold
            return self.handle_hold_release(action_id, execute_fn=action.execute_fn)

        return ApprovalResult(
            executed=False,
            decision="error",
            action_id=action_id,
            details={"error": "Unknown action type"},
        )

    def handle_hold_release(
        self,
        action_id: str,
        execute_fn: Callable | None = None,
    ) -> ApprovalResult:
        action = self._pending_actions.get(action_id)
        if action is None:
            return ApprovalResult(
                executed=False,
                decision="error",
                action_id=action_id,
                details={"error": f"Action {action_id} not found"},
            )

        if action.mode != "HOLD":
            return ApprovalResult(
                executed=False,
                decision="error",
                action_id=action_id,
                details={"error": f"Action {action_id} is not in HOLD mode"},
            )

        result = None
        if execute_fn:
            result = execute_fn()

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=f"{action.action_type}_released",
            entity_id=action.entity_id,
            outcome="released",
            details={"action_id": action_id},
        ))
        del self._pending_actions[action_id]
        return ApprovalResult(
            executed=True,
            decision="released",
            action_id=action_id,
            details={"result": result},
        )

    def handle_block(self, action_id: str, reason: str = "") -> ApprovalResult:
        action = self._pending_actions.pop(action_id, None)
        if action is None:
            return ApprovalResult(
                executed=False,
                decision="error",
                action_id=action_id,
                details={"error": f"Action {action_id} not found"},
            )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=f"{action.action_type}_blocked",
            entity_id=action.entity_id,
            outcome="blocked",
            details={"reason": reason},
        ))
        return ApprovalResult(
            executed=False,
            decision="blocked",
            action_id=action_id,
            details={"reason": reason},
        )

    def handle_hold_cancel(self, action_id: str) -> ApprovalResult:
        action = self._pending_actions.pop(action_id, None)
        if action is None:
            return ApprovalResult(
                executed=False,
                decision="error",
                action_id=action_id,
                details={"error": f"Action {action_id} not found"},
            )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=f"{action.action_type}_cancelled",
            entity_id=action.entity_id,
            outcome="cancelled",
            details={},
        ))
        return ApprovalResult(
            executed=False,
            decision="cancelled",
            action_id=action_id,
            details={},
        )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_pending_action(self, action_id: str) -> BuildApprovalAction | None:
        return self._pending_actions.get(action_id)

    def get_pending_actions_by_type(self, action_type: str) -> list[BuildApprovalAction]:
        return [
            a for a in self._pending_actions.values()
            if a.action_type == action_type
        ]

    def get_all_pending_actions(self) -> list[BuildApprovalAction]:
        return list(self._pending_actions.values())
