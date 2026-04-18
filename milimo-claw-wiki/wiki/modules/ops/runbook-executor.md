# Runbook Executor

**Summary**: Automated remediation procedures for common incidents with predefined runbook execution.

**Sources**: `milimo-blueprint/orchestrator/ops/runbook_executor.py`

**Last updated**: 2026-04-15

**Tags**: #module #ops #runbook #remediation

---

## Overview

`RunbookExecutor` matches incident analysis results to predefined runbooks and executes remediation steps automatically or with approval.

**Claw**: [[ops-claw]]

**File**: `orchestrator/ops/runbook_executor.py`

---

## Key Classes

### `RunbookResult`

Execution result.

| Field | Type | Description |
|-------|------|-------------|
| runbook_name | str | Executed runbook |
| success | bool | Execution success |
| steps_executed | int | Completed steps |
| steps_failed | int | Failed steps |
| output | str | Execution log |
| duration_seconds | float | Execution time |

---

### `RunbookExecutor`

Main executor class.

```python
executor = RunbookExecutor(operational_log, dispatcher)
result = executor.execute_runbook("restart_service", context=alert)
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `execute_runbook(name, context)` | Execute a runbook |
| `get_available_runbooks()` | List all runbooks |
| `get_execution_history(limit)` | Recent executions |
| `register_runbook(name, desc, steps)` | Add custom runbook |
| `handle_incident_with_remediation(alert, analysis)` | Full pipeline |

---

## Predefined Runbooks

### restart_service

Restarts failing Docker containers.

```yaml
steps:
  - log: "Initiating service restart"
  - shell: docker ps --format '{{.Names}}'
  - shell: docker restart $(docker ps -q --filter 'status=unhealthy')
  - wait: 10s
  - shell: docker ps --format '{{.Names}} {{.Status}}'
  - log: "Service restart complete"
```

### clear_cache

Clears temporary files and caches.

```yaml
steps:
  - log: "Initiating cache clear"
  - shell: du -sh /tmp
  - shell: find /tmp -type f -mtime +1 -delete
  - shell: df -h /
  - log: "Cache clear complete"
```

### scale_up

Scales service instances.

```yaml
steps:
  - log: "Initiating scale up"
  - shell: docker compose ps
  - shell: docker compose up -d --scale build-claw=2
  - wait: 15s
  - shell: docker compose ps
```

### rollback

Rolls back deployments (requires manual approval).

### investigate

Gathers diagnostic information.

```yaml
steps:
  - shell: uptime
  - shell: free -m
  - shell: df -h
  - shell: docker stats --no-stream
  - shell: tail -100 /var/log/syslog
```

### notify_team

Queues notification for review.

---

## Execution Modes

### Auto-Execute

These runbooks execute automatically:

- `restart_service`
- `clear_cache`
- `investigate`

### Requires Approval

These runbooks queue for War Room review:

- `rollback`
- `scale_up`
- `notify_team`

---

## Step Actions

| Action | Description |
|--------|-------------|
| `shell` | Execute shell command |
| `wait` | Sleep for N seconds |
| `log` | Log message |
| `notify` | Queue notification |

---

## Integration with Incident Analyzer

```python
# Full pipeline: analyze → match → execute
analysis = incident_analyzer.analyze_incident(alert)
result = runbook_executor.handle_incident_with_remediation(alert, analysis)
```

---

## Custom Runbooks

```python
executor.register_runbook(
    name="custom_remediation",
    description="Custom remediation procedure",
    steps=[
        {"action": "log", "message": "Starting custom remediation"},
        {"action": "shell", "command": "systemctl restart my-service"},
        {"action": "wait", "seconds": 5},
    ]
)
```

---

## Related Pages

- [[incident-analyzer]] — Incident analysis
- [[webhook-server]] — Alert ingestion
- [[ops-claw]] — Parent claw
- [[war-room]] — Approval queue

---

## See Also

- `orchestrator/ops/incident_analyzer.py` — Incident analysis
- `orchestrator/ops/webhook_server.py` — Alert ingestion
