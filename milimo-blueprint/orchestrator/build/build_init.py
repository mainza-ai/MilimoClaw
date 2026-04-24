# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw filesystem initialization and operational log management.

Creates and validates the full /sandbox/build/ filesystem structure.
Idempotent — safe to call on every claw startup.

Enhancement: Inference fallback chain and retry wrapper (from oh-my-openagent).
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

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
    "tasks",  # Enhancement: file-based task dependency storage (from OmO)
    "memory/daily",  # Enhancement: filesystem memory pattern (from Clawhip)
    "memory/projects",
    "memory/errors",
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

# Enhancement: Inference fallback chain (from oh-my-openagent session recovery)
# If the primary inference model fails, fall back through this chain.
INFERENCE_FALLBACK_CHAIN: list[str] = [
    os.environ.get("NEMOCLAW_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    "claude-sonnet-4-6",
    "gemini-3.1-pro",
]

_NEMOCLAW_MODEL = os.environ.get("NEMOCLAW_MODEL", "nvidia/nemotron-3-super-120b-a12b")

BUILD_CATEGORIES: dict[str, dict[str, Any]] = {
    "code_generation": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.1,
        "data_type": "source_code_generation",
    },
    "code_review": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.1,
        "data_type": "code_review",
    },
    "pr_description_generation": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.3,
        "data_type": "pr_description_generation",
    },
    "issue_complexity_scoring": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.2,
        "data_type": "issue_complexity_scoring",
    },
    "changelog_generation": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.7,
        "data_type": "changelog_generation",
    },
    "api_documentation_generation": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.3,
        "data_type": "api_documentation_generation",
    },
    "devlog_draft_generation": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.7,
        "data_type": "devlog_draft_generation",
    },
    "dependency_audit": {
        "model": _NEMOCLAW_MODEL,
        "temperature": 0.1,
        "data_type": "dependency_vulnerability_analysis",
    },
}


@dataclass
class InitResult:
    created_dirs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    already_existed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


@dataclass
class ValidationResult:
    missing_dirs: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_dirs and not self.missing_files


class BuildFilesystemInit:
    """
    Creates and validates the full /sandbox/build/ filesystem structure.
    Idempotent — safe to call on every claw startup.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self.base = base_path or BASE

    def initialize(self) -> InitResult:
        """Create all REQUIRED_DIRS and REQUIRED_FILES. Never overwrite existing files."""
        result = InitResult()

        for dir_rel in REQUIRED_DIRS:
            dir_path = self.base / dir_rel
            try:
                if dir_path.exists():
                    result.already_existed.append(dir_rel)
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    result.created_dirs.append(dir_rel)
            except OSError as exc:
                result.failed.append((dir_rel, str(exc)))

        for file_rel, default_content in REQUIRED_FILES.items():
            file_path = self.base / file_rel
            try:
                if file_path.exists():
                    result.already_existed.append(file_rel)
                else:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    if default_content is None:
                        file_path.touch()
                    elif isinstance(default_content, str):
                        file_path.write_text(default_content, encoding="utf-8")
                    else:
                        self.atomic_write_json(file_path, default_content)
                    result.created_files.append(file_rel)
            except OSError as exc:
                result.failed.append((file_rel, str(exc)))

        return result

    def validate(self) -> ValidationResult:
        """Check that all required dirs and files exist."""
        result = ValidationResult()

        for dir_rel in REQUIRED_DIRS:
            if not (self.base / dir_rel).is_dir():
                result.missing_dirs.append(dir_rel)

        for file_rel in REQUIRED_FILES:
            if not (self.base / file_rel).exists():
                result.missing_files.append(file_rel)

        return result

    def get_pr_path(
        self,
        status: Literal["drafted", "approved", "merged"],
        pr_id: str,
    ) -> Path:
        valid_statuses = ("drafted", "approved", "merged")
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid PR status: {status!r}. Must be one of {valid_statuses}"
            )
        return self.base / "prs" / status / f"{pr_id}.json"

    def get_deploy_path(
        self,
        status: Literal["pending", "history"],
        deploy_id: str,
    ) -> Path:
        valid_statuses = ("pending", "history")
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid deploy status: {status!r}. Must be one of {valid_statuses}"
            )
        return self.base / "deployments" / status / f"{deploy_id}.json"

    def get_error_pattern_path(self, pattern_id: str) -> Path:
        return self.base / "context" / "errors" / "patterns" / f"{pattern_id}.json"

    def get_active_error_path(self, error_id: str) -> Path:
        return self.base / "context" / "errors" / "active" / f"{error_id}.json"

    def get_task_path(self, task_id: str) -> Path:
        """Enhancement: file-based task dependency storage (from OmO)."""
        return self.base / "tasks" / f"{task_id}.json"

    def get_inference_history_path(self) -> Path:
        return self.base / "context" / "costs" / "inference-history.jsonl"

    def atomic_write_json(self, path: Path, data: dict) -> None:
        """Write to temp file in same directory, rename on success."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent), suffix=".tmp", prefix=".atomic_"
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                import os

                os.fsync(f.fileno())
            Path(tmp_path).rename(path)
        except Exception:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def read_json(self, path: Path) -> dict:
        """Read JSON file, return empty dict if not found."""
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


@dataclass
class BuildLogEntry:
    timestamp: str
    action_type: str
    entity_id: str
    outcome: str
    details: dict


class BuildOperationalLog:
    """Append-only structured log. Thread-safe via fcntl file locking."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, entry: BuildLogEntry) -> None:
        line = json.dumps(
            {
                "timestamp": entry.timestamp,
                "action_type": entry.action_type,
                "entity_id": entry.entity_id,
                "outcome": entry.outcome,
                "details": entry.details,
            }
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_recent(
        self,
        days: int = 30,
        action_type: str | None = None,
    ) -> list[BuildLogEntry]:
        if not self.log_path.exists():
            return []

        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        entries: list[BuildLogEntry] = []

        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    _dt = datetime.fromisoformat(data["timestamp"])
                    if _dt.tzinfo is None:
                        _dt = _dt.replace(tzinfo=timezone.utc)
                    if _dt < cutoff:
                        continue
                    if action_type and data.get("action_type") != action_type:
                        continue
                    entries.append(
                        BuildLogEntry(
                            timestamp=data["timestamp"],
                            action_type=data["action_type"],
                            entity_id=data.get("entity_id", ""),
                            outcome=data.get("outcome", ""),
                            details=data.get("details", {}),
                        )
                    )
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return entries

    def count_by_type(self, action_type: str, days: int = 30) -> int:
        return len(self.read_recent(days=days, action_type=action_type))

    def get_last_run_time(self, action_type: str) -> str | None:
        entries = self.read_recent(days=365, action_type=action_type)
        if not entries:
            return None
        return max(e.timestamp for e in entries)


class PRActivityLog:
    """Append-only PR event log. Thread-safe."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event_type: str, pr_id: str, details: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "pr_id": pr_id,
            "details": details,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_pr_history(self, pr_id: str) -> list[dict]:
        if not self.log_path.exists():
            return []
        history: list[dict] = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("pr_id") == pr_id:
                        history.append(data)
                except (json.JSONDecodeError, KeyError):
                    continue
        return history


class DeployActivityLog:
    """Append-only deploy event log. Thread-safe."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event_type: str, deploy_id: str, details: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "deploy_id": deploy_id,
            "details": details,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
