# Bridge CLI

**Summary**: CLI entry point for TypeScript → Python communication.

**Sources**:
- `milimo-blueprint/orchestrator/bridge_cli.py`

**Last updated**: 2026-04-17

**Tags**: #module #bridge #cli #typescript

---

## Overview

BridgeCLI provides a structured JSON interface for TypeScript to call Python functions. All output goes to stdout, debug logs to stderr.

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
