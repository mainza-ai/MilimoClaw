#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Cost Monitor

Tracks inference API costs daily and alerts on significant drift.

Reads usage from inference provider APIs.
Compares against 4-week rolling baseline.
Queues War Room REVIEW if drift > 15%.
Updates context/costs/inference-weekly.json.
Appends to context/costs/inference-history.jsonl.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .signal_dispatcher import BuildSignalDispatcher

logger = logging.getLogger("milimo.build")

ALERT_DRIFT_THRESHOLD = 0.15  # 15%


@dataclass
class UsageData:
    """Inference usage data for a period."""

    week_of: str
    total_tokens: int
    total_cost_usd: float
    cost_by_model: dict[str, float]
    calls_by_data_type: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "week_of": self.week_of,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "cost_by_model": self.cost_by_model,
            "calls_by_data_type": self.calls_by_data_type,
        }


@dataclass
class DriftResult:
    """Result of cost drift analysis."""

    current_cost: float
    baseline_cost: float
    drift_pct: float
    is_alert: bool
    cost_per_user: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_cost": self.current_cost,
            "baseline_cost": self.baseline_cost,
            "drift_pct": self.drift_pct,
            "is_alert": self.is_alert,
            "cost_per_user": self.cost_per_user,
        }


class CostMonitor:
    """
    Tracks inference API costs daily and alerts on significant drift.

    Reads usage from inference provider APIs.
    Compares against 4-week rolling baseline.
    Queues War Room REVIEW if drift > 15%.
    Updates context/costs/inference-weekly.json.
    Appends to context/costs/inference-history.jsonl.
    """

    ALERT_DRIFT_THRESHOLD = 0.15

    def __init__(
        self,
        fs: BuildFilesystemInit,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        inference_client: Any | None = None,
    ):
        self._fs = fs
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log
        self._inference = inference_client

    def run_daily_check(self) -> DriftResult:
        usage = self.fetch_api_usage()

        baseline = self.calculate_baseline()

        cost_per_user = self.get_cost_per_user(usage.total_cost_usd)

        if baseline > 0:
            drift_pct = (usage.total_cost_usd - baseline) / baseline
        else:
            drift_pct = 0.0

        is_alert = drift_pct > self.ALERT_DRIFT_THRESHOLD

        weekly_path = self._fs.get_inference_weekly_path()
        weekly_data = {
            "week_of": usage.week_of,
            "total_cost_usd": usage.total_cost_usd,
            "cost_per_user": cost_per_user or 0.0,
            "baseline_cost_usd": baseline,
            "drift_pct": round(drift_pct * 100, 2),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self._fs.atomic_write_json(weekly_path, weekly_data)

        history_path = self._fs.get_inference_history_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a") as f:
            f.write(json.dumps(usage.to_dict()) + "\n")

        if is_alert:
            self.queue_cost_alert(DriftResult(
                current_cost=usage.total_cost_usd,
                baseline_cost=baseline,
                drift_pct=drift_pct,
                is_alert=True,
                cost_per_user=cost_per_user,
            ))

        self._log.append(self._create_log_entry(
            "cost_monitoring_pass",
            usage.week_of,
            "alert" if is_alert else "normal",
            {
                "total_cost": usage.total_cost_usd,
                "baseline": baseline,
                "drift_pct": round(drift_pct * 100, 2),
            },
        ))

        return DriftResult(
            current_cost=usage.total_cost_usd,
            baseline_cost=baseline,
            drift_pct=drift_pct,
            is_alert=is_alert,
            cost_per_user=cost_per_user,
        )

    def fetch_api_usage(self) -> UsageData:
        week_of = datetime.now(timezone.utc).strftime("%Y-W%W")

        if self._inference and hasattr(self._inference, "get_usage"):
            try:
                raw = self._inference.get_usage()
                return UsageData(
                    week_of=week_of,
                    total_tokens=raw.get("total_tokens", 0),
                    total_cost_usd=raw.get("total_cost_usd", 0.0),
                    cost_by_model=raw.get("cost_by_model", {}),
                    calls_by_data_type=raw.get("calls_by_data_type", {}),
                )
            except Exception as e:
                logger.warning("Failed to fetch inference usage: %s", e)

        return UsageData(
            week_of=week_of,
            total_tokens=0,
            total_cost_usd=0.0,
            cost_by_model={},
            calls_by_data_type={},
        )

    def calculate_baseline(self) -> float:
        history_path = self._fs.get_inference_history_path()
        if not history_path.exists():
            return 0.0

        costs: list[float] = []
        try:
            with history_path.open("r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        costs.append(data.get("total_cost_usd", 0))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return 0.0

        if len(costs) < 2:
            return 0.0

        recent_costs = costs[-4:]
        return sum(recent_costs) / len(recent_costs)

    def queue_cost_alert(self, drift: DriftResult) -> None:
        self._approval.queue_cost_alert_review(
            drift_pct=drift.drift_pct * 100,
            current_cost=drift.current_cost,
            baseline_cost=drift.baseline_cost,
            cost_per_user=drift.cost_per_user or 0.0,
        )

        alerts_path = self._fs.get_cost_alerts_log_path()
        alerts_path.parent.mkdir(parents=True, exist_ok=True)

        alert_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "drift_pct": drift.drift_pct,
            "current_cost": drift.current_cost,
            "baseline_cost": drift.baseline_cost,
            "cost_per_user": drift.cost_per_user,
        }

        with alerts_path.open("a") as f:
            f.write(json.dumps(alert_entry) + "\n")

        self._log.append(self._create_log_entry(
            "cost_alert_queued",
            "weekly",
            "review",
            {"drift_pct": round(drift.drift_pct * 100, 2)},
        ))

    def get_cost_per_user(self, total_cost: float) -> float | None:
        signals = self._dispatcher.get_retention_signals()
        if signals and "user_count" in signals:
            return total_cost / signals["user_count"]

        weekly_path = self._fs._base / "context" / "sprint" / "retention-signals.json"
        data = self._fs.read_json(weekly_path)
        if data and "signals" in data and "user_count" in data["signals"]:
            return total_cost / data["signals"]["user_count"]

        return None

    def _create_log_entry(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        details: dict[str, Any],
    ):
        from .build_init import BuildLogEntry

        return BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )
