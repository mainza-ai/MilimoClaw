#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Platform Publisher and Performance Monitor.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.content.content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
)
from orchestrator.content.content_generator import Draft
from orchestrator.content.platform_publisher import (
    PlatformPublisher,
    PlatformCredentials,
    PublishResult,
    NotApprovedError,
    PlatformNotSupportedError,
    RetryExhaustedError,
    TwitterPublisher,
    LinkedInPublisher,
)
from orchestrator.content.performance_monitor import (
    PerformanceMonitor,
    EngagementData,
    AnomalyResult,
)
from orchestrator.content.publish_scheduler import (
    PublishScheduler,
    ScheduledItem,
    MissedPublish,
)


class TestPlatformPublisher:
    """Tests for PlatformPublisher class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        publisher = PlatformPublisher(fs, op_log)

        return fs, op_log, publisher

    def _create_approved_draft(self, fs: ContentFilesystemInit, draft_id: str) -> Draft:
        """Create an approved draft."""
        draft = Draft(
            draft_id=draft_id,
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Test content for publishing",
            status="approved",
        )

        approved_path = fs.get_draft_path("approved", draft_id)
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(draft.to_dict()))

        return draft

    def test_publish_approved_draft_succeeds(self, tmp_path: Path):
        """Approved draft publishes successfully."""
        fs, op_log, publisher = self._create_test_env(tmp_path)
        draft = self._create_approved_draft(fs, "draft-pub-1")

        credentials = PlatformCredentials(
            platform="twitter",
            access_token="test_token",
        )

        result = publisher.publish(draft, credentials)

        assert result.success is True
        assert result.post_id is not None
        assert result.url is not None

    def test_publish_non_approved_raises_error(self, tmp_path: Path):
        """Non-approved draft raises NotApprovedError."""
        fs, op_log, publisher = self._create_test_env(tmp_path)

        draft = Draft(
            draft_id="draft-pending",
            platform="twitter",
            client_id=None,
            project_id=None,
            content_type="post",
            raw_content="raw",
            processed_content="content",
            status="pending",
        )

        credentials = PlatformCredentials(platform="twitter", access_token="token")

        with pytest.raises(NotApprovedError):
            publisher.publish(draft, credentials)

    def test_publish_unsupported_platform_raises(self, tmp_path: Path):
        """Unsupported platform raises PlatformNotSupportedError."""
        fs, op_log, publisher = self._create_test_env(tmp_path)

        draft = Draft(
            draft_id="draft-unknown",
            platform="unknown_platform",
            client_id=None,
            project_id=None,
            content_type="post",
            raw_content="raw",
            processed_content="content",
            status="approved",
        )

        credentials = PlatformCredentials(platform="unknown_platform", access_token="token")

        with pytest.raises(PlatformNotSupportedError):
            publisher.publish(draft, credentials)

    def test_publish_moves_draft_to_published(self, tmp_path: Path):
        """Published draft is moved to published directory."""
        fs, op_log, publisher = self._create_test_env(tmp_path)
        draft = self._create_approved_draft(fs, "draft-move-test")

        credentials = PlatformCredentials(platform="twitter", access_token="token")
        publisher.publish(draft, credentials)

        published_path = fs.get_draft_path("published", draft.draft_id)
        assert published_path.exists()

        approved_path = fs.get_draft_path("approved", draft.draft_id)
        assert not approved_path.exists()

    def test_publish_writes_to_calendar_published(self, tmp_path: Path):
        """Publish writes record to calendar/published/."""
        fs, op_log, publisher = self._create_test_env(tmp_path)
        draft = self._create_approved_draft(fs, "draft-calendar-test")

        credentials = PlatformCredentials(platform="twitter", access_token="token")
        publisher.publish(draft, credentials)

        publish_record = fs.BASE / "calendar" / "published" / f"{draft.draft_id}.json"
        assert publish_record.exists()

        record_data = json.loads(publish_record.read_text())
        assert record_data["draft_id"] == draft.draft_id

    def test_publish_logs_to_operational(self, tmp_path: Path):
        """Publish creates operational log entry."""
        fs, op_log, publisher = self._create_test_env(tmp_path)
        draft = self._create_approved_draft(fs, "draft-log-test")

        credentials = PlatformCredentials(platform="twitter", access_token="token")
        publisher.publish(draft, credentials)

        entries = op_log.read_recent(days=1, action_type="content_published")
        assert len(entries) == 1


class TestSchedulePublish:
    """Tests for schedule_publish method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        publisher = PlatformPublisher(fs, op_log)

        return fs, op_log, publisher

    def test_schedule_publish_creates_schedule_file(self, tmp_path: Path):
        """Scheduling creates file in calendar/scheduled/."""
        fs, op_log, publisher = self._create_test_env(tmp_path)

        draft = Draft(
            draft_id="draft-sched-1",
            platform="linkedin",
            client_id="client-2",
            project_id="proj-2",
            content_type="article",
            raw_content="raw",
            processed_content="Scheduled content",
            status="approved",
        )

        approved_path = fs.get_draft_path("approved", draft.draft_id)
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(draft.to_dict()))

        credentials = PlatformCredentials(platform="linkedin", access_token="token")
        publish_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        schedule_id = publisher.schedule_publish(draft, publish_time, credentials)

        assert schedule_id.startswith("sched_")

        schedule_path = fs.BASE / "calendar" / "scheduled" / f"{schedule_id}.json"
        assert schedule_path.exists()


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        monitor = PerformanceMonitor(fs, op_log)

        return fs, op_log, monitor

    def test_monitor_post_schedules_collection(self, tmp_path: Path):
        """monitor_post schedules performance collection."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        schedule = monitor.monitor_post(
            post_id="post-123",
            platform="twitter",
            publish_time=datetime.now(timezone.utc).isoformat(),
        )

        assert schedule.post_id == "post-123"
        assert schedule.collection_points == [1, 24, 168]
        assert len(schedule.collected_points) == 0

    def test_collect_performance_returns_data(self, tmp_path: Path):
        """collect_performance returns engagement data."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        monitor.monitor_post(
            post_id="post-456",
            platform="twitter",
            publish_time=datetime.now(timezone.utc).isoformat(),
        )

        data = monitor.collect_performance("post-456", "twitter")

        assert data.post_id == "post-456"
        assert data.platform == "twitter"
        assert isinstance(data.likes, int)

    def test_record_performance_writes_to_log(self, tmp_path: Path):
        """record_performance writes to performance.log."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        monitor.monitor_post(
            post_id="post-789",
            platform="linkedin",
            publish_time=datetime.now(timezone.utc).isoformat(),
        )

        data = EngagementData(
            post_id="post-789",
            platform="linkedin",
            likes=100,
            shares=20,
            reach=500,
        )

        monitor.record_performance("post-789", data, collection_point=1)

        perf_log = fs.BASE / "logs" / "performance.log"
        assert perf_log.exists()

        record = json.loads(perf_log.read_text().strip())
        assert record["post_id"] == "post-789"
        assert record["engagement_data"]["likes"] == 100

    def test_detect_anomaly_high_performance(self, tmp_path: Path):
        """detect_anomaly identifies outperformance."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        monitor.monitor_post(
            post_id="post-high",
            platform="twitter",
            publish_time=datetime.now(timezone.utc).isoformat(),
        )

        data = EngagementData(
            post_id="post-high",
            platform="twitter",
            likes=500,
            shares=100,
            comments=50,
            click_through=200,
        )

        anomaly = monitor.detect_anomaly("post-high", data)

        assert anomaly is not None
        assert anomaly.direction == "outperformed"
        assert anomaly.ratio > 2.0

    def test_detect_anomaly_low_performance(self, tmp_path: Path):
        """detect_anomaly identifies underperformance."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        monitor.monitor_post(
            post_id="post-low",
            platform="twitter",
            publish_time=datetime.now(timezone.utc).isoformat(),
        )

        data = EngagementData(
            post_id="post-low",
            platform="twitter",
            likes=5,
            shares=1,
            comments=0,
            click_through=2,
        )

        anomaly = monitor.detect_anomaly("post-low", data)

        assert anomaly is not None
        assert anomaly.direction == "underperformed"
        assert anomaly.ratio < 0.5

    def test_detect_anomaly_normal_performance(self, tmp_path: Path):
        """detect_anomaly returns None for normal performance."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        monitor.monitor_post(
            post_id="post-normal",
            platform="twitter",
            publish_time=datetime.now(timezone.utc).isoformat(),
        )

        data = EngagementData(
            post_id="post-normal",
            platform="twitter",
            likes=80,
            shares=10,
            comments=5,
            click_through=15,
        )

        anomaly = monitor.detect_anomaly("post-normal", data)

        assert anomaly is None


