# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Payment Monitor."""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    PaymentEventsLog,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.payment_monitor import PaymentMonitor, PaymentStatus
from finance.invoice_manager import Invoice


class MockStripeClient:
    """Mock Stripe client."""

    def __init__(self, status: str = "open", amount_paid: float = 0):
        self.status = status
        self.amount_paid = amount_paid
        self.calls: list[dict] = []

    def get_invoice(self, invoice_id: str) -> dict:
        self.calls.append({"method": "get", "invoice_id": invoice_id})
        return {
            "id": invoice_id,
            "status": self.status,
            "amount_paid": int(self.amount_paid * 100),
            "amount_due": int(1000 * 100),
        }

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
        self.sent_messages.append(
            {
                "message_type": message_type,
                "recipient_role": sender_role,
                "payload": payload,
            }
        )
        return True


class MockRevenueTracker:
    """Mock revenue tracker."""

    def __init__(self):
        self.recorded_payments: list = []

    def record_payment(self, invoice):
        self.recorded_payments.append(invoice)


class MockApprovalHandler:
    """Mock approval handler."""

    def __init__(self):
        self.queued_reviews: list = []
        self.queued_holds: list = []

    def queue_overdue_review(self, invoice, days_overdue):
        self.queued_reviews.append((invoice, days_overdue))

    def queue_overdue_hold(self, invoice, days_overdue, overdue_count):
        self.queued_holds.append((invoice, days_overdue, overdue_count))


