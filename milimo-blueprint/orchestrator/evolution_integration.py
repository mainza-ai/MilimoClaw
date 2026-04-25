# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Evolution Cycle Scheduler Integration

Schedules and triggers the weekly evolution cycle for all claws.
Replaces mock inference with the real NvidiaInferenceClient.
Reads performance metrics written by each claw's MetricsCollector.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .evolution_cycle import (
    EvolutionCycle,
    EvolutionScheduler,
    EvolutionConfig,
    CycleResult,
)
from .inference_client import NvidiaInferenceClient
from .metrics_collector import MetricsCollector

logger = logging.getLogger("milimo.evolution_scheduler_integration")


class EvolutionIntegration:
    """
    Integrates the Evolution Cycle with the rest of the Milimo Claw system.

    - Registers evolution cycles for all 6 claws
    - Uses real inference client (not mock)
    - Reads performance metrics from MetricsCollector
    - Runs on a configurable schedule (default: weekly)
    - Triggers immediately on startup if data is available
    """

    def __init__(
        self,
        squad_id: str,
        blueprint_dir: Path | None = None,
        inference_client: Any | None = None,
        interval_days: int = 7,
    ) -> None:
        self.squad_id = squad_id
        self.blueprint_dir = blueprint_dir or Path(__file__).parent.parent
        self.inference_client = inference_client or NvidiaInferenceClient(
            api_key=os.environ.get("NVIDIA_API_KEY"),
            api_base=os.environ.get("NVIDIA_API_BASE"),
        )
        self.interval_days = interval_days
        self.scheduler = EvolutionScheduler()
        self._running = False
        self._timer: threading.Timer | None = None
        self._history: list[CycleResult] = []

    def register_claw(self, claw_role: str, log_dir: Path | None = None) -> None:
        """Register an evolution cycle for a specific claw role."""
        config = EvolutionConfig(
            cycle_interval_days=self.interval_days,
            window_days=7,
            minimum_actions=20,
            cross_signal_lookback_days=14,
            min_confidence=0.6,
            max_patterns=5,
            backtest_window_weeks=4,
            min_improvement_percent=5.0,
            max_tools_per_claw=30,
            require_proposal_approval=True,  # Evolution changes need approval
            notify_war_room=True,
        )

        cycle = EvolutionCycle(
            squad_id=self.squad_id,
            claw_role=claw_role,
            blueprint_dir=self.blueprint_dir,
            log_dir=str(log_dir) if log_dir else None,
            config=config,
        )
        self.scheduler.register(cycle)
        logger.info("Registered evolution cycle for %s claw", claw_role)

    def start(self) -> None:
        """Start the evolution scheduler with periodic triggering."""
        if self._running:
            logger.warning("Evolution integration already running")
            return

        self._running = True

        # Register all 6 claws by default
        for role in ["build", "content", "ops", "analytics", "finance", "assistant"]:
            self.register_claw(role)

        # Check if any cycles should run immediately (missed during downtime)
        self._check_missed_cycles()

        # Schedule next run
        self._schedule_next_run()

        logger.info(
            "Evolution integration started (interval: %d days)", self.interval_days
        )

    def stop(self) -> None:
        """Stop the evolution scheduler."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Evolution integration stopped")

    def trigger_now(
        self, claw_role: str | None = None, dry_run: bool = False
    ) -> list[CycleResult]:
        """Manually trigger evolution cycles."""
        results = self.scheduler.trigger(claw_role=claw_role, dry_run=dry_run)
        self._history.extend(results)

        for result in results:
            if result.stage_reached == "deploy":
                logger.info(
                    "Evolution: deployed tool '%s' for %s claw (+%.1f%%)",
                    result.proposal.tool_name if result.proposal else "unknown",
                    result.claw_role,
                    result.tool_deployed.performance_delta
                    if result.tool_deployed
                    else 0,
                )
            elif result.skipped_reason:
                logger.debug(
                    "Evolution: %s cycle skipped at %s stage: %s",
                    result.claw_role,
                    result.stage_reached,
                    result.skipped_reason,
                )

        return results

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get performance metrics summary for all claws."""
        summary = {}
        metrics_base = Path.home() / ".milimo" / "metrics"

        for role in ["build", "content", "ops", "analytics", "finance", "assistant"]:
            collector = MetricsCollector(
                claw_role=role, metrics_dir=metrics_base / role
            )
            summary[role] = collector.get_summary(
                lookback_hours=self.interval_days * 24
            )

        return summary

    def _check_missed_cycles(self) -> None:
        """Check if evolution cycles were missed during downtime and run them."""
        history = self.scheduler.get_history(limit=1)
        if not history:
            # Never run — trigger immediately (dry run first)
            logger.info("No evolution history found — running initial dry run")
            results = self.trigger_now(dry_run=True)
            if results:
                logger.info(
                    "Initial evolution dry run complete for %d claws", len(results)
                )
        else:
            last_run = history[-1].timestamp
            try:
                last_run_time = datetime.fromisoformat(last_run)
                if (datetime.now(timezone.utc) - last_run_time) > timedelta(
                    days=self.interval_days + 1
                ):
                    logger.info("Missed evolution cycle detected — triggering now")
                    self.trigger_now()
            except (ValueError, TypeError):
                pass

    def _schedule_next_run(self) -> None:
        """Schedule the next evolution cycle run."""
        if not self._running:
            return

        interval_seconds = self.interval_days * 86400

        def run_and_reschedule() -> None:
            if not self._running:
                return

            logger.info("Running scheduled evolution cycle")
            results = self.trigger_now()
            self._history.extend(results)

            # Reschedule
            if self._running:
                self._schedule_next_run()

        self._timer = threading.Timer(interval_seconds, run_and_reschedule)
        self._timer.daemon = True
        self._timer.start()

        logger.info("Next evolution cycle scheduled in %d days", self.interval_days)

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the evolution integration."""
        return {
            "running": self._running,
            "squad_id": self.squad_id,
            "interval_days": self.interval_days,
            "registered_claws": list(self.scheduler._cycles.keys()),
            "total_cycles_run": len(self._history),
            "last_cycle": self._history[-1].to_dict() if self._history else None,
            "scheduler_status": self.scheduler.get_status(),
        }
