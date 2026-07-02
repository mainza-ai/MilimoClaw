# Spend War Room Bridge

**Summary**: Glue layer between `SpendApprovalHandler` and `SoloWarRoom` that turns agent-initiated purchase requests into standard War Room REVIEW/HOLD actions. Propagates the active operator ID so `handle_hold_release` uses the correct per-operator `XDG_CONFIG_HOME` when invoking `link-cli`.

**Sources**:
- `milimo-blueprint/orchestrator/finance/spend_warroom_bridge.py`
- `milimo-blueprint/orchestrator/finance/spend_handler.py`
- `milimo-blueprint/templates/solo-founder.yaml`

**Last updated**: 2026-07-03

**Tags**: #module #finance #warroom #spend #bridge #approvals

---

## Purpose

`SpendWarRoomBridge` is the only integration point between the Finance Claw spend flow and the War Room action queue. It exists so:

1. Spend requests appear in the *same* unified queue as invoices, PRs, and deploys
2. The *same* keyboard shortcuts (`A` approve, `R` release, `B` block) work for spend
3. `SpendApprovalHandler.handle_hold_release()` receives the active `operator_id` so it routes to the correct per-operator `XDG_CONFIG_HOME` (`/sandbox/.config/users/{operator_id}/link-cli-nodejs/config.json`). The release is now **non-blocking**: `release_hold` returns immediately after starting a background polling thread, without waiting for the Link app approval.

Nothing about the TUI or [[war-room]] server needs to change — `solo_warroom.py` is already generic over claw/action_type/payload.

---

## Operator Propagation Chain

```
FinanceClaw
   ↓ operator_id from solo_warroom.operator
SpendWarRoomBridge.submit_spend_request(request)
   ↓
operator_id passed through approve_review() → release_hold()
   ↓
SpendApprovalHandler.handle_hold_release(action_id, operator_id=...)
   ↓
if operator_id is named (alice, bob, ...):
  XDG_CONFIG_HOME=/sandbox/.config/users/{operator_id}
else (system/operator/sandbox/empty):
  XDG_CONFIG_HOME=/sandbox/.config
   ↓
link-cli uses the scoped config for the correct Link account
```

> **Default operator fallback**: When `operator_id` is missing, empty, or one of the default system IDs (`system`, `operator`, `sandbox`), `handle_hold_release` falls back to `/sandbox/.config` instead of leaving `XDG_CONFIG_HOME` unset. Leaving it unset causes `link-cli` to use `/root/.config/link-cli-nodejs/config.json`, which is unauthenticated and results in Stripe Link API failures.

---

## ⚠️ Verified Audit Findings

| Finding | Severity | Status |
|---|---|---|
| **SA-1.1** [Critical] | War Room operator surface absent from OpenClaw (NemoClaw profile); Hermes HTMX server in `server.py:L42-76` is the only human-approval UI | **Verified Correct** |
| **SA-1.3** [High] | Bridge CLI lacks `approve-action` / `veto-action` subcommands; operators forced to use Hermes HTMX UI | **Verified Correct** |
| **SA3-1** [Critical] | `handle_hold_release()` has no idempotency lock; duplicate `R` press → duplicate Link sessions → duplicate charges | **Verified Correct** |

### SA-1.1: OpenClaw (NemoClaw) Has No Native War Room Operator UI

`server.py:L87-133` defines the HTMX HTTP server that moves files from `war_room` queue inbox to claw-specific inboxes (`mesh/inbox/finance`). The native NemoClaw profile uses `solo_warroom.py` to stage actions but has no HTTP listener, server loop, or CLI approval command. OpenClaw operators are blind to the War Room queue unless using the Hermes plugin manually.

**Fix**: Port `server.py` to `milimo-blueprint/orchestrator/` or add a CLI command: `milimo warroom approve <action_id>`.

### SA3-1: Duplicate Charge Risk on Hold Release

`SpendWarRoomBridge.release_hold()` calls `SpendApprovalHandler.handle_hold_release()` synchronously. There is no check whether a Link session ID already exists for the `spend_id`. If the operator presses `R` twice (or the bridge dispatches twice before the first call completes), `subprocess.run(cmd_create, ...)` creates two Stripe Link sessions and charges the operator twice.

**Fix**: Write a `spend_lock_<spend_id>` sentinel file before executing the create command; skip if already present.

---

### `submit_spend_request(request)`

