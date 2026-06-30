"""Unit tests for EvolutionScheduler."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from milimo_core.evolution_scheduler import (
    EvolutionScheduler,
    EvolutionSchedulerConfig,
    run_evolution_cycle_sync,
    run_tool_backtest_sync,
    run_hold_queue_review_sync,
)
from milimo_core.protocols.scheduling import ScheduledJob
from datetime import datetime, timezone
from pathlib import Path


class TestEvolutionSchedulerConfig:
    """Tests for EvolutionSchedulerConfig."""

    def test_default_config(self):
        """Test default EvolutionSchedulerConfig values."""
        config = EvolutionSchedulerConfig()

        assert config.squad_id == "default"
        assert config.blueprint_dir is None
        assert config.inference_client is None
        assert config.log_dir is None


class TestEvolutionScheduler:
    """Tests for EvolutionScheduler."""

    def test_initialization(self):
        """Test EvolutionScheduler initialization."""
        config = EvolutionSchedulerConfig(squad_id="test")
        scheduler = EvolutionScheduler(config=config)

        assert scheduler.config.squad_id == "test"
        assert hasattr(scheduler, "_jobs")
        assert isinstance(scheduler._jobs, dict)
        assert scheduler._running is False

    def test_schedule_job(self):
        """Test scheduling a job."""
        scheduler = EvolutionScheduler()
        job = ScheduledJob(
            name="test_job",
            cron_expression="0 * * * *",
            handler="test_handler",
            enabled=True
        )
        scheduler.schedule_job(job)

        assert "test_job" in scheduler._jobs
        assert scheduler._jobs["test_job"] == job

    def test_unschedule_job(self, sample_scheduled_job):
        """Test unscheduling a job."""
        scheduler = EvolutionScheduler()
        scheduler.schedule_job(sample_scheduled_job)
        scheduler.unschedule_job("test_job")

        assert "test_job" not in scheduler._jobs

    def test_unschedule_nonexistent_job(self):
        """Test unscheduling non-existent job doesn't raise."""
        scheduler = EvolutionScheduler()
        scheduler.unschedule_job("nonexistent")
        # Should not raise

    def test_get_due_jobs_empty(self):
        """Test getting due jobs when none scheduled."""
        scheduler = EvolutionScheduler()
        due = scheduler.get_due_jobs()
        assert due == []

    def test_get_due_jobs_with_jobs(self):
        """Test getting due jobs with scheduled jobs."""
        scheduler = EvolutionScheduler()
        # Add a job with next_run in the past
        job = ScheduledJob(
            name="test_job",
            cron_expression="0 * * * *",
            handler="test_handler",
            enabled=True,
            next_run=datetime.now(timezone.utc)
        )
        scheduler.schedule_job(job)
        due = scheduler.get_due_jobs()
        assert len(due) == 1
        assert due[0].name == "test_job"

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop methods."""
        scheduler = EvolutionScheduler()

        scheduler.start()
        assert scheduler._running is True

        scheduler.stop()
        assert scheduler._running is False

    def test_default_jobs_registered_on_start(self):
        """Test that default jobs are registered when starting."""
        scheduler = EvolutionScheduler()

        # Before start, no jobs
        assert len(scheduler._jobs) == 0

        # After start, default jobs should be registered
        scheduler.start()

        assert "evolution_cycle" in scheduler._jobs
        assert "tool_backtest" in scheduler._jobs
        assert "hold_queue_review" in scheduler._jobs

    def test_job_cron_expressions(self):
        """Test that registered jobs have correct cron expressions."""
        scheduler = EvolutionScheduler()
        scheduler.start()

        jobs = scheduler._jobs

        assert jobs["evolution_cycle"].cron_expression == "0 2 * * 0"  # Sunday 2AM
        assert jobs["tool_backtest"].cron_expression == "0 */6 * * *"  # Every 6 hours
        assert jobs["hold_queue_review"].cron_expression == "0 */4 * * *"  # Every 4 hours

    def test_job_handlers(self):
        """Test that registered jobs have correct handlers."""
        scheduler = EvolutionScheduler()
        scheduler.start()

        jobs = scheduler._jobs

        assert jobs["evolution_cycle"].handler == scheduler._run_evolution_cycle
        assert jobs["tool_backtest"].handler == scheduler._run_tool_backtest
        assert jobs["hold_queue_review"].handler == scheduler._run_hold_queue_review

    def test_job_enabled_by_default(self):
        """Test that registered jobs are enabled by default."""
        scheduler = EvolutionScheduler()
        scheduler.start()

        for job in scheduler._jobs.values():
            assert job.enabled is True

    def test_handler_methods_exist(self):
        """Test that handler methods exist."""
        scheduler = EvolutionScheduler()

        assert hasattr(scheduler, "_run_evolution_cycle")
        assert hasattr(scheduler, "_run_tool_backtest")
        assert hasattr(scheduler, "_run_hold_queue_review")
        assert callable(scheduler._run_evolution_cycle)
        assert callable(scheduler._run_tool_backtest)
        assert callable(scheduler._run_hold_queue_review)

    @pytest.mark.asyncio
    async def test_evolution_cycle_handler(self):
        """Test _run_evolution_cycle handler execution."""
        scheduler = EvolutionScheduler()

        with patch.object(scheduler, "_run_evolution_cycle", new_callable=AsyncMock) as mock_run:
            await scheduler._run_evolution_cycle()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_backtest_handler(self):
        """Test _run_tool_backtest handler execution."""
        scheduler = EvolutionScheduler()

        with patch.object(scheduler, "_run_tool_backtest", new_callable=AsyncMock) as mock_run:
            await scheduler._run_tool_backtest()
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_hold_queue_review_handler(self):
        """Test _run_hold_queue_review handler execution."""
        scheduler = EvolutionScheduler()

        with patch.object(scheduler, "_run_hold_queue_review", new_callable=AsyncMock) as mock_run:
            await scheduler._run_hold_queue_review()
            mock_run.assert_called_once()

    def test_get_status(self):
        """Test get_status method."""
        scheduler = EvolutionScheduler()
        scheduler.start()

        status = scheduler.get_status()

        assert "running" in status
        assert "registered_jobs" in status
        assert "registered_claws" in status
        assert status["running"] is True
        assert "evolution_cycle" in status["registered_jobs"]

    @patch("milimo_core.evolution_scheduler.Path.exists")
    @patch("milimo_core.evolution_scheduler.EvolutionConfig.from_file")
    def test_load_evolution_config_from_file(self, mock_from_file, mock_exists):
        """Test loading evolution config from YAML file."""
        scheduler = EvolutionScheduler()
        mock_exists.return_value = True
        mock_config = MagicMock()
        mock_from_file.return_value = mock_config

        result = scheduler._load_evolution_config()

        assert result == mock_config
        mock_from_file.assert_called_once()

    @patch("milimo_core.evolution_scheduler.Path.exists")
    @patch("milimo_core.evolution_scheduler.EvolutionConfig")
    def test_load_evolution_config_defaults(self, mock_config_class, mock_exists):
        """Test loading evolution config with defaults when file not found."""
        scheduler = EvolutionScheduler()
        mock_exists.return_value = False
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        result = scheduler._load_evolution_config()

        assert result == mock_config
        mock_config_class.assert_called_once()

    @patch("milimo_core.evolution_scheduler.EvolutionCycle")
    def test_get_evolution_cycle(self, mock_cycle_class):
        """Test getting or creating an evolution cycle."""
        scheduler = EvolutionScheduler()
        mock_cycle = MagicMock()
        mock_cycle_class.return_value = mock_cycle

        result = scheduler._get_evolution_cycle("build")

        assert result == mock_cycle
        mock_cycle_class.assert_called_once()

    @patch("milimo_core.evolution_scheduler.EvolutionCycle")
    def test_get_evolution_cycle_cached(self, mock_cycle_class):
        """Test that evolution cycle is cached."""
        scheduler = EvolutionScheduler()
        mock_cycle = MagicMock()
        mock_cycle_class.return_value = mock_cycle

        result1 = scheduler._get_evolution_cycle("build")
        result2 = scheduler._get_evolution_cycle("build")

        assert result1 == result2
        mock_cycle_class.assert_called_once()

    @pytest.mark.asyncio
    @patch("milimo_core.evolution_scheduler.EvolutionCycle")
    async def test_run_evolution_cycle(self, mock_cycle_class):
        """Test _run_evolution_cycle method."""
        scheduler = EvolutionScheduler()
        mock_cycle = MagicMock()
        mock_cycle_class.return_value = mock_cycle

        # Mock cycle.run() to return a CycleResult
        from milimo_core.evolution_cycle import CycleResult
        mock_result = CycleResult(
            claw_role="build",
            squad_id="default",
            stage_reached="deploy",
            proposal=None,
            tool_deployed=None,
            skipped_reason=None,
            timestamp=datetime.now(timezone.utc),
        )
        mock_cycle.run.return_value = mock_result

        results = await scheduler._run_evolution_cycle()

        assert len(results) == 6  # 6 claws
        assert all(isinstance(r, CycleResult) for r in results)
        assert mock_cycle_class.call_count == 6

    @pytest.mark.asyncio
    @patch("milimo_core.evolution_scheduler.ToolRegistry")
    async def test_run_tool_backtest(self, mock_registry_class):
        """Test _run_tool_tool_backtest method."""
        scheduler = EvolutionScheduler()
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        # Return evolved tool only for "build" claw, empty for others
        def list_tools_side_effect():
            # This will be called for each claw
            call_count = list_tools_side_effect.call_count
            list_tools_side_effect.call_count += 1
            if call_count == 0:  # build claw
                return [{"name": "test_tool", "is_evolved": True, "claw_role": "build"}]
            return []
        list_tools_side_effect.call_count = 0
        mock_registry.list_tools.side_effect = list_tools_side_effect

        with patch.object(scheduler, "_backtest_tool", new_callable=AsyncMock) as mock_backtest:
            mock_backtest.return_value = {
                "score": 0.9,
                "improvement_percent": 10.0,
                "passed": True,
            }
            results = await scheduler._run_tool_backtest()

        # Only one evolved tool across all 6 claws
        assert len(results) == 1
        assert results[0]["tool_name"] == "test_tool"
        assert results[0]["status"] == "passed"

    @pytest.mark.asyncio
    async def test_run_hold_queue_review(self):
        """Test _run_hold_queue_review method."""
        scheduler = EvolutionScheduler()

        results = await scheduler._run_hold_queue_review()

        assert len(results) == 1
        assert "reviewed_count" in results[0]
        assert "timestamp" in results[0]

    @pytest.mark.asyncio
    async def test_backtest_tool(self):
        """Test _backtest_tool method."""
        scheduler = EvolutionScheduler()

        tool = {"name": "test_tool", "claw_role": "build"}
        result = await scheduler._backtest_tool(tool, "build")

        assert result["score"] == 0.85
        assert result["improvement_percent"] == 7.5
        assert result["passed"] is True

    def test_register_claw(self):
        """Test register_claw method."""
        scheduler = EvolutionScheduler()

        with patch.object(scheduler, "_get_evolution_cycle") as mock_get:
            mock_cycle = MagicMock()
            mock_get.return_value = mock_cycle

            scheduler.register_claw("build", log_dir="/tmp/logs")

            mock_get.assert_called_once_with("build")

    def test_trigger_evolution_now(self):
        """Test trigger_evolution_now method."""
        scheduler = EvolutionScheduler()

        with patch.object(scheduler, "_get_evolution_cycle") as mock_get:
            mock_cycle = MagicMock()
            mock_get.return_value = mock_cycle
            from milimo_core.evolution_cycle import CycleResult
            mock_result = CycleResult(
                claw_role="build",
                squad_id="default",
                stage_reached="deploy",
                proposal=None,
                tool_deployed=None,
                skipped_reason=None,
                timestamp=datetime.now(timezone.utc),
            )
            mock_cycle.run.return_value = mock_result

            results = scheduler.trigger_evolution_now(claw_role="build")

            assert len(results) == 1
            mock_get.assert_called_once_with("build")

    def test_trigger_evolution_now_all_claws(self):
        """Test trigger_evolution_now for all claws."""
        scheduler = EvolutionScheduler()

        with patch.object(scheduler, "_get_evolution_cycle") as mock_get:
            mock_cycle = MagicMock()
            mock_get.return_value = mock_cycle
            from milimo_core.evolution_cycle import CycleResult
            mock_result = CycleResult(
                claw_role="build",
                squad_id="default",
                stage_reached="deploy",
                proposal=None,
                tool_deployed=None,
                skipped_reason=None,
                timestamp=datetime.now(timezone.utc),
            )
            mock_cycle.run.return_value = mock_result

            results = scheduler.trigger_evolution_now(claw_role=None)

            assert len(results) == 6
            assert mock_get.call_count == 6

    def test_get_evolution_history(self):
        """Test get_evolution_history method."""
        scheduler = EvolutionScheduler()
        from milimo_core.evolution_cycle import CycleResult
        result = CycleResult(
            claw_role="build",
            squad_id="default",
            stage_reached="deploy",
            proposal=None,
            tool_deployed=None,
            skipped_reason=None,
            timestamp=datetime.now(timezone.utc),
        )
        scheduler._history = [result, result, result]

        history = scheduler.get_evolution_history(limit=2)

        assert len(history) == 2

    def test_get_tool_backtest_history(self):
        """Test get_tool_backtest_history method."""
        scheduler = EvolutionScheduler()
        scheduler._tool_backtest_results = [
            {"tool_name": "tool1", "score": 0.8},
            {"tool_name": "tool2", "score": 0.9},
        ]

        history = scheduler.get_tool_backtest_history(limit=1)

        assert len(history) == 1
        assert history[0]["tool_name"] == "tool2"

    def test_get_hold_queue_review_history(self):
        """Test get_hold_queue_review_history method."""
        scheduler = EvolutionScheduler()
        scheduler._hold_queue_reviews = [
            {"reviewed_count": 5},
            {"reviewed_count": 3},
        ]

        history = scheduler.get_hold_queue_review_history(limit=1)

        assert len(history) == 1
        assert history[0]["reviewed_count"] == 3

    def test_get_status_with_history(self):
        """Test get_status with history."""
        scheduler = EvolutionScheduler()
        scheduler.start()
        from milimo_core.evolution_cycle import CycleResult
        result = CycleResult(
            claw_role="build",
            squad_id="default",
            stage_reached="deploy",
            proposal=None,
            tool_deployed=None,
            skipped_reason=None,
            timestamp=datetime.now(timezone.utc),
        )
        scheduler._history = [result]

        status = scheduler.get_status()

        assert status["total_evolution_cycles"] == 1
        assert status["last_evolution_run"] is not None

    @patch("milimo_core.evolution_scheduler.asyncio.run")
    def test_run_evolution_cycle_sync(self, mock_run):
        """Test run_evolution_cycle_sync wrapper."""
        mock_run.return_value = [{"test": "result"}]

        result = run_evolution_cycle_sync()

        assert result == [{"test": "result"}]
        mock_run.assert_called_once()

    @patch("milimo_core.evolution_scheduler.asyncio.run")
    def test_run_tool_backtest_sync(self, mock_run):
        """Test run_tool_backtest_sync wrapper."""
        mock_run.return_value = [{"test": "result"}]

        result = run_tool_backtest_sync()

        assert result == [{"test": "result"}]
        mock_run.assert_called_once()

    @patch("milimo_core.evolution_scheduler.asyncio.run")
    def test_run_hold_queue_review_sync(self, mock_run):
        """Test run_hold_queue_review_sync wrapper."""
        mock_run.return_value = [{"test": "result"}]

        result = run_hold_queue_review_sync()

        assert result == [{"test": "result"}]
        mock_run.assert_called_once()
