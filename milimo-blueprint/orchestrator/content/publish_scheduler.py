# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Publish Scheduler

Reads calendar/scheduled/ and publishes content at correct times.
Runs continuously, checking for due items every 60 seconds.
Handles restart recovery by checking for missed publishes.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from .platform_publisher import PlatformPublisher, PlatformCredentials

logger = logging.getLogger("milimo.publish_scheduler")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ScheduledItem:
    """A scheduled publish item."""

    schedule_id: str
    draft_id: str
    platform: str
    client_id: str | None
    publish_time: str
    content_preview: str
    status: str = "scheduled"
    scheduled_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledItem:
        return cls(
            schedule_id=data.get("schedule_id", ""),
            draft_id=data.get("draft_id", ""),
            platform=data.get("platform", ""),
            client_id=data.get("client_id"),
            publish_time=data.get("publish_time", ""),
            content_preview=data.get("content_preview", ""),
            status=data.get("status", "scheduled"),
            scheduled_at=data.get("scheduled_at", ""),
        )


@dataclass
class MissedPublish:
    """Record of a missed scheduled publish."""

    schedule_id: str
    draft_id: str
    platform: str
    client_id: str | None
    scheduled_time: str
    detected_at: str
    hours_late: float


# ---------------------------------------------------------------------------
# Publish Scheduler
# ---------------------------------------------------------------------------


