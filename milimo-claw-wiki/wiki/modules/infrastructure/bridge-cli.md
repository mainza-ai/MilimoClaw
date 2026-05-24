# Bridge CLI

**Summary**: CLI entry point for TypeScript → Python communication.

**Sources**:
- `milimo-blueprint/orchestrator/bridge_cli.py`
- `milimo/src/lib/python-bridge.ts`

**Last updated**: 2026-05-06

**Tags**: #module #bridge #cli #typescript

---

## Overview

BridgeCLI provides a structured JSON interface for TypeScript to call Python functions. All output goes to stdout, debug logs to stderr.

## Import Architecture

All imports in `bridge_cli.py` use **absolute package imports**:

```python
from orchestrator.contracts import ClawMessage, ContractValidator, ValidationResult
from orchestrator.mesh import MeshCoordinator
from orchestrator.milimo_paths import milimo_mesh_dir
```

This requires `PYTHONPATH` to include the blueprint root directory. The TypeScript bridge (`python-bridge.ts`) injects this automatically when spawning the process:

```typescript
env: { ...process.env, PYTHONPATH: options.blueprintDir }
```

> **Historical note** (2026-05-06): Previous versions used a mix of bare `import milimo_paths` and relative `from .contracts import ...` imports. These failed with `ImportError` / `ModuleNotFoundError` when the script was executed directly (not as a package module). All 22 relative imports and 26 bare `milimo_paths.X` references were converted to absolute imports.

---

## Usage

```bash
python3 bridge_cli.py --command evolution_status --args '{"claw": "build"}'
```

**Response format**:
```json
{"success": true, "data": {...}}
{"success": false, "error": "error message"}
```

---

## Commands

### Evolution Commands

| Command | Description |
|---------|-------------|
| `evolution_status` | Get evolution status for claw |
| `evolution_run` | Trigger evolution cycle |
| `tool_registry` | Get tool inventory |

### Blueprint Commands

| Command | Description |
|---------|-------------|
| `blueprint_info` | Get blueprint information |
| `blueprint_fork` | Fork blueprint |
| `blueprint_diff` | Show blueprint changes |
| `blueprint_merge` | Merge blueprint branches |

### Claw Commands

| Command | Description |
|---------|-------------|
| `claw_status` | Get claw status |
| `claw_start` | Start claw |
| `claw_stop` | Stop claw |
| `send_to_claw` | Send message to claw |

### Mesh Commands

| Command | Description |
|---------|-------------|
| `mesh_status` | Get mesh state |
| `mesh_pending` | Get pending messages |

### Squad Commands

| Command | Description |
|---------|-------------|
| `squad_status` | Get squad topology |
| `squad_create` | Create new squad |

---

## Response Structure

### Success Response

```json
{
  "success": true,
  "data": {
    "status": "idle",
    "tools_deployed": 5,
    "pending_proposals": 0
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Command failed: invalid arguments"
}
```

---

## Integration

### With TypeScript BridgeTools

```typescript
// In bridge-tools.ts
const response = await callPythonBridgeSafe("claw_status", {
  role: "build"
});
```

### With CLI Commands

```typescript
// In milimo/src/commands/
const result = await execFile("python3", [
  "bridge_cli.py",
  "--command", "evolution_status",
  "--args", JSON.stringify({ claw: "build" })
]);
```

---

## Handler Functions

| Function | Command |
|----------|---------|
| `handle_evolution_status()` | `evolution_status` |
| `handle_blueprint_info()` | `blueprint_info` |
| `handle_claw_status()` | `claw_status` |
| `handle_mesh_status()` | `mesh_status` |
| `handle_squad_status()` | `squad_status` |

---

## Related Pages

- [[bridge-tools]] — TypeScript wrapper
- [[cli-commands]] — CLI commands
- [[mesh-gateway-client]] — Gateway client
