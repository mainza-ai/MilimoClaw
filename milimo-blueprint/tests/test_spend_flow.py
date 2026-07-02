# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Stripe Link spend flow robustness and recovery."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.finance.finance_init import FinanceOperationalLog
from orchestrator.finance.spend_handler import SpendApprovalHandler, SpendRequest
from orchestrator.finance.spend_warroom_bridge import SpendWarRoomBridge
from orchestrator.solo_warroom import SoloWarRoom


class TestSpendFlowRobustness:
    """Tests for SpendApprovalHandler and SpendWarRoomBridge recovery & parsing."""

    @pytest.fixture
    def log_dir(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @pytest.fixture
    def operational_log(self, log_dir: Path):
        return FinanceOperationalLog(log_dir / "operational.log")

    @pytest.fixture
    def spend_handler(self, operational_log: FinanceOperationalLog, log_dir: Path):
        return SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=log_dir / "decisions.log",
            spend_log_path=log_dir / "agent-spend.log",
            test_mode=True,
        )

    def test_json_array_parsing_and_status_updates(
        self, spend_handler: SpendApprovalHandler
    ):
        """Verify that handle_hold_release parses link-cli list/array output correctly."""
        request = SpendRequest(
            spend_id="spend-001",
            claw="build-claw",
            merchant_name="Vercel",
            merchant_url="https://vercel.com",
            amount_cents=1500,
            currency="USD",
            justification="Test justification for Vercel provisioning",
            payment_method_id="pm_123",
        )

        spend_handler.queue_spend_review(request)
        spend_handler.handle_review_approve("spend-review-spend-001")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps([{"id": "lsrq_array_parsed_999"}])
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            released_req = spend_handler.handle_hold_release("spend-hold-spend-001")
            assert mock_run.called
            assert released_req.status == "released"
            assert released_req.link_spend_request_id == "lsrq_array_parsed_999"

    def test_state_recovery_across_restarts(
        self, operational_log: FinanceOperationalLog, log_dir: Path
    ):
        """Verify that handler can reconstruct requests and replay logs after a restart."""
        # 1. Queue a request in a handler session
        handler1 = SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=log_dir / "decisions.log",
            spend_log_path=log_dir / "agent-spend.log",
            test_mode=True,
        )
        request = SpendRequest(
            spend_id="spend-restart-002",
            claw="content-claw",
            merchant_name="OpenAI",
            merchant_url="https://openai.com",
            amount_cents=5000,
            currency="USD",
            justification="API credits bundle purchase for content generation",
        )
        handler1.queue_spend_review(request)
        handler1.handle_review_approve("spend-review-spend-restart-002")

        # 2. Simulate daemon restart -> Create a new handler instance with empty memory
        handler2 = SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=log_dir / "decisions.log",
            spend_log_path=log_dir / "agent-spend.log",
            test_mode=True,
        )
        assert "spend-restart-002" not in handler2._requests

        # 3. Trigger approve or hold release -> Should dynamically recover request
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps([{"id": "lsrq_recovered_888"}])
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc):
            recovered_req = handler2.handle_hold_release("spend-hold-spend-restart-002")
            assert recovered_req.status == "released"
            assert recovered_req.link_spend_request_id == "lsrq_recovered_888"
            assert recovered_req.merchant_name == "OpenAI"
            assert recovered_req.amount_cents == 5000

    def test_warroom_bridge_fallback_recovery(
        self, spend_handler: SpendApprovalHandler, log_dir: Path
    ):
        """Verify SpendWarRoomBridge recovers action id mappings from SoloWarRoom queue."""
        config = {
            "war_room": {"operator": "system", "mode": "solo"},
            "operator_policy": {"approval_modes": {}},
        }
        solo_warroom = SoloWarRoom(config=config, log_dir=log_dir)
        bridge = SpendWarRoomBridge(
            spend_handler=spend_handler, solo_warroom=solo_warroom
        )

        request = SpendRequest(
            spend_id="spend-bridge-003",
            claw="ops-claw",
            merchant_name="Slack",
            merchant_url="https://slack.com",
            amount_cents=3000,
            currency="USD",
            justification="Upgrade test workspace to pro plan for integration logs",
        )

        # Submit request -> creates action in war room
        wr_action_id = bridge.submit_spend_request(request)
        assert wr_action_id is not None

        # Clear memory mappings in the bridge (simulating restart)
        bridge._review_actions.clear()
        assert wr_action_id not in bridge._review_actions

        # Approve review -> should recover via SoloWarRoom action queue payload
        bridge.approve_review(wr_action_id)

        # Check that it successfully moved to hold and queued spend_hold action
        pending_actions = solo_warroom._queue
        hold_action = next(
            (a for a in pending_actions if a.action_type == "spend_hold"), None
        )
        assert hold_action is not None
        assert hold_action.payload["spend_id"] == "spend-bridge-003"

        # Clear hold actions mapping (simulating restart again)
        bridge._hold_actions.clear()
        assert hold_action.id not in bridge._hold_actions

        # Release hold -> should recover via payload fallback
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps([{"id": "lsrq_bridge_recovered_777"}])
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc):
            _, released_req = bridge.release_hold(hold_action.id)
            assert released_req is not None
            assert released_req.status == "released"
            assert released_req.link_spend_request_id == "lsrq_bridge_recovered_777"
