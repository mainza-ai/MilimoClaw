"""
Build Claw PR manager.

Handles:
- Opening PRs from resolution results
- Two-stage approval: REVIEW → HOLD → merge
- Conflict detection
- PR status tracking

Enhancement: Background execution for async PR operations.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from .approval_handler import BuildApprovalHandler, PRActivityLog
from .code_generator import ResolutionResult

logger = logging.getLogger(__name__)


@dataclass
class PRRecord:
    pr_id: str
    issue_number: int
    branch_name: str
    title: str
    description: str
    github_pr_number: int
    github_pr_url: str
    files_changed: int
    lines_added: int
    lines_removed: int
    test_status: str
    tests_count: int
    status: str  # "drafted", "approved", "merged", "blocked"
    review_action_id: str | None = None
    hold_action_id: str | None = None
    opened_at: str = ""
    approved_at: str | None = None
    merged_at: str | None = None

    def __post_init__(self) -> None:
        if not self.opened_at:
            self.opened_at = datetime.now(timezone.utc).isoformat()


class PRManager:
    """Manages pull request lifecycle with two-stage approval."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        github_client: Any,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        pr_log: PRActivityLog,
    ) -> None:
        self._fs = fs
        self._inference = inference_client
        self._github = github_client
        self._approval = approval_handler
        self._log = operational_log
        self._pr_log = pr_log

    # ------------------------------------------------------------------
    # Open PR
    # ------------------------------------------------------------------

    def open_pr(self, resolution: ResolutionResult) -> PRRecord:
        """Create a PR from a resolution result. Writes to drafted/ and queues REVIEW."""
        pr_id = f"pr-{uuid.uuid4().hex[:8]}"

        # Generate PR description via inference
        description = self._inference.complete(
            prompt=f"Write a PR description for issue #{resolution.issue_number}: {resolution.branch_name}",
            data_type="pr_description_generation",
            temperature=0.3,
        )

        # Create PR on GitHub
        gh_number, gh_url = self._github.create_pull_request(
            title=f"Fix #{resolution.issue_number}",
            body=str(description),
            branch=resolution.branch_name,
        )

        pr = PRRecord(
            pr_id=pr_id,
            issue_number=resolution.issue_number,
            branch_name=resolution.branch_name,
            title=f"Fix #{resolution.issue_number}",
            description=str(description),
            github_pr_number=gh_number,
            github_pr_url=gh_url,
            files_changed=len(resolution.files_changed),
            lines_added=resolution.tests_passing,
            lines_removed=resolution.tests_failing,
            test_status=resolution.test_result,
            tests_count=resolution.tests_passing + resolution.tests_failing,
            status="drafted",
        )

        # Write to drafted/
        pr_path = self._fs.get_pr_path("drafted", pr_id)
        self._fs.atomic_write_json(pr_path, self._pr_to_dict(pr))

        # Queue REVIEW approval
        review_action_id = self._approval.queue_pr_review(
            pr_id=pr_id,
            pr_title=pr.title,
            branch=pr.branch_name,
            issue_number=pr.issue_number,
            files_changed=pr.files_changed,
            lines_added=pr.lines_added,
            lines_removed=pr.lines_removed,
            test_result=pr.test_status,
            tests_count=pr.tests_count,
            github_pr_url=pr.github_pr_url,
        )
        pr.review_action_id = review_action_id

        # Update the file with the action ID
        self._fs.atomic_write_json(pr_path, self._pr_to_dict(pr))

        self._pr_log.append("pr_created", pr_id, {"issue": resolution.issue_number})
        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pr_opened",
            entity_id=pr_id,
            outcome="success",
            details={"issue_number": resolution.issue_number, "status": "drafted"},
        ))
        return pr

    # ------------------------------------------------------------------
    # REVIEW approved → move to approved/ (does NOT merge)
    # ------------------------------------------------------------------

    def handle_review_approved(self, pr_id: str) -> None:
        """Move PR from drafted/ to approved/. Does NOT call GitHub merge."""
        drafted_path = self._fs.get_pr_path("drafted", pr_id)
        if not drafted_path.exists():
            raise ValueError(f"PR {pr_id} not found in drafted/")

        pr_data = self._fs.read_json(drafted_path)
        pr_data["status"] = "approved"
        pr_data["approved_at"] = datetime.now(timezone.utc).isoformat()

        approved_path = self._fs.get_pr_path("approved", pr_id)
        self._fs.atomic_write_json(approved_path, pr_data)
        drafted_path.unlink(missing_ok=True)

        # Queue HOLD for merge
        hold_action_id = self._approval.queue_pr_merge_hold(
            pr_id=pr_id,
            pr_title=pr_data.get("title", ""),
            github_pr_url=pr_data.get("github_pr_url", ""),
        )

        self._pr_log.append("review_approved", pr_id, {})
        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pr_review_approved",
            entity_id=pr_id,
            outcome="approved",
            details={"hold_action_id": hold_action_id},
        ))

    # ------------------------------------------------------------------
    # HOLD released → merge
    # ------------------------------------------------------------------

    def handle_merge_hold_released(self, pr_id: str) -> PRRecord:
        """Release HOLD and merge the PR."""
        approved_path = self._fs.get_pr_path("approved", pr_id)
        if not approved_path.exists():
            raise ValueError(f"PR not found in approved/: {pr_id}")

        pr_data = self._fs.read_json(approved_path)

        # Call GitHub merge
        self._github.merge_pull_request(pr_data.get("github_pr_number", 0))

        pr_data["status"] = "merged"
        pr_data["merged_at"] = datetime.now(timezone.utc).isoformat()

        merged_path = self._fs.get_pr_path("merged", pr_id)
        self._fs.atomic_write_json(merged_path, pr_data)
        approved_path.unlink(missing_ok=True)

        self._pr_log.append("pr_merged", pr_id, {})
        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pr_merged",
            entity_id=pr_id,
            outcome="success",
            details={},
        ))

        return PRRecord(**pr_data)

    # ------------------------------------------------------------------
    # Blocked PR
    # ------------------------------------------------------------------

    def handle_review_blocked(self, pr_id: str, reason: str) -> None:
        """Mark PR as blocked."""
        drafted_path = self._fs.get_pr_path("drafted", pr_id)
        if drafted_path.exists():
            pr_data = self._fs.read_json(drafted_path)
            pr_data["status"] = "blocked"
            pr_data["block_reason"] = reason
            self._fs.atomic_write_json(drafted_path, pr_data)

        self._pr_log.append("review_blocked", pr_id, {"reason": reason})
        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pr_blocked",
            entity_id=pr_id,
            outcome="blocked",
            details={"reason": reason},
        ))

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self, branch_name: str, files_changed: list[str]) -> list[str]:
        """Detect conflicting open PRs."""
        open_prs = self._github.get_open_pull_requests()
        conflicts: list[str] = []

        for pr in open_prs:
            pr_branch = pr.get("head", {}).get("ref", "")
            if pr_branch == branch_name:
                continue
            pr_files = pr.get("files", [])
            overlapping = set(files_changed) & set(pr_files)
            if overlapping:
                conflicts.append(f"PR #{pr.get('number', '?')} ({pr_branch})")

        return conflicts

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _pr_to_dict(self, pr: PRRecord) -> dict[str, Any]:
        return {
            "pr_id": pr.pr_id,
            "issue_number": pr.issue_number,
            "branch_name": pr.branch_name,
            "title": pr.title,
            "description": pr.description,
            "github_pr_number": pr.github_pr_number,
            "github_pr_url": pr.github_pr_url,
            "files_changed": pr.files_changed,
            "lines_added": pr.lines_added,
            "lines_removed": pr.lines_removed,
            "test_status": pr.test_status,
            "tests_count": pr.tests_count,
            "status": pr.status,
            "review_action_id": pr.review_action_id,
            "hold_action_id": pr.hold_action_id,
            "opened_at": pr.opened_at,
            "approved_at": pr.approved_at,
            "merged_at": pr.merged_at,
        }
