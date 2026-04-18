# Message Matrix

**Summary**: Visual matrix of all inter-claw message flows.

**Sources**:
- `raw/AGENTS.md`
- [[message-contracts]]

**Last updated**: 2026-04-14

**Tags**: #reference #messages #matrix

---

## Complete Message Matrix

| From | To | Message Type | Trigger | SLA |
|------|-----|--------------|---------|-----|
| Content | War Room | `draft_ready` | Draft ready for review | Immediate |
| Content | Analytics | `content_performance_query` | Monday 06:00 + on demand | 2-min response |
| Content | Analytics | `performance_signal` | After every published post | Immediate |
| Content | Ops | `brief_acknowledged` | Within 5 min of project_brief | 5 min |
| Content | Ops | `deliverable_complete` | All deliverables published | Immediate |
| Ops | Content | `project_brief` | New project scoped | After pricing_response |
| Ops | Build | `project_brief` | New project scoped | After pricing_response |
| Ops | Build | `feature_brief` | New technical feature | After pricing_response |
| Ops | Finance | `pricing_query` | Before any proposal | 10-min response |
| Ops | Finance | `project_complete` | Client confirms delivery | Immediate |
| Ops | Analytics | `client_health_signal` | Weekly | Sunday |
| Ops | Analytics | `client_onboarded` | New client onboarded | Immediate |
| Analytics | Content | `performance_intel` | Weekly + opportunity | Sunday 02:05 |
| Analytics | Build | `retention_signals` | Weekly + churn anomaly | Sunday 02:05 |
| Analytics | Ops | `client_health_alert` | Health < 6.0 | Immediate |
| Analytics | Finance | `revenue_anomaly` | On anomaly detection | Immediate |
| Analytics | Content | `content_performance_response` | Query response | 2 min |
| Analytics | Build | `behavior_query_response` | Query response | 2 min |
| Finance | Ops | `pricing_response` | Within 10 min of query | 10 min |
| Finance | Ops | `invoice_ready` | After Stage 1 approval | Immediate |
| Finance | Ops | `payment_overdue` | On overdue detection | Immediate |
| Finance | Analytics | `revenue_summary` | Weekly + on payment | Sunday 03:00 |
| Build | Ops | `deploy_complete` | Production deploy | Immediate |
| Build | Ops | `feature_brief_acknowledged` | Within 10 min of feature_brief | 10 min |
| Build | Content | `shipping_summary` | Friday 17:00 | Friday 17:00 |
| Build | Analytics | `behavior_query` | Before sprint planning | 5-min timeout |
| Assistant | Any | `assistant_query` | Status request | 2 min |
| Assistant | Any | `assistant_task` | Task assignment | Async |
| Any | Assistant | `assistant_response` | Response to query | Varies |

---

## Visual Flow Diagram

```
                    ┌─────────────┐
                    │   War Room  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   Content   │ │     Ops     │ │   Finance   │
    │    Claw     │ │    Claw     │ │    Claw     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           │    draft_ready│               │
           │──────────────►│               │
           │               │               │
           │               │ project_brief │
           │◄──────────────│               │
           │               │               │
           │               │ pricing_query │
           │               │──────────────►│
           │               │               │
           │               │◄──────────────│
           │               │pricing_response│
           │               │               │
           ▼               ▼               ▼
    ┌─────────────────────────────────────────────┐
    │              Analytics Claw                  │
    │  (receives signals from all claws)          │
    └─────────────────────────────────────────────┘
```

---

## Message Categories

### Content Generation

- `project_brief` → Content/Build
- `brief_acknowledged` ← Content
- `draft_ready` → War Room
- `deliverable_complete` → Ops

### Financial

- `pricing_query` → Finance
- `pricing_response` ← Finance
- `invoice_ready` → Ops
- `payment_overdue` → Ops

### Intelligence

- `performance_signal` → Analytics
- `client_health_signal` → Analytics
- `revenue_summary` → Analytics
- `performance_intel` ← Analytics

### Development

- `feature_brief` → Build
- `feature_brief_acknowledged` ← Build
- `deploy_complete` → Ops
- `shipping_summary` → Content

---

## Related Pages

- [[message-contracts]] — Full schemas
- [[sequencing-rules]] — Ordering constraints
- [[inter-claw-communication]] — Gateway details
