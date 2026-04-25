# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Scheduler."""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import FinanceOperationalLog
from finance.finance_scheduler import FinanceScheduler


class MockPaymentMonitor:
    """Mock payment monitor."""

    def __init__(self):
        self.check_all_calls = 0
        self.flag_overdue_calls = 0

    def check_all_sent_invoices(self):
        self.check_all_calls += 1

    def check_and_flag_overdue(self):
        self.flag_overdue_calls += 1


class MockRevenueTracker:
    """Mock revenue tracker."""

    def __init__(self):
        self.summary_calls = 0
        self.last_summary = None

    def generate_weekly_summary(self):
        from finance.revenue_tracker import RevenueSummary

        self.summary_calls += 1
        self.last_summary = RevenueSummary(
            week_start="2026-03-15",
            week_total=5000,
            week_over_week_pct=10.0,
            invoices_paid=5,
            invoices_pending=2,
            pipeline_value=3000,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        return self.last_summary


class MockExpenseTracker:
    """Mock expense tracker."""

    def __init__(self):
        self.uncategorized = []
        self.expenses_by_period = []

    def get_uncategorized_expenses(self):
        return self.uncategorized

    def get_expenses_by_period(self, start_date, end_date):
        return self.expenses_by_period

    def get_category_summary(self):
        return {"office_supplies": 100}


class MockApprovalHandler:
    """Mock approval handler."""

    def __init__(self):
        self.queued_reviews = []
        self.queued_holds = []

    def queue_overdue_review(self, invoice, days_overdue):
        self.queued_reviews.append((invoice, days_overdue))

    def queue_overdue_hold(self, invoice, days_overdue, overdue_count):
        self.queued_holds.append((invoice, days_overdue, overdue_count))

    def queue_invoice_hold(self, invoice):
        self.queued_holds.append((invoice,))


class TestFinanceScheduler:
    """Tests for FinanceScheduler."""

    @pytest.fixture
    def fs_path(self, tmp_path: Path):
        (tmp_path / "invoices" / "approved").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tax" / "quarterly").mkdir(parents=True, exist_ok=True)
        return tmp_path

    @pytest.fixture
    def operational_log(self, tmp_path: Path):
        log_path = tmp_path / "logs" / "operational.log"
        return FinanceOperationalLog(log_path)

    @pytest.fixture
    def payment_monitor(self):
        return MockPaymentMonitor()

    @pytest.fixture
    def revenue_tracker(self):
        return MockRevenueTracker()

    @pytest.fixture
    def expense_tracker(self):
        return MockExpenseTracker()

    @pytest.fixture
    def approval_handler(self):
        return MockApprovalHandler()

    @pytest.fixture
    def scheduler(
        self,
        payment_monitor,
        revenue_tracker,
        expense_tracker,
        approval_handler,
        operational_log,
        fs_path,
    ):
        return FinanceScheduler(
            payment_monitor=payment_monitor,
            revenue_tracker=revenue_tracker,
            expense_tracker=expense_tracker,
            approval_handler=approval_handler,
            operational_log=operational_log,
            fs_path=fs_path,
        )

    def test_start_logs_scheduler_started(self, scheduler, operational_log):
        """start logs scheduler_started."""
        scheduler.start()
        scheduler.stop()

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "scheduler_started" for e in entries)

    def test_stop_logs_scheduler_stopped(self, scheduler, operational_log):
        """stop logs scheduler_stopped."""
        scheduler.start()
        scheduler.stop()

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "scheduler_stopped" for e in entries)

    def test_run_daily_payment_check_calls_monitor(self, scheduler, payment_monitor):
        """_run_daily_payment_check calls payment monitor methods."""
        scheduler._run_daily_payment_check()

        assert payment_monitor.check_all_calls == 1
        assert payment_monitor.flag_overdue_calls == 1

    def test_run_weekly_summary_calls_tracker(self, scheduler, revenue_tracker):
        """_run_weekly_summary calls revenue tracker."""
        scheduler._run_weekly_summary()

        assert revenue_tracker.summary_calls == 1

    def test_daily_payment_check_logged(self, scheduler, operational_log):
        """Daily payment check is logged."""
        scheduler._run_daily_payment_check()

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "daily_payment_check_complete" for e in entries)

    def test_weekly_summary_logged(self, scheduler, operational_log):
        """Weekly summary is logged."""
        scheduler._run_weekly_summary()

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "weekly_summary_complete" for e in entries)

    def test_quarterly_tax_prep_writes_file(self, scheduler, fs_path, operational_log):
        """Quarterly tax prep writes quarterly file."""
        scheduler._run_quarterly_tax_prep()

        year = datetime.now(timezone.utc).year
        quarter = (datetime.now(timezone.utc).month - 1) // 3 + 1

        tax_path = fs_path / "tax" / "quarterly" / f"{year}-Q{quarter}.json"
        assert tax_path.exists()

        data = json.loads(tax_path.read_text())
        assert data["year"] == year
        assert data["quarter"] == quarter

    def test_quarterly_tax_prep_logged(self, scheduler, operational_log):
        """Quarterly tax prep is logged."""
        scheduler._run_quarterly_tax_prep()

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "quarterly_tax_prep" for e in entries)

    def test_check_hold_staleness_flags_48h(self, scheduler, fs_path, operational_log):
        """_check_hold_staleness flags invoices stuck > 48h."""
        approved_dir = fs_path / "invoices" / "approved"
        approved_dir.mkdir(parents=True, exist_ok=True)

        stale_invoice = {
            "invoice_id": "inv-stale",
            "project_id": "proj-stale",
            "client_id": "client-1",
            "line_items": [],
            "subtotal": 1000,
            "total": 1000,
            "payment_risk_level": "low",
            "due_date": "2026-04-01",
            "status": "approved",
            "approved_at": (
                datetime.now(timezone.utc) - timedelta(hours=50)
            ).isoformat(),
        }
        (approved_dir / "inv-stale.json").write_text(json.dumps(stale_invoice))

        scheduler._check_hold_staleness()

        entries = operational_log.read_recent(days=1)
        stale_entries = [e for e in entries if "hold_stale" in e.action_type]
        assert len(stale_entries) >= 1

    def test_check_hold_staleness_escalates_7days(
        self, scheduler, fs_path, operational_log
    ):
        """_check_hold_staleness escalates invoices stuck > 7 days."""
        approved_dir = fs_path / "invoices" / "approved"
        approved_dir.mkdir(parents=True, exist_ok=True)

        very_stale_invoice = {
            "invoice_id": "inv-very-stale",
            "project_id": "proj-very-stale",
            "client_id": "client-2",
            "line_items": [],
            "subtotal": 2000,
            "total": 2000,
            "payment_risk_level": "low",
            "due_date": "2026-04-01",
            "status": "approved",
            "approved_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
        }
        (approved_dir / "inv-very-stale.json").write_text(
            json.dumps(very_stale_invoice)
        )

        scheduler._check_hold_staleness()

        entries = operational_log.read_recent(days=1)
        seven_day_entries = [e for e in entries if "hold_stale_7days" in e.action_type]
        assert len(seven_day_entries) >= 1

    def test_is_quarter_start(self, scheduler):
        """_is_quarter_start returns True for quarter starts."""

        class MockDatetime:
            @staticmethod
            def now(tz):
                class MockDate:
                    year = 2026
                    month = 1
                    day = 1

                return MockDate()

        import finance.finance_scheduler as fs_module

        original = fs_module.datetime
        fs_module.datetime = MockDatetime

        try:
            assert scheduler._is_quarter_start()
        finally:
            fs_module.datetime = original

    def test_seconds_until_next_day(self, scheduler):
        """_seconds_until calculates delay correctly."""
        delay = scheduler._seconds_until(9, 0)

        assert delay > 0
        assert delay < 86400

    def test_seconds_until_next_sunday(self, scheduler):
        """_seconds_until calculates delay for specific weekday."""
        delay = scheduler._seconds_until(3, 0, target_weekday=6)

        assert delay > 0
        assert delay <= 7 * 86400

    def test_scheduler_can_start_and_stop(self, scheduler):
        """Scheduler can start and stop cleanly."""
        scheduler.start()
        assert scheduler._running

        scheduler.stop()
        assert not scheduler._running

    def test_double_start_is_idempotent(self, scheduler):
        """Double start is idempotent."""
        scheduler.start()
        scheduler.start()

        assert scheduler._running

        scheduler.stop()

    def test_daily_check_exception_logged(
        self, scheduler, payment_monitor, operational_log
    ):
        """Daily check exceptions are logged."""
        payment_monitor.check_all_sent_invoices = lambda: (_ for _ in ()).throw(
            RuntimeError("Test error")
        )

        scheduler._run_daily_payment_check()

        entries = operational_log.read_recent(days=1)
        failed_entries = [
            e for e in entries if e.action_type == "daily_payment_check_failed"
        ]
        assert len(failed_entries) >= 1

    def test_weekly_summary_exception_logged(
        self, scheduler, revenue_tracker, operational_log
    ):
        """Weekly summary exceptions are logged."""
        revenue_tracker.generate_weekly_summary = lambda: (_ for _ in ()).throw(
            RuntimeError("Test error")
        )

        scheduler._run_weekly_summary()

        entries = operational_log.read_recent(days=1)
        failed_entries = [
            e for e in entries if e.action_type == "weekly_summary_failed"
        ]
        assert len(failed_entries) >= 1

    def test_quarterly_prep_with_uncategorized(
        self, scheduler, expense_tracker, approval_handler
    ):
        """Quarterly prep queues review for uncategorized expenses."""
        from finance.expense_tracker import ExpenseEntry

        expense_tracker.uncategorized = [
            ExpenseEntry(
                expense_id="exp-1",
                description="Uncategorized",
                amount=100,
                currency="USD",
                expense_date="2026-03-01",
                tax_category="uncategorized",
                source="manual",
                logged_at="2026-03-01T10:00:00",
            )
        ]

        scheduler._run_quarterly_tax_prep()

        assert len(approval_handler.queued_reviews) >= 1
