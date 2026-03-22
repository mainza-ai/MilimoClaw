#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Signal Dispatcher.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from milimo_blueprint.orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from milimo_blueprint.orchestrator.analytics.signal_dispatcher import SignalDispatcher


@pytest.fixture
def temp_sandbox() -> Path:
    sandbox = Path(tempfile.mkdtemp(prefix="dispatcher_test_"))
    yield sandbox
    shutil.rmtree(sandbox, ignore_errors=True)


@pytest.fixture
def fs(temp_sandbox: Path) -> AnalyticsFilesystemInit:
    fs = AnalyticsFilesystemInit(temp_sandbox)
    fs.initialize()
    return fs


@pytest.fixture
def operational_log(fs: AnalyticsFilesystemInit) -> AnalyticsOperationalLog:
    return AnalyticsOperationalLog(fs.get_log_path("operational.log"))


@pytest.fixture
def dispatched_messages() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def mock_mesh_sender(dispatched_messages: list[dict[str, Any]]) -> callable:
    def sender(message: dict) -> None:
        dispatched_messages.append(message)
    return sender


@pytest.fixture
def dispatcher(
    fs: AnalyticsFilesystemInit,
    operational_log: AnalyticsOperationalLog,
    mock_mesh_sender: callable,
) -> SignalDispatcher:
    return SignalDispatcher(operational_log, fs, mesh_sender=mock_mesh_sender)


class TestSignalDispatcher:
    def test_send_performance_intel_calls_send(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_performance_intel(
            top_formats=[{"format": "article", "avg_engagement": 0.08}],
            top_times=[{"hour": 10, "avg_engagement": 0.09}],
            engagement_trends=[],
            audience_signals=[],
        )
        assert len(dispatched_messages) == 1
        assert dispatched_messages[0]["message_type"] == "performance_intel"
        assert dispatched_messages[0]["recipient_role"] == "content"

    def test_send_retention_signals_calls_send(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_retention_signals(
            feature_adoption_rates={"feature_a": 10},
            churn_correlation=[{"client_id": "c1", "delta": -0.5}],
            recommended_features=[],
        )
        assert len(dispatched_messages) == 1
        assert dispatched_messages[0]["message_type"] == "retention_signals"
        assert dispatched_messages[0]["recipient_role"] == "build"

    def test_send_client_health_alert_calls_send(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_client_health_alert(
            client_id="client-001",
            health_score=5.0,
            risk_factors=["low engagement"],
            recommended_action="Schedule check-in",
        )
        assert len(dispatched_messages) == 1
        assert dispatched_messages[0]["message_type"] == "client_health_alert"
        assert dispatched_messages[0]["recipient_role"] == "ops"
        assert dispatched_messages[0]["payload"]["urgency"] == "high"

    def test_send_revenue_anomaly_calls_send(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_revenue_anomaly(
            anomaly_type="week_total_spike",
            current_value=5000,
            baseline_value=2000,
            severity="significant",
        )
        assert len(dispatched_messages) == 1
        assert dispatched_messages[0]["message_type"] == "revenue_anomaly"
        assert dispatched_messages[0]["recipient_role"] == "finance"

    def test_send_content_performance_response(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_content_performance_response(
            query_id="query-001",
            requesting_claw="content",
            response_data={"top_formats": []},
        )
        assert len(dispatched_messages) == 1
        assert dispatched_messages[0]["message_type"] == "content_performance_response"

    def test_send_behavior_query_response(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_behavior_query_response(
            query_id="query-002",
            requesting_claw="build",
            response_data={"feature_adoption": {}},
        )
        assert len(dispatched_messages) == 1
        assert dispatched_messages[0]["message_type"] == "behavior_query_response"

    def test_send_includes_message_id(self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]):
        dispatcher.send_performance_intel([], [], [], [])
        assert "message_id" in dispatched_messages[0]
        assert len(dispatched_messages[0]["message_id"]) > 0

    def test_send_includes_timestamp(self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]):
        dispatcher.send_performance_intel([], [], [], [])
        assert "timestamp" in dispatched_messages[0]

    def test_send_includes_sender_role(self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]):
        dispatcher.send_performance_intel([], [], [], [])
        assert dispatched_messages[0]["sender_role"] == "analytics"

    def test_dispatch_failure_logged_not_raised(
        self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog, dispatched_messages: list[dict[str, Any]]
    ):
        def failing_sender(message: dict) -> None:
            raise RuntimeError("Network error")

        failing_dispatcher = SignalDispatcher(operational_log, fs, mesh_sender=failing_sender)

        failing_dispatcher.send_performance_intel([], [], [], [])

        entries = operational_log.read_recent(days=1)
        failed_entries = [e for e in entries if e.action_type == "signal_dispatch_failed"]
        assert len(failed_entries) == 1

    def test_payload_structure_matches_expected(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_client_health_alert(
            client_id="client-test",
            health_score=5.5,
            risk_factors=["risk1", "risk2"],
            recommended_action="action",
        )
        payload = dispatched_messages[0]["payload"]
        assert payload["client_id"] == "client-test"
        assert payload["health_score"] == 5.5
        assert payload["risk_factors"] == ["risk1", "risk2"]
        assert payload["recommended_action"] == "action"

    def test_operational_log_entry_created(
        self, dispatcher: SignalDispatcher, operational_log: AnalyticsOperationalLog
    ):
        dispatcher.send_performance_intel([], [], [], [])
        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "signal_dispatched" for e in entries)

    def test_no_mesh_sender_does_not_raise(
        self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog
    ):
        no_sender_dispatcher = SignalDispatcher(operational_log, fs, mesh_sender=None)
        no_sender_dispatcher.send_performance_intel([], [], [], [])

    def test_revenue_anomaly_includes_ratio(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_revenue_anomaly(
            anomaly_type="spike",
            current_value=3000,
            baseline_value=1000,
            severity="extreme",
        )
        payload = dispatched_messages[0]["payload"]
        assert payload["ratio"] == 3.0

    def test_client_health_urgency_based_on_score(
        self, dispatcher: SignalDispatcher, dispatched_messages: list[dict[str, Any]]
    ):
        dispatcher.send_client_health_alert(
            client_id="c1",
            health_score=7.0,
            risk_factors=[],
            recommended_action="",
        )
        assert dispatched_messages[0]["payload"]["urgency"] == "normal"

        dispatched_messages.clear()

        dispatcher.send_client_health_alert(
            client_id="c2",
            health_score=4.0,
            risk_factors=[],
            recommended_action="",
        )
        assert dispatched_messages[0]["payload"]["urgency"] == "high"
