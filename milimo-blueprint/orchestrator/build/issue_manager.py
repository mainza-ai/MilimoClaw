#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Issue Manager

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

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .signal_dispatcher import BuildSignalDispatcher

logger = logging.getLogger("milimo.build")

ANALYTICS_WAIT_SECONDS = 300  # 5 minutes
RATE_LIMIT_BACKOFF_BASE = 60  # 1 minute base, doubles each attempt
RATE_LIMIT_BACKOFF_MAX = 1800  # 30 minutes max


@dataclass
class ComplexityScore:
    """Score for a GitHub issue's complexity."""

    issue_number: int
    issue_title: str
    complexity_tier: str  # "S" | "M" | "L" | "XL"
    estimated_hours: float
    clarity_score: str  # "clear" | "low"
    missing_elements: list[str]
    scored_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_number": self.issue_number,
            "issue_title": self.issue_title,
            "complexity_tier": self.complexity_tier,
            "estimated_hours": self.estimated_hours,
            "clarity_score": self.clarity_score,
            "missing_elements": self.missing_elements,
            "scored_at": self.scored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplexityScore:
        return cls(
            issue_number=data["issue_number"],
            issue_title=data["issue_title"],
            complexity_tier=data["complexity_tier"],
            estimated_hours=data["estimated_hours"],
            clarity_score=data["clarity_score"],
            missing_elements=data.get("missing_elements", []),
            scored_at=data["scored_at"],
        )


@dataclass
class SprintPlan:
    """A sprint plan with prioritized issues."""

    plan_id: str
    generated_at: str
    approved_at: str | None
    issues: list[ComplexityScore]
    total_estimated_hours: float
    retention_context: str | None
    velocity_calibrated: bool
    status: str  # "pending_review" | "approved" | "active" | "completed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "generated_at": self.generated_at,
            "approved_at": self.approved_at,
            "issues": [i.to_dict() for i in self.issues],
            "total_estimated_hours": self.total_estimated_hours,
            "retention_context": self.retention_context,
            "velocity_calibrated": self.velocity_calibrated,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SprintPlan:
        return cls(
            plan_id=data["plan_id"],
            generated_at=data["generated_at"],
            approved_at=data.get("approved_at"),
            issues=[ComplexityScore.from_dict(i) for i in data.get("issues", [])],
            total_estimated_hours=data.get("total_estimated_hours", 0),
            retention_context=data.get("retention_context"),
            velocity_calibrated=data.get("velocity_calibrated", False),
            status=data.get("status", "pending_review"),
        )


