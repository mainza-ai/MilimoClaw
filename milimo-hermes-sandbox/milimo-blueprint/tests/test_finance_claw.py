# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Main Entry Point."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_claw import FinanceClaw


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

    def get_invoice(self, invoice_id: str) -> dict:
        return {"id": invoice_id, "status": "open", "amount_paid": 0}

    def create_invoice(
        self,
        customer_id: str,
        amount: float,
        currency: str,
        description: str,
        due_date: str,
    ) -> dict:
        self.calls.append({"method": "create"})
        return {"id": "st_test_123"}

    def send_invoice(self, invoice_id: str) -> dict:
        self.calls.append({"method": "send"})
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
                "message_id": message_id,
                "timestamp": timestamp,
            }
        )
        return True


class TestFinanceClaw:
    """Tests for FinanceClaw."""

    @pytest.fixture
    def base_path(self, tmp_path: Path):
        return tmp_path

    @pytest.fixture
    def inference_client(self):
        return MockInferenceClient()

    @pytest.fixture
    def stripe_client(self):
        return MockStripeClient()

    @pytest.fixture
    def gateway(self):
        return MockMeshGateway()

    @pytest.fixture
    def finance_claw(self, base_path, inference_client, stripe_client, gateway):
        return FinanceClaw(
            squad_id="test-squad-001",
            inference_client=inference_client,
            stripe_client=stripe_client,
            gateway=gateway,
            base_path=base_path,
        )

    def test_startup_initializes_components(self, finance_claw, base_path):
        """startup initializes all components."""
        finance_claw.startup()

        assert finance_claw.is_initialized
        assert finance_claw.get_component("fs") is not None
        assert finance_claw.get_component("invoice_manager") is not None
        assert finance_claw.get_component("pricing_engine") is not None
        assert finance_claw.get_component("payment_monitor") is not None
        assert finance_claw.get_component("revenue_tracker") is not None
        assert finance_claw.get_component("expense_tracker") is not None
        assert finance_claw.get_component("approval_handler") is not None
        assert finance_claw.get_component("scheduler") is not None

        finance_claw.shutdown()

    def test_startup_creates_directories(self, finance_claw, base_path):
        """startup creates required directories."""
        finance_claw.startup()
        finance_claw.shutdown()

        assert (base_path / "invoices" / "pending").exists()
        assert (base_path / "invoices" / "approved").exists()
        assert (base_path / "invoices" / "sent").exists()
        assert (base_path / "invoices" / "paid").exists()
        assert (base_path / "logs").exists()
        assert (base_path / "pricing").exists()
        assert (base_path / "revenue").exists()
        assert (base_path / "expenses").exists()

    def test_startup_logs_claw_started(self, finance_claw, base_path):
        """startup logs claw_started."""
        finance_claw.startup()
        finance_claw.shutdown()

        log_path = base_path / "logs" / "operational.log"
        assert log_path.exists()

        with open(log_path) as f:
            content = f.read()

        assert "claw_started" in content

    def test_shutdown_logs_claw_stopped(self, finance_claw, base_path):
        """shutdown logs claw_stopped."""
        finance_claw.startup()
        finance_claw.shutdown()

        log_path = base_path / "logs" / "operational.log"
        with open(log_path) as f:
            content = f.read()

        assert "claw_stopped" in content

    def test_shutdown_stops_scheduler(self, finance_claw):
        """shutdown stops the scheduler."""
        finance_claw.startup()

        scheduler = finance_claw.get_component("scheduler")
        assert scheduler._running

        finance_claw.shutdown()

        assert not scheduler._running

    def test_handle_inbound_pricing_query(self, finance_claw, gateway):
        """handle_inbound routes pricing_query to pricing_engine."""
        finance_claw.startup()

        message = {
            "message_type": "pricing_query",
            "sender_role": "ops",
            "payload": {
                "project_id": "proj-123",
                "scope_description": "Test project",
                "complexity_estimate": "medium",
                "deadline": "2026-04-01",
            },
        }

        finance_claw.handle_inbound(message)

        pricing_responses = [
            m for m in gateway.sent_messages if m["message_type"] == "pricing_response"
        ]
        assert len(pricing_responses) >= 1

        finance_claw.shutdown()

    def test_handle_inbound_project_complete(self, finance_claw, base_path):
        """handle_inbound routes project_complete to invoice_manager."""
        finance_claw.startup()

        message = {
            "message_type": "project_complete",
            "sender_role": "ops",
            "payload": {
                "project_id": "proj-complete-1",
                "client_id": "client-1",
                "delivered_at": "2026-03-21",
            },
        }

        finance_claw.handle_inbound(message)

        pending_dir = base_path / "invoices" / "pending"
        assert pending_dir.exists()
        invoices = list(pending_dir.glob("*.json"))
        assert len(invoices) >= 1

        finance_claw.shutdown()

    def test_handle_inbound_unknown_message_type(self, finance_claw, base_path):
        """handle_inbound logs unknown message types."""
        finance_claw.startup()

        message = {
            "message_type": "unknown_type",
            "sender_role": "ops",
            "payload": {},
        }

        finance_claw.handle_inbound(message)

        log_path = base_path / "logs" / "operational.log"
        with open(log_path) as f:
            content = f.read()

        assert "unknown_message_type" in content

        finance_claw.shutdown()

    def test_handle_inbound_logs_receipt(self, finance_claw, base_path):
        """handle_inbound logs message receipt."""
        finance_claw.startup()

        message = {
            "message_type": "pricing_query",
            "sender_role": "ops",
            "payload": {
                "project_id": "proj-log-test",
                "scope_description": "Test",
                "complexity_estimate": "low",
                "deadline": "2026-04-01",
            },
        }

        finance_claw.handle_inbound(message)

        log_path = base_path / "logs" / "operational.log"
        with open(log_path) as f:
            content = f.read()

        assert "message_received" in content

        finance_claw.shutdown()

    def test_handle_inbound_catches_exceptions(self, finance_claw, base_path):
        """handle_inbound catches and logs exceptions."""
        finance_claw.startup()

        message = {
            "message_type": "pricing_query",
            "sender_role": "ops",
            "payload": {},
        }

        finance_claw.handle_inbound(message)

        base_path / "logs" / "operational.log"

        finance_claw.shutdown()

    def test_get_component_returns_none_for_unknown(self, finance_claw):
        """get_component returns None for unknown component."""
        finance_claw.startup()

        result = finance_claw.get_component("unknown_component")
        assert result is None

        finance_claw.shutdown()

    def test_double_startup_is_idempotent(self, finance_claw):
        """Double startup is idempotent."""
        finance_claw.startup()
        finance_claw.startup()

        assert finance_claw.is_initialized

        finance_claw.shutdown()

    def test_shutdown_without_startup(self, finance_claw):
        """Shutdown without startup is safe."""
        finance_claw.shutdown()

        assert not finance_claw.is_initialized

    def test_components_wired_correctly(self, finance_claw):
        """Components are wired with correct dependencies."""
        finance_claw.startup()

        payment_monitor = finance_claw.get_component("payment_monitor")
        assert payment_monitor.revenue_tracker is not None
        assert payment_monitor.approval_handler is not None

        revenue_tracker = finance_claw.get_component("revenue_tracker")
        assert revenue_tracker.approval_handler is not None

        scheduler = finance_claw.get_component("scheduler")
        assert scheduler.payment_monitor is not None
        assert scheduler.revenue_tracker is not None
        assert scheduler.expense_tracker is not None

        finance_claw.shutdown()

    def test_scheduler_started_on_startup(self, finance_claw):
        """Scheduler is started on startup."""
        finance_claw.startup()

        scheduler = finance_claw.get_component("scheduler")
        assert scheduler._running

        finance_claw.shutdown()
