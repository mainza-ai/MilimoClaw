# Mesh Coordinator

**Summary**: Central routing and coordination for inter-claw messages.

**Sources**:
- `milimo-blueprint/orchestrator/mesh.py`
- `raw/ARCHITECTURE.md`

**Last updated**: 2026-04-23

**Tags**: #architecture #mesh #coordination #routing

---

## Overview

The Mesh Coordinator is the central hub for all inter-claw communication. It routes messages between claws, enforces policies, and maintains the message queue.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ MESH COORDINATOR │
│ │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Content │ │ Ops │ │Analytics │ │ Finance │ │
│ │ Claw │ │ Claw │ │ Claw │ │ Claw │ │
│ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│ │ │ │ │ │
│ └───────────────┴───────────────┴───────────────┘ │
│ │ │
│ ┌──────┴──────┐ │
│ │ MESH │ │
│ │ COORDINATOR│ │
│ │ │ │
│ │ - Routing │ │
│ │ - Validate │ │
│ │ - Policy │ │
│ │ - Queue │ │
│ └──────┬──────┘ │
│ │ │
│ ┌────────┴────────┐ │
│ │ Build Claw │ │
│ │ (Tech squads) │ │
│ └────────┬────────┘ │
│ │ │
│ ┌────────┴────────┐ │
│ │ Assistant Claw │ │
│ │ (Operator bridge)│ │
│ └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Message Router

Routes messages to correct recipients based on `recipient_role`.

```python
def route_message(message: ClawMessage) -> DeliveryResult:
    """Route message to recipient's inbox."""
    recipient = message.recipient_role
    sender = message.sender_role

    # Validate contract
    if not validate_contract(message):
        return DeliveryResult(status="invalid", error="Contract validation failed")

    # Check policy
    if not policy_allows(message):
        return DeliveryResult(status="denied", error="Policy denied")

    # Deliver to inbox
    return deliver_to_inbox(message)
```

### 2. Contract Validator

Validates messages against their contract schemas.

```python
def validate_contract(message: ClawMessage) -> bool:
    """Validate message against its contract."""
    contract = CONTRACTS.get(message.message_type)
    if not contract:
        return False

    # Check sender/recipient roles
    if message.sender_role not in contract.sender_roles:
        return False
    if message.recipient_role not in contract.recipient_roles:
        return False

    # Validate payload schema
    return validate_payload(message.payload, contract.payload_schema)
```

### 3. Policy Enforcer

Enforces network and communication policies.

```python
def policy_allows(message: ClawMessage) -> bool:
    """Check if policy allows this message."""
    # Check message type is allowed for sender
    sender_policy = load_policy(message.sender_role)
    if message.message_type not in sender_policy.allowed_outbound:
        return False

    # Check recipient accepts this message type
    recipient_policy = load_policy(message.recipient_role)
    if message.message_type not in recipient_policy.allowed_inbound:
        return False

    return True
```

### 4. Message Queue

Manages inbox directories for each claw.

```
/sandbox/.milimo/mesh/
├── inbox/
│ ├── content/
│ ├── ops/
│ ├── analytics/
│ ├── finance/
│ ├── build/
│ └── assistant/
├── outbox/
├── heartbeats/
└── logs/
└── launcher.log
```

## Message Flow

### Sending a Message

```
1. Claw creates ClawMessage
2. Calls mesh_sender(message_type, target, payload)
3. Mesh Coordinator receives message
4. Validates against contract
5. Checks policy
6. Routes to recipient's inbox
7. Returns DeliveryResult
```

### Receiving a Message

```
1. InboxPoller checks inbox directory
2. New message file detected
3. Message parsed and validated
4. Handler looked up by message_type
5. Handler processes message
6. Result logged to operational log
7. Message moved to processed/
```

## Error Handling

### Delivery Failures

| Error | Cause | Recovery |
|-------|-------|----------|
| `invalid` | Contract validation failed | Fix message schema |
| `denied` | Policy blocked message | Check policy config |
| `timeout` | Recipient not responding | Retry with backoff |
| `queue_full` | Inbox directory full | Clear processed messages |

### Retry Logic

```python
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

def send_with_retry(message: ClawMessage) -> DeliveryResult:
    for attempt in range(MAX_RETRIES):
        result = route_message(message)
        if result.status == "delivered":
            return result
        time.sleep(RETRY_DELAY * (attempt + 1))
    return DeliveryResult(status="failed", error="Max retries exceeded")
```

## Health Monitoring

### Heartbeat System

Each claw emits a heartbeat every 30 seconds:

```json
{
    "claw": "content",
    "timestamp": "2026-04-14T12:00:00Z",
    "status": "healthy",
    "metrics": {
        "messages_processed": 42,
        "errors": 0
    }
}
```

### Stale Detection

Claws not emitting heartbeats for 90+ seconds are marked unhealthy.

## Related Pages

- [[inter-claw-communication]] — Message contract system
- [[message-contracts]] — Contract schemas
- [[sandbox-isolation]] — Isolation details
- [[war-room]] — Human oversight interface
- [[assistant-lucy]] — Assistant Claw (Lucy)
