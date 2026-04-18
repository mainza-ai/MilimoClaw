# signal-processor

**Summary**: Inbound signal ingestion and storage for Analytics Claw.

**Sources**: `milimo-blueprint/orchestrator/analytics/signal_processor.py`

**Last updated**: 2026-04-14

**Tags**: #module #analytics-claw

---

## Purpose

Processes incoming signals from other claws and stores them for analysis.

## Location

**File**: `milimo-blueprint/orchestrator/analytics/signal_processor.py`

## Key Classes

### SignalProcessor

Handles signal ingestion and storage.

```python
class SignalProcessor:
    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        anomaly_detector: AnomalyDetector,
    ):
        self._fs = fs
        self._anomaly = anomaly_detector

    def process_signal(self, signal: PerformanceSignal) -> None:
        """Process incoming performance signal."""
        pass

    def store_signal(self, signal: Signal) -> None:
        """Store signal in appropriate directory."""
        pass
```

## Signal Types Received

| Signal Type | From | Description |
|-------------|------|-------------|
| `performance_signal` | Content Claw | Post engagement data |
| `client_health_signal` | Ops Claw | Client health scores |
| `revenue_summary` | Finance Claw | Weekly revenue totals |
| `shipping_summary` | Build Claw | Engineering metrics |

## Storage Paths

```
/sandbox/analytics/data/
├── content-performance/{platform}/{YYYY-MM}/performance.jsonl
├── client-health/{client_id}/health-history.jsonl
├── revenue/weekly-revenue.jsonl
└── delivery-velocity/velocity.jsonl
```

## Processing Pipeline

1. **Receive** signal via inter-sandbox message
2. **Validate** signal format
3. **Store** to appropriate path
4. **Trigger** anomaly check
5. **Log** to operational.log

## Dependencies

- [[anomaly-detector]] — Anomaly checking
- [[analytics-claw]] — Parent claw

## Related Pages

- [[analytics-claw]] — Parent claw
- [[anomaly-detector]] — Anomaly detection
- [[message-contracts]] — Signal schemas
