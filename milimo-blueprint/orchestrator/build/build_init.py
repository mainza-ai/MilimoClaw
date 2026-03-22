#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Filesystem Initialization

Creates and validates the full /sandbox/build/ filesystem structure.
Idempotent — safe to call on every claw startup.
"""

from __future__ import annotations

import fcntl
import json
import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("milimo.build")

BASE = Path("/sandbox/build")

REQUIRED_DIRS = [
    "repo",
    "context/sprint",
    "context/errors/patterns",
    "context/errors/active",
    "context/costs",
    "prs/drafted",
    "prs/approved",
    "prs/merged",
    "deployments/pending",
    "deployments/history",
    "docs/api-reference",
    "docs/devlog",
    "logs",
]

REQUIRED_FILES: dict[str, Any] = {
    "context/sprint/current-plan.json": {
        "plan_id": None,
        "generated_at": None,
        "approved_at": None,
        "issues": [],
        "total_estimated_hours": 0,
        "status": "empty",
    },
    "context/sprint/backlog-scored.json": {
        "last_updated": None,
        "issues": [],
    },
    "context/sprint/velocity.json": {
        "sprints": [],
        "avg_hours_per_week": 0,
        "estimation_accuracy_pct": 0,
    },
    "context/costs/inference-weekly.json": {
        "week_of": None,
        "total_cost_usd": 0.0,
        "cost_per_user": 0.0,
        "baseline_cost_usd": 0.0,
        "drift_pct": 0.0,
        "last_updated": None,
    },
    "docs/changelog.md": "# Changelog\n\nAll notable changes documented here.\n",
    "logs/operational.log": None,
    "logs/pr-activity.log": None,
    "logs/deploy-activity.log": None,
    "logs/cost-alerts.log": None,
}


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
class BuildLogEntry:
    """Entry in the operational log."""

    timestamp: str
    action_type: str
    entity_id: str
    outcome: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "entity_id": self.entity_id,
            "outcome": self.outcome,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildLogEntry:
        return cls(
            timestamp=data["timestamp"],
            action_type=data["action_type"],
            entity_id=data["entity_id"],
            outcome=data["outcome"],
            details=data.get("details", {}),
        )


class BuildOperationalLog:
    """
    Append-only structured log for Build Claw actions.
    Thread-safe via fcntl file locking.
    """

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.touch()

    def append(self, entry: BuildLogEntry) -> None:
        with self._log_path.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry.to_dict()) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_recent(
        self, days: int = 30, action_type: str | None = None
    ) -> list[BuildLogEntry]:
        entries: list[BuildLogEntry] = []
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        if not self._log_path.exists():
            return entries

        with self._log_path.open("r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = BuildLogEntry.from_dict(data)
                        entry_time = datetime.fromisoformat(entry.timestamp).timestamp()
                        if entry_time >= cutoff:
                            if action_type is None or entry.action_type == action_type:
                                entries.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return entries

    def count_by_type(self, action_type: str, days: int = 30) -> int:
        return len(self.read_recent(days=days, action_type=action_type))

    def get_last_run_time(self, action_type: str) -> str | None:
        entries = self.read_recent(days=30, action_type=action_type)
        if not entries:
            return None
        sorted_entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)
        return sorted_entries[0].timestamp


class BuildFilesystemInit:
    """
    Creates and validates the full /sandbox/build/ filesystem structure.
    Idempotent — safe to call on every claw startup.
    """

    def __init__(self, base_path: Path | None = None):
        self._base = base_path or BASE

    def initialize(self) -> InitResult:
        result = InitResult()

        for dir_name in REQUIRED_DIRS:
            dir_path = self._base / dir_name
            try:
                if dir_path.exists():
                    result.already_existed.append(dir_name)
                else:
                    dir_path.mkdir(parents=True)
                    result.created_dirs.append(dir_name)
                    logger.info("Created directory: %s", dir_path)
            except OSError as e:
                result.failed.append((dir_name, str(e)))
                logger.error("Failed to create directory %s: %s", dir_path, e)

        for file_path, content in REQUIRED_FILES.items():
            full_path = self._base / file_path
            try:
                if full_path.exists():
                    result.already_existed.append(file_path)
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    if content is None:
                        full_path.touch()
                    elif isinstance(content, str):
                        full_path.write_text(content)
                    else:
                        full_path.write_text(json.dumps(content, indent=2))
                    result.created_files.append(file_path)
                    logger.info("Created file: %s", full_path)
            except OSError as e:
                result.failed.append((file_path, str(e)))
                logger.error("Failed to create file %s: %s", full_path, e)

        return result

    def validate(self) -> ValidationResult:
        result = ValidationResult()

        for dir_name in REQUIRED_DIRS:
            dir_path = self._base / dir_name
            if not dir_path.is_dir():
                result.missing_dirs.append(dir_name)

        for file_path in REQUIRED_FILES:
            full_path = self._base / file_path
            if not full_path.is_file():
                result.missing_files.append(file_path)

        return result

    def get_pr_path(
        self, status: str, pr_id: str
    ) -> Path:
        valid_statuses = {"drafted", "approved", "merged"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid PR status: {status}. Must be one of {valid_statuses}")
        return self._base / "prs" / status / f"{pr_id}.json"

    def get_deploy_path(
        self, status: str, deploy_id: str
    ) -> Path:
        valid_statuses = {"pending", "history"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid deploy status: {status}. Must be one of {valid_statuses}")
        return self._base / "deployments" / status / f"{deploy_id}.json"

    def get_error_pattern_path(self, pattern_id: str) -> Path:
        return self._base / "context" / "errors" / "patterns" / f"{pattern_id}.json"

    def get_active_error_path(self, error_id: str) -> Path:
        return self._base / "context" / "errors" / "active" / f"{error_id}.json"

    def atomic_write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with open(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            Path(tmp_path).rename(path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def get_sprint_plan_path(self) -> Path:
        return self._base / "context" / "sprint" / "current-plan.json"

    def get_backlog_path(self) -> Path:
        return self._base / "context" / "sprint" / "backlog-scored.json"

    def get_velocity_path(self) -> Path:
        return self._base / "context" / "sprint" / "velocity.json"

    def get_inference_weekly_path(self) -> Path:
        return self._base / "context" / "costs" / "inference-weekly.json"

    def get_inference_history_path(self) -> Path:
        return self._base / "context" / "costs" / "inference-history.jsonl"

    def get_changelog_path(self) -> Path:
        return self._base / "docs" / "changelog.md"

    def get_api_docs_dir(self) -> Path:
        return self._base / "docs" / "api-reference"

    def get_devlog_dir(self) -> Path:
        return self._base / "docs" / "devlog"

    def get_operational_log_path(self) -> Path:
        return self._base / "logs" / "operational.log"

    def get_pr_activity_log_path(self) -> Path:
        return self._base / "logs" / "pr-activity.log"

    def get_deploy_activity_log_path(self) -> Path:
        return self._base / "logs" / "deploy-activity.log"

    def get_cost_alerts_log_path(self) -> Path:
        return self._base / "logs" / "cost-alerts.log"

    def list_prs(self, status: str) -> list[str]:
        pr_dir = self._base / "prs" / status
        if not pr_dir.exists():
            return []
        return [f.stem for f in pr_dir.iterdir() if f.suffix == ".json"]

    def list_deployments(self, status: str) -> list[str]:
        deploy_dir = self._base / "deployments" / status
        if not deploy_dir.exists():
            return []
        return [f.stem for f in deploy_dir.iterdir() if f.suffix == ".json"]

    def list_error_patterns(self) -> list[str]:
        pattern_dir = self._base / "context" / "errors" / "patterns"
        if not pattern_dir.exists():
            return []
        return [f.stem for f in pattern_dir.iterdir() if f.suffix == ".json"]

    def list_active_errors(self) -> list[str]:
        active_dir = self._base / "context" / "errors" / "active"
        if not active_dir.exists():
            return []
        return [f.stem for f in active_dir.iterdir() if f.suffix == ".json"]
