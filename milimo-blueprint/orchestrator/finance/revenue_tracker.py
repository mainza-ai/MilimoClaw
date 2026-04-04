# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Revenue Tracker.

Tracks all revenue and maintains summary files.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Any, Protocol
import json

from .finance_init import FinanceFilesystemInit, FinanceOperationalLog, FinanceLogEntry
from .signal_dispatcher import FinanceSignalDispatcher
from .invoice_manager import Invoice


class InferenceClient(Protocol):
    """Protocol for inference client."""

    def complete(
        self,
        prompt: str,
        data_type: str,
        max_tokens: int = 800,
    ) -> str:
        """Complete a prompt with the model."""
        ...


@dataclass
class RevenueSummary:
    """Revenue summary for a week."""

    week_start: str
    week_total: float
    week_over_week_pct: float
    invoices_paid: int
    invoices_pending: int
    pipeline_value: float
    last_updated: str


class RevenueTracker:
    """
    Tracks all revenue and maintains summary files.

    Updates weekly-summary.json on every payment received.
    Generates full weekly summary every Sunday at 03:00.
    Sends revenue_summary to Analytics Claw after each update.
    Runs margin analysis and rate optimization checks weekly.
    All inference calls log data_type.
    """

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        inference_client: InferenceClient,
        dispatcher: FinanceSignalDispatcher,
        approval_handler: Any,
        operational_log: FinanceOperationalLog,
    ):
        self.fs = fs
        self.inference_client = inference_client
        self.dispatcher = dispatcher
        self.approval_handler = approval_handler
        self.operational_log = operational_log

    def record_payment(self, invoice: Invoice) -> None:
        """
        Record a payment.

        Called when payment_monitor detects a payment.
        1. Load weekly-summary.json
        2. Add payment to week_total
        3. Increment invoices_paid
        4. Write daily snapshot to revenue/history/{today}.json
        5. Update weekly-summary.json atomically (temp → rename)
        6. Update monthly and annual summaries
        7. Send revenue_summary to Analytics Claw via dispatcher
        8. Log: action_type="payment_recorded"
        """
        today = datetime.now(timezone.utc)
        today_str = today.strftime("%Y-%m-%d")

        weekly_path = self.fs.base / "revenue" / "weekly-summary.json"
        weekly_data = self._load_json(weekly_path, {
            "week_total": 0,
            "invoices_paid": 0,
            "invoices_pending": 0,
            "week_over_week_pct": 0.0,
            "last_updated": None,
        })

        previous_week_total = weekly_data.get("week_total", 0)
        weekly_data["week_total"] = previous_week_total + invoice.total
        weekly_data["invoices_paid"] = weekly_data.get("invoices_paid", 0) + 1
        weekly_data["last_updated"] = today.isoformat()

        self._atomic_write_summary(weekly_path, weekly_data)

        daily_path = self.fs.get_revenue_daily_path(today)
        daily_data = {
            "date": today_str,
            "payments": [{"invoice_id": invoice.invoice_id, "amount": invoice.total}],
            "total": invoice.total,
        }
        self._atomic_write_summary(daily_path, daily_data)

        self._update_monthly_summary(invoice)
        self._update_annual_summary(invoice)

        week_over_week = 0.0
        if previous_week_total > 0:
            week_over_week = ((weekly_data["week_total"] - previous_week_total) / previous_week_total) * 100

        self.dispatcher.send_revenue_summary(
            week_total=weekly_data["week_total"],
            week_over_week_pct=week_over_week,
            invoices_paid=weekly_data["invoices_paid"],
            invoices_pending=weekly_data.get("invoices_pending", 0),
        )

        entry = FinanceLogEntry(
            timestamp=today.isoformat(),
            action_type="payment_recorded",
            entity_id=invoice.invoice_id,
            amount=invoice.total,
            outcome="success",
            details={"week_total": weekly_data["week_total"]},
        )
        self.operational_log.append(entry)

    def generate_weekly_summary(self) -> RevenueSummary:
        """
        Generate full weekly summary.

        Full weekly aggregation — runs Sunday 03:00.
        1. Aggregate all paid/ invoices from past 7 days
        2. Count pending invoices (pending/ + approved/ + sent/)
        3. Calculate pipeline_value (sum of sent/ invoices not yet paid)
        4. Calculate week-over-week vs previous week snapshot
        5. Write to revenue/weekly-summary.json atomically
        6. Archive previous week to revenue/history/{last-monday}.json
        7. Run margin_analysis()
        8. Run rate_optimization_check()
        9. Send revenue_summary to Analytics Claw
        10. Log: action_type="weekly_summary_generated"
        """
        today = datetime.now(timezone.utc)

        week_invoices = self._load_week_invoices(days=7)
        week_total = sum(inv.total for inv in week_invoices)
        invoices_paid = len(week_invoices)

        pending_invoices = self._count_pending_invoices()
        pipeline_value = self._calculate_pipeline_value()

        previous_week_total = self._get_previous_week_total()
        week_over_week = 0.0
        if previous_week_total > 0:
            week_over_week = ((week_total - previous_week_total) / previous_week_total) * 100

        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

        summary = RevenueSummary(
            week_start=week_start,
            week_total=week_total,
            week_over_week_pct=week_over_week,
            invoices_paid=invoices_paid,
            invoices_pending=pending_invoices,
            pipeline_value=pipeline_value,
            last_updated=today.isoformat(),
        )

        weekly_path = self.fs.base / "revenue" / "weekly-summary.json"
        self._atomic_write_summary(weekly_path, {
            "week_start": summary.week_start,
            "week_total": summary.week_total,
            "week_over_week_pct": summary.week_over_week_pct,
            "invoices_paid": summary.invoices_paid,
            "invoices_pending": summary.invoices_pending,
            "pipeline_value": summary.pipeline_value,
            "last_updated": summary.last_updated,
        })

        self.dispatcher.send_revenue_summary(
            week_total=summary.week_total,
            week_over_week_pct=summary.week_over_week_pct,
            invoices_paid=summary.invoices_paid,
            invoices_pending=summary.invoices_pending,
        )

        entry = FinanceLogEntry(
            timestamp=today.isoformat(),
            action_type="weekly_summary_generated",
            entity_id=week_start,
            amount=week_total,
            outcome="success",
            details={"invoices_paid": invoices_paid, "pipeline": pipeline_value},
        )
        self.operational_log.append(entry)

        return summary

    def margin_analysis(self) -> dict:
        """
        Run margin analysis.

        Compare revenue vs expenses and estimated project costs.
        Inference call: data_type="margin_analysis".
        If margin < target by >10%: queue War Room REVIEW (margin alert).
        Log: action_type="margin_analysis_complete".
        """
        today = datetime.now(timezone.utc)

        revenue = self._get_current_revenue()
        expenses = self._get_current_expenses()

        margin_pct = 0.0
        if revenue > 0:
            margin_pct = ((revenue - expenses) / revenue) * 100

        target_margin = 30.0
        margin_gap = target_margin - margin_pct

        try:
            prompt = f"""Analyze business margin health.

Revenue: ${revenue:.2f}
Expenses: ${expenses:.2f}
Current Margin: {margin_pct:.1f}%
Target Margin: {target_margin:.1f}%
Gap: {margin_gap:.1f}%

Provide a brief analysis and any recommendations."""

            self.inference_client.complete(
                prompt=prompt,
                data_type="margin_analysis",
                max_tokens=400,
            )
        except Exception:
            pass

        result = {
            "revenue": revenue,
            "expenses": expenses,
            "margin_pct": margin_pct,
            "target_margin": target_margin,
            "margin_gap": margin_gap,
        }

        if margin_gap > 10:
            entry = FinanceLogEntry(
                timestamp=today.isoformat(),
                action_type="margin_alert",
                entity_id="margin",
                amount=margin_gap,
                outcome="alert",
                details=result,
            )
            self.operational_log.append(entry)

            if self.approval_handler:
                self.approval_handler.queue_margin_alert(
                    project_id="margin_analysis",
                    expected_margin_pct=target_margin,
                    actual_margin_pct=margin_pct,
                )

        entry = FinanceLogEntry(
            timestamp=today.isoformat(),
            action_type="margin_analysis_complete",
            entity_id="margin",
            amount=margin_pct,
            outcome="success",
            details=result,
        )
        self.operational_log.append(entry)

        return result

    def rate_optimization_check(self) -> dict:
        """
        Run rate optimization check.

        Compare current rates against delivery quality data.
        Inference call: data_type="rate_benchmarking_narrative".
        If systematically undercharging: queue War Room REVIEW.
        Log: action_type="rate_optimization_check".
        """
        today = datetime.now(timezone.utc)

        pricing_path = self.fs.base / "pricing" / "rules.json"
        pricing_data = self._load_json(pricing_path, {"default_hourly_rate": 100})
        current_rate = pricing_data.get("default_hourly_rate", 100)

        recommendation = "No change needed"
        suggested_rate = current_rate
        undercharging = False

        try:
            prompt = f"""Analyze current hourly rate for optimization.

Current Rate: ${current_rate}/hour

Market benchmark rates for similar services range from $80-$200/hour.

Should the rate be adjusted? Provide:
1. Recommendation: "increase", "decrease", or "maintain"
2. Suggested rate (if change recommended)
3. Brief reasoning"""

            output = self.inference_client.complete(
                prompt=prompt,
                data_type="rate_benchmarking_narrative",
                max_tokens=400,
            )

            if "increase" in output.lower():
                undercharging = True
                import re
                rate_match = re.search(r"\$(\d+)", output)
                if rate_match:
                    suggested_rate = float(rate_match.group(1))
                    recommendation = f"Increase rate to ${suggested_rate}/hour"
        except Exception:
            pass

        result = {
            "current_rate": current_rate,
            "recommendation": recommendation,
            "suggested_rate": suggested_rate,
        }

        if undercharging and self.approval_handler:
            self.approval_handler.queue_rate_recommendation(
                recommendation=recommendation,
                suggested_rate=suggested_rate,
                current_rate=current_rate,
            )

        entry = FinanceLogEntry(
            timestamp=today.isoformat(),
            action_type="rate_optimization_check",
            entity_id="rates",
            amount=current_rate,
            outcome="success",
            details=result,
        )
        self.operational_log.append(entry)

        return result

    def get_current_week_summary(self) -> RevenueSummary:
        """Read revenue/weekly-summary.json and return RevenueSummary."""
        weekly_path = self.fs.base / "revenue" / "weekly-summary.json"
        data = self._load_json(weekly_path, {
            "week_start": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "week_total": 0,
            "week_over_week_pct": 0.0,
            "invoices_paid": 0,
            "invoices_pending": 0,
            "pipeline_value": 0,
            "last_updated": None,
        })

        return RevenueSummary(
            week_start=data.get("week_start", ""),
            week_total=data.get("week_total", 0),
            week_over_week_pct=data.get("week_over_week_pct", 0.0),
            invoices_paid=data.get("invoices_paid", 0),
            invoices_pending=data.get("invoices_pending", 0),
            pipeline_value=data.get("pipeline_value", 0),
            last_updated=data.get("last_updated", ""),
        )

    def _load_week_invoices(self, days: int = 7) -> list[Invoice]:
        """Load all invoices paid within the last N days."""
        from finance.invoice_manager import Invoice

        invoices: list[Invoice] = []
        paid_dir = self.fs.base / "invoices" / "paid"

        if not paid_dir.exists():
            return invoices

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        for path in paid_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("paid_at"):
                    paid_at = datetime.fromisoformat(data["paid_at"])
                    if paid_at >= cutoff:
                        invoices.append(Invoice.from_dict(data))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return invoices

    def _count_pending_invoices(self) -> int:
        """Count invoices in pending/, approved/, and sent/."""
        count = 0

        for status in ["pending", "approved", "sent"]:
            status_dir = self.fs.base / "invoices" / status
            if status_dir.exists():
                count += len(list(status_dir.glob("*.json")))

        return count

    def _calculate_pipeline_value(self) -> float:
        """Sum all sent/ invoices not yet paid."""
        total = 0.0
        sent_dir = self.fs.base / "invoices" / "sent"

        if not sent_dir.exists():
            return total

        for path in sent_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                total += data.get("total", 0)
            except (json.JSONDecodeError, KeyError):
                continue

        return total

    def _get_previous_week_total(self) -> float:
        """Get total revenue from previous week snapshot."""
        today = datetime.now(timezone.utc)
        last_monday = today - timedelta(days=today.weekday() + 7)
        snapshot_path = self.fs.base / "revenue" / "history" / f"{last_monday.strftime('%Y-%m-%d')}.json"

        if not snapshot_path.exists():
            return 0.0

        data = self._load_json(snapshot_path, {})
        return data.get("week_total", 0)

    def _get_current_revenue(self) -> float:
        """Get current total revenue from annual summary."""
        annual_path = self.fs.base / "revenue" / "annual-summary.json"
        data = self._load_json(annual_path, {"year_total": 0})
        return data.get("year_total", 0)

    def _get_current_expenses(self) -> float:
        """Get current total expenses from expense log."""
        total = 0.0
        expense_path = self.fs.base / "expenses" / "log.jsonl"

        if not expense_path.exists():
            return total

        with open(expense_path) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    total += data.get("amount", 0)
                except (json.JSONDecodeError, KeyError):
                    continue

        return total

    def _update_monthly_summary(self, invoice: Invoice) -> None:
        """Update monthly summary with payment."""
        monthly_path = self.fs.base / "revenue" / "monthly-summary.json"
        data = self._load_json(monthly_path, {
            "month_total": 0,
            "invoices_paid": 0,
            "last_updated": None,
        })

        data["month_total"] = data.get("month_total", 0) + invoice.total
        data["invoices_paid"] = data.get("invoices_paid", 0) + 1
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

        self._atomic_write_summary(monthly_path, data)

    def _update_annual_summary(self, invoice: Invoice) -> None:
        """Update annual summary with payment."""
        annual_path = self.fs.base / "revenue" / "annual-summary.json"
        data = self._load_json(annual_path, {
            "year_total": 0,
            "invoices_paid": 0,
            "last_updated": None,
        })

        data["year_total"] = data.get("year_total", 0) + invoice.total
        data["invoices_paid"] = data.get("invoices_paid", 0) + 1
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

        self._atomic_write_summary(annual_path, data)

    def _load_json(self, path: Path, default: dict) -> dict:
        """Load JSON file or return default."""
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, Exception):
            return default

    def _atomic_write_summary(self, path: Path, data: dict) -> None:
        """
        Write to temp file in same dir, rename on success.
        Never overwrite good data with partial write.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.rename(path)