Turns a `SpendRequest` into a War Room `spend_review` action.

- Calls `SpendApprovalHandler.queue_spend_review(request)`
- If daily spend cap exceeded, returns `None` (request never reaches War Room)
- Otherwise queues a REVIEW action in `solo_warroom` and returns the action ID

### `approve_review(warroom_action_id)`

Operator presses `A` on a `spend_review` action.

- Moves spend request from REVIEW → HOLD
- Queues a new `spend_hold` action in the War Room with a summary that mentions the Link app approval

### `release_hold(warroom_action_id)`

Operator presses `R` on a `spend_hold` action.

- Reads `operator_id` from `self.solo_warroom.operator`
- Calls `SpendApprovalHandler.handle_hold_release(hold_action_id, operator_id=operator_id)`
- The handler immediately creates the spend request with `--no-request-approval`, fires a separate `request-approval` command, and starts a background polling thread
- Returns `(war_room_action, spend_request)` **immediately** — does NOT wait for Link app approval
- Check `spend_request.status == "released"` after the background polling thread completes to confirm Link approval; until then, the status will be `pending_approval`

### `block_review(warroom_action_id)` / `cancel_hold(warroom_action_id)`

Operator presses `B` — kills the request at either stage.

---

## State Recovery After Restart

`SpendWarRoomBridge` maintains two in-memory mapping dicts:

- `_review_actions: dict[str, str]` — War Room action ID → internal spend action ID
- `_hold_actions: dict[str, str]` — War Room action ID → internal spend action ID

If the orchestrator restarts, these mappings are lost. `_find_action_payload(warroom_action_id)` queries `SoloWarRoom`'s current queue and processed lists to recover the payload, then extracts the internal spend action ID from it.

All bridge methods (`approve_review`, `block_review`, `release_hold`, `cancel_hold`) call `_find_action_payload` as a fallback when the in-memory lookup returns `None`. This prevents duplicate notifications and `KeyError` crashes after daemon restarts.

---

## Usage

```python
from milimo_hermes_plugin.spend_warroom_bridge import SpendWarRoomBridge

bridge = SpendWarRoomBridge(spend_handler, solo_warroom)

# Any claw submits a purchase request
wr_action_id = bridge.submit_spend_request(request)

# Operator presses 'A' on the spend_review action
bridge.approve_review(wr_action_id)

# A new spend_hold action appears; operator presses 'R'
action, spend_request = bridge.release_hold(hold_action_id)

if spend_request and spend_request.status == "released":
    print(f"Charge completed: {spend_request.link_request_id}")
else:
    print("Charge denied or timed out in Link app")
```

---

## Approval Thresholds

Configured in `solo-founder.yaml`:

```yaml
finance:
  spend_review: REVIEW   # Stage 1: operator sees full justification
  spend_hold: HOLD       # Stage 2: operator explicitly releases → link-cli → Link app
```

---

## Error Handling

| Path | Behavior |
|------|----------|
| Daily spend cap exceeded | `submit_spend_request()` returns `None`; request logged in `agent-spend.log` with status `blocked` |
| No tracked action ID | Logs warning and returns `None` — no crash |
| Link app denies/times out | `spend_request.status` becomes `denied` or `timed_out` asynchronously; background polling thread logs the outcome |
| `link-cli` missing at runtime | Background polling thread catches `FileNotFoundError` and terminates cleanly; no crash |
| Daemon restart during approval | `_recover_and_resume_polling()` resumes background threads on startup for any orphaned `hold` + `release` entries in `decisions.log` |

---

## Related Pages

- [[spend-handler]] — SpendApprovalHandler two-stage gate, robust JSON parsing, and per-operator isolation
- [[finance-claw]] — Finance Claw entry point
- [[war-room]] — TUI and HTMX dashboard for pending actions
- [[approval-thresholds]] — REVIEW/HOLD/AUTO configuration
- [[link-cli-setup]] — Stripe Link CLI auth, device flow, and token locations
- [[message-contracts]] — `spend_request`, `spend_review_decision`, `spend_hold_decision` schemas
- [[test-spend-flow]] — Automated tests for JSON parsing, state recovery, background polling, and bridge fallback

---

## See Also

- `milimo-blueprint/orchestrator/finance/spend_handler.py` — Python implementation
- `milimo-blueprint/templates/solo-founder.yaml` — Approval mode configuration
