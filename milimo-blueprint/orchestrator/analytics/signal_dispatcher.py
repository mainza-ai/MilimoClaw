#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Signal Dispatcher

Sends all outbound messages from the Analytics Claw to other claws.
All sends go through the inter-claw mesh gateway.
Every dispatch logged to signals.log.
Never raises on dispatch failure — logs and continues.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .analytics_init import AnalyticsFilesystemInit, AnalyticsLogEntry, AnalyticsOperationalLog

logger = logging.getLogger("milimo.signal_dispatcher")


class SignalDispatcher:
    """
    Sends all outbound messages from the Analytics Claw to other claws.

    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to signals.log.
    Never raises on dispatch failure — logs and continues.
    """

    def __init__(
        self,
        operational_log: AnalyticsOperationalLog,
        fs: AnalyticsFilesystemInit,
        mesh_sender: Callable[[dict], None] | None = None,
    ) -> None:
        self.operational_log = operational_log
        self.fs = fs
        self.mesh_sender = mesh_sender
        self._signals_log_path = fs.get_log_path("signals.log")
        self._signals_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._signals_log_path.exists():
            self._signals_log_path.touch()

    def _log_to_signals_log(self, entry: dict[str, Any]) -> None:
        """Write entry to signals.log."""
        try:
            with open(self._signals_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
        except Exception as e:
            logger.warning("Failed to write to signals.log: %s", e)

    def send_performance_intel(
        self,
        top_formats: list[dict[str, Any]],
        top_times: list[dict[str, Any]],
        engagement_trends: list[dict[str, Any]],
        audience_signals: list[dict[str, Any]],
    ) -> None:
        """Send performance_intel to Content Claw."""
        payload = {
            "top_formats": top_formats,
            "top_publish_times": top_times,
            "engagement_trends": engagement_trends,
            "audience_signals": audience_signals,
        }

        self._send(
            message_type="performance_intel",
            recipient_role="content",
            payload=payload,
        )

    def send_retention_signals(
        self,
        feature_adoption_rates: list[dict[str, Any]],
        churn_correlation: list[dict[str, Any]],
        recommended_features: list[dict[str, Any]],
    ) -> None:
        """Send retention_signals to Build Claw."""
        payload = {
            "feature_adoption_rates": feature_adoption_rates,
            "churn_correlation": churn_correlation,
            "recommended_features": recommended_features,
        }

        self._send(
            message_type="retention_signals",
            recipient_role="build",
            payload=payload,
        )

    def send_client_health_alert(
        self,
        client_id: str,
        health_score: float,
        risk_factors: list[str],
        recommended_action: str,
    ) -> None:
        """Send client_health_alert to Ops Claw (IMMEDIATE when score < 6.0)."""
        payload = {
            "client_id": client_id,
            "health_score": health_score,
            "risk_factors": risk_factors,
            "recommended_action": recommended_action,
            "urgency": "high" if health_score < 6.0 else "normal",
        }

        self._send(
            message_type="client_health_alert",
            recipient_role="ops",
            payload=payload,
        )

    def send_revenue_anomaly(
        self,
        anomaly_type: str,
        current_value: float,
        baseline_value: float,
        severity: str,
    ) -> None:
        """Send revenue_anomaly to Finance Claw (IMMEDIATE on anomaly detection)."""
        payload = {
            "anomaly_type": anomaly_type,
            "current_value": current_value,
            "baseline_value": baseline_value,
            "severity": severity,
            "ratio": current_value / baseline_value if baseline_value > 0 else 0,
        }

        self._send(
            message_type="revenue_anomaly",
            recipient_role="finance",
            payload=payload,
        )

    def send_content_performance_response(
        self,
        query_id: str,
        requesting_claw: str,
        response_data: dict[str, Any],
    ) -> None:
        """Send response to a content_performance_query."""
        payload = {
            "query_id": query_id,
            "response_data": response_data,
            "responding_to": query_id,
        }

        self._send(
            message_type="content_performance_response",
            recipient_role=requesting_claw,
            payload=payload,
        )

    def send_behavior_query_response(
        self,
        query_id: str,
        requesting_claw: str,
        response_data: dict[str, Any],
    ) -> None:
        """Send response to a behavior_query."""
        payload = {
            "query_id": query_id,
            "response_data": response_data,
            "responding_to": query_id,
        }

        self._send(
            message_type="behavior_query_response",
            recipient_role=requesting_claw,
            payload=payload,
        )

    def _send(
        self, message_type: str, recipient_role: str, payload: dict[str, Any],
    ) -> None:
        """Core send via mesh gateway."""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        message = {
            "message_id": message_id,
            "timestamp": timestamp,
            "message_type": message_type,
            "sender_role": "analytics",
            "recipient_role": recipient_role,
            "payload": payload,
        }

        signals_log_entry = {
            "timestamp": timestamp,
            "message_id": message_id,
            "message_type": message_type,
            "recipient_role": recipient_role,
            "status": "dispatching",
        }

        try:
            if self.mesh_sender:
                self.mesh_sender(message)
            else:
                logger.debug("No mesh sender configured, message would be: %s", message)

            signals_log_entry["status"] = "dispatched"
            self._log_to_signals_log(signals_log_entry)

            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=timestamp,
                    action_type="signal_dispatched",
                    entity_id=message_id,
                    source_claw="analytics",
                    outcome="success",
                    details={
                        "message_type": message_type,
                        "recipient_role": recipient_role,
                    },
                )
            )

            logger.debug(
                "Dispatched %s to %s (message_id: %s)",
                message_type,
                recipient_role,
                message_id,
            )

        except Exception as exc:
            signals_log_entry["status"] = "failed"
            signals_log_entry["error"] = str(exc)
            self._log_to_signals_log(signals_log_entry)

            logger.error(
                "Failed to dispatch %s to %s: %s",
                message_type,
                recipient_role,
                exc,
            )

            self.operational_log.append(
                AnalyticsLogEntry(
                    timestamp=timestamp,
                    action_type="signal_dispatch_failed",
                    entity_id=message_id,
                    source_claw="analytics",
                    outcome="failure",
                    details={
                        "message_type": message_type,
                        "recipient_role": recipient_role,
                        "error": str(exc),
                    },
                )
            )
