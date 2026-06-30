# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Hermes Cron Scheduler — Hermes-specific implementation of SchedulerInterface.

Uses native Hermes cronjob for durable, interrupt-surviving scheduled execution.
Integrates with milimo-core EvolutionScheduler for evolution cycle, tool backtest,
and hold queue review jobs.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from milimo_core.protocols.scheduling import SchedulerInterface, ScheduledJob
from milimo_core import EvolutionScheduler, EvolutionSchedulerConfig


class HermesCronScheduler(SchedulerInterface):
    """
    Hermes-specific scheduler using native cronjob.

    Key difference from OpenClaw's threading.Timer approach:
    - cronjob is durable — survives sandbox restarts
    - cronjob is managed by Hermes runtime, not Python process
    - Jobs are defined in Hermes config, not in Python code

    Integrates with milimo-core EvolutionScheduler for:
    - evolution_cycle: Weekly evolution cycle (Sunday 2AM)
    - tool_backtest: Tool backtest cycle (every 6 hours)
    - hold_queue_review: HOLD queue review (every 4 hours)
    """

    def __init__(self, config: EvolutionSchedulerConfig | None = None):
        self._evolution_scheduler = EvolutionScheduler(config)
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._config_jobs: list[dict] = []

        # Register the three core jobs from milimo-compatibility.json
        self._register_core_jobs()

    def _register_core_jobs(self) -> None:
        """Register the three core cron jobs."""
        core_jobs = [
            ScheduledJob(
                name="evolution_cycle",
                cron_expression="0 2 * * 0",  # Sunday 2AM
                handler=self._run_evolution_cycle,
                enabled=True,
                metadata={"handler_name": "evolution_cycle"},
            ),
            ScheduledJob(
                name="tool_backtest",
                cron_expression="0 */6 * * *",  # Every 6 hours
                handler=self._run_tool_backtest,
                enabled=True,
                metadata={"handler_name": "tool_backtest"},
            ),
            ScheduledJob(
                name="hold_queue_review",
                cron_expression="0 */4 * * *",  # Every 4 hours
                handler=self._run_hold_queue_review,
                enabled=True,
                metadata={"handler_name": "hold_queue_review"},
            ),
        ]

        for job in core_jobs:
            self.schedule_job(job)

    def schedule_job(self, job: ScheduledJob) -> None:
        """Register a recurring job for Hermes cron."""
        self._jobs[job.name] = job
        # Build cron config entry
        self._config_jobs.append({
            "name": job.name,
            "schedule": job.cron_expression,
            "handler": job.metadata.get("handler_name", job.name),
            "enabled": job.enabled,
        })
        # Calculate next run
        job.next_run = self._calculate_next_run(job.cron_expression)

    def unschedule_job(self, job_name: str) -> None:
        """Remove a recurring job."""
        if job_name in self._jobs:
            del self._jobs[job_name]
        self._config_jobs = [j for j in self._config_jobs if j["name"] != job_name]

    def get_due_jobs(self) -> list[ScheduledJob]:
        """Get jobs that are due to run now (for polling fallback)."""
        now = datetime.now()
        return [
            job for job in self._jobs.values()
            if job.enabled and job.next_run and job.next_run <= now
        ]

    def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        self._evolution_scheduler.start()
        # In production, this writes to Hermes cron config
        # Hermes then manages execution natively

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        self._evolution_scheduler.stop()

    def get_job(self, job_name: str) -> Optional[ScheduledJob]:
        """Get a job by name."""
        return self._jobs.get(job_name)

    def get_cron_config(self) -> list[dict]:
        """Get the cron configuration for Hermes."""
        return self._config_jobs

    @staticmethod
    def _calculate_next_run(cron_expression: str) -> datetime:
        """Calculate next run time from cron expression."""
        # Simplified - in production use croniter
        from datetime import timedelta
        return datetime.now() + timedelta(minutes=1)

    # ---- Handler methods for the three core jobs ----

    async def _run_evolution_cycle(self) -> list[dict[str, Any]]:
        """Run evolution cycle for all claws."""
        return await self._evolution_scheduler._run_evolution_cycle()

    async def _run_tool_backtest(self) -> list[dict[str, Any]]:
        """Run tool backtest for all deployed evolved tools."""
        return await self._evolution_scheduler._run_tool_backtest()

    async def _run_hold_queue_review(self) -> list[dict[str, Any]]:
        """Run HOLD queue review."""
        return await self._evolution_scheduler._run_hold_queue_review()

    # ---- Public API ----

    def get_evolution_scheduler(self) -> EvolutionScheduler:
        """Get the underlying EvolutionScheduler instance."""
        return self._evolution_scheduler

    def get_status(self) -> dict[str, Any]:
        """Get combined status."""
        evo_status = self._evolution_scheduler.get_status()
        return {
            "running": self._running,
            "registered_jobs": list(self._jobs.keys()),
            "evolution": evo_status,
        }


# ---- Synchronous wrappers for Hermes cronjob handlers ----

def run_evolution_cycle_handler(config: EvolutionSchedulerConfig | None = None) -> list[dict[str, Any]]:
    """Synchronous handler for Hermes cronjob: evolution_cycle."""
    scheduler = EvolutionScheduler(config)
    return asyncio.run(scheduler._run_evolution_cycle())


def run_tool_backtest_handler(config: EvolutionSchedulerConfig | None = None) -> list[dict[str, Any]]:
    """Synchronous handler for Hermes cronjob: tool_backtest."""
    scheduler = EvolutionScheduler(config)
    return asyncio.run(scheduler._run_tool_backtest())


def run_hold_queue_review_handler(config: EvolutionSchedulerConfig | None = None) -> list[dict[str, Any]]:
    """Synchronous handler for Hermes cronjob: hold_queue_review."""
    scheduler = EvolutionScheduler(config)
    return asyncio.run(scheduler._run_hold_queue_review())


__all__ = [
    "HermesCronScheduler",
    "run_evolution_cycle_handler",
    "run_tool_backtest_handler",
    "run_hold_queue_review_handler",
]
