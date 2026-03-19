# Phase 4 Features — Scale & Distribution

**Version:** 1.0
**Date:** March 18, 2026
**Status:** Complete

---

## Overview

Phase 4 introduces scale and distribution capabilities, enabling Milimo Claw to operate across geographic regions and provide mobile access to the War Room.

---

## Multi-Region Mesh Support

### Region Detection

Automatic detection of optimal region based on:
- IP geolocation lookup
- Latency probing to known endpoints
- Manual configuration via `MILIMO_REGION` environment variable

```bash
# Set region manually
export MILIMO_REGION=eu-west-1
```

### Supported Regions

| Region | Code | Location |
|--------|------|----------|
| us-east-1 | use1 | Northern Virginia |
| us-west-2 | usw2 | Oregon |
| eu-west-1 | euw1 | Ireland |
| eu-central-1 | euc1 | Frankfurt |
| ap-southeast-1 | apse1 | Singapore |
| ap-northeast-1 | apne1 | Tokyo |
| sa-east-1 | sae1 | São Paulo |

### Latency Monitoring

Continuous latency tracking with:
- Background probing to all regions
- P95/P99 latency metrics
- Optimal route calculation

```python
from orchestrator.latency_monitor import LatencyMonitor

monitor = LatencyMonitor(region="us-east-1")
monitor.start()

latency = monitor.get_latency("eu-west-1")
route = monitor.get_optimal_route("ap-southeast-1")
```

### Relay Server

NAT traversal support for squad members behind firewalls:
- Public relay endpoint for message routing
- Mutual TLS authentication
- Automatic failover to relay when direct P2P unavailable

```python
from orchestrator.mesh_relay import RelayClient, RelayConfig

config = RelayConfig(
    relay_url="wss://relay.milimo.dev:443",
    squad_id="my-squad",
    role="content",
)

client = RelayClient(config)
client.connect()
client.send("ops", message)
```

### Failover & Split-Brain Resolution

Automatic failover handling:
- Node disconnection detection (heartbeat timeout)
- Region isolation handling
- Network partition recovery via version vectors

```python
from orchestrator.mesh_failover import FailoverManager, FailoverState

manager = FailoverManager(mesh_coordinator)
manager.start()

if manager.state == FailoverState.FAILOVER_ACTIVE:
    print("Operating in failover mode")
```

---

## Mobile War Room Companion

### REST API

Complete REST API for mobile access:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/token` | POST | Generate auth token |
| `/api/v1/pending` | GET | List pending actions |
| `/api/v1/pending/:id` | GET | Get action details |
| `/api/v1/pending/:id/approve` | POST | Approve action |
| `/api/v1/pending/:id/veto` | POST | Veto action |
| `/api/v1/status` | GET | Squad status |
| `/api/v1/status/claws` | GET | Claw health |

### WebSocket API

Real-time updates via WebSocket:

```javascript
const ws = new WebSocket('wss://warroom.milimo.dev/ws', {
  headers: { 'Authorization': 'Bearer <token>' }
});

ws.send(JSON.stringify({ type: 'subscribe', channel: 'pending' }));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'pending:new') {
    // New pending action received
  }
};
```

### Push Notifications

Firebase Cloud Messaging (FCM) and Apple Push Notification Service (APNs) integration:

| Notification Type | Priority |
|-------------------|----------|
| Pending action (high risk) | High |
| Pending action (normal) | Normal |
| Action approved | Normal |
| Action vetoed | Normal |
| Claw offline | High |
| Rate limit warning | High |

### Biometric Authentication

Challenge-response biometric verification for high-risk actions:

```typescript
import { generateChallenge, verifyBiometric } from './auth/biometric';

