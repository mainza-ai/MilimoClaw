"""Unit tests for scheduling protocol."""

import pytest
from milimo_core.protocols.scheduling import ScheduledJob, SchedulerInterface


class TestScheduledJob:
    """Tests for ScheduledJob dataclass."""

    def test_scheduled_job_creation(self):
        """Test creating a ScheduledJob with all fields."""
        job = ScheduledJob(
            name="test_job",
            cron_expression="0 2 * * 0",
            handler="evolution_cycle",
            enabled=True,
            last_run=None,
            next_run=None
        )
        assert job.name == "test_job"
        assert job.cron_expression == "0 2 * * 0"
        assert job.handler == "evolution_cycle"
        assert job.enabled is True
        assert job.last_run is None
        assert job.next_run is None

    def test_scheduled_job_defaults(self):
        """Test ScheduledJob with defaults."""
        job = ScheduledJob(name="simple", cron_expression="* * * * *", handler="handler")
        assert job.name == "simple"
        assert job.enabled is True
        assert job.last_run is None
        assert job.next_run is None

    def test_scheduled_job_disabled(self):
        """Test disabled ScheduledJob."""
        job = ScheduledJob(
            name="disabled_job",
            cron_expression="0 * * * *",
            handler="handler",
            enabled=False
        )
        assert job.enabled is False


class TestSchedulerInterface:
    """Tests for SchedulerInterface abstract base class."""

    def test_scheduler_interface_is_abstract(self):
        """Test that SchedulerInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SchedulerInterface()

    def test_scheduler_interface_methods(self):
        """Test SchedulerInterface has required methods."""
        required_methods = [
            "schedule_job",
            "unschedule_job",
            "get_due_jobs",
            "start",
            "stop"
        ]
        for method in required_methods:
            assert hasattr(SchedulerInterface, method)


class TestSchedulerImplementation:
    """Tests for SchedulerInterface implementations."""

    def test_mock_scheduler_schedule(self, mock_scheduler, sample_scheduled_job):
        """Test mock scheduler schedule_job."""
        mock_scheduler.schedule_job(sample_scheduled_job)
        mock_scheduler.schedule_job.assert_called_once_with(sample_scheduled_job)

    def test_mock_scheduler_unschedule(self, mock_scheduler):
        """Test mock scheduler unschedule_job."""
        mock_scheduler.unschedule_job("test_job")
        mock_scheduler.unschedule_job.assert_called_once_with("test_job")

    def test_mock_scheduler_get_due(self, mock_scheduler):
        """Test mock scheduler get_due_jobs."""
        jobs = mock_scheduler.get_due_jobs()
        assert isinstance(jobs, list)
        mock_scheduler.get_due_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_mock_scheduler_start_stop(self, mock_scheduler):
        """Test mock scheduler start/stop."""
        await mock_scheduler.start()
        await mock_scheduler.stop()
        mock_scheduler.start.assert_called_once()
        mock_scheduler.stop.assert_called_once()
