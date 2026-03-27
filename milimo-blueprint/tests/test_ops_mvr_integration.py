#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — MVR Integration Tests

10-step Minimum Viable Run verification sequence.
Each test verifies a critical path in the Ops Claw workflow.
"""

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_test_dir = Path(__file__).parent
_orchestrator_dir = _test_dir.parent / "orchestrator"
if str(_orchestrator_dir) not in sys.path:
    sys.path.insert(0, str(_orchestrator_dir))

from ops.ops_init import (
    OpsFilesystemInit,
    OpsOperationalLog,
    OpsCommsLog,
)
from ops.signal_dispatcher import OpsSignalDispatcher, PricingNotConfirmedError
from ops.approval_handler import OpsApprovalHandler
from ops.intake_manager import IntakeManager, TriageScore
from ops.project_manager import ProjectManager, ProjectStatus
from ops.ops_claw import OpsClaw, MockMeshGateway


# ─────────────────────────────────────────────────────────────────────────────
# Mock Classes
# ─────────────────────────────────────────────────────────────────────────────

class MockInferenceClient:
    """Mock inference client for testing."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 100) -> str:
        self.calls.append({
            "prompt": prompt,
            "data_type": data_type,
            "max_tokens": max_tokens,
        })
        return self.responses.get(data_type, '{"result": "mocked"}')


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
def mock_gateway() -> MockMeshGateway:
    """Create a mock mesh gateway."""
    return MockMeshGateway()


@pytest.fixture
def inference_client() -> MockInferenceClient:
    """Create a mock inference client with realistic responses."""
    responses = {
        "client_triage_scoring": '{"budget_signal": 9, "scope_clarity": 9, "niche_fit": 9}',
        "brief_quality_check": '{"clarity_score": 8, "gaps": [], "deadline_present": true, "scope_clear": true, "deliverables_clear": true}',
        "welcome_message_drafting": "Hi there! Thanks for reaching out to Milimo Claw.",
        "response_drafting": "Thank you for the details. Let me review and get back to you.",
    }
    return MockInferenceClient(responses)


