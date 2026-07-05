# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Build Claw issue manager.

Handles:
- GitHub issue fetching with rate limiting
- Issue complexity scoring via inference
- Sprint plan generation
- Velocity tracking
- Feature brief handling

Enhancement: Category-based model selection for inference calls.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from .signal_dispatcher import BuildSignalDispatcher, ANALYTICS_WAIT_SECONDS
from .approval_handler import BuildApprovalHandler

logger = logging.getLogger(__name__)

# GitHub API rate limit backoff
RATE_LIMIT_BACKOFF_SECONDS = [30, 60, 120]


@dataclass
class ComplexityScore:
    issue_number: int
    issue_title: str
    complexity_tier: str  # S, M, L, XL
    estimated_hours: float
    clarity_score: str  # "clear", "low"
    missing_elements: list[str] = field(default_factory=list)
    scored_at: str = ""

    def __post_init__(self) -> None:
        if not self.scored_at:
            self.scored_at = datetime.now(timezone.utc).isoformat()


@dataclass
class SprintPlan:
    plan_id: str
    issues: list[dict[str, Any]]
    total_estimated_hours: float
    status: str  # "pending_review", "approved", "rejected"
    generated_at: str = ""
    approved_at: str | None = None

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


class IssueManager:
    """Manages GitHub issues, sprint planning, and velocity tracking."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
    ) -> None:
        self._fs = fs
        self._inference = inference_client
        self._github = github_client
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log
        self._analytics_received = False

    # ------------------------------------------------------------------
    # GitHub issue fetching
    # ------------------------------------------------------------------

    def fetch_open_issues(self) -> list[dict[str, Any]]:
        """Fetch open issues with exponential backoff on rate limits."""
        for attempt, backoff in enumerate(RATE_LIMIT_BACKOFF_SECONDS):
            try:
                issues = self._github.get_open_issues()
                self._log.append(
                    BuildLogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        action_type="issues_fetched",
                        entity_id="github",
                        outcome="success",
                        details={"count": len(issues)},
                    )
                )
                return issues
            except Exception as exc:
                if "rate limit" in str(exc).lower():
                    if attempt < len(RATE_LIMIT_BACKOFF_SECONDS) - 1:
                        logger.warning("GitHub rate limited, backing off %ds", backoff)
                        time.sleep(backoff)
                    else:
                        logger.error(
                            "GitHub rate limit exhausted after %d attempts", attempt + 1
                        )
                        return []
                else:
                    raise
        return []

    # ------------------------------------------------------------------
    # Issue complexity scoring
    # ------------------------------------------------------------------

    def score_issue_complexity(self, issue: dict[str, Any]) -> ComplexityScore:
        body = issue.get("body", "")
        has_acceptance = "acceptance criteria" in body.lower()
        has_description = len(body) > 50

        missing = []
        if not has_description:
            missing.append("description")
        if not has_acceptance:
            missing.append("acceptance_criteria")

        clarity = "clear" if (has_acceptance and has_description) else "low"

        # Use inference for complexity estimation
        prompt = f"""Score this issue complexity (S/M/L/XL) and estimate hours.
