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

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from .approval_handler import BuildApprovalHandler

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

    # ------------------------------------------------------------------
    # Full audit execution
    # ------------------------------------------------------------------

    def run_full_audit(self) -> AuditResult:
        """Run a complete vulnerability audit on the repository.

        Fetches Dependabot alerts and code scanning alerts from GitHub,
        assesses fix complexity for each, and handles them appropriately:
        - Simple fixes: batched into a security PR
        - Breaking changes: queued for manual investigation
        - No fix available: queued for no-fix review

        Returns:
            AuditResult with vulnerability summary.
        """
        logger.info("Running full dependency audit on %s", self._repo_path)

        # Fetch vulnerabilities from GitHub
        dependabot_alerts = self._github.get_dependabot_alerts()
        code_scanning_alerts = self._github.get_code_scanning_alerts()

        vulnerabilities = []

        # Process Dependabot alerts
        for alert in dependabot_alerts:
            vuln = Vulnerability(
                package=alert.get("package", "unknown"),
                ecosystem=alert.get("ecosystem", "unknown"),
                current_version=alert.get("current_version", "unknown"),
                vulnerable_versions=alert.get("vulnerable_versions", ""),
                patched_version=alert.get("patched_version"),
                severity=alert.get("severity", "medium"),
                cve_id=alert.get("cve_id"),
                fix_complexity=alert.get("fix_complexity", "simple"),
            )
            vulnerabilities.append(vuln)

        # Process code scanning alerts
        for alert in code_scanning_alerts:
            vuln = Vulnerability(
                package=alert.get("tool", "code-scanning"),
                ecosystem="code",
                current_version="",
                vulnerable_versions="",
                patched_version=None,
                severity=alert.get("severity", "medium"),
                cve_id=alert.get("cve_id"),
                fix_complexity=alert.get("fix_complexity", "simple"),
            )
            vulnerabilities.append(vuln)

        # Count by severity
        critical_count = sum(1 for v in vulnerabilities if v.severity == "critical")
        high_count = sum(1 for v in vulnerabilities if v.severity == "high")
        medium_count = sum(1 for v in vulnerabilities if v.severity == "medium")
        low_count = sum(1 for v in vulnerabilities if v.severity == "low")

        # Handle vulnerabilities based on fix complexity
        simple_fixes = []
        for vuln in vulnerabilities:
            complexity = self.assess_fix_complexity(vuln)
            if complexity == "simple":
                simple_fixes.append(vuln)
            elif complexity == "breaking_change":
                self.queue_manual_investigation(vuln)
            elif complexity == "no_fix":
                self.queue_no_fix_review(vuln)

        # Batch simple fixes into a single security PR
        if simple_fixes:
            self.auto_draft_security_pr(simple_fixes)

        result = AuditResult(
            vulnerabilities=vulnerabilities,
            total_count=len(vulnerabilities),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )

        logger.info(
            "Dependency audit complete: %d vulnerabilities (%d critical, %d high, %d medium, %d low)",
            result.total_count,
            result.critical_count,
            result.high_count,
            result.medium_count,
            result.low_count,
        )

        return result
