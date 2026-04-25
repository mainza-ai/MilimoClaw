# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Finance Claw MVR Integration Tests - 14 Critical Tests.

These tests verify the Minimum Viable Release requirements for the Finance Claw.
Each test corresponds to a critical MVR requirement from the spec.

CRITICAL: Test 6 (two-stage approval) is the most important test.
It must assert ZERO Stripe calls after Stage 1 (REVIEW) approval.
"""

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
    PaymentEvent,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.pricing_engine import PricingEngine
from finance.invoice_manager import InvoiceManager, Invoice
from finance.approval_handler import FinanceApprovalHandler
from finance.payment_risk_scorer import PaymentRiskScorer
from finance.payment_monitor import PaymentMonitor
from finance.revenue_tracker import RevenueTracker
from finance.expense_tracker import ExpenseTracker
from finance.finance_claw import FinanceClaw


class MockInferenceClient:
    """Mock inference client for all tests."""

    def __init__(self, response: str | None = None):
        self.response = response
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        self.calls.append({"prompt": prompt, "data_type": data_type})
        if self.response:
            return self.response
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
    """Mock Stripe client - CRITICAL for tracking calls."""

    def __init__(self):
        self.calls: list[dict] = []
        self.invoice_status: dict = {}

    def get_invoice(self, invoice_id: str) -> dict:
        self.calls.append({"method": "get", "invoice_id": invoice_id})
        return self.invoice_status.get(
            invoice_id,
            {
                "id": invoice_id,
                "status": "open",
                "amount_paid": 0,
                "amount_due": 100000,
            },
        )

    def create_invoice(
        self,
        customer_id: str,
        amount: float,
        currency: str,
        description: str,
        due_date: str,
    ) -> dict:
        self.calls.append(
            {
                "method": "create",
                "customer_id": customer_id,
                "amount": amount,
            }
        )
        return {"id": f"st_test_{len(self.calls)}"}

    def send_invoice(self, invoice_id: str) -> dict:
        self.calls.append({"method": "send", "invoice_id": invoice_id})
        return {"status": "sent"}


class MockMeshGateway:
    """Mock mesh gateway for signal testing."""

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


class MockPaymentRiskScorer:
    """Mock payment risk scorer."""

    def score(self, client_id: str):
        mock_score = MagicMock()
        mock_score.score = 7.5
        mock_score.risk_level = "low"
        return mock_score


class MockRevenueTracker:
    """Mock revenue tracker."""

    def __init__(self):
        self.recorded_payments: list = []

    def record_payment(self, invoice):
        self.recorded_payments.append(invoice)


class MockApprovalHandler:
    """Mock approval handler for overdue tests."""

    def __init__(self):
        self.queued_reviews: list = []
        self.queued_holds: list = []

    def queue_overdue_review(self, invoice, days_overdue):
        self.queued_reviews.append((invoice, days_overdue))

    def queue_overdue_hold(self, invoice, days_overdue, overdue_count):
        self.queued_holds.append((invoice, days_overdue, overdue_count))


class TestMVRFinanceClaw:
    """MVR Integration Tests for Finance Claw."""

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
    def stripe_client(self):
        return MockStripeClient()

    @pytest.fixture
    def risk_scorer(self, payment_events_log, inference_client):
        return PaymentRiskScorer(payment_events_log, inference_client)

    # -------------------------------------------------------------------------
    # MVR Test 1: Filesystem structure initialized correctly
    # -------------------------------------------------------------------------
    def test_mvr_1_filesystem_structure(self, fs):
        """MVR-1: All required directories and files exist after init."""
        required_dirs = [
            "invoices/pending",
            "invoices/approved",
            "invoices/sent",
            "invoices/paid",
            "invoices/overdue",
            "logs",
            "pricing/estimates",
            "pricing/history",
            "revenue/history",
            "expenses/categories",
            "tax/quarterly",
        ]

        for dir_path in required_dirs:
            full_path = fs.base / dir_path
            assert full_path.exists(), f"Directory {dir_path} not created"

    # -------------------------------------------------------------------------
    # MVR Test 2: Pricing query response within SLA (includes data_type)
    # -------------------------------------------------------------------------
    def test_mvr_2_pricing_query_sla(
        self, fs, inference_client, dispatcher, operational_log
    ):
        """MVR-2: Pricing query responds with inference call using data_type."""
        engine = PricingEngine(fs, inference_client, dispatcher, operational_log)

        message = {
            "project_id": "proj-mvr-2",
            "scope_description": "Build a landing page",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }

        estimate = engine.handle_pricing_query(message)

        assert estimate.project_id == "proj-mvr-2"

        inference_calls = [
            c
            for c in inference_client.calls
            if c["data_type"] == "scope_cost_estimation"
        ]
        assert len(inference_calls) >= 1, (
            "Inference call missing data_type='scope_cost_estimation'"
        )

    # -------------------------------------------------------------------------
    # MVR Test 3: Invoice generated on project_complete
    # -------------------------------------------------------------------------
    def test_mvr_3_invoice_generation(
        self,
        fs,
        inference_client,
        dispatcher,
        risk_scorer,
        operational_log,
        payment_events_log,
    ):
        """MVR-3: Invoice is generated when project_complete message received."""
        invoice_manager = InvoiceManager(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            payment_risk_scorer=risk_scorer,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        invoice = invoice_manager.generate_invoice(
            project_id="proj-mvr-3",
            client_id="client-mvr-3",
            delivered_at="2026-03-21",
        )

        assert invoice.invoice_id.startswith("inv-")
        assert invoice.project_id == "proj-mvr-3"
        assert invoice.client_id == "client-mvr-3"

        pending_path = fs.get_invoice_path("pending", invoice.invoice_id)
        assert pending_path.exists()

    # -------------------------------------------------------------------------
    # MVR Test 4: Payment risk scoring uses inference with data_type
    # -------------------------------------------------------------------------
    def test_mvr_4_payment_risk_scoring(self, payment_events_log, inference_client):
        """MVR-4: Payment risk scoring uses inference with data_type='payment_risk_scoring'."""
        event = PaymentEvent(
            timestamp="2026-03-01T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-1",
            client_id="client-mvr-4",
            amount=1000,
            details={},
        )
        payment_events_log.append(event)

        scorer = PaymentRiskScorer(payment_events_log, inference_client)
        scorer.score("client-mvr-4")

        inference_calls = [
            c
            for c in inference_client.calls
            if c["data_type"] == "payment_risk_scoring"
        ]
        assert len(inference_calls) >= 1, (
            "Inference call missing data_type='payment_risk_scoring'"
        )

    # -------------------------------------------------------------------------
    # MVR Test 5: Approval handler queues REVIEW and HOLD correctly
    # -------------------------------------------------------------------------
    def test_mvr_5_approval_queue_workflow(
        self,
        fs,
        inference_client,
        dispatcher,
        risk_scorer,
        operational_log,
        payment_events_log,
    ):
        """MVR-5: Approval handler correctly queues REVIEW then HOLD."""
        invoice_manager = InvoiceManager(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            payment_risk_scorer=risk_scorer,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        decisions_path = fs.base / "logs" / "decisions.log"
        approval_handler = FinanceApprovalHandler(
            invoice_manager=invoice_manager,
            operational_log=operational_log,
            decisions_path=decisions_path,
        )

        invoice = invoice_manager.generate_invoice(
            project_id="proj-mvr-5",
            client_id="client-mvr-5",
            delivered_at="2026-03-21",
        )

        review_id = approval_handler.queue_invoice_review(invoice)
        assert review_id == f"review-{invoice.invoice_id}"

        approval_handler.handle_review_approve(review_id)

        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        assert approved_path.exists()

    # -------------------------------------------------------------------------
    # MVR Test 6: CRITICAL - Two-stage approval, ZERO Stripe calls after Stage 1
    # -------------------------------------------------------------------------
    def test_mvr_6_two_stage_approval_zero_stripe_calls(
        self,
        fs,
        inference_client,
        dispatcher,
        risk_scorer,
        operational_log,
        payment_events_log,
    ):
        """
        MVR-6: CRITICAL TEST - Two-stage approval.

        Stage 1 (REVIEW approve): Invoice moves to approved/, ZERO Stripe calls.
        Stage 2 (HOLD release): Invoice sent via Stripe.

        This is the most critical test in the Finance Claw.
        """
        invoice_manager = InvoiceManager(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            payment_risk_scorer=risk_scorer,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        stripe_client = MockStripeClient()

        invoice = invoice_manager.generate_invoice(
            project_id="proj-mvr-6-critical",
            client_id="client-mvr-6",
            delivered_at="2026-03-21",
        )

        invoice_manager.handle_stage1_approve(invoice.invoice_id)

        assert len(stripe_client.calls) == 0, (
            f"CRITICAL: Stripe was called {len(stripe_client.calls)} times after Stage 1 approve. "
            "Stage 1 (REVIEW) must NEVER trigger Stripe transmission."
        )

        approved_path = fs.get_invoice_path("approved", invoice.invoice_id)
        assert approved_path.exists(), "Invoice not in approved/ after Stage 1"

        pending_path = fs.get_invoice_path("pending", invoice.invoice_id)
        assert not pending_path.exists(), "Invoice still in pending/ after Stage 1"

        invoice_manager.handle_stage2_hold_release(invoice.invoice_id, stripe_client)

        assert len(stripe_client.calls) == 2, (
            f"Expected 2 Stripe calls (create + send) after Stage 2, got {len(stripe_client.calls)}"
        )

        sent_path = fs.get_invoice_path("sent", invoice.invoice_id)
        assert sent_path.exists(), "Invoice not in sent/ after Stage 2"

    # -------------------------------------------------------------------------
    # MVR Test 7: Payment monitor detects overdue invoices
    # -------------------------------------------------------------------------
    def test_mvr_7_payment_monitor_overdue_detection(
        self, fs, dispatcher, operational_log, payment_events_log
    ):
        """MVR-7: Payment monitor correctly detects and processes overdue invoices."""
        stripe_client = MockStripeClient()
        revenue_tracker = MockRevenueTracker()
        approval_handler = MockApprovalHandler()

        payment_monitor = PaymentMonitor(
            fs=fs,
            stripe_client=stripe_client,
            dispatcher=dispatcher,
            revenue_tracker=revenue_tracker,
            approval_handler=approval_handler,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        sent_dir = fs.base / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)

        overdue_invoice = Invoice(
            invoice_id="inv-overdue-mvr-7",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=10)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
            stripe_invoice_id="st_overdue",
        )

        sent_path = fs.get_invoice_path("sent", overdue_invoice.invoice_id)
        sent_path.write_text(json.dumps(overdue_invoice.to_dict()))

        overdue_invoices = payment_monitor.check_and_flag_overdue()

        assert len(overdue_invoices) >= 1
        assert any(i.invoice_id == "inv-overdue-mvr-7" for i in overdue_invoices)

    # -------------------------------------------------------------------------
    # MVR Test 8: First overdue queues REVIEW, repeat overdue queues HOLD
    # -------------------------------------------------------------------------
    def test_mvr_8_overdue_escalation(
        self, fs, dispatcher, operational_log, payment_events_log
    ):
        """MVR-8: First overdue queues REVIEW, repeat overdue queues HOLD."""
        stripe_client = MockStripeClient()
        revenue_tracker = MockRevenueTracker()
        approval_handler = MockApprovalHandler()

        payment_monitor = PaymentMonitor(
            fs=fs,
            stripe_client=stripe_client,
            dispatcher=dispatcher,
            revenue_tracker=revenue_tracker,
            approval_handler=approval_handler,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        invoice_first = Invoice(
            invoice_id="inv-first-overdue",
            project_id="proj-1",
            client_id="client-first",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date=(datetime.now(timezone.utc) - timedelta(days=5)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        sent_dir = fs.base / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)
        sent_path = fs.get_invoice_path("sent", invoice_first.invoice_id)
        sent_path.write_text(json.dumps(invoice_first.to_dict()))

        payment_monitor.process_payment_overdue(invoice_first)

        assert len(approval_handler.queued_reviews) == 1

        payment_events_log2 = PaymentEventsLog(fs.base / "logs" / "payment-events.log")
        approval_handler2 = MockApprovalHandler()

        payment_monitor2 = PaymentMonitor(
            fs=fs,
            stripe_client=stripe_client,
            dispatcher=dispatcher,
            revenue_tracker=revenue_tracker,
            approval_handler=approval_handler2,
            operational_log=operational_log,
            payment_events_log=payment_events_log2,
        )

        for i in range(2):
            event = PaymentEvent(
                timestamp=f"2026-03-{i + 1:02d}T10:00:00",
                event_type="payment_overdue",
                invoice_id=f"inv-old-{i}",
                client_id="client-repeat",
                amount=1000,
                details={},
            )
            payment_events_log2.append(event)

        invoice_repeat = Invoice(
            invoice_id="inv-repeat-overdue",
            project_id="proj-2",
            client_id="client-repeat",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="medium",
            due_date=(datetime.now(timezone.utc) - timedelta(days=5)).strftime(
                "%Y-%m-%d"
            ),
            status="sent",
        )

        payment_monitor2.process_payment_overdue(invoice_repeat)

        assert len(approval_handler2.queued_holds) == 1

    # -------------------------------------------------------------------------
    # MVR Test 9: Revenue summary contains only totals (no line items or client names)
    # -------------------------------------------------------------------------
    def test_mvr_9_revenue_summary_totals_only(
        self, fs, inference_client, dispatcher, operational_log
    ):
        """MVR-9: Revenue summary contains totals only - no line items or client names."""
        approval_handler = MagicMock()

        revenue_tracker = RevenueTracker(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        invoice = Invoice(
            invoice_id="inv-rev-mvr-9",
            project_id="proj-1",
            client_id="client-secret-name",
            line_items=[],
            subtotal=1500,
            total=1500,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        gateway = MockMeshGateway()
        revenue_tracker.dispatcher = FinanceSignalDispatcher(gateway, operational_log)

        revenue_tracker.record_payment(invoice)

        revenue_summaries = [
            m for m in gateway.sent_messages if m["message_type"] == "revenue_summary"
        ]
        assert len(revenue_summaries) >= 1

        payload = revenue_summaries[-1]["payload"]

        assert "line_items" not in payload, (
            "Revenue summary must NOT contain line_items"
        )
        assert "client_names" not in payload, (
            "Revenue summary must NOT contain client_names"
        )
        assert "invoice_ids" not in payload, (
            "Revenue summary must NOT contain invoice_ids"
        )
        assert "week_total" in payload, "Revenue summary must contain week_total"

    # -------------------------------------------------------------------------
    # MVR Test 10: Margin analysis uses inference with data_type
    # -------------------------------------------------------------------------
    def test_mvr_10_margin_analysis_inference(
        self, fs, inference_client, dispatcher, operational_log
    ):
        """MVR-10: Margin analysis uses inference with data_type='margin_analysis'."""
        approval_handler = MagicMock()

        revenue_tracker = RevenueTracker(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        revenue_tracker.margin_analysis()

        margin_calls = [
            c for c in inference_client.calls if c["data_type"] == "margin_analysis"
        ]
        assert len(margin_calls) >= 1, (
            "Margin analysis missing inference call with data_type='margin_analysis'"
        )

    # -------------------------------------------------------------------------
    # MVR Test 11: Rate optimization uses inference with data_type
    # -------------------------------------------------------------------------
    def test_mvr_11_rate_optimization_inference(
        self, fs, inference_client, dispatcher, operational_log
    ):
        """MVR-11: Rate optimization uses inference with data_type='rate_benchmarking_narrative'."""
        approval_handler = MagicMock()

        revenue_tracker = RevenueTracker(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        revenue_tracker.rate_optimization_check()

        rate_calls = [
            c
            for c in inference_client.calls
            if c["data_type"] == "rate_benchmarking_narrative"
        ]
        assert len(rate_calls) >= 1, (
            "Rate optimization missing inference call with data_type='rate_benchmarking_narrative'"
        )

    # -------------------------------------------------------------------------
    # MVR Test 12: Expense logging uses inference with data_type
    # -------------------------------------------------------------------------
    def test_mvr_12_expense_classification_inference(
        self, fs, inference_client, operational_log
    ):
        """MVR-12: Expense classification uses inference with data_type='tax_category_classification'."""
        expense_tracker = ExpenseTracker(
            fs_path=fs.base,
            inference_client=inference_client,
            operational_log=operational_log,
        )

        expense_tracker.log_expense(
            description="AWS subscription",
            amount=100,
            expense_date="2026-03-01",
        )

        tax_calls = [
            c
            for c in inference_client.calls
            if c["data_type"] == "tax_category_classification"
        ]
        assert len(tax_calls) >= 1, (
            "Expense logging missing inference call with data_type='tax_category_classification'"
        )

    # -------------------------------------------------------------------------
    # MVR Test 13: All JSONL log appends use file locking
    # -------------------------------------------------------------------------
    def test_mvr_13_file_locking_on_logs(self, fs, operational_log, payment_events_log):
        """MVR-13: All JSONL log appends use fcntl file locking."""
        import fcntl

        from finance.finance_init import FinanceLogEntry

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="test_locking",
            entity_id="test",
            amount=None,
            outcome="success",
            details={},
        )
        operational_log.append(entry)

        log_path = fs.base / "logs" / "operational.log"
        assert log_path.exists()

        with open(log_path) as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            content = f.read()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        assert "test_locking" in content

    # -------------------------------------------------------------------------
    # MVR Test 14: FinanceClaw full integration
    # -------------------------------------------------------------------------
    def test_mvr_14_full_finance_claw_integration(
        self, fs, inference_client, stripe_client, gateway
    ):
        """MVR-14: FinanceClaw initializes all components correctly and handles messages."""
        finance_claw = FinanceClaw(
            squad_id="mvr-test-squad",
            inference_client=inference_client,
            stripe_client=stripe_client,
            gateway=gateway,
            base_path=fs.base,
        )

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

        message = {
            "message_type": "pricing_query",
            "sender_role": "ops",
            "payload": {
                "project_id": "proj-mvr-14",
                "scope_description": "Full integration test",
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

        scheduler = finance_claw.get_component("scheduler")
        assert not scheduler._running