@dataclass
class VelocityRecord:
    """Record of sprint velocity."""

    sprint_id: str
    estimated_hours: float
    actual_hours: float
    issues_completed: int
    started_at: str
    completed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sprint_id": self.sprint_id,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "issues_completed": self.issues_completed,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


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

    TIER_HOURS = {
        "S": 2,
        "M": 8,
        "L": 20,
        "XL": 40,
    }

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
    ):
        self._fs = fs
        self._inference = inference_client
        self._github = github_client
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log
        self._analytics_response: dict[str, Any] | None = None
        self._analytics_received = False

    def generate_sprint_plan(self) -> SprintPlan:
        self._dispatcher.send_behavior_query(
            query="Which features have lowest retention correlation this week?",
            lookback_days=7,
        )

        start_time = time.time()
        while not self._analytics_received and (time.time() - start_time) < ANALYTICS_WAIT_SECONDS:
            time.sleep(0.1)

        if not self._analytics_received:
            logger.info("No Analytics response received within %ds, proceeding with complexity scores only", ANALYTICS_WAIT_SECONDS)
            self._log.append(self._create_log_entry(
                "analytics_timeout",
                "sprint-planning",
                "proceeded_without_analytics",
                {"wait_seconds": ANALYTICS_WAIT_SECONDS},
            ))

        issues = self.fetch_open_issues()
        scored_issues: list[ComplexityScore] = []

        for issue in issues:
            score = self.score_issue_complexity(issue)
            scored_issues.append(score)

        velocity_data = self._read_velocity_data()
        retention_context = self._build_retention_context()

        if retention_context:
            scored_issues = self._rank_by_retention(scored_issues, retention_context)

        sprint_hours = self._calculate_sprint_hours(velocity_data)
        selected_issues = self._select_issues_for_sprint(scored_issues, sprint_hours)

        total_hours = sum(i.estimated_hours for i in selected_issues)

        plan = SprintPlan(
            plan_id=f"sprint-{uuid.uuid4().hex[:8]}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            approved_at=None,
            issues=selected_issues,
            total_estimated_hours=total_hours,
            retention_context=retention_context,
            velocity_calibrated=len(velocity_data.get("sprints", [])) >= 3,
            status="pending_review",
        )

        self._fs.atomic_write_json(
            self._fs.get_sprint_plan_path(),
            plan.to_dict(),
        )

        backlog_path = self._fs.get_backlog_path()
        backlog_data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "issues": [s.to_dict() for s in scored_issues],
        }
        self._fs.atomic_write_json(backlog_path, backlog_data)

        self._approval.queue_sprint_plan_review(
            plan_id=plan.plan_id,
            issues=[i.to_dict() for i in selected_issues],
            total_hours=total_hours,
            retention_context=retention_context,
        )

        self._log.append(self._create_log_entry(
            "sprint_plan_generated",
            plan.plan_id,
            "pending_review",
            {
                "issue_count": len(selected_issues),
                "total_hours": total_hours,
                "analytics_used": self._analytics_received,
            },
        ))

        return plan

    def fetch_open_issues(self) -> list[dict]:
        backoff = RATE_LIMIT_BACKOFF_BASE
        attempts = 0

        while attempts < 4:
            try:
                issues = self._github.get_open_issues()
                self._log.append(self._create_log_entry(
                    "issues_fetched",
                    "github",
                    "success",
                    {"count": len(issues)},
                ))
                return issues
            except Exception as e:
                if "rate limit" in str(e).lower():
                    attempts += 1
                    logger.warning("GitHub rate limited, backing off for %ds (attempt %d)", backoff, attempts)
                    self._log.append(self._create_log_entry(
                        "github_rate_limited",
                        "github",
                        "backoff",
                        {"attempt": attempts, "backoff_seconds": backoff},
                    ))
                    time.sleep(backoff)
                    backoff = min(backoff * 2, RATE_LIMIT_BACKOFF_MAX)
                else:
                    raise

        raise RuntimeError("GitHub API rate limited after max retries")

    def score_issue_complexity(self, issue: dict) -> ComplexityScore:
        issue_number = issue.get("number", 0)
        title = issue.get("title", "")
        body = issue.get("body", "") or ""
        labels = [l.get("name", "") for l in issue.get("labels", [])]

        missing_elements: list[str] = []
        clarity_score = "clear"

        if not body or len(body.strip()) < 50:
            clarity_score = "low"
            missing_elements.append("description")

        acceptance_criteria_markers = [
            "acceptance criteria",
            "definition of done",
            "success criteria",
            "must have",
            "should have",
        ]
        has_acceptance = any(marker in body.lower() for marker in acceptance_criteria_markers)
        if not has_acceptance:
            clarity_score = "low"
            missing_elements.append("acceptance_criteria")

        if "question" in labels or "needs-info" in labels:
            clarity_score = "low"
            missing_elements.append("clarification_needed")

        prompt = f"""Analyze this GitHub issue and estimate its complexity.

Issue #{issue_number}: {title}

Description:
{body[:2000]}

Labels: {', '.join(labels)}

Rate complexity as one of:
- S (Small): ~2 hours - simple fix, documentation, minor tweak
- M (Medium): ~8 hours - standard feature, moderate refactor
- L (Large): ~20 hours - significant feature, complex refactor
- XL (Extra Large): ~40 hours - major feature, architectural change

Output only the tier letter (S, M, L, or XL) followed by estimated hours.
Example: M 8"""

        tier = "M"
        estimated_hours = 8.0

        try:
            response = self._inference.complete(
                prompt=prompt,
                data_type="issue_complexity_scoring",
                max_tokens=50,
            )
            parsed = self._parse_complexity_response(response)
            if parsed:
                tier, estimated_hours = parsed
        except Exception as e:
            logger.warning("Inference failed for issue %d, using defaults: %s", issue_number, e)

        score = ComplexityScore(
            issue_number=issue_number,
            issue_title=title,
            complexity_tier=tier,
            estimated_hours=estimated_hours,
            clarity_score=clarity_score,
            missing_elements=missing_elements,
            scored_at=datetime.now(timezone.utc).isoformat(),
        )

        self._log.append(self._create_log_entry(
            "issue_scored",
            str(issue_number),
            "success",
            {
                "tier": tier,
                "hours": estimated_hours,
                "clarity": clarity_score,
            },
        ))

        return score

    def handle_feature_brief(
        self,
        client_id: str,
        project_id: str,
        feature_description: str,
        deadline: str | None,
        acceptance_criteria: str | None,
    ) -> None:
        issue_title = f"[{project_id}] {feature_description[:80]}"
        issue_body = f"""## Feature Request

**Project:** {project_id}
**Client:** {client_id}

### Description
{feature_description}

### Acceptance Criteria
{acceptance_criteria or 'To be defined'}

---
*Created from Ops Claw feature_brief message*"""

        try:
            issue_number = self._github.create_issue(
                title=issue_title,
                body=issue_body,
                labels=["feature", "from-ops"],
            )
        except Exception as e:
            logger.error("Failed to create GitHub issue: %s", e)
            self._log.append(self._create_log_entry(
                "feature_brief_failed",
                project_id,
                "failed",
                {"error": str(e)},
            ))
            raise

        score = self.score_issue_complexity({
            "number": issue_number,
            "title": issue_title,
            "body": issue_body,
            "labels": [{"name": "feature"}],
        })

        backlog_path = self._fs.get_backlog_path()
        backlog_data = self._fs.read_json(backlog_path) or {"issues": []}
        backlog_data["issues"].append(score.to_dict())
        backlog_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._fs.atomic_write_json(backlog_path, backlog_data)

        if deadline:
            is_feasible, available_hours = self._check_deadline_feasibility(
                score.estimated_hours,
                deadline,
            )
            if not is_feasible:
                self._approval.queue_impossible_deadline_review(
                    project_id=project_id,
                    feature_description=feature_description,
                    deadline=deadline,
                    estimated_hours=score.estimated_hours,
                    available_hours=available_hours,
                )
                self._log.append(self._create_log_entry(
                    "deadline_risk_flagged",
                    project_id,
                    "review_queued",
                    {
                        "deadline": deadline,
                        "estimated_hours": score.estimated_hours,
                        "available_hours": available_hours,
                    },
                ))

        self._dispatcher.send_feature_brief_acknowledged(
            project_id=project_id,
            estimated_start=datetime.now(timezone.utc).isoformat(),
            clarity_score=score.clarity_score,
        )

        self._log.append(self._create_log_entry(
            "feature_brief_handled",
            str(issue_number),
            "success",
            {
                "project_id": project_id,
                "issue_number": issue_number,
                "tier": score.complexity_tier,
            },
        ))

    def handle_sprint_plan_approved(self, plan_id: str) -> ComplexityScore | None:
        plan_path = self._fs.get_sprint_plan_path()
        plan_data = self._fs.read_json(plan_path)

        if not plan_data:
            logger.error("Sprint plan not found: %s", plan_id)
            return None

        plan = SprintPlan.from_dict(plan_data)

        if plan.plan_id != plan_id:
            logger.error("Plan ID mismatch: expected %s, found %s", plan_id, plan.plan_id)
            return None

        plan.status = "approved"
        plan.approved_at = datetime.now(timezone.utc).isoformat()

        self._fs.atomic_write_json(plan_path, plan.to_dict())

        self._log.append(self._create_log_entry(
            "sprint_plan_approved",
            plan_id,
            "active",
            {"issue_count": len(plan.issues)},
        ))

        if plan.issues:
            return plan.issues[0]
        return None

    def update_velocity(
        self,
        estimated_hours: float,
        actual_hours: float,
        sprint_id: str,
    ) -> None:
        velocity_path = self._fs.get_velocity_path()
        velocity_data = self._fs.read_json(velocity_path) or {
            "sprints": [],
            "avg_hours_per_week": 0,
            "estimation_accuracy_pct": 0,
        }

        record = VelocityRecord(
            sprint_id=sprint_id,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            issues_completed=0,
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        velocity_data["sprints"].append(record.to_dict())

        sprints = velocity_data["sprints"]
        if sprints:
            total_actual = sum(s.get("actual_hours", 0) for s in sprints[-4:])
            velocity_data["avg_hours_per_week"] = total_actual / min(len(sprints), 4)

            total_estimated = sum(s.get("estimated_hours", 0) for s in sprints[-4:])
            if total_estimated > 0:
                accuracy = 100 - abs(100 - (total_actual / total_estimated) * 100)
                velocity_data["estimation_accuracy_pct"] = round(max(0, min(100, accuracy)), 1)

        self._fs.atomic_write_json(velocity_path, velocity_data)

        self._log.append(self._create_log_entry(
            "velocity_updated",
            sprint_id,
            "success",
            {
                "estimated": estimated_hours,
                "actual": actual_hours,
                "accuracy_pct": velocity_data["estimation_accuracy_pct"],
            },
        ))

    def receive_analytics_response(self, response: dict[str, Any]) -> None:
        self._analytics_response = response
        self._analytics_received = True
        self._log.append(self._create_log_entry(
            "analytics_response_received",
            response.get("message_id", "unknown"),
            "success",
            {"data_quality": response.get("data_quality", "unknown")},
        ))

    def _check_deadline_feasibility(
        self,
        estimated_hours: float,
        deadline: str,
    ) -> tuple[bool, float]:
        try:
            deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return True, estimated_hours * 2

        velocity_data = self._read_velocity_data()
        weekly_hours = velocity_data.get("avg_hours_per_week", 40)

        now = datetime.now(timezone.utc)
        days_until_deadline = (deadline_dt - now).total_seconds() / 86400
        weeks_until_deadline = days_until_deadline / 7

        available_hours = weekly_hours * weeks_until_deadline * 0.8

        is_feasible = estimated_hours <= available_hours
        return is_feasible, available_hours

    def _read_velocity_data(self) -> dict[str, Any]:
        velocity_path = self._fs.get_velocity_path()
        return self._fs.read_json(velocity_path) or {
            "sprints": [],
            "avg_hours_per_week": 0,
            "estimation_accuracy_pct": 0,
        }

    def _build_retention_context(self) -> str | None:
        signals = self._dispatcher.get_retention_signals()
        if not signals:
            return None

        parts = []
        if "feature_adoption_rates" in signals:
            parts.append(f"Feature adoption: {signals['feature_adoption_rates']}")
        if "churn_correlation" in signals:
            parts.append(f"Churn correlation: {signals['churn_correlation']}")
        if "recommended_features" in signals:
            parts.append(f"Recommended: {', '.join(signals['recommended_features'][:3])}")

        return "; ".join(parts) if parts else None

    def _rank_by_retention(
        self,
        issues: list[ComplexityScore],
        retention_context: str,
    ) -> list[ComplexityScore]:
        return sorted(issues, key=lambda i: (i.estimated_hours, i.clarity_score == "low"))

    def _calculate_sprint_hours(self, velocity_data: dict[str, Any]) -> float:
        weekly_hours = velocity_data.get("avg_hours_per_week", 40)
        accuracy = velocity_data.get("estimation_accuracy_pct", 100)

        if accuracy < 80:
            weekly_hours *= 0.8

        return weekly_hours * 2

    def _select_issues_for_sprint(
        self,
        issues: list[ComplexityScore],
        max_hours: float,
    ) -> list[ComplexityScore]:
        selected: list[ComplexityScore] = []
        total_hours = 0.0

        for issue in issues:
            if total_hours + issue.estimated_hours <= max_hours:
                selected.append(issue)
                total_hours += issue.estimated_hours

        return selected

    def _parse_complexity_response(self, response: str) -> tuple[str, float] | None:
        response = response.strip().upper()
        for tier in ["XL", "L", "M", "S"]:
            if response.startswith(tier):
                hours = self.TIER_HOURS.get(tier, 8)
                parts = response.split()
                if len(parts) > 1:
                    try:
                        hours = float(parts[1])
                    except ValueError:
                        pass
                return tier, hours
        return None

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
