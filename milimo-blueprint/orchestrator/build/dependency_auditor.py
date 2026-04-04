"""
Build Claw dependency auditor.

Handles:
- Vulnerability scanning
- Fix complexity assessment (simple, breaking_change, no_fix)
- Auto-draft security PRs for simple fixes
- Manual investigation queue for breaking changes
- Batch multiple simple fixes into single PR

Enhancement: File-based task dependency storage (from OmO).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build.build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from build.approval_handler import BuildApprovalHandler

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    package: str
    ecosystem: str
    current_version: str
    vulnerable_versions: str
    patched_version: str | None
    severity: str
    cve_id: str | None
    fix_complexity: str  # "simple", "breaking_change", "no_fix"


@dataclass
class AuditResult:
    vulnerabilities: list[Vulnerability]
    total_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    audited_at: str = ""

    def __post_init__(self) -> None:
        if not self.audited_at:
            self.audited_at = datetime.now(timezone.utc).isoformat()


class DependencyAuditor:
    """Audits project dependencies for vulnerabilities."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        github_client: Any,
        repo_path: Path,
    ) -> None:
        self._fs = fs
        self._approval = approval_handler
        self._log = operational_log
        self._github = github_client
        self._repo_path = repo_path

    # ------------------------------------------------------------------
    # Fix complexity assessment
    # ------------------------------------------------------------------

    def assess_fix_complexity(self, vuln: Vulnerability) -> str:
        """Assess whether a vulnerability fix is simple, breaking, or has no fix."""
        return vuln.fix_complexity

    # ------------------------------------------------------------------
    # Auto-draft security PR
    # ------------------------------------------------------------------

    def auto_draft_security_pr(self, vulns: list[Vulnerability]) -> str | None:
        """Batch simple fixes into a single security PR queued as REVIEW."""
        simple_fixes = [v for v in vulns if v.fix_complexity == "simple"]
        if not simple_fixes:
            return None

        vuln_data = [
            {
                "package": v.package,
                "current_version": v.current_version,
                "patched_version": v.patched_version,
                "severity": v.severity,
                "cve_id": v.cve_id,
            }
            for v in simple_fixes
        ]

        pr_id = f"security-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        action_id = self._approval.queue_security_pr(
            pr_id=pr_id,
            vulns=vuln_data,
            summary=f"Security update: {len(simple_fixes)} vulnerabilities",
        )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="security_pr_queued",
            entity_id=pr_id,
            outcome="queued",
            details={
                "vuln_count": len(simple_fixes),
                "action_id": action_id,
            },
        ))
        return action_id

    # ------------------------------------------------------------------
    # Breaking change handling
    # ------------------------------------------------------------------

    def queue_manual_investigation(self, vuln: Vulnerability) -> str:
        """Queue a REVIEW for manual investigation of breaking changes."""
        review_id = f"dep-review-{vuln.package}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        action_id = self._approval.queue_dependency_review(
            review_id=review_id,
            findings=[{
                "package": vuln.package,
                "current_version": vuln.current_version,
                "patched_version": vuln.patched_version,
                "severity": vuln.severity,
                "cve_id": vuln.cve_id,
                "complexity": "breaking_change",
            }],
            summary=f"Manual investigation needed: {vuln.package} {vuln.severity}",
        )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="dependency_review_queued",
            entity_id=review_id,
            outcome="queued",
            details={"package": vuln.package},
        ))
        return action_id

    # ------------------------------------------------------------------
    # No fix handling
    # ------------------------------------------------------------------

    def queue_no_fix_review(self, vuln: Vulnerability) -> str:
        """Queue REVIEW for vulnerabilities with no available fix."""
        review_id = f"no-fix-{vuln.package}"

        action_id = self._approval.queue_dependency_review(
            review_id=review_id,
            findings=[{
                "package": vuln.package,
                "severity": vuln.severity,
                "cve_id": vuln.cve_id,
                "complexity": "no_fix",
            }],
            summary=f"No fix available: {vuln.package} ({vuln.severity})",
        )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="no_fix_review_queued",
            entity_id=review_id,
            outcome="queued",
            details={"package": vuln.package},
        ))
        return action_id
