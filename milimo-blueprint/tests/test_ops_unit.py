# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Unit Tests

Comprehensive unit tests for Ops Claw components.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

_test_dir = Path(__file__).parent
_orchestrator_parent = _test_dir.parent
if str(_orchestrator_parent) not in sys.path:
    sys.path.insert(0, str(_orchestrator_parent))

from orchestrator.ops.ops_init import (
    OpsFilesystemInit,
    OpsOperationalLog,
    OpsCommsLog,
    OpsLogEntry,
    CommsLogEntry,
)
from orchestrator.ops.signal_dispatcher import (
    OpsSignalDispatcher,
    PricingNotConfirmedError,
)
from orchestrator.ops.approval_handler import OpsApprovalHandler
from orchestrator.ops.intake_manager import IntakeManager, TriageScore
from orchestrator.ops.health_scorer import ClientHealthScorer, ClientHealthScore
from orchestrator.ops.project_manager import ProjectManager, ProjectStatus
from orchestrator.ops.scope_monitor import ScopeMonitor
from orchestrator.ops.ops_claw import OpsClaw, MockMeshGateway


# ─────────────────────────────────────────────────────────────────────────────
# Mock Classes
# ─────────────────────────────────────────────────────────────────────────────


class MockInferenceClient:
    """Mock inference client for testing."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 100) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "data_type": data_type,
                "max_tokens": max_tokens,
            }
        )
        return self.responses.get(data_type, '{"result": "mocked"}')


class MockDispatcher:
    """Mock signal dispatcher."""

    def __init__(self):
        self.calls: list[dict] = []

    def send_project_brief(self, **kwargs):
        self.calls.append({"type": "project_brief", **kwargs})

    def send_pricing_query(self, **kwargs):
        self.calls.append({"type": "pricing_query", **kwargs})

    def send_project_complete(self, **kwargs):
        self.calls.append({"type": "project_complete", **kwargs})

    def send_client_health_signal(self, **kwargs):
        self.calls.append({"type": "client_health_signal", **kwargs})

    def send_client_onboarded(self, **kwargs):
        self.calls.append({"type": "client_onboarded", **kwargs})

    def mark_pricing_confirmed(self, project_id: str):
        self.calls.append({"type": "pricing_confirmed", "project_id": project_id})


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_sandbox(tmp_path: Path) -> Path:
    """Create a temporary sandbox directory."""
    sandbox = tmp_path / "sandbox" / "clients"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


@pytest.fixture
def fs(temp_sandbox: Path) -> OpsFilesystemInit:
    """Create an initialized filesystem."""
    fs = OpsFilesystemInit(temp_sandbox)
    fs.initialize()
    return fs


@pytest.fixture
def operational_log(temp_sandbox: Path) -> OpsOperationalLog:
    """Create an operational log."""
    log_path = temp_sandbox / "logs" / "operational.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return OpsOperationalLog(log_path)


@pytest.fixture
def comms_log(temp_sandbox: Path) -> OpsCommsLog:
    """Create a comms log."""
    log_path = temp_sandbox / "logs" / "comms.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return OpsCommsLog(log_path)


@pytest.fixture
def approval_handler(temp_sandbox: Path) -> OpsApprovalHandler:
    """Create an approval handler."""
    return OpsApprovalHandler(fs_base=temp_sandbox)


@pytest.fixture
def mock_gateway() -> MockMeshGateway:
    """Create a mock mesh gateway."""
    return MockMeshGateway()


@pytest.fixture
def dispatcher(
    mock_gateway: MockMeshGateway,
    operational_log: OpsOperationalLog,
    temp_sandbox: Path,
) -> OpsSignalDispatcher:
    """Create a signal dispatcher."""
    return OpsSignalDispatcher(
        gateway=mock_gateway,
        operational_log=operational_log,
        squad_id="test-squad",
        pricing_confirmed_dir=temp_sandbox / "pricing_confirmed",
    )


@pytest.fixture
def inference_client() -> MockInferenceClient:
    """Create a mock inference client."""
    return MockInferenceClient()


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsFilesystemInit
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsFilesystemInit:
    def test_initialize_creates_directories(self, fs: OpsFilesystemInit):
        assert (fs.BASE / "active").is_dir()
        assert (fs.BASE / "prospects").is_dir()
        assert (fs.BASE / "completed").is_dir()
        assert (fs.BASE / "contracts").is_dir()
        assert (fs.BASE / "templates").is_dir()
        assert (fs.BASE / "logs").is_dir()

    def test_initialize_creates_templates(self, fs: OpsFilesystemInit):
        assert (fs.BASE / "templates" / "welcome-message.md").is_file()
        assert (fs.BASE / "templates" / "intake-questionnaire.md").is_file()
        assert (fs.BASE / "templates" / "proposal-template.md").is_file()

    def test_initialize_is_idempotent(self, fs: OpsFilesystemInit):
        result = fs.initialize()
        assert result.success
        assert len(result.already_existed) > 0

    def test_create_client_dirs(self, fs: OpsFilesystemInit):
        fs.create_client_dirs("client-123")
        assert (fs.BASE / "active" / "client-123").is_dir()
        assert (fs.BASE / "active" / "client-123" / "projects").is_dir()
        assert (fs.BASE / "active" / "client-123" / "comms").is_dir()

    def test_create_project_dirs(self, fs: OpsFilesystemInit):
        fs.create_client_dirs("client-123")
        fs.create_project_dirs("client-123", "project-456")
        assert (
            fs.BASE / "active" / "client-123" / "projects" / "project-456"
        ).is_dir()

    def test_get_template(self, fs: OpsFilesystemInit):
        template = fs.get_template("welcome-message.md")
        assert "{{client_name}}" in template

    def test_get_template_raises_if_missing(self, fs: OpsFilesystemInit):
        with pytest.raises(FileNotFoundError):
            fs.get_template("nonexistent.md")


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsOperationalLog
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsOperationalLog:
    def test_append_and_read(self, operational_log: OpsOperationalLog):
        entry = OpsLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="test_action",
            entity_id="test-entity",
            outcome="success",
            details={"key": "value"},
        )
        operational_log.append(entry)

        entries = operational_log.read_recent(days=1)
        assert len(entries) == 1
        assert entries[0].action_type == "test_action"

    def test_read_by_action_type(self, operational_log: OpsOperationalLog):
        for i in range(3):
            operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="type_a" if i < 2 else "type_b",
                    entity_id=f"entity-{i}",
                    outcome="success",
                )
            )

        type_a_count = operational_log.count_by_type("type_a", days=1)
        assert type_a_count == 2


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsCommsLog
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsCommsLog:
    def test_append_and_get_client_history(self, comms_log: OpsCommsLog):
        comms_log.append(
            CommsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                direction="received",
                client_id="client-1",
                project_id=None,
                channel="email",
                content_preview="Hello, I have a question...",
            )
        )

        history = comms_log.get_client_history("client-1")
        assert len(history) == 1

    def test_get_response_times(self, comms_log: OpsCommsLog):
        now = datetime.now(timezone.utc)

        comms_log.append(
            CommsLogEntry(
                timestamp=(now - timedelta(hours=5)).isoformat(),
                direction="received",
                client_id="client-1",
                project_id=None,
                channel="email",
                content_preview="Question",
            )
        )

        comms_log.append(
            CommsLogEntry(
                timestamp=(now - timedelta(hours=4)).isoformat(),
                direction="sent",
                client_id="client-1",
                project_id=None,
                channel="email",
                content_preview="Response",
            )
        )

        times = comms_log.get_response_times("client-1")
        assert len(times) == 1
        assert 0.5 <= times[0] <= 1.5  # ~1 hour


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsSignalDispatcher
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsSignalDispatcher:
    def test_send_pricing_query(
        self,
        dispatcher: OpsSignalDispatcher,
        mock_gateway: MockMeshGateway,
        operational_log: OpsOperationalLog,
    ):
        dispatcher.send_pricing_query(
            project_id="project-1",
            scope_description="Test scope",
            complexity_estimate="medium",
            deadline="2025-01-01",
            client_id="client-1",
        )

        assert len(mock_gateway.calls) == 1
        assert mock_gateway.calls[0]["message_type"] == "pricing_query"

    def test_send_project_brief_requires_pricing(
        self,
        dispatcher: OpsSignalDispatcher,
    ):
        with pytest.raises(PricingNotConfirmedError):
            dispatcher.send_project_brief(
                client_id="client-1",
                project_id="project-1",
                brief_text="Test brief",
                deadline="2025-01-01",
                tone_requirements="professional",
                platform_targets=["email"],
                recipient_role="content",
            )

    def test_send_project_brief_after_pricing_confirmed(
        self,
        dispatcher: OpsSignalDispatcher,
        mock_gateway: MockMeshGateway,
    ):
        dispatcher.mark_pricing_confirmed("project-1")

        dispatcher.send_project_brief(
            client_id="client-1",
            project_id="project-1",
            brief_text="Test brief",
            deadline="2025-01-01",
            tone_requirements="professional",
            platform_targets=["email"],
            recipient_role="content",
        )

        assert len(mock_gateway.calls) == 1
        assert mock_gateway.calls[0]["message_type"] == "project_brief"

    def test_send_client_health_signal(
        self,
        dispatcher: OpsSignalDispatcher,
        mock_gateway: MockMeshGateway,
    ):
        dispatcher.send_client_health_signal(
            client_id="client-1",
            health_score=7.5,
            health_factors=["good_response_time"],
            recommended_action="continue",
        )

        assert len(mock_gateway.calls) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsApprovalHandler
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsApprovalHandler:
    def test_queue_review(self, approval_handler: OpsApprovalHandler):
        action_id = approval_handler.queue_review(
            action_type="welcome_message",
            entity_id="inquiry-1",
            content="Test content",
            context={"key": "value"},
        )

        assert action_id is not None
        action = approval_handler.get_action(action_id)
        assert action is not None
        assert action.action_type == "welcome_message"
        assert action.mode == "REVIEW"

    def test_queue_hold(self, approval_handler: OpsApprovalHandler):
        action_id = approval_handler.queue_hold(
            action_type="scope_change_order",
            entity_id="project-1",
            content="Change order content",
            context={},
        )

        action = approval_handler.get_action(action_id)
        assert action is not None
        assert action.mode == "HOLD"

    def test_handle_approve(self, approval_handler: OpsApprovalHandler):
        action_id = approval_handler.queue_review(
            action_type="test",
            entity_id="test-1",
            content="Test",
            context={},
        )

        send_called = []

        def send_fn():
            send_called.append(True)

        result = approval_handler.handle_approve(action_id, send_fn)
        assert result is True
        assert len(send_called) == 1

    def test_handle_block(self, approval_handler: OpsApprovalHandler):
        action_id = approval_handler.queue_review(
            action_type="welcome_message",
            entity_id="inquiry-1",
            content="Test",
            context={},
        )

        result = approval_handler.handle_block(action_id, reason="operator_blocked")
        assert result is True

        action = approval_handler.get_action(action_id)
        assert action is None

    def test_add_urgency_flag_24h(self, approval_handler: OpsApprovalHandler):
        action_id = approval_handler.queue_review(
            action_type="welcome_message",
            entity_id="inquiry-1",
            content="Test",
            context={},
        )

        approval_handler.add_urgency_flag(action_id, hours_waiting=24)

        action = approval_handler.get_action(action_id)
        assert action is not None
        assert action.urgency_flag is not None
        assert "24h" in action.urgency_flag

    def test_add_urgency_flag_48h(self, approval_handler: OpsApprovalHandler):
        action_id = approval_handler.queue_review(
            action_type="welcome_message",
            entity_id="inquiry-1",
            content="Test",
            context={},
        )

        approval_handler.add_urgency_flag(action_id, hours_waiting=48)

        action = approval_handler.get_action(action_id)
        assert action is not None
        assert action.urgency_flag is not None
        assert "closing" in action.urgency_flag.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Test IntakeManager
# ─────────────────────────────────────────────────────────────────────────────


class TestIntakeManager:
    def test_triage_score_calculation(self):
        score = TriageScore(
            inquiry_id="test",
            budget_signal=8.0,
            scope_clarity=7.0,
            niche_fit=9.0,
            combined_score=0.0,
            routing="",
        )

        expected = (8.0 * 0.4) + (7.0 * 0.3) + (9.0 * 0.3)
        score.combined_score = expected

        assert abs(score.combined_score - 7.9) < 0.1

    def test_score_inquiry_uses_weights(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        responses = {
            "client_triage_scoring": '{"budget_signal": 9, "scope_clarity": 8, "niche_fit": 7}',
        }
        inference = MockInferenceClient(responses)
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")

        manager = IntakeManager(
            fs=fs,
            inference_client=inference,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        score = manager.score_inquiry(
            "Test inquiry about web development", "web development"
        )

        assert score.budget_signal == 9.0
        assert score.scope_clarity == 8.0
        assert score.niche_fit == 7.0

        expected = (9.0 * 0.4) + (8.0 * 0.3) + (7.0 * 0.3)
        assert abs(score.combined_score - expected) < 0.1

    def test_routing_thresholds(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        responses = {
            "client_triage_scoring": '{"budget_signal": 10, "scope_clarity": 10, "niche_fit": 10}',
        }
        inference = MockInferenceClient(responses)
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")

        manager = IntakeManager(
            fs=fs,
            inference_client=inference,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        score = manager.score_inquiry("Test", "test")

        expected = (10.0 * 0.4) + (10.0 * 0.3) + (10.0 * 0.3)
        assert abs(score.combined_score - expected) < 0.1
        assert score.routing == "draft_welcome"


# ─────────────────────────────────────────────────────────────────────────────
# Test ClientHealthScorer
# ─────────────────────────────────────────────────────────────────────────────


class TestClientHealthScorer:
    def test_health_score_weights(self):
        ClientHealthScore(
            client_id="test",
            score=0.0,
            health_level="healthy",
            response_time_avg_hrs=4.0,
            revision_request_rate=0.1,
            scope_adherence_score=10.0,
            communication_sentiment=8.0,
        )

        (8.0 * 0.3) + (10.0 * 0.25) + (10.0 * 0.25) + (8.0 * 0.2)

    def test_at_risk_threshold(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        comms_log: OpsCommsLog,
        approval_handler: OpsApprovalHandler,
    ):
        inference = MockInferenceClient()
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")

        scorer = ClientHealthScorer(
            fs=fs,
            inference_client=inference,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
            comms_log=comms_log,
        )

        assert scorer.AT_RISK_THRESHOLD == 6.0
        assert scorer.HEALTHY_THRESHOLD == 8.0

    def test_at_risk_queues_war_room(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        comms_log: OpsCommsLog,
        approval_handler: OpsApprovalHandler,
    ):
        responses = {
            "communication_sentiment_analysis": '{"sentiment_score": 2.0, "indicators": ["very negative"]}',
        }
        inference = MockInferenceClient(responses)
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(
            gateway, operational_log, "test-squad", fs.BASE / "pricing_confirmed"
        )

        scorer = ClientHealthScorer(
            fs=fs,
            inference_client=inference,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
            comms_log=comms_log,
        )

        fs.create_client_dirs("client-at-risk")
        profile_file = fs.get_client_path("active", "client-at-risk") / "profile.json"
        fs.write_json_atomic(
            profile_file, {"client_id": "client-at-risk", "name": "Test"}
        )

        base_time = datetime.now(timezone.utc)
        for i in range(5):
            comms_log.append(
                CommsLogEntry(
                    timestamp=(base_time - timedelta(hours=72 + i * 72)).isoformat(),
                    direction="received",
                    client_id="client-at-risk",
                    project_id=None,
                    channel="email",
                    content_preview="Very frustrated, this is unacceptable",
                )
            )
            comms_log.append(
                CommsLogEntry(
                    timestamp=(base_time - timedelta(hours=48 + i * 72)).isoformat(),
                    direction="sent",
                    client_id="client-at-risk",
                    project_id=None,
                    channel="email",
                    content_preview="We apologize for the delay",
                )
            )

        health = scorer.score_client("client-at-risk")

        if health.score < 6.0:
            review_queue = approval_handler.get_review_queue()
            at_risk_actions = [
                a for a in review_queue if a.action_type == "client_at_risk"
            ]
            assert len(at_risk_actions) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Test ProjectManager
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectManager:
    def test_check_deadlines_elevated_risk(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")

        manager = ProjectManager(
            fs=fs,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        status = ProjectStatus(
            project_id="project-1",
            client_id="client-1",
            status="active",
            deadline=deadline,
        )

        risk = manager._check_project_deadline(status)
        assert risk is not None
        assert risk.risk_level == "elevated"

    def test_check_deadlines_critical_risk(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")

        manager = ProjectManager(
            fs=fs,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        deadline = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

        status = ProjectStatus(
            project_id="project-1",
            client_id="client-1",
            status="active",
            deadline=deadline,
        )

        risk = manager._check_project_deadline(status)
        assert risk is not None
        assert risk.risk_level == "critical"

    def test_confirm_client_receipt_sends_project_complete(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(
            gateway, operational_log, "test-squad", fs.BASE / "pricing_confirmed"
        )

        manager = ProjectManager(
            fs=fs,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        fs.create_client_dirs("client-1")
        fs.create_project_dirs("client-1", "project-1")

        project_dir = fs.get_project_path("client-1", "project-1")
        status = ProjectStatus(
            project_id="project-1",
            client_id="client-1",
            status="delivered",
            deadline="2025-01-01",
            deliverable_received=True,
            client_confirmed=False,
        )
        fs.write_json_atomic(project_dir / "status.json", status.to_dict())

        dispatcher.mark_pricing_confirmed("project-1")

        gateway.calls.clear()

        manager.confirm_client_receipt("project-1")

        complete_calls = [
            c for c in gateway.calls if c.get("message_type") == "project_complete"
        ]
        assert len(complete_calls) == 1

        completed_dir = fs.BASE / "completed" / "client-1" / "project-1"
        updated_status = fs.read_json(completed_dir / "status.json")
        assert updated_status is not None
        assert updated_status["client_confirmed"] is True
        assert updated_status["status"] == "completed"


# ──────────────────────────────────────────────────────────────────────
# Test ScopeMonitor
# ───────────────────────────────────────────────────────────────


class TestScopeMonitor:
    def test_detection_threshold(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")
        inference = MockInferenceClient()

        monitor = ScopeMonitor(
            fs=fs,
            inference_client=inference,
            approval_handler=approval_handler,
            dispatcher=dispatcher,
            operational_log=operational_log,
        )

        assert monitor.DETECTION_THRESHOLD == 0.7

    def test_scope_creep_queues_hold(
        self,
        fs: OpsFilesystemInit,
        operational_log: OpsOperationalLog,
        approval_handler: OpsApprovalHandler,
    ):
        gateway = MockMeshGateway()
        dispatcher = OpsSignalDispatcher(gateway, operational_log, "test-squad")
        responses = {
            "scope_creep_detection": '{"is_scope_creep": true, "new_request": "Add extra pages", "confidence": 0.8}',
        }
        inference = MockInferenceClient(responses)

        monitor = ScopeMonitor(
            fs=fs,
            inference_client=inference,
            approval_handler=approval_handler,
            dispatcher=dispatcher,
            operational_log=operational_log,
        )

        fs.create_client_dirs("client-1")
        fs.create_project_dirs("client-1", "project-1")
        project_dir = fs.get_project_path("client-1", "project-1")
        fs.write_json_atomic(
            project_dir / "brief.json",
            {
                "raw_text": "Original scope: 5 page website",
                "scope_description": "5 page website",
            },
        )

        detection = monitor.check_message(
            client_id="client-1",
            project_id="project-1",
            message_text="Can you add 10 more pages?",
        )

        assert detection is not None
        assert detection.confidence > 0.7

        hold_queue = approval_handler.get_hold_queue()
        assert len(hold_queue) >= 1
        assert hold_queue[-1].action_type == "scope_change_order"


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsScheduler
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsScheduler:
    def test_seconds_until_positive(self):
        now = datetime.now(timezone.utc)
        now + timedelta(hours=2)

        pass


# ─────────────────────────────────────────────────────────────────────────────
# Test OpsClaw
# ─────────────────────────────────────────────────────────────────────────────


class TestOpsClaw:
    def test_startup_initializes_components(
        self,
        temp_sandbox: Path,
        inference_client: MockInferenceClient,
    ):
        gateway = MockMeshGateway()

        claw = OpsClaw(
            squad_id="test-squad",
            inference_client=inference_client,
            mesh_gateway=gateway,
            base_path=temp_sandbox,
        )

        claw.startup()

        assert claw._fs is not None
        assert claw._operational_log is not None
        assert claw._dispatcher is not None
        assert claw._approval_handler is not None
        assert claw._intake_manager is not None
        assert claw._project_manager is not None
        assert claw._health_scorer is not None
        assert claw._scope_monitor is not None
        assert claw._comms_manager is not None
        assert claw._scheduler is not None

        claw.shutdown()

    def test_handle_inbound_routes_message(
        self,
        temp_sandbox: Path,
        inference_client: MockInferenceClient,
    ):
        gateway = MockMeshGateway()

        claw = OpsClaw(
            squad_id="test-squad",
            inference_client=inference_client,
            mesh_gateway=gateway,
            base_path=temp_sandbox,
        )

        claw.startup()

        message = {
            "message_type": "deliverable_complete",
            "project_id": "project-1",
            "published_urls": ["https://example.com"],
        }

        claw.handle_inbound(message)

        claw.shutdown()

    def test_handle_pricing_response(
        self,
        temp_sandbox: Path,
        inference_client: MockInferenceClient,
    ):
        gateway = MockMeshGateway()

        claw = OpsClaw(
            squad_id="test-squad",
            inference_client=inference_client,
            mesh_gateway=gateway,
            base_path=temp_sandbox,
        )

        claw.startup()

        message = {
            "message_type": "pricing_response",
            "project_id": "project-1",
            "floor": 1000.0,
            "ceiling": 2000.0,
            "notes": "Test pricing",
        }

        claw.handle_inbound(message)

        claw.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
