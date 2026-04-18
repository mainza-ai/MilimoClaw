# Mesh Gateway Client

**Summary**: Unix socket client for inter-claw messaging via OpenShell gateway.

**Sources**:
- `milimo/src/mesh/gateway-client.ts`

**Last updated**: 2026-04-15

**Tags**: #typescript #mesh #gateway

---

## Overview

GatewayClient connects to the OpenShell gateway via Unix socket for real-time inter-claw messaging. Falls back to file-based queues when gateway is unavailable.

---

## Key Class

### `GatewayClient`

```typescript
class GatewayClient {
  constructor(options: GatewayClientOptions) {}

  // Connect to gateway
  async connect(): Promise<void>

  // Disconnect from gateway
  disconnect(): void

  // Send message
  async send(message: GatewayMessage): Promise<void>

  // Subscribe to messages
  onMessage(handler: (message: GatewayMessage) => void): void
}
```

---

## Interfaces

```typescript
interface GatewayClientOptions {
  squadId: string;
  meshSecret: string;
  onMessage?: (message: GatewayMessage) => void;
}

interface GatewayMessage {
  id: string;
  sender_role: string;
  recipient_role: string;
  message_type: string;
  payload: Record<string, unknown>;
  timestamp: string;
  encrypted?: boolean;
}
```

---

## Socket Paths

| Platform | Path |
|----------|------|
| Linux | `/var/run/openshell/gateway.sock` |
| macOS | `/tmp/openshell-gateway.sock` |

---

## Retry Configuration

```typescript
const MAX_RETRIES = 5;
const INITIAL_RETRY_DELAY = 1000;  // 1 second
const MAX_RETRY_DELAY = 30000;     // 30 seconds
const MESSAGE_TIMEOUT = 5000;      // 5 seconds
```

---

## Fallback Mode

When gateway socket unavailable:
1. Messages written to file queue
2. Files stored in `/tmp/milimo-mesh-queue/`
3. Gateway polls queue when available
4. Automatic retry with exponential backoff

---

## Encryption

Messages encrypted using AES-256-GCM:
```typescript
import { createCipheriv, createDecipheriv, randomBytes, hkdfSync } from "node:crypto";

// Derive key from mesh secret
const key = hkdfSync('sha256', meshSecret, 'milimo-mesh', 32);

// Encrypt message
const cipher = createCipheriv('aes-256-gcm', key, iv);
```

---

## Integration

### With War Room

```typescript
const gateway = new GatewayClient({
  squadId,
  meshSecret,
  onMessage: (msg) => {
    if (msg.message_type === 'action_pending') {
      tui.refreshQueue();
    }
  }
});
await gateway.connect();
```

### With BridgeTools

```typescript
// Send via bridge
await bridgeTools.sendToClaw({
  role: 'ops',
  type: 'status_request',
  payload: {}
});
```

---

## Related Pages

- [[mesh-coordinator]] — Mesh overview
- [[bridge-tools]] — Python bridge
- [[warroom-tui]] — TUI integration
