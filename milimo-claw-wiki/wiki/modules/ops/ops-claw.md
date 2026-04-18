# Ops Claw

**Summary**: Main entry point for the Ops Claw. Initializes all components (filesystem, signal dispatcher, approval handler, intake manager, health scorer, project manager, scope monitor, comms manager, scheduler, incident analyzer, runbook executor, webhook server), wires them together, and starts the scheduler.

**Sources**: `milimo-blueprint/orchestrator/ops/ops_claw.py`

**Last updated**: 2026-04-17

**Tags**: #claw #ops #entry-point

---

## Overview

`OpsClaw` is the main entry point for the Ops Claw. Handles client lifecycle, project management, communications, and incident response.

**File**: `orchestrator/ops/ops_claw.py`

---

## Key Components

| Component | Type | Purpose |
|-----------|------|---------|
| `OpsFilesystemInit` | Filesystem | Initialize claw directory structure |
| `OpsOperationalLog` | Logging | Structured action logging |
| `OpsCommsLog` | Logging | Communication-specific logging |
| `OpsSignalDispatcher` | Communication | Inter-claw message routing |
| `OpsApprovalHandler` | Coordination | Approval workflow for ops actions |
| `IntakeManager` | Operations | Client intake and onboarding |
| `ClientHealthScorer` | Analytics | Client health scoring |
| `ProjectManager` | Operations | Project lifecycle management |
| `ScopeMonitor` | Operations | Scope creep detection |
| `CommsManager` | Operations | Client communication handler |
| `OpsScheduler` | Scheduler | Periodic task scheduling |
| `IncidentAnalyzer` | Operations | AI-powered incident analysis |
| `RunbookExecutor` | Operations | Automated remediation |
| `OpsWebhookServer` | Infrastructure | Real-time alert ingestion |

---

## Startup Sequence

```python
claw = OpsClaw(
    squad_id="my-squad",
    inference_client=inference,
    mesh_gateway=mesh_gateway,
    base_path=Path("/sandbox/ops")
)
claw.startup()
```

**Steps:**
1. Initialize filesystem
2. Validate directory structure
3. Create operational log and comms log
4. Initialize `OpsSignalDispatcher`
5. Initialize `OpsApprovalHandler`
6. Initialize all ops components
7. Register inbound message handlers
8. Start `OpsScheduler`
9. Initialize incident analyzer and runbook executor
10. Start webhook server (port from `OPS_WEBHOOK_PORT`, default 8080)

---

## Webhook Server

Ops Claw starts a webhook server for real-time alert ingestion:

```python
# Environment variable
OPS_WEBHOOK_PORT=8080  # default
```

---

## Inbound Message Handlers

| Message Type | Handler |
|--------------|---------|
| `deliverable_complete` | `_handle_deliverable_complete` |
| `deploy_complete` | `_handle_deploy_complete` |
| `pricing_response` | `_handle_pricing_response` |
| `invoice_ready` | `_handle_invoice_ready` |
| `payment_overdue` | `_handle_payment_overdue` |
| `brief_acknowledged` | `_handle_brief_acknowledged` |
| `assistant_query` | `_handle_assistant_query` |
| `assistant_task` | `_handle_assistant_task` |

---

## Incident Handling Pipeline

```python
# Handle incoming incident alert
claw.handle_incident(alert)
```

**Pipeline:**
1. Log alert via dispatcher
2. AI-powered analysis via IncidentAnalyzer
3. Automated remediation via RunbookExecutor

---

## Approval Decision Handler

Ops Claw handles War Room approval decisions:

```python
claw.handle_approval_decision(
    action_id="action_123",
    decision="approved"  # or "edited", "blocked", "released"
    edited_content="..."  # for "edited"
)
```

### Action-Specific Execution

On `released`:
- `scope_change_order` → update project status to "scope_changed"
- `deadline_critical` → update project status to "deadline_at_risk"

---

## Properties

| Property | Type | Access |
|----------|------|--------|
| `is_running` | `bool` | Read-only |
| `intake_manager` | `IntakeManager | None` | Read-only |
| `project_manager` | `ProjectManager | None` | Read-only |
| `health_scorer` | `ClientHealthScorer | None` | Read-only |
| `approval_handler` | `OpsApprovalHandler | None` | Read-only |
| `dispatcher` | `OpsSignalDispatcher | None` | Read-only |

---

## Related Pages

- [[ops-claw]] — This page
- [[ops-scheduler]] — Periodic task scheduling
- [[intake-manager]] — Client intake
- [[project-manager]] — Project management
- [[health-scorer]] — Client health scoring
- [[comms-manager]] — Client communications
- [[incident-analyzer]] — AI incident analysis
- [[runbook-executor]] — Automated remediation
- [[webhook-server]] — Alert ingestion

---

## See Also

- `orchestrator/ops/ops_init.py` — Filesystem initialization
- `orchestrator/ops/signal_dispatcher.py` — Message routing
- `orchestrator/ops/approval_handler.py` — Approval workflow
