# Inter-Claw Communication

**Summary**: Typed message contract system for all inter-claw communication.

**Sources**:
- `raw/AGENTS.md`
- `milimo-blueprint/orchestrator/contracts.py`

**Last updated**: 2026-04-14

**Tags**: #architecture #communication #contracts #messaging

---

## Overview

All inter-claw communication uses **typed message contracts** — structured payloads with defined schemas. This ensures that every message is validated, logged, and policy-enforced before delivery.

## Message Contract System

### Message Structure

Every message includes these required fields:

```python
{
    "message_id": str,        # UUID
    "message_type": str,      # Must match a key in contracts.py
    "sender_role": str,       # Must match contract sender_roles
    "recipient_role": str,    # Must match contract recipient_roles
    "timestamp": str,         # ISO 8601
    "payload": dict           # Must match contract payload schema
}
```

### Contract Definition

Contracts are defined in `milimo-blueprint/orchestrator/contracts.py`:

```python
@dataclass
class ClawMessage:
    sender_role: str
    recipient_role: str
    message_type: str
    payload: dict
    squad_id: str
    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

## Message Types

### Complete Message Matrix

| From | To | Message Type | Trigger |
|------|-----|--------------|---------|
| Content | War Room | `draft_ready` | Draft ready for review |
| Content | Analytics | `content_performance_query` | Monday 06:00 + on demand |
| Content | Analytics | `performance_signal` | After every published post |
| Content | Ops | `brief_acknowledged` | Within 5 min of project_brief |
| Content | Ops | `deliverable_complete` | All deliverables published |
| Ops | Content/Build | `project_brief` | New project scoped |
| Ops | Build | `feature_brief` | New technical feature |
| Ops | Finance | `pricing_query` | Before any proposal |
| Ops | Finance | `project_complete` | Client confirms delivery |
| Ops | Analytics | `client_health_signal` | Weekly |
| Ops | Analytics | `client_onboarded` | New client onboarded |
| Analytics | Content | `performance_intel` | Weekly + high-confidence opportunity |
| Analytics | Build | `retention_signals` | Weekly + churn anomaly |
| Analytics | Ops | `client_health_alert` | When client health < 6.0 |
| Analytics | Finance | `revenue_anomaly` | On anomaly detection |
| Analytics | Content | `content_performance_response` | Query response |
| Analytics | Build | `behavior_query_response` | Query response |
| Finance | Ops | `pricing_response` | Within 10 min of query |
| Finance | Ops | `invoice_ready` | After Stage 1 approval |
| Finance | Ops | `payment_overdue` | Immediately on overdue |
| Finance | Analytics | `revenue_summary` | Weekly + on payment |
| Build | Ops | `deploy_complete` | Production deploy |
| Build | Ops | `feature_brief_acknowledged` | Within 10 min of feature_brief |
| Build | Content | `shipping_summary` | Friday 17:00 (weekly) |
| Build | Analytics | `behavior_query` | Before sprint planning |
| Assistant | Any Claw | `assistant_query` | Status request |
| Assistant | Any Claw | `assistant_task` | Task assignment |

## Gateway Enforcement

### OpenShell Gateway

All messages pass through the OpenShell gateway:

```
┌─────────────┐                      ┌─────────────┐
│ Content Claw │ ──── message ────► │ OpenShell   │
│              │                     │ Gateway     │
└─────────────┘                      │             │
                                     │ - Validate  │
                                     │ - Log       │
                                     │ - Route     │
                                     └─────┬───────┘
                                           │
                                           ▼
                                     ┌─────────────┐
                                     │ Ops Claw    │
                                     └─────────────┘
```

### Validation Steps

1. **Schema Check**: Message matches contract schema
2. **Role Check**: Sender/recipient roles are valid
3. **Policy Check**: Message type is allowed for sender
4. **Rate Limit**: Sender hasn't exceeded rate limits
5. **Delivery**: Message routed to recipient's inbox

## Response SLAs

### Response Time Requirements

| Message Type | SLA | Recipient |
|--------------|-----|-----------|
| `pricing_query` | 10 minutes | Finance |
| `brief_acknowledged` | 5 minutes | Content |
| `feature_brief_acknowledged` | 10 minutes | Build |
| `content_performance_query` | 2 minutes | Analytics |
| `behavior_query` | 2 minutes | Analytics |

### SLA Violations

- Logged in operational log
- Flagged in health dashboard
- Included in morning digest

## Sequencing Rules

See [[sequencing-rules]] for non-negotiable ordering constraints.

Key rules:
1. `pricing_query` → `pricing_response` → `project_brief` (Ops → Finance → Content/Build)
2. `project_complete` only after client confirms delivery
3. Invoice send requires HOLD release (two-stage approval)

## Related Pages

- [[message-contracts]] — Detailed contract schemas
- [[sequencing-rules]] — Ordering constraints
- [[message-matrix]] — Visual message flow
- [[mesh-coordinator]] — Gateway implementation
