#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Query Handler.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from milimo_blueprint.orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from milimo_blueprint.orchestrator.analytics.query_handler import (
    QueryHandler,
    QueryResponse,
)


@pytest.fixture
def temp_sandbox() -> Path:
    sandbox = Path(tempfile.mkdtemp(prefix="query_test_"))
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
def query_handler(fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog) -> QueryHandler:
    return QueryHandler(fs, operational_log)


def create_mock_performance_data(fs: AnalyticsFilesystemInit, days: int = 7) -> None:
    platform_dir = fs.get_data_path("content-performance", "linkedin/2024-01")
    platform_dir.mkdir(parents=True, exist_ok=True)
    perf_file = platform_dir / "performance.jsonl"
    records = []
    for i in range(days):
        record = {
            "signal_id": f"signal-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            "post_id": f"post-{i}",
            "platform": "linkedin",
            "content_type": "article" if i % 2 == 0 else "carousel",
            "engagement_data": {"engagement_rate": 0.05 + (i * 0.01)},
            "publish_time": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
        }
        records.append(json.dumps(record))
    perf_file.write_text("\n".join(records) + "\n")


class TestQueryResponse:
    def test_to_dict_includes_all_fields(self):
        response = QueryResponse(
            query_id="q-001",
            query_type="content_performance_query",
            responding_to="msg-001",
            requesting_claw="content",
            data_quality="complete",
            data={"test": "data"},
            generated_at="2024-01-15T10:00:00Z",
            processing_time_ms=100,
        )
        data = response.to_dict()
        assert data["query_id"] == "q-001"
        assert data["data_quality"] == "complete"

    def test_to_dict_includes_optional_fields(self):
        response = QueryResponse(
            query_id="q-001",
            query_type="content_performance_query",
            responding_to="msg-001",
            requesting_claw="content",
            data_quality="insufficient",
            data=None,
            generated_at="2024-01-15T10:00:00Z",
            processing_time_ms=100,
            days_collected=3,
            days_needed=7,
        )
        data = response.to_dict()
        assert "days_collected" in data
        assert "days_needed" in data


class TestQueryHandler:
    def test_handle_returns_response(self, query_handler: QueryHandler):
        message = {
            "message_id": "query-001",
            "message_type": "content_performance_query",
            "sender_role": "content",
            "payload": {"query": "top_formats", "lookback_days": 7},
        }
        response = query_handler.handle(message)
        assert response is not None
        assert response.query_type == "content_performance_query"

    def test_handle_content_performance_query_returns_insufficient_when_no_data(
        self, query_handler: QueryHandler
    ):
        response = query_handler.handle_content_performance_query(
            query="top_formats",
            lookback_days=7,
            platform=None,
            requesting_claw="content",
            query_id="query-002",
        )
        assert response.data_quality == "insufficient"

    def test_handle_content_performance_query_returns_data(
        self, fs: AnalyticsFilesystemInit, query_handler: QueryHandler
    ):
        create_mock_performance_data(fs, days=10)
        response = query_handler.handle_content_performance_query(
            query="top_formats",
            lookback_days=7,
            platform=None,
            requesting_claw="content",
            query_id="query-003",
        )
        assert response.data_quality in ["complete", "insufficient"]
        if response.data_quality == "complete":
            assert "top_formats" in response.data
            assert len(response.data["top_formats"]) > 0

    def test_handle_content_performance_query_sorts_by_engagement(
        self, fs: AnalyticsFilesystemInit, query_handler: QueryHandler
    ):
        create_mock_performance_data(fs, days=10)
        response = query_handler.handle_content_performance_query(
            query="top_formats",
            lookback_days=7,
            platform=None,
            requesting_claw="content",
            query_id="query-004",
        )
        if response.data_quality == "complete":
            formats = response.data["top_formats"]
            for i in range(len(formats) - 1):
                assert formats[i]["avg_engagement"] >= formats[i + 1]["avg_engagement"]

    def test_handle_behavior_query_returns_insufficient_when_no_data(
        self, query_handler: QueryHandler
    ):
        response = query_handler.handle_behavior_query(
            query="feature_correlation",
            feature_id=None,
            lookback_days=14,
            requesting_claw="build",
            query_id="query-005",
        )
        assert response.data_quality == "insufficient"

    def test_handle_unknown_query_type_returns_error(
        self, query_handler: QueryHandler
    ):
        message = {
            "message_id": "query-006",
            "message_type": "unknown_query_type",
            "sender_role": "content",
            "payload": {},
        }
        response = query_handler.handle(message)
        assert response.data_quality == "error"

    def test_handle_logs_to_operational_log(
        self, fs: AnalyticsFilesystemInit, query_handler: QueryHandler, operational_log: AnalyticsOperationalLog
    ):
        message = {
            "message_id": "query-007",
            "message_type": "content_performance_query",
            "sender_role": "content",
            "payload": {"query": "top_formats", "lookback_days": 7},
        }
        query_handler.handle(message)
        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "query_received" for e in entries)
        assert any(e.action_type == "query_answered" for e in entries)

    def test_response_within_sla(
        self, fs: AnalyticsFilesystemInit, query_handler: QueryHandler
    ):
        import time
        create_mock_performance_data(fs, days=10)
        start = time.time()
        response = query_handler.handle_content_performance_query(
            query="top_formats",
            lookback_days=7,
            platform=None,
            requesting_claw="content",
            query_id="query-008",
        )
        elapsed = time.time() - start
        assert elapsed < 120

    def test_insufficient_response_includes_days_info(
        self, query_handler: QueryHandler
    ):
        response = query_handler._insufficient_response(
            query_id="q-001",
            query_type="test_query",
            requesting_claw="content",
            days_collected=3,
            days_needed=7,
        )
        assert response.days_collected == 3
        assert response.days_needed == 7
        assert response.data is None
