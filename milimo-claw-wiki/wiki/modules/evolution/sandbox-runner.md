# Sandbox Runner

**Summary**: Backtest execution in an isolated subprocess. **FIXED 2026-07-04**: `SandboxRunner` now uses `milimo_core.containment.get_contained_command()` to wrap execution with Bubblewrap (`bwrap --unshare-all --ro-bind`) or Docker (`--net=none python:3.11-slim`) when available. Falls back to host subprocess with a logged warning if neither is present.

**Sources**: `milimo-blueprint/orchestrator/evolution/sandbox_runner.py`

**Last updated**: 2026-04-17

**Tags**: #evolution #sandbox #security #backtesting

---

## Overview

`SandboxRunner` provides secure isolated execution for tool backtesting during the evolution cycle. It runs generated tool code in a subprocess with strict resource limits, blocked imports, and no network access.

## Key Class

### SandboxRunner

```python
from sandbox_runner import SandboxRunner, SandboxConfig, BacktestResult

runner = SandboxRunner()
result = runner.backtest(
    tool_code=generated_code,
    historical_data=action_records,
    target_metric="approval_rate",
    baseline_value=0.75,
)

if result.improvement_pct >= 5.0:
    print("Tool passes threshold")
```

## Configuration

### SandboxConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout_seconds` | 30 | Kill if execution exceeds |
| `memory_limit_mb` | 256 | Memory limit (Linux only) |
| `allowed_imports` | json, datetime, statistics, math, re, typing, dataclasses, collections, itertools, functools | Permitted modules |
| `blocked_imports` | requests, urllib, http, socket, subprocess, os.system, eval, exec, compile, __import__, importlib | Blocked modules |
| `read_only_paths` | () | Additional read-only paths |

**Note**: Memory limits are Linux-only. macOS has different `RLIMIT_AS` behavior and skips memory limiting.

## Backtest Results

### BacktestResult

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Name of tested tool |
| `improvement_pct` | `float` | Improvement percentage vs baseline |
| `baseline_value` | `float` | Baseline metric value |
| `tool_value` | `float` | Tool's metric value |
| `sample_outputs` | `list[dict]` | First 5 tool outputs |
| `error_rate` | `float` | Percentage of errors |
| `runtime_ms` | `int` | Execution time in ms |
| `passed` | `bool` | `improvement_pct >= 5.0` |
| `error` | `str` | Error message if failed |
| `blocked_imports` | `list[str]` | Blocked imports detected |

## Execution Flow

1. **Syntax Validation** — Parse code with `ast.parse()` to catch syntax errors
2. **Blocked Import Check** — AST walk to detect forbidden imports
3. **Sandbox Script Creation** — Generate isolated execution script
4. **Subprocess Execution** — Run with resource limits and timeout
5. **Result Parsing** — Extract JSON output, calculate improvement

## ✅ Containment Fix (2026-07-04)

**Audit Finding SA-4.3 [Critical]** was remediated in commits `455de10`–`0c86b7b`:

```python
# sandbox_runner.py:L190-201 — now calls containment helper
from milimo_core.containment import get_contained_command
base_cmd = [sys.executable, "-c", sandbox_script]
cmd = get_contained_command(base_cmd, parent_dir, clean_env)
result = subprocess.run(cmd, capture_output=True, text=True, timeout=..., env=clean_env)
```

`containment.py` wraps the command with:
- **bwrap** (preferred): `--unshare-all --ro-bind /usr /lib /lib64 /bin /sbin /etc --bind <work_dir>`
- **Docker** (fallback): `docker run --rm --net=none -v <work_dir> python:3.11-slim`
- **Host** (last resort): logs warning and returns base_args unchanged

Environment sanitization is also enforced: `HOME` is set to the temp work directory, and only `PATH`, `LANG`, `LC_ALL`, `PYTHONIOENCODING`, `PYTHONPATH` are propagated from the host environment.

Source: `milimo-core/src/milimo_core/evolution/sandbox_runner.py:188-210`, `milimo-core/src/milimo_core/containment.py:20-103`. Verified at HEAD `0c86b7b`.

## Security Features

| Feature | Implementation |
|---------|---------------|
| Restricted builtins | Empty `exec_globals`, only allowed imports |
| No network | Blocked imports: socket, urllib, requests, httpx |
| No arbitrary exec | Blocked: eval, exec, compile, __import__ |
| Memory limit | `resource.setrlimit(resource.RLIMIT_AS, ...)` on Linux |
| Timeout | 30-second subprocess timeout |
| Read-only data | Historical data passed via temp file |
| Filesystem write block | Blocked: open() for writing, .write() |

## Blocked Patterns

The sandbox blocks these patterns:
- `import subprocess` / `from subprocess`
- `import socket` / `from socket`
- `import urllib` / `from urllib`
- `os.system()`
- `eval()`, `exec()`, `compile()`
- `__import__()`
- `open(...'w')` — Write mode
- `.write(`
- `.popen(`

## Tool Requirements

Generated tools must provide an `apply()` function:

```python
def apply(action: dict) -> dict:
    """Apply tool to a single action record.

    Args:
        action: Historical action record

    Returns:
        dict with target metric in it
    """
    # Tool logic
    return {"approval_rate": 0.85, ...}
```

## macOS Handling

The sandbox detects macOS via `platform.system() == "Darwin"` and skips memory limiting since macOS doesn't enforce `RLIMIT_AS` the same way Linux does.

## Backtest Metrics

The backtest runs against up to 100 historical actions and calculates:

```
improvement_pct = ((tool_value - baseline_value) / abs(baseline_value)) * 100.0
```

Where:
- `tool_value` = average of `{target_metric}` across successful runs
- `baseline_value` = original metric value passed in

## Related Pages

- [[tool-generator]] — LLM-based tool code generation
- [[tool-builder]] — Tool building and backtesting workflow
- [[evolution-integration]] — Evolution scheduler
- [[sandbox-isolation]] — Landlock/process-limits/capability-drop filesystem isolation

## See Also

- `milimo-blueprint/orchestrator/evolution/sandbox_runner.py` — Source file
- `milimo-blueprint/orchestrator/tool_generator.py` — Tool generation
