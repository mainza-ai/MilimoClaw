# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo_privacy.py - Inference Router
"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from orchestrator.solo_privacy import (
    SoloPrivacyRouter,
    RoutingDecision,
    CostGuard,
    Route,
    FallbackStrategy,
    PrivacyPolicyViolationError,
    LOCKED_ROUTES,
)


# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "inference": {
        "solo_mode": True,
        "routing_overrides": {
            "client_facing_drafts": "cloud",
            "internal_ideation": "local",
            "financial_data": "local",
            "source_code": "local",
            "analytics_synthesis": "local",
            "public_docs_changelogs": "cloud",
        },
        "cost_guard": {
            "daily_cloud_token_budget": 50000,
            "alert_at_percent": 80,
            "fallback_on_exceed": "local",
        },
    },
}


# ---------------------------------------------------------------------------


class TestSoloPrivacyRouter:
    """Tests for SoloPrivacyRouter class."""

    @pytest.fixture
    def router(self, tmp_path: Path) -> SoloPrivacyRouter:
        """Create a router instance for testing."""
        return SoloPrivacyRouter(VALID_CONFIG, log_dir=tmp_path)

    def test_initialization(self, router: SoloPrivacyRouter) -> None:
        """Test router initialization."""
        assert router.solo_mode is True
        assert router.cost_guard.daily_budget == 50000

    def test_route_locked_financial_data(self, router: SoloPrivacyRouter) -> None:
        """Test that financial_data always routes to local."""
        decision = router.route("financial_data")

        assert decision.route == Route.LOCAL
        assert "locked" in decision.reason.lower()

    def test_route_locked_source_code(self, router: SoloPrivacyRouter) -> None:
        """Test that source_code always routes to local."""
        decision = router.route("source_code")

        assert decision.route == Route.LOCAL
        assert "locked" in decision.reason.lower()

    def test_route_cloud_data_type(self, router: SoloPrivacyRouter) -> None:
        """Test routing to cloud for client-facing drafts."""
        decision = router.route("client_facing_drafts", estimated_tokens=1000)

        assert decision.route == Route.CLOUD
        assert decision.cost_tokens == 1000

    def test_route_local_data_type(self, router: SoloPrivacyRouter) -> None:
        """Test routing to local for internal ideation."""
        decision = router.route("internal_ideation")

        assert decision.route == Route.LOCAL
        assert (
            "privacy" in decision.reason.lower() or "local" in decision.reason.lower()
        )

    def test_route_unknown_defaults_to_local(self, router: SoloPrivacyRouter) -> None:
        """Test that unknown data types default to local."""
        decision = router.route("unknown_data_type")

        assert decision.route == Route.LOCAL

    def test_locked_route_cannot_be_overridden(self) -> None:
        """Test that locked routes raise error when override attempted."""
        invalid_config: dict[str, Any] = {
            "inference": {
                "routing_overrides": {
                    "financial_data": "cloud",
                },
                "cost_guard": {
                    "daily_cloud_token_budget": 50000,
                    "alert_at_percent": 80,
                    "fallback_on_exceed": "local",
                },
            },
        }

        router = SoloPrivacyRouter(invalid_config)

        with pytest.raises(PrivacyPolicyViolationError) as exc_info:
            router.route("financial_data")

        assert "financial_data" in str(exc_info.value)
        assert "locked" in str(exc_info.value).lower()

    def test_cost_guard_triggers_alert(self, router: SoloPrivacyRouter) -> None:
        """Test that cost guard triggers alert at threshold."""
        router.cost_guard._used_today = 40000

        decision = router.route("client_facing_drafts", estimated_tokens=1000)

        assert decision.route == Route.CLOUD
        assert "alert" in decision.reason.lower()

    def test_cost_guard_fallback_on_exceed(self, router: SoloPrivacyRouter) -> None:
        """Test that cost guard falls back when budget exceeded."""
        router.cost_guard._used_today = 50000

        decision = router.route("client_facing_drafts", estimated_tokens=1000)

        assert decision.route == Route.LOCAL
        assert decision.budget_exceeded is True
        assert "falling back" in decision.reason.lower()

    def test_cost_guard_records_usage(self, router: SoloPrivacyRouter) -> None:
        """Test that usage is recorded."""
        initial_used = router.cost_guard._used_today

        router.route("client_facing_drafts", estimated_tokens=5000)

        assert router.cost_guard._used_today == initial_used + 5000

    def test_routing_log(self, router: SoloPrivacyRouter) -> None:
        """Test that routing decisions are logged."""
        router.route("client_facing_drafts")
        router.route("financial_data")

        log = router.get_routing_log()

        assert len(log) == 2
        assert log[0].data_type == "client_facing_drafts"
        assert log[1].data_type == "financial_data"

    def test_get_budget_status(self, router: SoloPrivacyRouter) -> None:
        """Test getting budget status."""
        router.route("client_facing_drafts", estimated_tokens=10000)

        status = router.get_budget_status()

        assert status["daily_budget"] == 50000
        assert status["used_today"] == 10000
        assert status["remaining"] == 40000
        assert status["usage_percent"] == 20.0

    def test_is_locked_route(self, router: SoloPrivacyRouter) -> None:
        """Test checking if route is locked."""
        assert router.is_locked_route("financial_data") is True
        assert router.is_locked_route("source_code") is True
        assert router.is_locked_route("client_facing_drafts") is False

    def test_get_route(self, router: SoloPrivacyRouter) -> None:
        """Test getting route without cost tracking."""
        route = router.get_route("financial_data")

        assert route == Route.LOCAL

    def test_route_batch(self, router: SoloPrivacyRouter) -> None:
        """Test routing multiple data types."""
        decisions = router.route_batch(
            [
                "financial_data",
                "client_facing_drafts",
                "internal_ideation",
            ]
        )

        assert len(decisions) == 3
        assert decisions[0].route == Route.LOCAL
        assert decisions[1].route == Route.CLOUD

    def test_multiple_cloud_requests(self, router: SoloPrivacyRouter) -> None:
        """Test multiple cloud requests accumulating usage."""
        router.route("client_facing_drafts", estimated_tokens=20000)
        router.route("client_facing_drafts", estimated_tokens=20000)

        status = router.get_budget_status()
        assert status["used_today"] == 40000


