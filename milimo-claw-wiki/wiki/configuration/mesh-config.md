# Mesh Configuration

**Summary**: Inter-claw message routing and escalation rules.

**Sources**:
- `milimo-blueprint/mesh_config.yaml`

**Last updated**: 2026-05-06

**Tags**: #configuration #mesh #routing

## Purpose

Defines the message matrix showing which claws can send which message types to which recipients. Includes escalation rules for high-stakes actions.

## File Location

`milimo-blueprint/mesh_config.yaml`

## Message Matrix

### Content Claw Sends

| Recipient | Message Types |
|-----------|--------------|
| Ops | `deliverable`, `deliverable_complete` |
| Analytics | `query`, `content_performance_query`, `performance_signal` |
| War Room | `draft_ready` |
| Assistant | `assistant_response` |

### Ops Claw Sends

| Recipient | Message Types |
|-----------|--------------|
| Content | `brief`, `project_brief`, `revision_request` |
| Finance | `query`, `pricing_query`, `project_complete` |
| Build | `brief`, `feature_brief` |
| Analytics | `client_onboarded` |
| War Room | `signal`, `deliverable` |
| Assistant | `assistant_response` |

### Analytics Claw Sends

| Recipient | Message Types |
|-----------|--------------|
| Content | `response`, `summary`, `performance_intel`, `client_health_signal` |
| Ops | `signal`, `client_health_signal_ops` |
| Finance | `summary`, `revenue_anomaly` |
| Build | `response`, `signal`, `retention_signals` |
| War Room | `signal`, `summary` |
| Assistant | `assistant_response` |

### Finance Claw Sends

| Recipient | Message Types |
|-----------|--------------|
| Ops | `response`, `signal`, `pricing_response`, `invoice_ready` |
| Analytics | `summary`, `revenue_summary` |
| War Room | `signal`, `deliverable`, `finance_summary`, `overdue_alert` |
| Assistant | `assistant_response` |

### Build Claw Sends

| Recipient | Message Types |
|-----------|--------------|
| Ops | `signal`, `deliverable`, `deploy_complete` |
| Analytics | `query`, `behavior_query` |
| Content | `summary`, `shipping_summary` |
| War Room | `signal`, `deliverable`, `tool_proposal` |
| Assistant | `assistant_response` |

### Assistant Sends

| Recipient | Message Types |
|-----------|--------------|
| Content | `assistant_query`, `assistant_task` |
| Ops | `assistant_query`, `assistant_task` |
| Analytics | `assistant_query`, `assistant_task` |
| Finance | `assistant_query`, `assistant_task` |
| Build | `assistant_query`, `assistant_task` |
| War Room | `assistant_response` |

## Message Types Requiring Approval

| Message Type | Description |
|--------------|-------------|
| `deliverable` | Completed work for review |
| `draft_ready` | Content draft ready |
| `invoice_ready` | Invoice for approval |
| `tool_proposal` | Evolution-generated tool |

## Escalation Rules

| Trigger | Action | Description |
|---------|--------|-------------|
| `invoice_over_500` | VETO | Invoice >$500 requires squad approval |
| `client_offboarding` | HOLD | Requires explicit confirmation |
| `brand_voice_change` | HOLD | Requires explicit confirmation |
| `payment_execution` | VETO | Requires squad approval |
| `rate_change` | VETO | Pricing changes require approval |
| `external_data_sharing` | VETO | Sharing data externally requires approval |

## Health Check

| Parameter | Value |
|-----------|-------|
| `interval_seconds` | 30 |
| `timeout_seconds` | 10 |
| `unhealthy_threshold` | 3 |
| `recovery_action` | notify_war_room |

## Relationships

- Used by: [[mesh-coordinator]] — Message routing
- Used by: [[message-contracts]] — Schema definitions
- Related: [[claw-schema]] — Role definitions

## Source

`milimo-blueprint/mesh_config.yaml`

> **YAML Indentation Note** (2026-05-06): The `message_matrix` key's children must be indented with 2 spaces under `message_matrix:`. A previous version had the sub-keys (`content:`, `ops:`, etc.) at root level, causing PyYAML to parse `message_matrix` as `None` — resulting in `AttributeError: 'NoneType' object has no attribute 'get'` in [[contracts]] validation.
