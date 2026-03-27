#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Content Filesystem Initialization

Creates and validates the full /sandbox/content/ filesystem structure.
Called during onboarding and on every claw startup to ensure
required directories and files exist.

Usage:
    from content.content_init import ContentFilesystemInit, ContentOperationalLog

    fs = ContentFilesystemInit()
    result = fs.initialize()
    if not result.success:
        print(f"Failed: {result.errors}")

    log = ContentOperationalLog(fs.BASE / "logs" / "operational.log")
    log.append(LogEntry(
        action_type="draft_generated",
        entity_id="draft-123",
        outcome="success",
        details={"platform": "twitter"}
    ))
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("milimo.content_init")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class InitResult:
    """Result of filesystem initialization."""

    success: bool
    created: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of filesystem validation."""

    valid: bool
    missing_paths: list[str] = field(default_factory=list)
    invalid_log_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LogEntry:
    """A single entry in the operational log."""

    timestamp: str
    action_type: str
    entity_id: str
    platform: str | None
    client_id: str | None
    outcome: str
    details: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        timestamp: str | None = None,
        platform: str | None = None,
        client_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.action_type = action_type
        self.entity_id = entity_id
        self.platform = platform
        self.client_id = client_id
        self.outcome = outcome
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "entity_id": self.entity_id,
            "platform": self.platform,
            "client_id": self.client_id,
            "outcome": self.outcome,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        return cls(
            timestamp=data.get("timestamp"),
            action_type=data["action_type"],
            entity_id=data["entity_id"],
            platform=data.get("platform"),
            client_id=data.get("client_id"),
            outcome=data["outcome"],
            details=data.get("details"),
        )


# ---------------------------------------------------------------------------
# Content Filesystem Init
# ---------------------------------------------------------------------------


class ContentFilesystemInit:
    """
    Creates and validates the full /sandbox/content/ filesystem structure.

    Called during onboarding and on every claw startup to ensure
    required directories and files exist.
    """

    BASE = Path("/sandbox/content")

    REQUIRED_DIRS = [
        "brand/style-guides",
        "brand/assets",
        "brand/voice-profiles",
        "drafts/pending",
        "drafts/approved",
        "drafts/rejected",
        "drafts/published",
        "briefs/active",
        "briefs/completed",
        "calendar/scheduled",
        "calendar/published",
        "intelligence/analytics-feed",
        "tools/style-descriptor",
        "tools/tone-classifier",
        "tools/approval-predictor",
        "tools/timing-optimizer",
        "tools/ab-variant-engine",
        "tools/platform-calibrator",
        "tools/client-voice-adapter",
        "tools/trend-injector",
        "logs",
    ]

    REQUIRED_LOG_FILES = [
        "logs/operational.log",
        "logs/approvals.log",
        "logs/performance.log",
    ]

    REQUIRED_INTEL_FILES = [
        "intelligence/analytics-feed/weekly-intelligence.json",
    ]

    def __init__(self, base_path: Path | None = None, squad_id: str | None = None):
        """
        Initialize filesystem manager.

        Args:
            base_path: Override default base path (for testing)
            squad_id: Squad identifier for fallback path
        """
        if base_path:
            self.BASE = base_path
        else:
            # Check for fallback to user directory
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            sandbox_base = Path(home) / ".milimo" / "sandboxes"

            if squad_id:
                self.BASE = sandbox_base / squad_id / "content"
            else:
                # Try /sandbox/content first, fall back to user directory
                if Path("/sandbox/content").exists() or os.access("/sandbox", os.W_OK):
                    self.BASE = Path("/sandbox/content")
                else:
                    self.BASE = sandbox_base / "default" / "content"

        self.BASE.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> InitResult:
        """
        Creates all directories and log files if they don't exist.
        Never overwrites existing files.

        Returns:
            InitResult with created, already_existed, failed counts
        """
        result = InitResult(success=True)

        # Create all required directories
        for dir_path in self.REQUIRED_DIRS:
            full_path = self.BASE / dir_path
            try:
                if full_path.exists():
                    result.already_existed.append(str(full_path))
                else:
                    full_path.mkdir(parents=True, exist_ok=True)
                    result.created.append(str(full_path))
                    logger.debug("Created directory: %s", full_path)
            except OSError as e:
                result.failed.append(str(full_path))
                result.errors.append(f"Failed to create {full_path}: {e}")
                result.success = False
                logger.error("Failed to create directory %s: %s", full_path, e)

        # Create all required log files (empty if not exists)
        for log_file in self.REQUIRED_LOG_FILES:
            full_path = self.BASE / log_file
            try:
                if full_path.exists():
                    result.already_existed.append(str(full_path))
                else:
                    # Create empty file
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.touch()
                    result.created.append(str(full_path))
                    logger.debug("Created log file: %s", full_path)
            except OSError as e:
                result.failed.append(str(full_path))
                result.errors.append(f"Failed to create {full_path}: {e}")
                result.success = False
                logger.error("Failed to create log file %s: %s", full_path, e)

        # Create all required intelligence files (empty JSON if not exists)
        for intel_file in self.REQUIRED_INTEL_FILES:
            full_path = self.BASE / intel_file
            try:
                if full_path.exists():
                    result.already_existed.append(str(full_path))
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text("{}")
                    result.created.append(str(full_path))
                    logger.debug("Created intel file: %s", full_path)
            except OSError as e:
                result.failed.append(str(full_path))
                result.errors.append(f"Failed to create {full_path}: {e}")
                result.success = False
                logger.error("Failed to create intel file %s: %s", full_path, e)

        logger.info(
            "Filesystem init complete: %d created, %d existed, %d failed",
            len(result.created),
            len(result.already_existed),
            len(result.failed),
        )

        return result

    def validate(self) -> ValidationResult:
        """
        Checks all required paths exist.
        Does not create anything — pure validation.

        Returns:
            ValidationResult with list of missing paths
        """
        missing: list[str] = []
        invalid_logs: list[str] = []

        # Check directories
        for dir_path in self.REQUIRED_DIRS:
            full_path = self.BASE / dir_path
            if not full_path.is_dir():
                missing.append(str(full_path))

        # Check log files
        for log_file in self.REQUIRED_LOG_FILES:
            full_path = self.BASE / log_file
            if not full_path.is_file():
                invalid_logs.append(str(full_path))

        valid = len(missing) == 0 and len(invalid_logs) == 0

        if not valid:
            logger.warning(
                "Validation failed: %d missing dirs, %d missing logs",
                len(missing),
                len(invalid_logs),
            )

        return ValidationResult(
            valid=valid,
            missing_paths=missing,
            invalid_log_files=invalid_logs,
        )

    def get_draft_path(
        self,
        status: Literal["pending", "approved", "rejected", "published"],
        draft_id: str,
    ) -> Path:
        """
        Get the full path for a draft file.

        Args:
            status: Draft status directory
            draft_id: Unique draft identifier

        Returns:
            Full path to draft JSON file
        """
        return self.BASE / "drafts" / status / f"{draft_id}.json"

    def get_brief_path(
        self,
        status: Literal["active", "completed"],
        brief_id: str,
    ) -> Path:
        """
        Get the full path for a brief file.

        Args:
            status: Brief status directory
            brief_id: Unique brief identifier

        Returns:
            Full path to brief JSON file
        """
        return self.BASE / "briefs" / status / f"{brief_id}.json"

    def get_calendar_path(
        self,
        status: Literal["scheduled", "published"],
        item_id: str,
    ) -> Path:
        """
        Get the full path for a calendar item.

        Args:
            status: Calendar item status
            item_id: Unique item identifier

        Returns:
            Full path to calendar JSON file
        """
        return self.BASE / "calendar" / status / f"{item_id}.json"

    def get_voice_profile_path(self, client_id: str) -> Path:
        """Get the path for a client's voice profile."""
        return self.BASE / "brand" / "voice-profiles" / f"{client_id}.json"

    def get_style_guide_path(self, client_id: str | None = None) -> Path:
        """Get the path for a style guide (client-specific or default)."""
        name = f"{client_id}.md" if client_id else "default.md"
        return self.BASE / "brand" / "style-guides" / name


