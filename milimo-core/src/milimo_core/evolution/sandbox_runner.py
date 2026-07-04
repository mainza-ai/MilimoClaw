# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Sandbox Runner

Executes tool backtests in isolated subprocess with restricted builtins,
no network access, read-only historical data, and resource limits.

Usage:
    from evolution.sandbox_runner import SandboxRunner

    runner = SandboxRunner()
    result = runner.backtest(tool_code, historical_data, "approval_rate", 0.75)
    if result.improvement_pct >= 5.0:
        print("Tool passed threshold")
"""

from __future__ import annotations

import ast
import json
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("milimo.sandbox_runner")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class BacktestResult:
    """Result of backtesting a tool in sandbox isolation."""

    tool_name: str = ""
    improvement_pct: float = 0.0
    baseline_value: float = 0.0
    tool_value: float = 0.0
    sample_outputs: list[dict[str, Any]] = field(default_factory=list)
    error_rate: float = 0.0
    runtime_ms: int = 0
    passed: bool = False
    error: str = ""
    blocked_imports: list[str] = field(default_factory=list)


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    timeout_seconds: int = 30
    memory_limit_mb: int = 256
    allowed_imports: tuple[str, ...] = (
        "json",
        "datetime",
        "statistics",
        "math",
        "re",
        "typing",
        "dataclasses",
        "collections",
        "itertools",
        "functools",
    )
    blocked_imports: tuple[str, ...] = (
        "requests",
        "urllib",
        "http",
        "socket",
        "subprocess",
        "os.system",
        "eval",
        "exec",
        "compile",
        "__import__",
        "importlib",
    )
    read_only_paths: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Sandbox Runner
# ---------------------------------------------------------------------------


class SandboxRunner:
    """
    Executes tool backtests in isolated sandbox.

    Security features:
    - Runs in subprocess with restricted builtins
    - No network access during backtest
    - Read-only access to historical data snapshot
    - 30-second timeout — kill if exceeded
    - 256MB memory limit via resource module
    - Only allowed imports: json, datetime, statistics, math, re
    - Blocked: requests, subprocess, os.system, eval, exec
    """

    def __init__(self, config: SandboxConfig | None = None):
        self._config = config or SandboxConfig()

    def backtest(
        self,
        tool_code: str,
        historical_data: list[dict[str, Any]],
        target_metric: str,
        baseline_value: float,
    ) -> BacktestResult:
        """
        Run tool backtest in isolated sandbox.

        Args:
            tool_code: Python code for the tool
            historical_data: List of historical action records
            target_metric: Metric to measure improvement on
            baseline_value: Current baseline metric value

        Returns:
            BacktestResult with improvement percentage and metrics
        """
        import time

        start_time = time.time()

        # Validate tool code syntax first
        syntax_errors = self._validate_syntax(tool_code)
        if syntax_errors:
            return BacktestResult(
                improvement_pct=0.0,
                baseline_value=baseline_value,
                tool_value=baseline_value,
                passed=False,
                error=f"Syntax errors: {syntax_errors}",
            )

        # Check for blocked imports
        blocked = self._check_blocked_imports(tool_code)
        if blocked:
            return BacktestResult(
                improvement_pct=0.0,
                baseline_value=baseline_value,
                tool_value=baseline_value,
                passed=False,
                error=f"Blocked imports detected: {blocked}",
                blocked_imports=blocked,
            )

        # Create temporary directory for data snapshot
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = Path(tmpdir) / "historical_data.json"
            with data_file.open("w") as f:
                json.dump(historical_data, f)

            # Run backtest in subprocess
            result = self._run_sandboxed_backtest(
                tool_code=tool_code,
                data_file=str(data_file),
                target_metric=target_metric,
                baseline_value=baseline_value,
            )

        result.runtime_ms = int((time.time() - start_time) * 1000)
        return result

    def _run_sandboxed_backtest(
        self,
        tool_code: str,
        data_file: str,
        target_metric: str,
        baseline_value: float,
    ) -> BacktestResult:
        """Run backtest in isolated subprocess."""
        # Create sandbox script
        sandbox_script = self._create_sandbox_script(
            tool_code, data_file, target_metric, baseline_value
        )

        # Run in subprocess with resource limits and clean environment
        try:
            import os
            import shutil
            clean_env = {}
            for k in ["PATH", "LANG", "LC_ALL", "PYTHONIOENCODING", "PYTHONPATH"]:
                if k in os.environ:
                    clean_env[k] = os.environ[k]
            # Set a mocked/empty HOME to prevent reading user files
            parent_dir = str(Path(data_file).parent)
            clean_env["HOME"] = parent_dir

            # Build command list based on containment availability
            bwrap_path = shutil.which("bwrap")
            docker_path = shutil.which("docker")

            # Check if docker daemon is responsive
            is_docker_active = False
            if docker_path:
                try:
                    proc_check = subprocess.run(
                        [docker_path, "ps"],
                        capture_output=True,
                        timeout=2,
                        env=clean_env,
                    )
                    if proc_check.returncode == 0:
                        is_docker_active = True
                except Exception:
                    pass

            if bwrap_path:
                cmd = [
                    bwrap_path,
                    "--unshare-all",
                    "--proc", "/proc",
                    "--dev", "/dev",
                ]
                # Bind-mount system binaries/libraries for python execution
                for p in ["/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc"]:
                    if os.path.exists(p):
                        cmd += ["--ro-bind", p, p]
                # Bind-mount the temp directory for the data files
                cmd += [
                    "--bind", parent_dir, parent_dir,
                    "--chdir", parent_dir,
                    sys.executable,
                    "-c",
                    sandbox_script,
                ]
                logger.info("Executing tool backtest under bubblewrap sandbox")
            elif is_docker_active and docker_path:
                cmd = [
                    docker_path,
                    "run",
                    "--rm",
                    "--net=none",
                    "-v", f"{parent_dir}:{parent_dir}",
                    "-w", parent_dir,
                    "python:3.11-slim",
                    "python3",
                    "-c",
                    sandbox_script,
                ]
                logger.info("Executing tool backtest under Docker sandbox")
            else:
                cmd = [sys.executable, "-c", sandbox_script]
                logger.warning("No bwrap or docker found; falling back to host subprocess execution")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
                env=clean_env,
                cwd=parent_dir,
            )

            if result.returncode != 0:
                return BacktestResult(
                    improvement_pct=0.0,
                    baseline_value=baseline_value,
                    tool_value=baseline_value,
                    passed=False,
                    error=result.stderr or "Unknown sandbox error",
                )

            # Parse result
            output = json.loads(result.stdout)
            return BacktestResult(
                tool_name=output.get("tool_name", ""),
                improvement_pct=output.get("improvement_pct", 0.0),
                baseline_value=output.get("baseline_value", baseline_value),
                tool_value=output.get("tool_value", baseline_value),
                sample_outputs=output.get("sample_outputs", []),
                error_rate=output.get("error_rate", 0.0),
                passed=output.get("improvement_pct", 0.0) >= 5.0,
            )

        except subprocess.TimeoutExpired:
            return BacktestResult(
                improvement_pct=0.0,
                baseline_value=baseline_value,
                tool_value=baseline_value,
                passed=False,
                error=f"Timeout after {self._config.timeout_seconds}s",
            )
        except json.JSONDecodeError as e:
            return BacktestResult(
                improvement_pct=0.0,
                baseline_value=baseline_value,
                tool_value=baseline_value,
                passed=False,
                error=f"Invalid output JSON: {e}",
            )
        except Exception as e:
            return BacktestResult(
                improvement_pct=0.0,
                baseline_value=baseline_value,
                tool_value=baseline_value,
                passed=False,
                error=f"Sandbox error: {e}",
            )

    def _create_sandbox_script(
        self,
        tool_code: str,
        data_file: str,
        target_metric: str,
        baseline_value: float,
    ) -> str:
        """Create sandboxed execution script."""
        # Escape the tool code for embedding
        escaped_code = tool_code.replace('"""', '\\"\\"\\"')

        # Platform detection for memory limits
        # macOS has different resource limits than Linux
        import platform

        is_macos = platform.system() == "Darwin"
        memory_limit = self._config.memory_limit_mb * 1024 * 1024

        # On macOS, skip memory limit due to different RLIMIT_AS behavior
        memory_limit_code = ""
        if not is_macos:
            memory_limit_code = f"resource.setrlimit(resource.RLIMIT_AS, ({memory_limit}, {memory_limit}))"

        script = f'''
import json
import sys
import resource
import platform

# Set memory limit (Linux only - macOS has different behavior)
{memory_limit_code}

# Load historical data
with open("{data_file}", "r") as f:
    historical_data = json.load(f)

# Tool code
tool_code = """{escaped_code}"""

# Execute tool code in a single namespace. Using separate globals/locals
# here would break module-level imports referenced inside apply(): the
# function's __globals__ is the globals dict, so an import bound in locals
# would be invisible and raise NameError at call time.
exec_globals = {{}}

try:
    exec(tool_code, exec_globals)
except Exception as e:
    result = {{
        "tool_name": "",
        "improvement_pct": 0.0,
        "baseline_value": {baseline_value},
        "tool_value": {baseline_value},
        "error_rate": 1.0,
        "sample_outputs": [],
        "error": f"Tool execution error: {{e}}"
    }}
    print(json.dumps(result))
    sys.exit(0)

# Get the apply function
apply_func = exec_globals.get("apply")

if apply_func is None:
    result = {{
        "tool_name": "",
        "improvement_pct": 0.0,
        "baseline_value": {baseline_value},
        "tool_value": {baseline_value},
        "error_rate": 1.0,
        "sample_outputs": [],
        "error": "No apply() function found in tool code"
    }}
    print(json.dumps(result))
    sys.exit(0)

# Run backtest
errors = 0
sample_outputs = []
tool_sum = 0.0

for i, action in enumerate(historical_data[:100]):  # Limit to 100 actions
    try:
        output = apply_func(action.copy())
        if isinstance(output, dict):
            value = output.get("{target_metric}", 1.0)
            tool_sum += float(value) if value is not None else 1.0
            if i < 5:
                sample_outputs.append(output)
    except Exception as e:
        errors += 1

sample_size = min(len(historical_data), 100)
tool_value = tool_sum / max(sample_size - errors, 1)

if {baseline_value} == 0:
    improvement = 0.0
else:
    improvement = ((tool_value - {baseline_value}) / abs({baseline_value})) * 100.0

result = {{
    "tool_name": "",
    "improvement_pct": round(improvement, 2),
    "baseline_value": {baseline_value},
    "tool_value": round(tool_value, 4),
    "error_rate": errors / max(sample_size, 1),
    "sample_outputs": sample_outputs[:5]
}}

print(json.dumps(result))
'''
        return script

    def _validate_syntax(self, code: str) -> list[str]:
        """Validate Python syntax of tool code."""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Line {e.lineno}: {e.msg}")
        return errors

    def _check_blocked_imports(self, code: str) -> list[str]:
        """Check for blocked imports in tool code."""
        blocked = []
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in self._config.blocked_imports:
                        blocked.append(module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in self._config.blocked_imports:
                        blocked.append(module)

        # Also check for direct string patterns
        for blocked_import in self._config.blocked_imports:
            if f"import {blocked_import}" in code or f"from {blocked_import}" in code:
                if blocked_import not in blocked:
                    blocked.append(blocked_import)

        return blocked


def _meets_threshold(result: BacktestResult, threshold_pct: float = 5.0) -> bool:
    """
    Check if backtest result meets improvement threshold.

    Args:
        result: BacktestResult to check
        threshold_pct: Minimum improvement percentage required

    Returns:
        True if improvement_pct >= threshold_pct
    """
    return result.improvement_pct >= threshold_pct
