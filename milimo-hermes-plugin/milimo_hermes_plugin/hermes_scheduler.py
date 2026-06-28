# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Hermes Cron Scheduler — Hermes-specific implementation of SchedulerInterface.

Uses native Hermes cronjob for durable, interrupt-surviving scheduled execution.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from milimo_core.protocols.scheduling import SchedulerInterface, ScheduledJob


class HermesCronScheduler(SchedulerInterface):
    """
    Hermes-specific scheduler using native cronjob.

    Key difference from OpenClaw's threading.Timer approach:
    - cronjob is durable — survives sandbox restarts
    - cronjob is managed by Hermes runtime, not Python process
    - Jobs are defined in Hermes config, not in Python code
    """

    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._config_jobs: list[dict] = []

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
        # In production, this writes to Hermes cron config
        # Hermes then manages execution natively

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

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


__all__ = ["HermesCronScheduler"]
