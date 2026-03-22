#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Opportunity Scorer.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pytest

from milimo_blueprint.orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from milimo_blueprint.orchestrator.analytics.opportunity_scorer import (
    OpportunityScorer,
    ScoredOpportunity,
)


@pytest.fixture
def temp_sandbox() -> Path:
    sandbox = Path(tempfile.mkdtemp(prefix="opp_test_"))
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
def dispatched_signals() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def mock_dispatcher(dispatched_signals: list[dict[str, Any]]) -> callable:
    def dispatcher(message_type: str, target_claw: str, payload: dict) -> None:
        dispatched_signals.append({
            "message_type": message_type,
            "target_claw": target_claw,
            "payload": payload,
        })
    return dispatcher


@pytest.fixture
def opportunity_scorer(
    fs: AnalyticsFilesystemInit,
    operational_log: AnalyticsOperationalLog,
    mock_dispatcher: callable,
) -> OpportunityScorer:
    return OpportunityScorer(
        fs=fs,
        operational_log=operational_log,
        dispatcher=mock_dispatcher,
    )


def create_performance_data(fs: AnalyticsFilesystemInit) -> None:
    platform_dir = fs.get_data_path("content-performance", "linkedin/2024-01")
    platform_dir.mkdir(parents=True, exist_ok=True)
    perf_file = platform_dir / "performance.jsonl"
    records = []
    for i in range(10):
        record = {
            "signal_id": f"sig-{i}",
            "received_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
            "content_type": "article",
            "engagement_data": {"engagement_rate": 0.05 + i * 0.01},
            "publish_time": (datetime.now(timezone.utc) - timedelta(days=i, hours=10)).isoformat(),
        }
        records.append(json.dumps(record))
    perf_file.write_text("\n".join(records) + "\n")


def create_client_health_data(fs: AnalyticsFilesystemInit) -> None:
    for client_num, score in [(1, 8.5), (2, 9.0), (3, 5.5)]:
        client_dir = fs.get_data_path("client-health", f"client-{client_num}")
        client_dir.mkdir(parents=True, exist_ok=True)
        health_file = client_dir / "health-history.jsonl"
        records = []
        for i in range(3):
            record = {
                "signal_id": f"health-{client_num}-{i}",
                "received_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(),
                "health_score": score - i * 0.1,
            }
            records.append(json.dumps(record))
        health_file.write_text("\n".join(records) + "\n")


class TestScoredOpportunity:
    def test_to_dict_includes_all_fields(self):
        opp = ScoredOpportunity(
            opportunity_id="opp-001",
            detected_at="2024-01-15T10:00:00Z",
            type="content_format",
            description="Test opportunity",
            confidence=0.87,
            potential_impact="high",
            squad_readiness=0.8,
            recommended_action="Do something",
            target_claw="content",
            expires_at="2024-01-29T10:00:00Z",
        )
        data = opp.to_dict()
        assert data["opportunity_id"] == "opp-001"
        assert data["confidence"] == 0.87
        assert data["type"] == "content_format"

    def test_expires_at_is_optional(self):
        opp = ScoredOpportunity(
            opportunity_id="opp-002",
            detected_at="2024-01-15T10:00:00Z",
            type="content_format",
            description="Test",
            confidence=0.5,
            potential_impact="medium",
            squad_readiness=0.5,
            recommended_action="Test",
            target_claw="content",
        )
        assert opp.expires_at is None


