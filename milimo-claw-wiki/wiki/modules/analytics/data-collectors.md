# Data Collectors

**Summary**: Real API connectors for external data sources including YouTube, Google Analytics 4, and generic REST endpoints.

**Sources**: `milimo-blueprint/orchestrator/analytics/data_collectors.py`

**Last updated**: 2026-04-15

**Tags**: #module #analytics #api #collectors

---

## Overview

`data_collectors.py` provides production-ready API connectors that replace mock/fabricated data with actual platform metrics. Each collector handles authentication, rate limiting, and data persistence.

**Claw**: [[analytics-claw]]

**File**: `orchestrator/analytics/data_collectors.py`

---

## Key Classes

### `CollectorResult`

Dataclass for collection results.

| Field | Type | Description |
|-------|------|-------------|
| source | str | Data source name |
| success | bool | Collection success flag |
| records_collected | int | Number of records |
| data | list[dict] | Collected records |
| error | str \| None | Error message if failed |
| collected_at | str | ISO timestamp |

---

### `YouTubeDataCollector`

Collects analytics from YouTube Data API v3.

**API**: `https://www.googleapis.com/youtube/v3`

**Required Environment**:
- `YOUTUBE_API_KEY` — YouTube Data API key
- `YOUTUBE_CHANNEL_ID` — Channel to monitor

**Methods**:

| Method | Returns |
|--------|---------|
| `collect_video_stats(max_results=50)` | Video performance metrics |
| `collect_channel_analytics()` | Channel-level statistics |
| `get_collected_data(lookback_days=30)` | Historical data retrieval |

**Collected Fields**:

```python
{
    "video_id": "...",
    "title": "...",
    "views": 12345,
    "likes": 500,
    "comments": 100,
    "engagement_rate": 4.87,
    "collected_at": "2026-04-15T..."
}
```

---

### `GoogleAnalyticsCollector`

Collects analytics from Google Analytics 4 via the GA4 Reporting API.

**API**: `https://analyticsdata.googleapis.com/v1beta`

**Required Environment**:
- `GA4_PROPERTY_ID` — GA4 property ID
- `GOOGLE_APPLICATION_CREDENTIALS` — Service account JSON path

**Methods**:

| Method | Returns |
|--------|---------|
| `collect_page_views(days=7)` | Page view metrics |
| `collect_events(days=7)` | Event metrics |
| `get_collected_data(lookback_days=30)` | Historical data |

**Collected Fields**:

```python
{
    "page_path": "/blog/post",
    "date": "20260415",
    "page_views": 500,
    "active_users": 120,
    "avg_session_duration": 45.2,
    "collected_at": "2026-04-15T..."
}
```

---

### `GenericAPICollector`

Configurable REST API collector for any platform.

```python
collector = GenericAPICollector(
    name="custom_platform",
    base_url="https://api.example.com/v1",
    api_key="...",
    headers={"X-Custom": "value"}
)
result = collector.collect("/endpoint", params={"limit": 100})
```

---

## Rate Limiting

All collectors implement retry logic with exponential backoff:

- **YouTube**: 3 retries, handles 429 rate limits
- **GA4**: Token caching, 1-hour expiry
- **Generic**: Configurable per-endpoint

---

## Data Persistence

Collected data persists to JSONL files:

```
~/.milimo/analytics/
├── youtube/
│   ├── video_stats.jsonl
│   └── channel_stats.jsonl
├── google_analytics/
│   ├── page_views.jsonl
│   └── events.jsonl
└── custom_platform/
    └── collected_20260415_120000.json
```

---

## Related Pages

- [[collection-workers]] — Scheduled collection orchestration
- [[analytics-claw]] — Parent claw
- [[baseline-manager]] — Uses collected data

---

## See Also

- `orchestrator/analytics/collection_workers.py` — Worker orchestration
