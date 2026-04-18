# Scope Monitor

Detects scope creep in client communications.

## Purpose

Analyzes every client message against original project brief. High-confidence detections (>0.7) immediately queue a HOLD change order — never auto-handled.

## Constants

- **DETECTION_THRESHOLD = 0.7** — Confidence threshold for HOLD

## ScopeCreepDetection Data Class

```python
@dataclass
class ScopeCreepDetection:
    project_id: str
    client_id: str
    original_scope: str
    new_request: str
    confidence: float
    detected_at: str
```

## Methods

| Method | Purpose |
|--------|---------|
| `check_message()` | Analyze message for scope creep |
| `draft_change_order()` | Generate change order document |
| `handle_scope_pricing_response()` | Update change order with pricing |
| `get_pending_change_orders()` | List pending change orders |

## Detection Flow

1. Load original brief from `brief.json`
2. Send to inference with `data_type="scope_creep_detection"`
3. If `confidence > 0.7`:
   - Queue HOLD change order
   - Send `pricing_query` to Finance Claw
   - Save detection to `scope_creep/detection_{timestamp}.json`

## Change Order Flow

```
Detection → HOLD queued → pricing_query sent
                ↓
Pricing response received → Change order updated → HOLD re-queued
```

## Inference Prompt

```
Analyze this client message for scope creep against the original project brief.

ORIGINAL PROJECT BRIEF: {original_scope}
NEW CLIENT MESSAGE: {message}

Determine:
1. Is this request outside the original scope?
2. What is the new request?
3. How confident are you? (0.0-1.0)
```

## File Locations

```
/sandbox/ops/clients/{client_id}/{project_id}/
├── brief.json                    # Original scope
└── scope_creep/
    └── detection_20260115_143052.json
```

## Relationships

- Used by: [[comms-manager]] — Called on every inbound message
- Sends to: [[signal-dispatcher-pattern|SignalDispatcher]] — Pricing queries
- Routes via: [[approval-handler]] — HOLD queue

## Source

`milimo-blueprint/orchestrator/ops/scope_monitor.py`
