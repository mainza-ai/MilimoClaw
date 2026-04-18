# Metrics Collector

**Summary**: Thread-safe performance metrics collector for all claws, feeding the Evolution Cycle's Observe and Identify stages.

**Sources**: `milimo-blueprint/orchestrator/metrics_collector.py`

**Last updated**: 2026-04-15

**Tags**: #module #operations #metrics #performance

---

## Overview

`MetricsCollector` provides a shared interface for all claws to record performance metrics. Data is persisted to JSONL files for cross-process readability.

**File**: `orchestrator/metrics_collector.py`

**Storage**: `~/.milimo/metrics/{claw_role}/metrics.jsonl`

---

## Key Classes

### `MetricEntry`

Single performance metric entry.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | str | ISO timestamp |
| claw_role | str | Claw identifier |
| metric_type | str | Type of metric |
| value | float/int | Metric value |
| unit | str | Unit of measure |
| tags | dict | Additional labels |

---

### `MetricsCollector`

Thread-safe metrics collector.

```python
collector = MetricsCollector(claw_role="content")

# Record message processing
collector.record_message_processed("brief_arrival", processing_time_ms=150)

# Record inference call
collector.record_inference_call("content_draft", tokens=500, latency_ms=800)

# Record error
collector.record_error("api_timeout", "Stripe API timeout")

# Record SLA compliance
collector.record_sla_compliance("brief_arrival", sla_ms=30000, actual_ms=15000)

# Get summary
summary = collector.get_summary(lookback_hours=24)
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `record_message_processed()` | Log message processing time |
| `record_error()` | Log error occurrence |
| `record_inference_call()` | Log inference API call |
| `record_sla_compliance()` | Log SLA compliance |
| `record_custom()` | Log custom metric |
| `get_summary()` | Get aggregated metrics |

---

## Metric Types

| Type | Description |
|------|-------------|
| message_processed | Successfully processed message |
| error | Error occurrence |
| inference_call | LLM inference call |
| sla_compliance | SLA check result |

---

## Summary Output

```python
{
    "claw_role": "content",
    "lookback_hours": 24,
    "counters": {
        "messages_processed": 500,
        "errors": 5,
        "inference_calls": 200,
        "inference_tokens": 50000,
        "sla_compliant": 495,
        "sla_violation": 5
    },
    "timings": {
        "latency.brief_arrival": {
            "count": 100,
            "avg_ms": 150.5,
            "min_ms": 50,
            "max_ms": 500,
            "p95_ms": 350
        }
    }
}
```

---

## Evolution Integration

Metrics feed the Evolution Cycle:

1. **Observe**: Read metrics from JSONL
2. **Identify**: Find patterns in metrics
3. **Propose**: Generate tool improvements

---

## Related Pages

- [[health-collector]] — Health monitoring
- [[evolution-cycle]] — Sunday evolution
- [[operation-log]] — Action logging
- [[latency-monitor]] — Network latency

---

## See Also

- `orchestrator/health_collector.py` — Health monitoring
- `orchestrator/operation_log.py` — Action logging
