#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Privacy Router

Inference routing with locked routes and cost guard for solo operators.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("milimo.solo_privacy")


# ---------------------------------------------------------------------------

class Route(Enum):
    """Inference route options."""
    CLOUD = "cloud"
    LOCAL = "local"
    VLLM = "vllm"


class FallbackStrategy(Enum):
    """Fallback strategy when budget is exceeded."""
    LOCAL = "local"
    VLLM = "vllm"
    CLOUD = "cloud"
    LIGHTER_PROMPT = "lighter_prompt"


class PrivacyPolicyViolationError(Exception):
    """Raised when attempting to override a locked route."""
    pass


# ---------------------------------------------------------------------------

LOCKED_ROUTES = {
    "financial_data": Route.LOCAL,
    "source_code": Route.LOCAL,
}

DEFAULT_ROUTES: dict[str, Route] = {
    "client_facing_drafts": Route.CLOUD,
    "internal_ideation": Route.LOCAL,
    "client_records": Route.LOCAL,
    "analytics_synthesis": Route.LOCAL,
    "public_docs_changelogs": Route.CLOUD,
}


# ---------------------------------------------------------------------------

@dataclass
class RoutingDecision:
    """Result of a routing decision."""
    data_type: str
    route: Route
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cost_tokens: int = 0
    budget_exceeded: bool = False


@dataclass
class CostGuard:
    """Daily cloud token budget management."""
    daily_budget: int = 50000
    alert_percent: float = 80.0
    fallback_strategy: FallbackStrategy = FallbackStrategy.LOCAL
    never_block: bool = True

    _used_today: int = 0
    _last_reset: date = field(default_factory=date.today)

    def check_budget(self) -> tuple[bool, bool]:
        """
        Check if budget allows cloud usage.

        Returns:
            Tuple of (allowed, is_alert)
        """
        self._maybe_reset()

        if self._used_today >= self.daily_budget:
            return False, False

        alert_threshold = self.daily_budget * (self.alert_percent / 100)
        is_alert = self._used_today >= alert_threshold

        return True, is_alert

    def record_usage(self, tokens: int) -> None:
        """Record token usage."""
        self._maybe_reset()
        self._used_today += tokens

    def get_remaining(self) -> int:
        """Get remaining budget."""
        self._maybe_reset()
        return max(0, self.daily_budget - self._used_today)

    def get_usage_percent(self) -> float:
        """Get usage as percentage."""
        self._maybe_reset()
        return (self._used_today / self.daily_budget) * 100

    def _maybe_reset(self) -> None:
        """Reset if new day."""
        today = date.today()
        if self._last_reset != today:
            self._used_today = 0
            self._last_reset = today
            logger.info(f"Cost guard reset for {today}")

    def apply_lighter_prompt_strategy(
        self,
        prompt: str,
        max_tokens: int,
    ) -> tuple[str, int]:
        """
        Reduce prompt complexity when daily token budget is exceeded.
        Called automatically when cost_guard triggers fallback.

        Args:
            prompt: Original prompt
            max_tokens: Original max_tokens

        Returns:
            Tuple of (trimmed_prompt, reduced_max_tokens)
        """
        reduced_max_tokens = max_tokens // 2

        TRIM_MARKERS = [
            "CODEBASE CONTEXT:",
            "COMMUNICATION HISTORY:",
            "HISTORICAL CALIBRATION DATA:",
            "SIMILAR PAST PROJECTS:",
        ]

        trimmed = prompt
        for marker in TRIM_MARKERS:
            if marker in trimmed:
                idx = trimmed.index(marker)
                next_section = trimmed.find("\n\n", idx + len(marker) + 200)
                if next_section != -1:
                    trimmed = (
                        trimmed[:idx + len(marker) + 200] +
                        "\n[context trimmed — cost guard active]\n\n" +
                        trimmed[next_section:]
                    )

        logger.info(
            f"action_type=cost_guard_fallback_active "
            f"original_tokens={max_tokens} reduced_tokens={reduced_max_tokens}"
        )

        return trimmed, reduced_max_tokens


# ---------------------------------------------------------------------------

