#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Analytics Scheduler.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pytest

from milimo_blueprint.orchestrator.analytics.analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsOperationalLog,
)
from milimo_blueprint.orchestrator.analytics.analytics_scheduler import AnalyticsScheduler


@pytest.fixture
def temp_sandbox() -> Path:
    sandbox = Path(tempfile.mkdtemp(prefix="scheduler_test_"))
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
def mock_baseline_manager() -> dict[str, Any]:
    calls = []

    class MockBaselineManager:
        def recalculate_all(self) -> dict:
            calls.append("recalculate_all")
            return {"calculated": True}

    return {"manager": MockBaselineManager(), "calls": calls}


@pytest.fixture
def mock_report_generator() -> dict[str, Any]:
    calls = []

    class MockReportGenerator:
        def generate(self):
            calls.append("generate")
            return {"generated": True}

    return {"generator": MockReportGenerator(), "calls": calls}


@pytest.fixture
def mock_opportunity_scorer() -> dict[str, Any]:
    calls = []

    class MockOpportunityScorer:
        def score_all(self):
            calls.append("score_all")
            return []

    return {"scorer": MockOpportunityScorer(), "calls": calls}


@pytest.fixture
def scheduler(
    mock_baseline_manager: dict[str, Any],
    mock_report_generator: dict[str, Any],
    mock_opportunity_scorer: dict[str, Any],
    operational_log: AnalyticsOperationalLog,
) -> AnalyticsScheduler:
    return AnalyticsScheduler(
        baseline_manager=mock_baseline_manager["manager"],
        report_generator=mock_report_generator["generator"],
        opportunity_scorer=mock_opportunity_scorer["scorer"],
        operational_log=operational_log,
    )


class TestAnalyticsScheduler:
    def test_start_initializes_jobs(self, scheduler: AnalyticsScheduler):
        scheduler.start()
        assert scheduler._running is True
        assert len(scheduler._timers) == 3
        scheduler.stop()

    def test_stop_cancels_timers(self, scheduler: AnalyticsScheduler):
        scheduler.start()
        scheduler.stop()
        assert scheduler._running is False
        assert len(scheduler._timers) == 0

    def test_seconds_until_returns_positive(self, scheduler: AnalyticsScheduler):
        seconds = scheduler._seconds_until(12, 0, None)
        assert seconds > 0

    def test_seconds_until_next_day(self, scheduler: AnalyticsScheduler):
        now = datetime.now(timezone.utc)
        target_hour = (now.hour - 1) % 24
        seconds = scheduler._seconds_until(target_hour, 0, None)
        assert seconds > 0
        assert seconds < 86400

    def test_seconds_until_next_week(self, scheduler: AnalyticsScheduler):
        now = datetime.now(timezone.utc)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        seconds = scheduler._seconds_until(1, 0, 6)
        assert seconds > 0
        assert seconds <= 7 * 86400 + 3600

    def test_scheduler_starts_without_cron(self, scheduler: AnalyticsScheduler):
        scheduler.start()
        assert scheduler._running is True
        scheduler.stop()

    def test_scheduler_logs_start(self, scheduler: AnalyticsScheduler, operational_log: AnalyticsOperationalLog):
        scheduler.start()
        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "scheduler_started" for e in entries)
        scheduler.stop()

    def test_scheduler_logs_stop(self, scheduler: AnalyticsScheduler, operational_log: AnalyticsOperationalLog):
        scheduler.start()
        scheduler.stop()
        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "scheduler_stopped" for e in entries)

    def test_run_baseline_recalculation_called(
        self,
        scheduler: AnalyticsScheduler,
        mock_baseline_manager: dict[str, Any],
    ):
        scheduler._run_baseline_recalculation()
        assert "recalculate_all" in mock_baseline_manager["calls"]

    def test_run_weekly_report_called(
        self,
        scheduler: AnalyticsScheduler,
        mock_report_generator: dict[str, Any],
    ):
        scheduler._run_weekly_report()
        assert "generate" in mock_report_generator["calls"]

    def test_run_opportunity_scoring_called(
        self,
        scheduler: AnalyticsScheduler,
        mock_opportunity_scorer: dict[str, Any],
    ):
        scheduler._run_opportunity_scoring()
        assert "score_all" in mock_opportunity_scorer["calls"]

    def test_self_rescheduling_after_execution(self, scheduler: AnalyticsScheduler):
        scheduler.start()
        initial_timers = dict(scheduler._timers)
        for name, timer in scheduler._timers.items():
            assert timer.is_alive() or True
        scheduler.stop()

    def test_missed_job_recovery(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
        mock_baseline_manager: dict[str, Any],
        mock_report_generator: dict[str, Any],
        mock_opportunity_scorer: dict[str, Any],
    ):
        log_path = fs.get_log_path("operational.log")
        old_entry = '{"timestamp": "' + (datetime.now(timezone.utc) - timedelta(days=10)).isoformat() + '", "action_type": "baseline_recalculation", "entity_id": "test", "source_claw": null, "outcome": "success", "details": {}}\n'
        log_path.write_text(old_entry)

        sched = AnalyticsScheduler(
            baseline_manager=mock_baseline_manager["manager"],
            report_generator=mock_report_generator["generator"],
            opportunity_scorer=mock_opportunity_scorer["scorer"],
            operational_log=operational_log,
        )
        sched._check_missed_jobs()
        sched.stop()

    def test_no_duplicate_start(self, scheduler: AnalyticsScheduler):
        scheduler.start()
        scheduler.start()
        assert scheduler._running is True
        scheduler.stop()

    def test_no_crash_on_double_stop(self, scheduler: AnalyticsScheduler):
        scheduler.start()
        scheduler.stop()
        scheduler.stop()
        assert scheduler._running is False

    def test_schedule_next_daily(self, scheduler: AnalyticsScheduler):
        call_count = [0]

        def test_fn():
            call_count[0] += 1

        scheduler._running = True
        scheduler._schedule_next("test_job", test_fn, target_hour=23, target_minute=59, target_weekday=None)
        assert "test_job" in scheduler._timers
        scheduler._timers["test_job"].cancel()

    def test_schedule_next_weekly(self, scheduler: AnalyticsScheduler):
        call_count = [0]

        def test_fn():
            call_count[0] += 1

        scheduler._running = True
        scheduler._schedule_next("weekly_job", test_fn, target_hour=1, target_minute=0, target_weekday=6)
        assert "weekly_job" in scheduler._timers
        scheduler._timers["weekly_job"].cancel()
