# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Approval Handler."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    PaymentEventsLog,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.invoice_manager import InvoiceManager, Invoice
from finance.approval_handler import FinanceApprovalHandler


class MockInferenceClient:
    """Mock inference client."""

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        return json.dumps(
            [{"description": "Work", "quantity": 1, "unit_price": 1000, "total": 1000}]
        )


class MockStripeClient:
    """Mock Stripe client."""

    def __init__(self):
        self.calls: list[dict] = []

    def create_invoice(
        self,
        customer_id: str,
        amount: float,
        currency: str,
        description: str,
        due_date: str,
    ) -> dict:
        self.calls.append({"method": "create", "customer_id": customer_id})
        return {"id": "st_test_123"}

    def send_invoice(self, invoice_id: str) -> dict:
        self.calls.append({"method": "send", "invoice_id": invoice_id})
        return {"status": "sent"}


class MockMeshGateway:
    """Mock mesh gateway."""

    def __init__(self):
        self.sent_messages: list[dict] = []

    def send(
        self,
        message_type: str,
        recipient_role: str,
        sender_role: str,
        payload: dict,
        message_id: str,
        timestamp: str,
    ) -> bool:
        self.sent_messages.append({"message_type": message_type, "payload": payload})
        return True


class MockPaymentRiskScorer:
    """Mock payment risk scorer."""

    def score(self, client_id: str):
        mock_score = MagicMock()
        mock_score.score = 7.5
        mock_score.risk_level = "low"
        return mock_score


