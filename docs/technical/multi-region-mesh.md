# Multi-Region Mesh Topology

**Version:** 1.0
**Date:** March 18, 2026
**Author:** Milimo Claw Team

---

## Overview

This document describes the multi-region mesh architecture that enables squad members in different geographic regions to participate in the same mesh. The design addresses NAT traversal, latency optimization, failover, and network partition recovery.

---

## Problem Statement

In Phase 3, the mesh coordinator supports:
- File-based queues (development)
- Unix sockets (single host)
- WebSockets (multi-host on same network)

Phase 4 extends this to support:
- Squad members in different AWS regions (us-east-1, eu-west-1, ap-southeast-1)
- NAT traversal for members behind firewalls
- Automatic relay selection based on latency
- Graceful failover when nodes disconnect

---

## Architecture

### Topology Model

```
                    ┌─────────────────┐
                    │   Relay Server   │
                    │  (Optional)      │
                    │  Public Endpoint │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────┴────┐        ┌─────┴─────┐       ┌─────┴─────┐
    │ Region A │        │ Region B  │       │ Region C  │
    │ us-east-1│        │ eu-west-1 │       │ ap-southeast-1
    └────┬────┘        └─────┬─────┘       └─────┬─────┘
         │                   │                   │
    ┌────┴────┐        ┌─────┴─────┐       ┌─────┴─────┐
    │ content │        │  ops      │       │  finance  │
    │   claw  │        │   claw    │       │   claw    │
    └─────────┘        └───────────┘       └───────────┘
```

### Connection Modes

| Mode | Use Case | Requirements |
|------|----------|--------------|
| **Direct P2P** | Low latency, same region | Public IP or port forwarding |
| **Relayed** | NAT traversal | Relay server with public IP |
| **Hybrid** | Mixed environments | Automatic mode selection |

---

## Components

### 1. Region Detector

Determines the optimal region for a claw based on:
- IP geolocation
- Latency probes to known endpoints
- Manual configuration

```python
class RegionInfo:
    region_id: str          # e.g., "us-east-1"
    region_code: str        # e.g., "use1"
    country: str            # e.g., "US"
    latency_samples: dict   # {region_id: [latency_ms, ...]}
    preferred_relay: str    # Optimal relay endpoint
```

### 2. Latency Monitor

Tracks inter-region latency for routing decisions:

```python
class LatencySample:
    source_region: str
    target_region: str
    latency_ms: float
    timestamp: datetime
    packet_loss: float      # 0.0 to 1.0
```

### 3. Mesh Relay

Optional relay server for NAT traversal:

```
┌─────────────────────────────────────────────────────────────┐
│                     Relay Server                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Connection  │  │  Message     │  │  Health      │       │
│  │  Manager     │  │  Router      │  │  Monitor     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  Endpoints:                                                  │
│  - wss://relay.milimo.dev:443 (public)                      │
│  - TCP 9000 (region-to-region)                              │
└─────────────────────────────────────────────────────────────┘
```

### 4. Failover Manager

Handles node disconnection scenarios:

| Scenario | Action |
|----------|--------|
| Single claw offline | Mark as offline, queue messages |
| Region isolated | Activate relay, reroute through alternate region |
| Relay failure | Fall back to direct P2P or queue locally |
| Network partition | Split-brain resolution via version vectors |

---

## Message Routing

### Routing Algorithm

```
1. Determine recipient region
2. If same region → Direct delivery via WebSocket
3. If different region:
   a. Check latency matrix for optimal path
   b. If relay available and lower latency → Route via relay
   c. If direct path available → Direct delivery
   d. If neither → Queue locally, retry on reconnection
```

### Routing Table Structure

```python
@dataclass
class RouteEntry:
    destination_region: str
    next_hop: str              # Direct endpoint or relay
    latency_ms: float
    reliability: float         # 0.0 to 1.0
    last_updated: datetime
    is_relay: bool
```

---

## Failover Scenarios

### Scenario 1: Single Node Failure

```
Before:                     After:
┌───────┐                   ┌───────┐
│ A ────┼─── B              │ A     │   B (offline)
│   ╲   │                   │   ╲   │
│    ╲  │                   │    ╲  │
│     ╲ │                   │     ╲ │
│      ╲│                   │      ╲│
│       C                   │       C
└───────┘                   └───────┘

Actions:
1. B marked as offline
2. Messages to B queued
3. Mesh continues with A and C
4. On B reconnection, replay queued messages
```

### Scenario 2: Region Isolation

