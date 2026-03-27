#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Signal Processor.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from orchestrator.analytics.signal_processor import (
    SignalProcessor,
    SignalValidationError,
    InboundSignal,
    SIGNAL_SCHEMAS,
)
from orchestrator.analytics.signal_dispatcher import SignalDispatcher


@pytest.fixture
def temp_sandbox() -> Path:
    """Create a temporary sandbox directory for testing."""
    sandbox = Path(tempfile.mkdtemp(prefix="signal_test_"))
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
def dispatcher(
    fs: AnalyticsFilesystemInit,
    operational_log: AnalyticsOperationalLog,
    dispatched_alerts: list[dict[str, Any]],
) -> SignalDispatcher:
    """Create signal dispatcher with mock sender."""

    def mock_sender(message: dict) -> None:
        dispatched_alerts.append(message)

    return SignalDispatcher(operational_log, fs, mesh_sender=mock_sender)


@pytest.fixture
def signal_processor(
    fs: AnalyticsFilesystemInit,
    operational_log: AnalyticsOperationalLog,
    dispatcher: SignalDispatcher,
    dispatched_alerts: list[dict[str, Any]],
) -> SignalProcessor:
    """Create signal processor."""
    def alert_callback(message_type: str, target_claw: str, payload: dict) -> None:
        dispatched_alerts.append({
            "message_type": message_type,
            "target_claw": target_claw,
            "payload": payload,
        })
    
    return SignalProcessor(fs, operational_log, alert_dispatcher=alert_callback)


class TestInboundSignal:
    """Tests for InboundSignal dataclass."""

    def test_to_dict_returns_all_fields(self):
        """Test that to_dict includes all fields."""
        signal = InboundSignal(
            signal_id="signal-123",
            message_type="performance_signal",
            source_claw="content",
            received_at="2024-01-15T10:00:00Z",
            payload={"test": "data"},
        )

        data = signal.to_dict()

        assert data["signal_id"] == "signal-123"
        assert data["message_type"] == "performance_signal"
        assert data["source_claw"] == "content"

    def test_stored_path_optional(self):
        """Test that stored_path is optional."""
        signal = InboundSignal(
            signal_id="signal-123",
            message_type="performance_signal",
            source_claw="content",
            received_at="2024-01-15T10:00:00Z",
            payload={},
        )

        assert signal.stored_path is None


class TestSignalSchemas:
    """Tests for signal schema validation."""

    def test_performance_signal_schema_exists(self):
        """Test that performance_signal schema is defined."""
        assert "performance_signal" in SIGNAL_SCHEMAS
        schema = SIGNAL_SCHEMAS["performance_signal"]
        assert "content" in schema.allowed_senders
        assert "post_id" in schema.required_payload_fields

    def test_client_health_signal_schema_exists(self):
        """Test that client_health_signal schema is defined."""
        assert "client_health_signal" in SIGNAL_SCHEMAS
        schema = SIGNAL_SCHEMAS["client_health_signal"]
        assert "ops" in schema.allowed_senders
        assert "client_id" in schema.required_payload_fields
        assert "health_score" in schema.required_payload_fields

    def test_revenue_summary_schema_exists(self):
        """Test that revenue_summary schema is defined."""
        assert "revenue_summary" in SIGNAL_SCHEMAS
        schema = SIGNAL_SCHEMAS["revenue_summary"]
        assert "finance" in schema.allowed_senders

    def test_shipping_summary_schema_exists(self):
        """Test that shipping_summary schema is defined."""
        assert "shipping_summary" in SIGNAL_SCHEMAS
        schema = SIGNAL_SCHEMAS["shipping_summary"]
        assert "build" in schema.allowed_senders


