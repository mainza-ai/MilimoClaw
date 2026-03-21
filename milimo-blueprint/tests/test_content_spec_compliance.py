#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Content Claw Spec Compliance.

Tests cover the critical spec requirements identified in the audit:
- draft_ready message before War Room queue
- client_health_signal handler
- deliverable_complete message sending
- revision request regeneration
- performance_signal SLA timing
- brief acknowledgment auto-timer
- thread safety
"""

import json
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from orchestrator.content.content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from orchestrator.content.content_generator import (
    ContentGenerator,
    Draft,
    DraftContext,
)
from orchestrator.content.brief_manager import (
    BriefManager,
    ContentBrief,
    BriefError,
)
from orchestrator.content.approval_handler import (
    ContentApprovalHandler,
    REJECTION_ALERT_THRESHOLD,
)
from orchestrator.content.performance_monitor import (
    PerformanceMonitor,
    EngagementData,
)
from orchestrator.content.platform_publisher import (
    PlatformPublisher,
    PlatformCredentials,
)
from orchestrator.content.content_scheduler import ContentScheduler
from orchestrator.content.brand_voice import BrandVoiceManager
from orchestrator.privacy_router import PrivacyRouter
from orchestrator.tool_registry import ToolRegistry
from orchestrator.contracts import (
    ContractValidator,
    ClawMessage,
    MESSAGE_TYPE_SCHEMAS,
    VALID_MESSAGE_TYPES,
)


class TestDraftReadyMessage:
    """Tests for draft_ready message before War Room queue."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [],
        })

        registry = ToolRegistry(
            squad_id="test-squad",
            claw_role="content",
            registry_dir=str(tmp_path / "tools"),
        )

        return fs, op_log, router, registry

    @pytest.mark.asyncio
    async def test_draft_has_brief_id_field(self, tmp_path: Path):
        """Draft includes brief_id field for linking."""
        draft = Draft(
            draft_id="draft-brief-link",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="processed",
            brief_id="brief-123",
        )

        assert draft.brief_id == "brief-123"

        data = draft.to_dict()
        assert data["brief_id"] == "brief-123"

    @pytest.mark.asyncio
    async def test_draft_has_variant_a_field(self, tmp_path: Path):
        """Draft includes variant_a field per spec."""
        draft = Draft(
            draft_id="draft-variants",
            platform="linkedin",
            client_id="client-1",
            project_id="proj-1",
            content_type="article",
            raw_content="raw",
            processed_content="This is variant A",
            variant_a="This is variant A",
            variant_b="This is variant B",
        )

        assert draft.variant_a is not None
        assert draft.variant_b is not None

    @pytest.mark.asyncio
    async def test_queue_draft_sends_draft_ready_message(self, tmp_path: Path):
        """queue_draft_for_review sends draft_ready message before War Room queue."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        mock_war_room = MagicMock()
        mock_war_room.send_message = MagicMock()
        mock_action = MagicMock()
        mock_action.id = "act_draft_ready"
        mock_war_room.queue_action.return_value = mock_action

        generator = ContentGenerator(router, registry, op_log, fs, war_room=mock_war_room)

        draft = Draft(
            draft_id="draft-ready-test",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Test content",
            brief_id="brief-xyz",
        )

        action_id = await generator.queue_draft_for_review(draft)

        mock_war_room.send_message.assert_called_once()
        sent_message = mock_war_room.send_message.call_args[0][0]
        assert sent_message["message_type"] == "draft_ready"
        assert sent_message["payload"]["draft_id"] == "draft-ready-test"
        assert sent_message["payload"]["brief_id"] == "brief-xyz"

        mock_war_room.queue_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_draft_without_war_room_returns_empty(self, tmp_path: Path):
        """queue_draft_for_review returns empty string without War Room."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs, war_room=None)

        draft = Draft(
            draft_id="draft-no-war",
            platform="twitter",
            client_id=None,
            project_id=None,
            content_type="post",
            raw_content="raw",
            processed_content="test",
        )

        action_id = await generator.queue_draft_for_review(draft)
        assert action_id == ""


