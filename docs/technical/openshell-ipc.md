# OpenShell IPC Technical Documentation

**Version:** 1.0
**Date:** March 18, 2026
**Status:** Draft

---

## Overview

This document describes how Milimo Claw integrates with OpenShell's Inter-Process Communication (IPC) capabilities to enable true distributed mesh communication between squad members.

---

## OpenShell Gateway Architecture

### Gateway Components

OpenShell provides a gateway service that handles all inter-sandbox communication:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host Machine                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Sandbox A  │    │  Gateway    │    │  Sandbox B  │         │
│  │  (Content)  │◄──►│  Service    │◄──►│   (Ops)     │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                 │
│         │                  ▼                  │                 │
│         │         ┌─────────────┐            │                 │
│         └────────►│ Message Bus │◄───────────┘                 │
│                   └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Message Flow

1. **Send:** Claw calls gateway API with message payload
2. **Route:** Gateway validates contract and routes to recipient
3. **Queue:** Message queued in recipient's sandbox inbox
4. **Receive:** Recipient claw polls or receives push notification

---

## IPC API Specification

### Connection Endpoint

```
unix:///var/run/openshell/gateway.sock
```

For remote gateways:
```
tcp://gateway.openshell.local:18789
```

### Message Format

All messages follow the ClawMessage contract:

```json
{
  "message_id": "abc123def456",
  "sender_role": "content",
  "recipient_role": "ops",
  "message_type": "deliverable",
  "payload": {
    "type": "draft",
    "content": "...",
    "metadata": {}
  },
  "squad_id": "my-squad",
  "timestamp": "2026-03-18T12:00:00Z",
  "signature": "ed25519:..."
}
```

### API Methods

#### SEND

Send a message to another sandbox.

**Request:**
```json
{
  "method": "SEND",
  "params": {
    "recipient": "ops",
    "message": { ... ClawMessage ... }
  }
}
```

**Response:**
```json
{
  "status": "queued",
  "message_id": "abc123def456",
  "requires_approval": false
}
```

#### RECEIVE

Poll for pending messages.

**Request:**
```json
{
  "method": "RECEIVE",
  "params": {
    "role": "content",
    "limit": 10,
    "ack": true
  }
}
```

**Response:**
```json
{
  "messages": [
    { ... ClawMessage ... },
    { ... ClawMessage ... }
  ],
  "has_more": false
}
```

#### SUBSCRIBE

Subscribe to real-time message notifications (WebSocket).

**Request:**
```json
{
  "method": "SUBSCRIBE",
  "params": {
    "role": "content",
    "events": ["message", "approval_request"]
  }
}
```

**Response:**
```json
{
  "status": "subscribed",
  "subscription_id": "sub_abc123"
}
```

#### APPROVE

Approve a pending action (War Room operator).

**Request:**
```json
{
  "method": "APPROVE",
  "params": {
    "message_id": "abc123def456",
    "operator_id": "local-operator",
    "decision": "APPROVED"
  }
}
```

**Response:**
```json
{
  "status": "approved",
  "delivered_at": "2026-03-18T12:01:00Z"
}
```

---

## Authentication

### Mesh Secret

Each squad has a shared secret used for message authentication:

```yaml
# In openclaw.plugin.json
meshSecret: "squad-secret-abc123"
```

### Ed25519 Signing

Messages are signed with Ed25519 to ensure authenticity:

```python
from nacl.signing import SigningKey

def sign_message(message: dict, private_key: SigningKey) -> str:
    message_bytes = json.dumps(message, sort_keys=True).encode()
    signed = private_key.sign(message_bytes)
    return f"ed25519:{signed.signature.hex()}"
```

### Verification

```python
from nacl.signing import VerifyKey

def verify_message(message: dict, signature: str, public_key: bytes) -> bool:
    sig_hex = signature.replace("ed25519:", "")
    verify_key = VerifyKey(public_key)
    message_bytes = json.dumps(message, sort_keys=True).encode()
    try:
        verify_key.verify(message_bytes, bytes.fromhex(sig_hex))
        return True
    except:
        return False
```

---

## Gateway Adapter Interface

Milimo Claw abstracts the gateway through an adapter interface:

```python
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class GatewayConfig:
    endpoint: str  # unix:// or tcp://
    mesh_secret: str
    squad_id: str
    role: str
    timeout_ms: int = 5000

class GatewayAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to gateway."""
        pass

    @abstractmethod
    def send(self, message: ClawMessage) -> SendResult:
        """Send message through gateway."""
        pass

    @abstractmethod
    def receive(self, limit: int = 10) -> list[ClawMessage]:
        """Poll for pending messages."""
        pass

    @abstractmethod
    def subscribe(self, handler: Callable[[ClawMessage], None]) -> str:
        """Subscribe to real-time notifications."""
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Cancel subscription."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close gateway connection."""
        pass
```

---

## Implementation Strategies

### Strategy 1: Unix Socket (Single Host)

For squad members on the same machine (development/testing):

```python
import socket
import json

class UnixSocketGateway(GatewayAdapter):
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        sock_path = self.config.endpoint.replace("unix://", "")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.connect(sock_path)
            self._authenticate()
            return True
        except socket.error:
            return False

    def send(self, message: ClawMessage) -> SendResult:
        payload = json.dumps({
            "method": "SEND",
            "params": {"recipient": message.recipient_role, "message": message.to_dict()}
        })
        self.sock.sendall(payload.encode() + b"\n")
        response = json.loads(self.sock.recv(65536))
        return SendResult(
            success=response["status"] in ("queued", "delivered"),
            message_id=response.get("message_id", ""),
            requires_approval=response.get("requires_approval", False)
        )
```

