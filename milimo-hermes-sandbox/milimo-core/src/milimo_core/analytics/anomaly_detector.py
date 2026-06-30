# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Anomaly Detector

Detects performance anomalies by comparing incoming signals
against 30-day rolling baselines. Writes anomalies to signals/anomalies/
and dispatches alerts to target claws immediately.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Callable

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
)
from .baseline_manager import ContentBaseline, RevenueBaseline, DeliveryBaseline

logger = logging.getLogger("milimo.anomaly_detector")


@dataclass
class DetectedAnomaly:
    """Represents a detected anomaly."""

    signal_id: str
    anomaly_id: str
    detected_at: str
    metric: str
    current_value: float
    baseline_mean: float
    baseline_std_dev: float
    ratio: float
    direction: Literal["positive", "negative"]
    severity: Literal["mild", "significant", "extreme"]
    requires_attention: bool
    target_claw: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "anomaly_id": self.anomaly_id,
            "detected_at": self.detected_at,
            "metric": self.metric,
            "current_value": self.current_value,
            "baseline_mean": self.baseline_mean,
            "baseline_std_dev": self.baseline_std_dev,
            "ratio": self.ratio,
            "direction": self.direction,
            "severity": self.severity,
            "requires_attention": self.requires_attention,
            "target_claw": self.target_claw,
            "details": self.details,
        }