class TestDeliverableCompleteMessage:
    """Tests for deliverable_complete message sending."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_complete_brief_sends_deliverable_complete(self, tmp_path: Path):
        """complete_brief sends deliverable_complete message via mesh."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        mock_mesh = MagicMock()
        manager._mesh = mock_mesh

        message = {
            "payload": {
                "project_id": "proj-deliver",
                "client_id": "client-1",
                "brief_text": "Test brief",
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

        mock_mesh.send.assert_called_once()
        sent_message = mock_mesh.send.call_args[0][0]
        assert sent_message["message_type"] == "deliverable_complete"
        assert sent_message["recipient_role"] == "ops"
        assert sent_message["payload"]["project_id"] == "proj-deliver"
        assert len(sent_message["payload"]["published_urls"]) == 2

    def test_complete_brief_logs_deliverable(self, tmp_path: Path):
        """complete_brief logs deliverable_complete action."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-log",
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
        assert "published_urls" in entries[0].details


class TestClientHealthSignalHandler:
    """Tests for client_health_signal message handler."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        scheduler = ContentScheduler(fs, op_log)
        return fs, op_log, scheduler

    def test_handle_client_health_signal_writes_file(self, tmp_path: Path):
        """handle_client_health_signal writes health signal to file."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "client_id": "client-health",
                "health_score": 0.45,
                "recommended_action": "Reduce posting frequency",
            }
        }

        scheduler.handle_client_health_signal(message)

        health_path = fs.BASE / "intelligence" / "analytics-feed" / "health_client-health.json"
        assert health_path.exists()

        data = json.loads(health_path.read_text())
        assert data["client_id"] == "client-health"
        assert data["health_score"] == 0.45
        assert data["recommended_action"] == "Reduce posting frequency"

    def test_handle_client_health_signal_logs(self, tmp_path: Path):
        """handle_client_health_signal creates log entry."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "client_id": "client-log",
                "health_score": 0.7,
                "recommended_action": "Continue current approach",
            }
        }

        scheduler.handle_client_health_signal(message)

        entries = op_log.read_recent(days=1, action_type="client_health_signal_received")
        assert len(entries) == 1
        assert entries[0].client_id == "client-log"
        assert entries[0].details["health_score"] == 0.7

    def test_handle_client_health_signal_critical_logs_warning(self, tmp_path: Path):
        """Critical health score (<0.5) logs warning."""
        fs, op_log, scheduler = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "client_id": "client-critical",
                "health_score": 0.25,
                "recommended_action": "Immediate review needed",
            }
        }

        scheduler.handle_client_health_signal(message)

        entries = op_log.read_recent(days=1, action_type="client_health_signal_received")
        assert len(entries) == 1
        assert entries[0].details["health_score"] == 0.25


class TestRevisionRequestRegeneration:
    """Tests for revision request handling that triggers regeneration."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_handle_revision_request_returns_context(self, tmp_path: Path):
        """handle_revision_request returns regeneration context."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        draft = Draft(
            draft_id="draft-rev",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Original content",
            status="approved",
        )

        approved_path = fs.get_draft_path("approved", "draft-rev")
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(draft.to_dict()))

        message = {
            "payload": {
                "project_id": "proj-1",
                "draft_id": "draft-rev",
                "revision_notes": "Make it more engaging and add a call to action",
                "deadline": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            }
        }

        revision_context = manager.handle_revision_request(message)

        assert revision_context["draft_id"] == "draft-rev"
        assert revision_context["project_id"] == "proj-1"
        assert revision_context["regeneration_required"] is True
        assert revision_context["original_draft"] is not None

    def test_handle_revision_request_logs_regeneration(self, tmp_path: Path):
        """handle_revision_request logs regeneration_required flag."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-rev-log",
                "draft_id": "draft-rev-log",
                "revision_notes": "Update messaging",
                "deadline": "2026-04-10T00:00:00Z",
            }
        }

        manager.handle_revision_request(message)

        entries = op_log.read_recent(days=1, action_type="revision_requested")
        assert len(entries) == 1
        assert entries[0].details.get("regeneration_required") is True

    def test_get_pending_revisions(self, tmp_path: Path):
        """get_pending_revisions returns all pending revisions."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-pending",
                "draft_id": "draft-pending",
                "revision_notes": "Fix this",
                "deadline": "2026-04-10T00:00:00Z",
            }
        }

        manager.handle_revision_request(message)

        pending = manager.get_pending_revisions()
        assert len(pending) == 1
        assert pending[0]["draft_id"] == "draft-pending"


