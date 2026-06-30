# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Brief Manager

Manages the lifecycle of project briefs received from Ops Claw.
Handles receipt, acknowledgment, draft association, and completion.

Usage:
    from content.brief_manager import BriefManager, ContentBrief

    manager = BriefManager(fs, op_log, mesh_client)
    brief = manager.receive_brief(message)
    manager.acknowledge_brief(brief.brief_id)
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Literal

from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
    generate_brief_id,
)

logger = logging.getLogger("milimo.brief_manager")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BriefError(Exception):
    """Base exception for brief operations."""

    pass


class BriefValidationError(BriefError):
    """Brief validation failed."""

    pass


class BriefAcknowledgmentError(BriefError):
    """Brief acknowledgment window exceeded."""

    pass


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ContentBrief:
    """A project brief from Ops Claw."""

    brief_id: str
    project_id: str
    client_id: str
    brief_text: str
    deadline: str
    tone_requirements: str
    platform_targets: list[str]
    received_at: str
    acknowledged_at: str | None = None
    status: Literal["active", "completed", "expired"] = "active"
    drafts_generated: list[str] = field(default_factory=list)
    published_urls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentBrief:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_overdue(self) -> bool:
        """Check if brief deadline has passed."""
        deadline_dt = datetime.fromisoformat(self.deadline.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > deadline_dt

    def hours_until_deadline(self) -> float:
        """Get hours remaining until deadline."""
        deadline_dt = datetime.fromisoformat(self.deadline.replace("Z", "+00:00"))
        remaining = deadline_dt - datetime.now(timezone.utc)
        return max(0, remaining.total_seconds() / 3600)


@dataclass
class BriefDeadlineRisk:
    """A brief at risk of missing deadline."""

    brief_id: str
    project_id: str
    client_id: str
    hours_remaining: float
    drafts_count: int
    risk_level: Literal["high", "critical"]


# ---------------------------------------------------------------------------
# Brief Manager
# ---------------------------------------------------------------------------


class BriefManager:
    """
    Manages the lifecycle of project briefs.

    Handles receipt, acknowledgment, draft association, completion.

    Per spec: Every received project_brief must get brief_acknowledged
    response within 5 minutes. An auto-acknowledgment timer ensures
    SLA compliance even if not acknowledged manually.
    """

    ACKNOWLEDGMENT_WINDOW_MINUTES = 5

    def __init__(
        self,
        fs: ContentFilesystemInit,
        operational_log: ContentOperationalLog,
        mesh_client: Any | None = None,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._mesh = mesh_client
        self._ack_timers: dict[str, threading.Timer] = {}
        self._lock = threading.RLock()

    def receive_brief(self, message: dict[str, Any]) -> ContentBrief:
        """
        Receive and store a new brief from Ops Claw.

        Validates payload, writes to active directory, logs receipt.
        Schedules auto-acknowledgment timer for SLA compliance.

        Per spec: Every received project_brief must get brief_acknowledged
        response within 5 minutes.
        """
        payload = message.get("payload", message)

        required_fields = [
            "client_id",
            "project_id",
            "brief_text",
            "deadline",
            "tone_requirements",
            "platform_targets",
        ]

        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise BriefValidationError(f"Missing required fields: {', '.join(missing)}")

        brief_id = payload.get("brief_id") or generate_brief_id()
        received_at = datetime.now(timezone.utc).isoformat()

        brief = ContentBrief(
            brief_id=brief_id,
            project_id=payload["project_id"],
            client_id=payload["client_id"],
            brief_text=payload["brief_text"],
            deadline=payload["deadline"],
            tone_requirements=payload["tone_requirements"],
            platform_targets=payload["platform_targets"],
            received_at=received_at,
            status="active",
        )

        brief_path = self._fs.get_brief_path("active", brief_id)
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(json.dumps(brief.to_dict(), indent=2))

        self._schedule_auto_acknowledgment(brief_id, brief)

        self._log.append(
            LogEntry(
                action_type="brief_received",
                entity_id=brief_id,
                outcome="success",
                client_id=brief.client_id,
                details={
                    "project_id": brief.project_id,
                    "platforms": brief.platform_targets,
                    "deadline": brief.deadline,
                },
            )
        )

        logger.info("Brief %s received from Ops Claw", brief_id)
        return brief

    def _schedule_auto_acknowledgment(self, brief_id: str, brief: ContentBrief) -> None:
        """
        Schedule automatic acknowledgment if not acknowledged within SLA.

        Per spec: 5-minute SLA. Timer fires at 4.5 minutes to ensure
        acknowledgment is sent before deadline.
        """
        safety_buffer_seconds = 30
        timer_seconds = (
            self.ACKNOWLEDGMENT_WINDOW_MINUTES * 60
        ) - safety_buffer_seconds

        def auto_acknowledge():
            with self._lock:
                try:
                    current_brief = self.get_brief(brief_id)
                    if current_brief and not current_brief.acknowledged_at:
                        logger.warning(
                            "Auto-acknowledging brief %s (SLA deadline approaching)",
                            brief_id,
                        )
                        self.acknowledge_brief(brief_id)
                        self._log.append(
                            LogEntry(
                                action_type="brief_auto_acknowledged",
                                entity_id=brief_id,
                                outcome="success",
                                client_id=current_brief.client_id,
                                details={"reason": "sla_safety"},
                            )
                        )
                except Exception as e:
                    logger.error(
                        "Auto-acknowledgment failed for brief %s: %s", brief_id, e
                    )

        timer = threading.Timer(timer_seconds, auto_acknowledge)
        with self._lock:
            self._ack_timers[brief_id] = timer
        timer.daemon = True
        timer.start()

        logger.debug("Scheduled auto-acknowledgment timer for brief %s", brief_id)

    def acknowledge_brief(self, brief_id: str) -> None:
        """
        Send brief_acknowledged message via mesh.

        Raises BriefAcknowledgmentError if called > 5 minutes after receipt.
        Cancels any pending auto-acknowledgment timer.
        """
        brief = self.get_brief(brief_id)
        if not brief:
            raise BriefError(f"Brief not found: {brief_id}")

        if brief.acknowledged_at:
            logger.warning("Brief %s already acknowledged", brief_id)
            return

        received_dt = datetime.fromisoformat(brief.received_at.replace("Z", "+00:00"))
        elapsed = datetime.now(timezone.utc) - received_dt
        elapsed_minutes = elapsed.total_seconds() / 60

        if elapsed_minutes > self.ACKNOWLEDGMENT_WINDOW_MINUTES:
            raise BriefAcknowledgmentError(
                f"Acknowledgment window exceeded for brief {brief_id}: "
                f"{elapsed_minutes:.1f} minutes (max: {self.ACKNOWLEDGMENT_WINDOW_MINUTES})"
            )

        with self._lock:
            if brief_id in self._ack_timers:
                self._ack_timers[brief_id].cancel()
                del self._ack_timers[brief_id]

        acknowledged_at = datetime.now(timezone.utc).isoformat()
        estimated_draft_time = (
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).isoformat()

        brief.acknowledged_at = acknowledged_at
        self._save_brief(brief)

        if self._mesh:
            self._mesh.send(
                {
                    "message_type": "brief_acknowledged",
                    "sender_role": "content",
                    "recipient_role": "ops",
                    "payload": {
                        "project_id": brief.project_id,
                        "estimated_first_draft_time": estimated_draft_time,
                        "acknowledged_at": acknowledged_at,
                    },
                }
            )

        self._log.append(
            LogEntry(
                action_type="brief_acknowledged",
                entity_id=brief_id,
                outcome="success",
                client_id=brief.client_id,
                details={
                    "project_id": brief.project_id,
                    "estimated_draft_time": estimated_draft_time,
                },
            )
        )

        logger.info("Brief %s acknowledged", brief_id)

    def handle_revision_request(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle revision request from Ops Claw.

        Per spec: loads original draft, creates revision context,
        and queues regeneration task.

        Returns revision context for ContentGenerator to use.
        """
        payload = message.get("payload", message)

        required = ["project_id", "draft_id", "revision_notes", "deadline"]
        missing = [f for f in required if f not in payload]
        if missing:
            raise BriefValidationError(f"Missing revision fields: {', '.join(missing)}")

        draft_id = payload["draft_id"]
        revision_notes = payload["revision_notes"]
        project_id = payload["project_id"]
        deadline = payload["deadline"]

        draft_path = self._fs.get_draft_path("approved", draft_id)
        if not draft_path.exists():
            draft_path = self._fs.get_draft_path("rejected", draft_id)

        original_draft_data = None
        if draft_path.exists():
            original_draft_data = json.loads(draft_path.read_text())

        revision_context = {
            "draft_id": draft_id,
            "project_id": project_id,
            "revision_notes": revision_notes,
            "deadline": deadline,
            "original_draft": original_draft_data,
            "regeneration_required": True,
        }

        self._log.append(
            LogEntry(
                action_type="revision_requested",
                entity_id=draft_id,
                outcome="success",
                details={
                    "project_id": project_id,
                    "revision_notes": revision_notes[:200],
                    "deadline": deadline,
                    "has_original_draft": original_draft_data is not None,
                    "regeneration_required": True,
                },
            )
        )

        logger.info(
            "Revision request for draft %s: %s",
            draft_id,
            revision_notes[:50],
        )

        return revision_context

    def get_pending_revisions(self) -> list[dict[str, Any]]:
        """Get all pending revision requests from operational log."""
        entries = self._log.read_recent(days=1, action_type="revision_requested")
        revisions = []
        for entry in entries:
            if entry.details.get("regeneration_required"):
                revisions.append(
                    {
                        "draft_id": entry.entity_id,
                        "project_id": entry.details.get("project_id"),
                        "revision_notes": entry.details.get("revision_notes"),
                        "deadline": entry.details.get("deadline"),
                    }
                )
        return revisions

    def complete_brief(self, brief_id: str, published_urls: list[str]) -> None:
        """
        Move brief to completed and send deliverable_complete message.

        Per spec: sends deliverable_complete message to Ops Claw
        when all deliverables are approved and published.
        """
        brief = self.get_brief(brief_id)
        if not brief:
            raise BriefError(f"Brief not found: {brief_id}")

        brief.status = "completed"
        brief.published_urls = published_urls

        completed_path = self._fs.get_brief_path("completed", brief_id)
        completed_path.parent.mkdir(parents=True, exist_ok=True)
        completed_path.write_text(json.dumps(brief.to_dict(), indent=2))

        active_path = self._fs.get_brief_path("active", brief_id)
        if active_path.exists():
            active_path.unlink()

        self._log.append(
            LogEntry(
                action_type="brief_completed",
                entity_id=brief_id,
                outcome="success",
                client_id=brief.client_id,
                details={
                    "project_id": brief.project_id,
                    "published_urls": published_urls,
                },
            )
        )

        if self._mesh:
            deliverable_message = {
                "message_type": "deliverable_complete",
                "sender_role": "content",
                "recipient_role": "ops",
                "payload": {
                    "project_id": brief.project_id,
                    "brief_id": brief_id,
                    "client_id": brief.client_id,
                    "published_urls": published_urls,
                    "performance_baseline": None,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            self._mesh.send(deliverable_message)
            logger.info("Sent deliverable_complete message for brief %s", brief_id)

        logger.info("Brief %s completed with %d URLs", brief_id, len(published_urls))

    def get_brief(self, brief_id: str) -> ContentBrief | None:
        """Get brief by ID from active or completed directory."""
        active_path = self._fs.get_brief_path("active", brief_id)
        if active_path.exists():
            data = json.loads(active_path.read_text())
            return ContentBrief.from_dict(data)

        completed_path = self._fs.get_brief_path("completed", brief_id)
        if completed_path.exists():
            data = json.loads(completed_path.read_text())
            return ContentBrief.from_dict(data)

        return None

    def get_active_briefs(self) -> list[ContentBrief]:
        """Get all active briefs."""
        briefs = []
        active_dir = self._fs.BASE / "briefs" / "active"

        if active_dir.exists():
            for brief_file in active_dir.glob("*.json"):
                try:
                    data = json.loads(brief_file.read_text())
                    briefs.append(ContentBrief.from_dict(data))
                except Exception as e:
                    logger.warning("Failed to load brief %s: %s", brief_file, e)

        return sorted(briefs, key=lambda b: b.deadline)

    def check_deadline_risks(self) -> list[BriefDeadlineRisk]:
        """
        Check for briefs at risk of missing deadline.

        Returns briefs where deadline is within 24 hours and no draft exists.
        """
        risks = []
        active_briefs = self.get_active_briefs()

        for brief in active_briefs:
            hours_remaining = brief.hours_until_deadline()
            drafts_count = len(brief.drafts_generated)

            if hours_remaining <= 24 and drafts_count == 0:
                risk_level: Literal["high", "critical"] = "high"
                if hours_remaining <= 4:
                    risk_level = "critical"

                risks.append(
                    BriefDeadlineRisk(
                        brief_id=brief.brief_id,
                        project_id=brief.project_id,
                        client_id=brief.client_id,
                        hours_remaining=hours_remaining,
                        drafts_count=drafts_count,
                        risk_level=risk_level,
                    )
                )

        return sorted(risks, key=lambda r: r.hours_remaining)

    def _save_brief(self, brief: ContentBrief) -> None:
        """Save brief to filesystem."""
        brief_path = self._fs.get_brief_path("active", brief.brief_id)
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(json.dumps(brief.to_dict(), indent=2))
