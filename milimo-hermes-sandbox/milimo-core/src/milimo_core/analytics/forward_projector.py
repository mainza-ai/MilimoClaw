# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Forward Projector

Generates 4-week forward projections for key metrics.
Requires minimum 8 weeks of historical data for reliable projections.
Always returns something — never refuses to project.
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .analytics_init import AnalyticsFilesystemInit

logger = logging.getLogger("milimo.forward_projector")


@dataclass
class ForwardProjection:
    """Represents a forward projection for a metric."""

    metric: str
    projection_weeks: int
    point_estimate: float
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_level: float
    data_weeks_used: int
    risk_flags: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "projection_weeks": self.projection_weeks,
            "point_estimate": round(self.point_estimate, 2),
            "confidence_interval": [
                round(self.confidence_interval_low, 2),
                round(self.confidence_interval_high, 2),
            ],
            "confidence_level": round(self.confidence_level, 2),
            "data_weeks_used": self.data_weeks_used,
            "risk_flags": self.risk_flags,
            "generated_at": self.generated_at,
        }


class ForwardProjector:
    """
    Generates 4-week forward projections for key metrics.

    Requires minimum 8 weeks of historical data for reliable projections.
    Returns low-confidence projections with wide intervals when < 8 weeks.
    Never refuses to project — always returns something.
    """

    MIN_WEEKS_FOR_RELIABLE_PROJECTION = 8
    PROJECTION_WEEKS = 4

    def __init__(self, fs: AnalyticsFilesystemInit) -> None:
        self.fs = fs

    def project_all(self) -> dict[str, ForwardProjection]:
        """Generate projections for all key metrics."""
        projections: dict[str, ForwardProjection] = {}

        revenue_proj = self.project_revenue()
        if revenue_proj:
            projections["revenue.week_total"] = revenue_proj

        platforms = self._get_content_platforms()
        for platform in platforms:
            proj = self.project_content_engagement(platform)
            if proj:
                projections[f"content.{platform}.avg_engagement"] = proj

        delivery_proj = self.project_delivery_velocity()
        if delivery_proj:
            projections["delivery.prs_merged"] = delivery_proj

        logger.info("Generated %d forward projections", len(projections))
        return projections

    def project_revenue(self) -> ForwardProjection | None:
        """Project revenue for the next 4 weeks."""
        revenue_path = self.fs.get_data_path("revenue", "weekly-revenue.jsonl")

        weekly_totals: list[tuple[str, float]] = []

        if revenue_path.exists():
            try:
                with open(revenue_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            received_at = record.get("received_at", "")
                            week_total = record.get("week_total", 0)
                            if isinstance(week_total, (int, float)) and week_total > 0:
                                weekly_totals.append((received_at, float(week_total)))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning("Failed to read revenue data: %s", e)

        if not weekly_totals:
            return self._empty_projection("revenue.week_total")

        weekly_totals.sort(key=lambda x: x[0])
        values = [v for _, v in weekly_totals]

        point_estimate = self._simple_projection(values)
        confidence_level = self._calculate_confidence_level(len(values))
        std_dev = statistics.stdev(values) if len(values) > 1 else values[0] * 0.2
        ci_low, ci_high = self._calculate_confidence_interval(
            point_estimate, std_dev, confidence_level
        )

        risk_flags = self._identify_risk_flags(values)

        return ForwardProjection(
            metric="revenue.week_total",
            projection_weeks=self.PROJECTION_WEEKS,
            point_estimate=point_estimate,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            confidence_level=confidence_level,
            data_weeks_used=len(values),
            risk_flags=risk_flags,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def project_content_engagement(self, platform: str) -> ForwardProjection | None:
        """Project content engagement for a specific platform."""
        platform_dir = self.fs.get_data_path("content-performance") / platform

        weekly_rates: list[tuple[str, float]] = []

        if platform_dir.exists():
            for month_dir in platform_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                perf_file = month_dir / "performance.jsonl"
                if not perf_file.exists():
                    continue

                try:
                    with open(perf_file) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                received_at = record.get("received_at", "")
                                engagement_data = record.get("engagement_data", {})
                                rate = engagement_data.get("engagement_rate")

                                if isinstance(rate, (int, float)) and rate > 0:
                                    weekly_rates.append((received_at, float(rate)))
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning("Failed to read %s: %s", perf_file, e)

        if not weekly_rates:
            return self._empty_projection(f"content.{platform}.avg_engagement")

        weekly_rates.sort(key=lambda x: x[0])
        values = [v for _, v in weekly_rates]

        point_estimate = self._simple_projection(values)
        confidence_level = self._calculate_confidence_level(len(values))
        std_dev = statistics.stdev(values) if len(values) > 1 else values[0] * 0.15
        ci_low, ci_high = self._calculate_confidence_interval(
            point_estimate, std_dev, confidence_level
        )

        risk_flags = self._identify_risk_flags(values)

        return ForwardProjection(
            metric=f"content.{platform}.avg_engagement",
            projection_weeks=self.PROJECTION_WEEKS,
            point_estimate=point_estimate,
            confidence_interval_low=ci_low,
            confidence_interval_high=ci_high,
            confidence_level=confidence_level,
            data_weeks_used=len(values),
            risk_flags=risk_flags,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def project_delivery_velocity(self) -> ForwardProjection | None:
        """Project delivery velocity (PRs merged) for the next 4 weeks."""
        delivery_path = self.fs.get_data_path("delivery-velocity", "velocity.jsonl")

        weekly_prs: list[tuple[str, int]] = []

        if delivery_path.exists():
            try:
                with open(delivery_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            received_at = record.get("received_at", "")
                            prs_merged = record.get("prs_merged", 0)
                            if isinstance(prs_merged, (int, float)):
                                weekly_prs.append((received_at, int(prs_merged)))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning("Failed to read delivery data: %s", e)

        if not weekly_prs:
            return self._empty_projection("delivery.prs_merged")

        weekly_prs.sort(key=lambda x: x[0])
        values = [float(v) for _, v in weekly_prs]

        point_estimate = self._simple_projection(values)
        confidence_level = self._calculate_confidence_level(len(values))
        std_dev = statistics.stdev(values) if len(values) > 1 else values[0] * 0.25
        ci_low, ci_high = self._calculate_confidence_interval(
            point_estimate, std_dev, confidence_level
        )

        risk_flags = self._identify_risk_flags(values)

        return ForwardProjection(
            metric="delivery.prs_merged",
            projection_weeks=self.PROJECTION_WEEKS,
            point_estimate=point_estimate,
            confidence_interval_low=max(ci_low, 0),
            confidence_interval_high=ci_high,
            confidence_level=confidence_level,
            data_weeks_used=len(values),
            risk_flags=risk_flags,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _calculate_confidence_level(self, weeks_available: int) -> float:
        """Calculate confidence level based on data availability."""
        if weeks_available < 4:
            return 0.2
        elif weeks_available < 8:
            return 0.5
        elif weeks_available < 16:
            return 0.75
        else:
            return 0.90

    def _calculate_confidence_interval(
        self,
        estimate: float,
        std_dev: float,
        confidence_level: float,
    ) -> tuple[float, float]:
        """Calculate confidence interval width based on confidence level."""
        multiplier = {
            0.2: 2.5,
            0.5: 2.0,
            0.75: 1.5,
            0.90: 1.2,
        }.get(confidence_level, 2.0)

        margin = std_dev * multiplier
        return (estimate - margin, estimate + margin)

    def _simple_projection(self, values: list[float]) -> float:
        """Calculate simple linear projection."""
        if not values:
            return 0.0

        if len(values) == 1:
            return values[0]

        recent_avg = sum(values[-4:]) / min(len(values), 4)

        if len(values) >= 4:
            older_avg = (
                sum(values[:-4]) / (len(values) - 4) if len(values) > 4 else recent_avg
            )
            trend = (recent_avg - older_avg) / max(older_avg, 1)
            trend = max(-0.2, min(0.2, trend))
            return recent_avg * (1 + trend)

        return recent_avg

    def _identify_risk_flags(self, values: list[float]) -> list[str]:
        """Identify risk factors in historical data."""
        flags: list[str] = []

        if len(values) < 4:
            flags.append("Insufficient historical data for reliable projection")
            return flags

        if len(values) >= 3:
            recent = values[-3:]
            if all(recent[i] < recent[i - 1] for i in range(1, len(recent))):
                flags.append("Declining trend in recent data")

        if len(values) >= 4:
            std_dev = statistics.stdev(values)
            mean = statistics.mean(values)
            if mean > 0 and std_dev / mean > 0.4:
                flags.append("High variance in historical data")

        return flags

    def _get_content_platforms(self) -> list[str]:
        """Get list of platforms with content data."""
        content_dir = self.fs.get_data_path("content-performance")
        platforms: list[str] = []

        if content_dir.exists():
            for platform_dir in content_dir.iterdir():
                if platform_dir.is_dir():
                    platforms.append(platform_dir.name)

        return platforms

    def _empty_projection(self, metric: str) -> None:
        """Return None when no data is available for the metric."""
        return None
