# Mesh Failover

**Summary**: Handles failover scenarios for the multi-region mesh.

**Sources**:
- `milimo-blueprint/orchestrator/mesh_failover.py`

**Last updated**: 2026-04-17

**Tags**: #module #mesh #failover #reliability

---

## Overview

FailoverManager detects node failures, region isolation, and network partitions. Implements automatic recovery and split-brain resolution.

---

## Key Class

### `FailoverManager`

```python
class FailoverManager:
    def __init__(
        self,
        mesh_coordinator: Any,
        heartbeat_interval: float = 5.0,
        failure_threshold: int = 3,
    ) -> None:
        ...
```

---

## States

### `FailoverState`

```python
class FailoverState(str, Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    FAILOVER_ACTIVE = "failover_active"
    PARTITION = "partition"
    RECOVERING = "recovering"
```

### `FailoverEvent`

```python
class FailoverEvent(str, Enum):
    NODE_OFFLINE = "node_offline"
    NODE_ONLINE = "node_online"
    REGION_ISOLATED = "region_isolated"
    REGION_RECOVERED = "region_recovered"
    PARTITION_DETECTED = "partition_detected"
    PARTITION_HEALED = "partition_healed"
    RELAY_CONNECTED = "relay_connected"
    RELAY_DISCONNECTED = "relay_disconnected"
```

---

## Data Classes

### `NodeHealth`

```python
@dataclass
class NodeHealth:
    role: str
    region: str
    status: str  # online, offline, unhealthy, recovering
    last_heartbeat: str
    consecutive_failures: int
    last_failure_reason: str = ""
    recovery_attempts: int = 0
```

---

## Failover Scenarios

| Event | Action |
|-------|--------|
| Node offline | Mark unhealthy, route around |
| Region isolated | Activate relay fallback |
| Partition detected | Enter split-brain mode |
| Partition healed | Merge state, recover |

---

## Integration

### With MeshCoordinator

```python
# In mesh.py
failover = FailoverManager(self)
failover.start()

# Check state
if failover.state == FailoverState.FAILOVER_ACTIVE:
    use_relay_fallback()
```

---

## Recovery Process

1. **Detect failure** — Missed heartbeats
2. **Mark unhealthy** — Route around node
3. **Attempt recovery** — Reconnect attempts
4. **Resume normal** — When heartbeat resumes

---

## Related Pages

- [[mesh-coordinator]] — Mesh overview
- [[mesh-encryption]] — Message encryption
- [[mesh-relay]] — Relay server
