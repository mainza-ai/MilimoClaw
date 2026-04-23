# Claw Silent Response Issues

**Summary**: Troubleshooting guide for claws (content, finance, build) that return no output or blank responses to assistant queries.

**Sources**: `milimo-blueprint/orchestrator/content/content_claw.py`, `milimo-blueprint/orchestrator/build/build_claw.py`, `milimo-blueprint/orchestrator/finance/finance_claw.py`

**Last updated**: 2026-04-18

**Tags**: #troubleshooting #claw #handler #mesh

---

## Symptoms

| Claw | Symptom | Root Cause |
|------|---------|------------|
| content | Returns blank output | Handler returns `None` instead of `dict` |
| finance | Returns directory listing instead of diagnostic | Handler falls through without explicit return |
| build | Returns blank output | Returns dict but bypasses mesh routing |
| ops | Works correctly | Has MockMeshGateway fallback |
| analytics | Works correctly | Explicit return statements in handlers |

## Root Cause: Handler Return Values

Each claw has `_handle_assistant_query` and `_handle_assistant_task` methods that process messages from the assistant (Lucy). These handlers must return a `dict[str, Any]` containing the response data. The InboxPoller writes this return value to the outbox for async result delivery.

**Working pattern (analytics):**
```python
def _handle_assistant_query(self, message: dict[str, Any]) -> dict[str, Any]:
    result = {...}
    self._send_assistant_response(message, result)
    return result  # Explicit return
```

**Broken pattern (content before fix):**
```python
def _handle_assistant_query(self, message: dict[str, Any]) -> None:
    result = {...}
    self._log_and_respond(message, result)
    # No return — implicitly returns None
```

When the handler returns `None`, the InboxPoller's result is `None`, and the outbox write contains empty/incomplete data.

## Fixes Applied

### content_claw.py

1. Changed return type annotations from `None` to `dict[str, Any]`
2. Added `return result` after `_log_and_respond()` calls in both handlers
3. Updated `_inbound_handlers` type annotation to accept `Callable[[dict[str, Any]], Any]`

```python
# Before
def _handle_assistant_query(self, message: dict[str, Any]) -> None:
    ...
    self._log_and_respond(message, result)

# After
def _handle_assistant_query(self, message: dict[str, Any]) -> dict[str, Any]:
    ...
    self._log_and_respond(message, result)
    return result
```

### build_claw.py

1. Added `mesh_sender` parameter to `__init__`
2. Added `_send_assistant_response()` method to route responses via mesh
3. Updated handlers to call `_send_assistant_response()` before returning

```python
def __init__(self, ..., mesh_sender: Any | None = None) -> None:
    ...
    self._mesh_sender = mesh_sender

def _send_assistant_response(self, message: dict[str, Any], result: dict[str, Any]) -> None:
    """Send response back to assistant via mesh gateway."""
    if self._mesh_sender:
        self._mesh_sender({...})

def _handle_assistant_query(self, message: dict) -> dict:
    result = {...}
    self._send_assistant_response(message, result)  # Route via mesh
    return result
```

### finance_claw.py

1. Added explicit `return result` after `_send_assistant_response()` calls

```python
elif message_type == "assistant_query":
    result["claw"] = "finance"
    ...
    self._send_assistant_response(raw_message, result)
    return result  # Explicit return

elif message_type == "assistant_task":
    result["claw"] = "finance"
    ...
    self._send_assistant_response(raw_message, result)
    return result  # Explicit return
```

## Verification

After applying fixes, rebuild the sandbox:
```bash
nemoclaw my-assistant rebuild --yes
```

Test via Lucy or the TUI:
```
Hello, this is Mainza
Conduct a tests to ensure all claws are functioning
```

All 5 claws should now return proper diagnostic output.

## Prevention

When adding new handler methods to any claw, ensure:
1. Return type is `dict[str, Any]` (not `None`)
2. Always include `return result` at the end
3. Call `_send_assistant_response()` to route via mesh if mesh_sender exists
4. For fallback behavior, add a MockMeshGateway like OpsClaw has

## Related Pages

- [[claw-launcher]] — How InboxPoller processes handler results
- [[content-claw]] — Content Claw handler documentation
- [[build-claw]] — Build Claw handler documentation
- [[finance-claw]] — Finance Claw handler documentation
- [[common-issues]] — Other common issues

## See Also

- `milimo-blueprint/orchestrator/content/content_claw.py` — Source file (fixed)
- `milimo-blueprint/orchestrator/build/build_claw.py` — Source file (fixed)
- `milimo-blueprint/orchestrator/finance/finance_claw.py` — Source file (fixed)
- `milimo-blueprint/orchestrator/ops/ops_claw.py` — Reference for working implementation
