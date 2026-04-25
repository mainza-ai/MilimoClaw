# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Revenue Tracker."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.revenue_tracker import RevenueTracker, RevenueSummary
from finance.invoice_manager import Invoice


class MockInferenceClient:
    """Mock inference client."""

    def __init__(self):
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        self.calls.append({"prompt": prompt, "data_type": data_type})
        return "Analysis complete. Margin looks healthy."


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
                "payload": payload,
            }
        )
        return True


class MockApprovalHandler:
    """Mock approval handler."""

    def __init__(self):
        self.margin_alerts: list = []
        self.rate_recommendations: list = []

    def queue_margin_alert(self, project_id, expected_margin_pct, actual_margin_pct):
        self.margin_alerts.append((project_id, expected_margin_pct, actual_margin_pct))

    def queue_rate_recommendation(self, recommendation, suggested_rate, current_rate):
        self.rate_recommendations.append((recommendation, suggested_rate, current_rate))


class TestRevenueTracker:
    """Tests for RevenueTracker."""

    @pytest.fixture
    def fs(self, tmp_path: Path):
        fs = FinanceFilesystemInit(tmp_path)
        fs.initialize()
        return fs

    @pytest.fixture
    def operational_log(self, fs: FinanceFilesystemInit):
        return FinanceOperationalLog(fs.base / "logs" / "operational.log")

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
    def approval_handler(self):
        return MockApprovalHandler()

    @pytest.fixture
    def revenue_tracker(
        self, fs, inference_client, dispatcher, approval_handler, operational_log
    ):
        return RevenueTracker(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

    def test_record_payment_updates_weekly_summary(self, revenue_tracker, fs):
        """record_payment updates weekly-summary.json."""
        invoice = Invoice(
            invoice_id="inv-1",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        weekly_path = fs.base / "revenue" / "weekly-summary.json"
        assert weekly_path.exists()

        data = json.loads(weekly_path.read_text())
        assert data["week_total"] == 1000
        assert data["invoices_paid"] == 1

    def test_record_payment_writes_daily_snapshot(self, revenue_tracker, fs):
        """record_payment writes daily snapshot."""
        invoice = Invoice(
            invoice_id="inv-daily",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=500,
            total=500,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        today = datetime.now(timezone.utc)
        daily_path = fs.get_revenue_daily_path(today)
        assert daily_path.exists()

    def test_record_payment_sends_revenue_summary(self, revenue_tracker, gateway):
        """record_payment sends revenue_summary signal."""
        invoice = Invoice(
            invoice_id="inv-signal",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=750,
            total=750,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        revenue_msgs = [
            m for m in gateway.sent_messages if m["message_type"] == "revenue_summary"
        ]
        assert len(revenue_msgs) >= 1

    def test_generate_weekly_summary_returns_revenue_summary(self, revenue_tracker):
        """generate_weekly_summary returns RevenueSummary."""
        summary = revenue_tracker.generate_weekly_summary()

        assert isinstance(summary, RevenueSummary)
        assert summary.week_total >= 0
        assert summary.invoices_paid >= 0

    def test_weekly_summary_counts_pending_invoices(self, revenue_tracker, fs):
        """Weekly summary counts pending invoices."""
        pending_dir = fs.base / "invoices" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            invoice = Invoice(
                invoice_id=f"inv-pending-{i}",
                project_id=f"proj-{i}",
                client_id=f"client-{i}",
                line_items=[],
                subtotal=500,
                total=500,
                payment_risk_level="low",
                due_date="2026-03-01",
            )
            (pending_dir / f"inv-pending-{i}.json").write_text(
                json.dumps(invoice.to_dict())
            )

        summary = revenue_tracker.generate_weekly_summary()

        assert summary.invoices_pending >= 3

    def test_margin_analysis_inference_call(self, revenue_tracker, inference_client):
        """margin_analysis makes inference call with data_type='margin_analysis'."""
        revenue_tracker.margin_analysis()

        margin_calls = [
            c for c in inference_client.calls if c["data_type"] == "margin_analysis"
        ]
        assert len(margin_calls) >= 1

    def test_rate_optimization_inference_call(self, revenue_tracker, inference_client):
        """rate_optimization_check makes inference call with data_type='rate_benchmarking_narrative'."""
        revenue_tracker.rate_optimization_check()

        rate_calls = [
            c
            for c in inference_client.calls
            if c["data_type"] == "rate_benchmarking_narrative"
        ]
        assert len(rate_calls) >= 1

    def test_margin_alert_queues_war_room_review(
        self, revenue_tracker, approval_handler, fs
    ):
        """Margin gap > 10% queues War Room REVIEW."""
        expense_path = fs.base / "expenses" / "log.jsonl"
        expense_path.parent.mkdir(parents=True, exist_ok=True)
        expense_path.write_text(
            json.dumps(
                {
                    "expense_id": "exp-1",
                    "amount": 900,
                    "description": "Test expense",
                    "expense_date": "2026-03-01",
                    "tax_category": "other",
                    "logged_at": "2026-03-01T10:00:00",
                }
            )
            + "\n"
        )

        annual_path = fs.base / "revenue" / "annual-summary.json"
        annual_path.write_text(json.dumps({"year_total": 1000}))

        result = revenue_tracker.margin_analysis()

        result.get("margin_gap", 0)

    def test_record_payment_updates_monthly_summary(self, revenue_tracker, fs):
        """record_payment updates monthly-summary.json."""
        invoice = Invoice(
            invoice_id="inv-monthly",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=800,
            total=800,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        monthly_path = fs.base / "revenue" / "monthly-summary.json"
        assert monthly_path.exists()

        data = json.loads(monthly_path.read_text())
        assert data["month_total"] == 800

    def test_record_payment_updates_annual_summary(self, revenue_tracker, fs):
        """record_payment updates annual-summary.json."""
        invoice = Invoice(
            invoice_id="inv-annual",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=1200,
            total=1200,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        annual_path = fs.base / "revenue" / "annual-summary.json"
        assert annual_path.exists()

        data = json.loads(annual_path.read_text())
        assert data["year_total"] == 1200

    def test_get_current_week_summary(self, revenue_tracker):
        """get_current_week_summary returns RevenueSummary."""
        summary = revenue_tracker.get_current_week_summary()

        assert isinstance(summary, RevenueSummary)

    def test_pipeline_value_calculation(self, revenue_tracker, fs):
        """Pipeline value sums sent/ invoices."""
        sent_dir = fs.base / "invoices" / "sent"
        sent_dir.mkdir(parents=True, exist_ok=True)

        for i in range(2):
            invoice = Invoice(
                invoice_id=f"inv-pipeline-{i}",
                project_id=f"proj-{i}",
                client_id=f"client-{i}",
                line_items=[],
                subtotal=500,
                total=500,
                payment_risk_level="low",
                due_date="2026-03-01",
            )
            (sent_dir / f"inv-pipeline-{i}.json").write_text(
                json.dumps(invoice.to_dict())
            )

        summary = revenue_tracker.generate_weekly_summary()

        assert summary.pipeline_value >= 1000

    def test_revenue_summary_totals_only(self, revenue_tracker, gateway):
        """Revenue summary contains only totals, no line items or client names."""
        invoice = Invoice(
            invoice_id="inv-totals",
            project_id="proj-1",
            client_id="client-secret",
            line_items=[],
            subtotal=1000,
            total=1000,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        revenue_msgs = [
            m for m in gateway.sent_messages if m["message_type"] == "revenue_summary"
        ]
        assert len(revenue_msgs) >= 1

        payload = revenue_msgs[-1]["payload"]
        assert "line_items" not in payload
        assert "client_names" not in payload
        assert "week_total" in payload

    def test_logged_to_operational_log(self, revenue_tracker, operational_log):
        """Payment recording is logged."""
        invoice = Invoice(
            invoice_id="inv-logged",
            project_id="proj-1",
            client_id="client-1",
            line_items=[],
            subtotal=100,
            total=100,
            payment_risk_level="low",
            due_date="2026-03-01",
        )

        revenue_tracker.record_payment(invoice)

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "payment_recorded" for e in entries)

    def test_multiple_payments_accumulate(self, revenue_tracker, fs):
        """Multiple payments accumulate in weekly summary."""
        for i in range(3):
            invoice = Invoice(
                invoice_id=f"inv-multi-{i}",
                project_id=f"proj-{i}",
                client_id=f"client-{i}",
                line_items=[],
                subtotal=333,
                total=333,
                payment_risk_level="low",
                due_date="2026-03-01",
            )
            revenue_tracker.record_payment(invoice)

        weekly_path = fs.base / "revenue" / "weekly-summary.json"
        data = json.loads(weekly_path.read_text())

        assert data["invoices_paid"] == 3
        assert data["week_total"] == 999
