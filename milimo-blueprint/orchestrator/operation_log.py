#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Operation Log

Structured logging for all claw actions. Every action taken by a claw is
recorded with its outcome, any human edits, and relevant metrics. The
operation log feeds the Evolution Cycle's Observe and Identify stages.

Storage format: JSONL at ~/.milimo/logs/<squadId>/<role>/operations.jsonl

Usage:
    from operation_log import OperationLog, ActionRecord

    log = OperationLog(squad_id="my-squad", claw_role="content")
    log.record(ActionRecord(
        action_type="social_post_draft",
        outcome="edited",
        edits={"tone": "hype → educational"},
        metrics={"engagement_rate": 0.042},
    ))
    window = log.get_window(days=7)
    patterns = log.get_action_summary(window)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("milimo.operation_log")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ActionRecord:
    """A single recorded claw action."""

    action_type: str
    outcome: str  # approved | edited | rejected | auto
    edits: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    claw_role: str = ""
    squad_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionRecord:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CrossSignal:
    """An inter-claw signal ingested from the mesh inbox."""

    sender_role: str
    signal_type: str  # summary | signal | response
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrossSignal:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ActionSummary:
    """Summary statistics for a window of actions."""

    total_actions: int
    by_type: dict[str, int]
    by_outcome: dict[str, int]
    approval_rate: float  # fraction of approved+auto vs total
    edit_rate: float  # fraction edited (not auto-approved)
    common_edits: dict[str, int]  # which fields are most frequently edited
    metric_averages: dict[str, float]


# ---------------------------------------------------------------------------
# Operation Log
# ---------------------------------------------------------------------------


class OperationLog:
    """
    Structured operation log for a single claw.

    Records actions to a JSONL file and provides windowed retrieval
    and summary statistics for the pattern detector.
    """

    def __init__(
        self,
        squad_id: str,
        claw_role: str,
        log_dir: str | None = None,
    ) -> None:
        self.squad_id = squad_id
        self.claw_role = claw_role

        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            self._log_dir = Path(home) / ".milimo" / "logs" / squad_id / claw_role

        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._operations_file = self._log_dir / "operations.jsonl"
        self._signals_file = self._log_dir / "cross_signals.jsonl"

    # ── Recording ─────────────────────────────────────────────────────

    def record(self, action: ActionRecord) -> None:
        """Append an action to the operation log."""
        action.claw_role = action.claw_role or self.claw_role
        action.squad_id = action.squad_id or self.squad_id

        with self._operations_file.open("a") as f:
            f.write(json.dumps(action.to_dict()) + "\n")

        logger.debug(
            "Recorded action: %s [%s] for %s",
            action.action_type,
            action.outcome,
            self.claw_role,
        )

    def record_cross_signal(self, signal: CrossSignal) -> None:
        """Record an inter-claw signal from the mesh inbox."""
        with self._signals_file.open("a") as f:
            f.write(json.dumps(signal.to_dict()) + "\n")

        logger.debug(
            "Recorded cross-signal from %s: %s",
            signal.sender_role,
            signal.signal_type,
        )

    # ── Retrieval ─────────────────────────────────────────────────────

    def get_window(self, days: int = 7) -> list[ActionRecord]:
        """Get all actions within the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return self._read_actions(cutoff)

    def get_all(self) -> list[ActionRecord]:
        """Get all recorded actions."""
        return self._read_actions(cutoff=None)

    def get_cross_signals(self, days: int = 14) -> list[CrossSignal]:
        """Get cross-claw signals within the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return self._read_signals(cutoff)

    def _read_actions(self, cutoff: datetime | None) -> list[ActionRecord]:
        """Read action records, optionally filtering by timestamp."""
        if not self._operations_file.exists():
            return []

        actions: list[ActionRecord] = []
        for line in self._operations_file.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                record = ActionRecord.from_dict(data)
                if cutoff is None or self._parse_ts(record.timestamp) >= cutoff:
                    actions.append(record)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Skipping malformed log entry: %s", e)
                continue
        return actions

    def _read_signals(self, cutoff: datetime) -> list[CrossSignal]:
        """Read cross-signal records within cutoff."""
        if not self._signals_file.exists():
            return []

        signals: list[CrossSignal] = []
        for line in self._signals_file.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                signal = CrossSignal.from_dict(data)
                if self._parse_ts(signal.timestamp) >= cutoff:
                    signals.append(signal)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Skipping malformed signal entry: %s", e)
                continue
        return signals

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        """Parse ISO timestamp, handling timezone-aware and naive formats."""
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    # ── Summarization ─────────────────────────────────────────────────

    def get_action_summary(self, actions: list[ActionRecord]) -> ActionSummary:
        """
        Compute summary statistics for a list of actions.

        Used by the pattern detector to identify evolution signals.
        """
        total = len(actions)
        if total == 0:
            return ActionSummary(
                total_actions=0,
                by_type={},
                by_outcome={},
                approval_rate=0.0,
                edit_rate=0.0,
                common_edits={},
                metric_averages={},
            )

        by_type: dict[str, int] = {}
        by_outcome: dict[str, int] = {}
        common_edits: dict[str, int] = {}
        metric_sums: dict[str, float] = {}
        metric_counts: dict[str, int] = {}

        for action in actions:
            by_type[action.action_type] = by_type.get(action.action_type, 0) + 1
            by_outcome[action.outcome] = by_outcome.get(action.outcome, 0) + 1

            for edit_field in action.edits:
                common_edits[edit_field] = common_edits.get(edit_field, 0) + 1

            for metric_name, metric_value in action.metrics.items():
                metric_sums[metric_name] = metric_sums.get(metric_name, 0.0) + metric_value
                metric_counts[metric_name] = metric_counts.get(metric_name, 0) + 1

        approved_count = by_outcome.get("approved", 0) + by_outcome.get("auto", 0)
        edited_count = by_outcome.get("edited", 0)

        return ActionSummary(
            total_actions=total,
            by_type=by_type,
            by_outcome=by_outcome,
            approval_rate=approved_count / total,
            edit_rate=edited_count / total,
            common_edits=common_edits,
            metric_averages={
                k: metric_sums[k] / metric_counts[k] for k in metric_sums
            },
        )

    # ── Housekeeping ──────────────────────────────────────────────────

    def count(self) -> int:
        """Count total recorded actions."""
        if not self._operations_file.exists():
            return 0
        return sum(1 for line in self._operations_file.read_text().strip().split("\n") if line)

    def clear(self) -> None:
        """Clear all log files (for testing)."""
        if self._operations_file.exists():
            self._operations_file.unlink()
        if self._signals_file.exists():
            self._signals_file.unlink()
