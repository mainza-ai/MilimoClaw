#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Evolution Scheduler

Schedules and manages the weekly self-evolution cycle for solo founders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

logger = logging.getLogger("milimo.solo_evolution")


# ---------------------------------------------------------------------------

DAYS_OF_WEEK = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

EVOLUTION_THRESHOLDS = {
    "content": "min_approved_posts",
    "ops": "min_client_interactions",
    "analytics": "min_data_weeks",
    "finance": "min_invoices",
    "build": "min_prs_merged",
    "assistant": "min_assisted_tasks",
}

DEFAULT_EVOLUTION_SCHEDULE = {
    "analytics_baseline": "01:00",
    "analytics_report": "02:00",
    "content": "02:05",
    "ops": "02:15",
    "analytics_evolution": "02:25",
    "build": "02:35",
    "finance": "03:00",
    "assistant": "03:15",
}

CLAW_SCHEDULE_KEYS = {
    "content": "content",
    "ops": "ops",
    "analytics": "analytics_evolution",
    "finance": "finance",
    "build": "build",
    "assistant": "assistant",
}

# Additional thresholds for Content Claw
CONTENT_ADDITIONAL_THRESHOLDS = {
    "rejected_drafts_min": 3,
    "performance_data_weeks_min": 1,
}


# ---------------------------------------------------------------------------


@dataclass
class EvolutionSchedule:
    """Schedule for a claw's evolution cycle."""

    claw: str
    enabled: bool = True
    day: str = "sunday"
    time: str = "02:00"
    threshold_field: str = ""
    threshold_value: int = 0
    performance_threshold: int = 5
    next_run: Optional[datetime] = None


@dataclass
class EvolutionStatus:
    """Status of evolution for a claw."""

    claw: str
    can_evolve: bool
    reason: str
    current_activity: int
    required_activity: int
    last_evolution: Optional[datetime] = None


# ---------------------------------------------------------------------------


def parse_evolution_schedule(evolution_config: dict[str, Any]) -> dict[str, str]:
    """
    Parse per-claw evolution schedule from solo-founder.yaml.

    Args:
        evolution_config: Evolution section from config

    Returns:
        Dict mapping claw role to scheduled time string.
        Falls back to legacy single-time format if schedule key missing.
    """
    schedule = evolution_config.get("schedule", {})

    if schedule:
        return {
            "content": schedule.get("content", DEFAULT_EVOLUTION_SCHEDULE["content"]),
            "ops": schedule.get("ops", DEFAULT_EVOLUTION_SCHEDULE["ops"]),
            "analytics_evolution": schedule.get(
                "analytics_evolution", DEFAULT_EVOLUTION_SCHEDULE["analytics_evolution"]
            ),
            "build": schedule.get("build", DEFAULT_EVOLUTION_SCHEDULE["build"]),
            "finance": schedule.get("finance", DEFAULT_EVOLUTION_SCHEDULE["finance"]),
        }
    else:
        legacy_time = evolution_config.get("time", "02:00")
        return {role: legacy_time for role in CLAW_SCHEDULE_KEYS.keys()}


def get_claw_schedule_time(evolution_config: dict[str, Any], claw: str) -> str:
    """
    Get the scheduled time for a specific claw.

    Args:
        evolution_config: Evolution section from config
        claw: Claw name

    Returns:
        Time string (HH:MM) for that claw's evolution cycle
    """
    schedule = parse_evolution_schedule(evolution_config)
    return schedule.get(claw, "02:00")


def _init_evolution_timers(
    evolution_config: dict[str, Any],
    claw_schedulers: dict[str, Any],
    schedule_fn: Any,
    log_fn: Any,
) -> dict[str, Any]:
    """
    Initialize per-claw evolution timers from staggered schedule.

    This function creates one timer per active claw based on the
    per-claw schedule defined in solo-founder.yaml.

    Args:
        evolution_config: Evolution section from config
        claw_schedulers: Dict mapping role name to that claw's scheduler instance.
            Each scheduler must expose a run_evolution_cycle() method.
        schedule_fn: Function to schedule a weekly job.
            Signature: (job_name, job_fn, target_hour, target_minute, target_weekday)
        log_fn: Function to log messages.

    Returns:
        Dict with 'scheduled' (list of claw names) and 'skipped' (list of claw names)
    """
    schedule = parse_evolution_schedule(evolution_config)
    result = {"scheduled": [], "skipped": []}

    for role, time_str in schedule.items():
        if role not in claw_schedulers or claw_schedulers[role] is None:
            log_fn(f"Skipping {role} — not active in current template")
            result["skipped"].append(role)
            continue

        hour, minute = map(int, time_str.split(":"))
        scheduler = claw_schedulers[role]

        if not hasattr(scheduler, "run_evolution_cycle"):
            log_fn(f"Skipping {role} — scheduler missing run_evolution_cycle method")
            result["skipped"].append(role)
            continue

        job_name = f"{role}_evolution"

        schedule_fn(
            job_name=job_name,
            job_fn=scheduler.run_evolution_cycle,
            target_hour=hour,
            target_minute=minute,
            target_weekday=6,
        )

        log_fn(f"Evolution scheduled for {role} at {time_str} on Sunday")
        result["scheduled"].append(role)

    return result


