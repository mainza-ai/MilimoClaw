# Lib Modules

**Summary**: TypeScript library modules providing Python bridge communication, Zod schemas for response validation, configuration encryption, and webhook handling.

**Sources**:
- `milimo/src/lib/python-bridge.ts`
- `milimo/src/lib/bridge-schemas.ts`
- `milimo/src/lib/config-encryption.ts`
- `milimo/src/lib/webhook-handler.ts`

**Last updated**: 2026-04-17

**Tags**: #lib #typescript #infrastructure

---

## Python Bridge

**File**: `milimo/src/lib/python-bridge.ts`

Provides safe execution of Python commands using spawnSync with array arguments to prevent shell injection vulnerabilities.

### Core Functions

| Function | Description |
|----------|-------------|
| `callPythonBridge()` | Call bridge_cli.py with command and args, returns parsed JSON |
| `callPythonBridgeSafe()` | Safe wrapper that returns `{success, data?, error?}` |
| `callPython()` | Execute arbitrary Python code string |
| `callPythonSafe()` | Safe wrapper for arbitrary Python code |
| `callPythonModule()` | Run a Python module as script |
| `callPythonFile()` | Run a Python file as script |
| `callPythonWithInput()` | Execute Python with stdin input |

### Usage

```typescript
import { callPythonBridge, callPythonBridgeSafe } from "./lib/python-bridge";

// Direct call (throws on error)
const health = callPythonBridge<ClawHealthMap>(
  "collect_health",
  { squad_id: "my-squad" },
  { blueprintDir: "/path/to/blueprint" }
);

// Safe call (returns result object)
const result = callPythonBridgeSafe<HealthStatus>(
  "health_status",
  { squad_id: "my-squad" },
  { blueprintDir: "/path/to/blueprint" }
);

if (result.success) {
  console.log(result.data);
} else {
  console.error(result.error);
}
```

### Bridge Response Format

```typescript
interface BridgeResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
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

### Usage

```typescript
import { validateBridgeResponse, HealthStatusSchema } from "./lib/bridge-schemas";

const validated = validateBridgeResponse(
  HealthStatusSchema,
  response.data
);
```

---

## Config Encryption

**File**: `milimo/src/lib/config-encryption.ts`

Encrypts sensitive configuration fields using AES-256-GCM with machine-specific key derivation.

### Encryption Details

| Parameter | Value |
|-----------|-------|
| Algorithm | `aes-256-gcm` |
| Key derivation | `scrypt` with machine-specific salt |
| Machine ID source | `/etc/machine-id` (Linux), hardware UUID (macOS), WMIC (Windows) |
| Prefix | `enc:v1:` |

### Sensitive Fields (auto-encrypted)

- `meshSecret`
- `apiKey`
- `apiToken`
- `accessToken`
- `refreshToken`

### Functions

| Function | Description |
|----------|-------------|
| `getMachineId()` | Get machine-specific identifier |
| `deriveKey()` | Derive encryption key from machine ID |
| `encryptValue()` | Encrypt a single value |
| `decryptValue()` | Decrypt a single value |
| `isEncrypted()` | Check if value is encrypted |
| `encryptConfig()` | Encrypt sensitive fields in config object |
| `decryptConfig()` | Decrypt sensitive fields in config object |

### Usage

```typescript
import { encryptValue, decryptValue, encryptConfig, decryptConfig } from "./lib/config-encryption";

// Encrypt a single value
const encrypted = encryptValue("my-secret-key");
// Returns: "enc:v1:..."

// Decrypt
const decrypted = decryptValue(encrypted);

// Encrypt config fields
const encryptedConfig = encryptConfig({
  meshSecret: "secret",
  otherField: "visible"
});
// meshSecret is encrypted, otherField unchanged
```

---

## Webhook Handler

**File**: `milimo/src/lib/webhook-handler.ts`

Handles incoming webhook requests from external services.

### Usage

```typescript
import { WebhookHandler } from "./lib/webhook-handler";

const handler = new WebhookHandler({
  secret: process.env.WEBHOOK_SECRET,
  onEvent: (event) => console.log(event),
});

server.use("/webhook", handler.middleware());
```

---

## Related Pages

- [[bridge-cli]] — Python bridge CLI
- [[bridge-tools]] — TypeScript bridge wrapper
- [[cli-commands]] — CLI command reference
- [[warroom-tui]] — War Room TUI
