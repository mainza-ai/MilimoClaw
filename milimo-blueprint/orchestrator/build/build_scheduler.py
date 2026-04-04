"""
Build Claw scheduler.

Timer-based scheduling for periodic monitoring tasks:
- Error monitoring every 30 minutes
- Cost monitoring daily
- Dependency audit every 7 days (Monday)
- Weekly devlog generation (Friday)

Enhancement: Self-rescheduling with missed-job recovery on startup.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from build.build_init import BuildOperationalLog, BuildLogEntry

logger = logging.getLogger(__name__)

# Monitoring intervals (in seconds)
ERROR_MONITOR_INTERVAL = 30 * 60  # 30 minutes
COST_MONITOR_INTERVAL = 24 * 60 * 60  # 24 hours
DEPENDENCY_AUDIT_INTERVAL = 7 * 24 * 60 * 60  # 7 days
DEVLOG_INTERVAL = 7 * 24 * 60 * 60  # 7 days


class BuildScheduler:
    """Timer-based scheduler for Build Claw periodic tasks."""

    def __init__(
        self,
        error_monitor: Any,
        cost_monitor: Any,
        dependency_auditor: Any,
        doc_maintainer: Any,
        operational_log: BuildOperationalLog,
    ) -> None:
        self._error_monitor = error_monitor
        self._cost_monitor = cost_monitor
        self._dependency_auditor = dependency_auditor
        self._doc_maintainer = doc_maintainer
        self._log = operational_log
        self._timers: list[threading.Timer] = []
        self._running = False

    def start(self) -> None:
        """Start all scheduled tasks with self-rescheduling timers."""
        self._running = True

        # Check for missed jobs on startup
        self._check_missed_jobs()

        # Error monitoring — every 30 minutes
        self._schedule_error_monitoring()

        # Cost monitoring — daily
        self._schedule_cost_monitoring()

        # Dependency audit — weekly (Monday)
        self._schedule_dependency_audit()

        # Devlog generation — weekly (Friday)
        self._schedule_devlog_generation()

        logger.info("BuildScheduler started with %d timers", len(self._timers))

    def stop(self) -> None:
        """Cancel all pending timers."""
        self._running = False
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()
        logger.info("BuildScheduler stopped, all timers cancelled")

    # ------------------------------------------------------------------
    # Error monitoring (every 30 min)
    # ------------------------------------------------------------------

    def _schedule_error_monitoring(self) -> None:
        if not self._running:
            return
        timer = threading.Timer(ERROR_MONITOR_INTERVAL, self._run_error_monitoring)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _run_error_monitoring(self) -> None:
        if not self._running:
            return
        try:
            self._error_monitor.run_error_check()
            self._log.append(BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="error_monitoring_pass",
                entity_id="monitoring",
                outcome="success",
                details={"interval_seconds": ERROR_MONITOR_INTERVAL},
            ))
        except Exception as exc:
            logger.error("Error monitoring failed: %s", exc)
            self._log.append(BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="error_monitoring_pass",
                entity_id="monitoring",
                outcome="error",
                details={"error": str(exc)},
            ))
        finally:
            self._schedule_error_monitoring()

    # ------------------------------------------------------------------
    # Cost monitoring (daily)
    # ------------------------------------------------------------------

    def _schedule_cost_monitoring(self) -> None:
        if not self._running:
            return
        timer = threading.Timer(COST_MONITOR_INTERVAL, self._run_cost_monitoring)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _run_cost_monitoring(self) -> None:
        if not self._running:
            return
        try:
            self._cost_monitor.run_daily_check()
            self._log.append(BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="cost_monitoring_pass",
                entity_id="costs",
                outcome="success",
                details={},
            ))
        except Exception as exc:
            logger.error("Cost monitoring failed: %s", exc)
        finally:
            self._schedule_cost_monitoring()

    # ------------------------------------------------------------------
    # Dependency audit (weekly, Monday)
    # ------------------------------------------------------------------

    def _schedule_dependency_audit(self) -> None:
        if not self._running:
            return
        timer = threading.Timer(DEPENDENCY_AUDIT_INTERVAL, self._run_dependency_audit)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _run_dependency_audit(self) -> None:
        if not self._running:
            return
        if not self._is_monday():
            # Reschedule if not Monday
            self._schedule_dependency_audit()
            return
        try:
            self._dependency_auditor.run_full_audit()
            self._log.append(BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="dependency_audit",
                entity_id="dependencies",
                outcome="success",
                details={},
            ))
        except Exception as exc:
            logger.error("Dependency audit failed: %s", exc)
        finally:
            self._schedule_dependency_audit()

    # ------------------------------------------------------------------
    # Devlog generation (weekly, Friday)
    # ------------------------------------------------------------------

    def _schedule_devlog_generation(self) -> None:
        if not self._running:
            return
        timer = threading.Timer(DEVLOG_INTERVAL, self._run_devlog_generation)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

    def _run_devlog_generation(self) -> None:
        if not self._running:
            return
        if not self._is_friday():
            self._schedule_devlog_generation()
            return
        try:
            self._doc_maintainer.generate_weekly_devlog()
            self._log.append(BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="devlog_generated",
                entity_id="docs",
                outcome="success",
                details={},
            ))
        except Exception as exc:
            logger.error("Devlog generation failed: %s", exc)
        finally:
            self._schedule_devlog_generation()

    # ------------------------------------------------------------------
    # Day helpers
    # ------------------------------------------------------------------

    def _is_monday(self) -> bool:
        return datetime.now(timezone.utc).weekday() == 0

    def _is_friday(self) -> bool:
        return datetime.now(timezone.utc).weekday() == 4

    # ------------------------------------------------------------------
    # Missed job recovery
    # ------------------------------------------------------------------

    def _check_missed_jobs(self) -> None:
        """Check operational log for missed jobs and trigger them."""
        now = datetime.now(timezone.utc)

        # Check error monitoring — should have run within last 30 min
        last_error = self._log.get_last_run_time("error_monitoring_pass")
        if last_error:
            last_dt = datetime.fromisoformat(last_error)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if (now - last_dt).total_seconds() > ERROR_MONITOR_INTERVAL:
                logger.warning("Missed error monitoring detected, triggering now")
                self._run_error_monitoring()
        else:
            logger.info("No prior error monitoring found, triggering initial pass")
            self._run_error_monitoring()

        # Check dependency audit — should have run within last 8 days
        last_audit = self._log.get_last_run_time("dependency_audit")
        if last_audit:
            last_dt = datetime.fromisoformat(last_audit)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if (now - last_dt).total_seconds() > DEPENDENCY_AUDIT_INTERVAL + 86400:
                logger.warning("Missed dependency audit detected, triggering now")
                self._dependency_auditor.run_full_audit()
        else:
            logger.info("No prior dependency audit found, will run on next Monday")
