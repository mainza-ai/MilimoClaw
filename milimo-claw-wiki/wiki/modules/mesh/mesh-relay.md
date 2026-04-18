# Mesh Relay

**Summary**: Relay server for NAT traversal and cross-region communication.

**Sources**:
- `milimo-blueprint/orchestrator/mesh_relay.py`

**Last updated**: 2026-04-17

**Tags**: #module #mesh #relay #networking

---

## Overview

MeshRelay provides relay server functionality for NAT traversal. Enables squad members behind firewalls to participate in the mesh through a public relay endpoint.

---

## Key Classes

### `MeshRelay` (Server Mode)

```python
class MeshRelay:
    def __init__(
        self,
        port: int = 443,
        tls_cert: str | None = None,
        tls_key: str | None = None,
        max_connections: int = 100,
    ) -> None:
        ...
```

### `RelayClient` (Client Mode)

```python
class RelayClient:
    def __init__(self, config: RelayConfig) -> None:
        ...
```

---

## States

### `RelayState`

```python
class RelayState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    READY = "ready"
    ERROR = "error"
```

---

## Data Classes

### `RelayConfig`

```python
@dataclass
class RelayConfig:
    relay_url: str = ""
    mesh_secret: str = ""
    squad_id: str = ""
    role: str = ""
    region: str = ""
    timeout_ms: int = 10000
    reconnect_attempts: int = 5
    reconnect_delay_ms: int = 2000
    heartbeat_interval_ms: int = 30000
    max_connections: int = 100
```

### `RelayConnection`

```python
@dataclass
class RelayConnection:
    connection_id: str
    squad_id: str
    role: str
    region: str
    connected_at: str
    last_activity: str
```

---

## Usage

### Server Mode

```python
from orchestrator.mesh_relay import MeshRelay

relay = MeshRelay(
    port=443,
    tls_cert="/path/to/cert.pem",
    tls_key="/path/to/key.pem"
)
relay.start()
```

### Client Mode

```python
from orchestrator.mesh_relay import RelayClient, RelayConfig

config = RelayConfig(
    relay_url="wss://relay.milimo.dev:443",
    mesh_secret="secret",
    squad_id="my-squad",
    role="content"
)
client = RelayClient(config)
client.connect()
```

---

## Integration

### With FailoverManager

```python
# When region isolated
failover.activate_relay(relay_url)
client = RelayClient(config)
client.connect()
```

### With GatewayClient

```python
# TypeScript can use relay
gateway.setRelayUrl("wss://relay.milimo.dev:443")
```

---

## Related Pages

- [[mesh-coordinator]] — Mesh overview
- [[mesh-encryption]] — Message encryption
- [[mesh-failover]] — Failover handling
- [[mesh-gateway-client]] — TypeScript client
