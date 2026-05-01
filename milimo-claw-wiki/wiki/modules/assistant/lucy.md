# lucy

**Summary**: Runtime coordinator for the Lucy assistant — bridges operator messages (OpenShell channel delivery) to claw queries/tasks via the mesh.

**Sources**: `milimo-blueprint/orchestrator/assistant/lucy.py`

**Last updated**: 2026-04-29

**Tags**: #module #assistant #lucy

---

## Purpose

The Lucy runtime coordinator receives operator messages delivered by OpenShell channel messaging (Telegram, Discord, Slack), routes them to the appropriate claw as `assistant_query` or `assistant_task` messages via the mesh, collects responses, and returns consolidated results.

Lucy does **not** poll messaging APIs directly. OpenShell delivers inbound messages and relays outbound responses.

## Location

**File**: `milimo-blueprint/orchestrator/assistant/lucy.py`

---

## Key Classes

### PendingQuery

Tracks a dispatched query awaiting claw responses. Each query has a TTL of 60 seconds (`RESPONSE_TIMEOUT_SECONDS`).

```python
class PendingQuery:
    def __init__(self, query_id, original_text, target_roles, created_at=None):
        self.query_id: str
        self.original_text: str
        self.target_roles: list[str]
        self.created_at: float
        self.responses: dict[str, dict] = {}
        self.responded: bool = False

    @property
    def is_complete -> bool  # All target_roles have responded

    @property
    def is_expired -> bool   # Older than RESPONSE_TIMEOUT_SECONDS

    def add_response(sender_role, payload) -> None
```

### LucyAssistant

Main coordinator that manages Lucy's lifecycle, dispatch, and message handling.

```python
class LucyAssistant:
    def __init__(self, squad_id, mesh_gateway, inbox_dir=None, base_path=None):
        self._squad_id: str
        self._mesh_gateway: Any           # RealMeshGateway instance
        self._inbox_dir: Path             # ~/.milimo/mesh/inbox/assistant/
        self._base_path: Path             # claw_base("assistant")
        self._pending: dict[str, PendingQuery]
        self._running: bool
        self._started: bool
```

---

## Key Methods

| Method | Purpose |
|--------|---------|
| `startup()` | Initialize Lucy, set running state |
| `shutdown()` | Stop Lucy, clear running state |
| `handle_inbound(raw_message)` | Process `assistant_response` from claws, collect into pending queries |
| `dispatch_query(query_text, target_roles=None)` | Send `assistant_query` to one or more claws |
| `dispatch_task(task_description, target_role, deadline="")` | Send `assistant_task` to a specific claw |
| `process_operator_message(text)` | Parse operator input: `@role` targeting, status keywords, general queries |
| `cleanup_expired()` | Remove pending queries past TTL, return count |

---

## Message Routing

### Operator Message Parsing

| Input Pattern | Action | Example |
|---------------|--------|---------|
| `"status"` / `"squad status"` / `"report"` | `dispatch_query` to all claws | `"status"` |
| `"@role"` (no body) | `dispatch_query` to that claw | `"@content"` |
| `"@role <task_keyword> ..."` | `dispatch_task` to that claw | `"@finance generate invoice for X"` |
| `"@role <question>"` | `dispatch_query` to that claw | `"@content how's the draft?"` |
| Any other text | `dispatch_query` to all claws | `"What's happening?"` |

**Task keywords**: `do`, `create`, `generate`, `send`, `schedule`, `start`, `build`

### Inbound Processing

`handle_inbound()` processes `assistant_response` messages from claws:

1. Look up `original_message_id` in pending queries
2. Add response to `PendingQuery`
3. If all targets responded → consolidate and return
4. If expired → consolidate with partial results
5. Unknown message types → `status: "unknown_type"`, `action: "ignored"`

### Silent Response Handling

When a claw returns an empty or `None` response, Lucy returns a diagnostic dict with `status`, `role`, and `message_type` fields instead of propagating silence.

---

## Consolidation

`_consolidate()` merges claw responses into a single result:

```python
{
    "query_id": "...",
    "original_text": "...",
    "responses": {
        "content": "status=ok, action=draft_ready",
        "ops": "status=ok, components={...}"
    },
    "missing": ["finance"]  # Claws that didn't respond
}
```

---

## Network Access

Lucy has broader network access than other claws (see [[assistant-lucy]] for full table). Messaging to the operator uses OpenShell channel messaging — not direct API calls.

---

## Dependencies

- `milimo_paths.claw_base` — Base path resolution for assistant claw
- `RealMeshGateway` — Inter-claw message dispatch
- `logging` — Operation logging
- `uuid` — Query/message ID generation

---

## Related Pages

- [[assistant-lucy]] — High-level claw documentation
- [[assistant-system]] — Assistant setup and configuration
- [[message-contracts]] — Message schemas
- [[mesh-coordinator]] — Mesh gateway details
