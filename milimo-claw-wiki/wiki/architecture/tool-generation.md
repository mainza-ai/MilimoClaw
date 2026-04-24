# tool-generation

**Summary**: Core evolution system for generating, building, and deploying autonomous tools.

**Sources**:
- `milimo-blueprint/orchestrator/tool_builder.py`
- `milimo-blueprint/orchestrator/tool_generator.py`
- `milimo-blueprint/orchestrator/tool_registry.py`
- `milimo-blueprint/orchestrator/tool_proposal.py`
- `milimo-blueprint/orchestrator/evolution/sandbox_runner.py`

**Last updated**: 2026-04-14

**Tags**: #architecture #evolution

---

## Purpose

The tool-generation system is the core of MilimoClaw's self-evolution capability. It generates, tests, and deploys new tools autonomously based on detected patterns in operational data.

## Location

**Files**:
- `orchestrator/tool_builder.py` — Build and backtest
- `orchestrator/tool_generator.py` — Code generation
- `orchestrator/tool_registry.py` — Deployment management
- `orchestrator/tool_proposal.py` — Proposal validation
- `orchestrator/evolution/sandbox_runner.py` — Isolated execution

---

## System Overview

```
Pattern Detected → ToolProposal → ToolBuilder → SandboxRunner → ToolRegistry
                      │                │              │              │
                      │                │              │              │
                   validates      generates      backtests      deploys
                   permissions    code          in sandbox     to claw
```

---

## Key Components

### ToolProposal

Creates and validates tool proposals from detected patterns.

```python
@dataclass
class ToolProposal:
    tool_name: str
    tool_type: str  # classifier | optimizer | predictor | generator_variant | anomaly_detector
    trigger_pattern: EvolutionPattern
    metric_target: str
    data_sources_required: list[str]
    estimated_improvement: float
    status: str  # proposed | approved | building | testing | deployed | rejected | disabled
```

**Key function**: `validate_permissions(proposal, sandbox_policy)` — Ensures tools don't exceed claw's existing permissions.

---

### ToolGenerator

Generates Python tool implementations using LLM inference.

```python
class ToolGenerator:
    def __init__(
        self,
        config: GenerationConfig | None = None,
        template_dir: str | Path | None = None,
    ): ...

    def generate(self, spec: ToolSpec) -> GenerationResult:
        """Generate tool implementation from specification."""
```

**Tool types supported**:
| Type | Description |
|------|-------------|
| `classifier` | Categorizes content/actions |
| `predictor` | Predicts outcomes/values |
| `optimizer` | Optimizes timing/parameters |
| `detector` | Detects anomalies/patterns |
| `generator` | Generates content variants |

**Security validation**: CodeValidator checks for forbidden patterns:
- No `subprocess`, `socket`, `urllib`, `requests`
- No `eval`, `exec`, `compile`
- No filesystem writes
- Must have type hints and docstrings

---

### ToolBuilder

Builds tools and backtests against 4 weeks of historical data.

```python
class ToolBuilder:
    def __init__(
        self,
        claw_role: str,
        squad_id: str = "",
        min_improvement_percent: float = 5.0,
        backtest_window_weeks: int = 4,
    ): ...

    def build(
        self,
        proposal: ToolProposal,
        historical_actions: list[ActionRecord],
    ) -> BuildResult:
        """Build and backtest a tool from proposal."""
```

**Build process**:
1. Generate tool code (via inference, `data_type: "source_code"`)
2. Compute data hash for provenance
3. Backtest against historical data
4. Check improvement threshold (default: 5%)
5. Stage for deployment if passed

**Privacy routing**: Tool code generation routes to **Local NIM (NEMOCLAW_MODEL)** — source code is IP.

---

### SandboxRunner

Executes tool backtests in isolated subprocess.

```python
class SandboxRunner:
    def backtest(
        self,
        tool_code: str,
        historical_data: list[dict],
        target_metric: str,
        baseline_value: float,
    ) -> BacktestResult:
        """Run tool backtest in isolated sandbox."""
```

