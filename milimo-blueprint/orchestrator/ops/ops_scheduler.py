# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Scheduler

Orchestrates all scheduled autonomous actions for the Ops Claw.

Schedule:
Daily 09:00 — Deadline risk check for all active projects
Daily 09:00 — Inquiry staleness check (24h/48h urgency flags)
Weekly Sunday 02:00 — Client health scoring for all active clients
On startup — Check for missed jobs

Uses threading.Timer. No cron. No APScheduler. Only stdlib.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Any

from .ops_init import OpsFilesystemInit, OpsOperationalLog, OpsLogEntry

logger = logging.getLogger("milimo.ops")


class OpsScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Ops Claw.

    Schedule:
    Daily 09:00 — Deadline risk check for all active projects
    Daily 09:00 — Inquiry staleness check (24h/48h urgency flags)
    Weekly Sunday 02:00 — Client health scoring for all active clients
    On startup — Check for missed jobs

    Uses threading.Timer. No cron. No APScheduler. Only stdlib.
    """

    DAILY_HOUR = 9
    DAILY_MINUTE = 0
    WEEKLY_HOUR = 2
    WEEKLY_MINUTE = 0
    WEEKLY_DAY = 6  # Sunday

    DAILY_CHECK_INTERVAL_HOURS = 36
    WEEKLY_CHECK_INTERVAL_DAYS = 8

    def __init__(
        self,
        project_manager: Any,
        intake_manager: Any,
        health_scorer: Any,
        comms_manager: Any,
        operational_log: OpsOperationalLog,
        fs: OpsFilesystemInit,
    ):
        self._project_manager = project_manager
        self._intake_manager = intake_manager
        self._health_scorer = health_scorer
        self._comms_manager = comms_manager
        self._operational_log = operational_log
        self._fs = fs

        self._timers: list[threading.Timer] = []
        self._running = False
        self._lock = threading.Lock()

        self._last_daily_check: datetime | None = None
        self._last_weekly_check: datetime | None = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return

            self._running = True

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="scheduler_started",
                entity_id="ops_scheduler",
                outcome="success",
                details={},
            )
        )

        self._check_missed_jobs()
        self._schedule_daily_deadline_check()
        self._schedule_weekly_health_scoring()

        logger.info("Ops scheduler started")

    def stop(self) -> None:
        with self._lock:
            self._running = False

            for timer in self._timers:
                timer.cancel()
            self._timers.clear()

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="scheduler_stopped",
                entity_id="ops_scheduler",
                outcome="success",
                details={},
            )
        )

        logger.info("Ops scheduler stopped")

    def _schedule_daily_deadline_check(self) -> None:
        if not self._running:
            return

        seconds_until = self._seconds_until(self.DAILY_HOUR, self.DAILY_MINUTE)

        if seconds_until < 60:
            seconds_until += 86400

        timer = threading.Timer(seconds_until, self._run_daily_deadline_check)
        timer.daemon = True

        with self._lock:
            if self._running:
                self._timers.append(timer)
                timer.start()
                logger.debug(
                    "Scheduled daily deadline check in %d seconds", seconds_until
                )

    def _schedule_weekly_health_scoring(self) -> None:
        if not self._running:
            return

        seconds_until = self._seconds_until(
            self.WEEKLY_HOUR,
            self.WEEKLY_MINUTE,
            target_weekday=self.WEEKLY_DAY,
        )

        if seconds_until < 60:
            seconds_until += 7 * 86400

        timer = threading.Timer(seconds_until, self._run_weekly_health_scoring)
        timer.daemon = True

        with self._lock:
            if self._running:
                self._timers.append(timer)
                timer.start()
                logger.debug(
                    "Scheduled weekly health scoring in %d seconds", seconds_until
                )

    def _run_daily_deadline_check(self) -> None:
        if not self._running:
            return

        start_time = datetime.now(timezone.utc)
        logger.info("Running daily deadline check")

        try:
            if self._project_manager:
                risks = self._project_manager.check_all_deadlines()
                logger.info("Found %d deadline risks", len(risks))

            if self._intake_manager:
                self._intake_manager._check_inquiry_staleness()

            self._last_daily_check = datetime.now(timezone.utc)

            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="daily_check_completed",
                    entity_id="ops_scheduler",
                    outcome="success",
                    details={
                        "duration_seconds": (
                            datetime.now(timezone.utc) - start_time
                        ).total_seconds(),
                    },
                )
            )

        except Exception as e:
            logger.error("Daily deadline check failed: %s", e)
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="daily_check_failed",
                    entity_id="ops_scheduler",
                    outcome="failed",
                    details={"error": str(e)},
                )
            )

        self._schedule_daily_deadline_check()

    def _run_weekly_health_scoring(self) -> None:
        if not self._running:
            return

        start_time = datetime.now(timezone.utc)
        logger.info("Running weekly health scoring")
        scores: list[Any] = []

        try:
            if self._health_scorer:
                scores = self._health_scorer.score_all_active_clients()
                logger.info("Scored %d clients", len(scores))

            self._last_weekly_check = datetime.now(timezone.utc)

            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="weekly_health_scoring_completed",
                    entity_id="ops_scheduler",
                    outcome="success",
                    details={
                        "clients_scored": len(scores),
                        "duration_seconds": (
                            datetime.now(timezone.utc) - start_time
                        ).total_seconds(),
                    },
                )
            )

        except Exception as e:
            logger.error("Weekly health scoring failed: %s", e)
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="weekly_health_scoring_failed",
                    entity_id="ops_scheduler",
                    outcome="failed",
                    details={"error": str(e)},
                )
            )

        self._schedule_weekly_health_scoring()

    def _check_missed_jobs(self) -> None:
        last_daily = self._get_last_run_timestamp("daily_check_completed")
        last_weekly = self._get_last_run_timestamp("weekly_health_scoring_completed")

        now = datetime.now(timezone.utc)

        if last_daily:
            hours_since_daily = (now - last_daily).total_seconds() / 3600
            if hours_since_daily > self.DAILY_CHECK_INTERVAL_HOURS:
                logger.info("Missed daily check detected, running now")
                self._run_daily_deadline_check()
        else:
            logger.info("No previous daily check found, running now")
            threading.Timer(5, self._run_daily_deadline_check).start()

        if last_weekly:
            days_since_weekly = (now - last_weekly).total_seconds() / 86400
            if days_since_weekly > self.WEEKLY_CHECK_INTERVAL_DAYS:
                logger.info("Missed weekly health scoring detected, running now")
                self._run_weekly_health_scoring()
        else:
            logger.info("No previous weekly check found, running now")
            threading.Timer(10, self._run_weekly_health_scoring).start()

    def _get_last_run_timestamp(self, action_type: str) -> datetime | None:
        entries = self._operational_log.read_recent(days=30, action_type=action_type)
        if not entries:
            return None

        latest = entries[-1]
        try:
            return datetime.fromisoformat(latest.timestamp)
        except ValueError:
            return None

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None,
    ) -> float:
        now = datetime.now(timezone.utc)

        if target_weekday is not None:
            days_ahead = target_weekday - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            elif days_ahead == 0:
                target_time = now.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )
                if now >= target_time:
                    days_ahead = 7

            target = now + timedelta(days=days_ahead)
            target = target.replace(
                hour=target_hour, minute=target_minute, second=0, microsecond=0
            )
        else:
            target = now.replace(
                hour=target_hour, minute=target_minute, second=0, microsecond=0
            )

            if now >= target:
                target += timedelta(days=1)

        delta = target - now
        return delta.total_seconds()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def get_next_daily_check(self) -> datetime | None:
        seconds = self._seconds_until(self.DAILY_HOUR, self.DAILY_MINUTE)
        return datetime.now(timezone.utc) + timedelta(seconds=seconds)

    def get_next_weekly_check(self) -> datetime | None:
        seconds = self._seconds_until(
            self.WEEKLY_HOUR,
            self.WEEKLY_MINUTE,
            target_weekday=self.WEEKLY_DAY,
        )
        return datetime.now(timezone.utc) + timedelta(seconds=seconds)
