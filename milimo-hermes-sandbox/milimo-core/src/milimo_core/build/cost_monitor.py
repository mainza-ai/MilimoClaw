# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Build Claw cost monitor.

Handles:
- Daily inference cost checks
- Baseline calculation from 4-week history
- Drift detection (>15% triggers REVIEW alert)
- Cost per user breakdown
- Cost alerts logging

Enhancement: Category-based cost tracking per data_type.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from .approval_handler import BuildApprovalHandler
from .signal_dispatcher import BuildSignalDispatcher

logger = logging.getLogger(__name__)


@dataclass
class CostCheckResult:
    total_cost_usd: float
    baseline_cost_usd: float
    drift_pct: float
    is_alert: bool
    week_of: str = ""

    def __post_init__(self) -> None:
        if not self.week_of:
            self.week_of = datetime.now(timezone.utc).strftime("%Y-W%W")


class CostMonitor:
    """Monitors inference costs and detects spending drift."""

    DRIFT_THRESHOLD = 0.15  # 15%

    def __init__(
        self,
        fs: BuildFilesystemInit,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        inference_client: Any,
    ) -> None:
        self._fs = fs
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log
        self._inference = inference_client

    # ------------------------------------------------------------------
    # Daily check
    # ------------------------------------------------------------------

    def run_daily_check(self) -> CostCheckResult:
        """Run daily cost check and alert if drift > 15%."""
        usage = self._inference.get_usage()
        total_cost = usage.get("total_cost_usd", 0.0)

        baseline = self.calculate_baseline()

        if baseline > 0:
            drift_pct = abs(total_cost - baseline) / baseline
        else:
            drift_pct = 0.0

        is_alert = drift_pct > self.DRIFT_THRESHOLD

        # Write weekly cost record
        history_path = self._fs.get_inference_history_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        week_record = {
            "week_of": datetime.now(timezone.utc).strftime("%Y-W%W"),
            "total_cost_usd": total_cost,
            "total_tokens": usage.get("total_tokens", 0),
            "cost_by_model": usage.get("cost_by_model", {}),
            "calls_by_data_type": usage.get("calls_by_data_type", {}),
            "baseline_cost_usd": baseline,
            "drift_pct": round(drift_pct, 4),
        }
        with history_path.open("a") as f:
            f.write(json.dumps(week_record) + "\n")

        # Write cost alerts log if alert triggered
        if is_alert:
            alerts_path = self._fs.BASE / "logs" / "cost-alerts.log"
            alerts_path.parent.mkdir(parents=True, exist_ok=True)
            with alerts_path.open("a") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "total_cost_usd": total_cost,
                            "baseline_cost_usd": baseline,
                            "drift_pct": round(drift_pct, 4),
                            "alert": True,
                        }
                    )
                    + "\n"
                )

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="cost_daily_check",
                entity_id="cost-monitoring",
                outcome="alert" if is_alert else "ok",
                details={
                    "total_cost": total_cost,
                    "baseline": baseline,
                    "drift_pct": round(drift_pct, 4),
                },
            )
        )

        return CostCheckResult(
            total_cost_usd=total_cost,
            baseline_cost_usd=baseline,
            drift_pct=drift_pct,
            is_alert=is_alert,
        )

    # ------------------------------------------------------------------
    # Baseline calculation
    # ------------------------------------------------------------------

    def calculate_baseline(self) -> float:
        """Calculate baseline from 4-week inference history."""
        history_path = self._fs.get_inference_history_path()
        if not history_path.exists():
            return 0.0

        costs: list[float] = []
        with history_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    cost = record.get("total_cost_usd", 0.0)
                    if cost > 0:
                        costs.append(cost)
                except (json.JSONDecodeError, KeyError):
                    continue

        # Use last 4 weeks
        last_4 = costs[-4:] if len(costs) >= 4 else costs
        if not last_4:
            return 0.0

        return sum(last_4) / len(last_4)

    # ------------------------------------------------------------------
    # Cost per user
    # ------------------------------------------------------------------

    def get_cost_per_user(self, budget_limit: float) -> dict[str, Any] | None:
        """Get cost breakdown per user. Returns None if Analytics unavailable."""
        if self._inference is None:
            return None

        try:
            usage = self._inference.get_usage()
            if not usage or "total_cost_usd" not in usage:
                return None
        except (AttributeError, TypeError):
            return None

        # Would need Analytics Claw data for per-user breakdown
        # Since that integration isn't wired, return None
        return None
