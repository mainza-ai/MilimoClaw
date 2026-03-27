#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Integration Tests

11-step Minimum Viable First Run (MVR) sequence tests.
All tests must pass before the claw is considered minimally functional.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pytest

from orchestrator.analytics.analytics_claw import AnalyticsClaw
from orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from orchestrator.analytics.signal_processor import SignalProcessor
from orchestrator.analytics.query_handler import QueryHandler
from orchestrator.analytics.report_generator import ReportGenerator
from orchestrator.analytics.signal_dispatcher import SignalDispatcher


@pytest.fixture
def temp_sandbox() -> Path:
    """Create a temporary sandbox directory for testing."""
    sandbox = Path(tempfile.mkdtemp(prefix="analytics_test_"))
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


class TestMVRSequence:
    """Minimum Viable First Run test sequence."""

    def test_mvr_step_01_performance_signal_stored(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 01: Inject mock performance_signal — confirm stored in data/."""
        from orchestrator.analytics.signal_processor import InboundSignal

        dispatcher = SignalDispatcher(operational_log, fs)
        processor = SignalProcessor(fs, operational_log)

        signal = InboundSignal(
            signal_id="test-signal-001",
            message_type="performance_signal",
            source_claw="content",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "post_id": "post-001",
                "platform": "linkedin",
                "content_type": "carousel",
                "engagement_data": {
                    "engagement_rate": 0.085,
                    "impressions": 1200,
                    "clicks": 45,
                },
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        )

        processor.handle_performance_signal(signal)

        data_dir = fs.get_data_path("content-performance")
        assert data_dir.exists()

        found = False
        for platform_dir in data_dir.iterdir():
            if platform_dir.is_dir() and platform_dir.name == "linkedin":
                for month_dir in platform_dir.iterdir():
                    if month_dir.is_dir():
                        perf_file = month_dir / "performance.jsonl"
                        if perf_file.exists():
                            found = True
                            content = perf_file.read_text()
                            assert "test-signal-001" in content or "engagement_rate" in content

        assert found, "Performance signal not stored"

    def test_mvr_step_02_data_written_to_correct_path(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 02: Confirm JSONL written to data/content-performance/{platform}/."""
        from orchestrator.analytics.signal_processor import InboundSignal

        dispatcher = SignalDispatcher(operational_log, fs)
        processor = SignalProcessor(fs, operational_log, dispatcher)

        signal = InboundSignal(
            signal_id="test-signal-002",
            message_type="performance_signal",
            source_claw="content",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "post_id": "post-002",
                "platform": "twitter",
                "content_type": "thread",
                "engagement_data": {
                    "engagement_rate": 0.12,
                    "impressions": 5000,
                },
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        )

        processor.handle_performance_signal(signal)

        twitter_dir = fs.get_data_path("content-performance") / "twitter"
        assert twitter_dir.exists()

        jsonl_files = list(twitter_dir.rglob("*.jsonl"))
        assert len(jsonl_files) > 0

    def test_mvr_step_03_query_received(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 03: Inject mock content_performance_query — confirm received."""
        dispatcher = SignalDispatcher(operational_log, fs)
        handler = QueryHandler(fs, operational_log)

        query = {
            "message_id": "test-query-003",
            "message_type": "content_performance_query",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_role": "content",
            "payload": {
                "query": "top_formats",
                "lookback_days": 7,
            },
        }

        response = handler.handle(query)

        assert response is not None
        assert response.query_type == "content_performance_query"

    def test_mvr_step_04_query_response_within_sla(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 04: Confirm response dispatched within 2 minutes (120 seconds)."""
        from orchestrator.analytics.signal_processor import InboundSignal

        dispatcher = SignalDispatcher(operational_log, fs)
        processor = SignalProcessor(fs, operational_log, dispatcher)
        handler = QueryHandler(fs, operational_log)

        for i in range(3):
            signal = InboundSignal(
                signal_id=f"perf-{i}",
                message_type="performance_signal",
                source_claw="content",
                received_at=datetime.now(timezone.utc).isoformat(),
                payload={
                    "post_id": f"post-{i}",
                    "platform": "linkedin",
                    "content_type": "article",
                    "engagement_data": {"engagement_rate": 0.05 + i * 0.01},
                    "publish_time": datetime.now(timezone.utc).isoformat(),
                },
            )
            processor.handle_performance_signal(signal)

        query = {
            "message_id": "test-query-004",
            "message_type": "content_performance_query",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_role": "content",
            "payload": {
                "query": "top_formats",
                "lookback_days": 7,
            },
        }

        start_time = time.time()
        response = handler.handle(query)
        elapsed = time.time() - start_time

        assert response is not None
        assert elapsed < 120, f"Query took {elapsed}s, exceeds 2-minute SLA"

    def test_mvr_step_05_seven_days_of_signals(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 05: Inject 7 days of mock signals — all stored correctly."""
        from orchestrator.analytics.signal_processor import InboundSignal

        dispatcher = SignalDispatcher(operational_log, fs)
        processor = SignalProcessor(fs, operational_log, dispatcher)

        base_date = datetime.now(timezone.utc) - timedelta(days=7)

        for day in range(7):
            signal_date = base_date + timedelta(days=day)
            signal = InboundSignal(
                signal_id=f"signal-day-{day}",
                message_type="performance_signal",
                source_claw="content",
                received_at=signal_date.isoformat(),
                payload={
                    "post_id": f"post-{day}",
                    "platform": "linkedin",
                    "content_type": "carousel",
                    "engagement_data": {
                        "engagement_rate": 0.05 + day * 0.01,
                        "impressions": 1000 + day * 100,
                    },
                    "publish_time": signal_date.isoformat(),
                },
            )
            processor.handle_performance_signal(signal)

        data_dir = fs.get_data_path("content-performance")
        signal_count = 0

        for jsonl_file in data_dir.rglob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    if line.strip():
                        signal_count += 1

        assert signal_count >= 7, f"Expected at least 7 signals, found {signal_count}"

    def test_mvr_step_06_manual_report_generation(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 06: Trigger report generation manually — confirm no exceptions."""
        report_gen = ReportGenerator(fs, operational_log, squad_id="test-squad")

        try:
            report = report_gen.generate()
            assert report is not None
        except Exception as e:
            pytest.fail(f"Report generation raised exception: {e}")

    def test_mvr_step_07_report_file_written(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 07: Confirm weekly-intelligence.json exists and is valid JSON."""
        report_gen = ReportGenerator(fs, operational_log, squad_id="test-squad")
        report_gen.generate()

        report_path = fs.get_report_path()
        assert report_path.exists(), "weekly-intelligence.json not written"

        content = report_path.read_text()
        try:
            data = json.loads(content)
            assert "generated_at" in data
            assert "week_of" in data
            assert "squad_id" in data
        except json.JSONDecodeError as e:
            pytest.fail(f"Report is not valid JSON: {e}")

    def test_mvr_step_08_content_claw_can_read_report(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 08: Simulate Content Claw file read — confirm access."""
        report_gen = ReportGenerator(fs, operational_log, squad_id="test-squad")
        report_gen.generate()

        report_path = fs.get_report_path()

        assert report_path.exists()
        content = report_path.read_text()
        data = json.loads(content)

        assert "content_performance" in data

    def test_mvr_step_09_ops_claw_can_read_report(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 09: Simulate Ops Claw file read — confirm access."""
        report_gen = ReportGenerator(fs, operational_log, squad_id="test-squad")
        report_gen.generate()

        report_path = fs.get_report_path()

        assert report_path.exists()
        content = report_path.read_text()
        data = json.loads(content)

        assert "client_health" in data

    def test_mvr_step_10_health_signal_below_threshold(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 10: Inject client_health_signal with score 5.0."""
        from orchestrator.analytics.signal_processor import InboundSignal

        dispatched_alerts: list[dict] = []

        def mock_sender(message: dict) -> None:
            dispatched_alerts.append(message)

        dispatcher = SignalDispatcher(operational_log, fs, mesh_sender=mock_sender)
        
        def alert_callback(message_type: str, target_claw: str, payload: dict) -> None:
            dispatcher.send_client_health_alert(
                client_id=payload.get("client_id", ""),
                health_score=payload.get("health_score", 0),
                risk_factors=payload.get("risk_factors", []),
                recommended_action=payload.get("recommended_action", ""),
            )
        
        processor = SignalProcessor(fs, operational_log, alert_dispatcher=alert_callback)

        signal = InboundSignal(
            signal_id="health-signal-010",
            message_type="client_health_signal",
            source_claw="ops",
            received_at=datetime.now(timezone.utc).isoformat(),
            payload={
                "client_id": "client-test-001",
                "health_score": 5.0,
                "health_factors": ["Low engagement", "Payment delays"],
            },
        )

        processor.handle_client_health_signal(signal)

        assert len(dispatched_alerts) == 1
        assert dispatched_alerts[0]["message_type"] == "client_health_alert"
        assert dispatched_alerts[0]["recipient_role"] == "ops"

    def test_mvr_step_11_health_alert_dispatched_immediately(self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog):
        """Step 11: Confirm client_health_alert sent to Ops Claw immediately."""
        dispatched_alerts: list[dict] = []

        def mock_sender(message: dict) -> None:
            dispatched_alerts.append(message)

        dispatcher = SignalDispatcher(operational_log, fs, mesh_sender=mock_sender)

        low_health_signal = {
            "message_id": "health-signal-011",
            "message_type": "client_health_signal",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_role": "ops",
            "client_id": "client-test-002",
            "health_score": 4.5,
            "risk_factors": ["Churn risk"],
        }

        dispatcher.send_client_health_alert(
            client_id=low_health_signal["client_id"],
            health_score=low_health_signal["health_score"],
            risk_factors=low_health_signal["risk_factors"],
            recommended_action="Immediate outreach required",
        )

        assert len(dispatched_alerts) == 1
        alert = dispatched_alerts[0]
        assert alert["message_type"] == "client_health_alert"
        assert alert["payload"]["client_id"] == "client-test-002"
        assert alert["payload"]["health_score"] == 4.5
        assert alert["payload"]["urgency"] == "high"


class TestAnalyticsClawIntegration:
    """Full integration tests for AnalyticsClaw."""

    def test_claw_startup_and_shutdown(self, temp_sandbox: Path):
        """Test that AnalyticsClaw starts and stops cleanly."""
        claw = AnalyticsClaw(
            squad_id="test-squad",
            base_path=temp_sandbox,
        )

        claw.startup()
        assert claw._started

        claw.shutdown()
        assert not claw._started

    def test_claw_handles_unknown_message_type(self, temp_sandbox: Path):
        """Test that unknown message types don't crash the claw."""
        claw = AnalyticsClaw(
            squad_id="test-squad",
            base_path=temp_sandbox,
        )
        claw.startup()

        unknown_message = {
            "message_id": "unknown-001",
            "message_type": "unknown_type",
            "sender_role": "test",
        }

        claw.handle_inbound(unknown_message)

        claw.shutdown()

    def test_claw_handles_performance_signal(self, temp_sandbox: Path):
        """Test that performance signals are handled correctly."""
        claw = AnalyticsClaw(
            squad_id="test-squad",
            base_path=temp_sandbox,
        )
        claw.startup()

        signal = {
            "message_id": "perf-test-001",
            "message_type": "performance_signal",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_role": "content",
            "payload": {
                "post_id": "post-001",
                "platform": "linkedin",
                "content_type": "article",
                "engagement_data": {"engagement_rate": 0.08},
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        }

        claw.handle_inbound(signal)

        data_dir = temp_sandbox / "data" / "content-performance"
        assert data_dir.exists()

        claw.shutdown()
