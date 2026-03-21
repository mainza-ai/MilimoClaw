#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Brand Voice Manager and Content Scheduler.
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
from orchestrator.content.brand_voice import (
    BrandVoiceManager,
    VoiceProfile,
    MAX_APPROVED_EXAMPLES,
    MAX_REJECTED_EXAMPLES,
)
from orchestrator.content.content_scheduler import (
    ContentScheduler,
    MORNING_PLANNING_TIME,
)
from orchestrator.content.brief_manager import BriefManager


class TestVoiceProfile:
    """Tests for VoiceProfile dataclass."""

    def test_profile_created_with_defaults(self):
        """Profile is created with default values."""
        profile = VoiceProfile(
            profile_id="voice-123",
            client_id="client-1",
            profile_name="Test Profile",
        )

        assert profile.profile_id == "voice-123"
        assert profile.client_id == "client-1"
        assert profile.tone_descriptors == []
        assert profile.example_approved_posts == []
        assert profile.example_rejected_posts == []
        assert profile.sentence_length == "medium"

    def test_profile_to_dict_and_from_dict(self):
        """Profile serializes and deserializes correctly."""
        profile = VoiceProfile(
            profile_id="voice-456",
            client_id="client-2",
            profile_name="Brand Voice",
            tone_descriptors=["professional", "warm"],
            vocabulary_preferences={"preferred": ["industry terms"], "avoid": ["jargon"]},
            sentence_length="short",
            example_approved_posts=["Post 1", "Post 2"],
        )

        data = profile.to_dict()
        restored = VoiceProfile.from_dict(data)

        assert restored.profile_id == "voice-456"
        assert restored.tone_descriptors == ["professional", "warm"]
        assert restored.sentence_length == "short"


class TestBrandVoiceManager:
    """Tests for BrandVoiceManager class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BrandVoiceManager(fs, op_log)

        return fs, op_log, manager

    def test_create_profile_from_brief(self, tmp_path: Path):
        """Profile is created from brief tone requirements."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        profile = manager.create_profile(
            client_id="client-acme",
            brief_tone_requirements="Professional and approachable tone with simple language",
        )

        assert profile.client_id == "client-acme"
        assert "professional" in profile.tone_descriptors
        assert profile.profile_id.startswith("voice-")

        profile_path = fs.get_voice_profile_path("client-acme")
        assert profile_path.exists()

    def test_create_profile_extracts_tone_descriptors(self, tmp_path: Path):
        """Profile extracts tone descriptors from brief."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        profile = manager.create_profile(
            client_id="client-beta",
            brief_tone_requirements="Casual and friendly tone, warm and direct",
        )

        assert "casual" in profile.tone_descriptors
        assert "friendly" in profile.tone_descriptors
        assert "warm" in profile.tone_descriptors

    def test_load_profile_returns_none_if_missing(self, tmp_path: Path):
        """load_profile returns None if no profile exists."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        profile = manager.load_profile("nonexistent-client")

        assert profile is None

    def test_load_profile_returns_existing(self, tmp_path: Path):
        """load_profile returns existing profile."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        manager.create_profile("client-existing", "Professional tone")

        profile = manager.load_profile("client-existing")

        assert profile is not None
        assert profile.client_id == "client-existing"

    def test_update_profile_from_approval_adds_post(self, tmp_path: Path):
        """update_profile_from_approval adds approved post."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        manager.create_profile("client-update", "Professional")
        profile = manager.update_profile_from_approval(
            "client-update",
            "This is an approved post",
        )

        assert len(profile.example_approved_posts) == 1
        assert "approved post" in profile.example_approved_posts[0]

    def test_update_profile_from_approval_fifo(self, tmp_path: Path):
        """Approved posts FIFO after max limit."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        manager.create_profile("client-fifo", "Professional")

        for i in range(MAX_APPROVED_EXAMPLES + 5):
            manager.update_profile_from_approval("client-fifo", f"Post {i}")

        profile = manager.load_profile("client-fifo")

        assert len(profile.example_approved_posts) == MAX_APPROVED_EXAMPLES

    def test_update_profile_from_rejection_adds_post(self, tmp_path: Path):
        """update_profile_from_rejection adds rejected post."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        manager.create_profile("client-reject", "Professional")
        profile = manager.update_profile_from_rejection(
            "client-reject",
            "This is a rejected post",
            "Not on brand",
        )

        assert len(profile.example_rejected_posts) == 1
        assert "REASON: Not on brand" in profile.example_rejected_posts[0]

    def test_update_profile_from_rejection_fifo(self, tmp_path: Path):
        """Rejected posts FIFO after max limit."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        manager.create_profile("client-reject-fifo", "Professional")

        for i in range(MAX_REJECTED_EXAMPLES + 5):
            manager.update_profile_from_rejection("client-reject-fifo", f"Post {i}")

        profile = manager.load_profile("client-reject-fifo")

        assert len(profile.example_rejected_posts) == MAX_REJECTED_EXAMPLES

    def test_apply_voice_with_profile(self, tmp_path: Path):
        """apply_voice applies profile to content."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        manager.create_profile("client-voice", "Professional, warm")

        content = "This is the original content"
        rewritten = manager.apply_voice(content, "client-voice")

        assert "professional" in rewritten.lower() or "warm" in rewritten.lower() or content in rewritten

    def test_apply_voice_without_profile_returns_original(self, tmp_path: Path):
        """apply_voice returns original if no profile."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        content = "Original content here"
        rewritten = manager.apply_voice(content, "no-profile-client")

        assert rewritten == content

    def test_load_style_guide_client_specific(self, tmp_path: Path):
        """load_style_guide loads client-specific guide."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        client_guide = fs.get_style_guide_path("client-style")
        client_guide.parent.mkdir(parents=True, exist_ok=True)
        client_guide.write_text("Client style guide content")

        guide = manager.load_style_guide("client-style")

        assert guide == "Client style guide content"

    def test_load_style_guide_default(self, tmp_path: Path):
        """load_style_guide loads default guide."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        default_guide = fs.get_style_guide_path()
        default_guide.parent.mkdir(parents=True, exist_ok=True)
        default_guide.write_text("Default style guide")

        guide = manager.load_style_guide()

        assert guide == "Default style guide"

    def test_load_style_guide_none_if_missing(self, tmp_path: Path):
        """load_style_guide returns None if missing."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        guide = manager.load_style_guide("nonexistent")

        assert guide is None