class PublishScheduler:
    """
    Reads calendar/scheduled/ and publishes at correct times.

    Runs continuously, checking every 60 seconds.
    Never misses a scheduled publish — handles restart recovery.
    """

    CHECK_INTERVAL_SECONDS = 60

    def __init__(
        self,
        fs: ContentFilesystemInit,
        operational_log: ContentOperationalLog,
        publisher: PlatformPublisher,
        war_room: Any | None = None,
        credentials_provider: Callable[[str], PlatformCredentials | None] | None = None,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._publisher = publisher
        self._war_room = war_room
        self._credentials_provider = credentials_provider

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Begin continuous scheduling loop."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._stop_event.clear()

        missed = self.recover_missed_publishes()
        if missed:
            self._handle_missed_publishes(missed)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info("Publish scheduler started")

    def stop(self) -> None:
        """Stop the scheduling loop."""
        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("Publish scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduling loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self._check_and_publish()
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)

            self._stop_event.wait(self.CHECK_INTERVAL_SECONDS)

    def _check_and_publish(self) -> None:
        """Check for due items and publish them."""
        due_items = self.check_due_items()

        for item in due_items:
            try:
                self._publish_item(item)
            except Exception as e:
                logger.error("Failed to publish %s: %s", item.schedule_id, e)

    def check_due_items(self) -> list[ScheduledItem]:
        """
        Check for scheduled items due for publishing.

        Returns items where publish_time <= now.
        """
        due = []
        scheduled_dir = self._fs.BASE / "calendar" / "scheduled"

        if not scheduled_dir.exists():
            return due

        now = datetime.now(timezone.utc)

        for schedule_file in scheduled_dir.glob("*.json"):
            try:
                data = json.loads(schedule_file.read_text())
                item = ScheduledItem.from_dict(data)

                if item.status != "scheduled":
                    continue

                try:
                    publish_dt = datetime.fromisoformat(
                        item.publish_time.replace("Z", "+00:00")
                    )
                except Exception:
                    continue

                if now >= publish_dt:
                    due.append(item)

            except Exception as e:
                logger.warning("Failed to read schedule file %s: %s", schedule_file, e)

        return due

    def recover_missed_publishes(self) -> list[MissedPublish]:
        """
        Find missed scheduled publishes on startup.

        Returns items with past publish_time that have no published record.
        """
        missed = []
        scheduled_dir = self._fs.BASE / "calendar" / "scheduled"
        published_dir = self._fs.BASE / "calendar" / "published"

        if not scheduled_dir.exists():
            return missed

        now = datetime.now(timezone.utc)

        for schedule_file in scheduled_dir.glob("*.json"):
            try:
                data = json.loads(schedule_file.read_text())
                item = ScheduledItem.from_dict(data)

                if item.status != "scheduled":
                    continue

                try:
                    publish_dt = datetime.fromisoformat(
                        item.publish_time.replace("Z", "+00:00")
                    )
                except Exception:
                    continue

                if now <= publish_dt:
                    continue

                published_file = published_dir / f"{item.draft_id}.json"
                if published_file.exists():
                    continue

                hours_late = (now - publish_dt).total_seconds() / 3600

                missed.append(
                    MissedPublish(
                        schedule_id=item.schedule_id,
                        draft_id=item.draft_id,
                        platform=item.platform,
                        client_id=item.client_id,
                        scheduled_time=item.publish_time,
                        detected_at=now.isoformat(),
                        hours_late=hours_late,
                    )
                )

            except Exception as e:
                logger.warning("Failed to check schedule %s: %s", schedule_file, e)

        return missed

    def _handle_missed_publishes(self, missed: list[MissedPublish]) -> None:
        """Handle missed publishes by escalating to War Room."""
        for item in missed:
            logger.warning(
                "Missed scheduled publish: %s for %s on %s (%.1f hours late)",
                item.schedule_id,
                item.client_id or "own content",
                item.platform,
                item.hours_late,
            )

            self._log.append(
                LogEntry(
                    action_type="missed_publish_detected",
                    entity_id=item.draft_id,
                    outcome="failed",
                    platform=item.platform,
                    client_id=item.client_id,
                    details={
                        "schedule_id": item.schedule_id,
                        "scheduled_time": item.scheduled_time,
                        "hours_late": item.hours_late,
                    },
                )
            )

            if self._war_room:
                self._war_room.queue_action(
                    claw="content",
                    action_type="missed_publish",
                    payload={
                        "schedule_id": item.schedule_id,
                        "draft_id": item.draft_id,
                        "platform": item.platform,
                        "client_id": item.client_id,
                        "scheduled_time": item.scheduled_time,
                        "hours_late": item.hours_late,
                        "message": (
                            f"Missed scheduled publish for {item.client_id or 'own content'} "
                            f"on {item.platform} — publish now?"
                        ),
                    },
                )

    def _publish_item(self, item: ScheduledItem) -> None:
        """Publish a scheduled item."""
        draft_path = self._fs.get_draft_path("approved", item.draft_id)

        if not draft_path.exists():
            logger.error("Draft not found: %s", item.draft_id)

            self._mark_schedule_failed(item, "Draft not found")
            return

        if not self._credentials_provider:
            logger.error("No credentials provider configured")
            self._mark_schedule_failed(item, "No credentials")
            return

        credentials = self._credentials_provider(item.platform)
        if not credentials:
            logger.error("No credentials for platform: %s", item.platform)
            self._mark_schedule_failed(item, f"No credentials for {item.platform}")
            return

        from .content_generator import Draft

        draft_data = json.loads(draft_path.read_text())
        draft = Draft.from_dict(draft_data)

        result = self._publisher.publish(draft, credentials)

        if result.success:
            self._mark_schedule_complete(item)
            logger.info("Published scheduled item %s", item.schedule_id)
        else:
            self._mark_schedule_failed(item, result.error or "Unknown error")

    def _mark_schedule_complete(self, item: ScheduledItem) -> None:
        """Mark a schedule as completed."""
        schedule_path = (
            self._fs.BASE / "calendar" / "scheduled" / f"{item.schedule_id}.json"
        )

        if schedule_path.exists():
            data = json.loads(schedule_path.read_text())
            data["status"] = "completed"
            data["completed_at"] = datetime.now(timezone.utc).isoformat()
            schedule_path.write_text(json.dumps(data, indent=2))

        self._log.append(
            LogEntry(
                action_type="scheduled_publish_completed",
                entity_id=item.draft_id,
                outcome="success",
                platform=item.platform,
                client_id=item.client_id,
                details={"schedule_id": item.schedule_id},
            )
        )

    def _mark_schedule_failed(self, item: ScheduledItem, reason: str) -> None:
        """Mark a schedule as failed."""
        schedule_path = (
            self._fs.BASE / "calendar" / "scheduled" / f"{item.schedule_id}.json"
        )

        if schedule_path.exists():
            data = json.loads(schedule_path.read_text())
            data["status"] = "failed"
            data["failed_at"] = datetime.now(timezone.utc).isoformat()
            data["failure_reason"] = reason
            schedule_path.write_text(json.dumps(data, indent=2))

        self._log.append(
            LogEntry(
                action_type="scheduled_publish_failed",
                entity_id=item.draft_id,
                outcome="failed",
                platform=item.platform,
                client_id=item.client_id,
                details={
                    "schedule_id": item.schedule_id,
                    "reason": reason,
                },
            )
        )