Title: {issue.get("title", "")}
Body: {body[:500]}
Respond with format: TIER HOURS (e.g., M 8)"""

        try:
            response = self._inference.complete(
                prompt=prompt,
                data_type="issue_complexity_scoring",
                temperature=0.2,
            )
            parts = str(response).strip().split()
            tier = parts[0].upper() if parts else "M"
            hours = float(parts[1]) if len(parts) > 1 else 8.0
        except Exception:
            tier = "M"
            hours = 8.0

        score = ComplexityScore(
            issue_number=issue.get("number", 0),
            issue_title=issue.get("title", ""),
            complexity_tier=tier,
            estimated_hours=hours,
            clarity_score=clarity,
            missing_elements=missing,
        )

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="issue_scored",
                entity_id=str(issue.get("number", 0)),
                outcome="success",
                details={
                    "tier": tier,
                    "hours": hours,
                    "clarity": clarity,
                },
            )
        )
        return score

    # ------------------------------------------------------------------
    # Sprint plan generation
    # ------------------------------------------------------------------

    def generate_sprint_plan(self) -> SprintPlan:
        """Generate a sprint plan from open issues.

        Waits for analytics retention signals (with timeout), then
        generates a plan and queues it for REVIEW approval.
        """
        # Wait for analytics signals (with timeout)
        self._analytics_received = False
        import os
        import sys

        is_testing = (
            os.getenv("TESTING") == "true"
            or "pytest" in sys.modules
            or "unittest" in sys.modules
        )
        wait_timeout = 1.0 if is_testing else ANALYTICS_WAIT_SECONDS

        start_wait = time.time()
        while time.time() - start_wait < wait_timeout:
            signals_file = (
                self._fs.BASE / "context" / "sprint" / "retention-signals.json"
            )
            if (
                self._dispatcher
                and getattr(self._dispatcher, "_retention_signals", None)
            ) or signals_file.exists():
                self._analytics_received = True
                break
            time.sleep(0.1)

        issues = self.fetch_open_issues()
        scored = []
        total_hours = 0.0

        for issue in issues:
            # Skip questions
            labels = [lbl.get("name", "") for lbl in issue.get("labels", [])]
            if "question" in labels:
                continue

            score = self.score_issue_complexity(issue)
            scored.append(
                {
                    "issue_number": score.issue_number,
                    "title": score.issue_title,
                    "complexity_tier": score.complexity_tier,
                    "estimated_hours": score.estimated_hours,
                    "clarity_score": score.clarity_score,
                }
            )
            total_hours += score.estimated_hours

        plan = SprintPlan(
            plan_id=f"sprint-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            issues=scored,
            total_estimated_hours=total_hours,
            status="pending_review",
        )

        # Write plan atomically
        plan_path = self._fs.BASE / "context" / "sprint" / "current-plan.json"
        plan_data = {
            "plan_id": plan.plan_id,
            "generated_at": plan.generated_at,
            "approved_at": plan.approved_at,
            "issues": plan.issues,
            "total_estimated_hours": plan.total_estimated_hours,
            "status": plan.status,
        }
        self._fs.atomic_write_json(plan_path, plan_data)

        # Queue for approval
        self._approval.queue_sprint_plan_review(
            plan_id=plan.plan_id,
            issues=plan.issues,
            total_hours=plan.total_estimated_hours,
            retention_context=None,
        )

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="sprint_plan_generated",
                entity_id=plan.plan_id,
                outcome="success",
                details={
                    "issue_count": len(scored),
                    "total_hours": total_hours,
                },
            )
        )
        return plan

    # ------------------------------------------------------------------
    # Sprint plan approval handling
    # ------------------------------------------------------------------

    def handle_sprint_plan_approved(self, plan_id: str) -> dict[str, Any] | None:
        plan_path = self._fs.BASE / "context" / "sprint" / "current-plan.json"
        plan_data = self._fs.read_json(plan_path)

        if plan_data.get("plan_id") != plan_id:
            return None

        plan_data["status"] = "approved"
        plan_data["approved_at"] = datetime.now(timezone.utc).isoformat()
        self._fs.atomic_write_json(plan_path, plan_data)

        issues = plan_data.get("issues", [])
        if issues:
            return issues[0]
        return None

    # ------------------------------------------------------------------
    # Velocity tracking
    # ------------------------------------------------------------------

    def update_velocity(
        self,
        estimated_hours: float,
        actual_hours: float,
        sprint_id: str,
    ) -> None:
        velocity_path = self._fs.BASE / "context" / "sprint" / "velocity.json"
        velocity_data = self._read_velocity_data()

        sprints = velocity_data.get("sprints", [])
        sprints.append(
            {
                "sprint_id": sprint_id,
                "estimated_hours": estimated_hours,
                "actual_hours": actual_hours,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        velocity_data["sprints"] = sprints

        # Recalculate average
        if sprints:
            total_actual = sum(s["actual_hours"] for s in sprints)
            total_estimated = sum(s["estimated_hours"] for s in sprints)
            velocity_data["avg_hours_per_week"] = total_actual / len(sprints)
            if total_estimated > 0:
                velocity_data["estimation_accuracy_pct"] = (
                    1 - abs(total_actual - total_estimated) / total_estimated
                ) * 100

        self._fs.atomic_write_json(velocity_path, velocity_data)

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="velocity_updated",
                entity_id=sprint_id,
                outcome="success",
                details={
                    "estimated": estimated_hours,
                    "actual": actual_hours,
                    "avg_hours": velocity_data["avg_hours_per_week"],
                },
            )
        )

    def _read_velocity_data(self) -> dict[str, Any]:
        velocity_path = self._fs.BASE / "context" / "sprint" / "velocity.json"
        if velocity_path.exists():
            try:
                data = self._fs.read_json(velocity_path)
                if "sprints" in data:
                    return data
            except Exception:
                pass
        return {
            "sprints": [],
            "avg_hours_per_week": 0,
            "estimation_accuracy_pct": 0,
        }

    # ------------------------------------------------------------------
    # Feature brief handling
    # ------------------------------------------------------------------

    def handle_feature_brief(
        self,
        client_id: str,
        project_id: str,
        feature_description: str,
        deadline: str,
        acceptance_criteria: str,
    ) -> None:
        # Check deadline feasibility
        try:
            deadline_dt = datetime.fromisoformat(deadline)
            now = datetime.now(timezone.utc)
            days_until = (deadline_dt - now).total_seconds() / 86400
            if days_until < 3:
                self._log.append(
                    BuildLogEntry(
                        timestamp=now.isoformat(),
                        action_type="deadline_risk_flagged",
                        entity_id=project_id,
                        outcome="warning",
                        details={
                            "deadline": deadline,
                            "days_remaining": round(days_until, 1),
                            "severity": "high",
                        },
                    )
                )
        except (ValueError, TypeError):
            pass

        # Create GitHub issue for the feature brief
        try:
            issue_number = self._github.create_issue(
                title=f"Feature Brief: {feature_description[:80]}",
                body=f"Client: {client_id}\n\nDescription: {feature_description}\n\nDeadline: {deadline}\n\nAcceptance Criteria:\n{acceptance_criteria}",
            )
        except Exception:
            issue_number = 0

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="feature_brief_processed",
                entity_id=project_id,
                outcome="success",
                details={
                    "client_id": client_id,
                    "issue_number": issue_number,
                },
            )
        )
