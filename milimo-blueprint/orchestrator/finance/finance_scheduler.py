# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Scheduler.

Orchestrates all scheduled autonomous actions for the Finance Claw.
"""

import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable
import json

from .finance_init import FinanceOperationalLog, FinanceLogEntry


class FinanceScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Finance Claw.

    Schedule:
    - Daily 09:00 — Payment status check for all sent invoices
    - Daily 09:00 — Overdue detection pass
    - Sunday 03:00 — Weekly revenue summary generation
    - Quarterly Day 1 — Tax prep summary generation (Jan 1, Apr 1, Jul 1, Oct 1)

    Uses threading.Timer with recalculated delay.
    No cron. No APScheduler. Only stdlib.
    Checks for missed jobs on startup.
    """

    def __init__(
        self,
        payment_monitor: Any,
        revenue_tracker: Any,
        expense_tracker: Any,
        approval_handler: Any,
        operational_log: FinanceOperationalLog,
        fs_path: Path,
    ):
        self.payment_monitor = payment_monitor
        self.revenue_tracker = revenue_tracker
        self.expense_tracker = expense_tracker
        self.approval_handler = approval_handler
        self.operational_log = operational_log
        self.fs_path = fs_path

        self._timers: list[threading.Timer] = []
        self._running = False

    def start(self) -> None:
        """
        Start the scheduler.

        Initialize all scheduled timers.
        Check for missed jobs since last shutdown.
        Log: action_type="scheduler_started"
        """
        if self._running:
            return

        self._running = True

        self._schedule_daily_payment_check()
        self._schedule_weekly_summary()
        self._schedule_quarterly_tax_prep()
        self._schedule_hold_staleness_check()

        self._check_missed_jobs()

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="scheduler_started",
            entity_id="scheduler",
            amount=None,
            outcome="success",
            details={},
        )
        self.operational_log.append(entry)

    def stop(self) -> None:
        """
        Stop the scheduler.

        Cancel all pending timers.
        Log: action_type="scheduler_stopped"
        """
        self._running = False

        for timer in self._timers:
            timer.cancel()

        self._timers.clear()

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="scheduler_stopped",
            entity_id="scheduler",
            amount=None,
            outcome="success",
            details={},
        )
        self.operational_log.append(entry)

    def _run_daily_payment_check(self) -> None:
        """
        Run daily payment check.

        payment_monitor.check_all_sent_invoices()
        payment_monitor.check_and_flag_overdue()
        Log timing.
        """
        start_time = datetime.now(timezone.utc)

        try:
            self.payment_monitor.check_all_sent_invoices()
            self.payment_monitor.check_and_flag_overdue()

            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="daily_payment_check_complete",
                entity_id="daily",
                amount=None,
                outcome="success",
                details={
                    "duration_seconds": (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds()
                },
            )
            self.operational_log.append(entry)

        except Exception as e:
            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="daily_payment_check_failed",
                entity_id="daily",
                amount=None,
                outcome="failed",
                details={"error": str(e)},
            )
            self.operational_log.append(entry)

        if self._running:
            self._schedule_daily_payment_check()

    def _run_weekly_summary(self) -> None:
        """
        Run weekly summary generation.

        revenue_tracker.generate_weekly_summary()
        Log timing.
        """
        start_time = datetime.now(timezone.utc)

        try:
            summary = self.revenue_tracker.generate_weekly_summary()

            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="weekly_summary_complete",
                entity_id=summary.week_start,
                amount=summary.week_total,
                outcome="success",
                details={
                    "duration_seconds": (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds()
                },
            )
            self.operational_log.append(entry)

        except Exception as e:
            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="weekly_summary_failed",
                entity_id="weekly",
                amount=None,
                outcome="failed",
                details={"error": str(e)},
            )
            self.operational_log.append(entry)

        if self._running:
            self._schedule_weekly_summary()

    def _run_quarterly_tax_prep(self) -> None:
        """
        Run quarterly tax prep.

        Aggregate income and expenses for the quarter.
        Verify all expenses are categorized.
        Batch uncategorized expenses → War Room REVIEW.
        Write tax/quarterly/{YYYY-Q}.json.
        Queue War Room AUTO: "Q{N} tax summary ready".
        Log: action_type="quarterly_tax_prep"
        """
        today = datetime.now(timezone.utc)
        year = today.year
        quarter = (today.month - 1) // 3 + 1

        try:
            uncategorized = self.expense_tracker.get_uncategorized_expenses()

            if uncategorized:
                for expense in uncategorized[:10]:
                    self.approval_handler.queue_overdue_review(
                        self._create_mock_invoice(expense),
                        0,
                    )

            quarter_start = datetime(year, (quarter - 1) * 3 + 1, 1)
            quarter_end_day = {1: 31, 2: 30, 3: 30, 4: 31}[quarter]
            quarter_end = datetime(year, quarter * 3, quarter_end_day)

            expenses = self.expense_tracker.get_expenses_by_period(
                quarter_start.strftime("%Y-%m-%d"),
                quarter_end.strftime("%Y-%m-%d"),
            )

            category_summary = self.expense_tracker.get_category_summary()

            tax_data = {
                "year": year,
                "quarter": quarter,
                "total_expenses": sum(e.amount for e in expenses),
                "expense_count": len(expenses),
                "uncategorized_count": len(uncategorized),
                "category_breakdown": category_summary,
                "generated_at": today.isoformat(),
            }

            tax_path = self.fs_path / "tax" / "quarterly" / f"{year}-Q{quarter}.json"
            tax_path.parent.mkdir(parents=True, exist_ok=True)
            tax_path.write_text(json.dumps(tax_data, indent=2))

            entry = FinanceLogEntry(
                timestamp=today.isoformat(),
                action_type="quarterly_tax_prep",
                entity_id=f"{year}-Q{quarter}",
                amount=tax_data["total_expenses"],
                outcome="success",
                details={"uncategorized": len(uncategorized)},
            )
            self.operational_log.append(entry)

        except Exception as e:
            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="quarterly_tax_prep_failed",
                entity_id="tax_prep",
                amount=None,
                outcome="failed",
                details={"error": str(e)},
            )
            self.operational_log.append(entry)

    def _check_hold_staleness(self) -> None:
        """
        Check for stale HOLD items.

        Runs daily.
        Check all invoices in approved/ (stuck in HOLD queue).
        If in HOLD > 48 hours: add urgency flag to War Room card.
        If in HOLD > 7 days: escalate urgency flag.
        """
        from .invoice_manager import Invoice

        approved_dir = self.fs_path / "invoices" / "approved"

        if not approved_dir.exists():
            return

        today = datetime.now(timezone.utc)

        for invoice_path in approved_dir.glob("*.json"):
            try:
                data = json.loads(invoice_path.read_text())
                approved_at = data.get("approved_at")

                if not approved_at:
                    continue

                approved_time = datetime.fromisoformat(
                    approved_at.replace("Z", "+00:00")
                )
                hours_in_hold = (today - approved_time).total_seconds() / 3600

                invoice = Invoice.from_dict(data)

                if hours_in_hold > 168:
                    entry = FinanceLogEntry(
                        timestamp=today.isoformat(),
                        action_type="hold_stale_7days",
                        entity_id=data.get("invoice_id", ""),
                        amount=data.get("total", 0),
                        outcome="escalated",
                        details={"hours_in_hold": hours_in_hold},
                    )
                    self.operational_log.append(entry)

                    if self.approval_handler:
                        self.approval_handler.queue_invoice_hold(invoice)

                elif hours_in_hold > 48:
                    entry = FinanceLogEntry(
                        timestamp=today.isoformat(),
                        action_type="hold_stale_48h",
                        entity_id=data.get("invoice_id", ""),
                        amount=data.get("total", 0),
                        outcome="flagged",
                        details={"hours_in_hold": hours_in_hold},
                    )
                    self.operational_log.append(entry)

                    if self.approval_handler:
                        self.approval_handler.queue_invoice_hold(invoice)

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def _check_missed_jobs(self) -> None:
        """
        Check for missed jobs since last shutdown.

        Read last_run timestamps from operational.log.
        If weekly summary last ran > 8 days ago: run immediately.
        If daily payment check last ran > 36 hours ago: run immediately.
        Log any recovered jobs.
        """
        entries = self.operational_log.read_recent(days=30)

        last_daily = None
        last_weekly = None

        for entry in reversed(entries):
            if entry.action_type == "daily_payment_check_complete":
                last_daily = entry.timestamp
            elif entry.action_type == "weekly_summary_complete":
                last_weekly = entry.timestamp

        today = datetime.now(timezone.utc)

        if last_daily:
            last_daily_time = datetime.fromisoformat(last_daily.replace("Z", "+00:00"))
            hours_since_daily = (today - last_daily_time).total_seconds() / 3600

            if hours_since_daily > 36:
                self._run_daily_payment_check()
                self._log_recovered_job("daily_payment_check", hours_since_daily)

        else:
            self._run_daily_payment_check()
            self._log_recovered_job("daily_payment_check", 0)

        if last_weekly:
            last_weekly_time = datetime.fromisoformat(
                last_weekly.replace("Z", "+00:00")
            )
            days_since_weekly = (today - last_weekly_time).total_seconds() / 86400

            if days_since_weekly > 8:
                self._run_weekly_summary()
                self._log_recovered_job("weekly_summary", days_since_weekly)

    def _schedule_daily_payment_check(self) -> None:
        """Schedule the next daily payment check at 09:00."""
        delay = self._seconds_until(9, 0)

        timer = threading.Timer(delay, self._run_daily_payment_check)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _schedule_weekly_summary(self) -> None:
        """Schedule the next weekly summary for Sunday 03:00."""
        delay = self._seconds_until(3, 0, target_weekday=6)

        timer = threading.Timer(delay, self._run_weekly_summary)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _schedule_quarterly_tax_prep(self) -> None:
        """Schedule quarterly tax prep check."""
        delay = self._seconds_until(9, 0)

        def check_quarterly():
            if self._is_quarter_start():
                self._run_quarterly_tax_prep()

            if self._running:
                self._schedule_quarterly_tax_prep()

        timer = threading.Timer(delay, check_quarterly)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None,
    ) -> float:
        """Calculate seconds until the next target time."""
        now = datetime.now(timezone.utc)

        target = now.replace(
            hour=target_hour,
            minute=target_minute,
            second=0,
            microsecond=0,
        )

        if target_weekday is not None:
            days_until = (target_weekday - now.weekday()) % 7
            if days_until == 0 and target <= now:
                days_until = 7
            target = target + timedelta(days=days_until)
        elif target <= now:
            target = target + timedelta(days=1)

        return (target - now).total_seconds()

    def _is_quarter_start(self) -> bool:
        """Check if today is a quarter start (Jan 1, Apr 1, Jul 1, Oct 1)."""
        today = datetime.now(timezone.utc)
        return today.month in [1, 4, 7, 10] and today.day == 1

    def _schedule_hold_staleness_check(self) -> None:
        """Schedule the next hold staleness check at 10:00 daily."""
        delay = self._seconds_until(10, 0)

        def check_staleness():
            self._check_hold_staleness()
            if self._running:
                self._schedule_hold_staleness_check()

        timer = threading.Timer(delay, check_staleness)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _log_recovered_job(self, job_name: str, delay: float) -> None:
        """Log a recovered job."""
        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="job_recovered",
            entity_id=job_name,
            amount=None,
            outcome="recovered",
            details={"delay_hours": delay},
        )
        self.operational_log.append(entry)

    def _create_mock_invoice(self, expense: Any) -> Any:
        """Create a mock invoice for approval handler."""
        from .invoice_manager import Invoice

        return Invoice(
            invoice_id=f"exp-review-{expense.expense_id}",
            project_id="",
            client_id="",
            line_items=[],
            subtotal=expense.amount,
            total=expense.amount,
            payment_risk_level="unknown",
        )
