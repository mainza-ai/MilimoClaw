# Spend Approval Handler

**Summary**: Mirror of `FinanceApprovalHandler` for the outbound direction of money — agent-initiated purchases via Stripe Link CLI.

**Sources**:
- `milimo-core/src/milimo_core/finance/spend_handler.py`
- `milimo-blueprint/orchestrator/finance/spend_warroom_bridge.py`

**Last updated**: 2026-07-03

**Tags**: #module #finance #spend #stripe #approval

---

## Overview

`SpendApprovalHandler` is the payables counterpart to `FinanceApprovalHandler` (receivables). While `FinanceApprovalHandler` governs invoices MilimoClaw sends and gets paid for, `SpendApprovalHandler` governs purchases a claw wants to make on the operator's behalf — buying API credit bundles, provisioning SaaS dependencies, paying per-call 402 APIs, etc.

Implements the NVIDIA x Stripe x Nous Research integration from the Hermes Agent Accelerated Business Hackathon (2026-06).

---

## Two-Stage Spend Approval

Same two-stage shape as invoice approval, opposite direction:

```
Stage 1 — REVIEW:
  Agent wants to buy X for $Y, because Z.
  Approving Stage 1 does NOT spend. It moves the request to HOLD only.

Stage 2 — HOLD release:
  Operator presses R. The handler immediately creates the spend request
  with --no-request-approval, then fires a separate request-approval
  command in the background. The link-cli subprocess does NOT block
  the TUI or the inter-claw gateway. A background daemon thread polls
  for final state (approved/denied/timed_out) and logs the outcome.
```

**Two independent human gates** sit between the agent and the charge:
1. War Room HOLD release — operator explicitly releases the spend hold
2. Stripe Link in-app approval — Hermes cannot self-approve this step either

The release is **non-blocking**: after the operator presses `R`, control returns immediately. Link approval happens asynchronously in the background.

---

## Daily Spend Cap

A safety cap (`MILIMO_DAILY_SPEND_CAP_CENTS`, default $100/10,000¢) auto-blocks any request exceeding the limit. Auto-blocked requests never reach the War Room and are logged immediately.

```python
import os
cap = int(os.environ.get("MILIMO_DAILY_SPEND_CAP_CENTS", "10000"))  # $100
```

---

## Spend Request Flow

```
Any claw sends a spend_request message
        ↓
SpendApprovalHandler.queue_spend_review()
        ↓
Daily cap check — auto-blocked if exceeded
        ↓
Queued in War Room as spend_review (REVIEW priority)
        ↓
Operator presses A → approve_review()
        ↓
Moves to HOLD — new spend_hold action appears in War Room (HOLD priority)
        ↓
Operator presses R → release_hold()
        ↓
handle_hold_release() creates spend request with --no-request-approval
        ↓
Separate background thread calls request-approval <id>
        ↓
link-cli push notification sent to user's phone (async)
        ↓
Polling thread checks status every 2s via link-cli spend-request retrieve
        ↓
Final outcome logged: purchase_approved or purchase_denied
```

The flow is **non-blocking** after the operator presses `R`. The TUI and inter-claw gateway remain responsive while the Link approval happens in the background.

---

## Non-Blocking Command Execution

`handle_hold_release` no longer blocks on `link-cli` during the approval push. It makes two quick sequential calls:

1. `link-cli spend-request create --no-request-approval ... --test --format json`
2. `link-cli spend-request request-approval <id>`

The first call creates the transaction immediately and returns the `lsrq_*` ID. The second call fires the push notification to the user's phone. Neither call waits for the user to approve — control returns to the War Room instantly.

```python
# 1. Create without blocking on approval
create_cmd = [
    self.link_cli_path, "spend-request", "create",
    "--no-request-approval",
    "--merchant-name", request.merchant_name,
    ...
    "--test", "--format", "json",
]
create_proc = subprocess.run(create_cmd, capture_output=True, text=True, timeout=310, env=env)
payload = json.loads(create_proc.stdout)
if isinstance(payload, list):
    payload = payload[0]
spend_id = payload.get("id")

# 2. Fire approval notification in background
approval_cmd = [self.link_cli_path, "spend-request", "request-approval", spend_id]
subprocess.run(approval_cmd, capture_output=True, text=True, timeout=30, env=env)

# 3. Hand off to background polling thread
self._start_polling_thread(spend_id)
```

---

## XDG_CONFIG_HOME Fallback for Default Operators

