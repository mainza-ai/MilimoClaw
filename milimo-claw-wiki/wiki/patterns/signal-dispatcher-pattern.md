# Signal Dispatcher Pattern

**Summary**: Inter-claw communication pattern used across all claws for consistent message format, logging, and error handling.

**Sources**: `milimo-blueprint/orchestrator/*/signal_dispatcher.py`, `milimo-blueprint/orchestrator/assistant/lucy.py`

**Last updated**: 2026-04-28

**Tags**: #patterns #signal-dispatcher #communication #mesh

---

## Purpose

Each claw has a `SignalDispatcher` that sends messages to other claws via the mesh gateway. This pattern ensures consistent message format, logging, and error handling.

## Implementation

Each claw implements its own SignalDispatcher:

| Claw | Class | File |
|------|-------|------|
| Ops | `OpsSignalDispatcher` | `ops/signal_dispatcher.py` |
| Finance | `FinanceSignalDispatcher` | `finance/signal_dispatcher.py` |
| Analytics | `AnalyticsSignalDispatcher` | `analytics/signal_dispatcher.py` |
| Build | `BuildSignalDispatcher` | `build/signal_dispatcher.py` |
| Assistant | `LucyAssistant` (dispatch methods) | `assistant/lucy.py` |

## Common Behaviors

All SignalDispatchers share these traits:

1. **Mesh Gateway** — All sends go through `MeshGateway.send()`
2. **Operational Logging** — Every dispatch logged to `operational.log`
3. **Error Resilience** — Never raises on failure, logs and continues
4. **Message ID** — UUID-based message tracking
5. **Timestamp** — ISO 8601 timestamps

## Message Format

```python
{
    "message_id": "abc123def456",
    "sender_role": "ops",
    "recipient_role": "finance",
    "message_type": "pricing_query",
    "payload": {...},
    "squad_id": "squad-001",
    "timestamp": "2026-01-15T10:30:00Z"
}
```

## Example: OpsSignalDispatcher

### Message Types

| Method | Message Type | Recipient |
|--------|--------------|-----------|
| `send_project_brief()` | `brief` | Content, Build |
| `send_feature_brief()` | `feature_brief` | Build |
| `send_pricing_query()` | `pricing_query` | Finance |
| `send_project_complete()` | `project_complete` | Finance |
| `send_client_health_signal()` | `client_health_signal` | Analytics |
| `send_client_onboarded()` | `client_onboarded` | Analytics |

### Pricing Confirmation

Ops enforces pricing confirmation before sending `project_brief`:

```python
def send_project_brief(...):
    if not self._is_pricing_confirmed(project_id):
        raise PricingNotConfirmedError(
            "Cannot send project_brief: pricing_response not confirmed"
        )
```

Confirmation tracked in `/sandbox/.openclaw-data/milimo/claws/ops/pricing_confirmed/{project_id}.json`

## Error Handling

```python
try:
    success = self._gateway.send(message)
    if not success:
        logger.error("Failed to send %s", message_type)
        # Log to operational.log
except Exception as e:
    logger.error("Exception sending %s: %s", message_type, e)
    # Log to operational.log
    # Never re-raise
```

## Relationships

- Used by: All 6 claws for inter-claw communication
- Depends on: `MeshGateway` protocol
- Logs to: `OperationalLog` for each claw

## Source Files

- `milimo-blueprint/orchestrator/ops/signal_dispatcher.py`
- `milimo-blueprint/orchestrator/finance/signal_dispatcher.py`
- `milimo-blueprint/orchestrator/analytics/signal_dispatcher.py`
- `milimo-blueprint/orchestrator/build/signal_dispatcher.py`
