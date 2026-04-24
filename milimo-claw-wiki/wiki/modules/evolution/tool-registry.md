# Tool Registry

**Summary**: Manages the inventory of all evolved tools for a claw with provenance signing.

**Sources**:
- `milimo-blueprint/orchestrator/tool_registry.py`

**Last updated**: 2026-04-23

**Tags**: #module #evolution #registry

---

## Overview

The Tool Registry maintains all evolved tools for a claw. Each claw has its own registry at:
```
~/.milimo/tools/<squadId>/<role>/registry.json
```

Supports provenance signing with Ed25519 signatures and automatic rollback on regression.

---

## Key Class

### `ToolRegistry`

```python
class ToolRegistry:
    def __init__(
        self,
        squad_id: str,
        claw_role: str,
        registry_dir: str | None = None,
        max_tools: int = 30,
    ) -> None:
        ...
```

**Parameters**:
- `squad_id` — Squad identifier
- `claw_role` — Claw role (content, ops, analytics, finance, build, assistant)
- `registry_dir` — Custom registry location (optional)
- `max_tools` — Maximum tools to retain (default: 30)

---

## Core Operations

### Register Tool

```python
registry.register(tool: BuiltTool) -> bool
```

Registers a newly evolved tool:
1. Validates tool structure
2. Signs with Ed25519 key
3. Stores in registry
4. Persists to disk

### Enable/Disable

```python
registry.enable(tool_name: str) -> bool
registry.disable(tool_name: str) -> bool
```

Toggle tool availability without removing from registry.

### Get Inventory

```python
inventory = registry.get_inventory()
# Returns: List[Dict[str, Any]]
```

Returns all registered tools with metadata.

---

## Data Classes

### `ToolProvenance`

```python
@dataclass
class ToolProvenance:
    tool_id: str
    claw_role: str
    generated_at: str
    generation_model: str = "local-nim"
    trigger_pattern: str = ""
    backtest_result: dict[str, Any] = field(default_factory=dict)
    deployed_at: str = ""
    signature: str = ""
    signer_key_id: str = ""
```

### `RollbackDecision`

```python
@dataclass
class RollbackDecision:
    should_rollback: bool
    tool_name: str
    reason: str
    current_metric: float
    baseline_metric: float
    threshold: float
    days_since_deploy: int
```

---

## Provenance Signing

When `cryptography` package is available:

1. **Key Generation**: Ed25519 key pair per squad
2. **Signing**: Each tool signed at registration
3. **Verification**: Signature checked at load time

See [[provenance-signing]] for details.

---

## Automatic Rollback

Registry monitors tool performance and can auto-rollback:

```python
decision = registry.check_rollback(tool_name)
if decision.should_rollback:
    registry.rollback(tool_name)
    logger.warning(f"Rolled back {tool_name}: {decision.reason}")
```

**Rollback triggers**:
- Performance regression > threshold
- Error rate exceeds baseline
- User manually disables

---

## Integration

### With ContentGenerator

```python
from orchestrator.tool_registry import ToolRegistry

registry = ToolRegistry(squad_id, claw_role="content")
generator = ContentGenerator(
    privacy_router,
    registry,  # tool_registry
    op_log,
    fs
)
```

### With EvolutionCycle

```python
# After tool generation
registered = tool_registry.register(tool)
if registered:
    logger.info(f"Tool {tool.name} registered successfully")
```

---

## Storage

| Path | Purpose |
|------|---------|
| `~/.milimo/tools/<squad>/<role>/registry.json` | Tool inventory |
| `~/.milimo/keys/<squad>/private.key` | Ed25519 private key |
| `~/.milimo/keys/<squad>/public.key` | Ed25519 public key |

---

## Limits

- Maximum 30 tools per claw (configurable)
- Oldest disabled tools pruned when limit reached
- Provenance data retained for audit

---

## Related Pages

- [[tool-generation]] — Tool creation process
- [[provenance-signing]] — Ed25519 signing
- [[evolution-cycle]] — Evolution pipeline
- [[content-generator]] — Uses tool registry
