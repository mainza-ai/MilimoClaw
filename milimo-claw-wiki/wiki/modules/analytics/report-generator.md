# report-generator

**Summary**: Generates weekly intelligence report for all claws.

**Sources**: `milimo-blueprint/orchestrator/analytics/report_generator.py`

**Last updated**: 2026-04-14

**Tags**: #module #analytics-claw

---

## Purpose

Generates the weekly intelligence report that all other claws consume.

## Location

**File**: `milimo-blueprint/orchestrator/analytics/report_generator.py`

## Key Classes

### ReportGenerator

Generates weekly intelligence reports.

```python
class ReportGenerator:
    def __init__(
        self,
        privacy_router: PrivacyRouter,
        fs: AnalyticsFilesystemInit,
        mesh: MeshClient,
    ):
        self._router = privacy_router
        self._fs = fs
        self._mesh = mesh

    def generate_weekly(self) -> WeeklyIntelligence:
        """Generate weekly intelligence report."""
        pass

    def archive_previous(self) -> None:
        """Archive previous report."""
        pass
```

## Report Schedule

Every Sunday at 02:00 (before Evolution Cycle).

## Report Structure

```json
{
  "generated_at": "ISO timestamp",
  "week_of": "YYYY-MM-DD",
  "content_performance": { ... },
  "client_health": { ... },
  "revenue": { ... },
  "delivery": { ... },
  "opportunities": [ ... ],
  "anomalies": [ ... ],
  "forward_projections": { ... },
  "summary_narrative": "string"
}
```

## Generation Sequence

1. Aggregate all `performance_signal` from past 7 days
2. Aggregate all `client_health_signal`
3. Aggregate all `revenue_summary`
4. Aggregate all `shipping_summary`
5. Pull external trend data
6. Run anomaly detection
7. Run opportunity scoring
8. Generate narrative via inference
9. Write to `weekly-intelligence.json`
10. Archive previous report

## Shared Access

This file is readable by ALL claws:
`/sandbox/analytics/reports/weekly-intelligence.json`

## Dependencies

- [[signal-processor]] — Signal data
- [[anomaly-detector]] — Anomaly detection
- [[opportunity-scorer]] — Opportunity scores

## Related Pages

- [[analytics-claw]] — Parent claw
- [[signal-processor]] — Signal ingestion
- [[anomaly-detector]] — Anomaly detection
