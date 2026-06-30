# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Cost Guard — Token usage tracking and daily limit enforcement.

Tracks inference token usage across all claws and enforces daily limits.
Integrates with MetricsCollector for token accounting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics_collector import MetricsCollector
from .milimo_paths import metrics_dir

logger = logging.getLogger("milimo.cost_guard")


@dataclass
class CostGuardConfig:
    """Configuration for Cost Guard."""
    daily_token_limit: int = 50000
    alert_threshold_percent: float = 80.0
    warning_threshold_percent: float = 60.0


@dataclass
class TokenUsage:
    """Token usage summary."""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    daily_limit: int = 50000
    remaining: int = 50000
    percent_used: float = 0.0
    alert_triggered: bool = False
    warning_triggered: bool = False
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "daily_limit": self.daily_limit,
            "remaining": self.remaining,
            "percent_used": round(self.percent_used, 1),
            "alert_triggered": self.alert_triggered,
            "warning_triggered": self.warning_triggered,
            "last_updated": self.last_updated,
        }


class CostGuard:
    """
    Cost Guard for daily token limit enforcement.

    Tracks inference token usage from all claws via MetricsCollector
    and enforces configurable daily limits with alerting.
    """

    def __init__(
        self,
        config: CostGuardConfig | None = None,
        metrics_base_dir: Path | None = None,
    ):
        self.config = config or CostGuardConfig()
        self.metrics_base_dir = metrics_base_dir or metrics_dir()
        self._collectors: dict[str, MetricsCollector] = {}
        self._initialize_collectors()

    def _initialize_collectors(self) -> None:
        """Initialize MetricsCollector for each claw role."""
        for role in ["build", "content", "ops", "analytics", "finance", "assistant"]:
            self._collectors[role] = MetricsCollector(
                claw_role=role,
                metrics_dir=self.metrics_base_dir / role,
            )

    def _collect_today_usage(self) -> dict[str, int]:
        """Collect token usage for today from all collectors using persisted metrics."""
        today = datetime.now(timezone.utc).date().isoformat()
        usage = {}

        for role, collector in self._collectors.items():
            # Use get_summary to read from persisted JSONL file
            summary = collector.get_summary(lookback_hours=24)
            counters = summary.get("counters", {})
            usage[role] = counters.get("inference_tokens", 0)

        return usage

    def get_usage(self) -> TokenUsage:
        """Get current token usage across all claws."""
        usage_by_role = self._collect_today_usage()
        total = sum(usage_by_role.values())
        remaining = max(0, self.config.daily_token_limit - total)
        percent_used = (total / self.config.daily_token_limit) * 100 if self.config.daily_token_limit > 0 else 0

        return TokenUsage(
            total_tokens=total,
            daily_limit=self.config.daily_token_limit,
            remaining=remaining,
            percent_used=percent_used,
            alert_triggered=percent_used >= self.config.alert_threshold_percent,
            warning_triggered=percent_used >= self.config.warning_threshold_percent,
        )

    def get_detailed_usage(self) -> dict[str, Any]:
        """Get detailed token usage by claw role."""
        usage_by_role = self._collect_today_usage()
        summary = self.get_usage()

        return {
            "summary": summary.to_dict(),
            "by_role": usage_by_role,
            "config": {
                "daily_token_limit": self.config.daily_token_limit,
                "alert_threshold_percent": self.config.alert_threshold_percent,
                "warning_threshold_percent": self.config.warning_threshold_percent,
            },
        }

    def check_limit(self) -> tuple[bool, str]:
        """
        Check if daily token limit has been exceeded.

        Returns:
            Tuple of (allowed, message). If allowed=False, execution should be blocked.
        """
        usage = self.get_usage()

        if usage.total_tokens >= self.config.daily_token_limit:
            return False, f"Daily token limit ({self.config.daily_token_limit}) exceeded. Used: {usage.total_tokens}"

        if usage.alert_triggered:
            logger.warning(
                "Cost guard alert: %.1f%% of daily token limit used (%d/%d)",
                usage.percent_used,
                usage.total_tokens,
                self.config.daily_token_limit,
            )
            return True, f"ALERT: {usage.percent_used:.1f}% of daily token limit used ({usage.total_tokens}/{self.config.daily_token_limit})"

        if usage.warning_triggered:
            logger.warning(
                "Cost guard warning: %.1f%% of daily token limit used (%d/%d)",
                usage.percent_used,
                usage.total_tokens,
                self.config.daily_token_limit,
            )
            return True, f"WARNING: {usage.percent_used:.1f}% of daily token limit used ({usage.total_tokens}/{self.config.daily_token_limit})"

        return True, "OK"

    def record_inference(self, claw_role: str, tokens: int) -> None:
        """Record an inference call for a specific claw."""
        if claw_role in self._collectors:
            self._collectors[claw_role].record_inference_call("chat", tokens, 0.0)


# Global instance for easy access
_global_cost_guard: CostGuard | None = None


def get_cost_guard(config: CostGuardConfig | None = None) -> CostGuard:
    """Get or create the global CostGuard instance."""
    global _global_cost_guard
    if _global_cost_guard is None:
        _global_cost_guard = CostGuard(config)
    return _global_cost_guard


def set_cost_guard(config: CostGuardConfig | None = None) -> CostGuard:
    """Set the global CostGuard instance (for testing/config changes)."""
    global _global_cost_guard
    _global_cost_guard = CostGuard(config)
    return _global_cost_guard


__all__ = [
    "CostGuard",
    "CostGuardConfig",
    "TokenUsage",
    "get_cost_guard",
    "set_cost_guard",
]
