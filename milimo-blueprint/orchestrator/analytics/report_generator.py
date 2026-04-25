# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Report Generator

Generates the weekly intelligence report every Sunday at 02:00.
This is the Analytics Claw's PRIMARY OUTPUT — read by all other claws.

ATOMIC WRITE: Always writes to temp file first, then renames.
Never overwrites a good report with a partial or failed one.
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
)

logger = logging.getLogger("milimo.report_generator")


@dataclass
class WeeklyReport:
    """The weekly intelligence report."""

    generated_at: str
    week_of: str
    squad_id: str
    content_performance: dict[str, Any]
    client_health: dict[str, Any]
    revenue: dict[str, Any]
    delivery: dict[str, Any]
    opportunities: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]
    forward_projections: dict[str, Any]
    summary_narrative: str
    data_quality: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "week_of": self.week_of,
            "squad_id": self.squad_id,
            "content_performance": self.content_performance,
            "client_health": self.client_health,
            "revenue": self.revenue,
            "delivery": self.delivery,
            "opportunities": self.opportunities,
            "anomalies": self.anomalies,
            "forward_projections": self.forward_projections,
            "summary_narrative": self.summary_narrative,
            "data_quality": self.data_quality,
        }


class ReportGenerator:
    """
    Generates the weekly intelligence report every Sunday at 02:00.

    ATOMIC WRITE: Always writes to a temp file first, then renames.
    Never overwrites a successful report with a partial or failed one.
    Archives the previous report before writing the new one.
    """

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
        squad_id: str = "default",
        inference_client: Any = None,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log
        self.squad_id = squad_id
        self.inference_client = inference_client

    def generate(self) -> WeeklyReport:
        """
        Generate the weekly intelligence report.

        Full generation sequence:
        1. Aggregate content performance for past 7 days
        2. Aggregate client health signals
        3. Aggregate revenue data
        4. Aggregate delivery velocity
        5. Pull external trend data (graceful fallback)
        6. Run anomaly detection pass
        7. Run opportunity scoring pass
        8. Generate forward projections
        9. Generate summary narrative via inference
        10. Assemble complete WeeklyReport
        11. Write atomically
        12. Archive previous report
        """
        generated_at = datetime.now(timezone.utc).isoformat()
        week_of = self._get_week_of()

        logger.info("Generating weekly report for week of %s", week_of)

        content_performance = self._aggregate_content_performance()
        client_health = self._aggregate_client_health()
        revenue = self._aggregate_revenue()
        delivery = self._aggregate_delivery()

        anomalies = self._collect_recent_anomalies()
        opportunities = self._collect_opportunities()
        forward_projections = self._generate_forward_projections(
            content_performance, revenue, delivery
        )

        data_quality = {
            "content_performance": "complete"
            if content_performance.get("top_formats")
            else "insufficient",
            "client_health": "complete"
            if client_health.get("overall_score")
            else "insufficient",
            "revenue": "complete" if revenue.get("week_total") else "insufficient",
            "delivery": "complete" if delivery.get("prs_merged") else "insufficient",
        }

        summary_narrative = self._generate_narrative(
            content_performance=content_performance,
            client_health=client_health,
            revenue=revenue,
            delivery=delivery,
        )

        report = WeeklyReport(
            generated_at=generated_at,
            week_of=week_of,
            squad_id=self.squad_id,
            content_performance=content_performance,
            client_health=client_health,
            revenue=revenue,
            delivery=delivery,
            opportunities=opportunities,
            anomalies=anomalies,
            forward_projections=forward_projections,
            summary_narrative=summary_narrative,
            data_quality=data_quality,
        )

        self.write_atomically(report)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=generated_at,
                action_type="report_generated",
                entity_id=week_of,
                source_claw=None,
                outcome="success",
                details={
                    "week_of": week_of,
                    "anomalies_count": len(anomalies),
                    "opportunities_count": len(opportunities),
                },
            )
        )

        logger.info("Generated weekly report for week of %s", week_of)

        return report

    def write_atomically(self, report: WeeklyReport) -> None:
        """
        Write report atomically.

        1. Serialize to JSON
        2. Write to temp file
        3. Validate JSON is parseable
        4. Archive existing report if present
        5. Rename temp to final path
        """
        report_path = self.fs.get_report_path()
        archive_dir = self.fs.base / "reports" / "weekly-intelligence-archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        report_json = json.dumps(report.to_dict(), indent=2)

        try:
            json.loads(report_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Generated invalid JSON: {e}")

        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="weekly-report-",
            dir=report_path.parent,
        )

        try:
            with open(temp_fd, "w") as f:
                f.write(report_json)
                f.write("\n")

            if report_path.exists():
                date_str = report.week_of
                archive_path = archive_dir / f"{date_str}.json"
                shutil.copy2(report_path, archive_path)
                logger.debug("Archived previous report to %s", archive_path)

            shutil.move(temp_path, report_path)
            logger.info("Wrote report to %s", report_path)

        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise

    def _get_week_of(self) -> str:
        """Get the Monday date of the current week."""
        now = datetime.now(timezone.utc)
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)
        return monday.strftime("%Y-%m-%d")

    def _aggregate_content_performance(self, days: int = 7) -> dict[str, Any]:
        """Aggregate content performance data for the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        data_dir = self.fs.get_data_path("content-performance")

        format_engagement: dict[str, list[float]] = {}
        platform_engagement: dict[str, list[float]] = {}
        time_engagement: dict[int, list[float]] = {}
        worst_performing: list[dict[str, Any]] = []

        if data_dir.exists():
            for platform_dir in data_dir.iterdir():
                if not platform_dir.is_dir():
                    continue
                platform = platform_dir.name

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
                                    try:
                                        record_time = datetime.fromisoformat(
                                            received_at
                                        )
                                        if record_time < cutoff:
                                            continue
                                    except ValueError:
                                        continue

                                    content_type = record.get("content_type", "unknown")
                                    engagement_data = record.get("engagement_data", {})
                                    engagement_rate = engagement_data.get(
                                        "engagement_rate"
                                    )

                                    if isinstance(engagement_rate, (int, float)):
                                        if content_type not in format_engagement:
                                            format_engagement[content_type] = []
                                        format_engagement[content_type].append(
                                            float(engagement_rate)
                                        )

                                        if platform not in platform_engagement:
                                            platform_engagement[platform] = []
                                        platform_engagement[platform].append(
                                            float(engagement_rate)
                                        )

                                        publish_time = record.get("publish_time", "")
                                        if publish_time:
                                            try:
                                                hour = datetime.fromisoformat(
                                                    publish_time
                                                ).hour
                                                if hour not in time_engagement:
                                                    time_engagement[hour] = []
                                                time_engagement[hour].append(
                                                    float(engagement_rate)
                                                )
                                            except ValueError:
                                                pass

                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.warning("Failed to read %s: %s", perf_file, e)

        top_formats = []
        for content_type, rates in format_engagement.items():
            if rates:
                avg = sum(rates) / len(rates)
                top_formats.append(
                    {
                        "format": content_type,
                        "avg_engagement": round(avg, 4),
                        "sample_count": len(rates),
                    }
                )
        top_formats.sort(key=lambda x: x["avg_engagement"], reverse=True)

        top_platforms = []
        for platform, rates in platform_engagement.items():
            if rates:
                avg = sum(rates) / len(rates)
                top_platforms.append(
                    {
                        "platform": platform,
                        "avg_engagement": round(avg, 4),
                        "sample_count": len(rates),
                    }
                )
        top_platforms.sort(key=lambda x: x["avg_engagement"], reverse=True)

        top_times = []
        for hour, rates in time_engagement.items():
            if rates:
                avg = sum(rates) / len(rates)
                top_times.append(
                    {
                        "hour": hour,
                        "avg_engagement": round(avg, 4),
                        "sample_count": len(rates),
                    }
                )
        top_times.sort(key=lambda x: x["avg_engagement"], reverse=True)
        top_times = top_times[:5]

        return {
            "top_formats": top_formats[:10],
            "top_platforms": top_platforms,
            "top_publish_times": top_times,
            "worst_performing": worst_performing,
            "platform_algorithm_notes": "",
        }

    def _aggregate_client_health(self, days: int = 7) -> dict[str, Any]:
        """Aggregate client health data."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        health_dir = self.fs.get_data_path("client-health")

        all_scores: list[float] = []
        client_scores: dict[str, list[float]] = {}
        at_risk_clients: list[dict[str, Any]] = []
        healthy_clients: list[dict[str, Any]] = []

        if health_dir.exists():
            for client_dir in health_dir.iterdir():
                if not client_dir.is_dir():
                    continue
                client_id = client_dir.name

                health_file = client_dir / "health-history.jsonl"
                if not health_file.exists():
                    continue

                try:
                    with open(health_file) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                received_at = record.get("received_at", "")
                                try:
                                    record_time = datetime.fromisoformat(received_at)
                                    if record_time < cutoff:
                                        continue
                                except ValueError:
                                    continue

                                score = record.get("health_score")
                                if isinstance(score, (int, float)):
                                    all_scores.append(float(score))
                                    if client_id not in client_scores:
                                        client_scores[client_id] = []
                                    client_scores[client_id].append(float(score))

                            except json.JSONDecodeError:
                                continue
                except Exception:
                    continue

        for client_id, scores in client_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score < 6.0:
                    at_risk_clients.append(
                        {
                            "client_id": client_id,
                            "score": round(avg_score, 1),
                            "risk_factor": "Low health score",
                        }
                    )
                elif avg_score >= 8.0:
                    healthy_clients.append(
                        {
                            "client_id": client_id,
                            "score": round(avg_score, 1),
                        }
                    )

        overall_score = (
            round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
        )

        return {
            "overall_score": overall_score,
            "at_risk_clients": at_risk_clients,
            "healthy_clients": healthy_clients,
            "new_signals": [],
        }

    def _aggregate_revenue(self, days: int = 7) -> dict[str, Any]:
        """Aggregate revenue data."""
        revenue_path = self.fs.get_data_path("revenue", "weekly-revenue.jsonl")

        latest_record: dict[str, Any] | None = None
        previous_record: dict[str, Any] | None = None

        if revenue_path.exists():
            records: list[dict[str, Any]] = []
            try:
                with open(revenue_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

                if records:
                    records.sort(key=lambda x: x.get("received_at", ""), reverse=True)
                    latest_record = records[0]
                    if len(records) > 1:
                        previous_record = records[1]
            except Exception as e:
                logger.warning("Failed to read revenue data: %s", e)

        if latest_record:
            week_total = latest_record.get("week_total", 0)
            previous_total = (
                previous_record.get("week_total", week_total)
                if previous_record
                else week_total
            )
            wow_pct = 0.0
            if previous_total > 0:
                wow_pct = round(
                    ((week_total - previous_total) / previous_total) * 100, 1
                )

            return {
                "week_total": week_total,
                "week_over_week_pct": wow_pct,
                "invoices_paid": latest_record.get("invoices_paid", 0),
                "invoices_pending": latest_record.get("invoices_pending", 0),
                "pipeline_value": latest_record.get("pipeline_value", 0),
                "anomalies": [],
            }

        return {
            "week_total": 0,
            "week_over_week_pct": 0.0,
            "invoices_paid": 0,
            "invoices_pending": 0,
            "pipeline_value": 0,
            "anomalies": [],
        }

    def _aggregate_delivery(self, days: int = 7) -> dict[str, Any]:
        """Aggregate delivery velocity data."""
        delivery_path = self.fs.get_data_path("delivery-velocity", "velocity.jsonl")

        prs_merged = 0
        deploys = 0
        avg_pr_cycle_hours: list[float] = []

        if delivery_path.exists():
            try:
                with open(delivery_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            prs_merged += record.get("prs_merged", 0)
                            deploys += record.get("deploys", 0)
                            cycle = record.get("avg_pr_cycle_hours")
                            if isinstance(cycle, (int, float)):
                                avg_pr_cycle_hours.append(float(cycle))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning("Failed to read delivery data: %s", e)

        avg_cycle = (
            round(sum(avg_pr_cycle_hours) / len(avg_pr_cycle_hours), 1)
            if avg_pr_cycle_hours
            else 0.0
        )

        return {
            "prs_merged": prs_merged,
            "deploys": deploys,
            "avg_pr_cycle_hours": avg_cycle,
            "open_issues": 0,
            "velocity_vs_baseline": "+0%",
        }

    def _generate_narrative(
        self,
        content_performance: dict[str, Any],
        client_health: dict[str, Any],
        revenue: dict[str, Any],
        delivery: dict[str, Any],
    ) -> str:
        """
        Generate summary narrative.

        Inference call with data_type="report_narrative_generation".
        Falls back to rule-based narrative if inference fails.
        """
        if self.inference_client:
            try:
                prompt = self._build_narrative_prompt(
                    content_performance, client_health, revenue, delivery
                )
                response = self.inference_client.complete(
                    prompt=prompt,
                    data_type="report_narrative_generation",
                    max_tokens=500,
                )
                if response:
                    return response.strip()
            except Exception as e:
                logger.warning("Inference failed, using fallback: %s", e)

        return self._fallback_narrative(
            content_performance, client_health, revenue, delivery
        )

    def _build_narrative_prompt(
        self,
        content_performance: dict[str, Any],
        client_health: dict[str, Any],
        revenue: dict[str, Any],
        delivery: dict[str, Any],
    ) -> str:
        """Build the prompt for narrative generation."""
        top_format = content_performance.get("top_formats", [])
        top_platform = content_performance.get("top_platforms", [])

        return f"""Generate a 3-4 sentence summary of this week's performance for a solo founder's analytics dashboard:

- Top content format: {top_format[0]["format"] if top_format else "N/A"} ({top_format[0].get("avg_engagement", 0):.2%} avg engagement)
- Top platform: {top_platform[0]["platform"] if top_platform else "N/A"}
- Client health score: {client_health.get("overall_score", 0):.1f}/10
- Revenue: ${revenue.get("week_total", 0):,.0f} ({revenue.get("week_over_week_pct", 0):+.1f}% WoW)
- Delivery: {delivery.get("prs_merged", 0)} PRs merged, {delivery.get("deploys", 0)} deploys

Write in a professional but friendly tone. Be specific with numbers. End with one actionable recommendation."""

    def _fallback_narrative(
        self,
        content_performance: dict[str, Any],
        client_health: dict[str, Any],
        revenue: dict[str, Any],
        delivery: dict[str, Any],
    ) -> str:
        """Generate a rule-based fallback narrative."""
        parts = []

        top_formats = content_performance.get("top_formats", [])
        if top_formats:
            parts.append(
                f"{top_formats[0]['format']} was your top content format "
                f"with {top_formats[0]['avg_engagement']:.2%} avg engagement."
            )

        score = client_health.get("overall_score", 0)
        if score > 0:
            status = (
                "strong"
                if score >= 8.0
                else "needs attention"
                if score < 6.0
                else "stable"
            )
            parts.append(f"Client health is {status} at {score:.1f}/10.")

        wow = revenue.get("week_over_week_pct", 0)
        total = revenue.get("week_total", 0)
        if total > 0:
            direction = "up" if wow > 0 else "down" if wow < 0 else "flat"
            parts.append(
                f"Weekly revenue ${total:,.0f} is {direction} ({wow:+.1f}% WoW)."
            )

        prs = delivery.get("prs_merged", 0)
        if prs > 0:
            parts.append(f"Engineering shipped {prs} PRs this week.")

        if not parts:
            return "Insufficient data for this week's analysis. Check back after more signals are collected."

        return " ".join(parts)

    def _collect_recent_anomalies(self) -> list[dict[str, Any]]:
        """Collect recent anomalies for the report."""
        anomalies_dir = self.fs.base / "signals" / "anomalies"
        anomalies: list[dict[str, Any]] = []

        if anomalies_dir.exists():
            for anomaly_file in sorted(anomalies_dir.glob("*.json"), reverse=True)[:10]:
                try:
                    data = json.loads(anomaly_file.read_text())
                    anomalies.append(data)
                except Exception:
                    continue

        return anomalies

    def _collect_opportunities(self) -> list[dict[str, Any]]:
        """Collect scored opportunities."""
        opp_path = self.fs.base / "reports" / "opportunity-scores.json"

        if opp_path.exists():
            try:
                data = json.loads(opp_path.read_text())
                return data.get("opportunities", [])
            except Exception:
                pass

        return []

    def _generate_forward_projections(
        self,
        content_performance: dict[str, Any],
        revenue: dict[str, Any],
        delivery: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate forward projections (simplified for now)."""
        week_total = revenue.get("week_total", 0)
        wow_pct = revenue.get("week_over_week_pct", 0)

        projected_revenue = week_total * (1 + wow_pct / 100) if wow_pct else week_total

        return {
            "next_week_revenue_estimate": round(projected_revenue, 2),
            "confidence_interval": [
                round(projected_revenue * 0.85, 2),
                round(projected_revenue * 1.15, 2),
            ],
            "next_week_risk_flags": [],
        }

    def _generate_empty_report(self, reason: str) -> WeeklyReport:
        """Generate an empty report when data is insufficient."""
        week_of = self._get_week_of()

        return WeeklyReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            week_of=week_of,
            squad_id=self.squad_id,
            content_performance={
                "top_formats": [],
                "top_platforms": [],
                "top_publish_times": [],
            },
            client_health={
                "overall_score": 0,
                "at_risk_clients": [],
                "healthy_clients": [],
            },
            revenue={"week_total": 0, "week_over_week_pct": 0},
            delivery={"prs_merged": 0, "deploys": 0},
            opportunities=[],
            anomalies=[],
            forward_projections={},
            summary_narrative=f"Insufficient data for analysis. {reason}",
            data_quality={
                "content_performance": "insufficient",
                "client_health": "insufficient",
                "revenue": "insufficient",
                "delivery": "insufficient",
            },
        )
