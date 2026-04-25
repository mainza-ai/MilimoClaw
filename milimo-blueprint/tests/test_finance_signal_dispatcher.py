# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Signal Dispatcher."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import FinanceOperationalLog
from finance.signal_dispatcher import FinanceSignalDispatcher


class MockMeshGateway:
    """Mock mesh gateway for testing."""

    def __init__(self):
        self.sent_messages: list[dict] = []
        self.should_fail = False

    def send(
        self,
        message_type: str,
        recipient_role: str,
        sender_role: str,
        payload: dict,
        message_id: str,
        timestamp: str,
    ) -> bool:
        if self.should_fail:
            raise RuntimeError("Gateway error")
        self.sent_messages.append(
            {
                "message_type": message_type,
                "recipient_role": recipient_role,
                "sender_role": sender_role,
                "payload": payload,
                "message_id": message_id,
                "timestamp": timestamp,
            }
        )
        return True


class TestFinanceSignalDispatcher:
    """Tests for FinanceSignalDispatcher."""

    @pytest.fixture
    def gateway(self):
        return MockMeshGateway()

    @pytest.fixture
    def log_path(self, tmp_path: Path):
        return tmp_path / "logs" / "operational.log"

    @pytest.fixture
    def operational_log(self, log_path: Path):
        return FinanceOperationalLog(log_path)

    @pytest.fixture
    def dispatcher(self, gateway, operational_log):
        return FinanceSignalDispatcher(gateway, operational_log)

    def test_send_pricing_response_sends_correct_message(self, dispatcher, gateway):
        """Pricing response has correct message_type and recipient."""
        dispatcher.send_pricing_response(
            project_id="proj-123",
            floor_price=1000.0,
            ceiling_price=1500.0,
            scope_notes="Standard scope",
            data_quality="complete",
        )

        assert len(gateway.sent_messages) == 1
        msg = gateway.sent_messages[0]
        assert msg["message_type"] == "pricing_response"
        assert msg["recipient_role"] == "ops"
        assert msg["sender_role"] == "finance"
        assert msg["payload"]["project_id"] == "proj-123"
        assert msg["payload"]["floor_price"] == 1000.0
        assert msg["payload"]["ceiling_price"] == 1500.0

    def test_send_pricing_response_data_quality_estimated(self, dispatcher, gateway):
        """Pricing response includes data_quality field."""
        dispatcher.send_pricing_response(
            project_id="proj-123",
            floor_price=1000.0,
            ceiling_price=1500.0,
            scope_notes="Estimate based on limited data",
            data_quality="estimated",
        )

        msg = gateway.sent_messages[0]
        assert msg["payload"]["data_quality"] == "estimated"

    def test_send_invoice_ready_sends_correct_message(self, dispatcher, gateway):
        """Invoice ready has correct message_type and recipient."""
        dispatcher.send_invoice_ready(
            project_id="proj-123",
            client_id="client-456",
            amount=2500.0,
            invoice_id="inv-789",
            due_date="2026-04-05",
        )

        assert len(gateway.sent_messages) == 1
        msg = gateway.sent_messages[0]
        assert msg["message_type"] == "invoice_ready"
        assert msg["recipient_role"] == "ops"
        assert msg["payload"]["project_id"] == "proj-123"
        assert msg["payload"]["client_id"] == "client-456"
        assert msg["payload"]["amount"] == 2500.0
        assert msg["payload"]["invoice_id"] == "inv-789"
        assert msg["payload"]["due_date"] == "2026-04-05"

    def test_send_payment_overdue_sends_correct_message(self, dispatcher, gateway):
        """Payment overdue has correct message_type and recipient."""
        dispatcher.send_payment_overdue(
            client_id="client-456",
            invoice_id="inv-789",
            days_overdue=5,
            amount=2500.0,
            risk_level="medium",
        )

        assert len(gateway.sent_messages) == 1
        msg = gateway.sent_messages[0]
        assert msg["message_type"] == "payment_overdue"
        assert msg["recipient_role"] == "ops"
        assert msg["payload"]["client_id"] == "client-456"
        assert msg["payload"]["days_overdue"] == 5
        assert msg["payload"]["risk_level"] == "medium"

    def test_send_revenue_summary_totals_only(self, dispatcher, gateway):
        """Revenue summary contains NO line items or client names."""
        dispatcher.send_revenue_summary(
            week_total=15000.0,
            week_over_week_pct=12.5,
            invoices_paid=5,
            invoices_pending=3,
        )

        assert len(gateway.sent_messages) == 1
        msg = gateway.sent_messages[0]
        assert msg["message_type"] == "revenue_summary"
        assert msg["recipient_role"] == "analytics"
        assert msg["payload"]["week_total"] == 15000.0
        assert msg["payload"]["week_over_week_pct"] == 12.5
        assert msg["payload"]["invoices_paid"] == 5
        assert msg["payload"]["invoices_pending"] == 3

        assert "line_items" not in msg["payload"]
        assert "client_names" not in msg["payload"]
        assert "invoice_ids" not in msg["payload"]

    def test_dispatch_failure_logged_not_raised(
        self, gateway, operational_log, tmp_path
    ):
        """Dispatch failure is logged but not raised."""
        gateway.should_fail = True
        dispatcher = FinanceSignalDispatcher(gateway, operational_log)

        dispatcher.send_pricing_response(
            project_id="proj-123",
            floor_price=1000.0,
            ceiling_price=1500.0,
            scope_notes="Test",
        )

        assert len(gateway.sent_messages) == 0

        entries = operational_log.read_recent(days=1)
        failed_entries = [e for e in entries if "failed" in e.action_type]
        assert len(failed_entries) >= 1
        assert "pricing_response_send_failed" in failed_entries[0].action_type

    def test_every_send_logged_to_operational_log(
        self, dispatcher, gateway, operational_log
    ):
        """Every successful send is logged to operational.log."""
        dispatcher.send_pricing_response(
            project_id="proj-1",
            floor_price=100.0,
            ceiling_price=150.0,
            scope_notes="Test 1",
        )
        dispatcher.send_invoice_ready(
            project_id="proj-2",
            client_id="client-1",
            amount=500.0,
            invoice_id="inv-1",
            due_date="2026-04-01",
        )
        dispatcher.send_revenue_summary(
            week_total=1000.0,
            week_over_week_pct=5.0,
            invoices_paid=2,
            invoices_pending=1,
        )

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "pricing_response_sent" for e in entries)
        assert any(e.action_type == "invoice_ready_sent" for e in entries)
        assert any(e.action_type == "revenue_summary_sent" for e in entries)

    def test_message_has_uuid_and_timestamp(self, dispatcher, gateway):
        """Messages include valid UUID and ISO timestamp."""
        dispatcher.send_pricing_response(
            project_id="proj-123",
            floor_price=1000.0,
            ceiling_price=1500.0,
            scope_notes="Test",
        )

        msg = gateway.sent_messages[0]

        assert len(msg["message_id"]) == 36
        assert msg["message_id"].count("-") == 4

        try:
            datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid ISO timestamp")

    def test_sender_role_is_finance(self, dispatcher, gateway):
        """All messages have sender_role='finance'."""
        dispatcher.send_pricing_response(
            project_id="proj-1",
            floor_price=100.0,
            ceiling_price=150.0,
            scope_notes="Test",
        )
        dispatcher.send_revenue_summary(
            week_total=1000.0,
            week_over_week_pct=5.0,
            invoices_paid=2,
            invoices_pending=1,
        )

        for msg in gateway.sent_messages:
            assert msg["sender_role"] == "finance"