### Strategy 2: TCP/WebSocket (Multi-Host)

For distributed squads across machines:

```python
import websocket
import threading

class WebSocketGateway(GatewayAdapter):
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.ws: Optional[websocket.WebSocketApp] = None
        self.message_queue: queue.Queue = queue.Queue()
        self.subscriptions: dict[str, Callable] = {}

    def connect(self) -> bool:
        ws_url = self.config.endpoint.replace("tcp://", "ws://")
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        return True

    def _on_message(self, ws, message):
        data = json.loads(message)
        if "event" in data and data["event"] in self.subscriptions:
            self.subscriptions[data["event"]](ClawMessage.from_dict(data["message"]))
        else:
            self.message_queue.put(data)
```

### Strategy 3: File-Based (Fallback)

For environments without OpenShell gateway:

```python
import json
from pathlib import Path

class FileBasedGateway(GatewayAdapter):
    """
    Fallback implementation using file-based queues.
    Used when OpenShell gateway is not available.
    """
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.base_dir = Path.home() / ".milimo" / "mesh"
        self.inbox = self.base_dir / "inbox" / config.role
        self.outbox = self.base_dir / "outbox" / config.role
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)

    def send(self, message: ClawMessage) -> SendResult:
        target_inbox = self.base_dir / "inbox" / message.recipient_role
        target_inbox.mkdir(parents=True, exist_ok=True)

        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        (target_inbox / filename).write_text(json.dumps(message.to_dict(), indent=2))

        return SendResult(success=True, message_id=message.message_id)
```

---

## Connection Lifecycle

### Connection States

```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│ DISCONN │────►│ CONNECTNG│────►│ CONNECTD│────►│   ERROR  │
└─────────┘     └──────────┘     └─────────┘     └──────────┘
     ▲                │               │                │
     │                │               │                │
     └────────────────┴───────────────┴────────────────┘
                         (reconnect)
```

### Reconnection Logic

```python
import time
from functools import wraps

def with_reconnect(max_attempts: int = 3, delay_ms: int = 1000):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except ConnectionError as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay_ms / 1000)
                    self.connect()
            return None
        return wrapper
    return decorator
```

---

## Error Handling

### Error Codes

| Code | Description | Recovery |
|------|-------------|----------|
| `E001` | Gateway unavailable | Retry with backoff |
| `E002` | Authentication failed | Check mesh secret |
| `E003` | Invalid message format | Validate against schema |
| `E004` | Contract violation | Check message matrix |
| `E005` | Recipient not found | Verify role is registered |
| `E006` | Approval timeout | Escalate to War Room |

### Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "E003",
    "message": "Invalid message format: missing 'message_type' field",
    "details": {
      "field": "message_type",
      "expected": "string",
      "received": null
    }
  }
}
```

---

## Performance Considerations

### Latency Targets

| Scenario | Target Latency | Max Acceptable |
|----------|---------------|----------------|
| Same host | < 10ms | 50ms |
| Same LAN | < 50ms | 200ms |
| Different region | < 500ms | 2000ms |

### Message Size Limits

- Maximum message size: 1MB
- Recommended size: < 100KB
- Large payloads should use external storage with reference

### Throughput

- Messages per second per sandbox: 100
- Burst capacity: 500 messages
- Queue depth limit: 10,000 messages

---

## Security

### TLS Requirements

- TLS 1.3 required for TCP connections
- Certificate validation enforced
- Self-signed certificates rejected in production

### Message Signing

All messages must be signed with Ed25519:
1. Serialize message to JSON with sorted keys
2. Sign with sender's private key
3. Include signature in message header
4. Gateway validates before routing

### Access Control

```yaml
# Gateway enforces message matrix
# Messages outside matrix are rejected
message_matrix:
  content:
    ops: [deliverable]
    analytics: [query]
    war_room: [deliverable]
```

---

## Monitoring

### Metrics

| Metric | Description |
|--------|-------------|
| `gateway.messages_sent` | Count of messages sent |
| `gateway.messages_received` | Count of messages received |
| `gateway.latency_ms` | Message round-trip latency |
| `gateway.queue_depth` | Pending messages in inbox |
| `gateway.errors` | Error count by code |

### Health Check

```python
def health_check(self) -> dict:
    return {
        "connected": self.sock is not None,
        "endpoint": self.config.endpoint,
        "last_message_at": self.last_message_time,
        "queue_depth": len(list(self.inbox.glob("*.json"))),
        "errors_count": self.error_count
    }
```

---

## Testing

### Unit Tests

```python
def test_gateway_send():
    gateway = FileBasedGateway(test_config)
    message = ClawMessage(
        sender_role="content",
        recipient_role="ops",
        message_type="deliverable",
        payload={"test": True},
        squad_id="test-squad"
    )
    result = gateway.send(message)
    assert result.success
    assert (gateway.base_dir / "inbox" / "ops").exists()
```

### Integration Tests

```python
@pytest.mark.integration
def test_gateway_round_trip():
    gateway_a = UnixSocketGateway(config_a)
    gateway_b = UnixSocketGateway(config_b)

    gateway_a.connect()
    gateway_b.connect()

    message = ClawMessage(...)
    gateway_a.send(message)

    received = gateway_b.receive(limit=1)
    assert len(received) == 1
    assert received[0].message_id == message.message_id
```

---

## References

- OpenShell Gateway Documentation: https://github.com/NVIDIA/OpenShell/docs/gateway.md
- NemoClaw Architecture: `docs/reference/architecture.md`
- Milimo Claw Contracts: `milimo-blueprint/orchestrator/contracts.py`
