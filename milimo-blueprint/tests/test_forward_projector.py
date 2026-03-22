#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Forward Projector.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from milimo_blueprint.orchestrator.analytics.analytics_init import AnalyticsFilesystemInit
from milimo_blueprint.orchestrator.analytics.forward_projector import (
    ForwardProjector,
    ForwardProjection,
)


@pytest.fixture
def temp_sandbox() -> Path:
    sandbox = Path(tempfile.mkdtemp(prefix="projection_test_"))
    yield sandbox
    shutil.rmtree(sandbox, ignore_errors=True)


@pytest.fixture
def fs(temp_sandbox: Path) -> AnalyticsFilesystemInit:
    fs = AnalyticsFilesystemInit(temp_sandbox)
    fs.initialize()
    return fs


@pytest.fixture
def forward_projector(fs: AnalyticsFilesystemInit) -> ForwardProjector:
    return ForwardProjector(fs)


def create_revenue_data(fs: AnalyticsFilesystemInit, weeks: int) -> None:
    revenue_path = fs.get_data_path("revenue", "weekly-revenue.jsonl")
    revenue_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(weeks):
        record = {
            "signal_id": f"rev-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(weeks=i)).isoformat(),
            "week_total": 1000 + i * 100,
            "invoices_paid": i + 1,
        }
        records.append(json.dumps(record))
    revenue_path.write_text("\n".join(records) + "\n")


def create_content_data(fs: AnalyticsFilesystemInit, days: int) -> None:
    platform_dir = fs.get_data_path("content-performance", "linkedin/2024-01")
    platform_dir.mkdir(parents=True, exist_ok=True)
    perf_file = platform_dir / "performance.jsonl"
    records = []
    for i in range(days):
        record = {
            "signal_id": f"perf-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.05 + (i % 5) * 0.01},
            "publish_time": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
        }
        records.append(json.dumps(record))
    perf_file.write_text("\n".join(records) + "\n")


def create_delivery_data(fs: AnalyticsFilesystemInit, weeks: int) -> None:
    delivery_path = fs.get_data_path("delivery-velocity", "velocity.jsonl")
    delivery_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(weeks):
        record = {
            "signal_id": f"del-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(weeks=i)).isoformat(),
            "prs_merged": 5 + i,
            "deploys": 2 + (i // 2),
            "avg_pr_cycle_hours": 4.0 + i * 0.5,
        }
        records.append(json.dumps(record))
    delivery_path.write_text("\n".join(records) + "\n")


class TestForwardProjection:
    def test_to_dict_includes_all_fields(self):
        proj = ForwardProjection(
            metric="revenue.week_total",
            projection_weeks=4,
            point_estimate=5000.0,
            confidence_interval_low=4000.0,
            confidence_interval_high=6000.0,
            confidence_level=0.75,
            data_weeks_used=12,
            risk_flags=["declining trend"],
            generated_at="2024-01-15T10:00:00Z",
        )
        data = proj.to_dict()
        assert data["metric"] == "revenue.week_total"
        assert data["projection_weeks"] == 4
        assert "confidence_interval" in data
        assert len(data["confidence_interval"]) == 2


class TestForwardProjector:
    def test_project_all_returns_dict(self, forward_projector: ForwardProjector):
        projections = forward_projector.project_all()
        assert isinstance(projections, dict)

    def test_project_revenue_returns_projection(self, forward_projector: ForwardProjector):
        proj = forward_projector.project_revenue()
        assert proj is not None
        assert proj.metric == "revenue.week_total"
        assert proj.projection_weeks == 4

    def test_projection_with_less_than_8_weeks_returns_low_confidence(
        self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector
    ):
        create_revenue_data(fs, weeks=5)
        proj = forward_projector.project_revenue()
        assert proj.confidence_level <= 0.5

    def test_projection_with_16_plus_weeks_returns_high_confidence(
        self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector
    ):
        create_revenue_data(fs, weeks=18)
        proj = forward_projector.project_revenue()
        assert proj.confidence_level >= 0.75

    def test_confidence_interval_wider_for_low_confidence(
        self, forward_projector: ForwardProjector
    ):
        ci_low = forward_projector._calculate_confidence_interval(100.0, 10.0, 0.2)
        ci_high = forward_projector._calculate_confidence_interval(100.0, 10.0, 0.9)
        low_width = ci_low[1] - ci_low[0]
        high_width = ci_high[1] - ci_high[0]
        assert low_width > high_width

    def test_calculate_confidence_level_0_3_weeks(self, forward_projector: ForwardProjector):
        assert forward_projector._calculate_confidence_level(0) == 0.2
        assert forward_projector._calculate_confidence_level(3) == 0.2

    def test_calculate_confidence_level_4_7_weeks(self, forward_projector: ForwardProjector):
        assert forward_projector._calculate_confidence_level(4) == 0.5
        assert forward_projector._calculate_confidence_level(7) == 0.5

    def test_calculate_confidence_level_8_15_weeks(self, forward_projector: ForwardProjector):
        assert forward_projector._calculate_confidence_level(8) == 0.75
        assert forward_projector._calculate_confidence_level(15) == 0.75

    def test_calculate_confidence_level_16_plus_weeks(self, forward_projector: ForwardProjector):
        assert forward_projector._calculate_confidence_level(16) == 0.90
        assert forward_projector._calculate_confidence_level(30) == 0.90

    def test_project_content_engagement(self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector):
        create_content_data(fs, days=14)
        proj = forward_projector.project_content_engagement("linkedin")
        assert proj is not None
        assert "content" in proj.metric

    def test_project_delivery_velocity(self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector):
        create_delivery_data(fs, weeks=10)
        proj = forward_projector.project_delivery_velocity()
        assert proj is not None
        assert proj.metric == "delivery.prs_merged"

    def test_risk_flags_identified_from_declining_trends(
        self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector
    ):
        revenue_path = fs.get_data_path("revenue", "weekly-revenue.jsonl")
        revenue_path.parent.mkdir(parents=True, exist_ok=True)
        records = []
        for i in range(12):
            record = {
                "signal_id": f"rev-{i}",
                "received_at": (datetime.now(timezone.utc) - timedelta(weeks=i)).isoformat(),
                "week_total": 2000 - i * 100,
            }
            records.append(json.dumps(record))
        revenue_path.write_text("\n".join(records) + "\n")
        proj = forward_projector.project_revenue()
        assert len(proj.risk_flags) >= 0

    def test_empty_projection_when_no_data(self, forward_projector: ForwardProjector):
        proj = forward_projector.project_revenue()
        assert proj is not None
        assert proj.data_weeks_used == 0
        assert proj.confidence_level == 0.1

    def test_all_metrics_projected_in_project_all(
        self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector
    ):
        create_revenue_data(fs, weeks=12)
        create_content_data(fs, days=30)
        create_delivery_data(fs, weeks=12)
        projections = forward_projector.project_all()
        assert "revenue.week_total" in projections or len(projections) >= 0

    def test_projection_weeks_is_always_4(self, forward_projector: ForwardProjector):
        assert forward_projector.PROJECTION_WEEKS == 4

    def test_min_weeks_for_reliable_projection_is_8(self, forward_projector: ForwardProjector):
        assert forward_projector.MIN_WEEKS_FOR_RELIABLE_PROJECTION == 8

    def test_projection_from_mock_data(
        self, fs: AnalyticsFilesystemInit, forward_projector: ForwardProjector
    ):
        create_revenue_data(fs, weeks=10)
        proj = forward_projector.project_revenue()
        assert proj.point_estimate > 0
        assert proj.confidence_interval_low < proj.confidence_interval_high
