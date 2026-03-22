#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Approval Handler

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

If REVIEW approve triggers merge: CRITICAL BUG.
If PR merge auto-deploys without deploy HOLD: CRITICAL BUG.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal

if TYPE_CHECKING:
    from .build_init import BuildFilesystemInit, BuildOperationalLog

logger = logging.getLogger("milimo.build")


@dataclass
class BuildApprovalAction:
    """Represents an action pending War Room approval."""

    action_id: str
    action_type: str
    entity_id: str
    mode: str
    content: dict[str, Any]
    timestamp: str
    outcome: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "entity_id": self.entity_id,
            "mode": self.mode,
            "content": self.content,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildApprovalAction:
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            entity_id=data["entity_id"],
            mode=data["mode"],
            content=data["content"],
            timestamp=data["timestamp"],
            outcome=data.get("outcome"),
        )


@dataclass
class ApprovalResult:
    """Result of an approval decision."""

    action_id: str
    decision: str
    executed: bool
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


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

    If REVIEW approve triggers merge: CRITICAL BUG.
    If PR merge auto-deploys without deploy HOLD: CRITICAL BUG.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        operational_log: BuildOperationalLog,
        pr_log: PRActivityLog | None = None,
        deploy_log: DeployActivityLog | None = None,
        war_room: Any | None = None,
    ):
        self._fs = fs
        self._log = operational_log
        self._pr_log = pr_log
        self._deploy_log = deploy_log
        self._war_room = war_room
        self._pending_actions: dict[str, BuildApprovalAction] = {}
        self._review_approved_callbacks: dict[str, Callable[[], None]] = {}
        self._hold_release_callbacks: dict[str, Callable[[], Any]] = {}

    def queue_sprint_plan_review(
        self,
        plan_id: str,
        issues: list[dict],
        total_hours: float,
        retention_context: str | None,
    ) -> str:
        action_id = f"sprint-{uuid.uuid4().hex[:8]}"
        content = {
            "plan_id": plan_id,
            "issues": issues,
            "total_estimated_hours": total_hours,
            "retention_context": retention_context,
            "card_title": f"Sprint Plan — {len(issues)} issues, {total_hours:.1f}h estimated",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="sprint_plan",
            entity_id=plan_id,
            mode="REVIEW",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="sprint_plan_queued",
                entity_id=plan_id,
                outcome="pending",
                details={"total_hours": total_hours, "issue_count": len(issues)},
            )
        )

        return action_id

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
        action_id = f"pr-review-{uuid.uuid4().hex[:8]}"
        content = {
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
            "card_title": f"PR #{pr_id} — {pr_title}",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="pr_review",
            entity_id=pr_id,
            mode="REVIEW",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="pr_review_queued",
                entity_id=pr_id,
                outcome="pending",
                details={"test_result": test_result, "files_changed": files_changed},
            )
        )

        if self._pr_log:
            self._pr_log.append("review_queued", pr_id, {
                "action_id": action_id,
                "branch": branch,
                "issue_number": issue_number,
            })

        return action_id

    def queue_pr_merge_hold(
        self,
        pr_id: str,
        pr_title: str,
        github_pr_url: str,
    ) -> str:
        action_id = f"pr-hold-{uuid.uuid4().hex[:8]}"
        content = {
            "pr_id": pr_id,
            "pr_title": pr_title,
            "github_pr_url": github_pr_url,
            "card_title": f"PR #{pr_id} — Ready to Merge",
            "warning": "Release HOLD to merge this PR. This action cannot be undone.",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="pr_merge_hold",
            entity_id=pr_id,
            mode="HOLD",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="pr_merge_hold_queued",
                entity_id=pr_id,
                outcome="pending",
                details={"pr_title": pr_title},
            )
        )

        if self._pr_log:
            self._pr_log.append("hold_queued", pr_id, {
                "action_id": action_id,
                "pr_title": pr_title,
            })

        return action_id

    def queue_deploy_hold(
        self,
        deploy_id: str,
        version: str,
        deploy_target: str,
        changes_summary: list[str],
    ) -> str:
        action_id = f"deploy-{uuid.uuid4().hex[:8]}"
        content = {
            "deploy_id": deploy_id,
            "version": version,
            "deploy_target": deploy_target,
            "changes_summary": changes_summary,
            "card_title": f"Deploy {version} to {deploy_target}",
            "warning": "This will deploy to production.",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="deploy_hold",
            entity_id=deploy_id,
            mode="HOLD",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="deploy_hold_queued",
                entity_id=deploy_id,
                outcome="pending",
                details={"version": version, "deploy_target": deploy_target},
            )
        )

        if self._deploy_log:
            self._deploy_log.append("hold_queued", deploy_id, {
                "action_id": action_id,
                "version": version,
                "deploy_target": deploy_target,
            })

        return action_id

    def queue_error_pattern_review(
        self,
        error_id: str,
        error_summary: str,
        occurrence_count: int,
        is_known_pattern: bool,
        auto_patch_available: bool,
    ) -> str:
        action_id = f"error-{uuid.uuid4().hex[:8]}"
        content = {
            "error_id": error_id,
            "error_summary": error_summary,
            "occurrence_count": occurrence_count,
            "is_known_pattern": is_known_pattern,
            "auto_patch_available": auto_patch_available,
            "card_title": f"Error Pattern: {error_summary[:50]}",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="error_pattern",
            entity_id=error_id,
            mode="REVIEW",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="error_pattern_queued",
                entity_id=error_id,
                outcome="pending",
                details={"occurrence_count": occurrence_count, "is_known": is_known_pattern},
            )
        )

        return action_id

    def queue_cost_alert_review(
        self,
        drift_pct: float,
        current_cost: float,
        baseline_cost: float,
        cost_per_user: float,
    ) -> str:
        action_id = f"cost-{uuid.uuid4().hex[:8]}"
        content = {
            "drift_pct": drift_pct,
            "current_cost": current_cost,
            "baseline_cost": baseline_cost,
            "cost_per_user": cost_per_user,
            "card_title": f"Inference Cost Alert: {drift_pct:.1f}% drift",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="cost_alert",
            entity_id=f"cost-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            mode="REVIEW",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="cost_alert_queued",
                entity_id=action_id,
                outcome="pending",
                details={"drift_pct": drift_pct, "current_cost": current_cost},
            )
        )

        return action_id

    def queue_security_pr_review(
        self,
        vuln_id: str,
        package: str,
        severity: str,
        fix_description: str,
    ) -> str:
        action_id = f"security-{uuid.uuid4().hex[:8]}"
        content = {
            "vuln_id": vuln_id,
            "package": package,
            "severity": severity,
            "fix_description": fix_description,
            "card_title": f"Security Patch: {package} ({severity})",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="security_pr",
            entity_id=vuln_id,
            mode="REVIEW",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="security_pr_queued",
                entity_id=vuln_id,
                outcome="pending",
                details={"package": package, "severity": severity},
            )
        )

        return action_id

    def queue_impossible_deadline_review(
        self,
        project_id: str,
        feature_description: str,
        deadline: str,
        estimated_hours: float,
        available_hours: float,
    ) -> str:
        action_id = f"deadline-{uuid.uuid4().hex[:8]}"
        content = {
            "project_id": project_id,
            "feature_description": feature_description,
            "deadline": deadline,
            "estimated_hours": estimated_hours,
            "available_hours": available_hours,
            "deadline_risk": "high",
            "card_title": f"Impossible Deadline: {project_id}",
        }

        action = BuildApprovalAction(
            action_id=action_id,
            action_type="impossible_deadline",
            entity_id=project_id,
            mode="REVIEW",
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        self._queue_action(action)
        self._log.append(
            self._create_log_entry(
                action_type="impossible_deadline_queued",
                entity_id=project_id,
                outcome="pending",
                details={
                    "deadline": deadline,
                    "estimated_hours": estimated_hours,
                    "available_hours": available_hours,
                },
            )
        )

        return action_id

    def handle_approve(
        self,
        action_id: str,
        next_step_fn: Callable[[], None] | None = None,
    ) -> ApprovalResult:
        action = self._pending_actions.get(action_id)
        if not action:
            return ApprovalResult(
                action_id=action_id,
                decision="approved",
                executed=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"error": "Action not found"},
            )

        action.outcome = "approved"

        if next_step_fn:
            if action.action_type == "pr_review":
                self._review_approved_callbacks[action_id] = next_step_fn
            next_step_fn()

        self._log.append(
            self._create_log_entry(
                action_type=f"{action.action_type}_approved",
                entity_id=action.entity_id,
                outcome="success",
                details={"action_id": action_id},
            )
        )

        if action.action_type == "pr_review" and self._pr_log:
            self._pr_log.append("review_approved", action.entity_id, {
                "action_id": action_id,
            })

        del self._pending_actions[action_id]

        return ApprovalResult(
            action_id=action_id,
            decision="approved",
            executed=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def handle_block(self, action_id: str, reason: str | None) -> ApprovalResult:
        action = self._pending_actions.get(action_id)
        if not action:
            return ApprovalResult(
                action_id=action_id,
                decision="blocked",
                executed=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"error": "Action not found"},
            )

        action.outcome = "blocked"

        self._log.append(
            self._create_log_entry(
                action_type=f"{action.action_type}_blocked",
                entity_id=action.entity_id,
                outcome="blocked",
                details={"action_id": action_id, "reason": reason},
            )
        )

        if action.action_type == "pr_review" and self._pr_log:
            self._pr_log.append("review_blocked", action.entity_id, {
                "action_id": action_id,
                "reason": reason,
            })

        del self._pending_actions[action_id]

        return ApprovalResult(
            action_id=action_id,
            decision="blocked",
            executed=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={"reason": reason},
        )

    def handle_hold_release(
        self,
        action_id: str,
        execute_fn: Callable[[], Any],
    ) -> ApprovalResult:
        action = self._pending_actions.get(action_id)
        if not action:
            return ApprovalResult(
                action_id=action_id,
                decision="released",
                executed=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"error": "Action not found"},
            )

        if action.mode != "HOLD":
            return ApprovalResult(
                action_id=action_id,
                decision="released",
                executed=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"error": f"Action is {action.mode}, not HOLD"},
            )

        action.outcome = "released"

        result = execute_fn()

        self._log.append(
            self._create_log_entry(
                action_type=f"{action.action_type}_released",
                entity_id=action.entity_id,
                outcome="success",
                details={"action_id": action_id},
            )
        )

        if action.action_type == "pr_merge_hold" and self._pr_log:
            self._pr_log.append("hold_released", action.entity_id, {
                "action_id": action_id,
            })

        if action.action_type == "deploy_hold" and self._deploy_log:
            self._deploy_log.append("hold_released", action.entity_id, {
                "action_id": action_id,
            })

        del self._pending_actions[action_id]

        return ApprovalResult(
            action_id=action_id,
            decision="released",
            executed=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={"result": str(result) if result else None},
        )

    def handle_hold_cancel(self, action_id: str) -> ApprovalResult:
        action = self._pending_actions.get(action_id)
        if not action:
            return ApprovalResult(
                action_id=action_id,
                decision="cancelled",
                executed=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"error": "Action not found"},
            )

        action.outcome = "cancelled"

        self._log.append(
            self._create_log_entry(
                action_type=f"{action.action_type}_cancelled",
                entity_id=action.entity_id,
                outcome="cancelled",
                details={"action_id": action_id},
            )
        )

        if action.action_type == "deploy_hold" and self._deploy_log:
            self._deploy_log.append("hold_cancelled", action.entity_id, {
                "action_id": action_id,
            })

        del self._pending_actions[action_id]

        return ApprovalResult(
            action_id=action_id,
            decision="cancelled",
            executed=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def log_auto(self, action_type: str, entity_id: str, details: dict[str, Any]) -> None:
        self._log.append(
            self._create_log_entry(
                action_type=action_type,
                entity_id=entity_id,
                outcome="success",
                details={"mode": "AUTO", **details},
            )
        )

    def get_pending_action(self, action_id: str) -> BuildApprovalAction | None:
        return self._pending_actions.get(action_id)

    def get_pending_actions_by_type(self, action_type: str) -> list[BuildApprovalAction]:
        return [
            a for a in self._pending_actions.values()
            if a.action_type == action_type
        ]

    def _queue_action(self, action: BuildApprovalAction) -> None:
        self._pending_actions[action.action_id] = action

        if self._war_room:
            try:
                self._war_room.queue_action(action.to_dict())
            except Exception as e:
                logger.error("Failed to queue action to War Room: %s", e)

    def _create_log_entry(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        details: dict[str, Any],
    ):
        from .build_init import BuildLogEntry

        return BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )


class PRActivityLog:
    """Append-only PR event log. Thread-safe."""

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.touch()

    def append(self, event_type: str, pr_id: str, details: dict[str, Any]) -> None:
        import fcntl

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "pr_id": pr_id,
            "details": details,
        }

        with self._log_path.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_pr_history(self, pr_id: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []

        if not self._log_path.exists():
            return entries

        import fcntl

        with self._log_path.open("r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("pr_id") == pr_id:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return entries


class DeployActivityLog:
    """Append-only deploy event log. Thread-safe."""

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.touch()

    def append(self, event_type: str, deploy_id: str, details: dict[str, Any]) -> None:
        import fcntl

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "deploy_id": deploy_id,
            "details": details,
        }

        with self._log_path.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
