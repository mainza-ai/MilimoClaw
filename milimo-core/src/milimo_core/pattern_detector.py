# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Pattern Detector

Analyzes the operation log to surface evolution signals — recurring
patterns that suggest a new tool should be built. The strongest pattern
becomes the input to the Tool Proposal stage.

Pattern types:
  - classifier:         categorize inputs/outputs
  - optimizer:          improve timing, format, routing
  - predictor:          forecast outcomes
  - generator_variant:  alternative output generation (A/B)
  - anomaly_detector:   surface unexpected deviations

Usage:
    from pattern_detector import PatternDetector
    from operation_log import OperationLog

    log = OperationLog(squad_id="my-squad", claw_role="content")
    detector = PatternDetector(claw_role="content")
    window = log.get_window(days=7)
    summary = log.get_action_summary(window)
    signals = log.get_cross_signals(days=14)
    patterns = detector.detect(summary, window, signals)
    best = detector.rank(patterns)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .operation_log import ActionRecord, ActionSummary, CrossSignal

logger = logging.getLogger("milimo.pattern_detector")

# ── Thresholds ────────────────────────────────────────────────────────

# If more than this fraction of actions are edited for the same field,
# it's a strong pattern.
EDIT_FREQUENCY_THRESHOLD = 0.25

# If approval rate for a specific action type is below this, flags it.
LOW_APPROVAL_THRESHOLD = 0.7

# If a metric's coefficient of variation exceeds this, it's drifting.
METRIC_DRIFT_THRESHOLD = 0.3

# Minimum actions of a given type to consider it statistically relevant.
MIN_ACTIONS_FOR_PATTERN = 5


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EvolutionPattern:
    """A detected pattern that may warrant a new evolved tool."""

    pattern_type: (
        str  # classifier | optimizer | predictor | generator_variant | anomaly_detector
    )
    trigger_description: str  # plain-language description of the observation
    metric_target: str  # which metric this tool should improve
    data_sources: list[str] = field(default_factory=list)  # log fields / signals used
    confidence: float = 0.0  # 0.0–1.0
    action_type: str = ""  # the action type this pattern relates to
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pattern Detector
# ---------------------------------------------------------------------------


