# Webhook Server

**Summary**: HTTP server for real-time incident ingestion from monitoring systems (Sentry, Vercel, uptime monitors).

**Sources**: `milimo-blueprint/orchestrator/ops/webhook_server.py`

**Last updated**: 2026-04-15

**Tags**: #module #ops #webhook #incident-ingestion

---

## Overview

`OpsWebhookServer` runs an HTTP server that receives alerts from monitoring systems and forwards them to the Ops Claw for analysis and remediation.

**Claw**: [[ops-claw]]

**File**: `orchestrator/ops/webhook_server.py`

---

## Key Classes

### `OpsWebhookServer`

Webhook server running in background thread.

```python
server = OpsWebhookServer(
    port=8080,
    dispatcher=ops_signal_dispatcher,
    ops_claw=ops_claw_instance
)
server.start()
# ... later ...
server.stop()
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `start()` | Begin listening in background |
| `stop()` | Shutdown server |
| `get_alerts()` | Retrieve buffered alerts |

---

## Endpoints

| Endpoint | Method | Source |
|----------|--------|--------|
| `/webhook/sentry` | POST | Sentry error alerts |
| `/webhook/vercel` | POST | Vercel deployment alerts |
| `/webhook/uptime` | POST | Uptime monitor alerts |
| `/webhook/generic` | POST | Generic JSON alerts |
| `/health` | GET | Health check |

---

## Alert Parsing

### Sentry Webhook

```python
{
    "alert_id": "sentry-20260415...",
    "source": "sentry",
    "severity": "critical",  # mapped from level
    "title": "OutOfMemoryError",
    "description": "...",
    "url": "https://sentry.io/...",
    "project": "my-app",
    "raw_payload": {...}
}
```

### Vercel Webhook

```python
{
    "alert_id": "vercel-20260415...",
    "source": "vercel",
    "severity": "warning",
    "title": "Vercel deployment ERROR",
    "description": "Deployment abc123 for my-app",
    "url": "https://...",
    "project": "my-app"
}
```

### Uptime Webhook

```python
{
    "alert_id": "uptime-20260415...",
    "source": "uptime",
    "severity": "critical",  # if status=down
    "title": "Service down: my-api",
    "description": "...",
    "url": "https://..."
}
```

---

## Alert Buffer

Alerts are buffered in memory for retrieval:

```python
alerts = server.get_alerts()  # Returns and clears buffer
```

---

## Integration Flow

```
Sentry/Vercel/Uptime
        ↓ POST /webhook/*
   OpsWebhookServer
        ↓ parse
   _WebhookHandler
        ↓ buffer + forward
   OpsClaw.handle_incident()
        ↓
   IncidentAnalyzer → RunbookExecutor
```

---

## Configuration

```python
server = OpsWebhookServer(
    port=8080,              # Listening port
    host="0.0.0.0",         # Bind address
    dispatcher=dispatcher,  # Signal dispatcher
    ops_claw=ops_claw       # Full Ops Claw instance
)
```

---

## Severity Mapping

### Sentry

| Sentry Level | Internal Severity |
|--------------|-------------------|
| fatal | critical |
| error | critical |
| warning | warning |
| info | info |
| debug | info |

---

## Related Pages

- [[incident-analyzer]] — Alert analysis
- [[runbook-executor]] — Remediation execution
- [[ops-claw]] — Parent claw
- [[mesh-coordinator]] — Mesh message routing

---

## See Also

- `orchestrator/ops/incident_analyzer.py` — Incident analysis
- `orchestrator/ops/runbook_executor.py` — Remediation
