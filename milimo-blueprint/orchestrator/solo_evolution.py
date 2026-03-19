#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Evolution Scheduler

Schedules and manages the weekly self-evolution cycle for solo founders.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
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

    cycle = evolution_config.get("cycle", "weekly")
    day = evolution_config.get("day", "sunday")
    time_str = evolution_config.get("time", "02:00")

    per_claw = evolution_config.get("per_claw", {})
    capacity = evolution_config.get("capacity", {})

    if current_activity is None:
        current_activity = {}

    schedules: dict[str, EvolutionSchedule] = {}
    statuses: dict[str, EvolutionStatus] = {}

    for claw, claw_config in per_claw.items():
        enabled = claw_config.get("enabled", True)

        threshold_field = EVOLUTION_THRESHOLDS.get(claw, "")
        threshold_value = claw_config.get(threshold_field, 0) if threshold_field else 0
        performance_threshold = claw_config.get("performance_threshold", 5)

        schedule = EvolutionSchedule(
            claw=claw,
            enabled=enabled,
            day=day,
            time=time_str,
            threshold_field=threshold_field,
            threshold_value=threshold_value,
            performance_threshold=performance_threshold,
            next_run=_calculate_next_run(day, time_str) if enabled else None,
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
            f"next_run={schedule.next_run}"
        )

    result: dict[str, Any] = {
        "cycle": cycle,
        "day": day,
        "time": time_str,
        "capacity": capacity,
        "schedules": {k: _schedule_to_dict(v) for k, v in schedules.items()},
        "statuses": {k: _status_to_dict(v) for k, v in statuses.items()},
        "next_evolution": _get_next_evolution_time(schedules),
    }

    _log_evolution_schedule(result)

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


def _get_next_evolution_time(schedules: dict[str, EvolutionSchedule]) -> Optional[datetime]:
    """
    Get the next evolution time across all claws.

    Args:
        schedules: Evolution schedules

    Returns:
        Next evolution datetime, or None if no enabled schedules
    """
    next_times = [
        s.next_run for s in schedules.values()
        if s.enabled and s.next_run
    ]

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
        "last_evolution": status.last_evolution.isoformat() if status.last_evolution else None,
    }


def _log_evolution_schedule(result: dict[str, Any]) -> None:
    """Log the evolution schedule to War Room."""
    print("\n" + "=" * 60)
    print("🔄  EVOLUTION SCHEDULE")
    print("=" * 60)
    print()

    print(f"Cycle: {result['cycle'].capitalize()}")
    print(f"Day: {result['day'].capitalize()}")
    print(f"Time: {result['time']} UTC")
    print()

    print("Claw Evolution Status:")
    for claw, status in result["statuses"].items():
        emoji = "✅" if status["can_evolve"] else "⏳"
        print(f"   {emoji} {claw.capitalize()}: {status['reason']}")
    print()

    if result["next_evolution"]:
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
        print(f"   Max tools per claw: {capacity.get('max_tools_per_claw', 30)}")
        print(f"   Log retention: {capacity.get('evolution_log_retention', 90)} days")
    print()

    print("=" * 60 + "\n")


def check_claw_evolution_ready(
    config: dict[str, Any],
    claw: str,
    current_activity: int,
) -> bool:
    """
    Check if a specific claw is ready for evolution.

    Args:
        config: Validated solo-founder configuration
        claw: Claw name
        current_activity: Current activity count

    Returns:
        True if ready for evolution
    """
    evolution_config = config.get("evolution", {}).get("per_claw", {}).get(claw, {})

    if not evolution_config.get("enabled", True):
        logger.info(f"{claw} evolution is disabled")
        return False

    result = _check_evolution_threshold(claw, evolution_config, current_activity)

    logger.info(f"{claw} evolution check: {result['reason']}")

    return result["can_evolve"]


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
