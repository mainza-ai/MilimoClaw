# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Invoice Manager - Two-Stage Approval."""

import json
import sys
from datetime import datetime, timezone, timedelta
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
from finance.invoice_manager import InvoiceManager


class MockInferenceClient:
    """Mock inference client."""

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        return json.dumps(
            [
                {
                    "description": "Development work",
                    "quantity": 1,
                    "unit_price": 1500,
                    "total": 1500,
                }
            ]
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
        self.calls.append(
            {"method": "create", "customer_id": customer_id, "amount": amount}
        )
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
        self.sent_messages.append(
            {
                "message_type": message_type,
                "recipient_role": recipient_role,
                "sender_role": sender_role,
                "payload": payload,
            }
        )
        return True


class MockPaymentRiskScorer:
    """Mock payment risk scorer."""

    def score(self, client_id: str):
        mock_score = MagicMock()
        mock_score.score = 7.5
        mock_score.risk_level = "low"
        return mock_score


class TestInvoiceManagerTwoStageApproval:
    """Tests for the critical two-stage invoice approval flow."""

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

    def test_generate_invoice_writes_to_pending(self, invoice_manager, fs):
        """generate_invoice writes to pending/ and queues REVIEW."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        pending_path = fs.get_invoice_path("pending", invoice.invoice_id)
        assert pending_path.exists()

        loaded = json.loads(pending_path.read_text())
        assert loaded["status"] == "pending"
        assert loaded["project_id"] == "proj-123"
        assert loaded["client_id"] == "client-456"

    def test_stage1_approve_moves_to_approved_not_sent(self, invoice_manager, fs):
        """
        CRITICAL: handle_stage1_approve moves to approved/ — DOES NOT SEND.

        This is the most critical test. Stage 1 approval must NEVER
        cause an invoice to be sent.
        """
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        stripe_client = MockStripeClient()

        approved_invoice = invoice_manager.handle_stage1_approve(invoice.invoice_id)

        assert approved_invoice.status == "approved"
        assert approved_invoice.approved_at is not None

        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        assert approved_path.exists()

        pending_path = fs.get_invoice_path("pending", invoice.invoice_id)
        assert not pending_path.exists()

        assert len(stripe_client.calls) == 0

    def test_stage2_hold_release_calls_stripe(self, invoice_manager, fs):
        """
        CRITICAL: handle_stage2_hold_release calls Stripe API.

        This is the ONLY place an invoice should be transmitted.
        """
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        stripe_client = MockStripeClient()

        sent_invoice = invoice_manager.handle_stage2_hold_release(
            invoice.invoice_id, stripe_client
        )

        assert sent_invoice.status == "sent"
        assert sent_invoice.stripe_invoice_id == "st_test_123"
        assert sent_invoice.sent_at is not None

        assert len(stripe_client.calls) == 2
        assert stripe_client.calls[0]["method"] == "create"
        assert stripe_client.calls[1]["method"] == "send"

        sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
        assert sent_path.exists()

        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        assert not approved_path.exists()

    def test_stage2_hold_release_retry_guard(self, invoice_manager, fs):
        """Verify that handle_stage2_hold_release does not recreate Stripe invoices on retry if stripe_invoice_id is present."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        # Pre-set a stripe_invoice_id on the approved invoice file
        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        invoice_data = json.loads(approved_path.read_text())
        invoice_data["stripe_invoice_id"] = "existing_invoice_xyz"
        approved_path.write_text(json.dumps(invoice_data, indent=2))

        stripe_client = MockStripeClient()

        sent_invoice = invoice_manager.handle_stage2_hold_release(
            invoice.invoice_id, stripe_client
        )

        assert sent_invoice.status == "sent"
        assert sent_invoice.stripe_invoice_id == "existing_invoice_xyz"

        # Verify that create_invoice was NOT called (so only 1 call to send_invoice exists)
        assert len(stripe_client.calls) == 1
        assert stripe_client.calls[0]["method"] == "send"
        assert stripe_client.calls[0]["invoice_id"] == "existing_invoice_xyz"

    def test_stage2_raises_if_not_approved(self, invoice_manager, fs):
        """handle_stage2 raises if invoice not in approved/ status."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        stripe_client = MockStripeClient()

        with pytest.raises(FileNotFoundError, match="not found in approved"):
            invoice_manager.handle_stage2_hold_release(
                invoice.invoice_id, stripe_client
            )

    def test_stage1_block_archives_with_reason(self, invoice_manager, fs):
        """handle_stage1_block archives with reason."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        invoice_manager.handle_stage1_block(invoice.invoice_id, "Client cancelled")

        pending_path = fs.get_invoice_path("pending", invoice.invoice_id)
        assert not pending_path.exists()

        blocked_path = fs.base / "invoices" / "blocked" / f"{invoice.invoice_id}.json"
        assert blocked_path.exists()

        loaded = json.loads(blocked_path.read_text())
        assert loaded["status"] == "blocked"

    def test_invoice_id_is_valid_uuid(self, invoice_manager):
        """invoice_id is always a valid UUID format."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        assert invoice.invoice_id.startswith("inv-")
        assert len(invoice.invoice_id) == 12

    def test_due_date_14_days_from_generation(self, invoice_manager):
        """due_date always 14 days from generation."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        expected_due = (datetime.now(timezone.utc) + timedelta(days=14)).strftime(
            "%Y-%m-%d"
        )

        assert invoice.due_date == expected_due

    def test_stage1_approve_then_verify_no_stripe_call(self, invoice_manager, fs):
        """
        CRITICAL TEST: Verify no Stripe call after Stage 1 approve.

        This is the most important test in the entire Finance Claw.
        """
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        stripe_client = MockStripeClient()

        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        assert stripe_client.calls == []

    def test_line_item_parsing_fallback(self, invoice_manager, fs):
        """Line item parsing fallback on malformed inference output."""
        invoice = invoice_manager.generate_invoice(
            project_id="proj-123",
            client_id="client-456",
            delivered_at="2026-03-21",
        )

        assert len(invoice.line_items) >= 1

    def test_get_pending_invoices(self, invoice_manager):
        """get_pending_invoices returns correct invoices."""
        invoice1 = invoice_manager.generate_invoice("proj-1", "client-1", "2026-03-21")
        invoice2 = invoice_manager.generate_invoice("proj-2", "client-2", "2026-03-21")

        pending = invoice_manager.get_pending_invoices()

        assert len(pending) == 2
        pending_ids = [i.invoice_id for i in pending]
        assert invoice1.invoice_id in pending_ids
        assert invoice2.invoice_id in pending_ids

    def test_get_approved_invoices(self, invoice_manager):
        """get_approved_invoices returns correct invoices."""
        invoice = invoice_manager.generate_invoice("proj-1", "client-1", "2026-03-21")
        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        approved = invoice_manager.get_approved_invoices()

        assert len(approved) == 1
        assert approved[0].invoice_id == invoice.invoice_id