class TestCostGuard:
    """Tests for CostGuard class."""

    def test_initialization(self) -> None:
        """Test cost guard initialization."""
        guard = CostGuard(
            daily_budget=100000,
            alert_percent=75.0,
            fallback_strategy=FallbackStrategy.LOCAL,
        )

        assert guard.daily_budget == 100000
        assert guard.alert_percent == 75.0
        assert guard.fallback_strategy == FallbackStrategy.LOCAL

    def test_check_budget_allowed(self) -> None:
        """Test budget check when under limit."""
        guard = CostGuard(daily_budget=1000)
        guard._used_today = 500

        allowed, is_alert = guard.check_budget()

        assert allowed is True
        assert is_alert is False

    def test_check_budget_alert(self) -> None:
        """Test budget alert threshold."""
        guard = CostGuard(daily_budget=1000, alert_percent=80)
        guard._used_today = 850

        allowed, is_alert = guard.check_budget()

        assert allowed is True
        assert is_alert is True

    def test_check_budget_exceeded(self) -> None:
        """Test budget exceeded."""
        guard = CostGuard(daily_budget=1000)
        guard._used_today = 1000

        allowed, is_alert = guard.check_budget()

        assert allowed is False

    def test_record_usage(self) -> None:
        """Test recording usage."""
        guard = CostGuard(daily_budget=1000)
        guard.record_usage(100)

        assert guard._used_today == 100

    def test_get_remaining(self) -> None:
        """Test getting remaining budget."""
        guard = CostGuard(daily_budget=1000)
        guard._used_today = 300

        assert guard.get_remaining() == 700

    def test_get_usage_percent(self) -> None:
        """Test getting usage percentage."""
        guard = CostGuard(daily_budget=1000)
        guard._used_today = 250

        assert guard.get_usage_percent() == 25.0

    def test_reset_on_new_day(self) -> None:
        """Test that budget resets on new day."""
        guard = CostGuard(daily_budget=1000)
        guard._used_today = 500
        guard._last_reset = date(2020, 1, 1)

        guard.check_budget()

        assert guard._used_today == 0
        assert guard._last_reset == date.today()


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_decision_has_timestamp(self) -> None:
        """Test that decision has a timestamp."""
        decision = RoutingDecision(
            data_type="test",
            route=Route.LOCAL,
            reason="test reason",
        )

        assert decision.timestamp is not None

    def test_decision_defaults(self) -> None:
        """Test decision default values."""
        decision = RoutingDecision(
            data_type="test",
            route=Route.CLOUD,
            reason="test",
        )

        assert decision.cost_tokens == 0
        assert decision.budget_exceeded is False


class TestRoute:
    """Tests for Route enum."""

    def test_route_values(self) -> None:
        """Test route enum values."""
        assert Route.CLOUD.value == "cloud"
        assert Route.LOCAL.value == "local"
        assert Route.VLLM.value == "vllm"


class TestLockedRoutes:
    """Tests for locked routes configuration."""

    def test_financial_data_locked(self) -> None:
        """Test that financial_data is locked."""
        assert "financial_data" in LOCKED_ROUTES
        assert LOCKED_ROUTES["financial_data"] == Route.LOCAL

    def test_source_code_locked(self) -> None:
        """Test that source_code is locked."""
        assert "source_code" in LOCKED_ROUTES
        assert LOCKED_ROUTES["source_code"] == Route.LOCAL

    def test_locked_routes_are_local(self) -> None:
        """Test that all locked routes route to local."""
        for data_type, route in LOCKED_ROUTES.items():
            assert route == Route.LOCAL
