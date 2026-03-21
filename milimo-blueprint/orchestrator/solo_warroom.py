#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo War Room

Single-operator action queue with prioritized processing.
All five claw queues merged into one unified view.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, time as time_type
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import uuid

logger = logging.getLogger("milimo.solo_warroom")


# ---------------------------------------------------------------------------

class ActionPriority(Enum):
    """Action priority levels."""
    HOLD = 1
    REVIEW = 2
    AUTO = 3


class ActionStatus(Enum):
    """Action status."""
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    AUTO_EXECUTED = "auto_executed"


# ---------------------------------------------------------------------------

@dataclass
class WarRoomAction:
    """An action pending operator review."""
    id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    claw: str = ""
    action_type: str = ""
    priority: ActionPriority = ActionPriority.REVIEW
    status: ActionStatus = ActionStatus.PENDING
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    operator_decision: Optional[str] = None


@dataclass
class DigestSchedule:
    """Schedule for morning/evening digests."""
    morning_brief: time_type = time_type(7, 0)
    evening_wrap: time_type = time_type(20, 0)


@dataclass
class RevenueSummary:
    """Revenue summary for War Room widget."""
    week_revenue: float = 0.0
    week_over_week_pct: float = 0.0
    invoices_paid: int = 0
    invoices_pending: int = 0
    last_updated: str = ""


# ---------------------------------------------------------------------------