class PatternDetector:
    """
    Analyzes operation log summaries and cross-claw signals to
    identify patterns that justify building a new tool.
    """

    def __init__(
        self,
        claw_role: str,
        min_confidence: float = 0.6,
        max_patterns: int = 5,
    ) -> None:
        self.claw_role = claw_role
        self.min_confidence = min_confidence
        self.max_patterns = max_patterns

    def detect(
        self,
        summary: ActionSummary,
        actions: list[ActionRecord],
        cross_signals: list[CrossSignal] | None = None,
    ) -> list[EvolutionPattern]:
        """
        Run all detection heuristics and return discovered patterns.

        Patterns below `min_confidence` are filtered out.
        """
        if summary.total_actions == 0:
            return []

        patterns: list[EvolutionPattern] = []

        # 1. Recurring human edits → classifier or optimizer
        patterns.extend(self._detect_edit_patterns(summary, actions))

        # 2. Low approval rate by action type → predictor or classifier
        patterns.extend(self._detect_approval_patterns(summary, actions))

        # 3. Timing patterns → optimizer
        patterns.extend(self._detect_timing_patterns(actions))

        # 4. Metric drift → anomaly_detector
        patterns.extend(self._detect_metric_drift(actions))

        # 5. Cross-claw signals → various (compound tools)
        if cross_signals:
            patterns.extend(self._detect_cross_signal_patterns(cross_signals, summary))

        # Filter by confidence threshold
        filtered = [p for p in patterns if p.confidence >= self.min_confidence]

        logger.info(
            "Detected %d patterns (%d above threshold) for %s",
            len(patterns),
            len(filtered),
            self.claw_role,
        )

        return filtered

    def rank(self, patterns: list[EvolutionPattern]) -> EvolutionPattern | None:
        """
        Rank patterns by confidence and return the strongest one.

        Returns None if no patterns qualify.
        """
        if not patterns:
            return None
        ranked = sorted(patterns, key=lambda p: p.confidence, reverse=True)
        return ranked[0]

    # ── Detection Heuristics ──────────────────────────────────────────

    def _detect_edit_patterns(
        self, summary: ActionSummary, actions: list[ActionRecord]
    ) -> list[EvolutionPattern]:
        """
        Detect fields that are consistently edited by humans.

        If the squad keeps editing the same field (e.g., "tone"), it means
        the claw isn't getting it right — a classifier or optimizer could
        learn the correction pattern.
        """
        patterns: list[EvolutionPattern] = []

        edited_actions = [a for a in actions if a.outcome == "edited"]
        if not edited_actions:
            return patterns

        for edit_field, edit_count in summary.common_edits.items():
            frequency = edit_count / max(summary.total_actions, 1)
            if (
                frequency >= EDIT_FREQUENCY_THRESHOLD
                and edit_count >= MIN_ACTIONS_FOR_PATTERN
            ):
                # Determine the specific edits for this field
                edit_values: dict[str, int] = {}
                for action in edited_actions:
                    if edit_field in action.edits:
                        val = action.edits[edit_field]
                        edit_values[val] = edit_values.get(val, 0) + 1

                confidence = min(frequency * 1.5, 0.95)

                patterns.append(
                    EvolutionPattern(
                        pattern_type="classifier",
                        trigger_description=(
                            f"{edit_count} of {summary.total_actions} actions had "
                            f"'{edit_field}' edited by the squad over the past week "
                            f"({frequency:.0%} edit rate for this field)"
                        ),
                        metric_target="approval_rate",
                        data_sources=[f"operation_log.edits.{edit_field}"],
                        confidence=confidence,
                        action_type=self._most_common_type_for_edit(
                            edited_actions, edit_field
                        ),
                        details={
                            "edit_field": edit_field,
                            "edit_frequency": frequency,
                            "common_corrections": dict(
                                sorted(
                                    edit_values.items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                )[:5]
                            ),
                        },
                    )
                )

        return patterns

    def _detect_approval_patterns(
        self, summary: ActionSummary, actions: list[ActionRecord]
    ) -> list[EvolutionPattern]:
        """
        Detect action types with unusually low approval rates.

        A low approval rate means the claw's output for this action type
        needs improvement — a predictor that estimates approval likelihood
        before surfacing could reduce noise.
        """
        patterns: list[EvolutionPattern] = []

        # Compute per-action-type approval rate
        type_outcomes: dict[str, dict[str, int]] = {}
        for action in actions:
            if action.action_type not in type_outcomes:
                type_outcomes[action.action_type] = {}
            outcomes = type_outcomes[action.action_type]
            outcomes[action.outcome] = outcomes.get(action.outcome, 0) + 1

        for action_type, outcomes in type_outcomes.items():
            total = sum(outcomes.values())
            if total < MIN_ACTIONS_FOR_PATTERN:
                continue
            approved = outcomes.get("approved", 0) + outcomes.get("auto", 0)
            rate = approved / total

            if rate < LOW_APPROVAL_THRESHOLD:
                rejected = outcomes.get("rejected", 0)
                confidence = min((1.0 - rate) * 1.2, 0.95)

                patterns.append(
                    EvolutionPattern(
                        pattern_type="predictor",
                        trigger_description=(
                            f"'{action_type}' actions have a {rate:.0%} approval rate "
                            f"({rejected} rejected out of {total} total) — "
                            f"a predictor could filter low-quality outputs before review"
                        ),
                        metric_target="approval_rate",
                        data_sources=[f"operation_log.action_type.{action_type}"],
                        confidence=confidence,
                        action_type=action_type,
                        details={
                            "action_type": action_type,
                            "approval_rate": rate,
                            "outcomes": outcomes,
                        },
                    )
                )

        return patterns

    def _detect_timing_patterns(
        self, actions: list[ActionRecord]
    ) -> list[EvolutionPattern]:
        """
        Detect temporal patterns in action outcomes.

        If outcomes vary by time of day or day of week, a timing optimizer
        could schedule actions for peak performance.
        """
        patterns: list[EvolutionPattern] = []

        # Group actions by hour and check outcome variance
        hourly_outcomes: dict[int, list[str]] = {}
        for action in actions:
            try:
                dt = OperationLog_parse_ts(action.timestamp)
                hour = dt.hour
                if hour not in hourly_outcomes:
                    hourly_outcomes[hour] = []
                hourly_outcomes[hour].append(action.outcome)
            except (ValueError, AttributeError):
                continue

        if len(hourly_outcomes) < 4:
            return patterns

        # Find hours with significantly better approval rates
        hourly_rates: dict[int, float] = {}
        for hour, outcomes in hourly_outcomes.items():
            if len(outcomes) >= 3:
                approved = sum(1 for o in outcomes if o in ("approved", "auto"))
                hourly_rates[hour] = approved / len(outcomes)

        if hourly_rates:
            best_hour = max(hourly_rates, key=lambda k: hourly_rates[k])
            worst_hour = min(hourly_rates, key=lambda k: hourly_rates[k])
            spread = hourly_rates[best_hour] - hourly_rates[worst_hour]

            if spread > 0.2:
                patterns.append(
                    EvolutionPattern(
                        pattern_type="optimizer",
                        trigger_description=(
                            f"Actions at hour {best_hour}:00 have {hourly_rates[best_hour]:.0%} "
                            f"approval vs {hourly_rates[worst_hour]:.0%} at hour {worst_hour}:00 "
                            f"— a timing optimizer could schedule for peak windows"
                        ),
                        metric_target="approval_rate",
                        data_sources=["operation_log.timestamp"],
                        confidence=min(spread * 1.5, 0.9),
                        details={
                            "best_hour": best_hour,
                            "worst_hour": worst_hour,
                            "spread": spread,
                            "hourly_rates": hourly_rates,
                        },
                    )
                )

        return patterns

    def _detect_metric_drift(
        self, actions: list[ActionRecord]
    ) -> list[EvolutionPattern]:
        """
        Detect metrics that are drifting from baseline.

        If a metric's variance is high across the window, an anomaly
        detector could surface it early.
        """
        patterns: list[EvolutionPattern] = []

        # Collect metric values across all actions
        metric_values: dict[str, list[float]] = {}
        for action in actions:
            for name, value in action.metrics.items():
                if name not in metric_values:
                    metric_values[name] = []
                metric_values[name].append(value)

        for metric_name, values in metric_values.items():
            if len(values) < MIN_ACTIONS_FOR_PATTERN:
                continue

            mean = sum(values) / len(values)
            if mean == 0:
                continue
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = variance**0.5
            cv = std_dev / abs(mean)  # coefficient of variation

            if cv > METRIC_DRIFT_THRESHOLD:
                # Check if there's a trend (last third vs first third)
                third = len(values) // 3
                first_avg = sum(values[:third]) / max(third, 1)
                last_avg = sum(values[-third:]) / max(third, 1)
                direction = "increasing" if last_avg > first_avg else "decreasing"

                patterns.append(
                    EvolutionPattern(
                        pattern_type="anomaly_detector",
                        trigger_description=(
                            f"Metric '{metric_name}' shows high variance "
                            f"(CV={cv:.2f}, trend: {direction}) — "
                            f"an anomaly detector could alert on unusual values"
                        ),
                        metric_target=metric_name,
                        data_sources=[f"operation_log.metrics.{metric_name}"],
                        confidence=min(cv * 0.8, 0.9),
                        details={
                            "metric_name": metric_name,
                            "mean": mean,
                            "std_dev": std_dev,
                            "cv": cv,
                            "direction": direction,
                        },
                    )
                )

        return patterns

    def _detect_cross_signal_patterns(
        self, signals: list[CrossSignal], summary: ActionSummary
    ) -> list[EvolutionPattern]:
        """
        Detect patterns from cross-claw signal data.

        Cross-claw signals enable compound tools — tools that couldn't be
        built from a single claw's data alone.
        """
        patterns: list[EvolutionPattern] = []

        # Group signals by sender
        by_sender: dict[str, list[CrossSignal]] = {}
        for signal in signals:
            if signal.sender_role not in by_sender:
                by_sender[signal.sender_role] = []
            by_sender[signal.sender_role].append(signal)

        # Heuristic: if we're receiving regular signals from another claw,
        # there's enough data to build a cross-signal tool
        for sender, sender_signals in by_sender.items():
            if len(sender_signals) >= 3:
                # Check for data richness in the signals
                data_fields: set[str] = set()
                for s in sender_signals:
                    data_fields.update(s.data.keys())

                if len(data_fields) >= 2:
                    confidence = min(len(sender_signals) / 10.0, 0.85)

                    patterns.append(
                        EvolutionPattern(
                            pattern_type="predictor",
                            trigger_description=(
                                f"Received {len(sender_signals)} signals from {sender} claw "
                                f"over the past 2 weeks with data fields: "
                                f"{', '.join(sorted(data_fields)[:5])} — "
                                f"sufficient for a cross-claw predictor"
                            ),
                            metric_target="cross_signal_utilization",
                            data_sources=[
                                f"cross_signal.{sender}.{f}"
                                for f in sorted(data_fields)[:5]
                            ],
                            confidence=confidence,
                            details={
                                "sender_role": sender,
                                "signal_count": len(sender_signals),
                                "data_fields": sorted(data_fields),
                            },
                        )
                    )

        return patterns

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _most_common_type_for_edit(
        edited_actions: list[ActionRecord], edit_field: str
    ) -> str:
        """Find the action type most associated with a given edit field."""
        type_counts: dict[str, int] = {}
        for action in edited_actions:
            if edit_field in action.edits:
                type_counts[action.action_type] = (
                    type_counts.get(action.action_type, 0) + 1
                )
        if not type_counts:
            return ""
        return max(type_counts, key=lambda k: type_counts[k])


# ---------------------------------------------------------------------------
# Helper — import-safe timestamp parsing
# ---------------------------------------------------------------------------


def OperationLog_parse_ts(ts: str):
    """Parse ISO timestamp (mirrors OperationLog._parse_ts)."""
    from datetime import datetime, timezone

    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
