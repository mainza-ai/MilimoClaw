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

1. `link-cli spend-request create --no-request-approval ... --format json`
2. `link-cli spend-request request-approval <id>`

The `--test` flag is only valid on `create`; passing it to `request-approval` or `retrieve` returns an UNKNOWN flag error.

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

## Queue State Persistence

`queue_spend_review()` and `queue_spend_hold()` call `_persist_queue_state()` to write a `queue_state` event to `agent-queue.log` (dedicated file, separate from spend records). On restart, `_recover_and_resume_polling()` restores pending REVIEW and HOLD entries by replaying `decisions.log` and `agent-queue.log`.

Key behavior: `_get_daily_spend_aggregate()` skips `queue_state` events so they do not inflate the daily cap calculation. Only actual spend entries (from `_append_spend_log`) count toward the cap.

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

After firing the approval notification, `handle_hold_release` starts a background non-daemon thread via `_start_polling_thread(spend_id)`. The thread:

- Calls `link-cli spend-request retrieve <id>` every 2 seconds
- Updates the in-memory spend state on each poll
- Logs the final outcome when the request reaches a terminal state:
  - `purchase_approved` — operator approved in the Link app
  - `purchase_denied` — operator denied in the Link app
  - `purchase_expired` / `purchase_failed` — terminal failure states
- Catches `FileNotFoundError` safely to terminate if `link-cli` is missing (e.g., during tests)

The thread is a non-daemon thread so it survives incidental process exits, and responds to `handler.close()` for graceful shutdown:

```python
def close(self) -> None:
    self._shutdown_event.set()
    for thread in list(self._active_poll_threads):
        thread.join(timeout=10)
```

The polling loop checks `self._shutdown_event.is_set()` at the top of each iteration and exits cleanly when FinanceClaw shuts down.

```python
def _poll_spend_request(self, spend_id: str) -> None:
    while True:
        if self._shutdown_event.is_set():
            break
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

## ⚠️ Audit Findings — Status

| Finding | Severity | Status | Notes |
|---|---|---|---|
| **SA3-1** | Critical | **Fixed (2026-07-04)** | Idempotency lock added at `spend_handler.py:352-389` (`O_CREAT|O_EXCL` + PID + stale cleanup). Duplicate `R` press no longer creates duplicate Link sessions. |
| **SA3-2** | Critical | **Fixed (2026-07-04)** | Daily spend cap now reads rolling 24h aggregate from `agent-spend.log` via `_get_daily_spend_aggregate()` with `fcntl.LOCK_SH` at `spend_handler.py:188-189`. Sub-cap repeated charges are now blocked. |
| **SA3-3** | Medium | **Fixed (2026-07-04)** | `_log_decision()` at `spend_handler.py:670-682` now calls `f.flush()` + `os.fsync()` after every write. Crash durability confirmed. |
| **F-1** | High | **Fixed (2026-07-04)** | `handle_hold_release` no longer marks requests `blocked` when `request-approval` fails. Status is `approval_pending` and polling still starts. |
| **F-2** | High | **Fixed (2026-07-04)** | `_find_prior_release()` checks `decisions.log` before `create` to prevent duplicate `lsrq_*` sessions after crashes. |
| **F-3** | High | **Fixed (2026-07-04)** | `request-approval` retried once after 5s on transient failure; permanent failures (e.g. `UNKNOWN flag`) are not retried. |
| **F-8** | Medium | **Fixed (2026-07-04)** | `_get_request` reconstructs from `hold/queued` and `hold/release` entries, not just `review/queued`. |
| **F-9** | Medium | **Fixed (2026-07-04)** | `_persist_queue_state` now writes to `agent-queue.log` (separate file). `_get_daily_spend_aggregate` no longer needs to filter `queue_state` events. |
| **F-10** | Medium | **Fixed (2026-07-04)** | `FinanceOperationalLog.append` now calls `f.flush()` + `os.fsync()` for crash durability. |
| **F-11** | Medium | **Fixed (2026-07-04)** | `SpendApprovalHandler.close()` signals all polling threads to stop and joins them with 10s timeout. |
| **F-12** | Low | **Fixed (2026-07-04)** | War Room server argparse default changed from `8080` to `9090`. |
| **F-14** | Low | **Fixed (2026-07-04)** | `_lsrq_index: dict[str, str]` added for O(1) `lsrq_*` → `spend_id` lookups; populated on every successful `create`. |

---

## Status Vocabulary

| Status | Meaning |
|--------|---------|
| `pending_review` | Queued in War Room REVIEW, awaiting operator |
| `held` | REVIEW approved, moved to HOLD queue |
| `released` | `create` AND `request-approval` both succeeded; polling started |
| `approval_pending` | `create` succeeded but `request-approval` failed; `lsrq_*` session exists and polling is active |
| `blocked` | `create` failed, cap exceeded, or operator blocked |
| `cancelled` | Operator cancelled from HOLD |

## Idempotency and Recovery

`handle_hold_release` is safe to call multiple times:

1. **Crash-safe create**: Before running `create`, `_find_prior_release()` scans `decisions.log`. If a prior `release_initiated` entry with a valid `lsrq_*` exists, the handler returns immediately with `status = "released"`.
2. **Notify retry**: If a prior `notify_failed` entry exists with a valid `lsrq_*`, the handler skips `create` and retries `request-approval`.
3. **Atomic lock**: `O_CREAT|O_EXCL` file lock prevents concurrent releases for the same `spend_id`. Stale locks (dead PID) are cleaned up automatically.

This means the operator can press `R` multiple times, or the daemon can restart mid-release, without creating duplicate Link charge sessions.

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

`agent-queue.log` records queue state transitions (review → hold → release stages):

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
