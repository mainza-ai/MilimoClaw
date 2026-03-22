#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Build Scheduler

Orchestrates all scheduled autonomous actions for the Build Claw.

Schedule:
Every 30 min — Error monitoring pass
Daily — Cost monitoring check
Monday 08:00 — Dependency security audit
Friday 17:00 — Weekly devlog generation + shipping_summary
Sunday 02:00 — Self-evolution cycle (shared evolution_cycle.py)

Uses threading.Timer. No cron. No APScheduler. Only stdlib.
Checks for missed jobs on startup.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .build_init import BuildOperationalLog
    from .cost_monitor import CostMonitor
    from .dependency_auditor import DependencyAuditor
    from .doc_maintainer import DocMaintainer
    from .error_monitor import ErrorMonitor

logger = logging.getLogger("milimo.build")

ERROR_MONITOR_INTERVAL = 30 * 60  # 30 minutes
COST_MONITOR_INTERVAL = 24 * 60 * 60  # 24 hours
DEPENDENCY_AUDIT_INTERVAL = 7 * 24 * 60 * 60  # 7 days
DEVLOG_INTERVAL = 7 * 24 * 60 * 60  # 7 days


class BuildScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Build Claw.

    Schedule:
    Every 30 min — Error monitoring pass
    Daily — Cost monitoring check
    Monday 08:00 — Dependency security audit
    Friday 17:00 — Weekly devlog generation + shipping_summary
    Sunday 02:00 — Self-evolution cycle (shared evolution_cycle.py)

    Uses threading.Timer. No cron. No APScheduler. Only stdlib.
    Checks for missed jobs on startup.
    """

    def __init__(
        self,
        error_monitor: ErrorMonitor,
        cost_monitor: CostMonitor,
        dependency_auditor: DependencyAuditor,
        doc_maintainer: DocMaintainer,
        operational_log: BuildOperationalLog,
    ):
        self._error_monitor = error_monitor
        self._cost_monitor = cost_monitor
        self._dependency_auditor = dependency_auditor
        self._doc_maintainer = doc_maintainer
        self._log = operational_log

        self._running = False
        self._timers: list[threading.Timer] = []

    def start(self) -> None:
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        logger.info("Build scheduler starting")

        self._check_missed_jobs()

        self._schedule_error_monitoring()
        self._schedule_cost_monitoring()
        self._schedule_dependency_audit()
        self._schedule_devlog_generation()

        self._log.append(self._create_log_entry(
            "scheduler_started",
            "scheduler",
            "success",
            {},
        ))

    def stop(self) -> None:
        self._running = False
        logger.info("Build scheduler stopping")

        for timer in self._timers:
            timer.cancel()

        self._timers.clear()

        self._log.append(self._create_log_entry(
            "scheduler_stopped",
            "scheduler",
            "success",
            {},
        ))

    def _run_error_monitoring(self) -> None:
        if not self._running:
            return

        try:
            logger.debug("Running error monitoring pass")
            self._error_monitor.run_monitoring_pass()
        except Exception as e:
            logger.error("Error monitoring failed: %s", e)

        if self._running:
            self._schedule_error_monitoring()

    def _run_cost_monitoring(self) -> None:
        if not self._running:
            return

        try:
            logger.debug("Running cost monitoring check")
            self._cost_monitor.run_daily_check()
        except Exception as e:
            logger.error("Cost monitoring failed: %s", e)

        if self._running:
            self._schedule_cost_monitoring()

    def _run_dependency_audit(self) -> None:
        if not self._running:
            return

        now = datetime.now(timezone.utc)
        if now.weekday() != 0:
            logger.debug("Skipping dependency audit - not Monday")
            if self._running:
                self._schedule_dependency_audit()
            return

        if now.hour < 8:
            logger.debug("Skipping dependency audit - before 08:00")
            if self._running:
                self._schedule_dependency_audit()
            return

        try:
            logger.info("Running dependency security audit")
            self._dependency_auditor.run_audit()
        except Exception as e:
            logger.error("Dependency audit failed: %s", e)

        if self._running:
            self._schedule_dependency_audit()

    def _run_devlog_generation(self) -> None:
        if not self._running:
            return

        now = datetime.now(timezone.utc)
        if now.weekday() != 4:
            logger.debug("Skipping devlog - not Friday")
            if self._running:
                self._schedule_devlog_generation()
            return

        if now.hour < 17:
            logger.debug("Skipping devlog - before 17:00")
            if self._running:
                self._schedule_devlog_generation()
            return

        try:
            logger.info("Generating weekly devlog")
            self._doc_maintainer.generate_weekly_devlog()
        except Exception as e:
            logger.error("Devlog generation failed: %s", e)

        if self._running:
            self._schedule_devlog_generation()

    def _check_missed_jobs(self) -> None:
        now = datetime.now(timezone.utc)

        last_error = self._log.get_last_run_time("error_monitoring_pass")
        if last_error:
            last_time = datetime.fromisoformat(last_error)
            elapsed = (now - last_time).total_seconds()
            if elapsed > ERROR_MONITOR_INTERVAL + 300:
                logger.info("Missed error monitoring, running now")
                try:
                    self._error_monitor.run_monitoring_pass()
                except Exception as e:
                    logger.error("Missed error monitoring failed: %s", e)

        last_cost = self._log.get_last_run_time("cost_monitoring_pass")
        if last_cost:
            last_time = datetime.fromisoformat(last_cost)
            elapsed = (now - last_time).total_seconds()
            if elapsed > COST_MONITOR_INTERVAL + 3600:
                logger.info("Missed cost monitoring, running now")
                try:
                    self._cost_monitor.run_daily_check()
                except Exception as e:
                    logger.error("Missed cost monitoring failed: %s", e)

        last_audit = self._log.get_last_run_time("dependency_audit_complete")
        if last_audit:
            last_time = datetime.fromisoformat(last_audit)
            elapsed = (now - last_time).total_seconds()
            if elapsed > DEPENDENCY_AUDIT_INTERVAL + 86400:
                logger.info("Missed dependency audit, running now")
                try:
                    self._dependency_auditor.run_audit()
                except Exception as e:
                    logger.error("Missed dependency audit failed: %s", e)

    def _schedule_error_monitoring(self) -> None:
        if not self._running:
            return

        timer = threading.Timer(ERROR_MONITOR_INTERVAL, self._run_error_monitoring)
        self._timers.append(timer)
        timer.daemon = True
        timer.start()

    def _schedule_cost_monitoring(self) -> None:
        if not self._running:
            return

        timer = threading.Timer(COST_MONITOR_INTERVAL, self._run_cost_monitoring)
        self._timers.append(timer)
        timer.daemon = True
        timer.start()

    def _schedule_dependency_audit(self) -> None:
        if not self._running:
            return

        seconds_until_monday_8am = self._seconds_until(8, 0, target_weekday=0)
        timer = threading.Timer(seconds_until_monday_8am, self._run_dependency_audit)
        self._timers.append(timer)
        timer.daemon = True
        timer.start()

    def _schedule_devlog_generation(self) -> None:
        if not self._running:
            return

        seconds_until_friday_5pm = self._seconds_until(17, 0, target_weekday=4)
        timer = threading.Timer(seconds_until_friday_5pm, self._run_devlog_generation)
        self._timers.append(timer)
        timer.daemon = True
        timer.start()

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None,
    ) -> float:
        now = datetime.now(timezone.utc)

        target = now.replace(
            hour=target_hour,
            minute=target_minute,
            second=0,
            microsecond=0,
        )

        if target_weekday is not None:
            days_ahead = target_weekday - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            elif days_ahead == 0 and now.hour >= target_hour:
                days_ahead = 7
            target = target.replace(day=now.day + days_ahead)
        else:
            if target <= now:
                target = target.replace(day=now.day + 1)

        delta = target - now
        return delta.total_seconds()

    def _is_monday(self) -> bool:
        return datetime.now(timezone.utc).weekday() == 0

    def _is_friday(self) -> bool:
        return datetime.now(timezone.utc).weekday() == 4

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
