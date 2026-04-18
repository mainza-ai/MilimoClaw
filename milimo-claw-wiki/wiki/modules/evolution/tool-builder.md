# Tool Builder

**Summary**: Builds proposed tools in isolation and backtests against historical data.

**Sources**:
- `milimo-blueprint/orchestrator/tool_builder.py`

**Last updated**: 2026-04-17

**Tags**: #module #evolution #tools #builder

---

## Overview

ToolBuilder is Stage 3 of the [[evolution-cycle]]. It takes tool proposals, generates code, backtests against 4 weeks of historical data, and only stages for deployment if performance beats baseline.

---

## Key Class

### `ToolBuilder`

```python
class ToolBuilder:
    def __init__(
        self,
        claw_role: str,
        inference: Any,
        registry: ToolRegistry,
        sandbox: ToolSandbox | None = None,
    ) -> None:
        ...
```

**Dependencies**:
- `ToolGenerator` — Generates tool code
- `ToolSandbox` — Isolated testing environment
- `ToolRegistry` — Tool inventory
- `PrivacyRouter` — Inference routing

---

## Build Process

1. **Receive Proposal** — From [[tool-proposal]]
2. **Generate Code** — Using inference backend
3. **Backtest** — Replay 4 weeks of historical data
4. **Compare to Baseline** — Check improvement threshold
5. **Stage or Reject** — Only stage if passes

---

## Data Classes

### `BuiltTool`

```python
@dataclass
class BuiltTool:
    name: str
    claw_role: str
    code: str
    spec: dict[str, Any]
    backtest_result: BacktestResult
    passed: bool
    improvement_pct: float
    created_at: str
```

### `BacktestResult`

```python
@dataclass
class BacktestResult:
    baseline_performance: float
    tool_performance: float
    improvement_pct: float
    passed: bool
    error_rate: float
    latency_ms: float
```

---

## Methods

| Method | Purpose |
|--------|---------|
| `build()` | Build tool from proposal |
| `backtest()` | Run historical data through tool |
| `stage_for_deployment()` | Queue tool for deployment |
| `reject()` | Log rejection reason |

---

## Backtest Configuration

```python
BACKTEST_WEEKS = 4
MIN_IMPROVEMENT_THRESHOLD = 0.10  # 10% improvement required
MAX_ERROR_RATE = 0.05  # 5% max error rate
MAX_LATENCY_MS = 1000  # 1 second max latency
```

---

## Integration

### With EvolutionCycle

```python
# In evolution_cycle.py
builder = ToolBuilder(claw_role, inference, registry)
result = builder.build(proposal)
if result.passed:
    builder.stage_for_deployment(result.tool)
```

### With ToolGenerator

```python
# Generate code using inference
generator = ToolGenerator(inference)
code = generator.generate(spec)
```

---

## Storage

| Path | Purpose |
|------|---------|
| `/sandbox/build/evolution/tools/` | Built tool code |
| `/sandbox/build/evolution/backtest/` | Backtest results |
| `~/.milimo/tools/<squad>/<role>/staged/` | Staged tools |

---

## Related Pages

- [[tool-generation]] — Evolution system overview
- [[tool-proposal]] — Proposal generation
- [[tool-validator]] — Tool validation
- [[tool-registry]] — Tool inventory
- [[evolution-cycle]] — Full pipeline
