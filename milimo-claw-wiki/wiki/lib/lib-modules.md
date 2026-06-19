# Lib Modules

**Summary**: TypeScript library modules providing Python RPC bridge communication, Zod schemas for response validation, configuration encryption, and webhook handling.

**Sources**:
- `milimo/src/lib/rpc-bridge.ts`
- `milimo/src/lib/python-bridge.ts`
- `milimo/src/lib/bridge-schemas.ts`
- `milimo/src/lib/config-encryption.ts`
- `milimo/src/lib/webhook-handler.ts`
- `milimo-blueprint/orchestrator/bridge_server.py`

**Last updated**: 2026-06-19

**Tags**: #lib #typescript #infrastructure

---

## Python Bridge (RPC Architecture)

**Files**:
- `milimo/src/lib/rpc-bridge.ts` — HTTP JSON-RPC client
- `milimo/src/lib/python-bridge.ts` — Typed wrapper (delegates to RPC)
- `milimo-blueprint/orchestrator/bridge_server.py` — Persistent Python RPC server

All Python communication now uses a **persistent JSON-RPC server** instead of per-call subprocess spawning:

```
TypeScript Plugin (no child_process)
  └── rpc-bridge.ts → HTTP POST /rpc → bridge_server.py (persistent process)
                                         └── orchestrator modules
```

### Architecture Benefits

| Aspect | Old (spawnSync) | New (RPC) |
|--------|-----------------|-----------|
| Python process | Spawned per call (15+ processes) | Single persistent server |
| Startup latency | ~500ms per call | Zero (already running) |
| Security surface | `child_process` in scanned plugin | No `child_process` in plugin |
| OpenClaw approval | Required `--dangerously-force-unsafe-install` | Clean install |

### RPC Client (`rpc-bridge.ts`)

Uses Node.js native `fetch()` to send JSON-RPC 2.0 requests:

```typescript
import { getRpcClient } from "../lib/rpc-bridge";

const rpc = getRpcClient();
const result = await rpc.call<T>("method_name", { params });
```

### Python Bridge Wrapper (`python-bridge.ts`)

Provides backwards-compatible API delegating to RPC. All functions are async:

| Function | Description |
|----------|-------------|
| `callPythonBridge()` | Call bridge_cli.py with command and args, returns parsed JSON |
| `callPythonBridgeSafe()` | Safe wrapper that returns `{success, data?, error?}` |
| `callPython()` | Execute arbitrary Python code string |
| `callPythonSafe()` | Safe wrapper for arbitrary Python code |
| `callPythonModule()` | Run a Python module as script |
| `callPythonFile()` | Run a Python file as script |
| `callPythonWithInput()` | Execute Python with stdin input |

### RPC Server (`bridge_server.py`)

Persistent Python HTTP server listening on `127.0.0.1:19999`. Started by `install.sh` and the OpenClaw service manager.

[Handlers: ping, python_eval, python_module, python_file, bridge, solo_init, assistant_setup, assistant_verify, start_launcher, stop_launcher, collect_health]

### Usage

```typescript
import { callPythonBridge, callPythonBridgeSafe } from "./lib/python-bridge";

// Direct call (throws on error)
const health = await callPythonBridge<ClawHealthMap>(
  "collect_health",
  { squad_id: "my-squad" },
  { blueprintDir: "/path/to/blueprint" }
);

// Safe call (returns result object)
const result = await callPythonBridgeSafe<HealthStatus>(
  "health_status",
  { squad_id: "my-squad" },
  { blueprintDir: "/path/to/blueprint" }
);
```

---

## Bridge Schemas

**File**: `milimo/src/lib/bridge-schemas.ts`

Zod schemas for validating responses from bridge_cli.py.

### Key Schemas

| Schema | Type | Description |
|--------|------|-------------|
| `EvolutionStatusSchema` | `EvolutionStatus` | Evolution cycle status |
| `BlueprintInfoSchema` | `BlueprintInfo` | Blueprint metadata |
| `ToolRegistrySchema` | `ToolRegistry` | Tool inventory |
| `HealthStatusSchema` | `HealthStatus` | Claw health map |
| `ProvenanceVerifySchema` | `ProvenanceVerify` | Provenance verification |
| `MarketplaceSearchSchema` | `MarketplaceSearch` | Marketplace results |

---

## Config Encryption

**File**: `milimo/src/lib/config-encryption.ts`

Encrypts sensitive configuration fields using AES-256-GCM with machine-specific key derivation.

| Parameter | Value |
|-----------|-------|
| Algorithm | `aes-256-gcm` |
| Key derivation | `scrypt` with machine-specific salt |
| Machine ID source | `/etc/machine-id` (Linux), `/var/lib/dbus/machine-id` (macOS), hostname fallback |
| Prefix | `enc:v1:` |

Machine ID detection uses native `node:fs` and `node:os` — no external subprocess calls.

---

## Related Pages

- [[bridge-cli]] — Python bridge CLI
- [[bridge-tools]] — TypeScript bridge wrapper
- [[cli-commands]] — CLI command reference
- [[warroom-tui]] — War Room TUI
