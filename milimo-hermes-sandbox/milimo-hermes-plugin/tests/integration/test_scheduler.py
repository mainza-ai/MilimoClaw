"""Integration tests for Hermes plugin scheduler."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from milimo_core.protocols.scheduling import ScheduledJob
from milimo_core.evolution_scheduler import EvolutionSchedulerConfig
from milimo_hermes_plugin.hermes_scheduler import (
    HermesCronScheduler,
    run_evolution_cycle_handler,
    run_tool_backtest_handler,
    run_hold_queue_review_handler,
)


class TestHermesCronScheduler:
    """Test HermesCronScheduler."""

    def test_initialization(self):
        """Test scheduler initialization with core jobs."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        assert scheduler._running is False
        assert "evolution_cycle" in scheduler._jobs
        assert "tool_backtest" in scheduler._jobs
        assert "hold_queue_review" in scheduler._jobs

    def test_core_jobs_registered(self):
        """Test all three core jobs are registered with correct cron expressions."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        evolution_job = scheduler.get_job("evolution_cycle")
        assert evolution_job is not None
        assert evolution_job.cron_expression == "0 2 * * 0"  # Sunday 2AM

        backtest_job = scheduler.get_job("tool_backtest")
        assert backtest_job is not None
        assert backtest_job.cron_expression == "0 */6 * * *"  # Every 6 hours

        hold_job = scheduler.get_job("hold_queue_review")
        assert hold_job is not None
        assert hold_job.cron_expression == "0 */4 * * *"  # Every 4 hours

    def test_schedule_job(self):
        """Test scheduling a new job."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        new_job = ScheduledJob(
            name="custom_job",
            cron_expression="0 * * * *",
            handler=lambda: None,
            enabled=True,
        )

        scheduler.schedule_job(new_job)

        assert "custom_job" in scheduler._jobs
        assert len(scheduler._config_jobs) == 4  # 3 core + 1 custom

    def test_unschedule_job(self):
        """Test unscheduling a job."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        scheduler.unschedule_job("tool_backtest")

        assert "tool_backtest" not in scheduler._jobs
        assert len(scheduler._config_jobs) == 2

    def test_unschedule_nonexistent_job(self):
        """Test unscheduling non-existent job doesn't error."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        scheduler.unschedule_job("nonexistent")

        assert len(scheduler._jobs) == 3  # Still 3 core jobs

    def test_start_stop(self):
        """Test start and stop."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        assert scheduler._running is False

        scheduler.start()
        assert scheduler._running is True

        scheduler.stop()
        assert scheduler._running is False

    def test_get_due_jobs(self):
        """Test getting due jobs."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        # Manually set next_run to past for testing
        for job in scheduler._jobs.values():
            job.next_run = datetime.now() - timedelta(minutes=1)

        due_jobs = scheduler.get_due_jobs()

        assert len(due_jobs) == 3

    def test_get_due_jobs_no_due(self):
        """Test getting due jobs when none are due."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        # Set next_run to future
        for job in scheduler._jobs.values():
            job.next_run = datetime.now() + timedelta(hours=1)

        due_jobs = scheduler.get_due_jobs()

        assert len(due_jobs) == 0

    def test_get_due_jobs_disabled(self):
        """Test disabled jobs not returned."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        # Set all jobs to past
        past = datetime.now() - timedelta(minutes=1)
        for job in scheduler._jobs.values():
            job.next_run = past

        # Disable one job
        scheduler._jobs["tool_backtest"].enabled = False

        due_jobs = scheduler.get_due_jobs()

        assert len(due_jobs) == 2
        assert all(j.enabled for j in due_jobs)
        assert all(j.name != "tool_backtest" for j in due_jobs)

    def test_get_cron_config(self):
        """Test getting cron configuration for Hermes."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        cron_config = scheduler.get_cron_config()

        assert len(cron_config) == 3
        for job in cron_config:
            assert "name" in job
            assert "schedule" in job
            assert "handler" in job
            assert "enabled" in job

    def test_get_status(self):
        """Test getting combined status."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        status = scheduler.get_status()

        assert "running" in status
        assert "registered_jobs" in status
        assert "evolution" in status
        assert set(status["registered_jobs"]) == {"evolution_cycle", "tool_backtest", "hold_queue_review"}

    def test_get_evolution_scheduler(self):
        """Test getting underlying EvolutionScheduler."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        evo_scheduler = scheduler.get_evolution_scheduler()

        assert evo_scheduler is scheduler._evolution_scheduler

    def test_run_evolution_cycle_handler(self):
        """Test evolution cycle handler."""
        with patch('milimo_hermes_plugin.hermes_scheduler.EvolutionScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler._run_evolution_cycle = AsyncMock(return_value=[{"claw": "build", "status": "completed"}])
            mock_scheduler_class.return_value = mock_scheduler

            results = run_evolution_cycle_handler()

            assert len(results) == 1
            assert results[0]["claw"] == "build"

    def test_run_tool_backtest_handler(self):
        """Test tool backtest handler."""
        with patch('milimo_hermes_plugin.hermes_scheduler.EvolutionScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler._run_tool_backtest = AsyncMock(return_value=[{"tool": "test_tool", "passed": True}])
            mock_scheduler_class.return_value = mock_scheduler

            results = run_tool_backtest_handler()

            assert len(results) == 1
            assert results[0]["tool"] == "test_tool"

    def test_run_hold_queue_review_handler(self):
        """Test hold queue review handler."""
        with patch('milimo_hermes_plugin.hermes_scheduler.EvolutionScheduler') as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler._run_hold_queue_review = AsyncMock(return_value=[{"reviewed": 5, "released": 2}])
            mock_scheduler_class.return_value = mock_scheduler

            results = run_hold_queue_review_handler()

            assert len(results) == 1
            assert results[0]["reviewed"] == 5

    def test_job_next_run_calculated(self):
        """Test next_run is calculated on job registration."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        for job in scheduler._jobs.values():
            assert job.next_run is not None
            assert isinstance(job.next_run, datetime)

    def test_job_metadata(self):
        """Test job metadata includes handler_name."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        for job in scheduler._jobs.values():
            assert "handler_name" in job.metadata

    def test_custom_job_metadata(self):
        """Test custom job gets metadata."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        new_job = ScheduledJob(
            name="custom",
            cron_expression="0 * * * *",
            handler=lambda: None,
            enabled=True,
            metadata={"custom": "data"}
        )

        scheduler.schedule_job(new_job)

        job = scheduler.get_job("custom")
        assert job.metadata.get("custom") == "data"


