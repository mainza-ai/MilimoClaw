# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Opportunity Scorer

Identifies growth opportunities by comparing squad performance
against external trend signals and internal capability assessment.

Runs daily at 06:00. High-confidence opportunities (>0.85) dispatched immediately.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
)

logger = logging.getLogger("milimo.opportunity_scorer")


@dataclass
class ScoredOpportunity:
    """Represents a scored growth opportunity."""

    opportunity_id: str
    detected_at: str
    type: str  # content_format, client_segment, platform_timing, pricing_adjustment
    description: str
    confidence: float
    potential_impact: str  # "low", "medium", "high"
    squad_readiness: float
    recommended_action: str
    target_claw: str
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "detected_at": self.detected_at,
            "type": self.type,
            "description": self.description,
            "confidence": self.confidence,
            "potential_impact": self.potential_impact,
            "squad_readiness": self.squad_readiness,
            "recommended_action": self.recommended_action,
            "target_claw": self.target_claw,
            "expires_at": self.expires_at,
        }


class OpportunityScorer:
    """
    Identifies growth opportunities by comparing squad performance
    against external trend signals and internal capability assessment.

    Runs daily at 06:00. High-confidence opportunities (>0.85) dispatched immediately.
    All opportunities written to reports/opportunity-scores.json.
    """

    IMMEDIATE_DISPATCH_THRESHOLD = 0.85
    MIN_CONFIDENCE_THRESHOLD = 0.3

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
        inference_client: Any = None,
        dispatcher: Callable[[str, str, dict], None] | None = None,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log
        self.inference_client = inference_client
        self.dispatcher = dispatcher

    def score_all(self) -> list[ScoredOpportunity]:
        """Run all scoring passes and return filtered, sorted opportunities."""
        all_opportunities: list[ScoredOpportunity] = []

        all_opportunities.extend(self.content_format_opportunities())
        all_opportunities.extend(self.platform_timing_opportunities())
        all_opportunities.extend(self.client_segment_opportunities())

        filtered = [
            o
            for o in all_opportunities
            if o.confidence >= self.MIN_CONFIDENCE_THRESHOLD
        ]
        filtered.sort(key=lambda x: x.confidence, reverse=True)

        self.write_opportunity_scores(filtered)

        high_confidence = [
            o for o in filtered if o.confidence >= self.IMMEDIATE_DISPATCH_THRESHOLD
        ]
        for opp in high_confidence:
            self.dispatch_high_confidence(opp)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="opportunity_scoring_complete",
                entity_id="daily",
                source_claw=None,
                outcome="success",
                details={
                    "total_opportunities": len(all_opportunities),
                    "filtered_opportunities": len(filtered),
                    "dispatched_immediately": len(high_confidence),
                },
            )
        )

        logger.info(
            "Scored %d opportunities, %d above threshold, %d dispatched immediately",
            len(all_opportunities),
            len(filtered),
            len(high_confidence),
        )

        return filtered

    def content_format_opportunities(self) -> list[ScoredOpportunity]:
        """
        Compare squad's content type distribution against trend data.
        Identify formats with high trend signal that squad uses rarely.
        """
        opportunities: list[ScoredOpportunity] = []
        data_dir = self.fs.get_data_path("content-performance")

        format_counts: dict[str, int] = {}
        format_engagement: dict[str, list[float]] = {}

        if data_dir.exists():
            for platform_dir in data_dir.iterdir():
                if not platform_dir.is_dir():
                    continue

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
                                    content_type = record.get("content_type", "unknown")
                                    engagement_data = record.get("engagement_data", {})
                                    engagement_rate = engagement_data.get(
                                        "engagement_rate", 0
                                    )

                                    format_counts[content_type] = (
                                        format_counts.get(content_type, 0) + 1
                                    )
                                    if content_type not in format_engagement:
                                        format_engagement[content_type] = []
                                    if isinstance(engagement_rate, (int, float)):
                                        format_engagement[content_type].append(
                                            float(engagement_rate)
                                        )
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.warning("Failed to read %s: %s", perf_file, e)

        total_content = sum(format_counts.values()) if format_counts else 0

        trend_data = self._get_trend_data()

        for content_type, trend_score in trend_data.items():
            usage_ratio = (
                (format_counts.get(content_type, 0) / total_content)
                if total_content > 0
                else 0
            )

            if trend_score > 0.7 and usage_ratio < 0.1:
                avg_engagement = 0.0
                if (
                    content_type in format_engagement
                    and format_engagement[content_type]
                ):
                    avg_engagement = sum(format_engagement[content_type]) / len(
                        format_engagement[content_type]
                    )

                confidence = self._calculate_content_confidence(
                    trend_score, usage_ratio, avg_engagement
                )

                if confidence >= self.MIN_CONFIDENCE_THRESHOLD:
                    description = f"{content_type} trending but underutilized by squad"
                    recommended_action = (
                        f"Increase {content_type} output to capture trend momentum"
                    )

                    opp = ScoredOpportunity(
                        opportunity_id=str(uuid.uuid4())[:12],
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        type="content_format",
                        description=description,
                        confidence=confidence,
                        potential_impact="high" if trend_score > 0.85 else "medium",
                        squad_readiness=0.8 if avg_engagement > 0 else 0.5,
                        recommended_action=recommended_action,
                        target_claw="content",
                        expires_at=(
                            datetime.now(timezone.utc) + timedelta(days=14)
                        ).isoformat(),
                    )
                    opportunities.append(opp)

        return opportunities

    def platform_timing_opportunities(self) -> list[ScoredOpportunity]:
        """
        Analyze squad's publishing time distribution vs engagement peaks.
        Identify timing gaps where engagement could improve.
        """
        opportunities: list[ScoredOpportunity] = []
        data_dir = self.fs.get_data_path("content-performance")

        hour_engagement: dict[int, list[float]] = {}
        hour_counts: dict[int, int] = {}

        if data_dir.exists():
            for platform_dir in data_dir.iterdir():
                if not platform_dir.is_dir():
                    continue

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
                                    publish_time = record.get("publish_time", "")
                                    engagement_data = record.get("engagement_data", {})
                                    engagement_rate = engagement_data.get(
                                        "engagement_rate"
                                    )

                                    if publish_time and isinstance(
                                        engagement_rate, (int, float)
                                    ):
                                        try:
                                            hour = datetime.fromisoformat(
                                                publish_time
                                            ).hour
                                            if hour not in hour_engagement:
                                                hour_engagement[hour] = []
                                            hour_engagement[hour].append(
                                                float(engagement_rate)
                                            )
                                            hour_counts[hour] = (
                                                hour_counts.get(hour, 0) + 1
                                            )
                                        except ValueError:
                                            continue
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.warning("Failed to read %s: %s", perf_file, e)

        if hour_engagement:
            avg_by_hour = {
                h: sum(rates) / len(rates) for h, rates in hour_engagement.items()
            }

            if avg_by_hour:
                sorted_hours = sorted(
                    avg_by_hour.items(), key=lambda x: x[1], reverse=True
                )
                best_hours = [h for h, _ in sorted_hours[:3]]

                total_posts = sum(hour_counts.values())
                best_hour_usage = (
                    sum(hour_counts.get(h, 0) for h in best_hours) / total_posts
                    if total_posts > 0
                    else 0
                )

                if best_hour_usage < 0.3 and len(sorted_hours) >= 2:
                    best_hour = sorted_hours[0][0]
                    opp = ScoredOpportunity(
                        opportunity_id=str(uuid.uuid4())[:12],
                        detected_at=datetime.now(timezone.utc).isoformat(),
                        type="platform_timing",
                        description=f"Best engagement at hour {best_hour}:00 but only {best_hour_usage:.0%} of posts published then",
                        confidence=0.75,
                        potential_impact="medium",
                        squad_readiness=0.9,
                        recommended_action=f"Shift publishing schedule to prioritize hours {', '.join(str(h) + ':00' for h in best_hours)}",
                        target_claw="content",
                    )
                    opportunities.append(opp)

        return opportunities

    def client_segment_opportunities(self) -> list[ScoredOpportunity]:
        """
        Analyze client health distribution.
        Identify segments with strong health scores (potential for expansion).
        """
        opportunities: list[ScoredOpportunity] = []
        health_dir = self.fs.get_data_path("client-health")

        healthy_clients: list[dict[str, Any]] = []
        at_risk_clients: list[dict[str, Any]] = []

        if health_dir.exists():
            for client_dir in health_dir.iterdir():
                if not client_dir.is_dir():
                    continue

                client_id = client_dir.name
                health_file = client_dir / "health-history.jsonl"

                if not health_file.exists():
                    continue

                try:
                    scores: list[float] = []
                    with open(health_file) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                score = record.get("health_score")
                                if isinstance(score, (int, float)):
                                    scores.append(float(score))
                            except json.JSONDecodeError:
                                continue

                    if scores:
                        avg_score = sum(scores) / len(scores)
                        if avg_score >= 8.0:
                            healthy_clients.append(
                                {
                                    "client_id": client_id,
                                    "score": avg_score,
                                }
                            )
                        elif avg_score < 6.0:
                            at_risk_clients.append(
                                {
                                    "client_id": client_id,
                                    "score": avg_score,
                                }
                            )
                except Exception as e:
                    logger.warning("Failed to read %s: %s", health_file, e)

        if healthy_clients:
            if len(healthy_clients) >= 3:
                opp = ScoredOpportunity(
                    opportunity_id=str(uuid.uuid4())[:12],
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    type="client_segment",
                    description=f"{len(healthy_clients)} clients with health score >= 8.0 — expansion opportunity",
                    confidence=0.8,
                    potential_impact="high",
                    squad_readiness=0.7,
                    recommended_action="Propose upsell or referral request to top healthy clients",
                    target_claw="ops",
                )
                opportunities.append(opp)

        if at_risk_clients:
            opp = ScoredOpportunity(
                opportunity_id=str(uuid.uuid4())[:12],
                detected_at=datetime.now(timezone.utc).isoformat(),
                type="client_segment",
                description=f"{len(at_risk_clients)} at-risk clients (score < 6.0) need attention",
                confidence=0.9,
                potential_impact="high",
                squad_readiness=0.6,
                recommended_action="Prioritize check-ins for at-risk clients",
                target_claw="ops",
            )
            opportunities.append(opp)

        return opportunities

    def dispatch_high_confidence(self, opportunity: ScoredOpportunity) -> None:
        """Dispatch high-confidence opportunity to target claw."""
        if not self.dispatcher:
            logger.warning(
                "No dispatcher configured for opportunity %s",
                opportunity.opportunity_id,
            )
            return

        message_type_map = {
            "content_format": "performance_intel",
            "platform_timing": "performance_intel",
            "client_segment": "retention_signals",
            "pricing_adjustment": "revenue_anomaly",
        }

        message_type = message_type_map.get(opportunity.type, "signal")

        payload = {
            "opportunity_id": opportunity.opportunity_id,
            "type": opportunity.type,
            "description": opportunity.description,
            "confidence": opportunity.confidence,
            "recommended_action": opportunity.recommended_action,
        }

        self.dispatcher(message_type, opportunity.target_claw, payload)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="opportunity_dispatched",
                entity_id=opportunity.opportunity_id,
                source_claw="analytics",
                outcome="success",
                details={
                    "message_type": message_type,
                    "target_claw": opportunity.target_claw,
                    "confidence": opportunity.confidence,
                },
            )
        )

        logger.info(
            "Dispatched opportunity %s to %s (confidence: %.2f)",
            opportunity.opportunity_id,
            opportunity.target_claw,
            opportunity.confidence,
        )

    def write_opportunity_scores(self, opportunities: list[ScoredOpportunity]) -> None:
        """Write all opportunities to opportunity-scores.json."""
        opp_path = self.fs.base / "reports" / "opportunity-scores.json"
        opp_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "opportunities": [o.to_dict() for o in opportunities],
            "total_count": len(opportunities),
            "high_confidence_count": len(
                [
                    o
                    for o in opportunities
                    if o.confidence >= self.IMMEDIATE_DISPATCH_THRESHOLD
                ]
            ),
        }

        opp_path.write_text(json.dumps(data, indent=2) + "\n")
        logger.debug("Wrote %d opportunities to %s", len(opportunities), opp_path)

    def _get_trend_data(self) -> dict[str, float]:
        """Get mock trend data for content formats."""
        return {
            "carousel": 0.85,
            "short_video": 0.92,
            "long_form": 0.45,
            "infographic": 0.72,
            "thread": 0.68,
        }

    def _calculate_content_confidence(
        self,
        trend_score: float,
        usage_ratio: float,
        avg_engagement: float,
    ) -> float:
        """Calculate confidence score for content format opportunity."""
        trend_factor = trend_score * 0.4
        gap_factor = (1 - usage_ratio) * 0.3
        engagement_factor = (
            min(avg_engagement / 0.1, 1.0) * 0.3 if avg_engagement > 0 else 0.15
        )

        return min(trend_factor + gap_factor + engagement_factor, 1.0)