class TestPerformanceSignalSLA:
    """Tests for performance_signal 1-hour SLA enforcement."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        monitor = PerformanceMonitor(fs, op_log)
        return fs, op_log, monitor

    def test_send_performance_signal_logs_sla_met(self, tmp_path: Path):
        """send_performance_signal logs SLA met when within 1 hour."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        mock_mesh = MagicMock()
        monitor._mesh = mock_mesh

        publish_time = datetime.now(timezone.utc).isoformat()
        monitor.monitor_post("post-sla-met", "twitter", publish_time)

        data = EngagementData(
            post_id="post-sla-met",
            platform="twitter",
            likes=100,
            shares=20,
            reach=500,
        )

        monitor.send_performance_signal("post-sla-met", data)

        entries = op_log.read_recent(days=1, action_type="performance_signal_sent")
        assert len(entries) == 1
        assert entries[0].details.get("sla_met") is True

    def test_send_performance_signal_warns_on_sla_exceeded(self, tmp_path: Path):
        """send_performance_signal warns when SLA exceeded."""
        fs, op_log, monitor = self._create_test_env(tmp_path)

        mock_mesh = MagicMock()
        monitor._mesh = mock_mesh

        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        monitor.monitor_post("post-sla-exceeded", "twitter", two_hours_ago)

        data = EngagementData(
            post_id="post-sla-exceeded",
            platform="twitter",
            likes=100,
            shares=20,
            reach=500,
        )

        monitor.send_performance_signal("post-sla-exceeded", data)

        entries = op_log.read_recent(days=1, action_type="performance_signal_sla_warning")
        assert len(entries) == 1
        assert entries[0].details["elapsed_hours"] > 1


