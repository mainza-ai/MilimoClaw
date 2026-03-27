#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Baseline Manager.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from orchestrator.analytics.baseline_manager import (
    BaselineManager,
    ContentBaseline,
    RevenueBaseline,
    DeliveryBaseline,
)


@pytest.fixture
def temp_sandbox() -> Path:
    """Create a temporary sandbox directory for testing."""
    sandbox = Path(tempfile.mkdtemp(prefix="baseline_test_"))
    yield sandbox
    shutil.rmtree(sandbox, ignore_errors=True)


@pytest.fixture
def fs(temp_sandbox: Path) -> AnalyticsFilesystemInit:
    """Create filesystem init with temp sandbox."""
    fs = AnalyticsFilesystemInit(temp_sandbox)
    fs.initialize()
    return fs


@pytest.fixture
def baseline_manager(fs: AnalyticsFilesystemInit) -> BaselineManager:
    """Create baseline manager with filesystem."""
    return BaselineManager(fs)


def create_mock_performance_data(fs: AnalyticsFilesystemInit, num_records: int = 10) -> None:
    """Create mock performance data for testing."""
    platform_dir = fs.get_data_path("content-performance", "linkedin/2024-01")
    platform_dir.mkdir(parents=True, exist_ok=True)

    perf_file = platform_dir / "performance.jsonl"

    records = []
    for i in range(num_records):
        record = {
            "signal_id": f"signal-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            "post_id": f"post-{i}",
            "platform": "linkedin",
            "content_type": "article" if i % 2 == 0 else "carousel",
            "engagement_data": {
                "engagement_rate": 0.05 + (i * 0.01),
                "impressions": 1000 + (i * 100),
            },
            "publish_time": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
        }
        records.append(json.dumps(record))

    perf_file.write_text("\n".join(records) + "\n")


def create_mock_revenue_data(fs: AnalyticsFilesystemInit, num_records: int = 10) -> None:
    """Create mock revenue data for testing."""
    revenue_path = fs.get_data_path("revenue", "weekly-revenue.jsonl")
    revenue_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for i in range(num_records):
        record = {
            "signal_id": f"revenue-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(days=i * 7)).isoformat(),
            "week_total": 1000 + (i * 100),
            "invoices_paid": i,
            "invoices_pending": max(0, 3 - i),
        }
        records.append(json.dumps(record))

    revenue_path.write_text("\n".join(records) + "\n")


