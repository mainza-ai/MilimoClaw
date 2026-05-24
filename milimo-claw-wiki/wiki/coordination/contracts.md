# contracts

**Summary**: Typed message contract definitions for inter-claw mesh communication.

**Sources**: `milimo-blueprint/orchestrator/contracts.py`

**Last updated**: 2026-05-24

**Tags**: #coordination #contracts

---

## Purpose

Defines and validates typed message contracts for squad mesh communication. Each message is validated against sender/recipient policies before delivery.

## Location

**File**: `orchestrator/contracts.py`

---

## Key Components

### ClawMessage

Base message structure for all inter-claw communication.

```python
@dataclass
class ClawMessage:
    sender_role: str
    recipient_role: str
    message_type: str
    payload: dict[str, Any]
    squad_id: str
    message_id: str = ""  # Auto-generated UUID
    timestamp: str = ""   # Auto-generated ISO timestamp
    priority: str = "AUTO"  # AUTO, REVIEW, HOLD
```

### ContractValidator

Validates messages against mesh configuration.

```python
class ContractValidator:
    @classmethod
    def from_config_file(cls, path: str | Path) -> ContractValidator: ...

    def validate(self, message: ClawMessage) -> ValidationResult: ...
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    valid: bool
    reason: str
    message_id: str
    requires_approval: bool
```

---

## Valid Roles

### Senders
`content`, `ops`, `analytics`, `finance`, `build`, `assistant`

### Recipients
`content`, `ops`, `analytics`, `finance`, `build`, `assistant`, `war_room`

---

## Message Type Categories

### Content Claw Messages

| Type | From | To | Required Payload |
|------|------|-----|------------------|
| `draft_ready` | content | war_room | draft_id, platform, content_type |
| `content_performance_query` | content | analytics | query |
| `performance_signal` | content | analytics | post_id, platform, engagement_data |
| `brief_acknowledged` | content | ops | project_id, estimated_first_draft_time |
| `deliverable_complete` | content | ops | project_id, published_urls |

### Ops Claw Messages

| Type | From | To | Required Payload |
|------|------|-----|------------------|
| `project_brief` | ops | content/build | client_id, project_id, brief_text |
| `feature_brief` | ops | build | client_id, project_id, feature_description |
| `pricing_query` | ops | finance | project_id, scope_description |
| `client_health_signal` | ops | analytics | client_id, health_score |
| `client_onboarded` | ops | analytics | client_id, niche, project_type |

### Analytics Claw Messages

| Type | From | To | Required Payload |
|------|------|-----|------------------|
| `performance_intel` | analytics | content | top_formats, top_times |
| `retention_signals` | analytics | build | feature_adoption_rates |
| `client_health_alert` | analytics | ops | client_id, health_score |
| `revenue_anomaly` | analytics | finance | anomaly_type, current_value |

### Finance Claw Messages

| Type | From | To | Required Payload |
|------|------|-----|------------------|
| `pricing_response` | finance | ops | query_id, floor, ceiling *(or project_id, floor_price, ceiling_price)* |
| `invoice_ready` | finance | ops | project_id, client_id, amount |
| `payment_overdue` | finance | ops | client_id, invoice_id, days_overdue |
| `revenue_summary` | finance | analytics | week_total, invoices_paid |

### Build Claw Messages

| Type | From | To | Required Payload |
|------|------|-----|------------------|
| `deploy_complete` | build | ops | project_id, deploy_url |
| `shipping_summary` | build | content | week_of, prs_merged |
| `behavior_query` | build | analytics | query, lookback_days |

### Assistant Messages

| Type | From | To | Required Payload |
|------|------|-----|------------------|
| `assistant_query` | assistant | any | query_type |
| `assistant_task` | assistant | any | task_description, deadline |
| `assistant_response` | any | assistant | query_id, response *(or original_message_id, response)* |

---

## Priority Levels

| Priority | Description | War Room Behavior |
|----------|-------------|-------------------|
| `VETO` | Any squad member can block; requires unanimous approval | Red priority, blocks all |
| `AUTO` | Automatic, logged | Visible in morning digest |
| `REVIEW` | Requires approval | Queued for operator review |
| `HOLD` | Blocks until released | Requires explicit release |

---

## SLA Requirements

| Message Type | SLA |
|--------------|-----|
| `brief_acknowledged` | 5 minutes |
| `pricing_response` | 10 minutes |
| `behavior_query_response` | 2 minutes |

---

## Validation Flow

```
1. Check sender_role is valid sender
2. Check recipient_role is valid recipient
3. Check message_type is valid
4. Check message_type is allowed for sender → recipient
5. Check required_payload fields present
6. Return ValidationResult
```

---

## Configuration File

`mesh_config.yaml` defines allowed message flows:

```yaml
message_flows:
  - sender: ops
    recipient: content
    allowed_types: [project_brief, revision_request]

  - sender: content
    recipient: analytics
    allowed_types: [performance_signal, content_performance_query]
```

---

## Dependencies

- `mesh_config.yaml` — Message flow configuration
- [[mesh-coordinator]] — Message routing

## Related Pages

- [[message-contracts]] — Full message documentation
- [[sequencing-rules]] — Message ordering
- [[mesh-coordinator]] — Routing implementation
