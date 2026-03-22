#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Baseline Manager

Calculates and maintains 30-day rolling baselines for all tracked metrics.
Runs full recalculation every Sunday at 01:00 (before report generation).
Baselines are required for anomaly detection to produce reliable results.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .analytics_init import AnalyticsFilesystemInit

logger = logging.getLogger("milimo.baseline_manager")


@dataclass
class ContentBaseline:
    """Baseline for a content metric."""

    platform: str
    content_type: str
    metric: str
    mean: float
    std_dev: float
    sample_count: int
    window_days: int
    calculated_at: str
    upper_anomaly_threshold: float
    lower_anomaly_threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "content_type": self.content_type,
            "metric": self.metric,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "sample_count": self.sample_count,
            "window_days": self.window_days,
            "calculated_at": self.calculated_at,
            "upper_anomaly_threshold": self.upper_anomaly_threshold,
            "lower_anomaly_threshold": self.lower_anomaly_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContentBaseline":
        return cls(**data)


@dataclass
class RevenueBaseline:
    """Baseline for a revenue metric."""

    metric: str
    mean: float
    std_dev: float
    sample_count: int
    calculated_at: str
    upper_anomaly_threshold: float
    lower_anomaly_threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "sample_count": self.sample_count,
            "calculated_at": self.calculated_at,
            "upper_anomaly_threshold": self.upper_anomaly_threshold,
            "lower_anomaly_threshold": self.lower_anomaly_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RevenueBaseline":
        return cls(**data)


@dataclass
class DeliveryBaseline:
    """Baseline for a delivery velocity metric."""

    metric: str
    mean: float
    std_dev: float
    sample_count: int
    calculated_at: str
    upper_anomaly_threshold: float
    lower_anomaly_threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "sample_count": self.sample_count,
            "calculated_at": self.calculated_at,
            "upper_anomaly_threshold": self.upper_anomaly_threshold,
            "lower_anomaly_threshold": self.lower_anomaly_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliveryBaseline":
        return cls(**data)


