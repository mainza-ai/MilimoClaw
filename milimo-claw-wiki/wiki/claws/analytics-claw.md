# Analytics Claw

**Summary**: Intelligence layer that observes everything and acts on nothing — reports, anomalies, and opportunity scoring.

**Sources**:
- `raw/ANALYTICS_CLAW_SPEC.md`
- `milimo-blueprint/roles/analytics-claw.yaml`

**Last updated**: 2026-04-28

**Tags**: #claw #analytics

---

## Role

The Analytics Claw is the **intelligence layer** of MilimoClaw. It observes everything but acts on nothing — it collects data, detects anomalies, and provides insights to other claws.

## Sandbox

**Mount**: `/sandbox/.openclaw/milimo/claws/analytics`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/.openclaw/milimo/claws/analytics/` | Performance data, reports | Read-write |
| `/sandbox/.openclaw/milimo/claws/analytics/reports/` | Weekly intelligence report | Read-write (shared) |
| `/sandbox/.openclaw/milimo/claws/ops/` | Client data | **NO ACCESS** |
| `/sandbox/.openclaw/milimo/claws/finance/` | Financial data | **NO ACCESS** |

## What It Does

- Collects and stores performance signals from all other claws
- Generates the weekly intelligence report every Sunday at 02:00
- Runs continuous anomaly detection against 30-day rolling baselines
- Scores opportunities daily at 06:00 — dispatches immediately at >0.85 confidence
- Responds to on-demand queries from Content and Build Claws within 2 minutes
- Maintains forward projections for revenue, engagement, and delivery velocity

## What It Cannot Do

- Write to any external platform — read-only network access only
- Read `/sandbox/.openclaw/milimo/claws/ops`, `/sandbox/.openclaw/milimo/claws/finance`, or `/sandbox/.openclaw/milimo/claws/build` raw records
- Queue HOLD actions in the War Room — it observes, never blocks
- Perform any write operation to external APIs

## Primary Output — Shared Filesystem

**CRITICAL**: The weekly intelligence report is the only file all claws can read directly:

```
/sandbox/.openclaw/milimo/claws/analytics/reports/weekly-intelligence.json
```

This file must be configured as a read-only mount in **every** claw's sandbox policy file. If any claw cannot read this file, the intelligence layer is silently broken.

## Anomaly Thresholds

- **Positive anomaly**: current value > 2× baseline
- **Negative anomaly**: current value < 0.5× baseline

## Query Response SLA

**2 minutes maximum** to respond to:
- `content_performance_query`
- `behavior_query`

Log violations. Never timeout silently.

## Scheduling

| Time | Action |
|------|--------|
| Sunday 01:00 | Baseline recalculation |
| Sunday 02:00 | Weekly intelligence report generation |
| Daily 06:00 | Opportunity scoring |
| On signal receipt | Anomaly detection |
| On query receipt | Query response (2-min SLA) |

## Inter-Claw Messages

### Sent

| Message Type | To | Trigger | SLA |
|--------------|-----|---------|-----|
| `performance_intel` | Content | Weekly + high-confidence opportunity | Sunday 02:05 |
| `retention_signals` | Build | Weekly + churn anomaly | Sunday 02:05 |
| `client_health_alert` | Ops | When client health < 6.0 | Immediate |
| `revenue_anomaly` | Finance | On anomaly detection | Immediate |
| `content_performance_response` | Content | Query response | 2 minutes |
| `behavior_query_response` | Build | Query response | 2 minutes |

### Received

| Message Type | From | Handler |
|--------------|------|---------|
| `performance_signal` | Content | Store and analyze |
| `client_health_signal` | Ops | Incorporate into health scoring |
| `client_onboarded` | Ops | Initialize tracking |
| `revenue_summary` | Finance | Update revenue projections |
| `shipping_summary` | Build | Track development velocity |
| `content_performance_query` | Content | Generate response |
| `behavior_query` | Build | Analyze user behavior patterns |
| `assistant_query` | Assistant | Return status and state |
| `assistant_task` | Assistant | Execute analytics-related tasks |

## Key Modules

- [[analytics-init]] — Filesystem initialization
- [[signal-processor]] — Incoming signal handling
- [[anomaly-detector]] — Anomaly detection engine
- [[opportunity-scorer]] — Opportunity confidence scoring
- [[baseline-manager]] — 30-day baseline management
- [[report-generator]] — Weekly intelligence report
- [[query-handler]] — 2-min SLA query responses
- [[forward-projector]] — Revenue/engagement projections
- [[signal-dispatcher]] — Inter-claw message sending
- [[analytics-scheduler]] — Scheduled tasks

## Hermes Skill Capabilities (2026-07-04)

When running under the Hermes profile, the Analytics Claw skill exposes these
capabilities as direct methods on the instantiated skill object:

| Capability | Method | Sub-Component |
|------------|--------|---------------|
| `process_signals` | `process_signals(message)` | `SignalProcessor.handle_performance_signal()` |
| `detect_anomalies` | `detect_anomalies(message)` | `AnomalyDetector.check_content_signal()` |
| `score_opportunities` | `score_opportunities(message)` | `OpportunityScorer.to_dict()` |
| `generate_reports` | `generate_reports()` | `ReportGenerator` |
| `query_analytics` | `query_analytics(message)` | `QueryHandler.handle()` |
| `project_forecasts` | `project_forecasts()` | `ForwardProjector.project_all()` |
| `manage_baselines` | `manage_baselines()` | `BaselineManager.load_content_baselines()` + `load_revenue_baseline()` |

**Skill factory** (`create_analytics_claw` in `milimo-hermes-plugin/__init__.py`) now instantiates `AnalyticsClaw` with:
- `squad_id` from `MILIMO_SQUAD_ID` env (default `"default"`)
- `mesh_sender` via `_get_mesh_sender()` callable

---

## Evolution Tools

Tools that emerge autonomously over time:

```
Engagement baseline model → Anomaly detector v2 → Opportunity scorer v2 →
Retention correlator → Competitor signal tracker → Forward projection engine v2
```

## Evolution Schedule

**Sunday 02:25** — Analytics Claw evolution cycle

Runs after Ops Claw evolution.

## Spec Document

Full specification: `raw/ANALYTICS_CLAW_SPEC.md`

## Related Pages

- [[message-contracts]] — Message schemas
- [[sandbox-isolation]] — Shared filesystem exception
- [[content-claw]] — Receives performance intel
- [[build-claw]] — Receives retention signals
- [[ops-claw]] — Receives health alerts

## See Also

- Implementation prompt: `milimo-claw-docs/prompts/ANALYTICS_CLAW_IMPLEMENTATION_PROMPT.md`
- Policy: `milimo-blueprint/policies/analytics-sandbox.yaml`
- Tests: `milimo-blueprint/tests/test_analytics_claw*.py`
