# Tool Validator

**Summary**: Static analysis and security validation for generated tool code.

**Sources**:
- `milimo-blueprint/orchestrator/tool_validator.py`

**Last updated**: 2026-04-17

**Tags**: #module #evolution #security #validation

---

## Overview

ToolValidator performs security validation on generated tool code to ensure compliance with sandbox policies before deployment.

---

## Key Class

### `ToolValidator`

```python
class ToolValidator:
    def __init__(
        self,
        policy: PolicyConstraints | None = None,
    ) -> None:
        self.policy = policy or PolicyConstraints()
```

---

## Data Classes

### `ValidationResult`

```python
@dataclass
class ValidationResult:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 0.0
    safe_to_deploy: bool = False
```

### `ValidationIssue`

```python
@dataclass
class ValidationIssue:
    severity: Severity  # INFO, WARNING, ERROR, CRITICAL
    code: str
    message: str
    line: int = 0
    column: int = 0
    suggestion: str = ""
```

### `PolicyConstraints`

```python
@dataclass
class PolicyConstraints:
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allow_subprocess: bool = False
    allow_dynamic_exec: bool = False
    allowed_imports: set[str] | None = None
    max_code_length: int = 10000
    max_complexity: int = 20
    require_type_hints: bool = True
```

---

## Validation Checks

| Check | Description | Severity |
|-------|-------------|----------|
| Import validation | Only allowed imports | ERROR |
| Network calls | Detect network requests | ERROR |
| File system write | Detect write operations | WARNING |
| Subprocess calls | Detect subprocess usage | ERROR |
| Dynamic execution | Detect eval/exec | CRITICAL |
| Code length | Max 10000 characters | WARNING |
| Complexity | Max cyclomatic complexity 20 | WARNING |
| Type hints | Required on public functions | INFO |

---

## Usage

```python
from tool_validator import ToolValidator, PolicyConstraints

validator = ToolValidator()
result = validator.validate(tool_code)

if result.passed and result.safe_to_deploy:
    print("Tool is safe to deploy")
else:
    for issue in result.issues:
        print(f"{issue.severity}: {issue.message}")
```

---

## Integration

### With ToolBuilder

```python
# After building tool
result = builder.build(proposal)
validation = validator.validate(result.code)
if not validation.passed:
    builder.reject(result, validation.issues)
```

---

## Related Pages

- [[tool-builder]] — Tool building
- [[tool-proposal]] — Proposal generation
- [[sandbox-isolation]] — Sandbox policies
