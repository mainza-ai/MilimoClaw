# Incident Analyzer

**Summary**: AI-powered incident analysis using inference client to analyze alerts and generate remediation recommendations.

**Sources**: `milimo-blueprint/orchestrator/ops/incident_analyzer.py`

**Last updated**: 2026-04-15

**Tags**: #module #ops #incident-management #ai

---

## Overview

`IncidentAnalyzer` receives alerts from webhooks or mesh messages, uses AI inference to analyze root cause, recommends actions, and matches runbooks for automated remediation.

**Claw**: [[ops-claw]]

**File**: `orchestrator/ops/incident_analyzer.py`

---

## Key Classes

### `IncidentAnalysis`

Result of incident analysis.

| Field | Type | Description |
|-------|------|-------------|
| alert_id | str | Alert identifier |
| source | str | Alert source (sentry, vercel, uptime) |
| severity | str | critical, warning, info |
| title | str | Incident title |
| root_cause_hypothesis | str | AI-generated hypothesis |
| recommended_actions | list[str] | Remediation steps |
| runbook_match | str | Matched runbook name |
| confidence | float | 0.0-1.0 confidence score |

---

### `IncidentAnalyzer`

Main analyzer class.

```python
analyzer = IncidentAnalyzer(inference_client, operational_log, dispatcher)
result = analyzer.analyze_incident(alert)
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `analyze_incident(alert)` | Analyze and return recommendations |
| `get_analysis_history(limit=50)` | Recent analysis results |
| `get_critical_incidents()` | All critical severity incidents |

---

## Analysis Pipeline

```
Alert → _run_inference_analysis() → IncidentAnalysis
         ↓ (on failure)
    _rule_based_analysis() → Fallback analysis
```

---

## Runbook Matching

The analyzer matches incidents to runbooks:

| Runbook | Trigger Patterns |
|---------|------------------|
| restart_service | "out of memory", "oom" |
| clear_cache | "disk", "storage" |
| scale_up | "cpu", "load" |
| rollback | "deployment fail" |
| investigate | Default fallback |
| notify_team | Manual escalation |

---

## Alert Input Format

```python
alert = {
    "alert_id": "sentry-20260415...",
    "source": "sentry",        # sentry, vercel, uptime, generic
    "severity": "critical",    # critical, warning, info
    "title": "OutOfMemoryError in main",
    "description": "...",
    "raw_payload": {...}
}
```

---

## AI Inference Prompt

The analyzer constructs prompts like:

```
Analyze the following incident alert:
Source: sentry
Severity: critical
Title: OutOfMemoryError in main
Description: ...

Return JSON with:
- root_cause_hypothesis
- recommended_actions (list)
- runbook_match (restart_service|clear_cache|scale_up|rollback|investigate|notify_team|none)
- confidence (0.0-1.0)
```

---

## Rule-Based Fallback

When inference fails, the analyzer uses pattern matching:

```python
# Example: OOM detection
if "out of memory" in title or "oom" in title:
    runbook = "restart_service"
    actions = ["Restart service", "Check memory limits"]
    confidence = 0.7
```

---

## Integration Points

- **Input**: [[webhook-server]] receives alerts, forwards to analyzer
- **Output**: [[runbook-executor]] executes matched runbooks
- **Logging**: Ops operational log

---

## Related Pages

- [[webhook-server]] — Alert ingestion
- [[runbook-executor]] — Remediation execution
- [[ops-claw]] — Parent claw
- [[mesh-coordinator]] — Mesh message routing

---

## See Also

- `orchestrator/ops/runbook_executor.py` — Remediation execution
- `orchestrator/ops/webhook_server.py` — Alert ingestion
