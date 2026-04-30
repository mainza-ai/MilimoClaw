# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Claw Filesystem Initialization

Creates and validates the full /sandbox/analytics/ filesystem structure.
Called during onboarding and on every claw startup.
Idempotent — safe to call multiple times.
"""

from __future__ import annotations

import json
import logging
import fcntl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("milimo.analytics_init")

from milimo_paths import claw_base

BASE = claw_base("analytics")

REQUIRED_DIRS = [
    "reports/weekly-intelligence-archive",
    "signals/anomalies",
    "signals/opportunities",
    "signals/alerts",
    "data/content-performance",
    "data/client-health",
    "data/revenue",
    "data/delivery-velocity",
    "baselines",
    "tools/engagement-baseline-model",
    "tools/anomaly-detector",
    "tools/opportunity-scorer",
    "tools/retention-correlator",
    "tools/competitor-signal-tracker",
    "tools/forward-projection-engine",
    "logs",
]

REQUIRED_FILES = [
    "logs/operational.log",
    "logs/queries.log",
    "logs/signals.log",
    "reports/opportunity-scores.json",
    "reports/monthly-summary.json",
]


@dataclass
class InitResult:
    """Result of filesystem initialization."""

    created_dirs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


@dataclass
class ValidationResult:
    """Result of filesystem validation."""

    missing_dirs: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_dirs and not self.missing_files


@dataclass
class AnalyticsLogEntry:
    """Structured log entry for Analytics Claw operations."""

    timestamp: str
    action_type: str
    entity_id: str
    source_claw: str | None
    outcome: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "action_type": self.action_type,
                "entity_id": self.entity_id,
                "source_claw": self.source_claw,
                "outcome": self.outcome,
                "details": self.details,
            }
        )


class AnalyticsOperationalLog:
    """
    Append-only structured log for all Analytics Claw actions.

    Uses file locking for thread-safe writes.
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._lock_path = Path(str(log_path) + ".lock")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not log_path.exists():
            log_path.touch()

    def append(self, entry: AnalyticsLogEntry) -> None:
        """Write JSON line with thread-safe file locking."""
        with open(self.log_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(entry.to_json() + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_recent(
        self,
        days: int = 7,
        action_type: str | None = None,
    ) -> list[AnalyticsLogEntry]:
        """Read recent log entries, optionally filtered by action_type.

        Returns entries from the last N days plus today (N+1 days total).
        So days=3 returns entries from today and the past 3 days.
        """
        entries: list[AnalyticsLogEntry] = []
        cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(
            days=days
        )
        cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)

        if not self.log_path.exists():
            return entries

        try:
            with open(self.log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = AnalyticsLogEntry(
                            timestamp=data.get("timestamp", ""),
                            action_type=data.get("action_type", ""),
                            entity_id=data.get("entity_id", ""),
                            source_claw=data.get("source_claw"),
                            outcome=data.get("outcome", ""),
                            details=data.get("details", {}),
                        )
                        if action_type and entry.action_type != action_type:
                            continue
                        try:
                            entry_time = datetime.fromisoformat(entry.timestamp)
                            if entry_time >= cutoff:
                                entries.append(entry)
                        except ValueError:
                            continue
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("Failed to read log: %s", e)

        return sorted(entries, key=lambda x: x.timestamp, reverse=True)

    def count_by_type(self, action_type: str, days: int = 7) -> int:
        """Count entries of a specific action_type in the last N days."""
        return len(self.read_recent(days=days, action_type=action_type))


class AnalyticsFilesystemInit:
    """
    Creates and validates the full /sandbox/analytics/ filesystem structure.

    Called during onboarding and on every claw startup.
    Idempotent — safe to call multiple times.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self.base = base_path or BASE

    def initialize(self) -> InitResult:
        """
        Create all required directories and files.

        Idempotent — does not overwrite existing files.
        """
        result = InitResult()

        for rel_dir in REQUIRED_DIRS:
            dir_path = self.base / rel_dir
            try:
                if dir_path.exists():
                    result.already_existed.append(rel_dir)
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    result.created_dirs.append(rel_dir)
                    logger.debug("Created directory: %s", rel_dir)
            except Exception as e:
                result.failed.append((rel_dir, str(e)))
                logger.error("Failed to create directory %s: %s", rel_dir, e)

        for rel_file in REQUIRED_FILES:
            file_path = self.base / rel_file
            try:
                if file_path.exists():
                    result.already_existed.append(rel_file)
                else:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    if rel_file.endswith(".json"):
                        file_path.write_text("{}\n")
                    else:
                        file_path.touch()
                    result.created_files.append(rel_file)
                    logger.debug("Created file: %s", rel_file)
            except Exception as e:
                result.failed.append((rel_file, str(e)))
                logger.error("Failed to create file %s: %s", rel_file, e)

        logger.info(
            "Analytics filesystem init: %d dirs created, %d files created, %d existed, %d failed",
            len(result.created_dirs),
            len(result.created_files),
            len(result.already_existed),
            len(result.failed),
        )

        return result

    def validate(self) -> ValidationResult:
        """
        Check all required paths exist.

        Never raises, never creates. Returns validation result.
        """
        result = ValidationResult()

        for rel_dir in REQUIRED_DIRS:
            dir_path = self.base / rel_dir
            if not dir_path.is_dir():
                result.missing_dirs.append(rel_dir)

        for rel_file in REQUIRED_FILES:
            file_path = self.base / rel_file
            if not file_path.is_file():
                result.missing_files.append(rel_file)

        return result

    def get_signal_path(
        self,
        signal_type: Literal["anomalies", "opportunities", "alerts"],
        signal_id: str,
    ) -> Path:
        """Get the path for a signal file."""
        return self.base / "signals" / signal_type / f"{signal_id}.json"

    def get_data_path(
        self,
        data_type: str,
        sub_path: str = "",
    ) -> Path:
        """Get the path for data storage."""
        path = self.base / "data" / data_type
        if sub_path:
            path = path / sub_path
        return path

    def get_report_path(self, report_name: str = "weekly-intelligence.json") -> Path:
        """Get the path for a report file."""
        return self.base / "reports" / report_name

    def get_archive_path(self, date_str: str) -> Path:
        """Get the archive path for a specific date."""
        return (
            self.base / "reports" / "weekly-intelligence-archive" / f"{date_str}.json"
        )

    def get_baseline_path(self, baseline_type: str) -> Path:
        """Get the path for a baseline file."""
        return self.base / "baselines" / f"{baseline_type}-baseline.json"

    def get_log_path(self, log_name: str) -> Path:
        """Get the path for a log file."""
        return self.base / "logs" / log_name