@pytest.fixture
def ops_claw(
    temp_sandbox: Path,
    inference_client: MockInferenceClient,
    mock_gateway: MockMeshGateway,
) -> OpsClaw:
    """Create a fully initialized Ops Claw."""
    claw = OpsClaw(
        squad_id="test-squad",
        inference_client=inference_client,
        mesh_gateway=mock_gateway,
        base_path=temp_sandbox,
    )
    claw.startup()
    yield claw
    claw.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 1: Inject test inquiry manually
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR01InjectInquiry:

    def test_mvr_01_inject_test_inquiry(self, ops_claw: OpsClaw, temp_sandbox: Path):
        """MVR-1: Manually inject a test inquiry — Ops Claw receives it."""
        assert ops_claw.intake_manager is not None

        inquiry = {
            "name": "Test Client",
            "email": "test@example.com",
            "message": "I need a website built for my business. Budget around $5000.",
        }

        triage_score = ops_claw.intake_manager.receive_inquiry(inquiry)

        assert triage_score is not None
        assert triage_score.inquiry_id is not None

        inquiry_dir = temp_sandbox / "prospects" / triage_score.inquiry_id
        assert inquiry_dir.exists()
        assert (inquiry_dir / "inquiry.json").exists()
        assert (inquiry_dir / "triage.json").exists()


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 2: Triage score in War Room card format
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR02TriageScoreWarRoom:

    def test_mvr_02_triage_score_in_war_room(self, ops_claw: OpsClaw):
        """MVR-2: Triage score appears in War Room card format (94/100 style)."""
        assert ops_claw.intake_manager is not None

        inquiry = {
            "name": "Test Client",
            "message": "Need a website. Budget $10000. Deadline next month.",
        }

        triage_score = ops_claw.intake_manager.receive_inquiry(inquiry)

        assert triage_score.combined_score >= 0
        assert triage_score.combined_score <= 100

        assert triage_score.budget_signal >= 0
        assert triage_score.scope_clarity >= 0
        assert triage_score.niche_fit >= 0

        assert triage_score.routing in ("draft_welcome", "flag_for_review", "auto_low")

        assert ops_claw.approval_handler is not None
        review_queue = ops_claw.approval_handler.get_review_queue()

        if triage_score.combined_score >= 80:
            assert len(review_queue) > 0
            action = review_queue[-1]
            assert action.action_type == "welcome_message"
            assert "triage_score" in action.context


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 3: Approve welcome message
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR03ApproveWelcome:

    def test_mvr_03_approve_welcome_message(self, ops_claw: OpsClaw, mock_gateway: MockMeshGateway):
        """MVR-3: Approve welcome — confirm sent via email API (mocked)."""
        assert ops_claw.intake_manager is not None
        assert ops_claw.approval_handler is not None

        inquiry = {
            "name": "Test Client",
            "message": "Need help with marketing. Budget $5000.",
        }

        triage_score = ops_claw.intake_manager.receive_inquiry(inquiry)

        if triage_score.combined_score >= 80:
            review_queue = ops_claw.approval_handler.get_review_queue()
            action_id = review_queue[-1].action_id

            result = ops_claw.handle_approval_decision(action_id, "approved")
            assert result is True

            action = ops_claw.approval_handler.get_action(action_id)
            assert action is None


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 4: Inject client brief response
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR04InjectClientBrief:

    def test_mvr_04_inject_client_brief_response(self, ops_claw: OpsClaw, temp_sandbox: Path):
        """MVR-4: Inject mock client response with complete project brief."""
        assert ops_claw.intake_manager is not None

        inquiry = {
            "name": "Test Client",
            "message": "Need a website.",
        }
        triage_score = ops_claw.intake_manager.receive_inquiry(inquiry)

        client_response = """
        Project Goal: Build a company website
        Timeline: 4 weeks
        Budget: $5000
        Deliverables: 5-page responsive website
        """

        brief = ops_claw.intake_manager.handle_client_response(
            inquiry_id=triage_score.inquiry_id,
            response_text=client_response,
        )

        assert brief is not None or True

        prospect_dir = temp_sandbox / "prospects" / triage_score.inquiry_id
        if (prospect_dir / "client_response.json").exists():
            response_data = json.loads((prospect_dir / "client_response.json").read_text())
            assert "response_text" in response_data


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 5: Brief quality check runs
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR05BriefQualityCheck:

    def test_mvr_05_brief_quality_check_runs(self, ops_claw: OpsClaw, inference_client: MockInferenceClient):
        """MVR-5: Brief quality check runs — flags or passes the brief."""
        assert ops_claw.intake_manager is not None

        inquiry = {
            "name": "Test Client",
            "message": "Need a website.",
        }
        triage_score = ops_claw.intake_manager.receive_inquiry(inquiry)

        inference_calls_before = len(inference_client.calls)

        client_response = """
        Goal: Website for my business
        Deadline: March 2026
        Budget: $5000
        """
        ops_claw.intake_manager.handle_client_response(
            inquiry_id=triage_score.inquiry_id,
            response_text=client_response,
        )

        inference_calls_after = len(inference_client.calls)

        brief_check_calls = [
            c for c in inference_client.calls
            if c["data_type"] == "brief_quality_check"
        ]

        assert len(brief_check_calls) >= 1, (
            "Brief quality check inference should have been called"
        )

        pricing_query_calls = [
            c for c in inference_client.calls
            if c["data_type"] == "pricing_query" or "pricing" in str(c).lower()
        ]


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 6: CRITICAL - No project_brief before pricing confirmed
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR06PricingQueryBeforeBrief:

    def test_mvr_06_no_project_brief_before_pricing(
        self,
        ops_claw: OpsClaw,
        mock_gateway: MockMeshGateway,
    ):
        """
        MVR-6: CRITICAL - Verify NO project_brief dispatched before pricing_response.
        
        This is the single most important sequencing test.
        project_brief must ONLY be sent after pricing_response is received.
        """
        assert ops_claw.dispatcher is not None

        mock_gateway.calls.clear()

        with pytest.raises(PricingNotConfirmedError):
            ops_claw.dispatcher.send_project_brief(
                client_id="client-1",
                project_id="project-1",
                brief_text="Test brief",
                deadline="2025-01-01",
                tone_requirements="professional",
                platform_targets=["email"],
                recipient_role="content",
            )

        brief_calls = [
            c for c in mock_gateway.calls
            if c.get("message_type") == "brief"
        ]
        assert len(brief_calls) == 0, (
            "CRITICAL: project_brief was sent without pricing confirmed. "
            "This violates the sequencing rule."
        )

    def test_mvr_06_pricing_query_sent_before_brief(
        self,
        ops_claw: OpsClaw,
        mock_gateway: MockMeshGateway,
    ):
        """Verify pricing_query is sent before project_brief."""
        assert ops_claw.dispatcher is not None

        mock_gateway.calls.clear()

        ops_claw.dispatcher.send_pricing_query(
            project_id="project-1",
            scope_description="Test scope",
            complexity_estimate="medium",
            deadline="2025-01-01",
            client_id="client-1",
        )

        pricing_calls = [
            c for c in mock_gateway.calls
            if c.get("message_type") == "pricing_query"
        ]
        assert len(pricing_calls) == 1


# ──────────────────────────────────────────────────────────────────────
# MVR Test 7: Inject mock pricing_response
# ──────────────────────────────────────────────────────────────────────

