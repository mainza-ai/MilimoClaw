# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Brief Manager.

Tests cover:
- Brief receipt and storage
- Acknowledgment window enforcement
- Revision request handling
- Brief completion
- Deadline risk detection
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from orchestrator.content.content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
)
from orchestrator.content.brief_manager import (
    BriefManager,
    ContentBrief,
    BriefValidationError,
    BriefAcknowledgmentError,
)


class TestContentBrief:
    """Tests for ContentBrief dataclass."""

    def test_brief_created_with_defaults(self):
        """Brief is created with default values."""
        brief = ContentBrief(
            brief_id="brief-123",
            project_id="proj-1",
            client_id="client-1",
            brief_text="Test brief",
            deadline="2026-04-01T12:00:00Z",
            tone_requirements="professional",
            platform_targets=["twitter"],
            received_at="2026-03-21T10:00:00Z",
        )

        assert brief.brief_id == "brief-123"
        assert brief.status == "active"
        assert brief.acknowledged_at is None
        assert brief.drafts_generated == []

    def test_brief_is_overdue(self):
        """is_overdue returns True for past deadlines."""
        past_deadline = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        brief = ContentBrief(
            brief_id="brief-123",
            project_id="proj-1",
            client_id="client-1",
            brief_text="Test",
            deadline=past_deadline,
            tone_requirements="pro",
            platform_targets=["twitter"],
            received_at=datetime.now(timezone.utc).isoformat(),
        )

        assert brief.is_overdue() is True

    def test_brief_not_overdue(self):
        """is_overdue returns False for future deadlines."""
        future_deadline = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        brief = ContentBrief(
            brief_id="brief-123",
            project_id="proj-1",
            client_id="client-1",
            brief_text="Test",
            deadline=future_deadline,
            tone_requirements="pro",
            platform_targets=["twitter"],
            received_at=datetime.now(timezone.utc).isoformat(),
        )

        assert brief.is_overdue() is False

    def test_hours_until_deadline(self):
        """hours_until_deadline calculates correctly."""
        deadline = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
        brief = ContentBrief(
            brief_id="brief-123",
            project_id="proj-1",
            client_id="client-1",
            brief_text="Test",
            deadline=deadline,
            tone_requirements="pro",
            platform_targets=["twitter"],
            received_at=datetime.now(timezone.utc).isoformat(),
        )

        hours = brief.hours_until_deadline()
        assert 4.9 < hours < 5.1

    def test_hours_until_deadline_past_returns_zero(self):
        """hours_until_deadline returns 0 for past deadlines."""
        past_deadline = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        brief = ContentBrief(
            brief_id="brief-123",
            project_id="proj-1",
            client_id="client-1",
            brief_text="Test",
            deadline=past_deadline,
            tone_requirements="pro",
            platform_targets=["twitter"],
            received_at=datetime.now(timezone.utc).isoformat(),
        )

        assert brief.hours_until_deadline() == 0

    def test_brief_to_dict_and_from_dict(self):
        """Brief serializes and deserializes correctly."""
        brief = ContentBrief(
            brief_id="brief-456",
            project_id="proj-2",
            client_id="client-2",
            brief_text="Campaign brief",
            deadline="2026-04-15T18:00:00Z",
            tone_requirements="casual",
            platform_targets=["instagram", "tiktok"],
            received_at="2026-03-21T09:00:00Z",
            acknowledged_at="2026-03-21T09:02:00Z",
            status="active",
            drafts_generated=["draft-1", "draft-2"],
        )

        data = brief.to_dict()
        restored = ContentBrief.from_dict(data)

        assert restored.brief_id == "brief-456"
        assert restored.platform_targets == ["instagram", "tiktok"]
        assert restored.drafts_generated == ["draft-1", "draft-2"]