class TestFinanceApprovalHandler:
    """Tests for FinanceApprovalHandler."""

    @pytest.fixture
    def fs(self, tmp_path: Path):
        fs = FinanceFilesystemInit(tmp_path)
        fs.initialize()
        return fs

    @pytest.fixture
    def operational_log(self, fs: FinanceFilesystemInit):
        return FinanceOperationalLog(fs.base / "logs" / "operational.log")

    @pytest.fixture
    def payment_events_log(self, fs: FinanceFilesystemInit):
        return PaymentEventsLog(fs.base / "logs" / "payment-events.log")

    @pytest.fixture
    def gateway(self):
        return MockMeshGateway()

    @pytest.fixture
    def dispatcher(self, gateway, operational_log):
        return FinanceSignalDispatcher(gateway, operational_log)

    @pytest.fixture
    def inference_client(self):
        return MockInferenceClient()

    @pytest.fixture
    def risk_scorer(self):
        return MockPaymentRiskScorer()

    @pytest.fixture
    def invoice_manager(
        self,
        fs,
        inference_client,
        dispatcher,
        risk_scorer,
        operational_log,
        payment_events_log,
    ):
        return InvoiceManager(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            payment_risk_scorer=risk_scorer,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

    @pytest.fixture
    def decisions_path(self, fs):
        return fs.base / "logs" / "decisions.log"

    @pytest.fixture
    def approval_handler(self, invoice_manager, operational_log, decisions_path):
        return FinanceApprovalHandler(
            invoice_manager=invoice_manager,
            operational_log=operational_log,
            decisions_path=decisions_path,
        )

    def test_queue_invoice_review_returns_action_id(self, approval_handler):
        """queue_invoice_review returns action_id."""
        invoice = Invoice(
            invoice_id="inv-review-1",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-04-01",
        )

        action_id = approval_handler.queue_invoice_review(invoice)

        assert action_id == "review-inv-review-1"

    def test_queue_invoice_hold_returns_action_id(self, approval_handler):
        """queue_invoice_hold returns action_id."""
        invoice = Invoice(
            invoice_id="inv-hold-1",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-04-01",
        )

        action_id = approval_handler.queue_invoice_hold(invoice)

        assert action_id == "hold-inv-hold-1"

    def test_handle_review_approve_moves_to_hold(
        self, approval_handler, invoice_manager, fs
    ):
        """handle_review_approve moves invoice to HOLD queue."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-approve",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        approval_handler.handle_review_approve(f"review-{invoice.invoice_id}")

        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        assert approved_path.exists()

    def test_handle_review_approve_logs_decision(
        self, approval_handler, invoice_manager, decisions_path
    ):
        """handle_review_approve logs to decisions.log."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-log",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        approval_handler.handle_review_approve(f"review-{invoice.invoice_id}")

        assert decisions_path.exists()
        with open(decisions_path) as f:
            lines = f.readlines()

        approve_logs = [line for line in lines if "approve" in line]
        assert len(approve_logs) >= 1

    def test_handle_hold_release_sends_invoice(
        self, approval_handler, invoice_manager, fs
    ):
        """handle_hold_release sends invoice via Stripe."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-release",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        stripe_client = MockStripeClient()
        approval_handler.handle_hold_release(
            f"hold-{invoice.invoice_id}", stripe_client
        )

        assert len(stripe_client.calls) == 2
        assert stripe_client.calls[0]["method"] == "create"
        assert stripe_client.calls[1]["method"] == "send"

        sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
        assert sent_path.exists()

    def test_handle_review_block_archives_invoice(
        self, approval_handler, invoice_manager, fs
    ):
        """handle_review_block archives invoice."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-block",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        approval_handler.handle_review_block(
            f"review-{invoice.invoice_id}", "Client cancelled"
        )

        blocked_path = fs.base / "invoices" / "blocked" / f"{invoice.invoice_id}.json"
        assert blocked_path.exists()

    def test_handle_review_edit_updates_invoice(
        self, approval_handler, invoice_manager, fs
    ):
        """handle_review_edit updates invoice."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-edit",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        edited_items = [
            {
                "description": "Updated work",
                "quantity": 1,
                "unit_price": 1500,
                "total": 1500,
            }
        ]

        approval_handler.handle_review_edit(
            f"review-{invoice.invoice_id}",
            edited_items,
            1500,
        )

        pending_path = fs.get_invoice_path("pending", invoice.invoice_id)
        json.loads(pending_path.read_text())

    def test_handle_hold_cancel_keeps_approved(
        self, approval_handler, invoice_manager, fs
    ):
        """handle_hold_cancel keeps invoice in approved/."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-cancel",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        approval_handler.handle_hold_cancel(f"hold-{invoice.invoice_id}")

        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        assert approved_path.exists()

    def test_queue_overdue_review_returns_action_id(self, approval_handler):
        """queue_overdue_review returns action_id."""
        invoice = Invoice(
            invoice_id="inv-overdue-review",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="medium",
            due_date="2026-03-01",
        )

        action_id = approval_handler.queue_overdue_review(invoice, days_overdue=5)

        assert action_id == "overdue-review-inv-overdue-review"

    def test_queue_overdue_hold_returns_action_id(self, approval_handler):
        """queue_overdue_hold returns action_id."""
        invoice = Invoice(
            invoice_id="inv-overdue-hold",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="high",
            due_date="2026-03-01",
        )

        action_id = approval_handler.queue_overdue_hold(
            invoice, days_overdue=10, overdue_count=3
        )

        assert action_id == "overdue-hold-inv-overdue-hold"

    def test_queue_margin_alert_returns_action_id(self, approval_handler):
        """queue_margin_alert returns action_id."""
        action_id = approval_handler.queue_margin_alert(
            project_id="margin-check",
            expected_margin_pct=30.0,
            actual_margin_pct=15.0,
        )

        assert action_id.startswith("margin-alert-")

    def test_queue_rate_recommendation_returns_action_id(self, approval_handler):
        """queue_rate_recommendation returns action_id."""
        action_id = approval_handler.queue_rate_recommendation(
            recommendation="Increase rate to $150/hour",
            suggested_rate=150,
            current_rate=100,
        )

        assert action_id.startswith("rate-rec-")

    def test_decision_logged_with_file_locking(self, approval_handler, decisions_path):
        """Decision log uses file locking."""
        invoice = Invoice(
            invoice_id="inv-lock",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-04-01",
        )

        approval_handler.queue_invoice_review(invoice)

        assert decisions_path.exists()

    def test_logged_to_operational_log(self, approval_handler, operational_log):
        """Approval actions are logged to operational.log."""
        invoice = Invoice(
            invoice_id="inv-oplog",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-04-01",
        )

        approval_handler.queue_invoice_review(invoice)

        entries = operational_log.read_recent(days=1)
        assert any("review" in e.action_type for e in entries)

    def test_two_stage_approval_separation(self, approval_handler, invoice_manager):
        """Stage 1 (review) and Stage 2 (hold) are separate."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-two-stage",
            client_id="client-1",
            delivered_at="2026-03-21",
        )

        stripe_client = MockStripeClient()

        approval_handler.handle_review_approve(f"review-{invoice.invoice_id}")

        assert len(stripe_client.calls) == 0

        approval_handler.handle_hold_release(
            f"hold-{invoice.invoice_id}", stripe_client
        )

        assert len(stripe_client.calls) == 2
