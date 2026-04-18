# Latency Monitor

**Summary**: Tracks inter-region latency for mesh routing decisions with continuous measurement and historical aggregation.

**Sources**: `milimo-blueprint/orchestrator/latency_monitor.py`

**Last updated**: 2026-04-15

**Tags**: #module #operations #latency #network

---

## Overview

`LatencyMonitor` probes regional endpoints to measure network latency, providing routing recommendations and degradation alerts.

**File**: `orchestrator/latency_monitor.py`

---

## Key Classes

### `LatencySample`

Single latency measurement.

| Field | Type | Description |
|-------|------|-------------|
| source_region | str | Source region |
| target_region | str | Target region |
| latency_ms | float | Latency in milliseconds |
| packet_loss | float | Loss rate (0-1) |
| jitter_ms | float | Latency variance |
| success | bool | Probe success |

### `LatencyStats`

Aggregated statistics.

| Field | Type | Description |
|-------|------|-------------|
| min_ms | float | Minimum latency |
| max_ms | float | Maximum latency |
| mean_ms | float | Mean latency |
| median_ms | float | Median latency |
| p95_ms | float | 95th percentile |
| p99_ms | float | 99th percentile |
| std_dev | float | Standard deviation |
| packet_loss_rate | float | Loss rate |

---

### `LatencyMonitor`

Main monitor class.

```python
monitor = LatencyMonitor(region="us-east-1")
monitor.start()

# Get latency to region
latency = monitor.get_latency("eu-west-1")
print(f"Latency: {latency:.2f}ms")

# Get statistics
stats = monitor.get_stats("eu-west-1")

# Get latency matrix
matrix = monitor.get_matrix()

# Find optimal route
route = monitor.get_optimal_route("ap-southeast-1")
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `start()` | Begin background monitoring |
| `stop()` | Stop monitoring |
| `get_latency(target)` | Get current latency |
| `get_stats(target)` | Get aggregated stats |
| `get_matrix()` | Get full latency matrix |
| `get_optimal_route(target)` | Find best route |
| `is_region_healthy(target)` | Health check |

---

## Default Regions

```python
DEFAULT_REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
    "ap-northeast-1",
    "sa-east-1",
]
```

---

## Probe Endpoints

Each region has a `/health` endpoint for probing:

```
https://{region}.endpoint.milimo.dev/health
```

---

## Routing Optimization

Direct routing preferred if latency < 500ms. Otherwise, find intermediate hop:

```python
# Direct route if fast enough
us-east-1 → eu-west-1 (if latency < 500ms)

# Intermediate route if slow
us-east-1 → eu-central-1 → eu-west-1
```

---

## Storage

Historical data: `~/.milimo/latency/latency_{region}.json`

---

## Integration Points

- **Input**: Regional health endpoints
- **Output**: Mesh routing decisions
- **Used by**: [[mesh-coordinator]]

---

## Related Pages

- [[health-collector]] — Health monitoring
- [[mesh-coordinator]] — Mesh routing
- [[metrics-collector]] — Performance metrics

---

## See Also

- `orchestrator/health_collector.py` — Health monitoring
- `orchestrator/mesh_coordinator.py` — Mesh coordination
