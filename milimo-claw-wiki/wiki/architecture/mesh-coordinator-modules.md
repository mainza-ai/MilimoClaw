# mesh-coordinator-modules

**Summary**: Mesh implementation modules including gateway adapters, encryption, and failover.

**Sources**:
- `milimo-blueprint/orchestrator/mesh.py`
- `milimo-blueprint/orchestrator/gateway_adapter.py`
- `milimo-blueprint/orchestrator/mesh_encryption.py`
- `milimo-blueprint/orchestrator/mesh_failover.py`
- `milimo-blueprint/orchestrator/mesh_relay.py`

**Last updated**: 2026-04-14

**Tags**: #architecture #mesh

---

## Purpose

Documents the implementation modules for the inter-claw mesh communication system.

## Location

**Files**:
- `orchestrator/mesh.py` — MeshCoordinator
- `orchestrator/gateway_adapter.py` — Transport adapters
- `orchestrator/mesh_encryption.py` — Message encryption
- `orchestrator/mesh_failover.py` — Failover handling
- `orchestrator/mesh_relay.py` — Message relay

---

## MeshCoordinator

Main mesh topology manager.

```python
class MeshCoordinator:
    def __init__(
        self,
        validator: ContractValidator,
        squad_id: str = "",
        mesh_dir: str | None = None,
        mesh_config: MeshConfig | None = None,
    ): ...

    def register_claw(self, role: str, address: str) -> None: ...
    def send_message(self, message: ClawMessage) -> DeliveryResult: ...
    def topology(self) -> dict[str, ClawNode]: ...
```

### ClawNode

```python
@dataclass
class ClawNode:
    role: str
    address: str
    status: str  # online, offline, unhealthy, finals-mode
    registered_at: str
    last_heartbeat: str
    consecutive_failures: int
```

### DeliveryResult

```python
@dataclass
class DeliveryResult:
    delivered: bool
    reason: str
    message_id: str
    requires_approval: bool
```

---

## Gateway Adapters

### Transport Modes

| Mode | Class | Use Case |
|------|-------|----------|
| `file` | `FileBasedGateway` | Development, fallback |
| `unix` | `UnixSocketGateway` | Single host via OpenShell |
| `websocket` | `WebSocketGateway` | Multi-host via OpenShell |

### GatewayAdapter Interface

```python
class GatewayAdapter:
    def connect(self) -> bool: ...
    def disconnect(self) -> None: ...
    def send(self, message: ClawMessage) -> bool: ...
    def receive(self) -> ClawMessage | None: ...
    def health_check(self) -> bool: ...
```

### FileBasedGateway

Uses filesystem for message queues:

```
~/.milimo/mesh/
├── inbox/{role}/      # Incoming messages
├── outbox/{role}/     # Outgoing messages
├── delivered/         # Successfully delivered
└── rejected/          # Failed deliveries
```

### UnixSocketGateway

Connects via Unix domain socket to OpenShell gateway:

```python
class UnixSocketGateway(GatewayAdapter):
    def __init__(self, socket_path: str = "/var/run/milimo/mesh.sock"): ...
```

### WebSocketGateway

Connects via WebSocket for multi-host:

```python
class WebSocketGateway(GatewayAdapter):
    def __init__(self, endpoint: str, squad_id: str): ...
```

---

## Mesh Encryption

### Message Encryption

All mesh messages encrypted using squad secret:

```python
class MeshEncryption:
    def __init__(self, mesh_secret: str): ...

    def encrypt(self, message: dict) -> str: ...
    def decrypt(self, encrypted: str) -> dict: ...
```

### Key Derivation

Uses PBKDF2 to derive encryption key from mesh_secret:

```python
key = PBKDF2(
    mesh_secret,
    salt=squad_id.encode(),
    iterations=100000,
    dkLen=32
)
```

---

## Mesh Failover

### Failover Handling

When a claw becomes unhealthy:

```python
class MeshFailover:
    def check_health(self, role: str) -> HealthStatus: ...
    def trigger_failover(self, role: str) -> None: ...
    def get_backup_node(self, role: str) -> ClawNode | None: ...
```

### Health Status

```python
@dataclass
class HealthStatus:
    role: str
    status: str  # healthy, degraded, failed
    last_heartbeat: str
    consecutive_failures: int
    failover_recommended: bool
```

### Failover Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Heartbeat age | > 90 seconds | Mark unhealthy |
| Consecutive failures | > 3 | Trigger failover |
| Gateway disconnect | Immediate | Queue messages locally |

---

## Mesh Relay

### Message Relay

Relays messages between transport modes:

```python
class MeshRelay:
    def relay(
        self,
        message: ClawMessage,
        from_transport: TransportMode,
        to_transport: TransportMode,
    ) -> bool: ...
```

### Relay Use Cases

- File → Unix: When gateway becomes available
- Unix → WebSocket: When switching to multi-host
- WebSocket → File: Fallback when network unavailable

---

## MeshConfig

```python
@dataclass
class MeshConfig:
    mesh_secret: str = ""
    gateway_endpoint: str = ""  # unix://, tcp://, ws://
    transport_mode: TransportMode = "file"
    timeout_ms: int = 5000
```

---

## Message Flow

```
Sender Claw
    │
    ▼
ContractValidator.validate(message)
    │
    ▼
MeshEncryption.encrypt(message)
    │
    ▼
GatewayAdapter.send(message)
    │
    ▼
OpenShell Gateway (or file queue)
    │
    ▼
Recipient Claw InboxPoller
    │
    ▼
MeshEncryption.decrypt(message)
    │
    ▼
claw.handle_inbound(message)
```

---

## File Storage

```
~/.milimo/mesh/
├── inbox/
│   ├── content/
│   ├── ops/
│   ├── analytics/
│   ├── finance/
│   └── build/
├── outbox/
│   └── {role}/
├── delivered/
├── rejected/
├── heartbeats/
│   └── {role}.json
└── alerts/
```

---

## Dependencies

- [[contracts]] — Message validation
- [[privacy-router]] — Inference routing
- OpenShell gateway — Transport layer

## Related Pages

- [[mesh-coordinator]] — Main mesh documentation
- [[contracts]] — Message schemas
- [[inter-claw-communication]] — Communication overview
- [[claw-launcher]] — Inbox/outbox polling