`handle_hold_release` defaults `XDG_CONFIG_HOME` to `/sandbox/.config` when `operator_id` is missing, empty, or one of the default system IDs (`system`, `operator`, `sandbox`). This prevents the orchestrator daemon from falling back to `/root/.config/link-cli-nodejs/config.json`, which is unauthenticated and causes Stripe Link API failures.

```python
env = os.environ.copy()
if operator_id and operator_id not in ("system", "operator", "sandbox", ""):
    env["XDG_CONFIG_HOME"] = f"/sandbox/.config/users/{operator_id}"
else:
    env["XDG_CONFIG_HOME"] = "/sandbox/.config"
```

This pairs with `_get_request(spend_id)` replacing direct `self._requests[...]` access in `handle_hold_release`, so a post-restart handler never crashes mid-release due to an empty in-memory cache.

---

## Daemon Restart / State Recovery

`SpendApprovalHandler` survives orchestrator restarts without losing spend state. A private `_get_request(spend_id)` method:

1. Checks the in-memory `self._requests` cache first
2. If missing (e.g., after a daemon restart), loads `logs/decisions.log`
3. Reconstructs a `SpendRequest` and replays all subsequent states (`approve`, `block`, `release`, `cancel`) from the log

All direct `self._requests[...]` accesses were replaced with `_get_request(spend_id)`, so no restart can trigger a `KeyError` on a valid spend ID.

---

## Background Polling Thread

After firing the approval notification, `handle_hold_release` starts a background daemon thread via `_start_polling_thread(spend_id)`. The thread:

- Calls `link-cli spend-request retrieve <id>` every 2 seconds
- Updates the in-memory spend state on each poll
- Logs the final outcome when the request reaches a terminal state:
  - `purchase_approved` — operator approved in the Link app
  - `purchase_denied` — operator denied in the Link app
  - `purchase_expired` / `purchase_failed` — terminal failure states
- Catches `FileNotFoundError` safely to terminate if `link-cli` is missing (e.g., during tests)

```python
def _start_polling_thread(self, spend_id: str) -> None:
    thread = threading.Thread(
        target=self._poll_spend_request,
        args=(spend_id,),
        daemon=True,
    )
    thread.start()

def _poll_spend_request(self, spend_id: str) -> None:
    while True:
        time.sleep(2)
        try:
            proc = subprocess.run(
                [self.link_cli_path, "spend-request", "retrieve", spend_id],
                capture_output=True, text=True, timeout=30, env=self._link_env,
            )
            status = json.loads(proc.stdout).get("status")
            request = self._get_request(spend_id)
            request.status = status
            if status in ("approved", "denied", "expired", "failed"):
                self._log_terminal_state(spend_id, status)
                break
        except FileNotFoundError:
            self._log_missing_link_cli(spend_id)
            break
```

This keeps the TUI and inter-claw gateway responsive for the entire approval window, which can be minutes.

---

## ⚠️ Audit Findings — Verified Limitations

Three confirmed gaps in the current `SpendApprovalHandler` implementation (audit: 2026-07-03, verified line-level):

| Finding | Severity | Location | Gap |
|---|---|---|---|
| **SA3-1** | Critical | `spend_handler.py:L360-387` | `handle_hold_release()` has no idempotency check. If the background polling thread crashes and the operator re-approves (or double-clicks), `subprocess.run(cmd_create, ...)` can generate duplicate Stripe Link sessions, causing duplicate charges. Fix: write a local `spend_lock_<spend_id>` file before executing the create command. |
| **SA3-2** | Critical | `spend_handler.py:L188` | Daily spend cap is per-transaction, not daily aggregate. `request.amount_cents > self.daily_spend_cap_cents` does not sum previously released transactions from `agent-spend.log`. Sub-cap repeated charges bypass the cap. Fix: sum all `released`/`purchase_approved` entries in the last 24 h before approving new requests. |
| **SA3-3** | Medium | `spend_handler.py:L534-543` | `_log_decision()` writes with `fcntl.flock` but omits `.flush()` + `os.fsync(f.fileno())`. A crash after transaction completion but before fsync loses the log entry, impairing restart recovery. Fix: call `f.flush()` and `os.fsync(f.fileno())` after every write. |

---

## Self-Healing Startup Recovery

`_recover_and_resume_polling()` is called automatically during `SpendApprovalHandler.__init__`. On startup, it scans `logs/decisions.log` for any spend requests that were released but never reached a terminal state. For each orphaned request, it resumes the background polling thread automatically.