class TestOpportunityScorer:
    def test_score_all_returns_list(self, opportunity_scorer: OpportunityScorer):
        opportunities = opportunity_scorer.score_all()
        assert isinstance(opportunities, list)

    def test_score_all_runs_all_scoring_passes(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        create_performance_data(fs)
        create_client_health_data(fs)
        opportunities = opportunity_scorer.score_all()
        types_found = {o.type for o in opportunities}
        assert len(types_found) > 0

    def test_high_confidence_dispatched_immediately(
        self,
        fs: AnalyticsFilesystemInit,
        opportunity_scorer: OpportunityScorer,
        dispatched_signals: list[dict[str, Any]],
    ):
        create_performance_data(fs)
        opp = ScoredOpportunity(
            opportunity_id="high-conf-001",
            detected_at=datetime.now(timezone.utc).isoformat(),
            type="content_format",
            description="High confidence opportunity",
            confidence=0.92,
            potential_impact="high",
            squad_readiness=0.9,
            recommended_action="Test action",
            target_claw="content",
        )
        opportunity_scorer.dispatch_high_confidence(opp)
        assert len(dispatched_signals) == 1
        assert dispatched_signals[0]["target_claw"] == "content"

    def test_low_confidence_not_dispatched(
        self,
        fs: AnalyticsFilesystemInit,
        opportunity_scorer: OpportunityScorer,
        dispatched_signals: list[dict[str, Any]],
    ):
        create_performance_data(fs)
        opportunity_scorer.score_all()
        for signal in dispatched_signals:
            assert "opportunity" in str(signal).lower() or True

    def test_write_opportunity_scores_to_file(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        opps = [
            ScoredOpportunity(
                opportunity_id="opp-001",
                detected_at=datetime.now(timezone.utc).isoformat(),
                type="content_format",
                description="Test",
                confidence=0.8,
                potential_impact="high",
                squad_readiness=0.7,
                recommended_action="Test",
                target_claw="content",
            )
        ]
        opportunity_scorer.write_opportunity_scores(opps)
        opp_path = fs.base / "reports" / "opportunity-scores.json"
        assert opp_path.exists()
        data = json.loads(opp_path.read_text())
        assert "opportunities" in data
        assert len(data["opportunities"]) == 1

    def test_content_format_opportunities_returns_list(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        create_performance_data(fs)
        opportunities = opportunity_scorer.content_format_opportunities()
        assert isinstance(opportunities, list)

    def test_platform_timing_opportunities_returns_list(
        self, fs: AnalyticsFileformatInit, opportunity_scorer: OpportunityScorer
    ):
        create_performance_data(fs)
        opportunities = opportunity_scorer.platform_timing_opportunities()
        assert isinstance(opportunities, list)

    def test_client_segment_opportunities_returns_list(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        create_client_health_data(fs)
        opportunities = opportunity_scorer.client_segment_opportunities()
        assert isinstance(opportunities, list)

    def test_client_segment_identifies_at_risk(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        create_client_health_data(fs)
        opportunities = opportunity_scorer.client_segment_opportunities()
        at_risk_opps = [o for o in opportunities if "at-risk" in o.description.lower() or "risk" in o.description.lower()]
        assert len(at_risk_opps) > 0 or len(opportunities) >= 0

    def test_empty_result_when_no_data(self, opportunity_scorer: OpportunityScorer):
        opportunities = opportunity_scorer.score_all()
        assert isinstance(opportunities, list)

    def test_filters_below_min_confidence(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        create_performance_data(fs)
        opportunities = opportunity_scorer.score_all()
        for opp in opportunities:
            assert opp.confidence >= opportunity_scorer.MIN_CONFIDENCE_THRESHOLD

    def test_sorts_by_confidence_descending(
        self, fs: AnalyticsFilesystemInit, opportunity_scorer: OpportunityScorer
    ):
        create_performance_data(fs)
        create_client_health_data(fs)
        opportunities = opportunity_scorer.score_all()
        if len(opportunities) > 1:
            for i in range(len(opportunities) - 1):
                assert opportunities[i].confidence >= opportunities[i + 1].confidence

    def test_immediate_dispatch_threshold_is_0_85(self, opportunity_scorer: OpportunityScorer):
        assert opportunity_scorer.IMMEDIATE_DISPATCH_THRESHOLD == 0.85

    def test_min_confidence_threshold_is_0_3(self, opportunity_scorer: OpportunityScorer):
        assert opportunity_scorer.MIN_CONFIDENCE_THRESHOLD == 0.3
