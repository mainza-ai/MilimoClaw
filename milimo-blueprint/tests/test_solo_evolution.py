#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo_evolution.py - Evolution Scheduler
"""

from datetime import datetime, timezone, timedelta
from typing import Any

import pytest

from orchestrator.solo_evolution import (
    schedule_evolution,
    check_claw_evolution_ready,
    check_content_evolution_thresholds,
    get_evolution_summary,
    _calculate_next_run,
    _check_evolution_threshold,
    EvolutionSchedule,
    EvolutionStatus,
    DAYS_OF_WEEK,
    EVOLUTION_THRESHOLDS,
    CONTENT_ADDITIONAL_THRESHOLDS,
)


# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "evolution": {
        "cycle": "weekly",
        "day": "sunday",
        "time": "02:00",
        "per_claw": {
            "content": {
                "enabled": True,
                "min_approved_posts": 10,
                "performance_threshold": 5,
            },
            "ops": {
                "enabled": True,
                "min_client_interactions": 5,
                "performance_threshold": 5,
            },
            "analytics": {
                "enabled": True,
                "min_data_weeks": 3,
                "performance_threshold": 5,
            },
            "finance": {
                "enabled": True,
                "min_invoices": 3,
                "performance_threshold": 5,
            },
            "build": {
                "enabled": True,
                "min_prs_merged": 5,
                "performance_threshold": 5,
            },
        },
        "capacity": {
            "max_tools_per_claw": 30,
            "evolution_log_retention": 90,
        },
    },
}


# ---------------------------------------------------------------------------

class TestScheduleEvolution:
    """Tests for schedule_evolution function."""

    def test_basic_schedule(self) -> None:
        """Test basic schedule creation."""
        result = schedule_evolution(VALID_CONFIG)

        assert result["cycle"] == "weekly"
        assert result["day"] == "sunday"
        assert result["time"] == "02:00"

    def test_all_claws_have_schedules(self) -> None:
        """Test that all claws have schedules."""
        result = schedule_evolution(VALID_CONFIG)

        assert "content" in result["schedules"]
        assert "ops" in result["schedules"]
        assert "analytics" in result["schedules"]
        assert "finance" in result["schedules"]
        assert "build" in result["schedules"]

    def test_threshold_field_assigned(self) -> None:
        """Test that threshold fields are assigned."""
        result = schedule_evolution(VALID_CONFIG)

        assert result["schedules"]["content"]["threshold_field"] == "min_approved_posts"
        assert result["schedules"]["ops"]["threshold_field"] == "min_client_interactions"
        assert result["schedules"]["finance"]["threshold_field"] == "min_invoices"

    def test_threshold_values_assigned(self) -> None:
        """Test that threshold values are assigned."""
        result = schedule_evolution(VALID_CONFIG)

        assert result["schedules"]["content"]["threshold_value"] == 10
        assert result["schedules"]["ops"]["threshold_value"] == 5
        assert result["schedules"]["finance"]["threshold_value"] == 3

    def test_with_current_activity_below_threshold(self) -> None:
        """Test status when activity is below threshold."""
        current_activity = {
            "content": 5,
            "ops": 2,
            "analytics": 1,
            "finance": 1,
            "build": 2,
        }

        result = schedule_evolution(VALID_CONFIG, current_activity)

        assert result["statuses"]["content"]["can_evolve"] is False
        assert "not met" in result["statuses"]["content"]["reason"]

    def test_with_current_activity_above_threshold(self) -> None:
        """Test status when activity is above threshold."""
        current_activity = {
            "content": 15,
            "ops": 10,
            "analytics": 5,
            "finance": 5,
            "build": 10,
        }

        result = schedule_evolution(VALID_CONFIG, current_activity)

        assert result["statuses"]["content"]["can_evolve"] is True
        assert "met" in result["statuses"]["content"]["reason"]

    def test_next_evolution_calculated(self) -> None:
        """Test that next evolution time is calculated."""
        result = schedule_evolution(VALID_CONFIG)

        assert result["next_evolution"] is not None

    def test_disabled_claw_no_next_run(self) -> None:
        """Test that disabled claws have no next run."""
        config = {
            "evolution": {
                "cycle": "weekly",
                "day": "sunday",
                "time": "02:00",
                "per_claw": {
                    "content": {
                        "enabled": False,
                        "min_approved_posts": 10,
                    },
                },
            },
        }

        result = schedule_evolution(config)

        assert result["schedules"]["content"]["enabled"] is False
        assert result["schedules"]["content"]["next_run"] is None

    def test_capacity_included(self) -> None:
        """Test that capacity config is included."""
        result = schedule_evolution(VALID_CONFIG)

        assert "capacity" in result
        assert result["capacity"]["max_tools_per_claw"] == 30

    def test_status_current_activity(self) -> None:
        """Test that status includes current activity."""
        current_activity = {"content": 8}

        result = schedule_evolution(VALID_CONFIG, current_activity)

        assert result["statuses"]["content"]["current_activity"] == 8
        assert result["statuses"]["content"]["required_activity"] == 10


class TestCalculateNextRun:
    """Tests for _calculate_next_run function."""

    def test_returns_datetime(self) -> None:
        """Test that datetime is returned."""
        next_run = _calculate_next_run("sunday", "02:00")

        assert isinstance(next_run, datetime)

    def test_correct_day(self) -> None:
        """Test that the correct day is calculated."""
        next_run = _calculate_next_run("sunday", "02:00")

        assert next_run.weekday() == 6

    def test_correct_time(self) -> None:
        """Test that the correct time is set."""
        next_run = _calculate_next_run("sunday", "14:30")

        assert next_run.hour == 14
        assert next_run.minute == 30

    def test_future_date(self) -> None:
        """Test that next run is in the future."""
        next_run = _calculate_next_run("sunday", "02:00")
        now = datetime.now(timezone.utc)

        assert next_run > now or next_run.date() >= now.date()


class TestCheckEvolutionThreshold:
    """Tests for _check_evolution_threshold function."""

    def test_threshold_met(self) -> None:
        """Test when threshold is met."""
        config = {"min_approved_posts": 10}
        result = _check_evolution_threshold("content", config, 15)

        assert result["can_evolve"] is True
        assert "met" in result["reason"]

    def test_threshold_not_met(self) -> None:
        """Test when threshold is not met."""
        config = {"min_approved_posts": 10}
        result = _check_evolution_threshold("content", config, 5)

        assert result["can_evolve"] is False
        assert "not met" in result["reason"]

    def test_no_threshold(self) -> None:
        """Test when no threshold is defined."""
        config = {}
        result = _check_evolution_threshold("unknown", config, 5)

        assert result["can_evolve"] is True
        assert "No threshold" in result["reason"]


class TestCheckClawEvolutionReady:
    """Tests for check_claw_evolution_ready function."""

    def test_ready_when_threshold_met(self) -> None:
        """Test ready when threshold is met."""
        ready = check_claw_evolution_ready(VALID_CONFIG, "content", 15)

        assert ready is True

    def test_not_ready_when_threshold_not_met(self) -> None:
        """Test not ready when threshold not met."""
        ready = check_claw_evolution_ready(VALID_CONFIG, "content", 5)

        assert ready is False

    def test_not_ready_when_disabled(self) -> None:
        """Test not ready when evolution is disabled."""
        config: dict[str, Any] = {
            "evolution": {
                "per_claw": {
                    "content": {
                        "enabled": False,
                        "min_approved_posts": 10,
                    },
                },
            },
        }

        ready = check_claw_evolution_ready(config, "content", 15)

        assert ready is False


class TestGetEvolutionSummary:
    """Tests for get_evolution_summary function."""

    def test_returns_string(self) -> None:
        """Test that a string is returned."""
        summary = get_evolution_summary(VALID_CONFIG)

        assert isinstance(summary, str)

    def test_includes_cycle(self) -> None:
        """Test that cycle is included."""
        summary = get_evolution_summary(VALID_CONFIG)

        assert "weekly" in summary

    def test_includes_day_and_time(self) -> None:
        """Test that day and time are included."""
        summary = get_evolution_summary(VALID_CONFIG)

        assert "sunday" in summary
        assert "02:00" in summary

    def test_includes_thresholds(self) -> None:
        """Test that thresholds are included."""
        summary = get_evolution_summary(VALID_CONFIG)

        assert "min_approved_posts" in summary
        assert "min_client_interactions" in summary


class TestEvolutionSchedule:
    """Tests for EvolutionSchedule dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        schedule = EvolutionSchedule(claw="content")

        assert schedule.enabled is True
        assert schedule.day == "sunday"
        assert schedule.time == "02:00"
        assert schedule.next_run is None