class TestBriefManager:
    """Tests for BriefManager class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_receive_brief_creates_file(self, tmp_path: Path):
        """Received brief is written to active directory."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-123",
                "client_id": "client-acme",
                "brief_text": "Create social media campaign",
                "deadline": "2026-04-01T12:00:00Z",
                "tone_requirements": "professional",
                "platform_targets": ["twitter", "linkedin"],
            }
        }

        brief = manager.receive_brief(message)

        assert brief.brief_id is not None
        assert brief.status == "active"

        brief_path = fs.get_brief_path("active", brief.brief_id)
        assert brief_path.exists()

        saved_data = json.loads(brief_path.read_text())
        assert saved_data["project_id"] == "proj-123"
        assert saved_data["platform_targets"] == ["twitter", "linkedin"]

    def test_receive_brief_logs_to_operational(self, tmp_path: Path):
        """Brief receipt creates operational log entry."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-456",
                "client_id": "client-beta",
                "brief_text": "Email campaign",
                "deadline": "2026-04-05T00:00:00Z",
                "tone_requirements": "friendly",
                "platform_targets": ["email"],
            }
        }

        brief = manager.receive_brief(message)

        entries = op_log.read_recent(days=1, action_type="brief_received")
        assert len(entries) == 1

        entry = entries[0]
        assert entry.entity_id == brief.brief_id
        assert entry.client_id == "client-beta"
        assert entry.outcome == "success"

    def test_receive_brief_missing_fields_raises(self, tmp_path: Path):
        """Missing required fields raises BriefValidationError."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-789",
                "brief_text": "Incomplete brief",
            }
        }

        with pytest.raises(BriefValidationError) as exc_info:
            manager.receive_brief(message)

        assert "Missing required fields" in str(exc_info.value)
        assert "client_id" in str(exc_info.value)

    def test_acknowledge_brief_on_time(self, tmp_path: Path):
        """Acknowledgment succeeds within 5-minute window."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)
        manager.acknowledge_brief(brief.brief_id)

        updated = manager.get_brief(brief.brief_id)
        assert updated is not None
        assert updated.acknowledged_at is not None

    def test_acknowledge_brief_too_late_raises(self, tmp_path: Path):
        """Acknowledgment after 5 minutes raises BriefAcknowledgmentError."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)

        old_received = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        brief.received_at = old_received
        manager._save_brief(brief)

        with pytest.raises(BriefAcknowledgmentError) as exc_info:
            manager.acknowledge_brief(brief.brief_id)

        assert "Acknowledgment window exceeded" in str(exc_info.value)

    def test_acknowledge_brief_idempotent(self, tmp_path: Path):
        """Second acknowledgment is silently ignored."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)
        manager.acknowledge_brief(brief.brief_id)
        manager.acknowledge_brief(brief.brief_id)

        entries = op_log.read_recent(days=1, action_type="brief_acknowledged")
        assert len(entries) == 1

    def test_handle_revision_request_logs(self, tmp_path: Path):
        """Revision request is logged correctly."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "draft_id": "draft-123",
                "revision_notes": "Make it more engaging",
                "deadline": "2026-04-02T00:00:00Z",
            }
        }

        manager.handle_revision_request(message)

        entries = op_log.read_recent(days=1, action_type="revision_requested")
        assert len(entries) == 1

        entry = entries[0]
        assert entry.entity_id == "draft-123"
        assert entry.outcome == "success"

    def test_handle_revision_missing_fields_raises(self, tmp_path: Path):
        """Missing revision fields raises BriefValidationError."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "draft_id": "draft-123",
            }
        }

        with pytest.raises(BriefValidationError):
            manager.handle_revision_request(message)

    def test_complete_brief_moves_to_completed(self, tmp_path: Path):
        """Completed brief is moved to completed directory."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)

        published_urls = [
            "https://twitter.com/post/123",
            "https://linkedin.com/post/456",
        ]
        manager.complete_brief(brief.brief_id, published_urls)

        completed_path = fs.get_brief_path("completed", brief.brief_id)
        assert completed_path.exists()

        active_path = fs.get_brief_path("active", brief.brief_id)
        assert not active_path.exists()

        saved_data = json.loads(completed_path.read_text())
        assert saved_data["status"] == "completed"
        assert len(saved_data["published_urls"]) == 2

    def test_complete_brief_logs(self, tmp_path: Path):
        """Brief completion creates log entry."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)
        manager.complete_brief(brief.brief_id, ["https://example.com"])

        entries = op_log.read_recent(days=1, action_type="brief_completed")
        assert len(entries) == 1


class TestGetActiveBriefs:
    """Tests for get_active_briefs method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_get_active_briefs_returns_all(self, tmp_path: Path):
        """All active briefs are returned."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        for i in range(3):
            message = {
                "payload": {
                    "project_id": f"proj-{i}",
                    "client_id": f"client-{i}",
                    "brief_text": f"Brief {i}",
                    "deadline": f"2026-04-0{i + 1}T00:00:00Z",
                    "tone_requirements": "pro",
                    "platform_targets": ["twitter"],
                }
            }
            manager.receive_brief(message)

        briefs = manager.get_active_briefs()

        assert len(briefs) == 3

    def test_get_active_briefs_sorted_by_deadline(self, tmp_path: Path):
        """Briefs are sorted by deadline."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        deadlines = [
            "2026-04-10T00:00:00Z",
            "2026-04-01T00:00:00Z",
            "2026-04-05T00:00:00Z",
        ]

        for i, deadline in enumerate(deadlines):
            message = {
                "payload": {
                    "project_id": f"proj-{i}",
                    "client_id": f"client-{i}",
                    "brief_text": f"Brief {i}",
                    "deadline": deadline,
                    "tone_requirements": "pro",
                    "platform_targets": ["twitter"],
                }
            }
            manager.receive_brief(message)

        briefs = manager.get_active_briefs()

        assert briefs[0].deadline == "2026-04-01T00:00:00Z"
        assert briefs[1].deadline == "2026-04-05T00:00:00Z"
        assert briefs[2].deadline == "2026-04-10T00:00:00Z"


