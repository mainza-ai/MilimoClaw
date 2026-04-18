# Operation Log

**Summary**: Structured logging for all claw actions, feeding the Evolution Cycle's Observe and Identify stages.

**Sources**: `milimo-blueprint/orchestrator/operation_log.py`

**Last updated**: 2026-04-15

**Tags**: #module #operations #logging #evolution

---

## Overview

`OperationLog` records every action taken by a claw with its outcome, human edits, and metrics. This data feeds the pattern detector for evolution.

**File**: `orchestrator/operation_log.py`

**Storage**: `~/.milimo/logs/{squadId}/{role}/operations.jsonl`

---

## Key Classes

### `ActionRecord`

Recorded claw action.

| Field | Type | Description |
|-------|------|-------------|
| action_type | str | Type of action |
| outcome | str | approved, edited, rejected, auto |
| edits | dict | Fields edited by human |
| metrics | dict | Performance metrics |
| payload | dict | Action data |
| claw_role | str | Claw identifier |
| timestamp | str | ISO timestamp |

### `CrossSignal`

Inter-claw signal from mesh.

| Field | Type | Description |
|-------|------|-------------|
| sender_role | str | Sending claw |
| signal_type | str | summary, signal, response |
| data | dict | Signal payload |
| timestamp | str | ISO timestamp |

### `ActionSummary`

Aggregated action statistics.

| Field | Type | Description |
|-------|------|-------------|
| total_actions | int | Total count |
| by_type | dict | Count by action type |
| by_outcome | dict | Count by outcome |
| approval_rate | float | Approved + auto / total |
| edit_rate | float | Edited / total |
| common_edits | dict | Most edited fields |
| metric_averages | dict | Average metrics |

---

### `OperationLog`

Main logging class.

```python
log = OperationLog(squad_id="my-squad", claw_role="content")

# Record action
log.record(ActionRecord(
    action_type="social_post_draft",
    outcome="edited",
    edits={"tone": "hype → educational"},
    metrics={"engagement_rate": 0.042}
))

# Get actions from past 7 days
window = log.get_window(days=7)

# Get summary
summary = log.get_action_summary(window)
print(f"Approval rate: {summary.approval_rate:.1%}")
```

**Methods**:

| Method | Purpose |
|--------|---------|
| `record(action)` | Record an action |
| `record_cross_signal(signal)` | Record mesh signal |
| `get_window(days)` | Get actions in window |
| `get_all()` | Get all actions |
| `get_cross_signals(days)` | Get mesh signals |
| `get_action_summary(actions)` | Compute statistics |
| `count()` | Count total actions |

---

## Outcomes

| Outcome | Description |
|---------|-------------|
| approved | Human approved without changes |
| edited | Human approved with changes |
| rejected | Human rejected |
| auto | Auto-approved (no human review) |

---

## Evolution Integration

Operation logs feed evolution:

1. **Observe**: Read actions from JSONL
2. **Identify**: Find patterns in edits/outcomes
3. **Propose**: Generate tool improvements based on patterns

### Pattern Detection Examples

- High edit rate on specific field → Improve that aspect
- Consistent rejection pattern → Add validation
- Low approval rate → Adjust thresholds

---

## File Structure

```
~/.milimo/logs/
└── my-squad/
    ├── content/
    │   ├── operations.jsonl
    │   └── cross_signals.jsonl
    ├── ops/
    │   ├── operations.jsonl
    │   └── cross_signals.jsonl
    └── ...
```

---

## Related Pages

- [[metrics-collector]] — Performance metrics
- [[evolution-cycle]] — Sunday evolution
- [[pattern-detection]] — Pattern identification
- [[tool-generation]] — Tool proposals

---

## See Also

- `orchestrator/metrics_collector.py` — Metrics collection
- `orchestrator/evolution/tool_proposal.py` — Tool proposals
