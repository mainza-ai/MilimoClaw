# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Scheduler

Orchestrates all scheduled autonomous actions for the Analytics Claw.

Schedule (all local time):
- Sunday 01:00 — Baseline recalculation
- Sunday 02:00 — Weekly intelligence report generation
- Daily 06:00 — Opportunity scoring

Uses threading.Timer with recalculated delay to next occurrence.
No cron dependency. No APScheduler. Only stdlib.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from .analytics_init import AnalyticsLogEntry, AnalyticsOperationalLog

logger = logging.getLogger("milimo.analytics_scheduler")


class AnalyticsScheduler:
    """
    Orchestrates all scheduled autonomous actions for the Analytics Claw.

    Schedule (all local time):
    - Sunday 01:00 — Baseline recalculation
    - Sunday 02:00 — Weekly intelligence report generation
    - Daily 06:00 — Opportunity scoring

    Uses threading.Timer with recalculated delay to next occurrence.
    No cron dependency. No APScheduler. Only stdlib.

    On startup: checks if any scheduled jobs were missed during downtime.
    If missed, runs the job immediately and logs "missed job recovered".
    """

    def __init__(
        self,
        baseline_manager: Any,
        report_generator: Any,
        opportunity_scorer: Any,
        operational_log: AnalyticsOperationalLog,
        signal_dispatcher: Any = None,
    ) -> None:
        self.baseline_manager = baseline_manager
        self.report_generator = report_generator
        self.opportunity_scorer = opportunity_scorer
        self.operational_log = operational_log
        self.signal_dispatcher = signal_dispatcher

        self._timers: dict[str, threading.Timer] = {}
        self._running = False

    def start(self) -> None:
        """Initialize all scheduled jobs and check for missed jobs."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True

        self._schedule_next(
            "baseline_recalculation",
            self._run_baseline_recalculation,
            target_hour=1,
            target_minute=0,
            target_weekday=6,
        )

        self._schedule_next(
            "weekly_report",
            self._run_weekly_report,
            target_hour=2,
            target_minute=0,
            target_weekday=6,
        )

        self._schedule_next(
            "opportunity_scoring",
            self._run_opportunity_scoring,
            target_hour=6,
            target_minute=0,
            target_weekday=None,
        )

        self._check_missed_jobs()

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="scheduler_started",
                entity_id="scheduler",
                source_claw=None,
                outcome="success",
                details={},
            )
        )

        logger.info("Analytics scheduler started")

    def stop(self) -> None:
        """Cancel all pending timers cleanly."""
        self._running = False

        for job_name, timer in self._timers.items():
            timer.cancel()
            logger.debug("Cancelled timer: %s", job_name)

        self._timers.clear()

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="scheduler_stopped",
                entity_id="scheduler",
                source_claw=None,
                outcome="success",
                details={},
            )
        )

        logger.info("Analytics scheduler stopped")

    def _schedule_next(
        self,
        job_name: str,
        job_fn: Callable[[], None],
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None,
    ) -> None:
        """Schedule the next occurrence of a job."""
        if not self._running:
            return

        delay_seconds = self._seconds_until(target_hour, target_minute, target_weekday)

        def run_and_reschedule() -> None:
            if not self._running:
                return

            try:
                logger.info("Running scheduled job: %s", job_name)
                job_fn()
            except Exception as e:
                logger.error("Scheduled job %s failed: %s", job_name, e)

            self._schedule_next(
                job_name, job_fn, target_hour, target_minute, target_weekday
            )

        if job_name in self._timers:
            self._timers[job_name].cancel()

        self._timers[job_name] = threading.Timer(delay_seconds, run_and_reschedule)
        self._timers[job_name].daemon = True
        self._timers[job_name].start()

        logger.debug(
            "Scheduled %s to run in %.0f seconds",
            job_name,
            delay_seconds,
        )

    def _run_baseline_recalculation(self) -> None:
        """Run baseline recalculation (Sunday 01:00)."""
        logger.info("Running baseline recalculation")

        start_time = time.time()

        try:
            if self.baseline_manager:
                self.baseline_manager.recalculate_all()

            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="baseline_recalculation",
                    entity_id="scheduled",
                    source_claw=None,
                    outcome="success",
                    details={
                        "duration_seconds": round(time.time() - start_time, 2),
                    },
                )
            )

            logger.info(
                "Baseline recalculation completed in %.2fs", time.time() - start_time
            )

        except Exception as e:
            logger.error("Baseline recalculation failed: %s", e)
            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="baseline_recalculation",
                    entity_id="scheduled",
                    source_claw=None,
                    outcome="failure",
                    details={"error": str(e)},
                )
            )

    def _run_weekly_report(self) -> None:
        """Run weekly report generation (Sunday 02:00)."""
        logger.info("Running weekly report generation")

        start_time = time.time()

        try:
            report = None
            if self.report_generator:
                report = self.report_generator.generate()

            if self.signal_dispatcher and report:
                self.signal_dispatcher.send_performance_intel(
                    top_formats=report.content_performance.get("top_formats", []),
                    top_times=report.content_performance.get("top_publish_times", []),
                    engagement_trends=[],
                    audience_signals=[],
                )

                self.signal_dispatcher.send_retention_signals(
                    feature_adoption_rates=[],
                    churn_correlation=report.client_health.get("at_risk_clients", []),
                    recommended_features=[],
                )

            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="weekly_report_generation",
                    entity_id="scheduled",
                    source_claw=None,
                    outcome="success",
                    details={
                        "duration_seconds": round(time.time() - start_time, 2),
                    },
                )
            )

            logger.info("Weekly report completed in %.2fs", time.time() - start_time)

        except Exception as e:
            logger.error("Weekly report generation failed: %s", e)
            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="weekly_report_generation",
                    entity_id="scheduled",
                    source_claw=None,
                    outcome="failure",
                    details={"error": str(e)},
                )
            )

    def _run_opportunity_scoring(self) -> None:
        """Run opportunity scoring (Daily 06:00)."""
        logger.info("Running opportunity scoring")

        start_time = time.time()

        try:
            if self.opportunity_scorer:
                self.opportunity_scorer.score_all()

            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="opportunity_scoring",
                    entity_id="scheduled",
                    source_claw=None,
                    outcome="success",
                    details={
                        "duration_seconds": round(time.time() - start_time, 2),
                    },
                )
            )

            logger.info(
                "Opportunity scoring completed in %.2fs", time.time() - start_time
            )

        except Exception as e:
            logger.error("Opportunity scoring failed: %s", e)
            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="opportunity_scoring",
                    entity_id="scheduled",
                    source_claw=None,
                    outcome="failure",
                    details={"error": str(e)},
                )
            )

    def _check_missed_jobs(self) -> None:
        """Check for missed jobs and run them immediately if needed."""
        now = datetime.now(timezone.utc)

        recent_entries = self.operational_log.read_recent(days=10)

        last_baseline = None
        last_report = None

        for entry in recent_entries:
            if (
                entry.action_type == "baseline_recalculation"
                and entry.outcome == "success"
            ):
                last_baseline = entry.timestamp
            elif (
                entry.action_type == "weekly_report_generation"
                and entry.outcome == "success"
            ):
                last_report = entry.timestamp

        if last_baseline:
            try:
                baseline_time = datetime.fromisoformat(last_baseline)
                if (now - baseline_time) > timedelta(days=8):
                    logger.info("Missed baseline recalculation detected, running now")
                    self._run_baseline_recalculation()
                    self._log_missed_job("baseline_recalculation", last_baseline)
            except ValueError:
                pass

        if last_report:
            try:
                report_time = datetime.fromisoformat(last_report)
                if (now - report_time) > timedelta(days=8):
                    logger.info("Missed weekly report detected, running now")
                    self._run_weekly_report()
                    self._log_missed_job("weekly_report", last_report)
            except ValueError:
                pass

    def _log_missed_job(self, job_name: str, last_run: str) -> None:
        """Log a recovered missed job."""
        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="missed_job_recovered",
                entity_id=job_name,
                source_claw=None,
                outcome="success",
                details={
                    "job_name": job_name,
                    "last_run": last_run,
                },
            )
        )

    def _seconds_until(
        self,
        target_hour: int,
        target_minute: int,
        target_weekday: int | None = None,
    ) -> float:
        """Calculate seconds until the next occurrence of target time."""
        now = datetime.now(timezone.utc)

        if target_weekday is not None:
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0:
                target = now.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )
                if target <= now:
                    days_ahead = 7
            else:
                pass

            target = now.replace(
                hour=target_hour, minute=target_minute, second=0, microsecond=0
            )
            target = target + timedelta(days=days_ahead)
        else:
            target = now.replace(
                hour=target_hour, minute=target_minute, second=0, microsecond=0
            )
            if target <= now:
                target = target + timedelta(days=1)

        delta = target - now
        return max(delta.total_seconds(), 0.1)
