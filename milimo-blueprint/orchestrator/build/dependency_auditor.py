#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Dependency Auditor

Weekly dependency security audit (Monday 08:00).

Simple fix path (non-breaking version bump): auto-draft PR → REVIEW
Breaking change or no fix: queue REVIEW for manual investigation.
All PRs from auditor are security-labelled — REVIEW, not AUTO.
"""

from __future__ import annotations

import logging
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler
    from .build_init import BuildFilesystemInit, BuildOperationalLog

logger = logging.getLogger("milimo.build")


@dataclass
class Vulnerability:
    """A dependency vulnerability."""

    package: str
    ecosystem: str
    current_version: str
    vulnerable_versions: str
    patched_version: str | None
    severity: str
    cve_id: str | None
    fix_complexity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "ecosystem": self.ecosystem,
            "current_version": self.current_version,
            "vulnerable_versions": self.vulnerable_versions,
            "patched_version": self.patched_version,
            "severity": self.severity,
            "cve_id": self.cve_id,
            "fix_complexity": self.fix_complexity,
        }


class DependencyAuditor:
    """
    Weekly dependency security audit (Monday 08:00).

    Simple fix path (non-breaking version bump): auto-draft PR → REVIEW
    Breaking change or no fix: queue REVIEW for manual investigation.
    All PRs from auditor are security-labelled — REVIEW, not AUTO.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        github_client: Any | None = None,
        repo_path: Path | None = None,
    ):
        self._fs = fs
        self._approval = approval_handler
        self._log = operational_log
        self._github = github_client
        self._repo_path = repo_path or Path("/sandbox/build/repo")

    def run_audit(self) -> list[Vulnerability]:
        project_type = self._detect_project_type()

        vulnerabilities: list[Vulnerability] = []

        if project_type in ("npm", "both"):
            npm_vulns = self._run_npm_audit()
            vulnerabilities.extend(npm_vulns)

        if project_type in ("python", "both"):
            python_vulns = self._run_pip_audit()
            vulnerabilities.extend(python_vulns)

        for vuln in vulnerabilities:
            vuln.fix_complexity = self.assess_fix_complexity(vuln)

        simple_vulns = [v for v in vulnerabilities if v.fix_complexity == "simple"]
        complex_vulns = [v for v in vulnerabilities if v.fix_complexity != "simple"]

        if simple_vulns:
            self.auto_draft_security_pr(simple_vulns)

        for vuln in complex_vulns:
            self.queue_manual_investigation(vuln)

        self._log.append(self._create_log_entry(
            "dependency_audit_complete",
            "audit",
            "success",
            {
                "total_vulns": len(vulnerabilities),
                "simple_fixes": len(simple_vulns),
                "complex_fixes": len(complex_vulns),
            },
        ))

        return vulnerabilities

    def assess_fix_complexity(self, vuln: Vulnerability) -> str:
        if not vuln.patched_version:
            return "no_fix"

        try:
            current_parts = [int(p) for p in vuln.current_version.split(".")[:2]]
            patched_parts = [int(p) for p in vuln.patched_version.split(".")[:2]]

            if patched_parts[0] > current_parts[0]:
                return "breaking_change"

            if len(patched_parts) > 1 and len(current_parts) > 1:
                if patched_parts[1] - current_parts[1] > 10:
                    return "breaking_change"

        except (ValueError, IndexError):
            pass

        return "simple"

    def auto_draft_security_pr(self, vulns: list[Vulnerability]) -> None:
        if not vulns:
            return

        vuln_ids = [v.cve_id or v.package for v in vulns]
        vuln_id = vulns[0].cve_id or vulns[0].package

        self._approval.queue_security_pr_review(
            vuln_id=vuln_id,
            package=", ".join(v.package for v in vulns),
            severity=vulns[0].severity,
            fix_description=f"Update {len(vulns)} packages: {', '.join(v.package for v in vulns)}",
        )

        self._log.append(self._create_log_entry(
            "security_pr_drafted",
            vuln_id,
            "review_queued",
            {"packages": [v.package for v in vulns]},
        ))

    def queue_manual_investigation(self, vuln: Vulnerability) -> None:
        self._approval.queue_security_pr_review(
            vuln_id=vuln.cve_id or vuln.package,
            package=vuln.package,
            severity=vuln.severity,
            fix_description=f"Manual investigation required: {vuln.fix_complexity}",
        )

        self._log.append(self._create_log_entry(
            "security_vuln_manual_investigation",
            vuln.package,
            "review_queued",
            {"cve": vuln.cve_id, "severity": vuln.severity},
        ))

    def _detect_project_type(self) -> str:
        repo = self._repo_path

        has_package_json = (repo / "package.json").exists()
        has_requirements = (repo / "requirements.txt").exists() or (repo / "pyproject.toml").exists()

        if has_package_json and has_requirements:
            return "both"
        elif has_package_json:
            return "npm"
        elif has_requirements:
            return "python"
        else:
            return "none"

    def _run_npm_audit(self) -> list[Vulnerability]:
        vulns: list[Vulnerability] = []

        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                import json
                try:
                    data = json.loads(result.stdout)
                    advisories = data.get("advisories", {})
                    for advisory in advisories.values() if isinstance(advisories, dict) else advisories:
                        vuln = Vulnerability(
                            package=advisory.get("module_name", "unknown"),
                            ecosystem="npm",
                            current_version=advisory.get("findings", [{}])[0].get("version", "unknown"),
                            vulnerable_versions=advisory.get("vulnerable_versions", ""),
                            patched_version=advisory.get("patched_versions", "").replace(">= ", "").split(" <")[0] if advisory.get("patched_versions") else None,
                            severity=advisory.get("severity", "medium"),
                            cve_id=advisory.get("cves", [None])[0] if advisory.get("cves") else None,
                            fix_complexity="unknown",
                        )
                        vulns.append(vuln)
                except json.JSONDecodeError:
                    pass

        except subprocess.TimeoutExpired:
            logger.warning("npm audit timed out")
        except FileNotFoundError:
            logger.warning("npm not found")
        except Exception as e:
            logger.error("npm audit failed: %s", e)

        return vulns

    def _run_pip_audit(self) -> list[Vulnerability]:
        vulns: list[Vulnerability] = []

        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            import json
            try:
                data = json.loads(result.stdout)
                for item in data.get("vulnerabilities", []):
                    vuln = Vulnerability(
                        package=item.get("package", "unknown"),
                        ecosystem="pypi",
                        current_version=item.get("version", "unknown"),
                        vulnerable_versions=item.get("affected_range", ""),
                        patched_version=item.get("fix_versions", [None])[0] if item.get("fix_versions") else None,
                        severity=item.get("severity", "medium"),
                        cve_id=item.get("cve_id"),
                        fix_complexity="unknown",
                    )
                    vulns.append(vuln)
            except json.JSONDecodeError:
                pass

        except subprocess.TimeoutExpired:
            logger.warning("pip-audit timed out")
        except FileNotFoundError:
            logger.warning("pip-audit not found")
        except Exception as e:
            logger.error("pip-audit failed: %s", e)

        return vulns

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
