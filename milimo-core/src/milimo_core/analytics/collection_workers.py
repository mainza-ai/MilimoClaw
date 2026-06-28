# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Collection Workers

Scheduled data collection workers that periodically fetch real data
from external platforms (YouTube, Google Analytics, etc.) and persist
it to the Analytics Claw's data directories.

Replaces fabricated/mock data with actual platform metrics.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from .data_collectors import (
    YouTubeDataCollector,
    GoogleAnalyticsCollector,
    GenericAPICollector,
    CollectorResult,
)
from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
)

logger = logging.getLogger("milimo.analytics.collection_workers")


class CollectionWorker:
    """
    Manages scheduled data collection from external platforms.

    Runs collection jobs on configurable intervals.
    Writes collected data to the Analytics Claw's data directories
    so that the QueryHandler and ReportGenerator can use real data.
    """

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log
        self._running = False
        self._collectors: dict[str, dict[str, Any]] = {}
        self._timers: list[threading.Timer] = []
        self._collection_history: list[dict[str, Any]] = []

    def register_youtube(
        self,
        channel_id: str | None = None,
        api_key: str | None = None,
        interval_hours: int = 6,
    ) -> None:
        """Register YouTube data collector."""
        collector = YouTubeDataCollector(
            channel_id=channel_id,
            api_key=api_key,
            data_dir=self.fs.get_data_path("youtube"),
        )
        if collector.is_configured():
            self._collectors["youtube"] = {
                "collector": collector,
                "interval_hours": interval_hours,
                "enabled": True,
            }
            logger.info("YouTube collector registered (interval: %dh)", interval_hours)
        else:
            logger.warning("YouTube collector not configured — skipping")

    def register_google_analytics(
        self,
        property_id: str | None = None,
        credentials_path: str | None = None,
        interval_hours: int = 12,
    ) -> None:
        """Register Google Analytics 4 collector."""
        collector = GoogleAnalyticsCollector(
            property_id=property_id,
            credentials_path=credentials_path,
            data_dir=self.fs.get_data_path("google_analytics"),
        )
        if collector.is_configured():
            self._collectors["google_analytics"] = {
                "collector": collector,
                "interval_hours": interval_hours,
                "enabled": True,
            }
            logger.info(
                "Google Analytics collector registered (interval: %dh)", interval_hours
            )
        else:
            logger.warning("Google Analytics collector not configured — skipping")

    def register_generic(
        self,
        name: str,
        base_url: str,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        interval_hours: int = 24,
    ) -> None:
        """Register a generic REST API collector."""
        collector = GenericAPICollector(
            name=name,
            base_url=base_url,
            api_key=api_key,
            headers=headers,
            data_dir=self.fs.get_data_path(name),
        )
        self._collectors[name] = {
            "collector": collector,
            "interval_hours": interval_hours,
            "enabled": True,
        }
        logger.info(
            "Generic collector '%s' registered (interval: %dh)", name, interval_hours
        )

    def start(self) -> None:
        """Start all collection workers on their schedules."""
        if self._running:
            logger.warning("Collection workers already running")
            return

        self._running = True

        for name, config in self._collectors.items():
            if config["enabled"]:
                self._schedule_collection(name, config)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="collection_workers_started",
                entity_id="collection_workers",
                source_claw="analytics",
                outcome="success",
                details={"collectors": list(self._collectors.keys())},
            )
        )

        logger.info("Collection workers started for %d sources", len(self._collectors))

    def stop(self) -> None:
        """Stop all collection workers."""
        self._running = False
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="collection_workers_stopped",
                entity_id="collection_workers",
                source_claw="analytics",
                outcome="success",
                details={},
            )
        )

        logger.info("Collection workers stopped")

    def collect_now(self, source: str | None = None) -> list[CollectorResult]:
        """Trigger immediate collection for all or a specific source."""
        results: list[CollectorResult] = []
        if source:
            config = self._collectors.get(source)
            if not config:
                return results
            targets: list[tuple[str, dict[str, Any]]] = [(source, config)]
        else:
            targets = list(self._collectors.items())

        for name, config in targets:
            if not config["enabled"]:
                continue

            collector = config["collector"]
            try:
                if name == "youtube":
                    result = collector.collect_video_stats()
                    channel_result = collector.collect_channel_analytics()
                    results.append(result)
                    results.append(channel_result)
                elif name == "google_analytics":
                    result = collector.collect_page_views()
                    events_result = collector.collect_events()
                    results.append(result)
                    results.append(events_result)
                else:
                    result = collector.collect("")
                    results.append(result)

                self._log_collection_result(name, result)

            except Exception as e:
                logger.error("Collection failed for %s: %s", name, e)
                results.append(
                    CollectorResult(
                        source=name,
                        success=False,
                        records_collected=0,
                        data=[],
                        error=str(e),
                    )
                )

        return results

    def get_collection_summary(self) -> dict[str, Any]:
        """Get summary of all collection activity."""
        summary = {}
        for name, config in self._collectors.items():
            collector = config["collector"]
            summary[name] = {
                "enabled": config["enabled"],
                "interval_hours": config["interval_hours"],
                "last_collection": collector._last_collection.isoformat()
                if collector._last_collection
                else None,
                "configured": collector.is_configured()
                if hasattr(collector, "is_configured")
                else True,
            }
        return summary

    def _schedule_collection(self, name: str, config: dict) -> None:
        """Schedule recurring collection for a source."""
        interval_seconds = config["interval_hours"] * 3600

        def run_and_reschedule() -> None:
            if not self._running:
                return

            try:
                results = self.collect_now(name)
                for result in results:
                    self._log_collection_result(name, result)
            except Exception as e:
                logger.error("Scheduled collection failed for %s: %s", name, e)

            # Reschedule
            if self._running:
                timer = threading.Timer(interval_seconds, run_and_reschedule)
                timer.daemon = True
                timer.start()
                self._timers.append(timer)

        timer = threading.Timer(interval_seconds, run_and_reschedule)
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

        logger.info(
            "Scheduled %s collection every %d hours", name, config["interval_hours"]
        )

    def _log_collection_result(self, source: str, result: CollectorResult) -> None:
        """Log collection result to operational log."""
        self._collection_history.append(
            {
                "source": result.source,
                "success": result.success,
                "records": result.records_collected,
                "error": result.error,
                "collected_at": result.collected_at,
            }
        )

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=result.collected_at,
                action_type="data_collection",
                entity_id=source,
                source_claw="analytics",
                outcome="success" if result.success else "failed",
                details={
                    "records_collected": result.records_collected,
                    "error": result.error,
                },
            )
        )

        if result.success:
            logger.info(
                "Collected %d records from %s", result.records_collected, source
            )
        else:
            logger.warning("Collection from %s failed: %s", source, result.error)
