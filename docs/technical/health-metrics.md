# Health Metrics Specification

**Version:** 1.0
**Date:** March 18, 2026
**Author:** Milimo Claw Team

---

## Overview

This document defines the health metrics and scoring system for real-time monitoring of squad claws in the mesh.

---

## Health Score Calculation

### Overall Health Score

The overall health score for each claw is a weighted average of individual metrics:

```
health_score = Σ(metric_value × weight) / Σ(weights)
```

### Metric Weights

| Metric | Weight | Description |
|--------|--------|-------------|
| Heartbeat Latency | 30% | Response time for health pings |
| Message Throughput | 25% | Messages processed per minute |
| Evolution Status | 20% | Last evolution cycle success |
| Approval Backlog | 15% | Pending actions in queue |
| Error Rate | 10% | Failed operations per hour |

---

## Individual Metrics

### 1. Heartbeat Latency (30%)

Measures the response time for health check pings.

| Latency | Score | Status |
|---------|-------|--------|
| < 100ms | 100% | Excellent |
| 100-500ms | 90% | Good |
| 500ms-1s | 70% | Fair |
| 1s-5s | 40% | Degraded |
| > 5s | 0% | Critical |

```python
def score_heartbeat_latency(latency_ms: float) -> float:
    if latency_ms < 100:
        return 100.0
    elif latency_ms < 500:
        return 90.0
    elif latency_ms < 1000:
        return 70.0
    elif latency_ms < 5000:
        return 40.0
    else:
        return 0.0
```

### 2. Message Throughput (25%)

Messages processed per minute relative to expected capacity.

| Throughput | Score | Status |
|------------|-------|--------|
| > 100% capacity | 100% | Excellent |
| 80-100% | 90% | Good |
| 50-80% | 70% | Fair |
| 20-50% | 40% | Degraded |
| < 20% | 20% | Critical |

```python
def score_throughput(current: int, capacity: int) -> float:
    ratio = current / capacity
    if ratio > 1.0:
        return 100.0
    elif ratio > 0.8:
        return 90.0
    elif ratio > 0.5:
        return 70.0
    elif ratio > 0.2:
        return 40.0
    else:
        return 20.0
```

### 3. Evolution Status (20%)

Status of the last evolution cycle.

| Status | Score |
|--------|-------|
| Success (within 24h) | 100% |
| Success (within 48h) | 80% |
| Success (within 7d) | 60% |
| Skipped (insufficient data) | 50% |
| Failed (recoverable) | 30% |
| Failed (critical) | 0% |
| Never run | 40% |

### 4. Approval Backlog (15%)

Number of pending actions waiting for approval.

| Backlog | Score | Status |
|---------|-------|--------|
| 0 | 100% | Excellent |
| 1-5 | 90% | Good |
| 6-10 | 70% | Fair |
| 11-20 | 50% | Warning |
| > 20 | 20% | Critical |

```python
def score_backlog(count: int) -> float:
    if count == 0:
        return 100.0
    elif count <= 5:
        return 90.0
    elif count <= 10:
        return 70.0
    elif count <= 20:
        return 50.0
    else:
        return 20.0
```

### 5. Error Rate (10%)

Failed operations per hour.

| Error Rate | Score | Status |
|------------|-------|--------|
| 0 | 100% | Excellent |
| 1-5/hour | 80% | Good |
| 6-10/hour | 60% | Fair |
| 11-20/hour | 30% | Warning |
| > 20/hour | 0% | Critical |

---

## Health Status Levels

### Overall Status

| Score Range | Status | Color |
|-------------|--------|-------|
| 90-100% | Healthy | 🟢 Green |
| 70-89% | Good | 🟡 Yellow |
| 50-69% | Fair | 🟠 Orange |
| 30-49% | Degraded | 🔴 Red |
| 0-29% | Critical | ⚫ Black |

### Alert Thresholds

| Status | Alert Level | Notification |
|--------|-------------|--------------|
| Healthy | None | None |
| Good | Info | Log only |
| Fair | Warning | Dashboard |
| Degraded | Error | Dashboard + Push |
| Critical | Critical | Dashboard + Push + Sound |

---

## Data Collection

### Collection Intervals

| Metric | Collection Interval | Storage |
|--------|-------------------|---------|
| Heartbeat Latency | 10s | Rolling 5min |
| Message Throughput | 60s | Rolling 1hour |
| Evolution Status | On cycle | Latest |
| Approval Backlog | 30s | Latest |
| Error Rate | 60s | Rolling 24hour |

### Aggregation

```python
@dataclass
class HealthSample:
    claw_role: str
    metric_type: str
    value: float
    timestamp: datetime
    labels: dict[str, str]  # region, squad_id, etc.
```