class TestContentScheduler:
    """Tests for ContentScheduler class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        scheduler = ContentScheduler(fs, op_log)

        return fs, op_log, scheduler

    def test_morning_planning_logs_execution(self, tmp_path: Path):
        """Morning planning creates log entry."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        scheduler.trigger_morning_planning()

        entries = op_log.read_recent(days=1, action_type="morning_planning_started")
        assert len(entries) == 1

        entries = op_log.read_recent(days=1, action_type="morning_planning_completed")
        assert len(entries) == 1

    def test_morning_planning_reads_briefs(self, tmp_path: Path):
        """Morning planning reads active briefs."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        brief_manager = BriefManager(fs, op_log)
        scheduler._brief_manager = brief_manager

        message = {
            "payload": {
                "project_id": "proj-1",
                "client_id": "client-1",
                "brief_text": "Test brief",
                "deadline": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }
        brief_manager.receive_brief(message)

        scheduler.trigger_morning_planning()

        entries = op_log.read_recent(days=1, action_type="morning_planning_completed")
        assert entries[0].details["active_briefs"] == 1

    def test_weekly_analytics_query_sends_message(self, tmp_path: Path):
        """Weekly query sends analytics message."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        mock_mesh = MagicMock()
        scheduler._mesh = mock_mesh

        scheduler.trigger_weekly_query()

        mock_mesh.send.assert_called_once()
        call_args = mock_mesh.send.call_args[0][0]
        assert call_args["message_type"] == "content_performance_query"
        assert call_args["payload"]["query"] == "top_performing_formats"

    def test_weekly_query_logs(self, tmp_path: Path):
        """Weekly query creates log entry."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        scheduler.trigger_weekly_query()

        entries = op_log.read_recent(days=1, action_type="analytics_query_sent")
        assert len(entries) == 1

    def test_handle_analytics_intel_writes_file(self, tmp_path: Path):
        """handle_analytics_intel writes to intel file."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "top_formats": ["video", "carousel"],
                "best_posting_times": ["09:00", "18:00"],
            }
        }

        scheduler.handle_analytics_intel(message)

        intel_path = fs.BASE / "intelligence" / "analytics-feed" / "latest.json"
        assert intel_path.exists()

        data = json.loads(intel_path.read_text())
        assert data["source"] == "analytics_claw"
        assert "top_formats" in data["data"]

    def test_handle_analytics_intel_logs(self, tmp_path: Path):
        """handle_analytics_intel creates log entry."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        message = {"payload": {"data": "test"}}
        scheduler.handle_analytics_intel(message)

        entries = op_log.read_recent(days=1, action_type="intel_received")
        assert len(entries) == 1

    def test_scheduler_start_and_stop(self, tmp_path: Path):
        """Scheduler starts and stops cleanly."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        scheduler.start()
        assert scheduler._running is True

        scheduler.stop()
        assert scheduler._running is False


class TestSentenceLengthInference:
    """Tests for sentence length inference."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BrandVoiceManager(fs, op_log)
        return fs, op_log, manager

    def test_short_sentence_length_detected(self, tmp_path: Path):
        """'concise' tone leads to short sentence length."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        profile = manager.create_profile(
            "client-short",
            "Concise and brief messaging",
        )

        assert profile.sentence_length == "short"

    def test_long_sentence_length_detected(self, tmp_path: Path):
        """'detailed' tone leads to long sentence length."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        profile = manager.create_profile(
            "client-long",
            "Detailed and comprehensive explanations",
        )

        assert profile.sentence_length == "long"

    def test_medium_sentence_length_default(self, tmp_path: Path):
        """Default is medium sentence length."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        profile = manager.create_profile(
            "client-medium",
            "Professional tone",
        )

        assert profile.sentence_length == "medium"