This handles the case where:
- The orchestrator daemon restarts while a Link approval is pending
- The operator approves on their phone while the daemon is down
- The daemon comes back online and must catch up

```python
def _recover_and_resume_polling(self) -> None:
    for entry in self._read_decisions_log():
        if entry.get("stage") == "hold" and entry.get("action_type") == "release":
            spend_id = entry["action_id"].replace("spend-hold-", "")
            request = self._get_request(spend_id)
            if request and request.status not in ("approved", "denied", "expired", "failed"):
                self._start_polling_thread(spend_id)
```

---

## Spend War Room Bridge

`SpendWarRoomBridge` connects `SpendApprovalHandler` to the existing `SoloWarRoom` action queue. Claws call the bridge instead of touching `SpendApprovalHandler` or `link-cli` directly:

```python
bridge = SpendWarRoomBridge(spend_handler, solo_warroom)
wr_action_id = bridge.submit_spend_request(request)
bridge.approve_review(wr_action_id)
action, request = bridge.release_hold(hold_action_id)
if request.status == "released":
    print("Charge completed")
```

---

## Inbound Message Handlers

| Message Type | Handler | Action |
|--------------|---------|--------|
| `spend_request` | `SpendApprovalHandler.queue_spend_review()` | Queue a purchase for review |
| `spend_review_decision` | `approve`/`edit`/`block` | Stage 1 decision |
| `spend_hold_decision` | `release`/`cancel` | Stage 2 decision |

---

## Logging

Every decision is written to `decisions.log` (same file as `FinanceApprovalHandler`), with the same format and stage vocabulary:

```json
{"action_id": "spend-review-abc123", "stage": "review", "action_type": "approve", ...}
{"action_id": "spend-hold-abc123", "stage": "hold", "action_type": "release", ...}
```

A dedicated `agent-spend.log` records completed purchase details:

```json
{"spend_id": "abc123", "claw": "build", "merchant_name": "Neon", "amount_cents": 5000, ...}
```

---

## Container / Runtime Code Paths

Inside a running Hermes sandbox container, the active Python modules may resolve from one of several paths depending on how the blueprint was installed:

| Path | When Used |
|------|-----------|
| `/sandbox/.nemoclaw/blueprints/0.1.0/orchestrator/finance/spend_handler.py` | Blueprint-managed runtime |
| `/opt/nemoclaw-blueprint/orchestrator/finance/spend_handler.py` | System-wide blueprint |
| `/opt/milimo-core/src/milimo_core/finance/spend_handler.py` | Core package install |

The host source of truth is `milimo-core/src/milimo_core/finance/spend_handler.py`. After host edits, sync to the container with:

```bash
docker cp milimo-core/src/milimo_core/finance/spend_handler.py \
  <container>:/sandbox/.nemoclaw/blueprints/0.1.0/orchestrator/finance/spend_handler.py

docker cp milimo-core/src/milimo_core/finance/spend_handler.py \
  <container>:/opt/nemoclaw-blueprint/orchestrator/finance/spend_handler.py

docker cp milimo-core/src/milimo_core/finance/spend_handler.py \
  <container>:/opt/milimo-core/src/milimo_core/finance/spend_handler.py
```

Run tests inside the container against the blueprint path:

```bash
docker exec -u sandbox <container> env PYTHONPATH=/sandbox/.nemoclaw/blueprints/0.1.0 \
  /opt/hermes/.venv/bin/pytest /sandbox/.nemoclaw/blueprints/0.1.0/tests/test_spend_flow.py
```

---

## Approval Modes

Configured in `solo-founder.yaml`:

```yaml
finance:
  spend_review: REVIEW   # agent wants to buy something — you see it first
  spend_hold: HOLD       # you explicitly release the charge (Link confirms too)
```

---

## Related Pages

- [[finance-claw]] — Finance claw main entry point
- [[approval-handler]] — Receivables approval (two-stage invoices)
- [[approval-thresholds]] — REVIEW/HOLD/AUTO rules
- [[war-room]] — TUI for pending actions
- [[message-contracts]] — Message types
- [[test-spend-flow]] — Automated tests for JSON parsing, state recovery, background polling, and bridge fallback

---

## See Also

- `milimo-core/src/milimo_core/finance/spend_handler.py` — Implementation
- `milimo-blueprint/orchestrator/finance/spend_warroom_bridge.py` — War Room bridge
- `milimo-blueprint/templates/solo-founder.yaml` — Approval mode config
- `milimo-blueprint/tests/test_spend_flow.py` — Tests for JSON parsing, state recovery, and bridge fallback