# ---------------------------------------------------------------------------


def schedule_evolution(
    config: dict[str, Any],
    current_activity: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """
    Schedule the evolution cycle based on configuration.

    Args:
        config: Validated solo-founder configuration
        current_activity: Current activity counts per claw

    Returns:
        Schedule and status information
    """
    evolution_config = config.get("evolution", {})

    cycle_day = evolution_config.get("cycle_day", "sunday")
    per_claw = evolution_config.get("per_claw", {})
    capacity = evolution_config.get("capacity", {})

    claw_schedule = parse_evolution_schedule(evolution_config)

    if current_activity is None:
        current_activity = {}

    schedules: dict[str, EvolutionSchedule] = {}
    statuses: dict[str, EvolutionStatus] = {}

    for claw, claw_config in per_claw.items():
        enabled = claw_config.get("enabled", True)

        threshold_field = EVOLUTION_THRESHOLDS.get(claw, "")
        threshold_value = claw_config.get(threshold_field, 0) if threshold_field else 0
        performance_threshold = claw_config.get("performance_threshold", 5)

        claw_time = claw_schedule.get(claw, "02:00")

        schedule = EvolutionSchedule(
            claw=claw,
            enabled=enabled,
            day=cycle_day,
            time=claw_time,
            threshold_field=threshold_field,
            threshold_value=threshold_value,
            performance_threshold=performance_threshold,
            next_run=_calculate_next_run(cycle_day, claw_time) if enabled else None,
        )
        schedules[claw] = schedule

        current = current_activity.get(claw, 0)
        can_evolve = _check_evolution_threshold(claw, claw_config, current)

        status = EvolutionStatus(
            claw=claw,
            can_evolve=can_evolve["can_evolve"],
            reason=can_evolve["reason"],
            current_activity=current,
            required_activity=threshold_value,
        )
        statuses[claw] = status

        logger.info(
            f"Evolution schedule for {claw}: enabled={enabled}, "
            f"threshold={threshold_value} ({threshold_field}), "
            f"time={claw_time}, next_run={schedule.next_run}"
        )

    result: dict[str, Any] = {
        "cycle": "weekly",
        "day": cycle_day,
        "schedule": claw_schedule,
        "capacity": capacity,
        "schedules": {k: _schedule_to_dict(v) for k, v in schedules.items()},
        "statuses": {k: _status_to_dict(v) for k, v in statuses.items()},
        "next_evolution": _get_next_evolution_time(schedules),
    }

    _log_evolution_schedule_v2(result)

    return result


def _calculate_next_run(day: str, time_str: str) -> datetime:
    """
    Calculate the next run time.

    Args:
        day: Day of the week
        time_str: Time string (HH:MM)

    Returns:
        Next run datetime
    """
    target_day = DAYS_OF_WEEK.get(day.lower(), 6)
    hour, minute = map(int, time_str.split(":"))

    now = datetime.now(timezone.utc)

    days_until = (target_day - now.weekday()) % 7
    if days_until == 0:
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_time <= now:
            days_until = 7

    next_run = now + timedelta(days=days_until)
    next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return next_run


def _check_evolution_threshold(
    claw: str,
    config: dict[str, Any],
    current: int,
) -> dict[str, Any]:
    """
    Check if a claw meets evolution threshold.

    Args:
        claw: Claw name
        config: Claw evolution config
        current: Current activity count

    Returns:
        Dictionary with can_evolve and reason
    """
    threshold_field = EVOLUTION_THRESHOLDS.get(claw)

    if not threshold_field:
        return {"can_evolve": True, "reason": "No threshold required"}

    required = config.get(threshold_field, 0)

    if current >= required:
        return {
            "can_evolve": True,
            "reason": f"Threshold met: {current}/{required} {threshold_field}",
        }
    else:
        return {
            "can_evolve": False,
            "reason": f"Threshold not met: {current}/{required} {threshold_field} (need {required - current} more)",
        }


def _get_next_evolution_time(
    schedules: dict[str, EvolutionSchedule],
) -> Optional[datetime]:
    """
    Get the next evolution time across all claws.

    Args:
        schedules: Evolution schedules

    Returns:
        Next evolution datetime, or None if no enabled schedules
    """
    next_times = [s.next_run for s in schedules.values() if s.enabled and s.next_run]

    if not next_times:
        return None

    return min(next_times)


def _schedule_to_dict(schedule: EvolutionSchedule) -> dict[str, Any]:
    """Convert EvolutionSchedule to dictionary."""
    return {
        "claw": schedule.claw,
        "enabled": schedule.enabled,
        "day": schedule.day,
        "time": schedule.time,
        "threshold_field": schedule.threshold_field,
        "threshold_value": schedule.threshold_value,
        "performance_threshold": schedule.performance_threshold,
        "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
    }


def _status_to_dict(status: EvolutionStatus) -> dict[str, Any]:
    """Convert EvolutionStatus to dictionary."""
    return {
        "claw": status.claw,
        "can_evolve": status.can_evolve,
        "reason": status.reason,
        "current_activity": status.current_activity,
        "required_activity": status.required_activity,
        "last_evolution": status.last_evolution.isoformat()
        if status.last_evolution
        else None,
    }


def _log_evolution_schedule(result: dict[str, Any]) -> None:
    """Log the evolution schedule to War Room."""
    print("\n" + "=" * 60)
    print("EVOLUTION SCHEDULE")
    print("=" * 60)
    print()

    print(f"Day: {result.get('day', 'sunday').capitalize()}")
    if "schedule" in result:
        print("Per-claw times:")
        for claw, time_str in result["schedule"].items():
            print(f"  {claw}: {time_str} UTC")
    else:
        print(f"Time: {result.get('time', '02:00')} UTC")
    print()

    print("Claw Evolution Status:")
    for claw, status in result.get("statuses", {}).items():
        emoji = "" if status["can_evolve"] else ""
        print(f" {emoji} {claw.capitalize()}: {status['reason']}")
    print()

    if result.get("next_evolution"):
        next_ev = result["next_evolution"]
        if isinstance(next_ev, datetime):
            next_run = next_ev
        else:
            next_run = datetime.fromisoformat(next_ev.replace("Z", "+00:00"))
        print(f"Next evolution: {next_run.strftime('%Y-%m-%d %H:%M')} UTC")
        print()

    capacity = result.get("capacity", {})
    if capacity:
        print("Capacity:")
        print(f" Max tools per claw: {capacity.get('max_tools_per_claw', 30)}")
        print(f" Log retention: {capacity.get('evolution_log_retention', 90)} days")
        print()

    print("=" * 60 + "\n")


def _log_evolution_schedule_v2(result: dict[str, Any]) -> None:
    """Log the evolution schedule to War Room (v2 format with per-claw times)."""
    print("\n" + "=" * 60)
    print("EVOLUTION SCHEDULE")
    print("=" * 60)
    print()

    print(f"Day: {result.get('day', 'sunday').capitalize()}")

    schedule = result.get("schedule", {})
    if schedule:
        print()
        print("Per-claw schedule (staggered):")
        for claw, time_str in schedule.items():
            print(f"  {claw}: {time_str} UTC")
    print()

    print("Claw Evolution Status:")
    for claw, status in result.get("statuses", {}).items():
        emoji = "" if status["can_evolve"] else ""
        print(f" {emoji} {claw.capitalize()}: {status['reason']}")
    print()

    if result.get("next_evolution"):
        next_ev = result["next_evolution"]
        if isinstance(next_ev, datetime):
            next_run = next_ev
        else:
            next_run = datetime.fromisoformat(next_ev.replace("Z", "+00:00"))
        print(f"Next evolution: {next_run.strftime('%Y-%m-%d %H:%M')} UTC")
        print()

    capacity = result.get("capacity", {})
    if capacity:
        print("Capacity:")
        print(f" Max tools per claw: {capacity.get('max_tools_per_claw', 30)}")
        print(f" Log retention: {capacity.get('evolution_log_retention', 90)} days")
        print()

    print("=" * 60 + "\n")


def check_claw_evolution_ready(
    config: dict[str, Any],
    claw: str,
    current_activity: int,
    additional_data: dict[str, Any] | None = None,
) -> bool:
    """
    Check if a specific claw is ready for evolution.

    Args:
        config: Validated solo-founder configuration
        claw: Claw name
        current_activity: Current activity count
        additional_data: Optional dict with claw-specific data:
            - rejected_count: Number of rejected drafts (Content Claw)
            - performance_log_age_days: Days of performance data (Content Claw)

    Returns:
        True if ready for evolution
    """
    evolution_config = config.get("evolution", {}).get("per_claw", {}).get(claw, {})

    if not evolution_config.get("enabled", True):
        logger.info(f"{claw} evolution is disabled")
        return False

    result = _check_evolution_threshold(claw, evolution_config, current_activity)

    if not result["can_evolve"]:
        logger.info(f"{claw} evolution check: {result['reason']}")
        return False

    # Content Claw specific additional thresholds
    if claw == "content" and additional_data:
        rejected_count = additional_data.get("rejected_count", 0)
        rejected_min = CONTENT_ADDITIONAL_THRESHOLDS["rejected_drafts_min"]

        if rejected_count < rejected_min:
            logger.info(
                f"content evolution skipped — insufficient rejected_drafts data "
                f"(have {rejected_count}, need {rejected_min})"
            )
            return False

        performance_weeks = additional_data.get("performance_log_age_days", 0) // 7
        weeks_min = CONTENT_ADDITIONAL_THRESHOLDS["performance_data_weeks_min"]

        if performance_weeks < weeks_min:
            logger.info(
                f"content evolution skipped — insufficient performance data "
                f"(have {performance_weeks} weeks, need {weeks_min} week)"
            )
            return False

    logger.info(f"{claw} evolution check: {result['reason']}")
    return True


def check_content_evolution_thresholds(
    approved_count: int,
    rejected_count: int,
    performance_log_age_days: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Check all Content Claw evolution thresholds.

    This function checks:
    - min_approved_posts (default: 10)
    - rejected_drafts_min (default: 3)
    - performance_data_weeks_min (default: 1)

    Args:
        approved_count: Number of approved posts
        rejected_count: Number of rejected drafts
        performance_log_age_days: Age of performance data in days
        config: Optional config to read threshold values

    Returns:
        Dict with 'can_evolve', 'reasons', 'thresholds_checked'
    """
    if config:
        evolution_config = (
            config.get("evolution", {}).get("per_claw", {}).get("content", {})
        )
    else:
        evolution_config = {}

    min_approved = evolution_config.get("min_approved_posts", 10)
    rejected_min = CONTENT_ADDITIONAL_THRESHOLDS["rejected_drafts_min"]
    weeks_min = CONTENT_ADDITIONAL_THRESHOLDS["performance_data_weeks_min"]

    results = {
        "can_evolve": True,
        "reasons": [],
        "thresholds_checked": {
            "approved_posts": {
                "required": min_approved,
                "actual": approved_count,
                "passed": True,
            },
            "rejected_drafts": {
                "required": rejected_min,
                "actual": rejected_count,
                "passed": True,
            },
            "performance_weeks": {
                "required": weeks_min,
                "actual": performance_log_age_days // 7,
                "passed": True,
            },
        },
    }

    # Check approved posts
    if approved_count < min_approved:
        results["can_evolve"] = False
        results["reasons"].append(
            f"insufficient approved_posts data (have {approved_count}, need {min_approved})"
        )
        results["thresholds_checked"]["approved_posts"]["passed"] = False

    # Check rejected drafts
    if rejected_count < rejected_min:
        results["can_evolve"] = False
        results["reasons"].append(
            f"insufficient rejected_drafts data (have {rejected_count}, need {rejected_min})"
        )
        results["thresholds_checked"]["rejected_drafts"]["passed"] = False

    # Check performance data age
    performance_weeks = performance_log_age_days // 7
    if performance_weeks < weeks_min:
        results["can_evolve"] = False
        results["reasons"].append(
            f"insufficient performance data (have {performance_weeks} weeks, need {weeks_min} week)"
        )
        results["thresholds_checked"]["performance_weeks"]["passed"] = False

    if not results["can_evolve"]:
        logger.info(f"content evolution skipped — {'; '.join(results['reasons'])}")

    return results


def get_evolution_summary(config: dict[str, Any]) -> str:
    """
    Get a human-readable evolution summary.

    Args:
        config: Validated solo-founder configuration

    Returns:
        Summary string
    """
    evolution_config = config.get("evolution", {})
    per_claw = evolution_config.get("per_claw", {})

    lines = [
        f"Evolution Cycle: {evolution_config.get('cycle', 'weekly')}",
        f"Runs on: {evolution_config.get('day', 'sunday')} at {evolution_config.get('time', '02:00')} UTC",
        "",
        "Per-claw thresholds:",
    ]

    for claw, claw_config in per_claw.items():
        threshold_field = EVOLUTION_THRESHOLDS.get(claw)
        if threshold_field:
            threshold = claw_config.get(threshold_field, 0)
            lines.append(f"  {claw}: {threshold} {threshold_field}")

    return "\n".join(lines)
