# Comms Manager

Manages all client communication with approval routing.

## Purpose

Handles inbound/outbound client messages with automatic classification. Routes routine messages through AUTO approval, non-routine through REVIEW. Never references pricing without confirmed `pricing_response` on file.

## Message Classification

| Type | Routing | Examples |
|------|---------|----------|
| `project_update` | AUTO | Status updates, progress inquiries |
| `schedule_confirmation` | AUTO | Timing confirmations |
| `file_delivery_notification` | AUTO | Delivery confirmations |
| `acknowledgment` | AUTO | Simple thanks, acknowledgments |
| `question` | REVIEW | Requires detailed response |
| `concern` | REVIEW | Client dissatisfaction |
| `request` | REVIEW | New requests |

## Methods

| Method | Purpose |
|--------|---------|
| `handle_inbound()` | Process incoming client message |
| `draft_response()` | Generate AI response draft |
| `send_auto_response()` | Send automatic reply |
| `send_deep_work_response()` | Send deep work auto-reply |
| `is_deep_work_active()` | Check deep work mode status |
| `log_outbound_message()` | Log sent message |

## Pricing Detection

Automatically detects pricing questions via:
1. LLM inference with `data_type="pricing_question_detection"`
2. Fallback keyword matching: "price", "cost", "budget", "how much", "rate", "charge", "fee"

On detection:
1. Sends holding response
2. Queues pricing inquiry for review
3. Sends `pricing_query` to Finance Claw via SignalDispatcher

## Deep Work Mode

When active (`config.json` → `deep_work.active: true`):
- Auto-responses sent without approval
- Uses template from `deep-work-response.md`
- Includes resume date in message

## Dependencies

- `OpsFilesystemInit` — Filesystem abstraction
- `OpsApprovalHandler` — Approval routing
- `OpsOperationalLog` — Action logging
- `OpsCommsLog` — Communication history
- `OpsSignalDispatcher` — Inter-claw messaging
- `ScopeMonitor` — Scope creep detection

## File Locations

```
/sandbox/ops/
├── logs/
│   ├── operational.log
│   └── comms.log
├── templates/
│   ├── deep-work-response.md
│   └── change-order-template.md
└── clients/
    └── {client_id}/
        └── comms-history.jsonl
```

## Relationships

- Uses: [[scope-monitor]] — Checks messages for scope creep
- Uses: [[signal-dispatcher-pattern|SignalDispatcher]] — Sends pricing queries
- Routes via: [[approval-handler]] — REVIEW/AUTO routing

## Source

`milimo-blueprint/orchestrator/ops/comms_manager.py`