class TestPublishScheduler:
    """Tests for PublishScheduler class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        publisher = PlatformPublisher(fs, op_log)
        scheduler = PublishScheduler(fs, op_log, publisher)

        return fs, op_log, scheduler

    def _create_scheduled_item(
        self,
        fs: ContentFilesystemInit,
        schedule_id: str,
        publish_time: str,
    ):
        """Create a scheduled item."""
        schedule_path = fs.BASE / "calendar" / "scheduled" / f"{schedule_id}.json"
        schedule_path.parent.mkdir(parents=True, exist_ok=True)

        schedule_data = {
            "schedule_id": schedule_id,
            "draft_id": f"draft-{schedule_id}",
            "platform": "twitter",
            "client_id": "client-1",
            "publish_time": publish_time,
            "content_preview": "Test content",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "status": "scheduled",
        }

        schedule_path.write_text(json.dumps(schedule_data))

        draft = Draft(
            draft_id=f"draft-{schedule_id}",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Test content",
            status="approved",
        )

        approved_path = fs.get_draft_path("approved", f"draft-{schedule_id}")
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(draft.to_dict()))

        return schedule_data

    def test_check_due_items_finds_past_items(self, tmp_path: Path):
        """check_due_items finds items with past publish time."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self._create_scheduled_item(fs, "sched-past", past_time)

        due = scheduler.check_due_items()

        assert len(due) == 1
        assert due[0].schedule_id == "sched-past"

    def test_check_due_items_skips_future_items(self, tmp_path: Path):
        """check_due_items skips future items."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        self._create_scheduled_item(fs, "sched-future", future_time)

        due = scheduler.check_due_items()

        assert len(due) == 0

    def test_recover_missed_publishes_finds_missed(self, tmp_path: Path):
        """recover_missed_publishes finds items without published record."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self._create_scheduled_item(fs, "sched-missed", past_time)

        missed = scheduler.recover_missed_publishes()

        assert len(missed) == 1
        assert missed[0].schedule_id == "sched-missed"

    def test_recover_missed_ignores_already_published(self, tmp_path: Path):
        """recover_missed_publishes ignores already published items."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self._create_scheduled_item(fs, "sched-done", past_time)

        published_dir = fs.BASE / "calendar" / "published"
        published_dir.mkdir(parents=True, exist_ok=True)
        (published_dir / "draft-sched-done.json").write_text(json.dumps({"draft_id": "draft-sched-done"}))

        missed = scheduler.recover_missed_publishes()

        assert len(missed) == 0
