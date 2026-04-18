# Health Collector

**Summary**: Collects and aggregates health metrics from all squad claws for real-time monitoring and alerting.

**Sources**: `milimo-blueprint/orchestrator/health_collector.py`

**Last updated**: 2026-04-15

**Tags**: #module #operations #health #monitoring

---

## Overview

`HealthCollector` runs background health checks on all claws, calculating health scores and generating alerts for degraded or offline claws.

**File**: `orchestrator/health_collector.py`

---

## Key Classes

### `HealthStatus`

Health status levels (enum).

| Status | Score Range |
|--------|-------------|
| HEALTHY | 90-100 |
| GOOD | 70-89 |
| FAIR | 50-69 |
| DEGRADED | 30-49 |
| CRITICAL | 0-29 |
| OFFLINE | N/A |

### `ClawHealthMetrics`

Metrics for a single claw.

| Metric | Type | Description |
|--------|------|-------------|
| heartbeat_latency_ms | float | Time since last heartbeat |
| message_throughput_per_min | float | Messages processed |
| evolution_status | str | Evolution cycle status |
| approval_backlog | int | Pending approvals |
| error_rate_per_hour | float | Errors per hour |

### `HealthScorer`

Calculates health scores with weighted components:

| Component | Weight |
|-----------|--------|
| heartbeat_latency | 30% |
| message_throughput | 25% |
| evolution_status | 20% |
| approval_backlog | 15% |
| error_rate | 10% |

---

### `HealthCollector`

Main collector class.

```python
collector = HealthCollector(mesh_coordinator)
collector.start()

# Get single claw health
health = collector.get_claw_health("content")
print(f"Status: {health.status}, Score: {health.score}")

# Get squad health
squad = collector.get_squad_health()
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `start()` | Begin background collection |
| `stop()` | Stop collection |
| `get_claw_health(role)` | Get claw health |
| `get_squad_health()` | Get overall squad health |
| `get_alerts()` | Current alerts |

---

## Scoring Logic

### Heartbeat Latency

| Latency | Score |
|---------|-------|
| < 100ms | 100 |
| < 500ms | 90 |
| < 1000ms | 70 |
| < 5000ms | 40 |
| > 5000ms | 0 |

### Evolution Status

| Status | Score |
|--------|-------|
| success | 100 |
| success_24h | 100 |
| success_48h | 80 |
| success_7d | 60 |
| skipped | 50 |
| failed_recoverable | 30 |
| failed_critical | 0 |

---

## Storage

Health data persisted to: `~/.milimo/health/health.json`

---

## Integration Points

- **Input**: Mesh coordinator topology
- **Output**: Alerts, health dashboard
- **Used by**: [[mesh-coordinator]], War Room

---

## Related Pages

- [[metrics-collector]] — Performance metrics
- [[latency-monitor]] — Network latency
- [[mesh-coordinator]] — Mesh topology
- [[war-room]] — Alert display

---

## See Also

- `orchestrator/metrics_collector.py` — Metrics collection
- `orchestrator/latency_monitor.py` — Latency tracking