const challenge = generateChallenge(deviceId);
// User verifies with Face ID / Touch ID
const verified = verifyBiometric({
  device_id: deviceId,
  challenge: challenge.challenge,
  signature: userSignature,
});
```

### React Native Mobile App

Cross-platform mobile app (iOS + Android):

```
milimo-mobile/
├── src/
│   ├── App.tsx              # Main navigation
│   ├── screens/
│   │   ├── PendingList.tsx  # Pending actions list
│   │   ├── ActionDetail.tsx # Action details & approve/veto
│   │   └── Settings.tsx     # App settings
│   ├── components/
│   │   └── ActionCard.tsx   # Action card component
│   ├── hooks/
│   │   └── useAuth.ts       # Authentication hook
│   └── api/
│       └── warroom.ts       # War Room API client
```

---

## Real-Time Health Monitoring

### Health Score Calculation

Overall health score is a weighted average of 5 metrics:

| Metric | Weight | Description |
|--------|--------|-------------|
| Heartbeat Latency | 30% | Response time for health pings |
| Message Throughput | 25% | Messages processed per minute |
| Evolution Status | 20% | Last evolution cycle success |
| Approval Backlog | 15% | Pending actions in queue |
| Error Rate | 10% | Failed operations per hour |

### Health Status Levels

| Score | Status | Icon |
|-------|--------|------|
| 90-100% | Healthy | 🟢 |
| 70-89% | Good | 🟡 |
| 50-69% | Fair | 🟠 |
| 30-49% | Degraded | 🔴 |
| 0-29% | Critical | ⚫ |

### CLI Health Command

```bash
# Show health overview
milimo health

# Show detailed health
milimo health --detailed

# Watch mode (continuous updates)
milimo health --watch

# Collect fresh data
milimo health --collect

# JSON output
milimo health --json
```

### Health Dashboard

Programmatic health dashboard:

```typescript
import { HealthDashboard } from './warroom/health-dashboard';

const dashboard = new HealthDashboard('my-squad');
dashboard.start(5000); // Update every 5 seconds

dashboard.on('update', (health) => {
  console.log(`Overall: ${health.overall_score}`);
});

dashboard.on('alert', (alert) => {
  console.log(`ALERT: ${alert.message}`);
});
```

### Alert Generation

Automatic alerts on health degradation:

| Alert Level | Condition | Notification |
|-------------|-----------|--------------|
| Warning | Score 50-69% | Dashboard |
| Critical | Score < 30% | Dashboard + Push |
| Offline | No heartbeat | Dashboard + Push + Sound |

---

## Configuration

### Regions Configuration

```yaml
# milimo-blueprint/regions.yaml
regions:
  us-east-1:
    code: use1
    endpoint: wss://us-east-1.mesh.milimo.dev:443
    relay: wss://relay-use1.milimo.dev:443
    fallback_region: eu-west-1
```

### Health Collection Settings

```yaml
# In mesh_config.yaml
health:
  collection_interval_ms: 10000
  heartbeat_timeout_ms: 30000
  alert_threshold_score: 50
```

---

## API Reference

### Python Modules

| Module | Key Classes |
|--------|-------------|
| `mesh_relay` | `RelayClient`, `MeshRelay`, `RelayConfig` |
| `region_detector` | `RegionDetector`, `RegionInfo` |
| `latency_monitor` | `LatencyMonitor`, `LatencyStats`, `LatencyMatrix` |
| `mesh_failover` | `FailoverManager`, `FailoverState`, `VersionVector` |
| `health_collector` | `HealthCollector`, `HealthScorer`, `ClawHealth` |

### TypeScript Modules

| Module | Key Exports |
|--------|-------------|
| `health.ts` | `healthCommand` CLI |
| `health-dashboard.ts` | `HealthDashboard`, `createHealthWidget` |
| `firebase.ts` | `FirebasePushService`, notification creators |
| `apns.ts` | `APNsService`, notification creators |
| `jwt.ts` | `generateToken`, `verifyToken` |
| `biometric.ts` | `generateChallenge`, `verifyBiometric` |

---

## Testing

### Integration Tests

```bash
# Run all integration tests
node --test test/integration/*.test.js

# Run multi-region tests only
node --test test/integration/multi-region.test.js
```

### Test Coverage

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| Multi-Region Mesh | 13 | Region detection, latency, failover, relay |
| Health Monitoring | - | Health collection, scoring, alerts |

---

## Monitoring

### Prometheus Metrics

```
milimo_claw_health_score{role="content"} 95.2
milimo_claw_heartbeat_latency_ms{role="content"} 45.2
milimo_claw_message_throughput{role="content"} 12
milimo_mesh_latency_ms{source="us-east-1",target="eu-west-1"} 85
milimo_mesh_failover_total{type="node"} 0
```

### Grafana Dashboard

Import the pre-built dashboard from `monitoring/grafana-dashboard.json`.

---

## Next Steps

Phase 5 (Blueprint Economy) will add:
- Real payment processing
- Cryptographic provenance verification
- Performance attestation