class SoloPrivacyRouter:
    """
    Privacy router for solo founder configuration.

    Routes inference requests based on data type sensitivity.
    Enforces locked routes and manages cloud budget.
    """

    def __init__(
        self,
        config: dict[str, Any],
        log_dir: Optional[Path] = None,
    ):
        """
        Initialize the privacy router.

        Args:
            config: Validated solo-founder configuration
            log_dir: Directory for logs
        """
        self.config = config

        inference_config = config.get("inference", {})
        self.solo_mode = inference_config.get("solo_mode", False)
        self.routing_overrides = inference_config.get("routing_overrides", {})

        cost_guard_config = inference_config.get("cost_guard", {})
        self.cost_guard = CostGuard(
            daily_budget=cost_guard_config.get("daily_cloud_token_budget", 50000),
            alert_percent=cost_guard_config.get("alert_at_percent", 80.0),
            fallback_strategy=FallbackStrategy(cost_guard_config.get("fallback_on_exceed", "local")),
            never_block=cost_guard_config.get("never_block_claw_action", True),
        )

        if log_dir is None:
            log_dir = Path.home() / ".milimo" / "logs"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._routing_log: list[RoutingDecision] = []

        logger.info("SoloPrivacyRouter initialized")
        if self.solo_mode:
            logger.info("Solo mode active — cost-optimized routing enabled")

    def route(self, data_type: str, estimated_tokens: int = 0) -> RoutingDecision:
        """
        Determine the inference route for a data type.

        Args:
            data_type: Type of data being processed
            estimated_tokens: Estimated token count for cost tracking

        Returns:
            RoutingDecision with the chosen route and reason

        Raises:
            PrivacyPolicyViolationError: If attempting to override a locked route
        """
        if data_type in LOCKED_ROUTES:
            locked_route = LOCKED_ROUTES[data_type]

            if data_type in self.routing_overrides:
                override = self.routing_overrides[data_type]
                try:
                    override_route = Route(override)
                except ValueError:
                    override_route = None

                if override_route and override_route != locked_route:
                    raise PrivacyPolicyViolationError(
                        f"Cannot override locked route for '{data_type}'. "
                        f"Must be '{locked_route.value}', got '{override}'. "
                        f"Financial data and source code must always be processed locally."
                    )

            decision = RoutingDecision(
                data_type=data_type,
                route=locked_route,
                reason=f"Locked route — {data_type} must be processed locally for privacy",
            )
            self._log_decision(decision)
            return decision

        if data_type in self.routing_overrides:
            route_str = self.routing_overrides[data_type]
            try:
                desired_route = Route(route_str)
            except ValueError:
                desired_route = Route.LOCAL
                logger.warning(f"Unknown route '{route_str}' for {data_type}, defaulting to local")
        elif data_type in DEFAULT_ROUTES:
            desired_route = DEFAULT_ROUTES[data_type]
        else:
            desired_route = Route.LOCAL

        if desired_route == Route.CLOUD:
            allowed, is_alert = self.cost_guard.check_budget()

            if not allowed:
                fallback_route = self._get_fallback_route()
                decision = RoutingDecision(
                    data_type=data_type,
                    route=fallback_route,
                    reason=f"Budget exceeded — falling back to {fallback_route.value}",
                    budget_exceeded=True,
                )
                logger.warning(
                    f"Cloud budget exceeded for {data_type}. "
                    f"Falling back to {fallback_route.value}"
                )
            elif is_alert:
                self.cost_guard.record_usage(estimated_tokens)
                decision = RoutingDecision(
                    data_type=data_type,
                    route=desired_route,
                    reason=f"Cloud route (budget alert: {self.cost_guard.get_usage_percent():.1f}% used)",
                    cost_tokens=estimated_tokens,
                )
                logger.warning(
                    f"Budget alert: {self.cost_guard.get_usage_percent():.1f}% of daily budget used"
                )
            else:
                self.cost_guard.record_usage(estimated_tokens)
                decision = RoutingDecision(
                    data_type=data_type,
                    route=desired_route,
                    reason="Cloud route — client-facing quality",
                    cost_tokens=estimated_tokens,
                )
        else:
            decision = RoutingDecision(
                data_type=data_type,
                route=desired_route,
                reason=f"{desired_route.value.capitalize()} route — privacy-preserving",
            )

        self._log_decision(decision)
        return decision

    def _log_decision(self, decision: RoutingDecision) -> None:
        """Log a routing decision."""
        self._routing_log.append(decision)
        logger.info(
            f"Routing decision: {decision.data_type} -> {decision.route.value} "
            f"({decision.reason})"
        )

    def _get_fallback_route(self) -> Route:
        """
        Get the fallback route based on the fallback strategy.

        For LIGHTER_PROMPT strategy, returns Route.LOCAL but the caller
        should also apply the lighter prompt transformation.

        Returns:
            Route to use when budget is exceeded.
        """
        strategy = self.cost_guard.fallback_strategy
        if strategy == FallbackStrategy.LIGHTER_PROMPT:
            return Route.LOCAL
        elif strategy == FallbackStrategy.CLOUD:
            return Route.CLOUD
        elif strategy == FallbackStrategy.VLLM:
            return Route.VLLM
        else:
            return Route.LOCAL

    def get_routing_log(self) -> list[RoutingDecision]:
        """Get all routing decisions."""
        return self._routing_log.copy()

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status."""
        return {
            "daily_budget": self.cost_guard.daily_budget,
            "used_today": self.cost_guard._used_today,
            "remaining": self.cost_guard.get_remaining(),
            "usage_percent": self.cost_guard.get_usage_percent(),
            "alert_threshold": self.cost_guard.alert_percent,
            "fallback_strategy": self.cost_guard.fallback_strategy.value,
        }

    def is_locked_route(self, data_type: str) -> bool:
        """Check if a data type has a locked route."""
        return data_type in LOCKED_ROUTES

    def get_route(self, data_type: str) -> Route:
        """
        Get route for a data type without cost tracking.

        Args:
            data_type: Type of data

        Returns:
            Route for the data type
        """
        return self.route(data_type, 0).route

    def route_batch(self, data_types: list[str]) -> list[RoutingDecision]:
        """
        Route multiple data types.

        Args:
            data_types: List of data types

        Returns:
            List of routing decisions
        """
        return [self.route(dt) for dt in data_types]
