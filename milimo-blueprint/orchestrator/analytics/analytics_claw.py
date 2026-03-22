#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Claw Main Entry Point

Main entry point for the Analytics Claw.
Initializes all components, wires them together, and starts the scheduler.
Called by the NemoClaw blueprint orchestrator on sandbox startup.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
    BASE,
)
from .analytics_scheduler import AnalyticsScheduler
from .anomaly_detector import AnomalyDetector
from .baseline_manager import BaselineManager
from .forward_projector import ForwardProjector
from .opportunity_scorer import OpportunityScorer
from .query_handler import QueryHandler
from .report_generator import ReportGenerator
from .signal_dispatcher import SignalDispatcher
from .signal_processor import SignalProcessor

logger = logging.getLogger("milimo.analytics_claw")


class AnalyticsClaw:
    """
    Main entry point for the Analytics Claw.

    Initializes all components, wires them together, and starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(
        self,
        squad_id: str = "default",
        inference_client: Any = None,
        mesh_sender: Callable[[dict], None] | None = None,
        base_path: Path | None = None,
    ) -> None:
        self.squad_id = squad_id
        self.inference_client = inference_client
        self.mesh_sender = mesh_sender
        self.base_path = base_path or BASE

        self.fs: AnalyticsFilesystemInit | None = None
        self.operational_log: AnalyticsOperationalLog | None = None
        self.signal_dispatcher: SignalDispatcher | None = None
        self.baseline_manager: BaselineManager | None = None
        self.signal_processor: SignalProcessor | None = None
        self.query_handler: QueryHandler | None = None
        self.anomaly_detector: AnomalyDetector | None = None
        self.report_generator: ReportGenerator | None = None
        self.opportunity_scorer: OpportunityScorer | None = None
        self.forward_projector: ForwardProjector | None = None
        self.scheduler: AnalyticsScheduler | None = None

        self._started = False
        self._handlers_registered = False

    def startup(self) -> None:
        """Initialize all components and start the scheduler."""
        if self._started:
            logger.warning("AnalyticsClaw already started")
            return

        logger.info("Starting AnalyticsClaw for squad: %s", self.squad_id)

        self.fs = AnalyticsFilesystemInit(self.base_path)
        init_result = self.fs.initialize()
        if not init_result.success:
            logger.error("Filesystem initialization failed: %s", init_result.failed)
            raise RuntimeError("Analytics filesystem initialization failed")

        validation = self.fs.validate()
        if not validation.valid:
            logger.error("Filesystem validation failed: %s", validation.missing_dirs + validation.missing_files)
            raise RuntimeError("Analytics filesystem validation failed")

        log_path = self.fs.get_log_path("operational.log")
        self.operational_log = AnalyticsOperationalLog(log_path)

        self.signal_dispatcher = SignalDispatcher(
            operational_log=self.operational_log,
            fs=self.fs,
            mesh_sender=self.mesh_sender,
        )

        self.baseline_manager = BaselineManager(
            fs=self.fs,
            operational_log=self.operational_log,
        )

        self.signal_processor = SignalProcessor(
            fs=self.fs,
            operational_log=self.operational_log,
        )

        self.query_handler = QueryHandler(
            fs=self.fs,
            operational_log=self.operational_log,
        )

        self.anomaly_detector = AnomalyDetector(
            fs=self.fs,
            operational_log=self.operational_log,
            alert_dispatcher=self._dispatch_anomaly_alert,
        )

        self.report_generator = ReportGenerator(
            fs=self.fs,
            operational_log=self.operational_log,
            squad_id=self.squad_id,
            inference_client=self.inference_client,
        )

        self.opportunity_scorer = OpportunityScorer(
            fs=self.fs,
            operational_log=self.operational_log,
            inference_client=self.inference_client,
            dispatcher=self._dispatch_opportunity,
        )

        self.forward_projector = ForwardProjector(fs=self.fs)

        self.scheduler = AnalyticsScheduler(
            baseline_manager=self.baseline_manager,
            report_generator=self.report_generator,
            opportunity_scorer=self.opportunity_scorer,
            operational_log=self.operational_log,
            signal_dispatcher=self.signal_dispatcher,
        )

        self.scheduler.start()

        self._started = True

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=self._now_iso(),
                action_type="claw_started",
                entity_id=self.squad_id,
                source_claw=None,
                outcome="success",
                details={
                    "base_path": str(self.base_path),
                },
            )
        )

        logger.info("AnalyticsClaw started successfully")

    def shutdown(self) -> None:
        """Stop scheduler cleanly."""
        if not self._started:
            return

        logger.info("Shutting down AnalyticsClaw")

        if self.scheduler:
            self.scheduler.stop()

        if self.operational_log:
            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=self._now_iso(),
                    action_type="claw_stopped",
                    entity_id=self.squad_id,
                    source_claw=None,
                    outcome="success",
                    details={},
                )
            )

        self._started = False
        logger.info("AnalyticsClaw stopped")

    def handle_inbound(self, raw_message: dict[str, Any]) -> None:
        """Route inbound message to correct handler."""
        if not self._started:
            logger.warning("AnalyticsClaw not started, cannot handle message")
            return

        message_type = raw_message.get("message_type", "")
        sender = raw_message.get("sender_role", "unknown")

        logger.debug("Received %s from %s", message_type, sender)

        try:
            handler_map = {
                "performance_signal": self._handle_performance_signal,
                "client_health_signal": self._handle_client_health_signal,
                "client_onboarded": self._handle_client_onboarded,
                "revenue_summary": self._handle_revenue_summary,
                "shipping_summary": self._handle_shipping_summary,
                "content_performance_query": self._handle_content_performance_query,
                "behavior_query": self._handle_behavior_query,
            }

            handler = handler_map.get(message_type)
            if handler:
                handler(raw_message)
            else:
                logger.warning("Unknown message type: %s", message_type)

            if self.operational_log:
                self.operational_log.append(
                    AnalyticsLogEntry(
                        timestamp=self._now_iso(),
                        action_type="message_handled",
                        entity_id=raw_message.get("message_id", ""),
                        source_claw=sender,
                        outcome="success",
                        details={"message_type": message_type},
                    )
                )

        except Exception as e:
            logger.error("Failed to handle %s: %s", message_type, e)

            if self.operational_log:
                self.operational_log.append(
                    AnalyticsLogEntry(
                        timestamp=self._now_iso(),
                        action_type="message_handling_failed",
                        entity_id=raw_message.get("message_id", ""),
                        source_claw=sender,
                        outcome="failure",
                        details={
                            "message_type": message_type,
                            "error": str(e),
                        },
                    )
                )

    def _handle_performance_signal(self, message: dict[str, Any]) -> None:
        """Handle performance_signal from Content Claw."""
        if self.signal_processor:
            self.signal_processor.handle_performance_signal(message)

            content_baselines = self.baseline_manager.load_content_baselines() if self.baseline_manager else {}
            if content_baselines and self.anomaly_detector:
                anomaly = self.anomaly_detector.check_content_signal(message, content_baselines)
                if anomaly:
                    self.anomaly_detector.save_anomaly(anomaly)
                    self.anomaly_detector.dispatch_alert(anomaly)

    def _handle_client_health_signal(self, message: dict[str, Any]) -> None:
        """Handle client_health_signal from Ops Claw."""
        if self.signal_processor:
            self.signal_processor.handle_client_health_signal(message)

            health_score = message.get("health_score", 10)
            if health_score < 6.0 and self.signal_dispatcher:
                self.signal_dispatcher.send_client_health_alert(
                    client_id=message.get("client_id", ""),
                    health_score=health_score,
                    risk_factors=message.get("risk_factors", []),
                    recommended_action=message.get("recommended_action", "Schedule client check-in"),
                )

    def _handle_client_onboarded(self, message: dict[str, Any]) -> None:
        """Handle client_onboarded from Ops Claw."""
        if self.signal_processor:
            self.signal_processor.handle_client_onboarded(message)

    def _handle_revenue_summary(self, message: dict[str, Any]) -> None:
        """Handle revenue_summary from Finance Claw."""
        if self.signal_processor:
            self.signal_processor.handle_revenue_summary(message)

            revenue_baselines = self.baseline_manager.load_revenue_baseline() if self.baseline_manager else {}
            if revenue_baselines and self.anomaly_detector:
                anomaly = self.anomaly_detector.check_revenue_signal(message, revenue_baselines)
                if anomaly:
                    self.anomaly_detector.save_anomaly(anomaly)
                    self.anomaly_detector.dispatch_alert(anomaly)

    def _handle_shipping_summary(self, message: dict[str, Any]) -> None:
        """Handle shipping_summary from Build Claw."""
        if self.signal_processor:
            self.signal_processor.handle_shipping_summary(message)

            delivery_baselines = self.baseline_manager.load_delivery_baseline() if self.baseline_manager else {}
            if delivery_baselines and self.anomaly_detector:
                anomaly = self.anomaly_detector.check_delivery_signal(message, delivery_baselines)
                if anomaly:
                    self.anomaly_detector.save_anomaly(anomaly)
                    self.anomaly_detector.dispatch_alert(anomaly)

    def _handle_content_performance_query(self, message: dict[str, Any]) -> None:
        """Handle content_performance_query from other claws."""
        if self.query_handler:
            response = self.query_handler.handle(message)
            if self.signal_dispatcher:
                self.signal_dispatcher.send_content_performance_response(
                    query_id=message.get("message_id", ""),
                    requesting_claw=message.get("sender_role", ""),
                    response_data=response.data if response.data else {},
                )

    def _handle_behavior_query(self, message: dict[str, Any]) -> None:
        """Handle behavior_query from other claws."""
        if self.query_handler:
            response = self.query_handler.handle(message)
            if self.signal_dispatcher:
                self.signal_dispatcher.send_behavior_query_response(
                    query_id=message.get("message_id", ""),
                    requesting_claw=message.get("sender_role", ""),
                    response_data=response.data if response.data else {},
                )

    def _dispatch_anomaly_alert(self, message_type: str, target_claw: str, payload: dict) -> None:
        """Dispatch anomaly alert via signal dispatcher."""
        if self.signal_dispatcher:
            if message_type == "revenue_anomaly":
                self.signal_dispatcher.send_revenue_anomaly(
                    anomaly_type=payload.get("metric", ""),
                    current_value=payload.get("current_value", 0),
                    baseline_value=payload.get("baseline_mean", 0),
                    severity=payload.get("severity", "mild"),
                )
            elif message_type == "client_health_alert":
                self.signal_dispatcher.send_client_health_alert(
                    client_id=payload.get("client_id", ""),
                    health_score=payload.get("health_score", 0),
                    risk_factors=payload.get("risk_factors", []),
                    recommended_action=payload.get("recommended_action", ""),
                )

    def _dispatch_opportunity(self, message_type: str, target_claw: str, payload: dict) -> None:
        """Dispatch opportunity via signal dispatcher."""
        if self.signal_dispatcher:
            if message_type == "performance_intel":
                self.signal_dispatcher.send_performance_intel(
                    top_formats=[payload],
                    top_times=[],
                    engagement_trends=[],
                    audience_signals=[],
                )
            elif message_type == "retention_signals":
                self.signal_dispatcher.send_retention_signals(
                    feature_adoption_rates=[],
                    churn_correlation=[payload],
                    recommended_features=[],
                )

    def _now_iso(self) -> str:
        """Return current ISO timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