class BaselineManager:
    """
    Calculates and maintains 30-day rolling baselines for all tracked metrics.

    Runs full recalculation every Sunday at 01:00 (before report generation).
    Baselines are required before anomaly detection can produce reliable results.
    Returns None baselines when insufficient data exists.
    """

    WINDOW_DAYS = 30
    MIN_SAMPLES = 5

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: Any = None,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log

    def recalculate_all(self) -> dict[str, Any]:
        """
        Recalculate all baselines from stored JSONL data.

        Returns summary of sample counts for all metrics.
        """
        results: dict[str, Any] = {
            "content": {},
            "revenue": {},
            "delivery": {},
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

        content_baselines = self.recalculate_content_baselines()
        for b in content_baselines:
            key = f"{b.platform}:{b.content_type}:{b.metric}"
            results["content"][key] = b.sample_count

        revenue_baselines = self.recalculate_revenue_baseline()
        for b in revenue_baselines:
            results["revenue"][b.metric] = b.sample_count

        delivery_baselines = self.recalculate_delivery_baseline()
        for b in delivery_baselines:
            results["delivery"][b.metric] = b.sample_count

        logger.info(
            "Recalculated baselines: %d content, %d revenue, %d delivery",
            len(content_baselines),
            len(revenue_baselines),
            len(delivery_baselines),
        )

        return results

    def recalculate_content_baselines(self) -> list[ContentBaseline]:
        """
        Recalculate content performance baselines.

        Reads all performance.jsonl files, filters to last 30 days,
        groups by platform/content_type/metric, and calculates baselines.
        """
        baselines: list[ContentBaseline] = []
        data_dir = self.fs.get_data_path("content-performance")

        if not data_dir.exists():
            logger.debug("No content performance data directory")
            return baselines

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.WINDOW_DAYS)
        records: dict[str, list[float]] = {}

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
                                    record_time = datetime.fromisoformat(received_at)
                                    if record_time < cutoff:
                                        continue
                                except ValueError:
                                    continue

                                content_type = record.get("content_type", "unknown")
                                engagement_data = record.get("engagement_data", {})

                                for metric_name, value in engagement_data.items():
                                    if not isinstance(value, (int, float)):
                                        continue
                                    key = f"{platform}:{content_type}:{metric_name}"
                                    if key not in records:
                                        records[key] = []
                                    records[key].append(float(value))

                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning("Failed to read %s: %s", perf_file, e)

        calculated_at = datetime.now(timezone.utc).isoformat()

        for key, values in records.items():
            if len(values) < self.MIN_SAMPLES:
                continue

            platform, content_type, metric = key.split(":")
            mean = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

            baseline = ContentBaseline(
                platform=platform,
                content_type=content_type,
                metric=metric,
                mean=mean,
                std_dev=std_dev,
                sample_count=len(values),
                window_days=self.WINDOW_DAYS,
                calculated_at=calculated_at,
                upper_anomaly_threshold=mean * 2.0,
                lower_anomaly_threshold=mean * 0.5,
            )
            baselines.append(baseline)

        if baselines:
            baseline_file = self.fs.get_baseline_path("content")
            baseline_file.parent.mkdir(parents=True, exist_ok=True)
            data = {f"{b.platform}:{b.content_type}:{b.metric}": b.to_dict() for b in baselines}
            baseline_file.write_text(json.dumps(data, indent=2) + "\n")
            logger.debug("Wrote %d content baselines to %s", len(baselines), baseline_file)

        return baselines

    def recalculate_revenue_baseline(self) -> list[RevenueBaseline]:
        """Recalculate revenue baselines from weekly revenue data."""
        baselines: list[RevenueBaseline] = []
        path = self.fs.get_data_path("revenue", "weekly-revenue.jsonl")

        if not path.exists():
            logger.debug("No revenue data file")
            return baselines

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.WINDOW_DAYS)
        metrics: dict[str, list[float]] = {
            "week_total": [],
            "invoices_paid": [],
            "invoices_pending": [],
        }

        try:
            with open(path) as f:
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

                        for metric in metrics:
                            value = record.get(metric)
                            if isinstance(value, (int, float)):
                                metrics[metric].append(float(value))

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("Failed to read revenue data: %s", e)
            return baselines

        calculated_at = datetime.now(timezone.utc).isoformat()

        for metric, values in metrics.items():
            if len(values) < self.MIN_SAMPLES:
                continue

            mean = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

            baseline = RevenueBaseline(
                metric=metric,
                mean=mean,
                std_dev=std_dev,
                sample_count=len(values),
                calculated_at=calculated_at,
                upper_anomaly_threshold=mean * 2.0,
                lower_anomaly_threshold=mean * 0.5,
            )
            baselines.append(baseline)

        if baselines:
            baseline_file = self.fs.get_baseline_path("revenue")
            baseline_file.parent.mkdir(parents=True, exist_ok=True)
            data = {b.metric: b.to_dict() for b in baselines}
            baseline_file.write_text(json.dumps(data, indent=2) + "\n")
            logger.debug("Wrote %d revenue baselines to %s", len(baselines), baseline_file)

        return baselines

    def recalculate_delivery_baseline(self) -> list[DeliveryBaseline]:
        """Recalculate delivery velocity baselines."""
        baselines: list[DeliveryBaseline] = []
        path = self.fs.get_data_path("delivery-velocity", "velocity.jsonl")

        if not path.exists():
            logger.debug("No delivery data file")
            return baselines

        cutoff = datetime.now(timezone.utc) - timedelta(days=self.WINDOW_DAYS)
        metrics: dict[str, list[float]] = {
            "prs_merged": [],
            "deploys": [],
            "avg_pr_cycle_hours": [],
        }

        try:
            with open(path) as f:
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

                        for metric in metrics:
                            value = record.get(metric)
                            if isinstance(value, (int, float)):
                                metrics[metric].append(float(value))

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("Failed to read delivery data: %s", e)
            return baselines

        calculated_at = datetime.now(timezone.utc).isoformat()

        for metric, values in metrics.items():
            if len(values) < self.MIN_SAMPLES:
                continue

            mean = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

            baseline = DeliveryBaseline(
                metric=metric,
                mean=mean,
                std_dev=std_dev,
                sample_count=len(values),
                calculated_at=calculated_at,
                upper_anomaly_threshold=mean * 2.0,
                lower_anomaly_threshold=mean * 0.5,
            )
            baselines.append(baseline)

        if baselines:
            baseline_file = self.fs.get_baseline_path("delivery")
            baseline_file.parent.mkdir(parents=True, exist_ok=True)
            data = {b.metric: b.to_dict() for b in baselines}
            baseline_file.write_text(json.dumps(data, indent=2) + "\n")
            logger.debug("Wrote %d delivery baselines to %s", len(baselines), baseline_file)

        return baselines

    def load_content_baselines(self) -> dict[str, ContentBaseline]:
        """Load content baselines from file."""
        baseline_file = self.fs.get_baseline_path("content")
        if not baseline_file.exists():
            return {}

        try:
            data = json.loads(baseline_file.read_text())
            return {k: ContentBaseline.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to load content baselines: %s", e)
            return {}

    def load_revenue_baseline(self) -> dict[str, RevenueBaseline]:
        """Load revenue baselines from file."""
        baseline_file = self.fs.get_baseline_path("revenue")
        if not baseline_file.exists():
            return {}

        try:
            data = json.loads(baseline_file.read_text())
            return {k: RevenueBaseline.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to load revenue baselines: %s", e)
            return {}

    def load_delivery_baseline(self) -> dict[str, DeliveryBaseline]:
        """Load delivery baselines from file."""
        baseline_file = self.fs.get_baseline_path("delivery")
        if not baseline_file.exists():
            return {}

        try:
            data = json.loads(baseline_file.read_text())
            return {k: DeliveryBaseline.from_dict(v) for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to load delivery baselines: %s", e)
            return {}

    def has_sufficient_data(self) -> tuple[bool, str]:
        """
        Check if there's enough data for meaningful baselines.

        Returns (True, "") if sufficient, (False, "reason") if not.
        """
        content_baselines = self.load_content_baselines()
        if not content_baselines:
            content_path = self.fs.get_data_path("content-performance")
            if not content_path.exists():
                return False, "No content performance data directory"

            sample_count = self._count_samples("content-performance")
            if sample_count < self.MIN_SAMPLES:
                return False, f"Only {sample_count} content samples, need {self.MIN_SAMPLES}"

        return True, ""

    def _count_samples(self, data_type: str) -> int:
        """Count total samples in a data directory."""
        count = 0
        data_dir = self.fs.get_data_path(data_type)

        if not data_dir.exists():
            return 0

        for jsonl_file in data_dir.rglob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        if line.strip():
                            count += 1
            except Exception:
                continue

        return count