class TestHermesCronSchedulerWithCustomConfig:
    """Test scheduler with custom EvolutionSchedulerConfig."""

    def test_custom_config_passed_to_evolution_scheduler(self):
        """Test custom config passed to EvolutionScheduler."""
        custom_config = EvolutionSchedulerConfig(
            squad_id="custom-squad",
            log_dir="/tmp/logs"
        )

        scheduler = HermesCronScheduler(custom_config)

        assert scheduler._evolution_scheduler.config.squad_id == "custom-squad"
        assert scheduler._evolution_scheduler.config.log_dir == "/tmp/logs"


class TestCalculateNextRun:
    """Test _calculate_next_run static method."""

    def test_calculate_next_run_returns_future_time(self):
        """Test next run is in the future."""
        next_run = HermesCronScheduler._calculate_next_run("0 * * * *")

        assert next_run > datetime.now()
        assert next_run < datetime.now() + timedelta(minutes=2)

    def test_calculate_next_run_different_expressions(self):
        """Test different cron expressions."""
        next_run1 = HermesCronScheduler._calculate_next_run("0 * * * *")
        next_run2 = HermesCronScheduler._calculate_next_run("0 2 * * 0")

        assert next_run1 > datetime.now()
        assert next_run2 > datetime.now()


class TestSchedulerIntegration:
    """Integration-style tests."""

    def test_full_lifecycle(self):
        """Test full scheduler lifecycle."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        # Start
        scheduler.start()
        assert scheduler._running is True

        # Add custom job
        custom_job = ScheduledJob(
            name="daily_report",
            cron_expression="0 8 * * *",
            handler=lambda: None,
            enabled=True,
        )
        scheduler.schedule_job(custom_job)

        # Verify
        assert scheduler.get_job("daily_report") is not None
        assert len(scheduler.get_cron_config()) == 4

        # Get status
        status = scheduler.get_status()
        assert status["running"] is True
        assert "daily_report" in status["registered_jobs"]

        # Stop
        scheduler.stop()
        assert scheduler._running is False

    def test_handler_methods_exist(self):
        """Test all handler methods exist and are callable."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        assert callable(scheduler._run_evolution_cycle)
        assert callable(scheduler._run_tool_backtest)
        assert callable(scheduler._run_hold_queue_review)

    @pytest.mark.asyncio
    async def test_handler_signatures(self):
        """Test handler methods have correct signatures."""
        config = EvolutionSchedulerConfig()
        scheduler = HermesCronScheduler(config)

        # Should not raise
        await scheduler._run_evolution_cycle()
        await scheduler._run_tool_backtest()
        await scheduler._run_hold_queue_review()