```
Before:                     After:
┌───────────┐               ┌───────────┐
│ Region A  │               │ Region A  │
│  ┌───┐    │               │  ┌───┐    │
│  │ A │    │               │  │ A │    │
│  └───┘    │               │  └───┘    │
│     │     │               │     │     │
│     ▼     │               │     ▼     │
│  ┌───┐    │               │  ┌───┐    │
│  │ B │────┼─── Region B   │  │Rel│    │   Region B
│  └───┘    │   (isolated)  │  │ay │────┼─── (isolated)
└───────────┘               └───┴───┘

Actions:
1. Detect region B isolation (heartbeat timeout)
2. Activate relay connection for region A
3. Route traffic through relay
4. Region B members connect to relay if available
5. On recovery, switch back to direct
```

### Scenario 3: Network Partition (Split Brain)

```
Partition:         ┌───────┐        ┌───────┐
                   │ A ────┼─── X ──┼─── B  │
                   │   ╲   │        │   ╱   │
                   │    ╲  │        │  ╱    │
                   │     ╲ │        │ ╱     │
                   │      ╲│        │╱      │
                   │       C        │       │
                   └───────┘        └───────┘
                   Partition point

Resolution:
1. Each partition continues independently
2. Version vectors track message order
3. On healing, merge using vector clocks
4. Conflicts resolved by:
   - Timestamp (last write wins)
   - Manual resolution for critical conflicts
```

---

## Configuration

### Region Configuration

```yaml
# milimo-blueprint/regions.yaml
regions:
  us-east-1:
    code: use1
    endpoint: wss://us-east-1.mesh.milimo.dev
    relay: wss://relay-use1.milimo.dev:443
    fallback_region: eu-west-1

  eu-west-1:
    code: euw1
    endpoint: wss://eu-west-1.mesh.milimo.dev
    relay: wss://relay-euw1.milimo.dev:443
    fallback_region: us-east-1

  ap-southeast-1:
    code:apse1
    endpoint: wss://ap-southeast-1.mesh.milimo.dev
    relay: wss://relay-apse1.milimo.dev:443
    fallback_region: eu-west-1
```

### Mesh Configuration Extension

```yaml
# milimo-blueprint/mesh_config.yaml
mesh:
  region: auto              # auto-detect or explicit region
  relay_mode: auto          # auto, always, never
  failover:
    heartbeat_timeout_ms: 10000
    reconnect_attempts: 5
    reconnect_delay_ms: 2000
  latency:
    probe_interval_ms: 30000
    sample_window: 10
```

---

## Security Considerations

### Authentication

1. **Region Tokens**: JWT tokens signed by mesh secret, scoped to region
2. **Relay Authentication**: Mutual TLS (mTLS) for relay connections
3. **Message Signing**: All inter-region messages signed with Ed25519

### Encryption

- TLS 1.3 for all WebSocket connections
- End-to-end encryption for message payloads
- Perfect forward secrecy (PFS) for key exchange

### Access Control

- Region-level ACLs for inter-region routing
- Rate limiting per region (防止 DDoS)
- Audit logging for cross-region messages

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Inter-region latency | < 500ms | 95th percentile |
| Failover time | < 10s | Detection to reroute |
| Message delivery | 99.9% | Success rate |
| Partition recovery | < 30s | Merge completion |

---

## Implementation Phases

### Phase 4.1.1: Region Detection
- IP geolocation lookup
- Latency probing infrastructure
- Region configuration loading

### Phase 4.1.2: Relay Nodes
- Relay server implementation
- Client relay connection handling
- NAT traversal (STUN/TURN concepts)

### Phase 4.1.3: Latency Monitoring
- Continuous latency measurement
- Historical data aggregation
- Routing decision integration

### Phase 4.1.4: Failover Logic
- Health check monitoring
- Automatic route recalculation
- Split-brain detection and resolution

---

## Monitoring and Observability

### Metrics

```
# Inter-region latency
milimo_mesh_latency_ms{source="us-east-1", target="eu-west-1"}

# Message delivery
milimo_mesh_messages_total{status="delivered|queued|failed"}

# Failover events
milimo_mesh_failover_total{type="node|region|partition"}

# Relay connections
milimo_mesh_relay_connections{state="active|fallback"}
```

### Alerts

- Inter-region latency > 500ms for 5 minutes
- Node offline > 30 seconds
- Relay connection failures > 3 in 5 minutes
- Unresolved network partition

---

## References

- [OpenShell IPC Documentation](./openshell-ipc.md)
- [AWS Region Latency Matrix](https://aws-latency.com)
- [WebRTC NAT Traversal](https://webrtc.org/getting-started/overview)
