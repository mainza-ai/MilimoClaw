# Solo Privacy

**Summary**: Inference routing with locked routes and cost guard for solo operator mode.

**Sources**: `milimo-blueprint/orchestrator/solo_privacy.py`

**Last updated**: 2026-04-23

**Tags**: #solo #privacy #routing #cost-guard

---

## Purpose

Routes inference requests based on data type sensitivity. Enforces locked routes (financial_data, source_code → local) and manages cloud token budget.

## Locked Routes

| Data Type | Route | Reason |
|-----------|-------|--------|
| `financial_data` | LOCAL | Privacy requirement |
| `source_code` | LOCAL | Security requirement |

Attempting to override locked routes raises `PrivacyPolicyViolationError`.

## Default Routes

| Data Type | Default Route |
|-----------|---------------|
| `client_facing_drafts` | CLOUD |
| `internal_ideation` | LOCAL |
| `client_records` | LOCAL |
| `analytics_synthesis` | LOCAL |
| `public_docs_changelogs` | CLOUD |

## Cost Guard

Manages daily cloud token budget:

| Parameter | Default |
|-----------|---------|
| `daily_budget` | 50,000 tokens |
| `alert_percent` | 80% |
| `fallback_strategy` | LOCAL |
| `never_block` | True |

### Budget Check

```python
def check_budget() -> (allowed, is_alert):
    if used >= budget: return (False, False)
    if used >= alert_threshold: return (True, True)
    return (True, False)
```

### Fallback Strategies

| Strategy | Behavior |
|----------|----------|
| `LOCAL` | Fall back to local inference |
| `VLLM` | Use vLLM backend |
| `CLOUD` | Continue with cloud (dangerous) |
| `LIGHTER_PROMPT` | Trim context, use local |

## Route Enum

| Value | Meaning |
|-------|---------|
| `CLOUD` | Cloud (NEMOCLAW_MODEL) |
| `LOCAL` | Local NIM (NEMOCLAW_MODEL) on RTX |
| `VLLM` | Local vLLM |

## Main Functions

| Function | Purpose |
|----------|---------|
| `route()` | Determine inference route for data type |
| `get_budget_status()` | Current budget status |
| `is_locked_route()` | Check if data type is locked |
| `route_batch()` | Route multiple data types |

## RoutingDecision Data Class

```python
@dataclass
class RoutingDecision:
    data_type: str
    route: Route
    reason: str
    timestamp: datetime
    cost_tokens: int
    budget_exceeded: bool
```

## Relationships

- Uses: [[solo-init]] — Configuration loading
- Used by: All claws — Inference routing
- Related: [[privacy-router]] — Base routing system

## Source

`milimo-blueprint/orchestrator/solo_privacy.py`