class SoloWarRoom:
    """
    Single-operator War Room.

    Manages a prioritized action queue for all five claws.
    """

    def __init__(
        self,
        config: dict[str, Any],
        log_dir: Optional[Path] = None,
    ):
        """
        Initialize Solo War Room.

        Args:
            config: Validated solo-founder configuration
            log_dir: Directory for logs (defaults to ~/.milimo/logs/)
        """
        self.config = config
        self.operator = config.get("war_room", {}).get("operator", "operator")
        self.mode = config.get("war_room", {}).get("mode", "solo")

        self._queue: list[WarRoomAction] = []
        self._processed: list[WarRoomAction] = []
        self._auto_executed: list[WarRoomAction] = []

        self.approval_modes = config.get("operator_policy", {}).get("approval_modes", {})

        if log_dir is None:
            log_dir = Path.home() / ".milimo" / "logs"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / "warroom.log"
        self._setup_logger()

        digest_config = config.get("war_room", {}).get("digest_schedule", {})
        self.digest_schedule = DigestSchedule(
            morning_brief=self._parse_time(digest_config.get("morning_brief", "07:00")),
            evening_wrap=self._parse_time(digest_config.get("evening_wrap", "20:00")),
        )

        logger.info(f"War Room initialized for operator: {self.operator}")

    def _parse_time(self, time_str: str) -> time_type:
        """Parse time string (HH:MM) to time object."""
        parts = time_str.split(":")
        return time_type(int(parts[0]), int(parts[1]))

    def _setup_logger(self) -> None:
        """Setup file handler for War Room logs."""
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(file_handler)

    def _get_action_priority(self, claw: str, action_type: str) -> ActionPriority:
        """
        Determine action priority based on operator policy.

        Args:
            claw: Claw name
            action_type: Type of action

        Returns:
            ActionPriority for the action
        """
        claw_modes = self.approval_modes.get(claw, {})
        mode = claw_modes.get(action_type, "REVIEW")

        priority_map = {
            "HOLD": ActionPriority.HOLD,
            "REVIEW": ActionPriority.REVIEW,
            "AUTO": ActionPriority.AUTO,
        }

        return priority_map.get(mode, ActionPriority.REVIEW)

    def queue_action(
        self, claw: str, action_type: str, payload: dict[str, Any],
    ) -> WarRoomAction:
        """
        Add an action to the queue.

        Args:
            claw: Claw submitting the action
            action_type: Type of action
            payload: Action data

        Returns:
            The queued action
        """
        priority = self._get_action_priority(claw, action_type)

        action = WarRoomAction(
            claw=claw,
            action_type=action_type,
            priority=priority,
            payload=payload,
        )

        self._queue.append(action)
        self._sort_queue()

        logger.info(
            f"Queued action: {action.id} from {claw} "
            f"type={action_type} priority={priority.name}"
        )

        self._emit_action_event(action)

        if priority == ActionPriority.AUTO:
            self.auto_execute(action.id)

        return action

    def _sort_queue(self) -> None:
        """Sort queue by priority (HOLD first, then REVIEW, then AUTO)."""
        self._queue.sort(key=lambda a: a.priority.value)

    def get_pending(self, priority_filter: Optional[ActionPriority] = None) -> list[WarRoomAction]:
        """
        Get pending actions.

        Args:
            priority_filter: Optional filter by priority

        Returns:
            List of pending actions
        """
        pending = [a for a in self._queue if a.status == ActionStatus.PENDING]

        if priority_filter:
            pending = [a for a in pending if a.priority == priority_filter]

        return pending

    def approve(self, action_id: str) -> Optional[WarRoomAction]:
        """
        Approve an action.

        Args:
            action_id: ID of the action to approve

        Returns:
            The approved action, or None if not found
        """
        action = self._find_action(action_id)
        if action is None:
            logger.warning(f"Action not found: {action_id}")
            return None

        action.status = ActionStatus.APPROVED
        action.decided_at = datetime.now(timezone.utc)
        action.operator_decision = "approved"

        self._queue.remove(action)
        self._processed.append(action)

        logger.info(
            f"Action approved: {action_id} by {self.operator} "
            f"claw={action.claw} type={action.action_type}"
        )

        return action

    def block(self, action_id: str, reason: str = "") -> Optional[WarRoomAction]:
        """
        Block (veto) an action.

        Args:
            action_id: ID of the action to block
            reason: Optional reason for blocking

        Returns:
            The blocked action, or None if not found
        """
        action = self._find_action(action_id)
        if action is None:
            logger.warning(f"Action not found: {action_id}")
            return None

        action.status = ActionStatus.BLOCKED
        action.decided_at = datetime.now(timezone.utc)
        action.operator_decision = f"blocked: {reason}" if reason else "blocked"

        self._queue.remove(action)
        self._processed.append(action)

        logger.info(
            f"Action blocked: {action_id} by {self.operator} "
            f"claw={action.claw} type={action.action_type} reason={reason}"
        )

        return action

    def auto_execute(self, action_id: str) -> Optional[WarRoomAction]:
        """
        Auto-execute an action (for AUTO priority).

        Args:
            action_id: ID of the action to execute

        Returns:
            The executed action, or None if not found
        """
        action = self._find_action(action_id)
        if action is None:
            logger.warning(f"Action not found: {action_id}")
            return None

        action.status = ActionStatus.AUTO_EXECUTED
        action.decided_at = datetime.now(timezone.utc)
        action.operator_decision = "auto_executed"

        self._queue.remove(action)
        self._auto_executed.append(action)
        self._processed.append(action)

        logger.info(
            f"Action auto-executed: {action_id} "
            f"claw={action.claw} type={action.action_type}"
        )

        return action

    def _find_action(self, action_id: str) -> Optional[WarRoomAction]:
        """Find an action by ID."""
        for action in self._queue:
            if action.id == action_id:
                return action
        return None

    def get_stats(self) -> dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Statistics about the queue
        """
        pending = self.get_pending()
        return {
            "total_pending": len(pending),
            "hold_count": len([a for a in pending if a.priority == ActionPriority.HOLD]),
            "review_count": len([a for a in pending if a.priority == ActionPriority.REVIEW]),
            "auto_count": len([a for a in pending if a.priority == ActionPriority.AUTO]),
            "processed_today": len(self._processed),
            "auto_executed_today": len(self._auto_executed),
        }

    def print_morning_brief(self) -> None:
        """Print the morning brief."""
        stats = self.get_stats()
        pending = self.get_pending()

        print("\n" + "=" * 60)
        print("☀️  MORNING BRIEF — " + datetime.now().strftime("%Y-%m-%d"))
        print("=" * 60)
        print()

        print("📊 Queue Status:")
        print(f"   Total pending: {stats['total_pending']}")
        print(f"   🔴 HOLD (requires immediate attention): {stats['hold_count']}")
        print(f"   🟡 REVIEW (needs your decision): {stats['review_count']}")
        print(f"   🟢 AUTO (executed automatically): {stats['auto_count']}")
        print()

        if stats['auto_executed_today'] > 0:
            print(f"✅ Auto-executed overnight: {stats['auto_executed_today']} actions")
            print()

        if pending:
            print("📋 Pending Actions (priority order):")
            for action in pending[:10]:
                emoji = {"HOLD": "🔴", "REVIEW": "🟡", "AUTO": "🟢"}
                print(f"   {emoji.get(action.priority.name, '⚪')} [{action.id}] {action.claw}: {action.action_type}")
            print()

        print("=" * 60 + "\n")

        logger.info("Morning brief printed")

    def print_evening_wrap(self) -> None:
        """Print the evening wrap."""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("🌙  EVENING WRAP — " + datetime.now().strftime("%Y-%m-%d"))
        print("=" * 60)
        print()

        print("📊 Today's Summary:")
        print(f"   Total processed: {stats['processed_today']}")
        print(f"   Auto-executed: {stats['auto_executed_today']}")
        print(f"   Remaining pending: {stats['total_pending']}")
        print()

        if stats['total_pending'] > 0:
            print("⚠️  Actions still pending:")
            pending = self.get_pending()
            for action in pending[:5]:
                print(f"   • [{action.priority.name}] {action.claw}: {action.action_type}")
            print()

        print("=" * 60 + "\n")

        logger.info("Evening wrap printed")

    def export_log(self, output_path: Path) -> None:
        """
        Export the action log to a file.

        Args:
            output_path: Path to export the log
        """
        log_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "operator": self.operator,
            "processed": [
                {
                    "id": a.id,
                    "claw": a.claw,
                    "action_type": a.action_type,
                    "priority": a.priority.name,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat(),
                    "decided_at": a.decided_at.isoformat() if a.decided_at else None,
                    "operator_decision": a.operator_decision,
                }
                for a in self._processed
            ],
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

        logger.info(f"Log exported to {output_path}")

    def get_revenue_summary(self, sandbox_dir: Optional[Path] = None) -> RevenueSummary:
        """
        Get revenue summary for the War Room widget.

        Reads from /sandbox/finance/revenue/weekly_summary.json or
        falls back to ~/.milimo/finance/weekly_summary.json

        Args:
            sandbox_dir: Optional override for sandbox directory

        Returns:
            RevenueSummary with week revenue, WoW %, invoice counts
        """
        if sandbox_dir is None:
            sandbox_dir = Path.home() / ".milimo"

        summary_file = sandbox_dir / "finance" / "revenue" / "weekly_summary.json"

        if not summary_file.exists():
            logger.debug("Revenue summary file not found at %s", summary_file)
            return RevenueSummary(
                week_revenue=0.0,
                week_over_week_pct=0.0,
                invoices_paid=0,
                invoices_pending=0,
                last_updated="",
            )

        try:
            with summary_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            current_week = data.get("current_week", {})
            previous_week = data.get("previous_week", {})

            week_revenue = float(current_week.get("total_revenue", 0.0))
            previous_revenue = float(previous_week.get("total_revenue", 0.0))

            if previous_revenue > 0:
                week_over_week_pct = ((week_revenue - previous_revenue) / previous_revenue) * 100
            else:
                week_over_week_pct = 0.0

            return RevenueSummary(
                week_revenue=week_revenue,
                week_over_week_pct=round(week_over_week_pct, 2),
                invoices_paid=int(current_week.get("invoices_paid", 0)),
                invoices_pending=int(data.get("pending_invoices", 0)),
                last_updated=data.get("last_updated", ""),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse revenue summary: %s", e)
            return RevenueSummary(
                week_revenue=0.0,
                week_over_week_pct=0.0,
                invoices_paid=0,
                invoices_pending=0,
                last_updated="",
            )

    def _emit_action_event(self, action: WarRoomAction) -> None:
        """
        Emit WebSocket event for new action.

        Writes event to ~/.milimo/events/ for the realtime bridge to pick up.

        Args:
            action: The action that was queued
        """
        try:
            events_dir = self.log_dir.parent / "events"
            events_dir.mkdir(parents=True, exist_ok=True)

            event = {
                "type": "action_queued",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "action_id": action.id,
                    "claw": action.claw,
                    "action_type": action.action_type,
                    "priority": action.priority.name,
                    "message_type": action.action_type,
                    "payload": action.payload,
                },
            }

            event_file = events_dir / f"action_{action.id}.json"
            with event_file.open("w", encoding="utf-8") as f:
                json.dump(event, f)

        except Exception as e:
            logger.warning("Failed to emit action event: %s", e)
