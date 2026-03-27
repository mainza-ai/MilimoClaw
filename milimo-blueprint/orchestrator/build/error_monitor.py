#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Error Monitor

Monitors production errors via Sentry API every 30 minutes.

For known patterns: auto-draft patch PR, queue as REVIEW.
For new patterns: write to context/errors/active/, queue REVIEW.
Patterns accumulate in context/errors/patterns/ over time.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .code_generator import CodeGenerator

logger = logging.getLogger("milimo.build")


@dataclass
class ErrorEvent:
    """A single error event from Sentry."""

    event_id: str
    timestamp: str
    error_type: str
    message: str
    stack_trace: str
    occurrence_count: int
    affected_users: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "error_type": self.error_type,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "occurrence_count": self.occurrence_count,
            "affected_users": self.affected_users,
        }


@dataclass
class ErrorGroup:
    """A group of related errors."""

    group_id: str
    root_cause: str
    error_count: int
    events: list[ErrorEvent]
    first_seen: str
    last_seen: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "root_cause": self.root_cause,
            "error_count": self.error_count,
            "events": [e.to_dict() for e in self.events],
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class ErrorPattern:
    """A known error pattern with fix template."""

    pattern_id: str
    root_cause: str
    fix_template: str
    times_applied: int
    success_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "root_cause": self.root_cause,
            "fix_template": self.fix_template,
            "times_applied": self.times_applied,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ErrorPattern:
        return cls(
            pattern_id=data["pattern_id"],
            root_cause=data["root_cause"],
            fix_template=data["fix_template"],
            times_applied=data.get("times_applied", 0),
            success_rate=data.get("success_rate", 0.0),
        )


class ErrorMonitor:
    """
    Monitors production errors via Sentry API every 30 minutes.

    For known patterns: auto-draft patch PR, queue as REVIEW.
    For new patterns: write to context/errors/active/, queue REVIEW.
    Patterns accumulate in context/errors/patterns/ over time.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        sentry_client: Any,
        code_generator: CodeGenerator,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
    ):
        self._fs = fs
        self._sentry = sentry_client
        self._code_generator = code_generator
        self._approval = approval_handler
        self._log = operational_log

    def run_monitoring_pass(self) -> list[ErrorGroup]:
        errors = self.fetch_recent_errors()
        if not errors:
            self._log.append(self._create_log_entry(
                "error_monitoring_pass",
                "monitoring",
                "success",
                {"errors_found": 0},
            ))
            return []

        groups = self.group_by_root_cause(errors)

        for group in groups:
            pattern = self.check_known_patterns(group)

            if pattern:
                self.auto_draft_patch(group, pattern)
            else:
                self.save_new_pattern(group)

        self._log.append(self._create_log_entry(
            "error_monitoring_pass",
            "monitoring",
            "success",
            {"errors_found": len(errors), "groups": len(groups)},
        ))

        return groups

    def fetch_recent_errors(self) -> list[ErrorEvent]:
        if not self._sentry:
            logger.debug("Sentry client not configured")
            return []

        try:
            raw_errors = self._sentry.get_recent_errors()
        except Exception as e:
            logger.error("Failed to fetch Sentry errors: %s", e)
            return []

        events = []
        for raw in raw_errors:
            event = ErrorEvent(
                event_id=raw.get("id", uuid.uuid4().hex[:12]),
                timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
                error_type=raw.get("type", "Unknown"),
                message=raw.get("message", ""),
                stack_trace=raw.get("stacktrace", ""),
                occurrence_count=raw.get("count", 1),
                affected_users=raw.get("users", 0),
            )
            events.append(event)

        return events

    def group_by_root_cause(self, errors: list[ErrorEvent]) -> list[ErrorGroup]:
        groups_by_type: dict[str, list[ErrorEvent]] = {}

        for error in errors:
            key = self._extract_root_cause_key(error)
            if key not in groups_by_type:
                groups_by_type[key] = []
            groups_by_type[key].append(error)

        groups = []
        for root_cause, events in groups_by_type.items():
            group = ErrorGroup(
                group_id=f"error-{uuid.uuid4().hex[:8]}",
                root_cause=root_cause,
                error_count=len(events),
                events=events,
                first_seen=min(e.timestamp for e in events),
                last_seen=max(e.timestamp for e in events),
            )
            groups.append(group)

        return groups

    def check_known_patterns(self, group: ErrorGroup) -> ErrorPattern | None:
        pattern_ids = self._fs.list_error_patterns()

        for pattern_id in pattern_ids:
            pattern_path = self._fs.get_error_pattern_path(pattern_id)
            data = self._fs.read_json(pattern_path)

            if data:
                pattern = ErrorPattern.from_dict(data)
                if self._root_cause_matches(group.root_cause, pattern.root_cause):
                    return pattern

        return None

    def auto_draft_patch(self, group: ErrorGroup, pattern: ErrorPattern) -> None:
        self._approval.queue_error_pattern_review(
            error_id=group.group_id,
            error_summary=group.root_cause[:100],
            occurrence_count=group.error_count,
            is_known_pattern=True,
            auto_patch_available=True,
        )

        self._log.append(self._create_log_entry(
            "error_patch_drafted",
            group.group_id,
            "review_queued",
            {"pattern_id": pattern.pattern_id, "occurrences": group.error_count},
        ))

    def save_new_pattern(self, group: ErrorGroup) -> str:
        active_path = self._fs.get_active_error_path(group.group_id)

        pattern_data = {
            "group_id": group.group_id,
            "root_cause": group.root_cause,
            "error_count": group.error_count,
            "first_seen": group.first_seen,
            "last_seen": group.last_seen,
            "events": [e.to_dict() for e in group.events[:5]],
            "status": "new",
        }

        self._fs.atomic_write_json(active_path, pattern_data)

        self._approval.queue_error_pattern_review(
            error_id=group.group_id,
            error_summary=group.root_cause[:100],
            occurrence_count=group.error_count,
            is_known_pattern=False,
            auto_patch_available=False,
        )

        self._log.append(self._create_log_entry(
            "new_error_pattern_saved",
            group.group_id,
            "review_queued",
            {"root_cause": group.root_cause[:50], "occurrences": group.error_count},
        ))

        return group.group_id

    def promote_to_known_pattern(
        self,
        group_id: str,
        fix_template: str,
    ) -> None:
        active_path = self._fs.get_active_error_path(group_id)
        data = self._fs.read_json(active_path)

        if not data:
            logger.error("Active error not found: %s", group_id)
            return

        pattern = ErrorPattern(
            pattern_id=f"pattern-{uuid.uuid4().hex[:8]}",
            root_cause=data.get("root_cause", ""),
            fix_template=fix_template,
            times_applied=0,
            success_rate=0.0,
        )

        pattern_path = self._fs.get_error_pattern_path(pattern.pattern_id)
        self._fs.atomic_write_json(pattern_path, pattern.to_dict())

        if active_path.exists():
            active_path.unlink()

        self._log.append(self._create_log_entry(
            "error_pattern_promoted",
            pattern.pattern_id,
            "success",
            {"group_id": group_id},
        ))

    def _extract_root_cause_key(self, error: ErrorEvent) -> str:
        if error.stack_trace:
            lines = error.stack_trace.split("\n")[:3]
            return f"{error.error_type}:{':'.join(lines)}"
        return f"{error.error_type}:{error.message[:50]}"

    def _root_cause_matches(self, cause1: str, cause2: str) -> bool:
        return cause1.split(":")[0] == cause2.split(":")[0]

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
