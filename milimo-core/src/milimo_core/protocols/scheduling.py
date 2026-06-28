# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Scheduling Protocol — Profile-agnostic interface for scheduled jobs.

Concrete implementations are profile-specific:
- OpenClaw profile: uses Build Claw scheduler + evolution_cycle.py (Python threading.Timer)
- Hermes profile: uses native cronjob (durable, survives interrupts)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass
class ScheduledJob:
    """Profile-agnostic scheduled job descriptor."""
    name: str
    cron_expression: str
    handler: Callable[[], Any]
    enabled: bool = True
    last_run: Optional[datetime] = field(default=None, repr=False)
    next_run: Optional[datetime] = field(default=None, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)


class SchedulerInterface(ABC):
    """
    Profile-agnostic interface for scheduling recurring jobs.

    OpenClaw profile implements via threading.Timer (evolution_cycle.py).
    Hermes profile implements via native cronjob.
    """

    @abstractmethod
    def schedule_job(self, job: ScheduledJob) -> None:
        """Register a recurring job."""
        ...

    @abstractmethod
    def unschedule_job(self, job_name: str) -> None:
        """Remove a recurring job."""
        ...

    @abstractmethod
    def get_due_jobs(self) -> list[ScheduledJob]:
        """Get jobs that are due to run now."""
        ...

    @abstractmethod
    def start(self) -> None:
        """Start the scheduler."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the scheduler."""
        ...

    @abstractmethod
    def get_job(self, job_name: str) -> Optional[ScheduledJob]:
        """Get a job by name."""
        ...


__all__ = [
    "ScheduledJob",
    "SchedulerInterface",
]