### Storage Format

```json
{
  "claw_role": "content",
  "squad_id": "my-squad",
  "timestamp": "2026-03-18T10:00:00Z",
  "metrics": {
    "heartbeat_latency_ms": 45.2,
    "message_throughput_per_min": 12,
    "evolution_status": "success",
    "approval_backlog": 3,
    "error_rate_per_hour": 1
  },
  "health_score": 89.5,
  "status": "good"
}
```

---

## Dashboard Display

### Claw Health Card

```
┌─────────────────────────────────────┐
│  Content Claw          🟢 Healthy   │
│  Region: us-east-1                  │
│  Score: 95.2                        │
│  ─────────────────────────────────  │
│  Heartbeat:    45ms      ████████   │
│  Throughput:   12/min    ████████   │
│  Evolution:    Success   █████████  │
│  Backlog:      3 items   ███████    │
│  Errors:       1/hour    ████████   │
└─────────────────────────────────────┘
```

### Squad Health Overview

```
┌──────────────────────────────────────────────────────────┐
│  Squad Health Overview                                   │
│  ─────────────────────────────────────────────────────── │
│  Overall: 87.5 (Good)                                    │
│  ─────────────────────────────────────────────────────── │
│  🟢 content    95.2  Healthy   us-east-1                 │
│  🟡 ops        78.3  Good      eu-west-1                 │
│  🟢 finance    92.1  Healthy   us-east-1                 │
│  🟠 build      62.5  Fair      ap-southeast-1            │
│  ⚫ ops_admin  15.0  Critical  us-west-2 (offline)       │
└──────────────────────────────────────────────────────────┘
```

### Trend Visualization

```
Health Score Trend (24h)
100 ├────────────────────────────────────────┤
 90 ├─────────╮                              │
 80 ├─────────┴───────────────────────────╮──│
 70 ├─────────────────────────────────────┴──│
 60 ├────────────────────────────────────────│
 50 ├────────────────────────────────────────│
  0 └────────────────────────────────────────┘
    00:00  06:00  12:00  18:00  24:00
```

---

## API Endpoints

### Get Claw Health

```http
GET /api/v1/health/claws/:role

Response:
{
  "role": "content",
  "status": "healthy",
  "score": 95.2,
  "metrics": {
    "heartbeat_latency_ms": 45,
    "message_throughput_per_min": 12,
    "evolution_status": "success",
    "approval_backlog": 3,
    "error_rate_per_hour": 1
  },
  "last_updated": "2026-03-18T10:00:00Z"
}
```

### Get Squad Health

```http
GET /api/v1/health/squad

Response:
{
  "squad_id": "my-squad",
  "overall_score": 87.5,
  "overall_status": "good",
  "claws": [
    { "role": "content", "score": 95.2, "status": "healthy" },
    { "role": "ops", "score": 78.3, "status": "good" },
    ...
  ],
  "alerts": [
    { "role": "ops_admin", "level": "critical", "message": "Offline" }
  ]
}
```

---

## Monitoring Integration

### Prometheus Metrics

```
# HELP milimo_claw_health_score Overall health score for a claw
# TYPE milimo_claw_health_score gauge
milimo_claw_health_score{role="content"} 95.2
milimo_claw_health_score{role="ops"} 78.3

# HELP milimo_claw_heartbeat_latency_ms Heartbeat latency in milliseconds
# TYPE milimo_claw_heartbeat_latency_ms gauge
milimo_claw_heartbeat_latency_ms{role="content"} 45.2

# HELP milimo_claw_message_throughput Messages processed per minute
# TYPE milimo_claw_message_throughput gauge
milimo_claw_message_throughput{role="content"} 12

# HELP milimo_claw_approval_backlog Pending approvals count
# TYPE milimo_claw_approval_backlog gauge
milimo_claw_approval_backlog{role="content"} 3

# HELP milimo_claw_error_rate Errors per hour
# TYPE milimo_claw_error_rate gauge
milimo_claw_error_rate{role="content"} 1
```

### Grafana Dashboard

Import dashboard from `monitoring/grafana-dashboard.json`

---

## Alerting Rules

### Alert Definitions

```yaml
groups:
  - name: milimo_claw_health
    rules:
      - alert: ClawHealthDegraded
        expr: milimo_claw_health_score < 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Claw {{ $labels.role }} health degraded"

      - alert: ClawHealthCritical
        expr: milimo_claw_health_score < 30
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Claw {{ $labels.role }} health critical"

      - alert: ClawOffline
        expr: milimo_claw_health_score == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Claw {{ $labels.role }} is offline"
```
