# War Room Empty — Investigation Report

> **Date:** 2026-04-05
> **Issue:** The War Room TUI shows no pending actions, even though Lucy reported delivering a message (ID: `9fea0edbcba3`) to the build claw inbox.

---

## Root Cause

**Messages that require approval are never routed to the War Room.** They go directly to the claw's inbox, bypassing the War Room entirely.

The War Room TUI reads from `~/.milimo/mesh/inbox/war_room/` (`approval.ts:38-39`), but the mesh coordinator's `_write_message` method (`mesh.py:461-481`) only writes to the war_room inbox when `recipient_role == "war_room"`. For all other recipients, messages go directly to the claw's inbox — even when `needs_approval=True`.

### The Broken Flow

**What should happen:**
```
Message sent → needs_approval? → YES → War Room inbox → Operator approves → Claw inbox
                              → NO  → Claw inbox directly
```

**What actually happens:**
```
Message sent → Claw inbox directly (always)
```

The `requires_approval` flag is computed in `mesh.py:333` and returned in the `DeliveryResult`, but it is never used to change the routing destination.

---

## Three Specific Problems

### Problem 1: No War Room Routing for Approval-Required Messages

**File:** `milimo-blueprint/orchestrator/mesh.py:290-339`

The `send_message` method computes `needs_approval` but then sends to the claw inbox regardless:

```python
needs_approval = self._validator.requires_approval(message.message_type)

# 4. Send via gateway if connected, otherwise use file-based
if self._gateway and self._gateway.state == ConnectionState.CONNECTED:
    return self._send_via_gateway(message, needs_approval)
else:
    return self._send_via_file(message, needs_approval)  # Goes to claw inbox, not war room
```

The `_send_via_file` method calls `_write_message`, which writes to the recipient's inbox — not the War Room.

**Fix:** When `needs_approval=True`, write to `war_room` inbox instead of the claw inbox. On approval, the `ApprovalEngine.processDecision` (`approval.ts:141-181`) already moves the file from war_room inbox to the claw inbox.

### Problem 2: Assistant Message Types Not in the Message Matrix

**File:** `milimo-blueprint/mesh_config.yaml`

The `message_matrix` has no entry for `assistant` as a sender. The contract validator reads the matrix and checks:

```python
sender_routes = self._matrix.get(message.sender_role, {})  # "assistant" → {}
allowed_types = sender_routes.get(message.recipient_role, [])  # {} → []
# message_type not in [] → validation FAILS
```

This means `assistant_query` and `assistant_task` messages would be rejected by the contract validator if sent through a properly configured MeshCoordinator.

The `handle_send_to_claw` bridge command works around this by creating a MeshCoordinator with an empty config (`from_dict({}, ...)`), which also produces an empty matrix — so the same validation failure would occur there too.

**Fix:** Add `assistant` entry to the `message_matrix` in `mesh_config.yaml`:
```yaml
assistant:
  content: [assistant_query, assistant_task]
  ops: [assistant_query, assistant_task]
  analytics: [assistant_query, assistant_task]
  finance: [assistant_query, assistant_task]
  build: [assistant_query, assistant_task]
```

And add the message type configs:
```yaml
assistant_query:
  description: "Assistant query to a claw (read-only)"
  requires_approval: true
assistant_task:
  description: "Assistant task assignment to a claw"
  requires_approval: true
assistant_response:
  description: "Claw response to assistant query"
  requires_approval: false
```

### Problem 3: `send_to_claw` Uses Empty Mesh Config

**File:** `milimo-blueprint/orchestrator/bridge_cli.py:770`

```python
mesh = MeshCoordinator.from_dict({}, squad_id=squad_id, mesh_dir=str(mesh_dir))
```

This creates a MeshCoordinator with no message matrix and no message types config. The `requires_approval` check in `send_message` always returns `False` because `self._types` is empty. So even if Problem 1 were fixed, messages sent via `send_to_claw` would still bypass the War Room because the coordinator doesn't know they require approval.

**Fix:** Load the actual mesh config instead of an empty dict:
```python
config_path = Path(__file__).parent.parent / "mesh_config.yaml"
mesh = MeshCoordinator.from_config_file(config_path, squad_id=squad_id, mesh_dir=str(mesh_dir))
```

---

## Why Lucy's Message Disappeared

Lucy reported message ID `9fea0edbcba3` was "delivered to the build claw inbox." This message was written directly to `~/.milimo/mesh/inbox/build/` — NOT to the War Room inbox. The War Room TUI only reads from `~/.milimo/mesh/inbox/war_room/`, so it shows nothing.

The message is likely sitting in the build claw's inbox file, but since there's no autonomous build claw process running to read it, it just sits there unread.

---

## Fix Priority

| Priority | Fix | Files | Effort |
|----------|-----|-------|--------|
| **P0** | Route approval-required messages to War Room inbox | `mesh.py:290-339`, `mesh.py:461-481` | ~30 lines |
| **P0** | Load real mesh config in `send_to_claw` | `bridge_cli.py:770` | ~5 lines |
| **P1** | Add assistant to message matrix | `mesh_config.yaml` | ~10 lines |
| **P1** | Add assistant message types to config | `mesh_config.yaml` | ~10 lines |

---

## Corrected Message Flow (After Fix)

```
Assistant (Lucy)
  → bridge: send_to_claw(role="build", type="assistant_task", payload={...})
  → MeshCoordinator.send_message()
  → ContractValidator.validate() → passes (assistant in matrix)
  → requires_approval("assistant_task") → True
  → _write_message() → writes to ~/.milimo/mesh/inbox/war_room/
  → DeliveryResult(requires_approval=True)

Operator opens War Room TUI:
  → milimo warroom
  → ApprovalEngine.getPendingMessages() reads war_room inbox
  → Shows: [assistant_task] assistant → build
  → Operator runs: approve <message_id>
  → processDecision() moves file from war_room inbox → build inbox

Build claw (when running):
  → Reads from ~/.milimo/mesh/inbox/build/
  → Processes the task
```