class TestPaymentMonitor:
    """Tests for PaymentMonitor."""

    @pytest.fixture
    def fs(self, tmp_path: Path):
        fs = FinanceFilesystemInit(tmp_path)
        fs.initialize()
        return fs

    @pytest.fixture
    def operational_log(self, fs: FinanceFilesystemInit):
        return FinanceOperationalLog(fs.BASE / "logs" / "operational.log")

    @pytest.fixture
    def payment_events_log(self, fs: FinanceFilesystemInit):
        return PaymentEventsLog(fs.BASE / "logs" / "payment-events.log")

    @pytest.fixture
    def gateway(self):
        return MockMeshGateway()

    @pytest.fixture
    def dispatcher(self, gateway, operational_log):
        return FinanceSignalDispatcher(gateway, operational_log)

    @pytest.fixture
    def stripe_client(self):
        return MockStripeClient()

    @pytest.fixture
    def revenue_tracker(self):
        return MockRevenueTracker()

    @pytest.fixture
    def approval_handler(self):
        return MockApprovalHandler()

    @pytest.fixture
    def payment_monitor(
        self,
        fs,
        stripe_client,
        dispatcher,
        revenue_tracker,
        approval_handler,
        operational_log,
        payment_events_log,
    ):
        return PaymentMonitor(
            fs=fs,
            stripe_client=stripe_client,
            dispatcher=dispatcher,
            revenue_tracker=revenue_tracker,
            approval_handler=approval_handler,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

    def test_check_invoice_status_returns_payment_status(self, payment_monitor):
        """check_invoice_status returns a PaymentStatus."""
        invoice = Invoice(
            invoice_id="inv-123",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=5)).strftime(
                "%Y-%m-%d"
            ),
            stripe_invoice_id="st_123",
        )

        status = payment_monitor.check_invoice_status(invoice)

        assert isinstance(status, PaymentStatus)
        assert status.invoice_id == "inv-123"

    def test_check_invoice_status_calls_stripe(self, payment_monitor, stripe_client):
        """check_invoice_status calls Stripe API."""
        invoice = Invoice(
            invoice_id="inv-stripe",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
            stripe_invoice_id="st_stripe_test",
        )

        payment_monitor.check_invoice_status(invoice)

        assert len(stripe_client.calls) == 1
        assert stripe_client.calls[0]["method"] == "get"

    def test_process_payment_received_moves_to_paid(self, payment_monitor, fs):
        """Payment received moves invoice to paid/."""
        sent_dir = fs.BASE / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)

        invoice = Invoice(
            invoice_id="inv-paid",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
            status="sent",
        )

        sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
        sent_path.write_text(json.dumps(invoice.to_dict()))

        payment_monitor.process_payment_received(invoice)

        paid_path = fs.get_invoice_path("paid", invoice.invoice_id)
        assert paid_path.exists()
        assert not sent_path.exists()

    def test_process_payment_received_calls_revenue_tracker(
        self, payment_monitor, revenue_tracker
    ):
        """Payment received calls revenue_tracker.record_payment."""
        invoice = Invoice(
            invoice_id="inv-rev",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        payment_monitor.process_payment_received(invoice)

        assert len(revenue_tracker.recorded_payments) == 1
        assert revenue_tracker.recorded_payments[0].invoice_id == "inv-rev"

    def test_process_payment_overdue_moves_to_overdue(self, payment_monitor, fs):
        """Overdue payment moves invoice to overdue/."""
        sent_dir = fs.BASE / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)

        invoice = Invoice(
            invoice_id="inv-overdue",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=5)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
        sent_path.write_text(json.dumps(invoice.to_dict()))

        payment_monitor.process_payment_overdue(invoice)

        overdue_path = fs.get_invoice_path("overdue", invoice.invoice_id)
        assert overdue_path.exists()

    def test_first_overdue_queues_review(
        self, payment_monitor, approval_handler, payment_events_log
    ):
        """First overdue queues REVIEW in War Room."""
        invoice = Invoice(
            invoice_id="inv-first-overdue",
            project_id="proj-1",
            client_id="client-first",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        payment_monitor.process_payment_overdue(invoice)

        assert len(approval_handler.queued_reviews) == 1

    def test_repeat_overdue_queues_hold(
        self, payment_monitor, approval_handler, payment_events_log
    ):
        """Repeat overdue (2+) queues HOLD in War Room."""
        client_id = "client-repeat"

        for i in range(2):
            from finance.finance_init import PaymentEvent

            event = PaymentEvent(
                timestamp=f"2026-03-{1 + i:02d}T10:00:00",
                event_type="payment_overdue",
                invoice_id=f"inv-old-{i}",
                client_id=client_id,
                amount=1000,
                details={},
            )
            payment_events_log.append(event)

        invoice = Invoice(
            invoice_id="inv-repeat-overdue",
            project_id="proj-1",
            client_id=client_id,
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        payment_monitor.process_payment_overdue(invoice)

        assert len(approval_handler.queued_holds) == 1

    def test_check_and_flag_overdue_returns_overdue_invoices(self, payment_monitor, fs):
        """check_and_flag_overdue returns list of overdue invoices."""
        sent_dir = fs.BASE / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)

        invoice = Invoice(
            invoice_id="inv-flag-overdue",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=5)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
        sent_path.write_text(json.dumps(invoice.to_dict()))

        overdue = payment_monitor.check_and_flag_overdue()

        assert len(overdue) >= 1
        overdue_ids = [i.invoice_id for i in overdue]
        assert "inv-flag-overdue" in overdue_ids

    def test_stripe_call_logged_to_payment_events(
        self, payment_monitor, payment_events_log
    ):
        """Stripe API call is logged to payment-events.log."""
        invoice = Invoice(
            invoice_id="inv-logged",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
            stripe_invoice_id="st_logged",
        )

        payment_monitor.check_invoice_status(invoice)

        events = payment_events_log.read_recent(days=1)
        status_checks = [e for e in events if e.event_type == "status_check"]
        assert len(status_checks) >= 1

    def test_check_all_sent_invoices_returns_statuses(self, payment_monitor, fs):
        """check_all_sent_invoices returns list of statuses."""
        sent_dir = fs.BASE / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            invoice = Invoice(
                invoice_id=f"inv-check-{i}",
                project_id=f"proj-{i}",
                client_id=f"client-{i}",
                line_items=[],
                subtotal=1000,
                total=1000,
                payment_risk_level="low",
                due_date="2026-03-01",
                stripe_invoice_id=f"st_{i}",
            )
            sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
            sent_path.write_text(json.dumps(invoice.to_dict()))

        statuses = payment_monitor.check_all_sent_invoices()

        assert len(statuses) == 3

    def test_days_overdue_calculation(self, payment_monitor):
        """days_overdue is calculated correctly."""
        due_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
            "%Y-%m-%d"
        )

        invoice = Invoice(
            invoice_id="inv-days",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=due_date,
            stripe_invoice_id="st_days",
        )

        status = payment_monitor.check_invoice_status(invoice)

        assert status.days_overdue >= 10

    def test_no_stripe_invoice_id_returns_unknown_status(self, payment_monitor):
        """Missing stripe_invoice_id returns unknown status."""
        invoice = Invoice(
            invoice_id="inv-no-stripe",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
            stripe_invoice_id="",
        )

        status = payment_monitor.check_invoice_status(invoice)

        assert status.status == "unknown"

    def test_payment_overdue_sends_signal(self, payment_monitor, gateway):
        """Overdue sends payment_overdue signal."""
        invoice = Invoice(
            invoice_id="inv-signal",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=5)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        payment_monitor.process_payment_overdue(invoice)

        assert len(gateway.sent_messages) >= 1
        overdue_msgs = [
            m for m in gateway.sent_messages if m["message_type"] == "payment_overdue"
        ]
        assert len(overdue_msgs) >= 1
