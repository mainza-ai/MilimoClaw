# Tool Generator

**Summary**: LLM-based code generation for creating new tool implementations from specifications. Part of the self-evolution engine's BUILD stage.

**Sources**: `milimo-blueprint/orchestrator/tool_generator.py`

**Last updated**: 2026-04-17

**Tags**: #evolution #tool-generation #build

---

## Overview

The `ToolGenerator` class generates Python tool implementations from structured specifications using LLM inference. It coordinates prompt building, code validation, and testing to produce production-ready tool code.

## Key Classes

### ToolGenerator

Main class for generating tool implementations.

```python
from tool_generator import ToolGenerator, ToolSpec, GenerationResult

generator = ToolGenerator()
result = generator.generate(tool_spec)

if result.success:
    print(result.code)
```

**Methods**:
- `generate(spec: ToolSpec) -> GenerationResult` — Generate tool code from specification
- `_call_llm(prompt, tool_type)` — Routes to LLM inference (placeholder for NemoClaw integration)
- `_extract_code(response: str) -> str` — Extracts Python from markdown code blocks
- `_estimate_performance(code: str, spec: ToolSpec) -> float` — Estimates improvement percentage

### PromptBuilder

Builds prompts for each tool type using templates.

**Location**: `prompts/tool-generation/{tool_type}.txt`

**Template variables**:
- `{{tool_name}}`, `{{description}}`, `{{input_schema}}`, `{{output_schema}}`
- Type-specific: `{{target_classes}}`, `{{optimization_target}}`, `{{detection_target}}`, etc.

### CodeValidator

Validates generated code for security and correctness.

**Forbidden imports**: `subprocess`, `os.system`, `eval`, `exec`, `socket`, `urllib`, `requests`, `pickle`

**Checks**:
- Code length limits (default: 10,000 chars)
- Forbidden pattern detection via regex
- Type hints on `run()` function
- Docstrings on `run()` function
- Python syntax validation via `compile()`

### CodeTester

Tests generated tools against test cases in isolated execution.

**Test validations**:
- `exact` — Output must match expected exactly
- `partial` — Output must contain expected keys
- `schema_only` — Just validate JSON output

## Types

### ToolSpec

Specification for a tool to be generated.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Tool name |
| `tool_type` | `ToolType` | One of: classifier, predictor, optimizer, detector, generator, transformer, aggregator |
| `description` | `str` | Tool description |
| `input_schema` | `dict` | JSON schema for input |
| `output_schema` | `dict` | JSON schema for output |
| `permissions` | `dict` | Sandbox permissions |
| `pattern_description` | `str` | When to use this tool |
| `frequency` | `int` | Expected uses per week |
| `test_cases` | `list[dict]` | Test cases with `input`, `expected_output`, `validation` |

### GenerationResult

Result of tool generation.

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether generation succeeded |
| `code` | `str` | Generated Python code |
| `error` | `str` | Error message if failed |
| `warnings` | `list[str]` | Validation/test warnings |
| `validation_passed` | `bool` | Code passed validation |
| `test_passed` | `bool` | Tests passed |
| `estimated_performance` | `float` | Estimated improvement % |

### GenerationConfig

Configuration for tool generation.

| Field | Default | Description |
|-------|---------|-------------|
| `max_code_length` | 10000 | Max code characters |
| `max_execution_time_ms` | 5000 | Test timeout |
| `max_memory_mb` | 200 | Memory limit |
| `require_type_hints` | `True` | Enforce type hints |
| `require_docstrings` | `True` | Enforce docstrings |
| `forbid_network` | `True` | Block network imports |
| `forbid_filesystem_write` | `True` | Block file writes |

## Tool Types

| Type | Base Improvement | Use Case |
|------|------------------|----------|
| `classifier` | 5.0% | Categorize inputs (spam, sentiment, urgency) |
| `predictor` | 7.0% | Forecast values (revenue, engagement) |
| `optimizer` | 10.0% | Maximize/minimize metrics |
| `detector` | 6.0% | Identify anomalies, threats |
| `generator` | 4.0% | Create content (copy, designs) |
| `transformer` | 5.0% | Format conversion, enrichment |
| `aggregator` | 3.0% | Combine, summarize data |

## Workflow

1. **Prompt Building** — `PromptBuilder.build_prompt()` reads template based on `tool_type`
2. **LLM Generation** — `ToolGenerator._call_llm()` generates code (placeholder for NemoClaw)
3. **Code Extraction** — Extract Python from markdown code blocks
4. **Validation** — `CodeValidator` checks security patterns, type hints, syntax
5. **Testing** — `CodeTester` runs test cases in temporary directory
6. **Performance Estimation** — Calculate estimated improvement based on type and frequency

## Related Pages

- [[evolution-cycle]] — Sunday 5-stage evolution pipeline
- [[tool-builder]] — Tool building and backtesting workflow
- [[tool-proposal]] — Proposal schema and validation
- [[tool-validator]] — Security validation of generated tools
- [[sandbox-runner]] — Isolated backtest execution

## See Also

- `milimo-blueprint/orchestrator/tool_generator.py` — Source file
- `milimo-blueprint/orchestrator/evolution/sandbox_runner.py` — Backtest execution
