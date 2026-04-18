# Query Handler

Handles on-demand queries from other claws with enforced SLA.

## Purpose

Provides real-time data access for other claws. Enforces 2-minute SLA for all responses. Never times out silently — always responds.

## SLA Enforcement

- **RESPONSE_TIMEOUT_SECONDS = 110** — Hard timeout before SLA
- **SLA_VIOLATION_THRESHOLD_MS = 120000** — 2-minute SLA threshold
- **MIN_DAYS_FOR_COMPLETE = 7** — Minimum data for "complete" quality

## Response Quality Levels

| Quality | Meaning |
|---------|---------|
| `complete` | ≥7 days of data collected |
| `partial` | Data available but <7 days |
| `estimated` | Inference-based projection |
| `insufficient` | Not enough data, includes `days_collected` and `days_needed` |

## Methods

| Method | Purpose |
|--------|---------|
| `handle(raw_message)` | Route to correct handler by message_type |
| `handle_content_performance_query()` | Return top formats by engagement |
| `handle_behavior_query()` | Correlate features with client health |

## Message Types

### content_performance_query

Returns top content formats sorted by engagement:
```json
{
  "data_quality": "complete",
  "data": {
    "top_formats": [
      {"format": "carousel", "avg_engagement": 0.042, "sample_count": 45}
    ],
    "lookback_days": 7,
    "platform_filter": null
  },
  "days_collected": 12,
  "days_needed": 7
}
```

### behavior_query

Correlates feature shipping with client health changes:
```json
{
  "data_quality": "complete",
  "data": {
    "feature_adoption_rates": {"feature-a": 5},
    "retention_correlation": [
      {"client_id": "client-123", "health_delta": 0.15}
    ]
  }
}
```

## Logging

- **queries.log** — All query receipts and responses
- **signals.log** — SLA violations
- **operational.log** — Query lifecycle events

## Error Handling

- Never raises on timeout — returns partial response
- Unknown query types return `data_quality="error"`
- Failed inference falls back to rule-based scoring

## Relationships

- Used by: [[finance-claw]], [[ops-claw]], [[build-claw]] — Query analytics data
- Depends on: `AnalyticsFilesystemInit`, `AnalyticsOperationalLog`
- Related: [[baseline-manager]] — May use baseline data for comparisons

## Source

`milimo-blueprint/orchestrator/analytics/query_handler.py`
