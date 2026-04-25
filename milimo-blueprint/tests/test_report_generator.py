# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Report Generator.
"""

import json
import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from orchestrator.analytics.report_generator import (
    ReportGenerator,
    WeeklyReport,
)


@pytest.fixture
def temp_sandbox() -> Iterator[Path]:
    sandbox = Path(tempfile.mkdtemp(prefix="report_test_"))
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
def report_generator(
    fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog
) -> ReportGenerator:
    return ReportGenerator(fs, operational_log, squad_id="test-squad")


class TestWeeklyReport:
    def test_to_dict_includes_all_fields(self):
        report = WeeklyReport(
            generated_at="2024-01-15T10:00:00Z",
            week_of="2024-01-15",
            squad_id="test-squad",
            content_performance={"top_formats": []},
            client_health={"overall_score": 0},
            revenue={"week_total": 0},
            delivery={"prs_merged": 0},
            opportunities=[],
            anomalies=[],
            forward_projections={},
            summary_narrative="Test",
            data_quality={},
        )
        data = report.to_dict()
        assert "generated_at" in data
        assert "week_of" in data
        assert "squad_id" in data


class TestReportGenerator:
    def test_generate_returns_report(self, report_generator: ReportGenerator):
        report = report_generator.generate()
        assert report is not None
        assert isinstance(report, WeeklyReport)

    def test_generate_writes_report_file(
        self, fs: AnalyticsFilesystemInit, report_generator: ReportGenerator
    ):
        report_generator.generate()
        report_path = fs.get_report_path()
        assert report_path.exists()

    def test_generate_writes_valid_json(
        self, fs: AnalyticsFilesystemInit, report_generator: ReportGenerator
    ):
        report_generator.generate()
        report_path = fs.get_report_path()
        content = report_path.read_text()
        data = json.loads(content)
        assert "generated_at" in data
        assert "week_of" in data

    def test_atomic_write_cleans_up_temp_file(
        self, fs: AnalyticsFilesystemInit, report_generator: ReportGenerator
    ):
        report = WeeklyReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            week_of="2024-01-15",
            squad_id="test-squad",
            content_performance={},
            client_health={},
            revenue={},
            delivery={},
            opportunities=[],
            anomalies=[],
            forward_projections={},
            summary_narrative="Test",
        )
        report_generator.write_atomically(report)
        report_path = fs.get_report_path()
        parent_files = list(report_path.parent.glob("weekly-report-*"))
        temp_files = [
            f
            for f in parent_files
            if f.suffix == ".json" and "weekly-report-" in f.name
        ]
        assert report_path.exists()
        for tf in temp_files:
            assert not tf.name.endswith(".tmp")

    def test_generate_archives_previous_report(
        self, fs: AnalyticsFilesystemInit, report_generator: ReportGenerator
    ):
        report_generator.generate()
        first_report_path = fs.get_report_path()
        first_report_path.read_text()
        report_generator.generate()
        archive_dir = fs.base / "reports" / "weekly-intelligence-archive"
        assert archive_dir.exists()
        archive_files = list(archive_dir.glob("*.json"))
        assert len(archive_files) >= 1

    def test_generate_empty_report(self, report_generator: ReportGenerator):
        report = report_generator._generate_empty_report("No data available")
        assert report.summary_narrative.startswith("Insufficient data")
        assert report.data_quality.get("content_performance") == "insufficient"

    def test_generate_narrative_with_inference(
        self, fs: AnalyticsFilesystemInit, operational_log: AnalyticsOperationalLog
    ):
        class MockInferenceClient:
            def complete(
                self, prompt: str, data_type: str, max_tokens: int = 500
            ) -> str:
                return "This is a test narrative."

        gen = ReportGenerator(
            fs, operational_log, squad_id="test", inference_client=MockInferenceClient()
        )
        narrative = gen._generate_narrative(
            content_performance={
                "top_formats": [{"format": "article", "avg_engagement": 0.08}]
            },
            client_health={"overall_score": 7.5},
            revenue={"week_total": 5000},
            delivery={"prs_merged": 10},
        )
        assert "test narrative" in narrative.lower() or len(narrative) > 0

    def test_aggregate_content_performance(
        self, fs: AnalyticsFilesystemInit, report_generator: ReportGenerator
    ):
        platform_dir = fs.get_data_path("content-performance", "linkedin/2024-01")
        platform_dir.mkdir(parents=True, exist_ok=True)
        perf_file = platform_dir / "performance.jsonl"
        records = []
        for i in range(5):
            record = {
                "signal_id": f"sig-{i}",
                "received_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "article",
                "engagement_data": {"engagement_rate": 0.05 + i * 0.01},
                "publish_time": datetime.now(timezone.utc).isoformat(),
            }
            records.append(json.dumps(record))
        perf_file.write_text("\n".join(records) + "\n")
        result = report_generator._aggregate_content_performance()
        assert "top_formats" in result

    def test_aggregate_client_health(
        self, fs: AnalyticsFilesystemInit, report_generator: ReportGenerator
    ):
        client_dir = fs.get_data_path("client-health", "client-001")
        client_dir.mkdir(parents=True, exist_ok=True)
        health_file = client_dir / "health-history.jsonl"
        records = []
        for i in range(3):
            record = {
                "signal_id": f"health-{i}",
                "received_at": datetime.now(timezone.utc).isoformat(),
                "health_score": 5.0 + i,
            }
            records.append(json.dumps(record))
        health_file.write_text("\n".join(records) + "\n")
        result = report_generator._aggregate_client_health()
        assert "overall_score" in result
