"""Unit tests for CostGuard."""

import pytest
from milimo_core.cost_guard import CostGuard, CostGuardConfig, TokenUsage, get_cost_guard, set_cost_guard


class TestCostGuardConfig:
    """Tests for CostGuardConfig."""

    def test_default_config(self):
        """Test default CostGuardConfig values."""
        config = CostGuardConfig()

        assert config.daily_token_limit == 50000
        assert config.alert_threshold_percent == 80.0
        assert config.warning_threshold_percent == 60.0

    def test_custom_config(self):
        """Test CostGuardConfig with custom values."""
        config = CostGuardConfig(
            daily_token_limit=100000,
            alert_threshold_percent=75.0,
            warning_threshold_percent=50.0
        )

        assert config.daily_token_limit == 100000
        assert config.alert_threshold_percent == 75.0
        assert config.warning_threshold_percent == 50.0


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_token_usage_creation(self):
        """Test TokenUsage creation with defaults."""
        usage = TokenUsage()

        assert usage.total_tokens == 0
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.daily_limit == 50000
        assert usage.remaining == 50000
        assert usage.percent_used == 0.0
        assert usage.alert_triggered is False
        assert usage.warning_triggered is False

    def test_token_usage_to_dict(self):
        """Test TokenUsage to_dict method."""
        usage = TokenUsage(
            total_tokens=25000,
            daily_limit=50000,
            remaining=25000,
            percent_used=50.0,
            alert_triggered=False,
            warning_triggered=True
        )

        data = usage.to_dict()

        assert data["total_tokens"] == 25000
        assert data["daily_limit"] == 50000
        assert data["remaining"] == 25000
        assert data["percent_used"] == 50.0
        assert data["alert_triggered"] is False
        assert data["warning_triggered"] is True


class TestCostGuard:
    """Tests for CostGuard."""

    def test_initialization(self):
        """Test CostGuard initialization with default config."""
        cg = CostGuard()

        assert cg.config.daily_token_limit == 50000
        assert cg.config.alert_threshold_percent == 80.0
        assert cg.config.warning_threshold_percent == 60.0

    def test_initialization_with_config(self):
        """Test CostGuard initialization with custom config."""
        config = CostGuardConfig(
            daily_token_limit=100000,
            alert_threshold_percent=75.0,
            warning_threshold_percent=50.0
        )
        cg = CostGuard(config=config)

        assert cg.config.daily_token_limit == 100000
        assert cg.config.alert_threshold_percent == 75.0
        assert cg.config.warning_threshold_percent == 50.0

    def test_get_usage_returns_token_usage(self, cost_guard):
        """Test get_usage returns TokenUsage."""
        usage = cost_guard.get_usage()

        assert isinstance(usage, TokenUsage)
        assert hasattr(usage, 'total_tokens')
        assert hasattr(usage, 'daily_limit')
        assert hasattr(usage, 'remaining')
        assert hasattr(usage, 'percent_used')
        assert hasattr(usage, 'alert_triggered')
        assert hasattr(usage, 'warning_triggered')

    def test_get_detailed_usage(self, cost_guard):
        """Test get_detailed_usage returns dict with summary and by_role."""
        detailed = cost_guard.get_detailed_usage()

        assert "summary" in detailed
        assert "by_role" in detailed
        assert "config" in detailed

        assert detailed["config"]["daily_token_limit"] == 50000
        assert detailed["config"]["alert_threshold_percent"] == 80.0
        assert detailed["config"]["warning_threshold_percent"] == 60.0

    def test_check_limit_returns_tuple(self, cost_guard):
        """Test check_limit returns (allowed, message) tuple."""
        allowed, message = cost_guard.check_limit()

        assert isinstance(allowed, bool)
        assert isinstance(message, str)
        assert allowed is True  # Should be OK with 0 usage

    def test_record_inference(self, cost_guard):
        """Test recording inference tokens."""
        # Should not raise
        cost_guard.record_inference("content", 100)
        cost_guard.record_inference("build", 200)

        # Verify role tracking
        detailed = cost_guard.get_detailed_usage()
        assert detailed["by_role"]["content"] == 100
        assert detailed["by_role"]["build"] == 200

    def test_check_limit_exceeded(self):
        """Test check_limit returns False when limit exceeded."""
        config = CostGuardConfig(daily_token_limit=100)
        cg = CostGuard(config=config)

        # Record enough tokens to exceed limit
        cg.record_inference("content", 150)

        allowed, message = cg.check_limit()

        assert allowed is False
        assert "exceeded" in message.lower()

    def test_check_limit_warning_threshold(self, cost_guard, caplog):
        """Test check_limit triggers warning at threshold."""
        # Use the fixture which has temp metrics dir
        # Override config for this test
        cost_guard.config.daily_token_limit = 1000
        cost_guard.config.warning_threshold_percent = 50.0

        # Record tokens to hit warning threshold (50%) but not exceed limit
        cost_guard.record_inference("content", 500)

        with caplog.at_level("WARNING"):
            allowed, message = cost_guard.check_limit()

        assert allowed is True
        assert "warning" in message.lower()
        assert any("warning" in record.message.lower() for record in caplog.records)

    def test_check_limit_alert_threshold(self, cost_guard, caplog):
        """Test check_limit triggers alert at threshold."""
        # Use the fixture which has temp metrics dir
        # Override config for this test
        cost_guard.config.daily_token_limit = 1000
        cost_guard.config.alert_threshold_percent = 80.0

        # Record tokens to hit alert threshold (80%) but not exceed limit
        cost_guard.record_inference("content", 800)

        with caplog.at_level("WARNING"):
            allowed, message = cost_guard.check_limit()

        assert allowed is True
        assert "alert" in message.lower() or "critical" in message.lower()
        assert any("alert" in record.message.lower() or "critical" in record.message.lower() for record in caplog.records)

    def test_record_inference_updates_role_breakdown(self):
        """Test record_inference updates per-role tracking."""
        config = CostGuardConfig(daily_token_limit=10000)
        cg = CostGuard(config=config)

        cg.record_inference("content", 100)
        cg.record_inference("build", 200)
        cg.record_inference("content", 50)  # Second call for same role

        detailed = cg.get_detailed_usage()

        assert detailed["by_role"]["content"] == 150
        assert detailed["by_role"]["build"] == 200
        assert detailed["summary"]["total_tokens"] == 350


class TestCostGuardSingleton:
    """Tests for CostGuard singleton functions."""

    def test_get_cost_guard_returns_instance(self):
        """Test get_cost_guard returns CostGuard instance."""
        cg = get_cost_guard()

        assert isinstance(cg, CostGuard)

    def test_get_cost_guard_singleton(self):
        """Test get_cost_guard returns same instance."""
        cg1 = get_cost_guard()
        cg2 = get_cost_guard()

        assert cg1 is cg2

    def test_set_cost_guard_creates_new(self):
        """Test set_cost_guard creates new instance."""
        # Reset singleton first
        import milimo_core.cost_guard as cg_module
        cg_module._global_cost_guard = None

        config = CostGuardConfig(daily_token_limit=75000)
        cg = set_cost_guard(config)

        assert cg.config.daily_token_limit == 75000

        cg2 = get_cost_guard()
        assert cg is cg2
        assert cg2.config.daily_token_limit == 75000
