# Module Template

**Summary**: Template for documenting a Python module.

**Last updated**: 2026-04-14

**Tags**: #template #module

---

# {{module-name}}

**Summary**: One-line description of this module's purpose.

**Sources**:
- `milimo-blueprint/orchestrator/{{claw}}/{{module}}.py`

**Last updated**: YYYY-MM-DD

**Tags**: #module #{{claw}}-claw

---

## Purpose

Describe what this module does and why it exists.

## Location

**File**: `milimo-blueprint/orchestrator/{{claw}}/{{module}}.py`

## Key Classes

### ClassName

Brief description of the class.

```python
class ClassName:
    def __init__(self, param1, param2):
        """Initialize with parameters."""
        pass

    def method_name(self, arg):
        """Method description."""
        pass
```

## Key Functions

### function_name(param1, param2) → ReturnType

Description of what the function does.

**Parameters**:
- `param1` (type): Description
- `param2` (type): Description

**Returns**: Description of return value

## Dependencies

- `dependency1` — Purpose
- `dependency2` — Purpose

## Usage

```python
from orchestrator.{{claw}}.{{module}} import ClassName

instance = ClassName(param1, param2)
result = instance.method(arg)
```

## Interactions

### Called By

- [[calling-module-1]]
- [[calling-module-2]]

### Calls

- [[called-module-1]]
- [[called-module-2]]

## Configuration

Any configuration values or environment variables used.

## Error Handling

How errors are handled and logged.

## Testing

- Test file: `tests/test_{{module}}.py`
- Coverage: What is tested

## Related Pages

- [[{{claw}}-claw]]
- [[related-module-1]]
- [[related-module-2]]
