# Assistant (Lucy)

**Summary**: Conversational assistant that bridges users to all claws — the primary user interface for MilimoClaw.

**Sources**:
- `milimo-blueprint/orchestrator/assistant/lucy.py`
- `milimo-blueprint/orchestrator/templates/assistant_system_prompt.md`
- `milimo-blueprint/policies/assistant-sandbox.yaml`

**Last updated**: 2026-04-23

**Tags**: #claw #assistant #lucy

---

## Role

Lucy is the **conversational assistant** that serves as the primary user interface for MilimoClaw. She bridges users to all claws through natural language conversation.

## Sandbox

**Mount**: `/sandbox/.openclaw/`

| Path | Purpose | Access |
|------|---------|--------|
| `/sandbox/.openclaw/` | Assistant state and configuration | Read-write |
| `/sandbox/.milimo/` | Mesh communication | Read-write |
| `/sandbox/clients/` | Client data (read-only) | Read-only |
| `/sandbox/content/drafts/` | Content drafts (read-only) | Read-only |
| `/sandbox/finance/revenue/` | Revenue data | Read-only |
| `/sandbox/build/prs/` | PR data | Read-only |
| `/sandbox/analytics/reports/` | Intelligence reports | Read-only |

## What It Does

- Provides natural language interface to all claws
- Sends `assistant_query` messages for status checks
- Sends `assistant_task` messages for task execution
- Routes user requests to appropriate claws
- Maintains conversation context and history
- Can read from cross-mounted directories for context

## What It Cannot Do

- Execute any action without claw involvement
- Modify client data directly
- Send invoices or make payments
- Deploy code directly
- Bypass the War Room for actions requiring approval

## Message Types

### Outbound Messages

| Message Type | To | Purpose |
|--------------|-----|---------|
| `assistant_query` | Any claw | Request status or state |
| `assistant_task` | Any claw | Request task execution |

### Inbound Messages

| Message Type | From | Handler |
|--------------|------|---------|
| `assistant_response` | Any claw | Process claw response |

## Communication Protocol

### Query Pattern

```
1. User asks Lucy: "What's the status of the Acme project?"
2. Lucy sends assistant_query to Ops Claw
3. Ops Claw responds with project status
4. Lucy presents information to user
```

### Task Pattern

```
1. User instructs Lucy: "Generate a social post for Acme's new product"
2. Lucy sends assistant_task to Content Claw
3. Content Claw queues task and responds
4. Lucy confirms task queued to user
5. Later: Content Claw sends draft_ready to War Room
6. User approves in War Room
7. Lucy can report result if asked
```

## Network Access

Lucy has broader network access than other claws:

| API | Purpose |
|-----|---------|
| NVIDIA NIM | Inference for conversation |
| Telegram Bot API | User messaging interface |
| GitHub API | Repository and PR information |
| Vercel API | Deployment status |
| Sentry API | Error tracking |
| Stripe API | Payment status (read-only) |

## Implementation

### Runtime Coordinator (lucy.py)

The `LucyAssistant` class in `milimo-blueprint/orchestrator/assistant/lucy.py` is the runtime coordinator that manages Lucy's lifecycle:

**Key Classes**:

| Class | Purpose |
|-------|---------|
| `TelegramBridge` | Polls Telegram Bot API for user messages, sends responses |
| `PendingQuery` | Tracks dispatched queries awaiting claw responses (with TTL) |
| `LucyAssistant` | Main coordinator: startup, shutdown, dispatch, telegram integration |

**Key Methods**:

| Method | Purpose |
|--------|---------|
| `startup()` | Initialize Telegram bridge, connect to mesh |
| `shutdown()` | Graceful cleanup of all resources |
| `handle_inbound(message)` | Route incoming mesh messages to handlers |
| `dispatch_query(target, query)` | Send assistant_query to a specific claw |
| `dispatch_task(target, task)` | Send assistant_task to a specific claw |
| `process_telegram_message(text)` | Parse user input and route to appropriate claw |
| `telegram_poll_loop()` | Background loop polling Telegram for new messages |
| `cleanup_expired()` | Remove expired pending queries past TTL |

**Silent Response Handling**: When a claw returns an empty or None response, Lucy returns a diagnostic dict with `status`, `role`, and `message_type` fields instead of propagating silence.

### System Prompt

Located at: `milimo-blueprint/orchestrator/templates/assistant_system_prompt.md`

The system prompt includes:
- Full command reference (41+ commands)
- Claw capabilities summary
- Message routing knowledge
- Response formatting rules

### Policy File

Located at: `milimo-blueprint/policies/assistant-sandbox.yaml`

Includes:
- Network egress policies for all APIs
- Filesystem access rules
- Process execution permissions
- Binary allowlist (including Node.js)

## Handled Issues

### Previous Problems (Now Fixed)

1. **Missing handlers in claws** — All claws now have `_handle_assistant_query` and `_handle_assistant_task` methods
2. **Network policy blocking Node.js** — `/usr/local/bin/node` added to GitHub API policy
3. **Approval blocking** — `assistant_query` and `assistant_task` now have `requires_approval: false` in mesh_config.yaml

## Key Files

- `milimo-blueprint/orchestrator/templates/assistant_system_prompt.md` — System prompt
- `milimo-blueprint/policies/assistant-sandbox.yaml` — Network policy
- `milimo-blueprint/mesh_config.yaml` — Message routing config

## Related Pages

- [[content-claw]] — Content generation tasks
- [[ops-claw]] — Project status queries
- [[analytics-claw]] — Report queries
- [[finance-claw]] — Payment status queries
- [[build-claw]] — PR and deploy status
- [[message-contracts]] — Message schemas
- [[network-egress]] — Network policy details

## See Also

- System prompt: `milimo-blueprint/orchestrator/templates/assistant_system_prompt.md`
- Policy: `milimo-blueprint/policies/assistant-sandbox.yaml`
- Troubleshooting: `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`
