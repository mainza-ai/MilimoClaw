# Message Contracts

**Summary**: Complete schemas for all 24+ inter-claw message types.

**Sources**:
- `milimo-blueprint/orchestrator/contracts.py`
- `raw/AGENTS.md`

**Last updated**: 2026-05-24

**Tags**: #coordination #contracts #messaging

---

## Overview

All inter-claw communication uses typed message contracts. Each message type has a defined schema for sender, recipient, and payload structure.

## Message Structure

Every message includes these fields:

```python
{
    "message_id": str,        # UUID
    "message_type": str,      # Contract key
    "sender_role": str,       # Sending claw
    "recipient_role": str,    # Receiving claw
    "timestamp": str,         # ISO 8601
    "payload": dict           # Type-specific data
}
```

## Content Claw Messages

### `draft_ready`

From: Content Claw → To: War Room

```python
{
    "draft_id": str,
    "draft_type": str,  # "social_post" | "proposal" | "campaign"
    "content_preview": str,
    "platform": str | None,
    "client_id": str | None,
}
```

### `brief_acknowledged`

From: Content Claw → To: Ops Claw

```python
{
    "brief_id": str,
    "acknowledged_at": str,
    "estimated_completion": str,
}
```

### `deliverable_complete`

From: Content Claw → To: Ops Claw

```python
{
    "project_id": str,
    "deliverable_type": str,
    "completed_at": str,
    "published_url": str | None,
}
```

### `performance_signal`

From: Content Claw → To: Analytics Claw

```python
{
    "content_id": str,
    "platform": str,
    "metrics": {
        "views": int,
        "engagement": int,
        "clicks": int,
    },
    "published_at": str,
}
```

---

## Ops Claw Messages

### `project_brief`

From: Ops Claw → To: Content Claw / Build Claw

```python
{
    "project_id": str,
    "client_id": str,
    "brief_type": str,  # "content" | "build"
    "requirements": dict,
    "deadline": str,
    "budget": float,
    "priority": str,  # "high" | "medium" | "low"
}
```

### `feature_brief`

From: Ops Claw → To: Build Claw

```python
{
    "feature_id": str,
    "project_id": str,
    "client_id": str,
    "requirements": dict,
    "deadline": str,
}
```

### `pricing_query`

From: Ops Claw → To: Finance Claw

```python
{
    "project_id": str,
    "client_id": str,
    "scope": {
        "type": str,
        "complexity": str,
        "timeline": str,
    },
}
```

### `project_complete`

From: Ops Claw → To: Finance Claw

```python
{
    "project_id": str,
    "client_id": str,
    "delivered_at": str,
    "client_confirmed": bool,  # MUST be True
}
```

---

## Analytics Claw Messages

### `performance_intel`

From: Analytics Claw → To: Content Claw

```python
{
    "report_id": str,
    "top_performing": list[dict],
    "recommendations": list[str],
    "opportunity_score": float,
}
```

### `client_health_alert`

From: Analytics Claw → To: Ops Claw

```python
{
    "client_id": str,
    "health_score": float,  # < 6.0 triggers alert
    "trend": str,  # "declining" | "improving" | "stable"
    "factors": list[str],
}
```

### `revenue_anomaly`

From: Analytics Claw → To: Finance Claw

```python
{
    "anomaly_type": str,  # "positive" | "negative"
    "current_value": float,
    "baseline_value": float,
    "detected_at": str,
}
```

---

## Finance Claw Messages

### `pricing_response`

From: Finance Claw → To: Ops Claw

```python
{
    "query_id": str,          # Required (alias "project_id" accepted)
    "floor": float,           # Required (alias "floor_price" accepted)
    "ceiling": float,         # Required (alias "ceiling_price" accepted)
    "notes": str | None,      # Optional
    "valid_until": str | None # Optional
}
```

### `invoice_ready`

From: Finance Claw → To: Ops Claw

```python
{
    "invoice_id": str,
    "project_id": str,
    "amount": float,
    "stage": str,  # "stage_1_pending"
}
```

### `payment_overdue`

From: Finance Claw → To: Ops Claw

```python
{
    "invoice_id": str,
    "client_id": str,
    "amount": float,
    "days_overdue": int,
    "escalation_level": int,
}
```

### `spend_request`

From: Any claw → To: Finance Claw

```python
{
    "spend_id": str,           # Optional — generated if omitted
    "merchant_name": str,      # Required — who gets paid
    "merchant_url": str,       # Required — Link destination URL
    "amount_cents": int,       # Required — amount in cents
    "currency": str,           # Optional — default "usd"
    "justification": str,      # Required — one sentence: what + why
    "payment_method_id": str,  # Optional — specific payment method
    "credential_type": str,    # Optional — "card" (default) | "shared_payment_token"
}
```

Response: `spend_queued_review` or `spend_blocked` (over daily cap).

### `spend_review_decision`

From: War Room → To: Finance Claw

```python
{
    "action_id": str,       # Required — action id from the REVIEW queue
    "decision": str,        # "approve" | "edit" | "block"
    "amount_cents": int,    # Required for "edit" — new amount
    "justification": str,   # Required for "edit" — new justification
    "reason": str,          # Required for "block"
}
```

Response: `spend_moved_to_hold`, `spend_review_edited`, or `spend_blocked`.

### `spend_hold_decision`

From: War Room → To: Finance Claw

```python
{
    "action_id": str,       # Required — action id from the HOLD queue
    "decision": str,        # "release" | "cancel"
    "reason": str,          # Required for "cancel"
}
```

Response: `spend_completed` or `spend_release_failed` (Link app denied/timed out).

---

## Build Claw Messages

### `deploy_complete`

From: Build Claw → To: Ops Claw

```python
{
    "deployment_id": str,
    "project_id": str,
    "environment": str,  # "production" | "staging"
    "deployed_at": str,
    "url": str,
}
```

### `shipping_summary`

From: Build Claw → To: Content Claw

```python
{
    "week_ending": str,
    "features_shipped": list[dict],
    "bugs_fixed": int,
    "prs_merged": int,
}
```

---

## Assistant Messages

### `assistant_query`

From: Assistant → To: Any Claw

```python
{
    "query_type": str,
    "target_entity": str | None,
    "filters": dict | None,
}
```

### `assistant_task`

From: Assistant → To: Any Claw

```python
{
    "task_type": str,
    "target_entity": str | None,
    "parameters": dict,
    "priority": str,
}
```

### `assistant_response`

From: Any Claw → To: Assistant

```python
{
    "query_id": str,          # Required (alias "original_message_id" accepted)
    "response": str | dict,   # Required
    "data": dict | None,      # Optional
    "confidence": float | None, # Optional
    "generated_at": str | None # Optional (ISO timestamp)
}
```

---

## Related Pages

- [[sequencing-rules]] — Message ordering
- [[message-matrix]] — Visual flow
- [[inter-claw-communication]] — Gateway system
- [[mesh-coordinator]] — Routing