# ---------------------------------------------------------------------------
# Content Operational Log
# ---------------------------------------------------------------------------


class ContentOperationalLog:
    """
    Append-only structured log for all Content Claw actions.

    Thread-safe — uses file locking for concurrent writes.
    """

    def __init__(self, log_path: Path):
        """
        Initialize operational log.

        Args:
            log_path: Path to operational.log file
        """
        self._log_path = log_path
        self._lock_path = log_path.with_suffix(".lock")

        # Ensure log file exists
        if not self._log_path.exists():
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_path.touch()

    def append(self, entry: LogEntry) -> None:
        """
        Write a log entry to operational.log.
        Thread-safe — uses file locking.

        Args:
            entry: Log entry to append
        """
        line = json.dumps(entry.to_dict()) + "\n"

        # Use file locking for thread safety
        with open(self._log_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        logger.debug("Logged action: %s [%s]", entry.action_type, entry.outcome)

    def read_recent(
        self,
        days: int = 7,
        action_type: str | None = None,
    ) -> list[LogEntry]:
        """
        Read recent log entries.

        Args:
            days: Number of days to look back
            action_type: Filter by action type (optional)

        Returns:
            List of log entries, newest first
        """
        if not self._log_path.exists():
            return []

        entries: list[LogEntry] = []
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        try:
            with open(self._log_path, "r") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            entry = LogEntry.from_dict(data)

                            # Filter by timestamp
                            entry_time = datetime.fromisoformat(entry.timestamp).timestamp()
                            if entry_time < cutoff:
                                continue

                            # Filter by action type
                            if action_type and entry.action_type != action_type:
                                continue

                            entries.append(entry)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            logger.error("Failed to read log: %s", e)
            return []

        # Return newest first
        entries.reverse()
        return entries

    def count_by_type(self, action_type: str, days: int = 7) -> int:
        """
        Count log entries by action type.

        Args:
            action_type: Action type to count
            days: Number of days to look back

        Returns:
            Count of matching entries
        """
        entries = self.read_recent(days=days, action_type=action_type)
        return len(entries)

    def count_by_outcome(
        self,
        outcome: str,
        action_type: str | None = None,
        days: int = 7,
    ) -> int:
        """
        Count log entries by outcome.

        Args:
            outcome: Outcome to count (success, failed, etc.)
            action_type: Optional action type filter
            days: Number of days to look back

        Returns:
            Count of matching entries
        """
        entries = self.read_recent(days=days, action_type=action_type)
        return sum(1 for e in entries if e.outcome == outcome)

    def clear(self) -> None:
        """Clear the log file (for testing only)."""
        if self._log_path.exists():
            self._log_path.unlink()


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def generate_draft_id() -> str:
    """Generate a unique draft ID."""
    return f"draft-{uuid.uuid4().hex[:12]}"


def generate_brief_id() -> str:
    """Generate a unique brief ID."""
    return f"brief-{uuid.uuid4().hex[:12]}"


def generate_post_id() -> str:
    """Generate a unique post ID."""
    return f"post-{uuid.uuid4().hex[:12]}"