class TestSignalProcessor:
    """Tests for SignalProcessor class."""

    def test_handle_performance_signal_stores_data(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that performance signal is stored correctly."""
        signal = InboundSignal(
            signal_id="test-signal-001",
            message_type="performance_signal",
            source_claw="content",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "post_id": "post-001",
                "platform": "linkedin",
                "content_type": "article",
                "engagement_data": {"engagement_rate": 0.08},
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        )

        signal_processor.handle_performance_signal(signal)

        data_dir = fs.get_data_path("content-performance")
        assert data_dir.exists()

        found = False
        for platform_dir in data_dir.iterdir():
            if platform_dir.is_dir() and platform_dir.name == "linkedin":
                found = True

        assert found

    def test_handle_performance_signal_stores_to_correct_path(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that signal is stored to platform/month path."""
        signal = InboundSignal(
            signal_id="test-signal-002",
            message_type="performance_signal",
            source_claw="content",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "post_id": "post-002",
                "platform": "twitter",
                "content_type": "thread",
                "engagement_data": {"engagement_rate": 0.12},
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        )

        signal_processor.handle_performance_signal(signal)

        twitter_dir = fs.get_data_path("content-performance") / "twitter"
        assert twitter_dir.exists()

    def test_handle_client_health_signal_stores_data(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that client health signal is stored correctly."""
        signal = InboundSignal(
            signal_id="health-signal-001",
            message_type="client_health_signal",
            source_claw="ops",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "client_id": "client-001",
                "health_score": 7.5,
                "health_factors": ["good communication"],
            },
        )

        signal_processor.handle_client_health_signal(signal)

        health_path = fs.get_data_path("client-health") / "client-001" / "health-history.jsonl"
        assert health_path.exists()

    def test_handle_client_health_signal_below_6_triggers_alert(
        self,
        signal_processor: SignalProcessor,
        fs: AnalyticsFilesystemInit,
        dispatched_alerts: list[dict[str, Any]],
    ):
        """Test that health score < 6.0 triggers immediate alert."""
        signal = InboundSignal(
            signal_id="health-signal-002",
            message_type="client_health_signal",
            source_claw="ops",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "client_id": "client-002",
                "health_score": 5.0,
                "health_factors": ["low engagement"],
            },
        )

        signal_processor.handle_client_health_signal(signal)

        assert len(dispatched_alerts) == 1
        assert dispatched_alerts[0]["message_type"] == "client_health_alert"

    def test_handle_client_health_signal_above_6_no_alert(
        self,
        signal_processor: SignalProcessor,
        dispatched_alerts: list[dict[str, Any]],
    ):
        """Test that health score >= 6.0 does not trigger alert."""
        signal = InboundSignal(
            signal_id="health-signal-003",
            message_type="client_health_signal",
            source_claw="ops",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "client_id": "client-003",
                "health_score": 7.5,
                "health_factors": [],
            },
        )

        signal_processor.handle_client_health_signal(signal)

        assert len(dispatched_alerts) == 0

    def test_handle_client_onboarded_creates_entry(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that client_onboarded creates health history entry."""
        signal = InboundSignal(
            signal_id="onboard-001",
            message_type="client_onboarded",
            source_claw="ops",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "client_id": "new-client-001",
                "niche": "saas",
                "project_type": "marketing",
                "estimated_value": 5000,
            },
        )

        signal_processor.handle_client_onboarded(signal)

        health_path = fs.get_data_path("client-health") / "new-client-001" / "health-history.jsonl"
        assert health_path.exists()

        content = health_path.read_text()
        data = json.loads(content.strip())
        assert data.get("event_type") == "onboarded"

    def test_handle_revenue_summary_stores_data(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that revenue summary is stored correctly."""
        signal = InboundSignal(
            signal_id="revenue-001",
            message_type="revenue_summary",
            source_claw="finance",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "week_total": 5000,
                "week_over_week_pct": 10.5,
                "invoices_paid": 3,
                "invoices_pending": 1,
            },
        )

        signal_processor.handle_revenue_summary(signal)

        revenue_path = fs.get_data_path("revenue", "weekly-revenue.jsonl")
        assert revenue_path.exists()

    def test_handle_shipping_summary_stores_data(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that shipping summary is stored correctly."""
        signal = InboundSignal(
            signal_id="shipping-001",
            message_type="shipping_summary",
            source_claw="build",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "prs_merged": 5,
                "deploys": 2,
                "issues_closed": 3,
            },
        )

        signal_processor.handle_shipping_summary(signal)

        delivery_path = fs.get_data_path("delivery-velocity", "velocity.jsonl")
        assert delivery_path.exists()

    def test_jsonl_append_is_thread_safe(
        self, signal_processor: SignalProcessor, fs: AnalyticsFilesystemInit
    ):
        """Test that concurrent signal handling is safe."""
        import threading

        num_threads = 5
        signals_per_thread = 10

        def write_signals(thread_id: int) -> None:
            for i in range(signals_per_thread):
                signal = InboundSignal(
                    signal_id=f"thread-{thread_id}-signal-{i}",
                    message_type="performance_signal",
                    source_claw="content",
                    received_at=datetime.now(timezone.utc).isoformat(),
                    payload={
                        "post_id": f"post-{thread_id}-{i}",
                        "platform": "linkedin",
                        "content_type": "article",
                        "engagement_data": {"engagement_rate": 0.05},
                        "publish_time": datetime.now(timezone.utc).isoformat(),
                    },
                )
                signal_processor.handle_performance_signal(signal)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=write_signals, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        count = 0
        for jsonl_file in fs.get_data_path("content-performance").rglob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    if line.strip():
                        count += 1

        assert count == num_threads * signals_per_thread


class TestSignalValidation:
    """Tests for signal validation."""

    def test_process_validates_message_type(
        self, signal_processor: SignalProcessor
    ):
        """Test that process validates message_type."""
        message = {
            "message_id": "test-001",
            "sender_role": "content",
            "payload": {"test": "data"},
        }

        with pytest.raises(SignalValidationError) as exc_info:
            signal_processor.process(message)

        assert "message_type" in str(exc_info.value).lower()

    def test_process_validates_sender(
        self, signal_processor: SignalProcessor
    ):
        """Test that process validates sender against schema."""
        message = {
            "message_id": "test-002",
            "message_type": "performance_signal",
            "sender_role": "finance",
            "payload": {
                "post_id": "post-1",
                "platform": "linkedin",
                "engagement_data": {},
                "publish_time": datetime.now(timezone.utc).isoformat(),
                "content_type": "article",
            },
        }

        with pytest.raises(SignalValidationError) as exc_info:
            signal_processor.process(message)

        assert "sender" in str(exc_info.value).lower() or "allowed" in str(exc_info.value).lower()

    def test_process_validates_required_fields(
        self, signal_processor: SignalProcessor
    ):
        """Test that process validates required payload fields."""
        message = {
            "message_id": "test-003",
            "message_type": "performance_signal",
            "sender_role": "content",
            "payload": {
                "platform": "linkedin",
            },
        }

        with pytest.raises(SignalValidationError) as exc_info:
            signal_processor.process(message)

        assert "post_id" in str(exc_info.value) or "required" in str(exc_info.value).lower()