class TestEvolutionStatus:
    """Tests for EvolutionStatus dataclass."""

    def test_required_fields(self) -> None:
        """Test required fields."""
        status = EvolutionStatus(
            claw="content",
            can_evolve=True,
            reason="Threshold met",
            current_activity=15,
            required_activity=10,
        )

        assert status.claw == "content"
        assert status.can_evolve is True
        assert status.current_activity == 15


class TestConstants:
    """Tests for module constants."""

    def test_days_of_week_mapping(self) -> None:
        """Test day of week mapping."""
        assert DAYS_OF_WEEK["monday"] == 0
        assert DAYS_OF_WEEK["sunday"] == 6

    def test_evolution_thresholds_mapping(self) -> None:
        """Test evolution thresholds mapping."""
        assert EVOLUTION_THRESHOLDS["content"] == "min_approved_posts"
        assert EVOLUTION_THRESHOLDS["build"] == "min_prs_merged"

    def test_content_additional_thresholds(self) -> None:
        """Test content additional thresholds exist."""
        assert "rejected_drafts_min" in CONTENT_ADDITIONAL_THRESHOLDS
        assert "performance_data_weeks_min" in CONTENT_ADDITIONAL_THRESHOLDS
        assert CONTENT_ADDITIONAL_THRESHOLDS["rejected_drafts_min"] == 3
        assert CONTENT_ADDITIONAL_THRESHOLDS["performance_data_weeks_min"] == 1


