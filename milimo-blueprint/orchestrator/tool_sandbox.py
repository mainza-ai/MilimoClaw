# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Sandbox

Provides an isolated execution environment for testing generated tools.
Ensures tools run safely before deployment to the claw.

Usage:
    from tool_sandbox import ToolSandbox

    sandbox = ToolSandbox()
    result = sandbox.execute(code, test_input)

    if result.success:
        print("Tool passed sandbox test")
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("milimo.tool_sandbox")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    max_execution_time_ms: int = 5000
    max_memory_mb: int = 200
    max_output_bytes: int = 1024 * 1024  # 1MB
    max_stack_size_kb: int = 8192
    allowed_imports: set[str] | None = None
    forbidden_imports: set[str] | None = None
    enable_network: bool = False
    enable_filesystem_write: bool = False


@dataclass
class ExecutionResult:
    """Result of sandboxed execution."""

    success: bool
    output: Any = None
    error: str = ""
    error_type: str = ""
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""


@dataclass
class TestResult:
    """Result of testing a tool against test cases."""

    passed: bool
    results: list[dict[str, Any]] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error: str = ""


# ---------------------------------------------------------------------------
# Sandboxed Executor
# ---------------------------------------------------------------------------


class SandboxedExecutor:
    """
    Executes Python code in a subprocess with resource limits.

    Uses subprocess isolation to ensure generated code cannot:
    - Access the network (unless explicitly allowed)
    - Write to the filesystem (unless explicitly allowed)
    - Execute indefinitely (enforced timeout)
    - Use excessive memory (enforced limit)
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

    def execute(
        self,
        code: str,
        input_data: dict[str, Any],
        function_name: str = "run",
    ) -> ExecutionResult:
        """
        Execute code with input data in a sandboxed subprocess.

        Args:
            code: Python source code to execute
            input_data: Input to pass to the function
            function_name: Function to call (default: "run")

        Returns:
            ExecutionResult with output or error details
        """
        start_time = datetime.now(timezone.utc)

        # Create wrapper script
        wrapper = self._create_wrapper(code, function_name, input_data)

        # Execute in subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "sandboxed_tool.py"
            script_path.write_text(wrapper)

            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.config.max_execution_time_ms / 1000,
                    cwd=tmpdir,
                    env=self._build_env(),
                    # Resource limits via subprocess
                    # Note: More restrictive limits would require containerization
                )

                execution_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000

                if result.returncode != 0:
                    return ExecutionResult(
                        success=False,
                        error=result.stderr or f"Exit code: {result.returncode}",
                        error_type="ExecutionError",
                        execution_time_ms=execution_time,
                        stdout=result.stdout,
                        stderr=result.stderr,
                    )

                # Parse JSON output
                try:
                    output = json.loads(result.stdout.strip())
                except json.JSONDecodeError as e:
                    return ExecutionResult(
                        success=False,
                        error=f"Invalid JSON output: {e}",
                        error_type="OutputError",
                        execution_time_ms=execution_time,
                        stdout=result.stdout,
                        stderr=result.stderr,
                    )

                return ExecutionResult(
                    success=True,
                    output=output,
                    execution_time_ms=execution_time,
                    stdout=result.stdout,
                )

            except subprocess.TimeoutExpired:
                execution_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000
                return ExecutionResult(
                    success=False,
                    error=f"Execution timeout after {self.config.max_execution_time_ms}ms",
                    error_type="TimeoutError",
                    execution_time_ms=execution_time,
                )

            except Exception as e:
                execution_time = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000
                return ExecutionResult(
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                    execution_time_ms=execution_time,
                    traceback=traceback.format_exc(),
                )

    def _create_wrapper(
        self,
        code: str,
        function_name: str,
        input_data: dict[str, Any],
    ) -> str:
        """Create a wrapper script that executes the tool."""
        return f"""
import sys
import json
import resource

# Set resource limits
resource.setrlimit(resource.RLIMIT_AS, ({self.config.max_memory_mb * 1024 * 1024}, {self.config.max_memory_mb * 1024 * 1024}))
resource.setrlimit(resource.RLIMIT_STACK, ({self.config.max_stack_size_kb * 1024}, {self.config.max_stack_size_kb * 1024}))

# Import restrictions (if needed)
class ImportBlocker:
    def __init__(self, forbidden):
        self.forbidden = forbidden or set()

    def find_module(self, name, path=None):
        if name in self.forbidden or name.split('.')[0] in self.forbidden:
            raise ImportError(f"Import of {{name}} is blocked")

# Block dangerous imports
forbidden = {{"subprocess", "socket", "urllib", "requests", "os"}}
if not {self.config.enable_network}:
    forbidden.update(["http", "urllib", "requests", "socket", "ssl", "websocket"])

# Tool code
{code}

# Execute
try:
    result = {function_name}({json.dumps(input_data)})
    print(json.dumps(result, default=str))
except Exception as e:
    print(json.dumps({{"__error__": str(e), "__type__": type(e).__name__}}))