class AnomalyDetector:
    """
    Detects performance anomalies by comparing incoming signals
    against 30-day rolling baselines.

    Triggered on every inbound signal that has a baseline.
    Skips detection gracefully when no baseline exists (fresh install).
    """

    POSITIVE_THRESHOLD = 2.0
    NEGATIVE_THRESHOLD = 0.5

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
        alert_dispatcher: Callable[[str, str, dict], None] | None = None,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log
        self.alert_dispatcher = alert_dispatcher

    def check_content_signal(
        self,
        signal: dict[str, Any],
        baselines: dict[str, ContentBaseline],
    ) -> DetectedAnomaly | None:
        """Check content performance signal for anomalies."""
        platform = signal.get("platform", "")
        content_type = signal.get("content_type", "")
        engagement_data = signal.get("engagement_data", {})

        for metric_name, value in engagement_data.items():
            if not isinstance(value, (int, float)):
                continue

            key = f"{platform}:{content_type}:{metric_name}"
            baseline = baselines.get(key)

            if not baseline:
                logger.debug("No baseline for %s", key)
                continue

            ratio = float(value) / baseline.mean if baseline.mean > 0 else 0.0

            if ratio >= self.POSITIVE_THRESHOLD:
                return self._create_anomaly(
                    signal_id=signal.get("signal_id", ""),
                    metric=f"content.{platform}.{content_type}.{metric_name}",
                    current_value=float(value),
                    baseline=baseline,
                    ratio=ratio,
                    direction="positive",
                    target_claw="content",
                )
            elif ratio <= self.NEGATIVE_THRESHOLD:
                return self._create_anomaly(
                    signal_id=signal.get("signal_id", ""),
                    metric=f"content.{platform}.{content_type}.{metric_name}",
                    current_value=float(value),
                    baseline=baseline,
                    ratio=ratio,
                    direction="negative",
                    target_claw="content",
                )

        return None

    def check_revenue_signal(
        self,
        signal: dict[str, Any],
        baselines: dict[str, RevenueBaseline],
    ) -> DetectedAnomaly | None:
        """Check revenue signal for anomalies."""
        for metric in ["week_total", "invoices_paid", "invoices_pending"]:
            value = signal.get(metric)
            if not isinstance(value, (int, float)):
                continue

            baseline = baselines.get(metric)
            if not baseline:
                continue

            ratio = float(value) / baseline.mean if baseline.mean > 0 else 0.0

            if ratio >= self.POSITIVE_THRESHOLD:
                return self._create_anomaly(
                    signal_id=signal.get("signal_id", ""),
                    metric=f"revenue.{metric}",
                    current_value=float(value),
                    baseline=baseline,
                    ratio=ratio,
                    direction="positive",
                    target_claw="finance",
                )
            elif ratio <= self.NEGATIVE_THRESHOLD:
                return self._create_anomaly(
                    signal_id=signal.get("signal_id", ""),
                    metric=f"revenue.{metric}",
                    current_value=float(value),
                    baseline=baseline,
                    ratio=ratio,
                    direction="negative",
                    target_claw="finance",
                )

        return None

    def check_delivery_signal(
        self,
        signal: dict[str, Any],
        baselines: dict[str, DeliveryBaseline],
    ) -> DetectedAnomaly | None:
        """Check delivery velocity signal for anomalies."""
        for metric in ["prs_merged", "deploys", "avg_pr_cycle_hours"]:
            value = signal.get(metric)
            if not isinstance(value, (int, float)):
                continue

            baseline = baselines.get(metric)
            if not baseline:
                continue

            ratio = float(value) / baseline.mean if baseline.mean > 0 else 0.0

            # For avg_pr_cycle_hours, lower is better, so invert the logic
            if metric == "avg_pr_cycle_hours":
                if ratio <= self.NEGATIVE_THRESHOLD:
                    return self._create_anomaly(
                        signal_id=signal.get("signal_id", ""),
                        metric=f"delivery.{metric}",
                        current_value=float(value),
                        baseline=baseline,
                        ratio=ratio,
                        direction="positive",  # Faster is positive
                        target_claw="build",
                    )
                elif ratio >= self.POSITIVE_THRESHOLD:
                    return self._create_anomaly(
                        signal_id=signal.get("signal_id", ""),
                        metric=f"delivery.{metric}",
                        current_value=float(value),
                        baseline=baseline,
                        ratio=ratio,
                        direction="negative",  # Slower is negative
                        target_claw="build",
                    )
            else:
                if ratio >= self.POSITIVE_THRESHOLD:
                    return self._create_anomaly(
                        signal_id=signal.get("signal_id", ""),
                        metric=f"delivery.{metric}",
                        current_value=float(value),
                        baseline=baseline,
                        ratio=ratio,
                        direction="positive",
                        target_claw="build",
                    )
                elif ratio <= self.NEGATIVE_THRESHOLD:
                    return self._create_anomaly(
                        signal_id=signal.get("signal_id", ""),
                        metric=f"delivery.{metric}",
                        current_value=float(value),
                        baseline=baseline,
                        ratio=ratio,
                        direction="negative",
                        target_claw="build",
                    )

        return None

    def _create_anomaly(
        self,
        signal_id: str,
        metric: str,
        current_value: float,
        baseline: ContentBaseline | RevenueBaseline | DeliveryBaseline,
        ratio: float,
        direction: Literal["positive", "negative"],
        target_claw: str,
    ) -> DetectedAnomaly:
        """Create a DetectedAnomaly object."""
        anomaly_id = str(uuid.uuid4())[:12]
        severity = self._classify_severity(ratio, direction)
        requires_attention = direction == "negative" and severity == "extreme"

        return DetectedAnomaly(
            signal_id=signal_id,
            anomaly_id=anomaly_id,
            detected_at=datetime.now(timezone.utc).isoformat(),
            metric=metric,
            current_value=current_value,
            baseline_mean=baseline.mean,
            baseline_std_dev=baseline.std_dev,
            ratio=ratio,
            direction=direction,
            severity=severity,
            requires_attention=requires_attention,
            target_claw=target_claw,
        )

    def _classify_severity(
        self,
        ratio: float,
        direction: str,
    ) -> Literal["mild", "significant", "extreme"]:
        """
        Classify anomaly severity.

        Mild: 1.5x-2x positive or 0.33x-0.5x negative
        Significant: 2x-5x positive or 0.2x-0.33x negative
        Extreme: >5x positive or <0.2x negative
        """
        if direction == "positive":
            if ratio > 5.0:
                return "extreme"
            elif ratio >= 2.0:
                return "significant"
            elif ratio >= 1.5:
                return "mild"
            return "mild"
        else:
            if ratio < 0.2:
                return "extreme"
            elif ratio <= 0.33:
                return "significant"
            elif ratio <= 0.5:
                return "mild"
            return "mild"

    def _determine_target_claw(self, anomaly_type: str) -> str:
        """
        Determine which claw should receive the anomaly alert.

        content anomaly -> "content"
        revenue anomaly -> "finance"
        delivery anomaly -> "build"
        client health anomaly -> "ops"
        """
        target_map = {
            "content": "content",
            "revenue": "finance",
            "delivery": "build",
            "client_health": "ops",
        }
        return target_map.get(anomaly_type, "content")

    def save_anomaly(self, anomaly: DetectedAnomaly) -> Path:
        """Save anomaly to file and log it."""
        path = self.fs.get_signal_path("anomalies", anomaly.anomaly_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(anomaly.to_dict(), indent=2) + "\n")

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=anomaly.detected_at,
                action_type="anomaly_detected",
                entity_id=anomaly.anomaly_id,
                source_claw=None,
                outcome="success",
                details={
                    "metric": anomaly.metric,
                    "severity": anomaly.severity,
                    "target_claw": anomaly.target_claw,
                },
            )
        )

        logger.info(
            "Detected %s %s anomaly in %s (ratio: %.2f)",
            anomaly.severity,
            anomaly.direction,
            anomaly.metric,
            anomaly.ratio,
        )

        return path

    def dispatch_alert(self, anomaly: DetectedAnomaly) -> None:
        """Dispatch alert to target claw via mesh."""
        if not self.alert_dispatcher:
            logger.warning("No alert dispatcher configured")
            return

        message_type_map = {
            "content": "revenue_anomaly"
            if "revenue" in anomaly.metric
            else "performance_intel",
            "finance": "revenue_anomaly",
            "build": "retention_signals",
            "ops": "client_health_alert",
        }

        message_type = message_type_map.get(anomaly.target_claw, "signal")

        payload = {
            "anomaly_id": anomaly.anomaly_id,
            "metric": anomaly.metric,
            "current_value": anomaly.current_value,
            "baseline_mean": anomaly.baseline_mean,
            "ratio": anomaly.ratio,
            "direction": anomaly.direction,
            "severity": anomaly.severity,
            "requires_attention": anomaly.requires_attention,
        }

        self.alert_dispatcher(message_type, anomaly.target_claw, payload)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="anomaly_alert_dispatched",
                entity_id=anomaly.anomaly_id,
                source_claw="analytics",
                outcome="success",
                details={
                    "message_type": message_type,
                    "target_claw": anomaly.target_claw,
                },
            )
        )

        logger.info(
            "Dispatched %s alert to %s for anomaly %s",
            message_type,
            anomaly.target_claw,
            anomaly.anomaly_id,
        )