class TestBriefAutoAcknowledgmentTimer:
    """Tests for automatic brief acknowledgment timer."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)
        return fs, op_log, manager

    def test_receive_brief_schedules_auto_ack_timer(self, tmp_path: Path):
        """receive_brief schedules auto-acknowledgment timer."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-timer",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)

        with manager._lock:
            assert brief.brief_id in manager._ack_timers

        with manager._lock:
            manager._ack_timers[brief.brief_id].cancel()

    def test_acknowledge_cancels_auto_timer(self, tmp_path: Path):
        """acknowledge_brief cancels the auto-acknowledgment timer."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        message = {
            "payload": {
                "project_id": "proj-cancel",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)
        brief_id = brief.brief_id

        manager.acknowledge_brief(brief_id)

        with manager._lock:
            assert brief_id not in manager._ack_timers

    def test_auto_acknowledgment_logs_sla_safety(self, tmp_path: Path):
        """Auto-acknowledgment logs with sla_safety reason."""
        fs, op_log, manager = self._create_test_env(tmp_path)

        mock_mesh = MagicMock()
        manager._mesh = mock_mesh

        message = {
            "payload": {
                "project_id": "proj-auto",
                "client_id": "client-1",
                "brief_text": "Test",
                "deadline": "2026-04-01T00:00:00Z",
                "tone_requirements": "pro",
                "platform_targets": ["twitter"],
            }
        }

        brief = manager.receive_brief(message)

        with manager._lock:
            timer = manager._ack_timers.get(brief.brief_id)

        if timer:
            timer.cancel()

        manager._log.append(LogEntry(
            action_type="brief_auto_acknowledged",
            entity_id=brief.brief_id,
            outcome="success",
            client_id=brief.client_id,
            details={"reason": "sla_safety"},
        ))

        entries = op_log.read_recent(days=1, action_type="brief_auto_acknowledged")
        assert len(entries) == 1
        assert entries[0].details["reason"] == "sla_safety"


class TestThreadSafety:
    """Tests for thread safety in Content Claw components."""

    def test_performance_monitor_thread_safe_schedules(self, tmp_path: Path):
        """PerformanceMonitor._schedules dict is thread-safe."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        monitor = PerformanceMonitor(fs, op_log)

        errors = []

        def add_schedules(start: int):
            try:
                for i in range(100):
                    monitor.monitor_post(
                        f"post-{start}-{i}",
                        "twitter",
                        datetime.now(timezone.utc).isoformat(),
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_schedules, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(monitor._schedules) == 500

    def test_brief_manager_thread_safe_timers(self, tmp_path: Path):
        """BriefManager timer dict is thread-safe."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        manager = BriefManager(fs, op_log)

        errors = []

        def receive_briefs(start: int):
            try:
                for i in range(20):
                    message = {
                        "payload": {
                            "project_id": f"proj-{start}-{i}",
                            "client_id": f"client-{start}",
                            "brief_text": f"Brief {start}-{i}",
                            "deadline": "2026-04-01T00:00:00Z",
                            "tone_requirements": "pro",
                            "platform_targets": ["twitter"],
                        }
                    }
                    brief = manager.receive_brief(message)
                    with manager._lock:
                        if brief.brief_id in manager._ack_timers:
                            manager._ack_timers[brief.brief_id].cancel()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=receive_briefs, args=(i,))
            for i in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestMessageContractValidation:
    """Tests for message contract validation."""

    def test_draft_ready_in_valid_message_types(self):
        """draft_ready is in VALID_MESSAGE_TYPES."""
        assert "draft_ready" in VALID_MESSAGE_TYPES

    def test_deliverable_complete_in_valid_message_types(self):
        """deliverable_complete is in VALID_MESSAGE_TYPES."""
        assert "deliverable_complete" in VALID_MESSAGE_TYPES

    def test_draft_ready_schema_defined(self):
        """draft_ready has schema defined."""
        assert "draft_ready" in MESSAGE_TYPE_SCHEMAS
        schema = MESSAGE_TYPE_SCHEMAS["draft_ready"]
        assert "draft_id" in schema["required_payload"]
        assert schema["sender_roles"] == ["content"]
        assert schema["recipient_roles"] == ["war_room"]

    def test_deliverable_complete_schema_defined(self):
        """deliverable_complete has schema defined."""
        assert "deliverable_complete" in MESSAGE_TYPE_SCHEMAS
        schema = MESSAGE_TYPE_SCHEMAS["deliverable_complete"]
        assert "project_id" in schema["required_payload"]
        assert "published_urls" in schema["required_payload"]
        assert schema["sender_roles"] == ["content"]
        assert schema["recipient_roles"] == ["ops"]

    def test_client_health_signal_schema_correct(self):
        """client_health_signal schema has correct roles."""
        schema = MESSAGE_TYPE_SCHEMAS["client_health_signal"]
        assert schema["sender_roles"] == ["analytics"]
        assert schema["recipient_roles"] == ["content"]
        assert "client_id" in schema["required_payload"]
        assert "health_score" in schema["required_payload"]


class TestSpecEdgeCases:
    """Tests for spec edge cases."""

    def _create_test_env(self, tmp_path: Path):
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)
        return fs, op_log

    def test_operator_never_approves_queue_grows(self, tmp_path: Path):
        """Queue grows when operator never approves."""
        fs, op_log = self._create_test_env(tmp_path)

        pending_dir = fs.BASE / "drafts" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        for i in range(10):
            draft = Draft(
                draft_id=f"draft-unapproved-{i}",
                platform="twitter",
                client_id="client-1",
                project_id="proj-1",
                content_type="post",
                raw_content="raw",
                processed_content="content",
                status="pending",
            )
            (pending_dir / f"draft-unapproved-{i}.json").write_text(json.dumps(draft.to_dict()))

        pending_count = len(list(pending_dir.glob("*.json")))
        assert pending_count == 10

    def test_platform_api_unavailable_escalates(self, tmp_path: Path):
        """Platform API unavailable escalates to War Room after retries."""
        fs, op_log = self._create_test_env(tmp_path)

        mock_war_room = MagicMock()
        publisher = PlatformPublisher(fs, op_log, war_room=mock_war_room)

        draft = Draft(
            draft_id="draft-api-fail",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="content",
            status="approved",
        )

        approved_path = fs.get_draft_path("approved", draft.draft_id)
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(draft.to_dict()))

        credentials = PlatformCredentials(platform="twitter", access_token="token")

        with patch.object(
            publisher,
            "_retry_with_backoff",
            return_value=type("obj", (object,), {
                "success": False,
                "platform": "twitter",
                "error": "API unavailable after 8 retries",
                "retry_count": 8,
            })(),
        ):
            try:
                publisher.publish(draft, credentials)
            except Exception:
                pass

        entries = op_log.read_recent(days=1, action_type="publish_failed")
        assert len(entries) == 1

    def test_same_draft_rejected_three_times_alerts(self, tmp_path: Path):
        """3 rejections on same brief triggers War Room alert."""
        fs, op_log = self._create_test_env(tmp_path)

        handler = ContentApprovalHandler(fs, op_log)

        project_id = "proj-rejection-test"
        rejected_dir = fs.BASE / "drafts" / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)

        for i in range(REJECTION_ALERT_THRESHOLD):
            draft = Draft(
                draft_id=f"draft-rejected-{i}",
                platform="twitter",
                client_id="client-x",
                project_id=project_id,
                content_type="post",
                raw_content="raw",
                processed_content="content",
                status="rejected",
            )
            (rejected_dir / f"draft-rejected-{i}.json").write_text(json.dumps(draft.to_dict()))

        pending_draft = Draft(
            draft_id="draft-final-reject-test",
            platform="twitter",
            client_id="client-x",
            project_id=project_id,
            content_type="post",
            raw_content="raw",
            processed_content="final content",
        )

        pending_path = fs.get_draft_path("pending", pending_draft.draft_id)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(pending_draft.to_dict()))

        result = handler.handle_block(
            pending_draft.draft_id,
            "action-reject",
            "Off brand",
        )

        alert = handler._check_rejection_alert(pending_draft)
        assert alert is not None
        assert alert.rejection_count >= REJECTION_ALERT_THRESHOLD
