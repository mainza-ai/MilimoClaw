# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Stripe Link spend flow robustness and recovery."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.finance.finance_init import FinanceOperationalLog
from orchestrator.finance.spend_handler import SpendApprovalHandler, SpendRequest
from orchestrator.finance.spend_warroom_bridge import SpendWarRoomBridge
from orchestrator.solo_warroom import SoloWarRoom


def mock_subprocess_run(cmd, *args, **kwargs):
    """Unified mock for subprocess.run supporting the non-blocking spend steps."""
    proc = MagicMock()
    proc.returncode = 0
    proc.stderr = ""
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)

    if "create" in cmd_str:
        proc.stdout = json.dumps([{"id": "lsrq_mock_parsed_123"}])
    elif "request-approval" in cmd_str:
        proc.stdout = json.dumps(
            [
                {
                    "id": "lsrq_mock_parsed_123",
                    "approval_link": "https://app.link.com/approve",
                }
            ]
        )
    elif "retrieve" in cmd_str:
        proc.stdout = json.dumps([{"id": "lsrq_mock_parsed_123", "status": "approved"}])
    else:
        proc.stdout = "[]"
    return proc


@patch("subprocess.run", side_effect=mock_subprocess_run)
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
        self, mock_run, spend_handler: SpendApprovalHandler
    ):
        """Verify that handle_hold_release parses link-cli list/array output correctly."""
        request = SpendRequest(
            spend_id="spend-001",
            claw="build-claw",
            merchant_name="Vercel",
            merchant_url="https://vercel.com",
            amount_cents=1500,
            currency="USD",
            justification="Test justification for Vercel provisioning" + "." * 58,
            payment_method_id="pm_123",
        )

        spend_handler.queue_spend_review(request)
        # Test signature robustness with operator keyword argument
        spend_handler.handle_review_approve("spend-review-spend-001", operator="system")

        # Mock stdout returning JSON wrapped in warning / tip text prefix & suffix
        def wrap_json_run(cmd, *args, **kwargs):
            proc = MagicMock()
            proc.returncode = 0
            proc.stderr = ""
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "create" in cmd_str:
                proc.stdout = (
                    "Welcome to Hermes Agent!\n"
                    "Tip: Drop a YAML in ~/.hermes/dashboard-themes/\n"
                    "[\n"
                    "  {\n"
                    '    "id": "lsrq_wrapped_999"\n'
                    "  }\n"
                    "]\n"
                    "Done.\n"
                )
            else:
                proc.stdout = json.dumps(
                    [{"id": "lsrq_wrapped_999", "status": "approved"}]
                )
            return proc

        mock_run.side_effect = wrap_json_run

        released_req = spend_handler.handle_hold_release("spend-hold-spend-001")
        assert released_req.status == "released"
        assert released_req.link_spend_request_id == "lsrq_wrapped_999"

    def test_state_recovery_across_restarts(
        self, mock_run, operational_log: FinanceOperationalLog, log_dir: Path
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
            justification="API credits bundle purchase for content generation"
            + "." * 50,
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
        recovered_req = handler2.handle_hold_release("spend-hold-spend-restart-002")
        assert recovered_req.status == "released"
        assert recovered_req.link_spend_request_id == "lsrq_mock_parsed_123"
        assert recovered_req.merchant_name == "OpenAI"
        assert recovered_req.amount_cents == 5000

    def test_warroom_bridge_fallback_recovery(
        self, mock_run, spend_handler: SpendApprovalHandler, log_dir: Path
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
            justification="Upgrade test workspace to pro plan for integration logs"
            + "." * 45,
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
        _, released_req = bridge.release_hold(hold_action.id)
        assert released_req is not None
        assert released_req.status == "released"
        assert released_req.link_spend_request_id == "lsrq_mock_parsed_123"

    def test_background_polling_and_restart_recovery(
        self, mock_run, operational_log: FinanceOperationalLog, log_dir: Path
    ):
        """Verify that the background polling thread successfully updates state and resumes on restart."""
        # 1. Start a handler and submit request
        handler = SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=log_dir / "decisions.log",
            spend_log_path=log_dir / "agent-spend.log",
            test_mode=True,
        )
        request = SpendRequest(
            spend_id="spend-poll-004",
            claw="build-claw",
            merchant_name="Sentry",
            merchant_url="https://sentry.io",
            amount_cents=2900,
            currency="USD",
            justification="Upgrade team plan for error monitoring integrations"
            + "." * 49,
        )
        handler.queue_spend_review(request)
        handler.handle_review_approve("spend-review-spend-poll-004")

        # 2. Release hold -> Mock subprocess to simulate non-blocking create/approval
        poll_calls = 0

        def custom_run(cmd, *args, **kwargs):
            nonlocal poll_calls
            proc = MagicMock()
            proc.returncode = 0
            proc.stderr = ""
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "create" in cmd_str:
                proc.stdout = json.dumps([{"id": "lsrq_poll_test_456"}])
            elif "request-approval" in cmd_str:
                proc.stdout = json.dumps(
                    [
                        {
                            "id": "lsrq_poll_test_456",
                            "approval_link": "https://app.link.com/approve",
                        }
                    ]
                )
            elif "retrieve" in cmd_str:
                poll_calls += 1
                if poll_calls < 2:
                    proc.stdout = json.dumps(
                        [{"id": "lsrq_poll_test_456", "status": "pending_approval"}]
                    )
                else:
                    proc.stdout = json.dumps(
                        [{"id": "lsrq_poll_test_456", "status": "approved"}]
                    )
            return proc

        mock_run.side_effect = custom_run

        released_req = handler.handle_hold_release("spend-hold-spend-poll-004")
        # Immediately returns non-blocking
        assert released_req.status == "released"
        assert released_req.link_spend_request_id == "lsrq_poll_test_456"

        # Wait for background thread to run retrieve calls
        time.sleep(2.5)
        assert poll_calls >= 2
        assert released_req.status == "released"

        # 3. Simulate restart and verify that it resumes polling if not terminal
        # Let's write a pending release directly to decisions.log to simulate a restart where a released request is recovered
        decisions_file = log_dir / "decisions.log"
        with open(decisions_file, "w", encoding="utf-8") as f:
            # Queued
            f.write(
                json.dumps(
                    {
                        "spend_id": "spend-recover-poll-005",
                        "stage": "review",
                        "action_type": "queued",
                        "timestamp": "2026-07-02T19:00:00Z",
                        "operator": "operator",
                        "details": {
                            "claw": "content-claw",
                            "merchant_name": "Medium",
                            "merchant_url": "https://medium.com",
                            "amount_cents": 500,
                            "currency": "USD",
                            "justification": "Premium account sign up" + "." * 77,
                        },
                    }
                )
                + "\n"
            )
            # Approve
            f.write(
                json.dumps(
                    {
                        "spend_id": "spend-recover-poll-005",
                        "stage": "review",
                        "action_type": "approve",
                        "timestamp": "2026-07-02T19:01:00Z",
                        "operator": "operator",
                        "details": {},
                    }
                )
                + "\n"
            )
            # Release (never finished, so it has release but no terminal state log)
            f.write(
                json.dumps(
                    {
                        "spend_id": "spend-recover-poll-005",
                        "stage": "hold",
                        "action_type": "release",
                        "action_id": "spend-hold-spend-recover-poll-005",
                        "timestamp": "2026-07-02T19:02:00Z",
                        "operator": "operator",
                        "details": {
                            "outcome": "release_initiated",
                            "link_spend_request_id": "lsrq_recovered_poll_789",
                        },
                    }
                )
                + "\n"
            )

        recovered_poll_calls = 0

        def recovery_run(cmd, *args, **kwargs):
            nonlocal recovered_poll_calls
            proc = MagicMock()
            proc.returncode = 0
            proc.stderr = ""
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "retrieve" in cmd_str:
                recovered_poll_calls += 1
                proc.stdout = json.dumps(
                    [{"id": "lsrq_recovered_poll_789", "status": "approved"}]
                )
            return proc

        mock_run.side_effect = recovery_run

        # Creating handler triggers recover_and_resume_polling
        handler_recovery = SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=decisions_file,
            spend_log_path=log_dir / "agent-spend-rec.log",
            test_mode=True,
        )
        # Sleep to let recovery polling thread run
        time.sleep(0.5)
        assert recovered_poll_calls > 0
        req = handler_recovery._get_request("spend-recover-poll-005")
        assert req.status == "released"

    def test_spend_handler_double_release_idempotency(
        self, mock_run, spend_handler, log_dir
    ):
        """Verify that concurrent handle_hold_release calls are serialized/rejected via atomic file locking."""
        from concurrent.futures import ThreadPoolExecutor

        request = SpendRequest(
            spend_id="idemp-test-001",
            claw="build",
            merchant_name="Github",
            merchant_url="github.com",
            amount_cents=1000,
            currency="usd",
            justification="CI running costs" + "." * 84,
        )
        spend_handler._requests[request.spend_id] = request

        results = []
        errors = []

        def run_release():
            try:
                res = spend_handler.handle_hold_release("spend-hold-idemp-test-001")
                results.append(res)
            except Exception as e:
                errors.append(e)

        # Run 5 concurrent threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_release) for _ in range(5)]
            for f in futures:
                f.result()

        # We expect exactly 1 request to have been successfully processed, or others raised "locked" ValueError
        assert (
            len(errors) > 0 or len([r for r in results if r.status == "released"]) == 1
        )
        # The file lock should be cleaned up
        lock_path = spend_handler.spend_log_path.parent / ".spend_lock_idemp-test-001"
        assert not lock_path.exists()

    def test_daily_spend_cap_aggregation(self, mock_run, spend_handler):
        """Verify that daily rolling aggregate check aggregates spends in past 24 hours."""
        import os
        from datetime import datetime, timezone, timedelta

        # Set cap to 10000 cents ($100.00)
        spend_handler.daily_spend_cap_cents = 10000

        # Pre-populate agent-spend.log with some old and some new transactions
        now = datetime.now(timezone.utc)
        recent_ts = (now - timedelta(hours=2)).isoformat()
        old_ts = (now - timedelta(hours=26)).isoformat()

        # Write to log path directly
        os.makedirs(spend_handler.spend_log_path.parent, exist_ok=True)
        with open(spend_handler.spend_log_path, "w") as f:
            # $50.00 within 24 hours
            f.write(
                json.dumps(
                    {
                        "spend_id": "prev-1",
                        "claw": "build",
                        "merchant_name": "Stripe",
                        "amount_cents": 5000,
                        "currency": "usd",
                        "timestamp": recent_ts,
                    }
                )
                + "\n"
            )
            # $40.00 within 24 hours
            f.write(
                json.dumps(
                    {
                        "spend_id": "prev-2",
                        "claw": "build",
                        "merchant_name": "Stripe",
                        "amount_cents": 4000,
                        "currency": "usd",
                        "timestamp": recent_ts,
                    }
                )
                + "\n"
            )
            # $30.00 older than 24 hours (should be ignored)
            f.write(
                json.dumps(
                    {
                        "spend_id": "prev-3",
                        "claw": "build",
                        "merchant_name": "Stripe",
                        "amount_cents": 3000,
                        "currency": "usd",
                        "timestamp": old_ts,
                    }
                )
                + "\n"
            )

        # Total active spend within 24 hours: $90.00
        # A new request of $20.00 should exceed the cap (total would be $110.00)
        req = SpendRequest(
            spend_id="new-tx-001",
            claw="build",
            merchant_name="AWS",
            merchant_url="aws.amazon.com",
            amount_cents=2000,
            currency="usd",
            justification="Hosting" + "." * 93,
        )
        spend_handler._requests[req.spend_id] = req

        # Check queue check (auto_blocked)
        spend_handler.queue_spend_review(req)
        assert req.status == "blocked"

        # If we try to release a request that was somehow queued (e.g. amount is $20.00),
        # but daily cap is already exceeded by other transactions:
        req2 = SpendRequest(
            spend_id="new-tx-002",
            claw="build",
            merchant_name="AWS",
            merchant_url="aws.amazon.com",
            amount_cents=2000,
            currency="usd",
            justification="Hosting" + "." * 93,
        )
        spend_handler._requests[req2.spend_id] = req2
        res = spend_handler.handle_hold_release("spend-hold-new-tx-002")
        assert res.status == "blocked"