class TestCheckContentEvolutionThresholds:
    """Tests for check_content_evolution_thresholds function."""

    def test_all_thresholds_met(self) -> None:
        """Test when all thresholds are met."""
        result = check_content_evolution_thresholds(
            approved_count=15,
            rejected_count=5,
            performance_log_age_days=14,
        )

        assert result["can_evolve"] is True
        assert len(result["reasons"]) == 0
        assert result["thresholds_checked"]["approved_posts"]["passed"] is True
        assert result["thresholds_checked"]["rejected_drafts"]["passed"] is True
        assert result["thresholds_checked"]["performance_weeks"]["passed"] is True

    def test_approved_posts_threshold_fails(self) -> None:
        """Test when approved posts threshold fails."""
        result = check_content_evolution_thresholds(
            approved_count=5,
            rejected_count=5,
            performance_log_age_days=14,
        )

        assert result["can_evolve"] is False
        assert any("approved_posts" in r for r in result["reasons"])
        assert result["thresholds_checked"]["approved_posts"]["passed"] is False

    def test_rejected_drafts_threshold_fails(self) -> None:
        """Test when rejected drafts threshold fails."""
        result = check_content_evolution_thresholds(
            approved_count=15,
            rejected_count=1,
            performance_log_age_days=14,
        )

        assert result["can_evolve"] is False
        assert any("rejected_drafts" in r for r in result["reasons"])
        assert result["thresholds_checked"]["rejected_drafts"]["passed"] is False

    def test_performance_weeks_threshold_fails(self) -> None:
        """Test when performance weeks threshold fails."""
        result = check_content_evolution_thresholds(
            approved_count=15,
            rejected_count=5,
            performance_log_age_days=3,
        )

        assert result["can_evolve"] is False
        assert any("performance" in r for r in result["reasons"])
        assert result["thresholds_checked"]["performance_weeks"]["passed"] is False

    def test_threshold_at_minimum_passes(self) -> None:
        """Test that exactly at minimum threshold passes (boundary condition)."""
        result = check_content_evolution_thresholds(
            approved_count=10,
            rejected_count=3,
            performance_log_age_days=7,
        )

        assert result["can_evolve"] is True
        assert result["thresholds_checked"]["approved_posts"]["actual"] == 10
        assert result["thresholds_checked"]["rejected_drafts"]["actual"] == 3
        assert result["thresholds_checked"]["performance_weeks"]["actual"] == 1

    def test_multiple_thresholds_fail(self) -> None:
        """Test when multiple thresholds fail."""
        result = check_content_evolution_thresholds(
            approved_count=2,
            rejected_count=1,
            performance_log_age_days=2,
        )

        assert result["can_evolve"] is False
        assert len(result["reasons"]) == 3

    def test_custom_config_thresholds(self) -> None:
        """Test with custom config thresholds."""
        config: dict[str, Any] = {
            "evolution": {
                "per_claw": {
                    "content": {
                        "min_approved_posts": 5,
                    },
                },
            },
        }

        result = check_content_evolution_thresholds(
            approved_count=7,
            rejected_count=3,
            performance_log_age_days=7,
            config=config,
        )

        assert result["can_evolve"] is True
        assert result["thresholds_checked"]["approved_posts"]["required"] == 5


class TestCheckClawEvolutionReadyWithAdditionalData:
    """Tests for check_claw_evolution_ready with Content Claw additional thresholds."""

    def test_content_ready_with_all_thresholds_met(self) -> None:
        """Test Content Claw ready when all thresholds met."""
        ready = check_claw_evolution_ready(
            VALID_CONFIG,
            "content",
            15,
            additional_data={
                "rejected_count": 5,
                "performance_log_age_days": 14,
            },
        )

        assert ready is True

    def test_content_not_ready_rejected_threshold_fails(self) -> None:
        """Test Content Claw not ready when rejected threshold fails."""
        ready = check_claw_evolution_ready(
            VALID_CONFIG,
            "content",
            15,
            additional_data={
                "rejected_count": 1,
                "performance_log_age_days": 14,
            },
        )

        assert ready is False

    def test_content_not_ready_performance_threshold_fails(self) -> None:
        """Test Content Claw not ready when performance threshold fails."""
        ready = check_claw_evolution_ready(
            VALID_CONFIG,
            "content",
            15,
            additional_data={
                "rejected_count": 5,
                "performance_log_age_days": 3,
            },
        )

        assert ready is False

    def test_other_claws_ignore_additional_data(self) -> None:
        """Test that non-content claws ignore additional_data."""
        ready = check_claw_evolution_ready(
            VALID_CONFIG,
            "ops",
            10,
            additional_data={
                "rejected_count": 0,
                "performance_log_age_days": 0,
            },
        )

        # Ops claw doesn't check content thresholds
        assert ready is True