**Security features**:
| Feature | Implementation |
|---------|----------------|
| Subprocess isolation | Runs in separate process |
| No network | Blocked imports: requests, urllib, socket |
| No filesystem writes | Read-only historical data |
| 30s timeout | Kill if exceeded |
| 256MB memory limit | Via resource module |
| Restricted imports | Only: json, datetime, statistics, math, re, typing |

---

### ToolRegistry

Manages deployed tools with provenance signing.

```python
class ToolRegistry:
    def __init__(
        self,
        squad_id: str,
        claw_role: str,
        max_tools: int = 30,
    ): ...

    def register(self, tool: BuiltTool) -> bool: ...
    def disable(self, tool_name: str) -> bool: ...
    def enable(self, tool_name: str) -> bool: ...
    def check_for_regression(self, tool_name: str, current_metric: float) -> RollbackDecision: ...
```

**Provenance signing**:
- Uses Ed25519 signatures
- Signs tool metadata and backtest results
- Verifiable by third parties

**Automatic rollback**:
- Monitors metric for 7 days post-deploy
- If metric < baseline × 0.95: deactivates tool
- Prevents regression from deployed tools

---

## Tool Lifecycle

### Stage 1: Proposal

```
EvolutionPattern detected → generate_proposal(pattern, claw_role)
                                ↓
                         ToolProposal created
                                ↓
                         validate_permissions(proposal, sandbox_policy)
```

### Stage 2: Build

```
ToolProposal approved → ToolBuilder.build(proposal, historical_actions)
                              ↓
                        ToolGenerator.generate(spec)
                              ↓
                        code generated (data_type: source_code)
```

### Stage 3: Backtest

```
Code generated → SandboxRunner.backtest(code, data, metric, baseline)
                      ↓
                 Execute in subprocess
                      ↓
                 Compare to baseline
                      ↓
                 Pass if improvement >= 5%
```

### Stage 4: Deploy

```
Backtest passed → ToolRegistry.register(tool)
                       ↓
                  Sign provenance
                       ↓
                  Monitor for 7 days
                       ↓
                  Auto-rollback if regression
```

---

## Configuration

### GenerationConfig

```python
@dataclass
class GenerationConfig:
    template_dir: str = ""
    max_code_length: int = 10000
    max_execution_time_ms: int = 5000
    max_memory_mb: int = 200
    require_type_hints: bool = True
    require_docstrings: bool = True
    forbid_network: bool = True
    forbid_filesystem_write: bool = True
```

### SandboxConfig

```python
@dataclass
class SandboxConfig:
    timeout_seconds: int = 30
    memory_limit_mb: int = 256
    allowed_imports: tuple = ("json", "datetime", "statistics", "math", "re", "typing")
    blocked_imports: tuple = ("requests", "urllib", "socket", "subprocess", "eval", "exec")
```

---

## File Storage

### Tool Registry

```
~/.milimo/tools/{squad_id}/{claw_role}/
└── registry.json
```

### Tool Staging

```
/tmp/milimo-tool-staging/{claw_role}/
└── {tool_name}.json
```

---

## Integration with Evolution Cycle

The tool-generation system is invoked during [[evolution-cycle]] Stage 4 (Build & Test):

```
STAGE 4 — BUILD & TEST
├── ToolGenerator.generate(spec)
├── ToolBuilder.build(proposal, historical_actions)
│   ├── SandboxRunner.backtest(code, data, metric, baseline)
│   └── Check: improvement >= min_improvement_percent
└── If passed: ToolRegistry.register(tool)
```

---

## Dependencies

- [[evolution-cycle]] — Sunday evolution pipeline
- [[privacy-router]] — Inference routing (source_code → Local NIM (NEMOCLAW_MODEL))
- [[pattern-detector]] — Pattern identification

## Related Pages

- [[evolution-cycle]] — 5-stage evolution pipeline
- [[privacy-router]] — Inference routing
- [[claw-launcher]] — Claw initialization
- [[sandbox-isolation]] — Sandbox security model
