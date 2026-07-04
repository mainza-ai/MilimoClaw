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

    def test_sandbox_runner_environment_isolation(self) -> None:
        """Verify that SandboxRunner subprocesses execute with sanitized environments and mocked paths."""
        import os
        from unittest.mock import patch, MagicMock

        # Temporarily mock os.environ to contain a simulated secret
        with patch.dict(os.environ, {"STRIPE_API_KEY": "sk_test_mocked"}):
            runner = SandboxRunner()
            with patch("subprocess.run") as mock_sub_run:
                mock_sub_run.returncode = 0
                mock_sub_run.stdout = "{}"

                mock_res = MagicMock()
                mock_res.returncode = 0
                mock_res.stdout = '{"tool_name": "test", "improvement_pct": 10.0}'
                mock_sub_run.return_value = mock_res

                runner.backtest(
                    VALID_TOOL_CODE,
                    [{"metrics": {"approval_rate": 0.7}}],
                    "approval_rate",
                    0.7,
                )

                assert mock_sub_run.called
                args, kwargs = mock_sub_run.call_args
                passed_env = kwargs.get("env", {})

                # Assert our secret is NOT in the passed environment dictionary
                assert "STRIPE_API_KEY" not in passed_env
                assert passed_env.get("HOME") is not None

    def test_sandbox_runner_containment_checking(self) -> None:
        """Verify SandboxRunner builds the command correctly when bwrap or docker are present."""
        from unittest.mock import patch, MagicMock

        runner = SandboxRunner()

        # 1. Test when bwrap is available
        with (
            patch(
                "shutil.which",
                side_effect=lambda name: "/usr/bin/bwrap" if name == "bwrap" else None,
            ),
            patch("subprocess.run") as mock_sub_run,
        ):
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = '{"tool_name": "test", "improvement_pct": 10.0}'
            mock_sub_run.return_value = mock_res

            runner.backtest(
                VALID_TOOL_CODE,
                [{"metrics": {"approval_rate": 0.7}}],
                "approval_rate",
                0.7,
            )

            assert mock_sub_run.called
            args = mock_sub_run.call_args[0][0]
            assert args[0] == "/usr/bin/bwrap"
            assert "--unshare-all" in args

        # 2. Test when bwrap is not available, but docker is available and active
        def which_side_effect(name: str) -> str | None:
            if name == "docker":
                return "/usr/bin/docker"
            return None

        with (
            patch("shutil.which", side_effect=which_side_effect),
            patch("subprocess.run") as mock_sub_run,
        ):
            # We mock the first call to subprocess.run (the docker ps daemon check) to return 0
            mock_check_res = MagicMock()
            mock_check_res.returncode = 0

            mock_run_res = MagicMock()
            mock_run_res.returncode = 0
            mock_run_res.stdout = '{"tool_name": "test", "improvement_pct": 10.0}'

            mock_sub_run.side_effect = [mock_check_res, mock_run_res]

            runner.backtest(
                VALID_TOOL_CODE,
                [{"metrics": {"approval_rate": 0.7}}],
                "approval_rate",
                0.7,
            )

            assert mock_sub_run.call_count == 2
            # Second call should be the docker run
            args = mock_sub_run.call_args_list[1][0][0]
            assert args[0] == "/usr/bin/docker"
            assert "run" in args
            assert "--net=none" in args
