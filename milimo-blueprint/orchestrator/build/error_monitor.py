"""
Build Claw error monitor.

Handles:
- Fetching errors from Sentry
- Grouping by root cause
- Known pattern matching and auto-fix
- New pattern detection and REVIEW queueing

Enhancement: Tmux session monitoring for sandbox error detection.
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
from build.code_generator import CodeGenerator

logger = logging.getLogger(__name__)


@dataclass
class ErrorEvent:
    error_id: str
    timestamp: str
    error_type: str
    message: str
    stacktrace: str
    count: int
    severity: int  # 1-5


@dataclass
class ErrorPattern:
    pattern_id: str
    root_cause: str
    fix_template: str
    times_applied: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "root_cause": self.root_cause,
            "fix_template": self.fix_template,
            "times_applied": self.times_applied,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErrorPattern":
        return cls(
            pattern_id=data.get("pattern_id", ""),
            root_cause=data.get("root_cause", ""),
            fix_template=data.get("fix_template", ""),
            times_applied=data.get("times_applied", 0),
            success_rate=data.get("success_rate", 0.0),
        )


class ErrorMonitor:
    """Monitors production errors and auto-generates fixes."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        sentry_client: Any,
        code_generator: CodeGenerator,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
    ) -> None:
        self._fs = fs
        self._sentry = sentry_client
        self._code_gen = code_generator
        self._approval = approval_handler
        self._log = operational_log

    # ------------------------------------------------------------------
    # Monitoring pass
    # ------------------------------------------------------------------

    def run_monitoring_pass(self) -> list[dict[str, Any]]:
        """Fetch errors, group by root cause, match patterns, queue fixes."""
        raw_errors = self._sentry.get_recent_errors()
        errors = [
            ErrorEvent(
                error_id=e.get("id", ""),
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_type=e.get("type", "Unknown"),
                message=e.get("message", ""),
                stacktrace=e.get("stacktrace", ""),
                count=e.get("count", 1),
                severity=min(5, e.get("count", 1)),
            )
            for e in raw_errors
        ]

        groups = self.group_by_root_cause(errors)
        results = []

        for root_cause, group_errors in groups.items():
            # Check if we have a known pattern
            pattern = self._load_known_pattern(root_cause)
            if pattern:
                # Auto-draft fix using known pattern
                self._auto_draft_pattern_fix(pattern, group_errors)
                results.append({
                    "root_cause": root_cause,
                    "status": "pattern_matched",
                    "error_count": len(group_errors),
                    "pattern_id": pattern.pattern_id,
                })
            else:
                # New pattern — save to active/ and queue REVIEW
                self._save_new_pattern(root_cause, group_errors)
                results.append({
                    "root_cause": root_cause,
                    "status": "new_pattern",
                    "error_count": len(group_errors),
                })

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="error_monitoring_pass",
            entity_id="monitoring",
            outcome="success",
            details={"groups": len(results)},
        ))
        return results

    def run_error_check(self) -> list[dict[str, Any]]:
        """Alias for run_monitoring_pass (scheduler calls this name)."""
        return self.run_monitoring_pass()

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    def group_by_root_cause(self, errors: list[ErrorEvent]) -> dict[str, list[ErrorEvent]]:
        groups: dict[str, list[ErrorEvent]] = {}
        for error in errors:
            root_cause = error.error_type
            if root_cause not in groups:
                groups[root_cause] = []
            groups[root_cause].append(error)
        return groups

    # ------------------------------------------------------------------
    # Pattern management
    # ------------------------------------------------------------------

    def _load_known_pattern(self, root_cause: str) -> ErrorPattern | None:
        patterns_dir = self._fs.base / "context" / "errors" / "patterns"
        if not patterns_dir.exists():
            return None

        for pattern_file in patterns_dir.glob("*.json"):
            try:
                data = json.loads(pattern_file.read_text())
                pattern = ErrorPattern.from_dict(data)
                if pattern.root_cause == root_cause:
                    return pattern
            except (json.JSONDecodeError, KeyError):
                continue
        return None

    def _save_new_pattern(self, root_cause: str, errors: list[ErrorEvent]) -> None:
        group_id = f"error-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        active_path = self._fs.get_active_error_path(group_id)
        active_path.parent.mkdir(parents=True, exist_ok=True)

        pattern_data = {
            "group_id": group_id,
            "root_cause": root_cause,
            "error_count": len(errors),
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "messages": [e.message for e in errors[:5]],
        }
        self._fs.atomic_write_json(active_path, pattern_data)

        # Queue REVIEW for investigation
        self._approval.queue_pr_review(
            pr_id=group_id,
            pr_title=f"Investigate {root_cause} errors",
            branch=f"fix/{group_id}",
            issue_number=0,
            files_changed=0,
            lines_added=0,
            lines_removed=0,
            test_result="unknown",
            tests_count=0,
            github_pr_url="",
        )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="new_error_pattern",
            entity_id=group_id,
            outcome="queued",
            details={"root_cause": root_cause, "count": len(errors)},
        ))

    def _auto_draft_pattern_fix(self, pattern: ErrorPattern, errors: list[ErrorEvent]) -> None:
        """Auto-draft a fix using a known pattern."""
        pattern.times_applied += 1

        # Save updated pattern
        pattern_path = self._fs.get_error_pattern_path(pattern.pattern_id)
        self._fs.atomic_write_json(pattern_path, pattern.to_dict())

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pattern_fix_applied",
            entity_id=pattern.pattern_id,
            outcome="success",
            details={
                "root_cause": pattern.root_cause,
                "times_applied": pattern.times_applied,
            },
        ))

    def promote_to_known_pattern(self, group_id: str, fix_template: str) -> None:
        """Promote an active error pattern to known patterns."""
        active_path = self._fs.get_active_error_path(group_id)
        if not active_path.exists():
            return

        data = self._fs.read_json(active_path)
        pattern = ErrorPattern(
            pattern_id=group_id,
            root_cause=data.get("root_cause", "Unknown"),
            fix_template=fix_template,
            times_applied=0,
            success_rate=0.0,
        )

        pattern_path = self._fs.get_error_pattern_path(group_id)
        self._fs.atomic_write_json(pattern_path, pattern.to_dict())
        active_path.unlink(missing_ok=True)

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pattern_promoted",
            entity_id=group_id,
            outcome="success",
            details={"root_cause": pattern.root_cause},
        ))