class TestDeadlineRisks:
    """Tests for check_deadline_risks method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_deadline_risk_detected_within_24h(self, tmp_path: Path):
        """Brief within 24h with no drafts is detected as risk."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        soon_deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        message = {
            "payload": {
                "project_id": "proj-urgent",
                "client_id": "client-1",
                "brief_text": "Urgent brief",
                "deadline": soon_deadline,
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        manager.receive_brief(message)

        risks = manager.check_deadline_risks()

        assert len(risks) == 1
        assert risks[0].project_id == "proj-urgent"
        assert risks[0].risk_level == "high"
        assert risks[0].drafts_count == 0

    def test_critical_risk_within_4h(self, tmp_path: Path):
        """Brief within 4h is marked as critical."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        critical_deadline = (
            datetime.now(timezone.utc) + timedelta(hours=2)
        ).isoformat()
        message = {
            "payload": {
                "project_id": "proj-critical",
                "client_id": "client-1",
                "brief_text": "Critical brief",
                "deadline": critical_deadline,
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        manager.receive_brief(message)

        risks = manager.check_deadline_risks()

        assert len(risks) == 1
        assert risks[0].risk_level == "critical"

    def test_brief_with_drafts_not_flagged(self, tmp_path: Path):
        """Brief with drafts is not flagged as risk."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        soon_deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        message = {
            "payload": {
                "project_id": "proj-has-drafts",
                "client_id": "client-1",
                "brief_text": "Brief with drafts",
                "deadline": soon_deadline,
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)
        brief.drafts_generated = ["draft-1"]
        manager._save_brief(brief)

        risks = manager.check_deadline_risks()

        assert len(risks) == 0

    def test_brief_far_deadline_not_flagged(self, tmp_path: Path):
        """Brief with deadline > 24h is not flagged."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        far_deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        message = {
            "payload": {
                "project_id": "proj-far",
                "client_id": "client-1",
                "brief_text": "Far deadline brief",
                "deadline": far_deadline,
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        manager.receive_brief(message)

        risks = manager.check_deadline_risks()

        assert len(risks) == 0


class TestGetBrief:
    """Tests for get_brief method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_get_brief_from_active(self, tmp_path: Path):
        """Brief is retrieved from active directory."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)

        retrieved = manager.get_brief(brief.brief_id)
        assert retrieved is not None
        assert retrieved.brief_id == brief.brief_id

    def test_get_brief_from_completed(self, tmp_path: Path):
        """Brief is retrieved from completed directory."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)
        manager.complete_brief(brief.brief_id, ["https://example.com"])

        retrieved = manager.get_brief(brief.brief_id)
        assert retrieved is not None
        assert retrieved.status == "completed"

    def test_get_brief_nonexistent_returns_none(self, tmp_path: Path):
        """Nonexistent brief returns None."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        retrieved = manager.get_brief("nonexistent-brief")
        assert retrieved is None
