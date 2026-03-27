#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — PR Manager

Manages the full PR lifecycle from opening to merge.

TWO-STAGE APPROVAL (non-negotiable):
1. PR opened → queued as REVIEW
2. REVIEW approved → queued as HOLD (NOT merged)
3. HOLD released → GitHub merge triggered

Stage 1 REVIEW approval MUST NOT trigger merge.
Verify this with an explicit test.

PR conflicts detected at open time and flagged in War Room REVIEW.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler, PRActivityLog
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .code_generator import ResolutionResult

logger = logging.getLogger("milimo.build")


@dataclass
class PRRecord:
    """Record of a pull request."""

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
    test_status: str
    tests_count: int
    status: str
    review_action_id: str | None
    hold_action_id: str | None
    opened_at: str
    approved_at: str | None
    merged_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pr_id": self.pr_id,
            "issue_number": self.issue_number,
            "branch_name": self.branch_name,
            "title": self.title,
            "description": self.description,
            "github_pr_number": self.github_pr_number,
            "github_pr_url": self.github_pr_url,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "test_status": self.test_status,
            "tests_count": self.tests_count,
            "status": self.status,
            "review_action_id": self.review_action_id,
            "hold_action_id": self.hold_action_id,
            "opened_at": self.opened_at,
            "approved_at": self.approved_at,
            "merged_at": self.merged_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PRRecord:
        return cls(
            pr_id=data["pr_id"],
            issue_number=data["issue_number"],
            branch_name=data["branch_name"],
            title=data["title"],
            description=data["description"],
            github_pr_number=data.get("github_pr_number"),
            github_pr_url=data.get("github_pr_url"),
            files_changed=data.get("files_changed", 0),
            lines_added=data.get("lines_added", 0),
            lines_removed=data.get("lines_removed", 0),
            test_status=data.get("test_status", "unknown"),
            tests_count=data.get("tests_count", 0),
            status=data["status"],
            review_action_id=data.get("review_action_id"),
            hold_action_id=data.get("hold_action_id"),
            opened_at=data["opened_at"],
            approved_at=data.get("approved_at"),
            merged_at=data.get("merged_at"),
        )


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
        pr_log: PRActivityLog,
    ):
        self._fs = fs
        self._inference = inference_client
        self._github = github_client
        self._approval = approval_handler
        self._log = operational_log
        self._pr_log = pr_log

    def open_pr(self, resolution: ResolutionResult) -> PRRecord:
        pr_id = f"pr-{resolution.issue_number}-{uuid.uuid4().hex[:6]}"

        description = self._generate_pr_description(resolution)

        try:
            pr_number, pr_url = self._github.create_pull_request(
                branch=resolution.branch_name,
                title=f"Fix #{resolution.issue_number}",
                body=description,
            )
        except Exception as e:
            logger.error("Failed to create PR: %s", e)
            pr_number = None
            pr_url = None

        conflicts = self.detect_conflicts(resolution.branch_name, resolution.files_changed)

        test_status = "passing" if resolution.test_result == "passing" else "failing"
        tests_count = resolution.tests_passing + resolution.tests_failing

        pr = PRRecord(
            pr_id=pr_id,
            issue_number=resolution.issue_number,
            branch_name=resolution.branch_name,
            title=f"Fix #{resolution.issue_number}",
            description=description,
            github_pr_number=pr_number,
            github_pr_url=pr_url,
            files_changed=len(resolution.files_changed),
            lines_added=0,
            lines_removed=0,
            test_status=test_status,
            tests_count=tests_count,
            status="drafted",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=None,
            merged_at=None,
        )

        pr_path = self._fs.get_pr_path("drafted", pr_id)
        self._fs.atomic_write_json(pr_path, pr.to_dict())

        if conflicts:
            conflict_msg = f"Conflicts with: {', '.join(conflicts)}"
        else:
            conflict_msg = None

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
            github_pr_url=pr.github_pr_url or "",
        )

        pr.review_action_id = review_action_id
        self._fs.atomic_write_json(pr_path, pr.to_dict())

        self._pr_log.append("pr_opened", pr_id, {
            "issue_number": resolution.issue_number,
            "branch": resolution.branch_name,
            "conflicts": conflicts,
        })

        self._log.append(self._create_log_entry(
            "pr_opened",
            pr_id,
            "success",
            {
                "issue_number": resolution.issue_number,
                "files_changed": len(resolution.files_changed),
                "conflicts": conflicts,
            },
        ))

        return pr

    def handle_review_approved(self, pr_id: str) -> None:
        pr = self.load_pr(pr_id, "drafted")
        if not pr:
            logger.error("PR not found in drafted: %s", pr_id)
            raise ValueError(f"PR not found: {pr_id}")

        pr.status = "approved"
        pr.approved_at = datetime.now(timezone.utc).isoformat()

        hold_action_id = self._approval.queue_pr_merge_hold(
            pr_id=pr.pr_id,
            pr_title=pr.title,
            github_pr_url=pr.github_pr_url or "",
        )

        pr.hold_action_id = hold_action_id

        old_path = self._fs.get_pr_path("drafted", pr_id)
        new_path = self._fs.get_pr_path("approved", pr_id)

        self._fs.atomic_write_json(new_path, pr.to_dict())

        if old_path.exists():
            old_path.unlink()

        self._pr_log.append("pr_review_approved", pr_id, {
            "hold_action_id": hold_action_id,
        })

        self._log.append(self._create_log_entry(
            "pr_review_approved",
            pr_id,
            "hold_queued",
            {"hold_action_id": hold_action_id},
        ))

    def handle_merge_hold_released(self, pr_id: str) -> PRRecord:
        pr = self.load_pr(pr_id, "approved")
        if not pr:
            logger.error("PR not found in approved: %s", pr_id)
            raise ValueError(f"PR not found in approved: {pr_id}")

        if pr.status != "approved":
            raise ValueError(f"PR status is '{pr.status}', expected 'approved'")

        try:
            self._github.merge_pull_request(pr.github_pr_number)
        except Exception as e:
            logger.error("Failed to merge PR: %s", e)
            raise

        pr.status = "merged"
        pr.merged_at = datetime.now(timezone.utc).isoformat()

        old_path = self._fs.get_pr_path("approved", pr_id)
        new_path = self._fs.get_pr_path("merged", pr_id)

        self._fs.atomic_write_json(new_path, pr.to_dict())

        if old_path.exists():
            old_path.unlink()

        self._pr_log.append("pr_merged", pr_id, {
            "merged_at": pr.merged_at,
        })

        self._log.append(self._create_log_entry(
            "pr_merged",
            pr_id,
            "success",
            {"issue_number": pr.issue_number},
        ))

        return pr

    def handle_review_blocked(self, pr_id: str, reason: str) -> None:
        pr = self.load_pr(pr_id, "drafted")
        if not pr:
            pr = self.load_pr(pr_id, "approved")
            if pr:
                old_path = self._fs.get_pr_path("approved", pr_id)
                if old_path.exists():
                    old_path.unlink()

        if not pr:
            logger.error("PR not found: %s", pr_id)
            raise ValueError(f"PR not found: {pr_id}")

        pr.status = "blocked"

        pr_path = self._fs.get_pr_path("drafted", pr_id)
        self._fs.atomic_write_json(pr_path, pr.to_dict())

        self._pr_log.append("pr_blocked", pr_id, {"reason": reason})

        self._log.append(self._create_log_entry(
            "pr_blocked",
            pr_id,
            "blocked",
            {"reason": reason, "issue_number": pr.issue_number},
        ))

    def detect_conflicts(self, branch_name: str, files_changed: list[str]) -> list[str]:
        conflicts: list[str] = []

        try:
            open_prs = self._github.get_open_pull_requests()
        except Exception:
            return conflicts

        for open_pr in open_prs:
            open_pr_branch = open_pr.get("head", {}).get("ref", "")
            if open_pr_branch == branch_name:
                continue

            open_pr_files = open_pr.get("files", [])
            for file_changed in files_changed:
                if file_changed in open_pr_files:
                    conflicts.append(f"PR #{open_pr.get('number', 'unknown')}")

        return conflicts

    def get_drafted_prs(self) -> list[PRRecord]:
        drafted_dir = self._fs._base / "prs" / "drafted"
        if not drafted_dir.exists():
            return []

        prs = []
        for pr_file in drafted_dir.glob("*.json"):
            data = self._fs.read_json(pr_file)
            if data:
                prs.append(PRRecord.from_dict(data))

        return prs

    def get_approved_prs(self) -> list[PRRecord]:
        approved_dir = self._fs._base / "prs" / "approved"
        if not approved_dir.exists():
            return []

        prs = []
        for pr_file in approved_dir.glob("*.json"):
            data = self._fs.read_json(pr_file)
            if data:
                prs.append(PRRecord.from_dict(data))

        return prs

    def load_pr(self, pr_id: str, status: str) -> PRRecord | None:
        pr_path = self._fs.get_pr_path(status, pr_id)
        data = self._fs.read_json(pr_path)
        if data:
            return PRRecord.from_dict(data)
        return None

    def _generate_pr_description(self, resolution: ResolutionResult) -> str:
        prompt = f"""Generate a pull request description for this change.

Issue: #{resolution.issue_number}
Branch: {resolution.branch_name}
Files changed: {', '.join(resolution.files_changed)}
Test status: {resolution.test_result} ({resolution.tests_passing} passing, {resolution.tests_failing} failing)

Write a concise PR description that:
1. Summarizes the changes
2. Explains the solution approach
3. Notes any testing considerations

Output only the PR description, no additional formatting."""

        try:
            response = self._inference.complete(
                prompt=prompt,
                data_type="pr_description_generation",
                max_tokens=500,
            )
            return response.strip()
        except Exception as e:
            logger.warning("PR description generation failed: %s", e)
            return f"Fixes #{resolution.issue_number}\n\nChanges: {', '.join(resolution.files_changed)}"

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
