# anomaly-detector

**Summary**: Continuous anomaly detection against 30-day rolling baselines.

**Sources**: `milimo-blueprint/orchestrator/analytics/anomaly_detector.py`

**Last updated**: 2026-04-14

**Tags**: #module #analytics-claw

---

## Purpose

Detects anomalies in performance data by comparing against 30-day rolling baselines.

## Location

**File**: `milimo-blueprint/orchestrator/analytics/anomaly_detector.py`

## Key Classes

### AnomalyDetector

Detects statistical anomalies.

```python
class AnomalyDetector:
    def __init__(
        self,
        baseline_manager: BaselineManager,
        operational_log: AnalyticsOperationalLog,
    ):
        self._baselines = baseline_manager
        self._log = operational_log

    def check_signal(self, signal: PerformanceSignal) -> Anomaly | None:
        """Check if signal is anomalous."""
        pass

    def detect_anomaly(self, metric: str, current: float) -> Anomaly | None:
        """Detect if current value is anomalous."""
        baseline = self._baselines.get_baseline(metric)
        if current > baseline * 2:
            return Anomaly(type="positive", metric=metric)
        if current < baseline * 0.5:
            return Anomaly(type="negative", metric=metric)
        return None
```

## Anomaly Thresholds

- **Positive anomaly**: current > 2× baseline
- **Negative anomaly**: current < 0.5× baseline

## Baseline Management

Baselines are recalculated every Sunday at 01:00.

See [[baseline-manager]] for details.

## Anomaly Types

```python
@dataclass
class Anomaly:
    anomaly_id: str
    metric: str
    anomaly_type: str  # "positive" | "negative"
    current_value: float
    baseline_value: float
    detected_at: str
    confidence: float
```

## Alert Dispatching

Anomalies are dispatched to appropriate claws:

| Metric Type | Dispatched To |
|-------------|---------------|
| Content performance | Content Claw |
| Client health | Ops Claw |
| Revenue | Finance Claw |
| Churn | Build Claw |

## Dependencies

- [[baseline-manager]] — Baseline storage
- [[signal-processor]] — Signal handling
- [[signal-dispatcher]] — Alert sending

## Related Pages

- [[analytics-claw]] — Parent claw
- [[baseline-manager]] — Baseline management
- [[report-generator]] — Weekly reports