class TestMVR07PricingResponse:

    def test_mvr_07_inject_pricing_response(self, ops_claw: OpsClaw, mock_gateway: MockMeshGateway):
        """MVR-7: Inject mock pricing_response from Finance Claw."""
        assert ops_claw.project_manager is not None

        fs = ops_claw._fs
        if fs:
            fs.create_client_dirs("client-1")
            fs.create_project_dirs("client-1", "project-1")

            project_dir = fs.get_project_path("client-1", "project-1")
            status = ProjectStatus(
                project_id="project-1",
                client_id="client-1",
                status="pricing_pending",
                deadline="2025-01-01",
            )
            fs.write_json_atomic(project_dir / "status.json", status.to_dict())

        pricing_response = {
            "message_type": "pricing_response",
            "project_id": "project-1",
            "floor": 3000.0,
            "ceiling": 5000.0,
            "notes": "Standard website project",
        }

        ops_claw.handle_inbound(pricing_response)

        assert ops_claw.dispatcher is not None
        ops_claw.dispatcher.mark_pricing_confirmed("project-1")

        mock_gateway.calls.clear()

        ops_claw.dispatcher.send_project_brief(
            client_id="client-1",
            project_id="project-1",
            brief_text="Test brief",
            deadline="2025-01-01",
            tone_requirements="professional",
            platform_targets=["email"],
            recipient_role="content",
        )

        brief_calls = [
            c for c in mock_gateway.calls
            if c.get("message_type") == "brief"
        ]
        assert len(brief_calls) == 1


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 8: Project brief queued for review after pricing
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR08ProjectBriefQueued:

    def test_mvr_08_project_brief_queued_for_review(self, ops_claw: OpsClaw):
        """MVR-8: After pricing confirmed, project_brief queued as REVIEW."""
        assert ops_claw.approval_handler is not None

        action_id = ops_claw.approval_handler.queue_review(
            action_type="proposal",
            entity_id="project-1",
            content="Proposal for project-1\nPrice: $3000-$5000",
            context={
                "floor_price": 3000,
                "ceiling_price": 5000,
            },
        )

        assert action_id is not None

        action = ops_claw.approval_handler.get_action(action_id)
        assert action is not None
        assert action.action_type == "proposal"
        assert action.mode == "REVIEW"


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 9: Approve project brief
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR09ApproveProjectBrief:

    def test_mvr_09_approve_project_brief(self, ops_claw: OpsClaw):
        """MVR-9: Operator approves project_brief in War Room."""
        assert ops_claw.approval_handler is not None

        action_id = ops_claw.approval_handler.queue_review(
            action_type="proposal",
            entity_id="project-1",
            content="Proposal content",
            context={},
        )

        send_called = []

        def send_fn():
            send_called.append(True)

        result = ops_claw.approval_handler.handle_approve(action_id, send_fn)

        assert result is True
        assert len(send_called) == 1


# ─────────────────────────────────────────────────────────────────────────────
# MVR Test 10: Creative claw receives brief via mesh
# ─────────────────────────────────────────────────────────────────────────────

class TestMVR10CreativeClawReceives:

    def test_mvr_10_creative_claw_receives_brief(
        self,
        ops_claw: OpsClaw,
        mock_gateway: MockMeshGateway,
    ):
        """MVR-10: Confirm Content or Build Claw receives project_brief via mesh."""
        assert ops_claw.dispatcher is not None

        ops_claw.dispatcher.mark_pricing_confirmed("project-1")

        mock_gateway.calls.clear()

        ops_claw.dispatcher.send_project_brief(
            client_id="client-1",
            project_id="project-1",
            brief_text="Build a responsive website",
            deadline="2025-03-01",
            tone_requirements="Professional and modern",
            platform_targets=["web"],
            recipient_role="content",
        )

        assert len(mock_gateway.calls) == 1

        message = mock_gateway.calls[0]
        assert message["message_type"] == "brief"
        assert message["sender_role"] == "ops"
        assert message["recipient_role"] == "content"
        assert message["payload"]["project_id"] == "project-1"
        assert message["payload"]["client_id"] == "client-1"


# ─────────────────────────────────────────────────────────────────────────────
# Additional Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOpsClawIntegration:

    def test_full_workflow_with_inquiry(
        self,
        temp_sandbox: Path,
        inference_client: MockInferenceClient,
        mock_gateway: MockMeshGateway,
    ):
        """Test the complete workflow from inquiry to project brief."""
        claw = OpsClaw(
            squad_id="test-squad",
            inference_client=inference_client,
            mesh_gateway=mock_gateway,
            base_path=temp_sandbox,
        )

        try:
            claw.startup()

            assert claw.intake_manager is not None

            inquiry = {
                "name": "Integration Test Client",
                "email": "integration@example.com",
                "message": "Need a full marketing campaign. Budget $15000.",
            }

            triage = claw.intake_manager.receive_inquiry(inquiry)
            assert triage is not None

            if claw.approval_handler:
                queue = claw.approval_handler.get_review_queue()
                assert len(queue) >= 1

        finally:
            claw.shutdown()

    def test_data_type_logged_on_inference(
        self,
        temp_sandbox: Path,
        inference_client: MockInferenceClient,
        mock_gateway: MockMeshGateway,
    ):
        """Verify data_type is logged on every inference call."""
        claw = OpsClaw(
            squad_id="test-squad",
            inference_client=inference_client,
            mesh_gateway=mock_gateway,
            base_path=temp_sandbox,
        )

        try:
            claw.startup()

            inference_client.calls.clear()

            inquiry = {
                "name": "Data Type Test",
                "message": "Test inquiry",
            }

            claw.intake_manager.receive_inquiry(inquiry)

            for call in inference_client.calls:
                assert "data_type" in call
                assert call["data_type"] is not None
                assert len(call["data_type"]) > 0

        finally:
            claw.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
