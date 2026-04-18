# Performance Monitor

Monitors published content performance across platforms.

## Purpose

Polls analytics endpoints for engagement data. Writes results to `performance.log`. Sends `performance_signal` messages to Analytics Claw. Detects anomalies and flags in War Room.

## Collection Schedule

Three-point collection after publish:
- **T+1 hour** — Initial engagement
- **T+24 hours** — Short-term performance
- **T+7 days** — Long-term performance

## Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `COLLECTION_SCHEDULE_HOURS` | [1, 24, 168] | Collection points |
| `ANOMALY_HIGH_THRESHOLD` | 2.0 | >2x baseline = outperformed |
| `ANOMALY_LOW_THRESHOLD` | 0.5 | <0.5x baseline = underperformed |
| `PERFORMANCE_SIGNAL_SLA_HOURS` | 1 | Signal must be sent within 1hr |

## Data Classes

### PerformanceRecord

```python
@dataclass
class PerformanceRecord:
    post_id: str
    platform: str
    content_type: str
    client_id: str | None
    publish_time: str
    collected_at: str
    engagement_data: dict[str, int]
    collection_point: int  # 1, 24, or 168 hours
```

### AnomalyResult

```python
@dataclass
class AnomalyResult:
    post_id: str
    platform: str
    direction: Literal["outperformed", "underperformed"]
    baseline_engagement: float
    actual_engagement: float
    ratio: float
    message: str
```

### MonitoringSchedule

```python
@dataclass
class MonitoringSchedule:
    post_id: str
    platform: str
    publish_time: str
    collection_points: list[int]  # [1, 24, 168]
    collected_points: list[int]   # Tracking progress
    client_id: str | None
    content_type: str
```

## Methods

| Method | Purpose |
|--------|---------|
| `monitor_post()` | Schedule performance monitoring |
| `collect_performance()` | Fetch engagement from platform API |
| `record_performance()` | Write to `performance.log` |
| `send_performance_signal()` | Send signal to Analytics Claw |
| `detect_anomaly()` | Compare against 30-day baseline |
| `flag_anomaly_in_war_room()` | Queue anomaly for review |
| `check_due_collections()` | Find posts due for collection |
| `run_collection_cycle()` | Process all due posts |

## SLA Enforcement

`performance_signal` must be sent within 1 hour of publish:
```python
if elapsed_hours > PERFORMANCE_SIGNAL_SLA_HOURS:
    logger.warning("Performance signal SLA exceeded")
    # Log warning but still send signal
```

## Anomaly Detection

Compares total engagement against 30-day baseline:
```python
total = likes + shares + comments + click_through
ratio = total / baseline

if ratio > 2.0: return "outperformed"
if ratio < 0.5: return "underperformed"
```

## File Locations

```
/sandbox/content/logs/
└── performance.log    # JSONL engagement records
```

## Relationships

- Sends to: [[analytics-claw]] — `performance_signal` messages
- Flags to: [[war-room]] — Anomaly queueing
- Depends on: `ContentFilesystemInit`, `ContentOperationalLog`

## Source

`milimo-blueprint/orchestrator/content/performance_monitor.py`
