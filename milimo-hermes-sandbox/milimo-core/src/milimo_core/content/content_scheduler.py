# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Content Scheduler

Runs the scheduled autonomous actions defined in the spec.

Morning planning: 06:00 daily
Weekly analytics query: Monday 06:00
Evolution cycle: handled by evolution_cycle.py
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone, timedelta, time as time_type
from typing import Any

from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from .content_generator import ContentGenerator
from .brief_manager import BriefManager
from .performance_monitor import PerformanceMonitor

logger = logging.getLogger("milimo.content_scheduler")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MORNING_PLANNING_TIME = time_type(6, 0)  # 06:00
CHECK_INTERVAL_SECONDS = 60


# ---------------------------------------------------------------------------
# Content Scheduler
# ---------------------------------------------------------------------------


class ContentScheduler:
    """
    Runs scheduled autonomous actions.

    Morning planning: 06:00 daily
    Weekly analytics query: Monday 06:00
    """

    def __init__(
        self,
        fs: ContentFilesystemInit,
        operational_log: ContentOperationalLog,
        generator: ContentGenerator | None = None,
        brief_manager: BriefManager | None = None,
        performance_monitor: PerformanceMonitor | None = None,
        mesh_client: Any | None = None,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._generator = generator
        self._brief_manager = brief_manager
        self._performance_monitor = performance_monitor
        self._mesh = mesh_client

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_morning_planning: datetime | None = None
        self._last_weekly_query: datetime | None = None

    def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info("Content scheduler started")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("Content scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running and not self._stop_event.is_set():
            try:
                self._check_and_run_tasks()
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)

            self._stop_event.wait(CHECK_INTERVAL_SECONDS)

    def _check_and_run_tasks(self) -> None:
        """Check if any scheduled tasks are due."""
        now = datetime.now(timezone.utc)
        now_time = now.time()

        if (
            now_time.hour == MORNING_PLANNING_TIME.hour
            and now_time.minute == MORNING_PLANNING_TIME.minute
        ):
            if self._should_run_morning_planning(now):
                self._morning_planning()
                self._last_morning_planning = now

            if now.weekday() == 0 and self._should_run_weekly_query(now):
                self._send_weekly_analytics_query()
                self._last_weekly_query = now

    def _should_run_morning_planning(self, now: datetime) -> bool:
        """Check if morning planning should run."""
        if self._last_morning_planning is None:
            return True

        return (now - self._last_morning_planning) > timedelta(hours=23)

    def _should_run_weekly_query(self, now: datetime) -> bool:
        """Check if weekly query should run."""
        if self._last_weekly_query is None:
            return True

        return (now - self._last_weekly_query) > timedelta(days=6)

    def _morning_planning(self) -> None:
        """
        Run morning planning at 06:00 daily.

        1. Read all active briefs
        2. Read latest analytics intel
        3. Query Analytics Claw if Monday
        4. Generate daily content plan
        5. Begin draft generation for priority briefs
        """
        logger.info("Starting morning planning")

        self._log.append(
            LogEntry(
                action_type="morning_planning_started",
                entity_id=f"plan-{datetime.now(timezone.utc).date().isoformat()}",
                outcome="success",
                details={"time": datetime.now(timezone.utc).isoformat()},
            )
        )

        active_briefs = []
        if self._brief_manager:
            active_briefs = self._brief_manager.get_active_briefs()
            logger.info("Found %d active briefs", len(active_briefs))

        self._read_analytics_intel()

        risks = []
        if self._generator:
            try:
                # Use a dedicated event loop for async generation
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    # Already in an async context — use create_task with error callback
                    task = loop.create_task(self._generator.generate_daily_plan())
                    task.add_done_callback(self._handle_plan_result)
                except RuntimeError:
                    # No running loop — create a new one (sync context)
                    loop = asyncio.new_event_loop()
                    try:
                        plan = loop.run_until_complete(
                            self._generator.generate_daily_plan()
                        )
                        logger.info("Generated daily plan: %s", plan.plan_id)
                    finally:
                        loop.close()
            except Exception as e:
                logger.error("Failed to generate daily plan: %s", e)

        if self._brief_manager:
            risks = self._brief_manager.check_deadline_risks()
            if risks:
                logger.warning("%d briefs at deadline risk", len(risks))

        self._log.append(
            LogEntry(
                action_type="morning_planning_completed",
                entity_id=f"plan-{datetime.now(timezone.utc).date().isoformat()}",
                outcome="success",
                details={
                    "active_briefs": len(active_briefs),
                    "risks": len(risks),
                },
            )
        )

        logger.info("Morning planning completed")

    def _handle_plan_result(self, future) -> None:
        """Callback for daily plan generation result — logs errors instead of swallowing them."""
        try:
            plan = future.result()
            logger.info("Generated daily plan: %s", plan.plan_id)
        except Exception as e:
            logger.error("Daily plan generation failed: %s", e)
            self._log.append(
                LogEntry(
                    action_type="daily_plan_failed",
                    entity_id=f"plan-{datetime.now(timezone.utc).date().isoformat()}",
                    outcome="failed",
                    details={"error": str(e)},
                )
            )

    def _send_weekly_analytics_query(self) -> None:
        """
        Send weekly analytics query on Monday 06:00.

        Sends content_performance_query via mesh.
        """
        logger.info("Sending weekly analytics query")

        query = {
            "message_type": "content_performance_query",
            "sender_role": "content",
            "recipient_role": "analytics",
            "payload": {
                "query": "top_performing_formats",
                "lookback_days": 7,
                "platform": None,
            },
        }

        if self._mesh:
            self._mesh.send(query)

        self._log.append(
            LogEntry(
                action_type="analytics_query_sent",
                entity_id=f"query-{datetime.now(timezone.utc).date().isoformat()}",
                outcome="success",
                details={
                    "query_type": "top_performing_formats",
                    "lookback_days": 7,
                },
            )
        )

        logger.info("Weekly analytics query sent")

    def handle_analytics_intel(self, message: dict) -> None:
        """
        Handle incoming performance_intel from Analytics Claw.

        Writes to /intelligence/analytics-feed/latest.json.
        """
        payload = message.get("payload", message)

        intel_path = self._fs.BASE / "intelligence" / "analytics-feed" / "latest.json"
        intel_path.parent.mkdir(parents=True, exist_ok=True)

        intel_data = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "source": "analytics_claw",
            "data": payload,
        }

        intel_path.write_text(json.dumps(intel_data, indent=2))

        self._log.append(
            LogEntry(
                action_type="intel_received",
                entity_id="analytics-intel",
                outcome="success",
                details={"source": "analytics"},
            )
        )

        logger.info("Analytics intel received and stored")

    def handle_client_health_signal(self, message: dict) -> None:
        """
        Handle incoming client_health_signal from Analytics Claw.

        Per spec: adjusts content generation priority for at-risk clients.
        Low health score triggers more conservative content approach.

        Message payload:
        - client_id: str
        - health_score: float (0.0 to 1.0)
        - recommended_action: str
        """
        payload = message.get("payload", message)

        client_id = payload.get("client_id")
        health_score = payload.get("health_score", 1.0)
        recommended_action = payload.get("recommended_action", "")

        if not client_id:
            logger.warning("client_health_signal missing client_id")
            return

        self._log.append(
            LogEntry(
                action_type="client_health_signal_received",
                entity_id=client_id,
                outcome="success",
                client_id=client_id,
                details={
                    "health_score": health_score,
                    "recommended_action": recommended_action,
                },
            )
        )

        health_signal_path = (
            self._fs.BASE
            / "intelligence"
            / "analytics-feed"
            / f"health_{client_id}.json"
        )
        health_signal_path.parent.mkdir(parents=True, exist_ok=True)

        health_data = {
            "client_id": client_id,
            "health_score": health_score,
            "recommended_action": recommended_action,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "action_taken": "logged_for_priority_adjustment",
        }

        health_signal_path.write_text(json.dumps(health_data, indent=2))

        if health_score < 0.5:
            logger.warning(
                "Client %s health score critical: %.2f. Action: %s",
                client_id,
                health_score,
                recommended_action,
            )
            if self._brief_manager:
                briefs = self._brief_manager.get_active_briefs()
                for brief in briefs:
                    if brief.client_id == client_id:
                        self._log.append(
                            LogEntry(
                                action_type="client_health_priority_adjustment",
                                entity_id=brief.brief_id,
                                outcome="success",
                                client_id=client_id,
                                details={
                                    "health_score": health_score,
                                    "brief_id": brief.brief_id,
                                },
                            )
                        )

        logger.info(
            "Client health signal processed for %s: score=%.2f",
            client_id,
            health_score,
        )

    def _read_analytics_intel(self) -> dict | None:
        """Read latest analytics intelligence."""
        intel_path = self._fs.BASE / "intelligence" / "analytics-feed" / "latest.json"

        if not intel_path.exists():
            logger.debug("No analytics intel available")
            return None

        try:
            data = json.loads(intel_path.read_text())
            logger.debug(
                "Read analytics intel from %s", data.get("received_at", "unknown")
            )
            return data
        except Exception as e:
            logger.warning("Failed to read analytics intel: %s", e)
            return None

    def trigger_morning_planning(self) -> None:
        """Manually trigger morning planning (for testing)."""
        self._morning_planning()

    def trigger_weekly_query(self) -> None:
        """Manually trigger weekly query (for testing)."""
        self._send_weekly_analytics_query()