def create_mock_delivery_data(fs: AnalyticsFilesystemInit, num_records: int = 10) -> None:
    """Create mock delivery data for testing."""
    delivery_path = fs.get_data_path("delivery-velocity", "velocity.jsonl")
    delivery_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for i in range(num_records):
        record = {
            "signal_id": f"delivery-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            "prs_merged": 5 + i,
            "deploys": 1 + (i // 2),
            "avg_pr_cycle_hours": 4.0 + (i * 0.5),
        }
        records.append(json.dumps(record))

    delivery_path.write_text("\n".join(records) + "\n")


class TestContentBaseline:
    """Tests for ContentBaseline dataclass."""

    def test_to_dict_returns_all_fields(self):
        """Test that to_dict includes all fields."""
        baseline = ContentBaseline(
            platform="linkedin",
            content_type="article",
            metric="engagement_rate",
            mean=0.08,
            std_dev=0.02,
            sample_count=30,
            window_days=30,
            calculated_at="2024-01-15T10:00:00Z",
            upper_anomaly_threshold=0.16,
            lower_anomaly_threshold=0.04,
        )

        data = baseline.to_dict()

        assert data["platform"] == "linkedin"
        assert data["content_type"] == "article"
        assert data["metric"] == "engagement_rate"
        assert data["mean"] == 0.08
        assert data["sample_count"] == 30

    def test_from_dict_recreates_baseline(self):
        """Test that from_dict recreates baseline correctly."""
        data = {
            "platform": "twitter",
            "content_type": "thread",
            "metric": "engagement_rate",
            "mean": 0.12,
            "std_dev": 0.03,
            "sample_count": 25,
            "window_days": 30,
            "calculated_at": "2024-01-15T10:00:00Z",
            "upper_anomaly_threshold": 0.24,
            "lower_anomaly_threshold": 0.06,
        }

        baseline = ContentBaseline.from_dict(data)

        assert baseline.platform == "twitter"
        assert baseline.content_type == "thread"
        assert baseline.mean == 0.12


class TestBaselineManager:
    """Tests for BaselineManager class."""

    def test_recalculate_content_baselines_returns_empty_when_no_data(
        self, baseline_manager: BaselineManager
    ):
        """Test that recalculate returns empty list when no data."""
        baselines = baseline_manager.recalculate_content_baselines()

        assert baselines == []

    def test_recalculate_content_baselines_calculates_from_data(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that recalculate calculates baselines from data."""
        create_mock_performance_data(fs, num_records=10)

        baselines = baseline_manager.recalculate_content_baselines()

        assert len(baselines) > 0

        for b in baselines:
            assert b.platform == "linkedin"
            assert b.content_type in ["article", "carousel"]
            assert b.sample_count >= 5

    def test_recalculate_content_baselines_filters_30_days(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that recalculate only uses last 30 days."""
        platform_dir = fs.get_data_path("content-performance", "linkedin/2024-01")
        platform_dir.mkdir(parents=True, exist_ok=True)

        perf_file = platform_dir / "performance.jsonl"

        records = []
        for i in range(50):
            days_ago = i
            record = {
                "signal_id": f"signal-{i}",
                "received_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
                "post_id": f"post-{i}",
                "platform": "linkedin",
                "content_type": "article",
                "engagement_data": {"engagement_rate": 0.05 + (i * 0.001)},
                "publish_time": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
            }
            records.append(json.dumps(record))

        perf_file.write_text("\n".join(records) + "\n")

        baselines = baseline_manager.recalculate_content_baselines()

        assert len(baselines) > 0

        for b in baselines:
            assert b.window_days == 30
            assert b.sample_count <= 30

    def test_recalculate_returns_none_for_insufficient_samples(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that baseline is not created for < MIN_SAMPLES."""
        create_mock_performance_data(fs, num_records=3)

        baselines = baseline_manager.recalculate_content_baselines()

        assert len(baselines) == 0

    def test_recalculate_calculates_thresholds_correctly(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that thresholds are calculated as 2x and 0.5x mean."""
        create_mock_performance_data(fs, num_records=10)

        baselines = baseline_manager.recalculate_content_baselines()

        assert len(baselines) > 0

        for b in baselines:
            assert b.upper_anomaly_threshold == pytest.approx(b.mean * 2.0, rel=0.01)
            assert b.lower_anomaly_threshold == pytest.approx(b.mean * 0.5, rel=0.01)

    def test_recalculate_writes_to_file(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that baselines are written to file."""
        create_mock_performance_data(fs, num_records=10)

        baseline_manager.recalculate_content_baselines()

        baseline_file = fs.get_baseline_path("content")
        assert baseline_file.exists()

        data = json.loads(baseline_file.read_text())
        assert len(data) > 0

    def test_load_content_baselines_returns_empty_when_no_file(
        self, baseline_manager: BaselineManager
    ):
        """Test that load returns empty dict when file doesn't exist."""
        baselines = baseline_manager.load_content_baselines()

        assert baselines == {}

    def test_load_content_baselines_returns_baselines(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that load returns baselines from file."""
        create_mock_performance_data(fs, num_records=10)
        baseline_manager.recalculate_content_baselines()

        baselines = baseline_manager.load_content_baselines()

        assert len(baselines) > 0

        for key, b in baselines.items():
            assert ":" in key
            assert isinstance(b, ContentBaseline)

    def test_recalculate_revenue_baseline(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test revenue baseline calculation."""
        create_mock_revenue_data(fs, num_records=10)

        baselines = baseline_manager.recalculate_revenue_baseline()

        assert len(baselines) > 0

        for b in baselines:
            assert b.metric in ["week_total", "invoices_paid", "invoices_pending"]
            assert b.upper_anomaly_threshold == pytest.approx(b.mean * 2.0, rel=0.01)

    def test_recalculate_delivery_baseline(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test delivery baseline calculation."""
        create_mock_delivery_data(fs, num_records=10)

        baselines = baseline_manager.recalculate_delivery_baseline()

        assert len(baselines) > 0

        for b in baselines:
            assert b.metric in ["prs_merged", "deploys", "avg_pr_cycle_hours"]

    def test_recalculate_all_returns_summary(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that recalculate_all returns summary."""
        create_mock_performance_data(fs, num_records=10)
        create_mock_revenue_data(fs, num_records=10)
        create_mock_delivery_data(fs, num_records=10)

        summary = baseline_manager.recalculate_all()

        assert "content" in summary
        assert "revenue" in summary
        assert "delivery" in summary
        assert "calculated_at" in summary

    def test_has_sufficient_data_returns_true_when_enough(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that has_sufficient_data returns True when enough data."""
        create_mock_performance_data(fs, num_records=10)

        sufficient, reason = baseline_manager.has_sufficient_data()

        assert sufficient is True
        assert reason == ""

    def test_has_sufficient_data_returns_false_when_insufficient(
        self, baseline_manager: BaselineManager
    ):
        """Test that has_sufficient_data returns False when no data."""
        sufficient, reason = baseline_manager.has_sufficient_data()

        assert sufficient is False
        assert len(reason) > 0


class TestBaselineThresholds:
    """Tests for baseline threshold calculations."""

    def test_threshold_at_exactly_2x_triggers_positive(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that 2x threshold is correctly set."""
        create_mock_performance_data(fs, num_records=10)

        baselines = baseline_manager.recalculate_content_baselines()

        for b in baselines:
            test_value = b.mean * 2.0
            assert test_value >= b.upper_anomaly_threshold * 0.99

    def test_threshold_at_exactly_0_5x_triggers_negative(
        self, fs: AnalyticsFilesystemInit, baseline_manager: BaselineManager
    ):
        """Test that 0.5x threshold is correctly set."""
        create_mock_performance_data(fs, num_records=10)

        baselines = baseline_manager.recalculate_content_baselines()

        for b in baselines:
            test_value = b.mean * 0.5
            assert test_value <= b.lower_anomaly_threshold * 1.01
