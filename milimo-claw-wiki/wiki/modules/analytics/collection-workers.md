# Collection Workers

**Summary**: Scheduled data collection workers that periodically fetch real data from external platforms and persist to Analytics Claw directories.

**Sources**: `milimo-blueprint/orchestrator/analytics/collection_workers.py`

**Last updated**: 2026-04-15

**Tags**: #module #analytics #data-collection

---

## Overview

`CollectionWorker` manages scheduled data collection from external platforms. It replaces fabricated/mock data with actual platform metrics by running collection jobs on configurable intervals.

**Claw**: [[analytics-claw]]

**File**: `orchestrator/analytics/collection_workers.py`

---

## Key Classes

### `CollectionWorker`

Main worker class that manages scheduled collection from multiple sources.

```python
worker = CollectionWorker(fs, operational_log)
worker.register_youtube(channel_id="...", api_key="...", interval_hours=6)
worker.register_google_analytics(property_id="...", interval_hours=12)
worker.start()
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `register_youtube()` | Register YouTube data collector |
| `register_google_analytics()` | Register GA4 collector |
| `register_generic()` | Register generic REST API collector |
| `start()` | Begin scheduled collection loop |
| `stop()` | Halt all collection workers |
| `collect_now()` | Trigger immediate collection |
| `get_collection_summary()` | Get collection status overview |

---

## Supported Sources

| Source | Collector Class | Default Interval |
|--------|-----------------|------------------|
| YouTube | `YouTubeDataCollector` | 6 hours |
| Google Analytics 4 | `GoogleAnalyticsCollector` | 12 hours |
| Generic REST API | `GenericAPICollector` | 24 hours |

---

## Data Flow

```
External API → Collector → CollectionWorker
                           ↓
                    Persist to data_dir
                           ↓
                    QueryHandler / ReportGenerator
```

---

## Configuration

### YouTube Collector

```python
worker.register_youtube(
    channel_id="UC...",           # YouTube channel ID
    api_key="AIza...",            # YouTube Data API key
    interval_hours=6              # Collection frequency
)
```

### Google Analytics Collector

```python
worker.register_google_analytics(
    property_id="123456789",      # GA4 property ID
    credentials_path="/path/to/service-account.json",
    interval_hours=12
)
```

### Generic API Collector

```python
worker.register_generic(
    name="custom_platform",
    base_url="https://api.example.com/v1",
    api_key="...",
    headers={"X-Custom": "value"},
    interval_hours=24
)
```

---

## Operational Log Integration

All collection events are logged to the operational log:

```python
AnalyticsLogEntry(
    action_type="data_collection",
    entity_id="youtube",
    outcome="success",
    details={"records_collected": 50}
)
```

---

## Related Pages

- [[data-collectors]] — Individual collector implementations
- [[analytics-claw]] — Parent claw
- [[query-handler]] — Consumes collected data
- [[report-generator]] — Uses data for reports

---

## See Also

- `orchestrator/analytics/data_collectors.py` — Collector implementations
