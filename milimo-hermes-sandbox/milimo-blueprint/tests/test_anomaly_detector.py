# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Anomaly Detector.
"""

import json
import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from orchestrator.analytics.anomaly_detector import (
    AnomalyDetector,
    DetectedAnomaly,
)
from orchestrator.analytics.baseline_manager import (
    ContentBaseline,
    RevenueBaseline,
    DeliveryBaseline,
)


@pytest.fixture
def temp_sandbox() -> Iterator[Path]:
    """Create a temporary sandbox directory for testing."""
    sandbox = Path(tempfile.mkdtemp(prefix="anomaly_test_"))
    yield sandbox
    shutil.rmtree(sandbox, ignore_errors=True)


@pytest.fixture
def fs(temp_sandbox: Path) -> AnalyticsFilesystemInit:
    """Create filesystem init with temp sandbox."""
    fs = AnalyticsFilesystemInit(temp_sandbox)
    fs.initialize()
    return fs


@pytest.fixture
def operational_log(fs: AnalyticsFilesystemInit) -> AnalyticsOperationalLog:
    """Create operational log."""
    return AnalyticsOperationalLog(fs.get_log_path("operational.log"))


@pytest.fixture
def dispatched_alerts() -> list[dict[str, Any]]:
    """Track dispatched alerts."""
    return []


@pytest.fixture
def anomaly_detector(
    fs: AnalyticsFilesystemInit,
    operational_log: AnalyticsOperationalLog,
    dispatched_alerts: list[dict[str, Any]],
) -> AnomalyDetector:
    """Create anomaly detector with mock dispatcher."""

    def mock_dispatcher(message_type: str, target_claw: str, payload: dict) -> None:
        dispatched_alerts.append(
            {
                "message_type": message_type,
                "target_claw": target_claw,
                "payload": payload,
            }
        )

    return AnomalyDetector(
        fs=fs,
        operational_log=operational_log,
        alert_dispatcher=mock_dispatcher,
    )


def create_content_baseline(
    mean: float = 0.08,
    std_dev: float = 0.02,
) -> ContentBaseline:
    """Create a test content baseline."""
    return ContentBaseline(
        platform="linkedin",
        content_type="article",
        metric="engagement_rate",
        mean=mean,
        std_dev=std_dev,
        sample_count=30,
        window_days=30,
        calculated_at=datetime.now(timezone.utc).isoformat(),
        upper_anomaly_threshold=mean * 2.0,
        lower_anomaly_threshold=mean * 0.5,
    )


class TestDetectedAnomaly:
    """Tests for DetectedAnomaly dataclass."""

    def test_to_dict_returns_all_fields(self):
        """Test that to_dict includes all fields."""
        anomaly = DetectedAnomaly(
            signal_id="signal-123",
            anomaly_id="anomaly-456",
            detected_at="2024-01-15T10:00:00Z",
            metric="content.linkedin.article.engagement_rate",
            current_value=0.20,
            baseline_mean=0.08,
            baseline_std_dev=0.02,
            ratio=2.5,
            direction="positive",
            severity="significant",
            requires_attention=False,
            target_claw="content",
        )

        data = anomaly.to_dict()

        assert data["signal_id"] == "signal-123"
        assert data["anomaly_id"] == "anomaly-456"
        assert data["ratio"] == 2.5
        assert data["severity"] == "significant"

    def test_details_field_optional(self):
        """Test that details field is optional."""
        anomaly = DetectedAnomaly(
            signal_id="signal-123",
            anomaly_id="anomaly-456",
            detected_at="2024-01-15T10:00:00Z",
            metric="test.metric",
            current_value=0.20,
            baseline_mean=0.08,
            baseline_std_dev=0.02,
            ratio=2.5,
            direction="positive",
            severity="significant",
            requires_attention=False,
            target_claw="content",
            details={"extra": "info"},
        )

        assert anomaly.details == {"extra": "info"}


class TestAnomalyDetector:
    """Tests for AnomalyDetector class."""

    def test_check_content_signal_returns_none_when_no_baseline(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test that no detection when no baseline exists."""
        signal = {
            "signal_id": "test-signal",
            "platform": "linkedin",
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.20},
        }

        result = anomaly_detector.check_content_signal(signal, {})

        assert result is None

    def test_check_content_signal_returns_none_when_within_normal_range(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test that no detection when value is within normal range."""
        baselines = {
            "linkedin:article:engagement_rate": create_content_baseline(mean=0.08),
        }

        signal = {
            "signal_id": "test-signal",
            "platform": "linkedin",
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.10},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is None

    def test_check_content_signal_detects_positive_anomaly_at_2x(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test that anomaly detected at exactly 2x baseline."""
        baselines = {
            "linkedin:article:engagement_rate": create_content_baseline(mean=0.08),
        }

        signal = {
            "signal_id": "test-signal",
            "platform": "linkedin",
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.16},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is not None
        assert result.direction == "positive"
        assert result.ratio >= 2.0

    def test_check_content_signal_detects_negative_anomaly_at_0_5x(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test that anomaly detected at exactly 0.5x baseline."""
        baselines = {
            "linkedin:article:engagement_rate": create_content_baseline(mean=0.08),
        }

        signal = {
            "signal_id": "test-signal",
            "platform": "linkedin",
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.04},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is not None
        assert result.direction == "negative"
        assert result.ratio <= 0.5

    def test_classify_severity_mild_positive(self, anomaly_detector: AnomalyDetector):
        """Test severity classification for mild positive anomalies."""
        severity = anomaly_detector._classify_severity(1.8, "positive")

        assert severity == "mild"

    def test_classify_severity_significant_positive(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test severity classification for significant positive anomalies."""
        severity = anomaly_detector._classify_severity(3.5, "positive")

        assert severity == "significant"

    def test_classify_severity_extreme_positive(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test severity classification for extreme positive anomalies."""
        severity = anomaly_detector._classify_severity(6.0, "positive")

        assert severity == "extreme"

    def test_classify_severity_mild_negative(self, anomaly_detector: AnomalyDetector):
        """Test severity classification for mild negative anomalies."""
        severity = anomaly_detector._classify_severity(0.4, "negative")

        assert severity == "mild"

    def test_classify_severity_significant_negative(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test severity classification for significant negative anomalies."""
        severity = anomaly_detector._classify_severity(0.25, "negative")

        assert severity == "significant"

    def test_classify_severity_extreme_negative(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test severity classification for extreme negative anomalies."""
        severity = anomaly_detector._classify_severity(0.15, "negative")

        assert severity == "extreme"

    def test_requires_attention_only_for_negative_extreme(
        self, anomaly_detector: AnomalyDetector, fs: AnalyticsFilesystemInit
    ):
        """Test that requires_attention is True only for negative extreme."""
        baselines = {
            "linkedin:article:engagement_rate": create_content_baseline(mean=0.08),
        }

        signal_extreme = {
            "signal_id": "test-signal-1",
            "platform": "linkedin",
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.01},
        }

        result_extreme = anomaly_detector.check_content_signal(
            signal_extreme, baselines
        )
        assert result_extreme is not None
        assert result_extreme.requires_attention is True

        signal_positive = {
            "signal_id": "test-signal-2",
            "platform": "linkedin",
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.50},
        }

        result_positive = anomaly_detector.check_content_signal(
            signal_positive, baselines
        )
        assert result_positive is not None
        assert result_positive.requires_attention is False

    def test_target_claw_routing_content(self, anomaly_detector: AnomalyDetector):
        """Test that content anomalies route to content claw."""
        target = anomaly_detector._determine_target_claw("content")

        assert target == "content"

    def test_target_claw_routing_revenue(self, anomaly_detector: AnomalyDetector):
        """Test that revenue anomalies route to finance claw."""
        target = anomaly_detector._determine_target_claw("revenue")

        assert target == "finance"

    def test_target_claw_routing_delivery(self, anomaly_detector: AnomalyDetector):
        """Test that delivery anomalies route to build claw."""
        target = anomaly_detector._determine_target_claw("delivery")

        assert target == "build"

    def test_target_claw_routing_client_health(self, anomaly_detector: AnomalyDetector):
        """Test that client health anomalies route to ops claw."""
        target = anomaly_detector._determine_target_claw("client_health")

        assert target == "ops"

    def test_save_anomaly_writes_to_file(
        self, anomaly_detector: AnomalyDetector, fs: AnalyticsFilesystemInit
    ):
        """Test that save_anomaly writes to correct path."""
        anomaly = DetectedAnomaly(
            signal_id="signal-123",
            anomaly_id="anomaly-456",
            detected_at=datetime.now(timezone.utc).isoformat(),
            metric="content.linkedin.article.engagement_rate",
            current_value=0.20,
            baseline_mean=0.08,
            baseline_std_dev=0.02,
            ratio=2.5,
            direction="positive",
            severity="significant",
            requires_attention=False,
            target_claw="content",
        )

        path = anomaly_detector.save_anomaly(anomaly)

        assert path.exists()
        assert path.name == "anomaly-456.json"

        content = json.loads(path.read_text())
        assert content["signal_id"] == "signal-123"

    def test_dispatch_alert_sends_to_correct_claw(
        self, anomaly_detector: AnomalyDetector, dispatched_alerts: list[dict[str, Any]]
    ):
        """Test that dispatch_alert sends to target claw."""
        anomaly = DetectedAnomaly(
            signal_id="signal-123",
            anomaly_id="anomaly-456",
            detected_at=datetime.now(timezone.utc).isoformat(),
            metric="revenue.week_total",
            current_value=5000,
            baseline_mean=2000,
            baseline_std_dev=500,
            ratio=2.5,
            direction="positive",
            severity="significant",
            requires_attention=False,
            target_claw="finance",
        )

        anomaly_detector.dispatch_alert(anomaly)

        assert len(dispatched_alerts) == 1
        assert dispatched_alerts[0]["target_claw"] == "finance"

    def test_check_revenue_signal_detects_anomaly(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test revenue signal anomaly detection."""
        baselines = {
            "week_total": RevenueBaseline(
                metric="week_total",
                mean=2000.0,
                std_dev=500.0,
                sample_count=30,
                calculated_at=datetime.now(timezone.utc).isoformat(),
                upper_anomaly_threshold=4000.0,
                lower_anomaly_threshold=1000.0,
            )
        }

        signal = {
            "signal_id": "revenue-signal",
            "week_total": 5000.0,
        }

        result = anomaly_detector.check_revenue_signal(signal, baselines)

        assert result is not None
        assert result.direction == "positive"

    def test_check_delivery_signal_detects_anomaly(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test delivery signal anomaly detection."""
        baselines = {
            "prs_merged": DeliveryBaseline(
                metric="prs_merged",
                mean=10.0,
                std_dev=3.0,
                sample_count=30,
                calculated_at=datetime.now(timezone.utc).isoformat(),
                upper_anomaly_threshold=20.0,
                lower_anomaly_threshold=5.0,
            )
        }

        signal = {
            "signal_id": "delivery-signal",
            "prs_merged": 25,
        }

        result = anomaly_detector.check_delivery_signal(signal, baselines)

        assert result is not None
        assert result.direction == "positive"

    def test_delivery_cycle_hours_inverted_logic(
        self, anomaly_detector: AnomalyDetector
    ):
        """Test that higher avg_pr_cycle_hours is negative anomaly."""
        baselines = {
            "avg_pr_cycle_hours": DeliveryBaseline(
                metric="avg_pr_cycle_hours",
                mean=4.0,
                std_dev=1.0,
                sample_count=30,
                calculated_at=datetime.now(timezone.utc).isoformat(),
                upper_anomaly_threshold=8.0,
                lower_anomaly_threshold=2.0,
            )
        }

        signal = {
            "signal_id": "delivery-signal",
            "avg_pr_cycle_hours": 12.0,
        }

        result = anomaly_detector.check_delivery_signal(signal, baselines)

        assert result is not None
        assert result.direction == "negative"


class TestAnomalyThresholds:
    """Tests for anomaly threshold boundaries."""

    def test_threshold_at_exactly_2x(self, anomaly_detector: AnomalyDetector):
        """Test anomaly detected at exactly 2.0x threshold."""
        baselines = {
            "test:test:metric": create_content_baseline(mean=1.0),
        }

        signal = {
            "signal_id": "test",
            "platform": "test",
            "content_type": "test",
            "engagement_data": {"metric": 2.0},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is not None

    def test_threshold_just_below_2x(self, anomaly_detector: AnomalyDetector):
        """Test no anomaly just below 2.0x threshold."""
        baselines = {
            "test:test:metric": create_content_baseline(mean=1.0),
        }

        signal = {
            "signal_id": "test",
            "platform": "test",
            "content_type": "test",
            "engagement_data": {"metric": 1.99},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is None

    def test_threshold_at_exactly_0_5x(self, anomaly_detector: AnomalyDetector):
        """Test anomaly detected at exactly 0.5x threshold."""
        baselines = {
            "test:test:metric": create_content_baseline(mean=1.0),
        }

        signal = {
            "signal_id": "test",
            "platform": "test",
            "content_type": "test",
            "engagement_data": {"metric": 0.5},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is not None

    def test_threshold_just_above_0_5x(self, anomaly_detector: AnomalyDetector):
        """Test no anomaly just above 0.5x threshold."""
        baselines = {
            "test:test:metric": create_content_baseline(mean=1.0),
        }

        signal = {
            "signal_id": "test",
            "platform": "test",
            "content_type": "test",
            "engagement_data": {"metric": 0.51},
        }

        result = anomaly_detector.check_content_signal(signal, baselines)

        assert result is None
