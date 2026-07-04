# Bridge CLI

**Summary**: CLI entry point for TypeScript → Python communication.

**Sources**:
- `milimo-blueprint/orchestrator/bridge_cli.py`
- `milimo-blueprint/orchestrator/bridge_server.py`
- `milimo/src/lib/python-bridge.ts`
- `milimo/src/lib/rpc-bridge.ts`

**Last updated**: 2026-07-03

**Tags**: #module #bridge #cli #typescript

---

## Overview

BridgeCLI provides a structured JSON interface for TypeScript to call Python functions. All output goes to stdout, debug logs to stderr.

## Communication Architecture

```
TypeScript Plugin
  └── python-bridge.ts / bridge-tools.ts
      └── rpc-bridge.ts (HTTP JSON-RPC client)
          └── bridge_server.py (persistent server, port 19999)
              └── bridge_cli.py (command handlers)
```

The **persistent RPC server** (`bridge_server.py`) replaces the old per-call subprocess spawning. It runs continuously as a background process, eliminating process startup overhead and removing `child_process` from the plugin's security surface.

### Server Lifecycle

- **Start**: Auto-started by `install.sh` via nohup + PID file
- **Persistence**: Startup command added to `/sandbox/.bashrc` for sandbox restarts
- **Health**: RPC server exposes `/health` endpoint on port 19999
- **Management**: Can be managed via OpenClaw's `api.registerService()` when available

---

## Usage

```bash
# Direct Python invocation (outside plugin)
python3 bridge_cli.py --command evolution_status --args '{"claw": "build"}'

# Via RPC server (normal path — server handles routing)
# Handled automatically by rpc-bridge.ts in the plugin
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
const response = await callPythonBridgeSafe("claw_status", {
  role: "build"
});
// Routes through RPC server automatically
```

### With RPC Client (Direct)

```typescript
import { getRpcClient } from "../lib/rpc-bridge";

const rpc = getRpcClient();
const result = await rpc.call("bridge", {
  command: "evolution_status",
  args: { claw: "build" },
  blueprintDir: "/sandbox/.openclaw/milimo/milimo-blueprint"
});
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

## ✅ Audit Finding SA-1.3 [High] — FIXED 2026-07-04

`bridge_cli.py` now exposes `approve-action` and `veto-action` handlers at lines 2039-2077:

| Handler | Purpose |
|---|---|
| `handle_approve_action(action_id)` | Moves action from `war_room` inbox to recipient claw inbox |
| `handle_veto_action(action_id)` | Moves action to `rejected/` queue |

Both are registered in `COMMAND_HANDLERS` at lines 2080-2082. Shell-native operators can now approve/veto without the Hermes HTMX UI.

Source: `milimo-blueprint/orchestrator/bridge_cli.py:2039-2082`. Verified at HEAD `0c86b7b`.

---

## Related Pages

- [[bridge-tools]] — TypeScript wrapper
- [[cli-commands]] — CLI commands
- [[mesh-gateway-client]] — Gateway client
