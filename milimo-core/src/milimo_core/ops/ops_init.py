# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Filesystem Initialization

Creates and validates the full /sandbox/clients/ filesystem structure.
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
from typing import Any, Literal

logger = logging.getLogger("milimo.ops")

from ..milimo_paths import claw_base

BASE = claw_base("ops")

REQUIRED_DIRS = [
    "active",
    "prospects",
    "completed",
    "contracts",
    "templates",
    "logs",
]

REQUIRED_TEMPLATE_FILES = {
    "templates/welcome-message.md": (
        "Hi {{client_name}},\n\n"
        "Thank you for reaching out to {{squad_name}}. "
        "We'd love to learn more about your project.\n\n"
        "Could you tell us a bit more about what you're looking for?\n\n"
        "Best,\n{{squad_name}}"
    ),
    "templates/intake-questionnaire.md": (
        "## Project Brief\n\n"
        "1. What is the goal of this project?\n"
        "2. What is your target timeline/deadline?\n"
        "3. What does success look like to you?\n"
        "4. Do you have any existing brand guidelines or references?\n"
        "5. What is your approximate budget range?"
    ),
    "templates/proposal-template.md": (
        "## Proposal for {{project_name}}\n\n"
        "**Scope:** {{scope_description}}\n\n"
        "**Timeline:** {{timeline}}\n\n"
        "**Investment:** {{price_range}}\n\n"
        "**Deliverables:**\n{{deliverables}}"
    ),
    "templates/change-order-template.md": (
        "## Change Order Request\n\n"
        "**Original Scope:** {{original_scope}}\n\n"
        "**Requested Addition:** {{new_request}}\n\n"
        "**Additional Investment:** {{additional_cost}}\n\n"
        "**Revised Timeline:** {{revised_timeline}}"
    ),
    "templates/delivery-message.md": (
        "Hi {{client_name}},\n\n"
        "Your project is complete! Here's what we delivered:\n\n"
        "{{deliverables_summary}}\n\n"
        "Please review and let us know if you have any questions.\n\n"
        "Best,\n{{squad_name}}"
    ),
    "templates/deep-work-response.md": (
        "Hey {{client_name}}, I'm heads-down on a focused sprint until "
        "{{resume_date}}. Your project is on track — I'll be back in "
        "full swing then. 🙏"
    ),
}

REQUIRED_LOG_FILES = [
    "logs/operational.log",
    "logs/comms.log",
    "logs/decisions.log",
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
class OpsLogEntry:
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
    def from_dict(cls, data: dict[str, Any]) -> OpsLogEntry:
        return cls(
            timestamp=data["timestamp"],
            action_type=data["action_type"],
            entity_id=data["entity_id"],
            outcome=data["outcome"],
            details=data.get("details", {}),
        )


@dataclass
class CommsLogEntry:
    """Entry in the communications log."""

    timestamp: str
    direction: str
    client_id: str
    project_id: str | None
    channel: str
    content_preview: str
    approved_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "direction": self.direction,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "channel": self.channel,
            "content_preview": self.content_preview,
            "approved_by": self.approved_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommsLogEntry:
        return cls(
            timestamp=data["timestamp"],
            direction=data["direction"],
            client_id=data["client_id"],
            project_id=data.get("project_id"),
            channel=data["channel"],
            content_preview=data["content_preview"],
            approved_by=data.get("approved_by"),
        )


class OpsOperationalLog:
    """
    Append-only structured log for Ops Claw actions.
    Thread-safe via fcntl file locking.
    """

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.touch()

    def append(self, entry: OpsLogEntry) -> None:
        with self._log_path.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry.to_dict()) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read_recent(
        self, days: int = 30, action_type: str | None = None
    ) -> list[OpsLogEntry]:
        entries: list[OpsLogEntry] = []
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
                        entry = OpsLogEntry.from_dict(data)
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


