# Analytics Claw

**Summary**: Main entry point for the Analytics Claw. Initializes all components (filesystem, scheduler, signal dispatcher, anomaly detector, baseline manager, report generator, opportunity scorer, forward projector), wires them together, and starts the scheduler.

**Sources**: `milimo-blueprint/orchestrator/analytics/analytics_claw.py`

**Last updated**: 2026-04-17

**Tags**: #claw #analytics #entry-point

---

## Overview

`AnalyticsClaw` is the main entry point for the Analytics Claw. Called by the NemoClaw blueprint orchestrator on sandbox startup.

**File**: `orchestrator/analytics/analytics_claw.py`

---

## Key Components

| Component | Type | Purpose |
|-----------|------|---------|
| `AnalyticsFilesystemInit` | Filesystem | Initialize claw directory structure |
| `AnalyticsOperationalLog` | Logging | Structured action logging |
| `SignalDispatcher` | Communication | Inter-claw message routing |
| `BaselineManager` | Analytics | 30-day rolling baseline calculator |
| `SignalProcessor` | Analytics | Signal processing pipeline |
| `QueryHandler` | Analytics | On-demand query handler with SLA |
| `AnomalyDetector` | Analytics | Anomaly detection engine |
| `ReportGenerator` | Analytics | Report generation |
| `OpportunityScorer` | Analytics | Opportunity scoring |
| `ForwardProjector` | Analytics | 4-week projection engine |
| `AnalyticsScheduler` | Scheduler | Periodic task scheduler |
| `CollectionWorker` | Data | Real data collection from external platforms |

---

## Startup Sequence

```python
claw = AnalyticsClaw(
    squad_id="my-squad",
    inference_client=inference,
    mesh_sender=send_via_mesh,
    base_path=Path("/sandbox/analytics")
)
claw.startup()
```

**Steps:**
1. Initialize filesystem (`AnalyticsFilesystemInit`)
2. Validate directory structure
3. Create operational log
4. Initialize `SignalDispatcher` with mesh sender
5. Initialize all analytics components
6. Start `AnalyticsScheduler`
7. Register external data collectors (YouTube, GA4, generic REST)
8. Start collection workers

---

## Inbound Message Handlers

| Message Type | Handler | Source Claw |
|--------------|---------|-------------|
| `performance_signal` | `_handle_performance_signal` | Content Claw |
| `client_health_signal` | `_handle_client_health_signal` | Ops Claw |
| `client_onboarded` | `_handle_client_onboarded` | Ops Claw |
| `revenue_summary` | `_handle_revenue_summary` | Finance Claw |
| `shipping_summary` | `_handle_shipping_summary` | Build Claw |
| `content_performance_query` | `_handle_content_performance_query` | Any |
| `behavior_query` | `_handle_behavior_query` | Any |
| `assistant_query` | `_handle_assistant_query` | Lucy |
| `assistant_task` | `_handle_assistant_task` | Lucy |

---

## Signal Processing Pipeline

When `performance_signal` arrives:
1. SignalProcessor handles the signal
2. BaselineManager loads content baselines
3. AnomalyDetector checks for anomalies
4. If anomaly found → save and dispatch alert

When `client_health_signal` arrives:
1. If health_score < 6.0 → dispatch `client_health_alert` via SignalDispatcher

---

## External Data Collection

Analytics Claw collects real data from external platforms:

### YouTube Data API
```python
# Environment variables
YOUTUBE_API_KEY=...
YOUTUBE_CHANNEL_ID=...
YOUTUBE_COLLECTION_INTERVAL=6  # hours
```

### Google Analytics 4
```python
# Environment variables
GA4_PROPERTY_ID=...
GOOGLE_APPLICATION_CREDENTIALS=...  # path to credentials JSON
GA_COLLECTION_INTERVAL=12  # hours
```

### Generic REST Collectors
```python
# Pattern: COLLECTOR_{NAME}_URL, COLLECTOR_{NAME}_KEY, COLLECTOR_{NAME}_INTERVAL
COLLECTOR_SHOPIFY_URL=https://shop.example.com/api
COLLECTOR_SHOPIFY_KEY=...
COLLECTOR_SHOPIFY_INTERVAL=24
```

---

## Properties

| Property | Type | Access |
|----------|------|--------|
| `baseline_manager` | `BaselineManager | None` | Read-only |
| `anomaly_detector` | `AnomalyDetector | None` | Read-only |
| `opportunity_scorer` | `OpportunityScorer | None` | Read-only |
| `report_generator` | `ReportGenerator | None` | Read-only |

---

## Related Pages

- [[analytics-claw]] — This page
- [[analytics-scheduler]] — Periodic task scheduler
- [[anomaly-detector]] — Anomaly detection
- [[baseline-manager]] — Baseline calculations
- [[query-handler]] — On-demand queries
- [[signal-processor]] — Signal processing

---

## See Also

- `orchestrator/analytics/analytics_init.py` — Filesystem initialization
- `orchestrator/analytics/analytics_scheduler.py` — Scheduler
- `orchestrator/analytics/signal_dispatcher.py` — Message routing
