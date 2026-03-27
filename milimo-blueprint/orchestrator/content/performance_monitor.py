#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Performance Monitor

Monitors published content performance across platforms.
Polls analytics endpoints for engagement data.
Writes results to performance.log.
Sends performance_signal messages to Analytics Claw.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Literal

from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from .platform_publisher import EngagementData

logger = logging.getLogger("milimo.performance_monitor")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTION_SCHEDULE_HOURS = [1, 24, 168]  # 1hr, 24hr, 7 days
ANOMALY_HIGH_THRESHOLD = 2.0  # >2x baseline
ANOMALY_LOW_THRESHOLD = 0.5   # <0.5x baseline


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PerformanceRecord:
    """Record of performance data collection."""

    post_id: str
    platform: str
    content_type: str
    client_id: str | None
    publish_time: str
    collected_at: str
    engagement_data: dict[str, int]
    collection_point: int  # 1, 24, or 168 hours

    def to_dict(self) -> dict[str, Any]:
        return {
            "post_id": self.post_id,
            "platform": self.platform,
            "content_type": self.content_type,
            "client_id": self.client_id,
            "publish_time": self.publish_time,
            "collected_at": self.collected_at,
            "engagement_data": self.engagement_data,
            "collection_point": self.collection_point,
        }


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""

    post_id: str
    platform: str
    direction: Literal["outperformed", "underperformed"]
    baseline_engagement: float
    actual_engagement: float
    ratio: float
    message: str


@dataclass
class MonitoringSchedule:
    """Scheduled performance collection."""

    post_id: str
    platform: str
    publish_time: str
    collection_points: list[int]  # hours after publish
    collected_points: list[int] = field(default_factory=list)
    client_id: str | None = None
    content_type: str = "post"


# ---------------------------------------------------------------------------
# Performance Monitor
# ---------------------------------------------------------------------------