class OpsCommsLog:
    """
    Log of all client communications.
    Append-only. Thread-safe via fcntl.
    """

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.touch()

    def append(self, entry: CommsLogEntry) -> None:
        with self._log_path.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry.to_dict()) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_client_history(self, client_id: str, days: int = 90) -> list[CommsLogEntry]:
        entries: list[CommsLogEntry] = []
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
                        entry = CommsLogEntry.from_dict(data)
                        if entry.client_id != client_id:
                            continue
                        entry_time = datetime.fromisoformat(entry.timestamp).timestamp()
                        if entry_time >= cutoff:
                            entries.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return entries

    def get_response_times(self, client_id: str) -> list[float]:
        history = self.get_client_history(client_id, days=90)
        response_times: list[float] = []

        inbound_time: datetime | None = None
        for entry in sorted(history, key=lambda e: e.timestamp):
            if entry.direction == "received":
                inbound_time = datetime.fromisoformat(entry.timestamp)
            elif entry.direction == "sent" and inbound_time is not None:
                outbound_time = datetime.fromisoformat(entry.timestamp)
                delta_hours = (outbound_time - inbound_time).total_seconds() / 3600
                if delta_hours >= 0:
                    response_times.append(delta_hours)
                inbound_time = None

        return response_times


class OpsFilesystemInit:
    """
    Creates and validates the full /sandbox/clients/ filesystem structure.
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

        for file_path, content in REQUIRED_TEMPLATE_FILES.items():
            full_path = self._base / file_path
            try:
                if full_path.exists():
                    result.already_existed.append(file_path)
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    result.created_files.append(file_path)
                    logger.info("Created template: %s", full_path)
            except OSError as e:
                result.failed.append((file_path, str(e)))
                logger.error("Failed to create template %s: %s", full_path, e)

        for log_file in REQUIRED_LOG_FILES:
            log_path = self._base / log_file
            try:
                if log_path.exists():
                    result.already_existed.append(log_file)
                else:
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    log_path.touch()
                    result.created_files.append(log_file)
                    logger.info("Created log file: %s", log_path)
            except OSError as e:
                result.failed.append((log_file, str(e)))
                logger.error("Failed to create log %s: %s", log_path, e)

        return result

    def validate(self) -> ValidationResult:
        result = ValidationResult()

        for dir_name in REQUIRED_DIRS:
            dir_path = self._base / dir_name
            if not dir_path.is_dir():
                result.missing_dirs.append(dir_name)

        for file_path in REQUIRED_TEMPLATE_FILES:
            full_path = self._base / file_path
            if not full_path.is_file():
                result.missing_files.append(file_path)

        for log_file in REQUIRED_LOG_FILES:
            log_path = self._base / log_file
            if not log_path.is_file():
                result.missing_files.append(log_file)

        return result

    def get_client_path(
        self, status: Literal["active", "completed"], client_id: str
    ) -> Path:
        return self._base / status / client_id

    def get_project_path(self, client_id: str, project_id: str) -> Path:
        return self._base / "active" / client_id / "projects" / project_id

    def get_prospect_path(self, inquiry_id: str) -> Path:
        return self._base / "prospects" / inquiry_id

    def get_template(self, template_name: str) -> str:
        template_path = self._base / "templates" / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
        return template_path.read_text()

    def create_client_dirs(self, client_id: str) -> None:
        client_dir = self.get_client_path("active", client_id)
        client_dir.mkdir(parents=True, exist_ok=True)
        (client_dir / "projects").mkdir(exist_ok=True)
        (client_dir / "comms").mkdir(exist_ok=True)
        logger.info("Created client directories for: %s", client_id)

    def create_project_dirs(self, client_id: str, project_id: str) -> None:
        project_dir = self.get_project_path(client_id, project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "comms").mkdir(exist_ok=True)
        logger.info("Created project directories for: %s/%s", client_id, project_id)

    def write_json_atomic(self, path: Path, data: dict[str, Any]) -> None:
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

    def get_active_clients(self) -> list[str]:
        active_dir = self._base / "active"
        if not active_dir.exists():
            return []
        return [d.name for d in active_dir.iterdir() if d.is_dir()]

    def get_active_projects(self) -> list[tuple[str, str]]:
        projects: list[tuple[str, str]] = []
        active_dir = self._base / "active"
        if not active_dir.exists():
            return projects

        for client_dir in active_dir.iterdir():
            if not client_dir.is_dir():
                continue
            projects_dir = client_dir / "projects"
            if not projects_dir.exists():
                continue
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    projects.append((client_dir.name, project_dir.name))

        return projects
