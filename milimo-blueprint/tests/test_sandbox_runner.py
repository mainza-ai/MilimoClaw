# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for sandbox_runner.py - Real Backtesting in Sandbox Isolation
"""

from typing import Any

import pytest

from orchestrator.evolution.sandbox_runner import (
    SandboxRunner,
    BacktestResult,
    SandboxConfig,
    _meets_threshold,
)


# ---------------------------------------------------------------------------

VALID_TOOL_CODE = '''
def apply(action_data: dict) -> dict:
    """Apply tool to action data."""
    result = action_data.copy()
    result["processed"] = True
    result["approval_rate"] = 0.85
    return result
'''

BLOCKED_IMPORT_CODE = '''
import requests

def apply(action_data: dict) -> dict:
    """Tool with blocked import."""
    return action_data
'''

SYNTAX_ERROR_CODE = """
def apply(action_data: dict
    return action_data
"""

# ---------------------------------------------------------------------------


class TestSandboxRunner:
    """Tests for SandboxRunner class."""

    @pytest.fixture
    def runner(self) -> SandboxRunner:
        """Create a SandboxRunner instance for testing."""
        return SandboxRunner()

    @pytest.fixture
    def historical_data(self) -> list[dict[str, Any]]:
        """Create sample historical data for testing."""
        return [
            {
                "action_id": "act_1",
                "type": "social_post",
                "metrics": {"approval_rate": 0.7},
            },
            {
                "action_id": "act_2",
                "type": "social_post",
                "metrics": {"approval_rate": 0.75},
            },
            {
                "action_id": "act_3",
                "type": "social_post",
                "metrics": {"approval_rate": 0.8},
            },
            {
                "action_id": "act_4",
                "type": "social_post",
                "metrics": {"approval_rate": 0.72},
            },
            {
                "action_id": "act_5",
                "type": "social_post",
                "metrics": {"approval_rate": 0.78},
            },
        ]

    def test_initialization(self, runner: SandboxRunner) -> None:
        """Test SandboxRunner initialization."""
        assert runner._config is not None
        assert runner._config.timeout_seconds == 30
        assert runner._config.memory_limit_mb == 256

    def test_custom_config(self) -> None:
        """Test SandboxRunner with custom config."""
        config = SandboxConfig(
            timeout_seconds=60,
            memory_limit_mb=512,
        )
        runner = SandboxRunner(config)
        assert runner._config.timeout_seconds == 60
        assert runner._config.memory_limit_mb == 512

    def test_validate_syntax_valid(self, runner: SandboxRunner) -> None:
        """Test syntax validation with valid code."""
        errors = runner._validate_syntax(VALID_TOOL_CODE)
        assert len(errors) == 0

    def test_validate_syntax_invalid(self, runner: SandboxRunner) -> None:
        """Test syntax validation with invalid code."""
        errors = runner._validate_syntax(SYNTAX_ERROR_CODE)
        assert len(errors) > 0

    def test_check_blocked_imports_clean(self, runner: SandboxRunner) -> None:
        """Test blocked import check with clean code."""
        blocked = runner._check_blocked_imports(VALID_TOOL_CODE)
        assert len(blocked) == 0

    def test_check_blocked_imports_blocked(self, runner: SandboxRunner) -> None:
        """Test blocked import check with blocked import."""
        blocked = runner._check_blocked_imports(BLOCKED_IMPORT_CODE)
        assert "requests" in blocked

    def test_backtest_successful_validation(
        self, runner: SandboxRunner, historical_data: list[dict[str, Any]]
    ) -> None:
        """Test backtest with valid tool code."""
        result = runner.backtest(
            tool_code=VALID_TOOL_CODE,
            historical_data=historical_data,
            target_metric="approval_rate",
            baseline_value=0.75,
        )

        assert result.error == "" or "Syntax" not in result.error
        assert result.runtime_ms > 0

    def test_backtest_syntax_error(
        self, runner: SandboxRunner, historical_data: list[dict[str, Any]]
    ) -> None:
        """Test backtest with syntax error in tool code."""
        result = runner.backtest(
            tool_code=SYNTAX_ERROR_CODE,
            historical_data=historical_data,
            target_metric="approval_rate",
            baseline_value=0.75,
        )

        assert result.passed is False
        assert "Syntax" in result.error

    def test_backtest_blocked_import(
        self, runner: SandboxRunner, historical_data: list[dict[str, Any]]
    ) -> None:
        """Test backtest with blocked import in tool code."""
        result = runner.backtest(
            tool_code=BLOCKED_IMPORT_CODE,
            historical_data=historical_data,
            target_metric="approval_rate",
            baseline_value=0.75,
        )

        assert result.passed is False
        assert len(result.blocked_imports) > 0
        assert "requests" in result.blocked_imports

    def test_backtest_empty_data(self, runner: SandboxRunner) -> None:
        """Test backtest with empty historical data."""
        result = runner.backtest(
            tool_code=VALID_TOOL_CODE,
            historical_data=[],
            target_metric="approval_rate",
            baseline_value=0.75,
        )

        assert result.sample_outputs == []

    def test_backtest_timeout(self) -> None:
        """Test backtest timeout enforcement."""
        import platform

        # Skip on macOS due to different subprocess timeout behavior
        if platform.system() == "Darwin":
            import pytest

            pytest.skip("Timeout test unreliable on macOS subprocess handling")

        config = SandboxConfig(timeout_seconds=1)
        runner = SandboxRunner(config)

        # Code that would take longer than 1 second
        slow_code = """
import time
def apply(action_data: dict) -> dict:
    time.sleep(10)  # This will timeout
    return action_data
"""

        result = runner.backtest(
            tool_code=slow_code,
            historical_data=[{"id": "1"}],
            target_metric="approval_rate",
            baseline_value=0.5,
        )

        # Should have timed out
        assert result.passed is False
        assert "Timeout" in result.error


class TestMeetsThreshold:
    """Tests for _meets_threshold function."""

    def test_meets_threshold_passing(self) -> None:
        """Test threshold check with passing result."""
        result = BacktestResult(improvement_pct=7.5)
        assert _meets_threshold(result, threshold_pct=5.0) is True

    def test_meets_threshold_failing(self) -> None:
        """Test threshold check with failing result."""
        result = BacktestResult(improvement_pct=3.0)
        assert _meets_threshold(result, threshold_pct=5.0) is False

    def test_meets_threshold_exact(self) -> None:
        """Test threshold check at exact threshold."""
        result = BacktestResult(improvement_pct=5.0)
        assert _meets_threshold(result, threshold_pct=5.0) is True

    def test_meets_threshold_custom(self) -> None:
        """Test threshold check with custom threshold."""
        result = BacktestResult(improvement_pct=10.0)
        assert _meets_threshold(result, threshold_pct=8.0) is True


class TestBacktestResult:
    """Tests for BacktestResult dataclass."""

    def test_default_values(self) -> None:
        """Test BacktestResult default values."""
        result = BacktestResult()
        assert result.tool_name == ""
        assert result.improvement_pct == 0.0
        assert result.baseline_value == 0.0
        assert result.tool_value == 0.0
        assert result.sample_outputs == []
        assert result.error_rate == 0.0
        assert result.runtime_ms == 0
        assert result.passed is False
        assert result.error == ""
        assert result.blocked_imports == []

    def test_custom_values(self) -> None:
        """Test BacktestResult with custom values."""
        result = BacktestResult(
            tool_name="test_tool",
            improvement_pct=15.5,
            baseline_value=0.7,
            tool_value=0.81,
            passed=True,
        )
        assert result.tool_name == "test_tool"
        assert result.improvement_pct == 15.5
        assert result.passed is True