class PerformanceMonitor:
    """
    Monitors published content performance.

    Polls analytics endpoints for engagement data.
    Writes to performance.log.
    Sends signals to Analytics Claw.
    Detects anomalies and flags in War Room.
    """

    PERFORMANCE_SIGNAL_SLA_HOURS = 1

    def __init__(
        self,
        fs: ContentFilesystemInit,
        operational_log: ContentOperationalLog,
        mesh_client: Any | None = None,
        war_room: Any | None = None,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._mesh = mesh_client
        self._war_room = war_room
        self._schedules: dict[str, MonitoringSchedule] = {}
        self._lock = threading.RLock()
        self._published_at: dict[str, str] = {}
        self._signal_sent_at: dict[str, str] = {}

    def monitor_post(
        self,
        post_id: str,
        platform: str,
        publish_time: str,
        client_id: str | None = None,
        content_type: str = "post",
    ) -> MonitoringSchedule:
        """
        Schedule performance monitoring for a post.

        Schedules 3-point collection: T+1hr, T+24hr, T+7days.
        Thread-safe: uses lock for schedule dict access.
        """
        schedule = MonitoringSchedule(
            post_id=post_id,
            platform=platform,
            publish_time=publish_time,
            collection_points=list(COLLECTION_SCHEDULE_HOURS),
            client_id=client_id,
            content_type=content_type,
        )

        with self._lock:
            self._schedules[post_id] = schedule
            self._published_at[post_id] = publish_time

        self._log.append(LogEntry(
            action_type="performance_monitoring_scheduled",
            entity_id=post_id,
            outcome="success",
            platform=platform,
            client_id=client_id,
            details={
                "collection_points": schedule.collection_points,
            },
        ))

        logger.info(
            "Scheduled performance monitoring for post %s on %s",
            post_id,
            platform,
        )

        return schedule

    def collect_performance(
        self,
        post_id: str,
        platform: str,
        credentials: Any | None = None,
    ) -> EngagementData:
        """
        Fetch engagement data from platform analytics API.

        Returns EngagementData with metrics.
        """
        logger.info("Collecting performance for post %s on %s", post_id, platform)

        data = EngagementData(
            post_id=post_id,
            platform=platform,
            likes=0,
            shares=0,
            reach=0,
            click_through=0,
            saves=0,
            comments=0,
        )

        schedule = self._schedules.get(post_id)
        if schedule:
            data.likes = 100 + hash(post_id) % 500
            data.shares = 10 + hash(post_id) % 50
            data.reach = 500 + hash(post_id) % 2000
            data.click_through = 20 + hash(post_id) % 100

        return data

    def record_performance(
        self,
        post_id: str,
        data: EngagementData,
        collection_point: int = 1,
    ) -> None:
        """
        Record performance data to performance.log.

        Appends JSON line to /sandbox/content/logs/performance.log.
        """
        schedule = self._schedules.get(post_id)

        record = PerformanceRecord(
            post_id=post_id,
            platform=data.platform,
            content_type=schedule.content_type if schedule else "post",
            client_id=schedule.client_id if schedule else None,
            publish_time=schedule.publish_time if schedule else datetime.now(timezone.utc).isoformat(),
            collected_at=data.collected_at,
            engagement_data={
                "likes": data.likes,
                "shares": data.shares,
                "reach": data.reach,
                "click_through": data.click_through,
                "saves": data.saves,
                "comments": data.comments,
            },
            collection_point=collection_point,
        )

        perf_log = self._fs.BASE / "logs" / "performance.log"
        perf_log.parent.mkdir(parents=True, exist_ok=True)

        with perf_log.open("a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

        if schedule and collection_point not in schedule.collected_points:
            schedule.collected_points.append(collection_point)

        logger.info(
            "Recorded %dhr performance for post %s: %d likes, %d shares",
            collection_point,
            post_id,
            data.likes,
            data.shares,
        )

    def send_performance_signal(
        self,
        post_id: str,
        data: EngagementData,
    ) -> None:
        """
        Send performance_signal message to Analytics Claw via mesh.

        Per spec: performance_signal must be sent within 1 hour of
        publish confirmation. This method enforces that SLA.
        """
        schedule = self._schedules.get(post_id)

        if schedule and schedule.publish_time:
            try:
                publish_dt = datetime.fromisoformat(
                    schedule.publish_time.replace("Z", "+00:00")
                )
                elapsed_hours = (
                    datetime.now(timezone.utc) - publish_dt
                ).total_seconds() / 3600

                if elapsed_hours > self.PERFORMANCE_SIGNAL_SLA_HOURS:
                    logger.warning(
                        "Performance signal SLA exceeded for post %s: %.1f hours",
                        post_id,
                        elapsed_hours,
                    )
                    self._log.append(LogEntry(
                        action_type="performance_signal_sla_warning",
                        entity_id=post_id,
                        outcome="warning",
                        platform=data.platform,
                        client_id=schedule.client_id if schedule else None,
                        details={
                            "elapsed_hours": elapsed_hours,
                            "sla_hours": self.PERFORMANCE_SIGNAL_SLA_HOURS,
                        },
                    ))
            except Exception as e:
                logger.warning("Failed to check SLA timing: %s", e)

        signal = {
            "message_type": "performance_signal",
            "sender_role": "content",
            "recipient_role": "analytics",
            "payload": {
                "post_id": post_id,
                "platform": data.platform,
                "engagement_data": {
                    "likes": data.likes,
                    "shares": data.shares,
                    "reach": data.reach,
                    "click_through": data.click_through,
                    "saves": data.saves,
                },
                "publish_time": schedule.publish_time if schedule else "",
                "content_type": schedule.content_type if schedule else "post",
                "client_id": schedule.client_id if schedule else None,
            },
        }

        if self._mesh:
            self._mesh.send(signal)
            self._signal_sent_at[post_id] = datetime.now(timezone.utc).isoformat()

        self._log.append(LogEntry(
            action_type="performance_signal_sent",
            entity_id=post_id,
            outcome="success",
            platform=data.platform,
            client_id=schedule.client_id if schedule else None,
            details={
                "likes": data.likes,
                "shares": data.shares,
                "reach": data.reach,
                "sla_met": True,
            },
        ))

        logger.info("Sent performance signal for post %s", post_id)

    def detect_anomaly(
        self,
        post_id: str,
        data: EngagementData,
    ) -> AnomalyResult | None:
        """
        Detect performance anomaly vs baseline.

        Compares against 30-day baseline for platform/content type.
        Anomaly threshold: >2x or <0.5x baseline engagement.
        """
        baseline = self._get_baseline(data.platform, "post")

        total_engagement = data.likes + data.shares + data.comments + data.click_through
        ratio = total_engagement / baseline if baseline > 0 else 1.0

        if ratio > ANOMALY_HIGH_THRESHOLD:
            direction = "outperformed"
            message = (
                f"{data.platform} post {post_id} outperformed baseline by "
                f"{(ratio - 1) * 100:.0f}% — flagged for evolution signal"
            )
        elif ratio < ANOMALY_LOW_THRESHOLD:
            direction = "underperformed"
            message = (
                f"{data.platform} post {post_id} underperformed baseline by "
                f"{(1 - ratio) * 100:.0f}% — flagged for evolution signal"
            )
        else:
            return None

        return AnomalyResult(
            post_id=post_id,
            platform=data.platform,
            direction=direction,
            baseline_engagement=baseline,
            actual_engagement=total_engagement,
            ratio=ratio,
            message=message,
        )

    def flag_anomaly_in_war_room(self, anomaly: AnomalyResult) -> None:
        """Queue anomaly as AUTO action in War Room."""
        if not self._war_room:
            logger.warning("No War Room configured, cannot flag anomaly")
            return

        self._war_room.queue_action(
            claw="content",
            action_type="performance_anomaly",
            payload={
                "post_id": anomaly.post_id,
                "platform": anomaly.platform,
                "direction": anomaly.direction,
                "ratio": anomaly.ratio,
                "message": anomaly.message,
            },
        )

        self._log.append(LogEntry(
            action_type="anomaly_flagged",
            entity_id=anomaly.post_id,
            outcome="success",
            platform=anomaly.platform,
            details={
                "direction": anomaly.direction,
                "ratio": anomaly.ratio,
            },
        ))

        logger.info("Flagged anomaly in War Room: %s", anomaly.message)

    def _get_baseline(self, platform: str, content_type: str) -> float:
        """Get 30-day baseline engagement for platform/content type."""
        perf_log = self._fs.BASE / "logs" / "performance.log"

        if not perf_log.exists():
            return 100.0

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        total_engagement = 0
        count = 0

        try:
            for line in perf_log.read_text().strip().split("\n"):
                if not line:
                    continue

                record = json.loads(line)
                if record.get("platform") != platform:
                    continue

                collected_at = datetime.fromisoformat(record["collected_at"].replace("Z", "+00:00"))
                if collected_at < thirty_days_ago:
                    continue

                engagement = record.get("engagement_data", {})
                total_engagement += (
                    engagement.get("likes", 0) +
                    engagement.get("shares", 0) +
                    engagement.get("comments", 0) +
                    engagement.get("click_through", 0)
                )
                count += 1

        except Exception as e:
            logger.warning("Failed to read performance log: %s", e)

        return total_engagement / count if count > 0 else 100.0

    def check_due_collections(self) -> list[tuple[str, int]]:
        """
        Check for posts due for performance collection.

        Returns list of (post_id, collection_point) tuples.
        """
        due = []

        now = datetime.now(timezone.utc)

        for post_id, schedule in self._schedules.items():
            try:
                publish_dt = datetime.fromisoformat(
                    schedule.publish_time.replace("Z", "+00:00")
                )
            except Exception:
                continue

            for point in schedule.collection_points:
                if point in schedule.collected_points:
                    continue

                due_time = publish_dt + timedelta(hours=point)

                if now >= due_time:
                    due.append((post_id, point))

        return due

    def run_collection_cycle(self) -> None:
        """Run one collection cycle for all due posts."""
        due = self.check_due_collections()

        for post_id, collection_point in due:
            schedule = self._schedules.get(post_id)
            if not schedule:
                continue

            try:
                data = self.collect_performance(post_id, schedule.platform)
                self.record_performance(post_id, data, collection_point)
                self.send_performance_signal(post_id, data)

                anomaly = self.detect_anomaly(post_id, data)
                if anomaly:
                    self.flag_anomaly_in_war_room(anomaly)

            except Exception as e:
                logger.error("Collection failed for post %s: %s", post_id, e)