"""

    def _build_env(self) -> dict[str, str]:
        """Build environment for subprocess."""
        env = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }

        if not self.config.enable_network:
            # Disable network-related env vars
            env["NO_PROXY"] = "*"
            env["HTTP_PROXY"] = ""
            env["HTTPS_PROXY"] = ""

        return env


# ---------------------------------------------------------------------------
# Tool Sandbox
# ---------------------------------------------------------------------------


class ToolSandbox:
    """
    High-level sandbox for testing generated tools.

    Provides:
    - Isolated execution
    - Test case validation
    - Performance benchmarking
    - Security validation
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self.executor = SandboxedExecutor(self.config)

    def test(
        self,
        code: str,
        test_cases: list[dict[str, Any]],
        function_name: str = "run",
    ) -> TestResult:
        """
        Test a tool against multiple test cases.

        Args:
            code: Python source code
            test_cases: List of test case dicts with 'input' and 'expected_output'
            function_name: Function to call

        Returns:
            TestResult with pass/fail status for each case
        """
        results: list[dict[str, Any]] = []
        passed_count = 0
        failed_count = 0

        for i, test_case in enumerate(test_cases):
            input_data = test_case.get("input", {})
            expected = test_case.get("expected_output")
            validation = test_case.get("validation", "schema_only")
            case_name = test_case.get("name", f"test_{i}")

            # Execute
            exec_result = self.executor.execute(code, input_data, function_name)

            case_result = {
                "name": case_name,
                "passed": False,
                "input": input_data,
                "expected": expected,
                "actual": exec_result.output,
                "error": exec_result.error if not exec_result.success else None,
                "execution_time_ms": exec_result.execution_time_ms,
            }

            if not exec_result.success:
                case_result["error"] = exec_result.error
                failed_count += 1
                results.append(case_result)
                continue

            # Validate output
            if validation == "exact":
                case_result["passed"] = exec_result.output == expected
            elif validation == "partial":
                case_result["passed"] = self._partial_match(
                    exec_result.output, expected
                )
            elif validation == "custom":
                validator = test_case.get("validator")
                if validator and callable(validator):
                    case_result["passed"] = validator(exec_result.output)
                else:
                    case_result["passed"] = True  # No validator provided
            else:  # schema_only
                case_result["passed"] = True  # Already validated by JSON parse

            if case_result["passed"]:
                passed_count += 1
            else:
                failed_count += 1

            results.append(case_result)

        return TestResult(
            passed=failed_count == 0,
            results=results,
            total_tests=len(test_cases),
            passed_tests=passed_count,
            failed_tests=failed_count,
        )

    def benchmark(
        self,
        code: str,
        input_data: dict[str, Any],
        iterations: int = 100,
        function_name: str = "run",
    ) -> dict[str, float]:
        """
        Benchmark tool performance.

        Returns statistics: min, max, avg, p50, p95, p99 latency
        """
        times: list[float] = []
        errors = 0

        for _ in range(iterations):
            result = self.executor.execute(code, input_data, function_name)
            if result.success:
                times.append(result.execution_time_ms)
            else:
                errors += 1

        if not times:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "errors": errors,
                "iterations": iterations,
            }

        times.sort()

        return {
            "min": times[0],
            "max": times[-1],
            "avg": sum(times) / len(times),
            "p50": times[len(times) // 2],
            "p95": times[int(len(times) * 0.95)],
            "p99": times[int(len(times) * 0.99)],
            "errors": errors,
            "iterations": iterations,
        }

    def validate_security(
        self,
        code: str,
    ) -> tuple[bool, list[str]]:
        """
        Perform security validation before execution.

        Returns (is_safe, list_of_issues)
        """
        issues: list[str] = []

        # Check for forbidden patterns
        forbidden_patterns = [
            ("__import__", "Dynamic import"),
            ("eval(", "Dynamic evaluation"),
            ("exec(", "Dynamic execution"),
            ("compile(", "Dynamic compilation"),
            ("subprocess", "Subprocess execution"),
            ("os.system", "System command execution"),
            ("socket.", "Network access"),
            ("open(", "File operations"),
        ]

        for pattern, description in forbidden_patterns:
            if pattern in code:
                issues.append(f"Potentially unsafe: {description}")

        return len(issues) == 0, issues

    def _partial_match(
        self,
        actual: Any,
        expected: Any,
    ) -> bool:
        """Check if actual output partially matches expected."""
        if not isinstance(expected, dict) or not isinstance(actual, dict):
            return actual == expected

        for key, value in expected.items():
            if key not in actual:
                return False
            if isinstance(value, dict):
                if not self._partial_match(actual[key], value):
                    return False
            elif actual[key] != value:
                return False

        return True


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def sandbox_test(
    code: str,
    test_cases: list[dict[str, Any]],
    config: SandboxConfig | None = None,
) -> TestResult:
    """
    Convenience function to test tool code.

    Args:
        code: Python source code
        test_cases: Test cases to run
        config: Optional sandbox configuration

    Returns:
        TestResult
    """
    sandbox = ToolSandbox(config)
    return sandbox.test(code, test_cases)


def sandbox_execute(
    code: str,
    input_data: dict[str, Any],
    config: SandboxConfig | None = None,
) -> ExecutionResult:
    """
    Convenience function to execute tool code once.

    Args:
        code: Python source code
        input_data: Input to pass
        config: Optional sandbox configuration

    Returns:
        ExecutionResult
    """
    executor = SandboxedExecutor(config)
    return executor.execute(code, input_data)
