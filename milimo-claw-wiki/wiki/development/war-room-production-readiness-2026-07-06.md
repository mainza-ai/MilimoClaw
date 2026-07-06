# War Room Production-Readiness Investigation & Fix Plan

**Summary**: Complete investigation of the empty/static war room observed during the 2026-07-06 Finance Claw spend flow live test. Identifies the root cause (warroom_bridge not on sys.path), the static-HTML polling-destruction bug, the missing auto-start + port-forward path, and documents the phased fix plan for production-grade operation. Do not implement until this plan is reviewed and approved.

**Sources**:
- `milimo-hermes-sandbox/milimo-hermes-plugin/warroom/server.py`
- `milimo-hermes-sandbox/milimo-hermes-plugin/warroom/warroom_bridge.py`
- `milimo-hermes-sandbox/milimo-hermes-plugin/warroom/warroom.html`
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/spend_handler.py`
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/approval_handler.py`
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/ops/approval_handler.py`
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/build/approval_handler.py`
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/content/approval_handler.py`
- `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/finance_claw.py`
- `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py`
- `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py`
- `milimo-hermes-sandbox/scripts/start.sh`
- `milimo-hermes-sandbox/Dockerfile`
- `milimo-claw-wiki/wiki/coordination/war-room.md`
- `milimo-claw-wiki/wiki/tui/warroom-tui.md`
- `milimo-claw-wiki/wiki/modules/finance/spend-warroom-bridge.md`
- `milimo-claw-wiki/wiki/coordination/war-room-security.md`

**Last updated**: 2026-07-06

**Tags**: #development #warroom #production #fix-plan #finance #ops #content #build

---

## 1. Symptom

During the 2026-07-06 end-to-end Finance Claw spend flow test:
- Three spend requests were created in `decisions.log`: `spend-e46e59e3`, `spend-c078beaf`, `spend-b4efaadf`
- The War Room UI at `http://localhost:9090/warroom.html` showed **"No pending actions — all claws clear"**
- `ls /sandbox/.hermes/mesh/inbox/war_room/` returned empty
- The operator had no visibility into any pending action from any claw

---

## 2. Root Cause (Primary)

**`warroom_bridge.py` is not on the Python `sys.path` for any `milimo_core` approval-handler process.**

### Why the import fails everywhere

The file `warroom_bridge.py` lives at:
- `/opt/hermes/warroom/warroom_bridge.py` (static assets copy — Dockerfile step 69)
- `/sandbox/.hermes/plugins/milimo-hermes/warroom/warroom_bridge.py` (sandbox plugin copy)

Neither path is:
1. Part of any installed Python package
2. Added to `sys.path` by the Dockerfile
3. Inside the `milimo_hermes_plugin` package tree

`milimo_core` runs from `/opt/milimo-core/src/` on `sys.path`. Python cannot find `warroom_bridge` there → `ModuleNotFoundError` → every handler's `except ImportError: pass` silently swallows it → **no JSON files written** → server polls empty directory → UI shows nothing.

### Every place that silently fails

| File | Line(s) | What it tries to import |
|------|---------|------------------------|
| `finance/spend_handler.py` | 276, 398 | `from warroom_bridge import write_warroom_action` |
| `finance/approval_handler.py` | 61 | `from warroom_bridge import write_warroom_action` |
| `ops/approval_handler.py` | 36 | `from warroom_bridge import write_warroom_action, remove_warroom_action` |
| `build/approval_handler.py` | 29 | `from warroom_bridge import write_warroom_action` |
| `content/approval_handler.py` | 33 | `from warroom_bridge import write_warroom_action, remove_warroom_action` |
| `content/content_generator.py` | 41 | `from warroom_bridge import write_warroom_action` |
| `finance/finance_claw.py` | 194 | `from warroom_bridge import register_warroom_action_handler` |
| `content/content_claw.py` | 181 | `from warroom_bridge import register_warroom_action_handler` |
| `build/build_claw.py` | 143 | `from warroom_bridge import register_warroom_action_handler` |
| `milimo_hermes_plugin/__init__.py` | 156 | `from warroom_bridge import register_warroom_action_handler` |
| `milimo_hermes_plugin/tools.py` | 47, 292 | `from warroom_bridge import resolve_mesh_dir, write_warroom_action, ...` |

All use `try: ... except ImportError: pass` — zero logging on failure.

### Why the server itself starts fine

`server.py` is run as `python /opt/hermes/warroom/server.py`. Python implicitly adds the script's directory (`/opt/hermes/warroom/`) to `sys.path[0]`. The `from warroom_bridge import ...` at `server.py:62` succeeds **accidentally** because the warroom folder happens to be on `sys.path` for that process only. This is not by design.

---

## 3. Root Cause (Secondary) — Static UI

### Bug A — HTMX polling destroyed after approve/veto

In `warroom.html`, the approve/veto buttons use `hx-target="#hold-queue" hx-swap="outerHTML"`. The server's `_process_decision()` returns the **full re-rendered queue HTML** from `_handle_hold_queue()`. When this replaces `#hold-queue` via `outerHTML`, the new `<div id="hold-queue">` has **no `hx-trigger="every 5s"` attribute**. Result: after the first approval/veto, polling stops permanently until the operator does a full page refresh.

### Bug B — No real-time push

Even when polling works, `every 5s` is a pull model. There is no WebSocket, SSE, or EventSource. Items submitted by a claw can take up to 5 seconds to appear. There is no audible/desktop notification for new holds.

### Bug C — GET endpoints unauthenticated

`WARROOM_AUTH_TOKEN` only protects POST (`approve`/`veto`). All GET endpoints (`/v1/warroom/hold-queue`, `/v1/warroom/claw-status`, `/v1/warroom/cost-guard`) are open. Any device on the network can read the full action queue including financial holds and PR reviews.

---

## 4. Root Cause (Tertiary) — Server Never Auto-Starts

### No auto-start in container entrypoint

`scripts/start.sh` handles:
- Hermes gateway
- Hermes dashboard
- socat forwarders for API (8642) and dashboard (18789/18790)

But port **9090** (the war room) has:
- No startup block in `start.sh`
- No socat forwarder
- No systemd unit or init.d script

The operator must manually start the server inside the sandbox. Even then, the host cannot reach it because no `openshell forward start 9090 milimo-hermes` exists for it.

---

## 5. Gap Inventory

### CRITICAL (must fix before any production use)

| # | Gap | Files Affected | Impact |
|---|-----|---------------|--------|
| C-1 | `warroom_bridge.py` not on `sys.path`; all imports fail silently | All approval handlers + claw startups + `tools.py` | War room always empty; no action ever surfaces |
| C-2 | No war room server auto-start in container | `scripts/start.sh`, `Dockerfile` | Server never runs unless operator manually starts it |
| C-3 | Port 9090 not forwarded from sandbox to host | `scripts/start.sh`, OpenShell config | Even if server runs, host cannot reach `http://localhost:9090` |

### HIGH (must fix for production-grade operation)

| # | Gap | Files | Impact |
|---|-----|-------|--------|
| H-1 | HTMX outerHTML polling-destruction after approve/veto | `warroom.html`, `server.py` | After first approval, queue freezes until manual page refresh |
| H-2 | No real-time push (no WebSocket, SSE, EventSource) | `warroom.html`, `server.py` | Operator waits up to 5s for new items; no instant awareness |
| H-3 | All GET endpoints unauthenticated | `server.py` | Any device on the network can read the full action queue |
| H-4 | `FinanceApprovalHandler` has no `_unsync_warroom` | `finance/approval_handler.py` | Approved invoices stay in `war_room/` inbox forever; never cleaned up |
| H-5 | Finance spend callbacks not registered with `warroom_bridge._ACTION_HANDLERS` | `finance/spend_handler.py`, `finance/finance_claw.py` | Server approve/veto buttons dispatch to no handler for spend actions |
| H-6 | No notification system for new War Room items | `warroom.html`, all claws | Operator must stare at the page; no audible/desktop alert |

### MEDIUM (must fix for production readiness)

| # | Gap | Files | Impact |
|---|-----|-------|--------|
| M-1 | No audit trail / action history view in UI | `warroom.html`, `server.py` | Operator cannot see past approvals/vetoes without reading `decisions.log` |
| M-2 | No per-operator view or filtering | `warroom.html`, `server.py` | Multi-operator setups expose all actions to everyone |
| M-3 | No action detail view (full payload) | `warroom.html`, `server.py` | Operator can only see the one-line summary |
| M-4 | No rate limiting on POST endpoints | `server.py` | API can be flooded with approve/veto requests |
| M-5 | No retry/recovery for transient bridge write failures | all approval handlers | If a write transiently fails, item is lost from war room forever |

### LOW (enhancements for full production UX)

| # | Gap | Files | Impact |
|---|-----|-------|--------|
| L-1 | No search/filter in web UI | `warroom.html` | Must scroll to find specific items |
| L-2 | No keyboard shortcuts in web UI | `warroom.html` | Terminal TUI has shortcuts; web UI has none |
| L-3 | No bulk-approve / bulk-veto | `server.py` | Must approve items one at a time |
| L-4 | No export of queue state | `server.py` | Cannot share or archive the current action list |
| L-5 | No SLA / age indicator on items | `warroom.html`, `server.py` | Cannot see how long an item has been waiting |

---

## 6. Consistency Issues Between Handlers

| Feature | Ops | Build | Content | Finance (invoice) | Finance (spend) |
|---------|-----|-------|---------|-------------------|-----------------|
| `_write_warroom` on init | ✓ `_try_import_write_warroom_action()` | ✓ same | ✓ `_try_import_warroom_bridge()` | ✓ inline method | ✗ inline per-call |
| `_remove_warroom` on init | ✓ | ✓ | ✓ | ✗ missing | ✗ missing |
| `_sync_warroom` method | ✓ explicit | partial | ✓ `sync_warroom()` | ✗ missing | ✗ missing |
| `_unsync_warroom` method | ✓ explicit | partial | ✓ `unsync_warroom()` | ✗ missing | ✗ missing |
| Callbacks registered with `_ACTION_HANDLERS` | ✓ | ✓ | partial | ✓ | ✗ |
| Fallback approve/veto server-side | ✓ | ✓ | ✓ | ✓ | ✓ |

Finance (spend) is the weakest: it does inline `try/except ImportError: pass` in both `queue_spend_review` and `queue_spend_hold`, and never registers `handle_review_approve`/`handle_review_block` callbacks with `warroom_bridge._ACTION_HANDLERS`. Even if the import succeeded, the server's `approve_hold_message()` would dispatch to no finance handler.

---

## 7. Production Implementation Plan

> **No code will be written until you approve, modify, or reprioritize this plan.**

### Phase A — Fix the empty war room (prerequisite for everything)

**A-1. Install `warroom_bridge` into the Python package**

Preferred long-term option: make `warroom_bridge.py` an installable module inside `milimo_hermes_plugin/`:
- Move or symlink `warroom_bridge.py` into `milimo-hermes-plugin/milimo_hermes_plugin/warroom_bridge.py`
- Change all `from warroom_bridge import ...` to `from milimo_hermes_plugin.warroom_bridge import ...`
- The existing `uv pip install -e /opt/milimo-hermes-plugin/` then makes it importable everywhere

Minimal-change option: add a `.pth` file in the Dockerfile so `/opt/hermes/warroom/` is always on `sys.path`:
```dockerfile
RUN printf '%s\n' '/opt/hermes/warroom' > /usr/lib/python3/dist-packages/warroom_bridge.pth
```

**A-2. Remove silent `except ImportError: pass` everywhere**

Replace all instances with explicit logging:
```python
except ImportError as exc:
    logger.error("warroom_bridge unavailable — war room sync skipped: %s", exc)
```

This turns invisible failures into observable ones. Essential for production debugging.

**A-3. Register Finance spend callbacks with `warroom_bridge._ACTION_HANDLERS`**

In `finance/finance_claw.py` `startup()`, after creating `spend_handler`, register:
```python
from warroom_bridge import register_warroom_action_handler
register_warroom_action_handler(
    "finance",
    lambda action_id, data: spend_handler.handle_review_approve(action_id),
    lambda action_id, data: spend_handler.handle_review_block(action_id, reason="vetoed from war room"),
)
```
Also need a separate handler registration for `spend-hold-*` action IDs → `spend_handler.handle_hold_release(action_id, operator_id=...)`.

**A-4. Add `_unsync_warroom` to `FinanceApprovalHandler`**

Mirror the pattern from `OpsApprovalHandler._unsync_warroom` and `ContentApprovalHandler.unsync_warroom`. When `handle_review_approve` creates the hold, remove the review entry from `war_room/`. When `handle_hold_release` fires, remove the hold entry.

**A-5. Verification**

```bash
ls /sandbox/.hermes/mesh/inbox/war_room/
# Expected: spend-review-<id>.json, spend-hold-<id>.json, etc. after queueing items

grep "warroom_bridge" <container-logs>
# Expected: NO "warroom_bridge unavailable" lines
```

---

### Phase B — Fix the static UI

**B-1. Fix HTMX outerHTML polling-destruction bug** ✅ Implemented 2026-07-06

Approve/veto buttons used `hx-target="#hold-queue" hx-swap="outerHTML"`. After the swap, the replacement `#hold-queue` div had no `hx-trigger`, so polling stopped after the first approval until a full page refresh.

**Fix applied** (`milimo-hermes-sandbox/milimo-hermes-plugin/warroom/server.py`):
- Extracted `_build_hold_queue_html()` from `_handle_hold_queue()` — returns the inner queue HTML as a string without sending an HTTP response.
- `_handle_hold_queue()` now delegates to it and sends the result (used for normal polling GET).
- `_process_decision()` now calls `_build_hold_queue_html()` directly (no double-send), wraps the result in a full `<div id="hold-queue" hx-get="..." hx-trigger="every 5s" hx-on::after-request="..." hx-swap="innerHTML">…</div>` and sends that as the POST response.

This preserves the `hx-trigger="every 5s"` attribute through every approve/veto cycle. The inner `hx-swap="innerHTML"` on buttons correctly re-probes the outer wrapper once per cycle.

**B-2. Add WebSocket or SSE endpoint to `server.py`**

Replace or supplement HTMX polling with WebSocket. The existing `http.server.HTTPServer` is single-threaded and blocking — migrate to `asyncio` + `websockets` for the real-time layer.

Architecture:
```
browser ←WebSocket→ server.py (asyncio loop) ←inotify/poll→ mesh_dir/inbox/war_room/
```

When any approval handler calls `write_warroom_action()`, the bridge should:
1. Write the JSON file
2. Emit a WebSocket message to all connected clients

When an operator clicks approve/veto:
1. Server processes the action
2. Removes/moves the file
3. Emits a WebSocket message: `{type: "removed", action_id: "..."}`

**B-3. Server-side filesystem watcher**

`server.py` should watch `mesh_dir/inbox/war_room/` using `inotify` (Linux) or `watchdog` observer. When a new `.json` file appears or is removed/renamed, broadcast via WebSocket.

---

### Phase C — Auto-start and port forwarding

**C-1. Add war room to `scripts/start.sh`** ✅ Implemented 2026-07-06

After the dashboard startup block, added: - `WARROOM_INTERNAL_PORT` (env: `NEMOCLAW_WARROOM_PORT`, default `9090`) + `WARROOM_PUBLIC_PORT=WARROOM_INTERNAL_PORT` with collision detection against PUBLIC_PORT, INTERNAL_PORT, DASHBOARD_PUBLIC_PORT, DASHBOARD_INTERNAL_PORT - `start_warroom_server_current_user()` and `start_warroom_server_sandbox_user()` — launch `/opt/hermes/warroom/server.py` via `nohup`, capture PID, assign tracked role, start socat forwarder - `hermes_warroom_healthy()` — HTTP 200 probe on `/health` endpoint - Added to `ensure_hermes_supervised_auxiliaries()` for auto-restart on failure - Added to `refresh_hermes_supervised_child_pids()` and `hermes_auxiliaries_need_recovery()` - `cleanup_orphan_socat_forwarders()` now kills orphaned war room socat forwarders - `hermes_role_identity_value()` / `hermes_set_role_identity()` extended with `warroom`, `warroom-socat`, `warroom-log` cases  - `hermes_process_start_identity()` cmdline validation extended for `warroom` role and `warroom-log` sed tail   **C-2. Add port 9090 socat forwarder** ✅ Implemented as part of C-1   - `start_warroom_server_*` calls `start_socat_forwarder` to expose `WARROOM_INTERNAL_PORT` on `WARROOM_PUBLIC_PORT`   - socat forwarder monitored in `ensure_hermes_supervised_auxiliaries()` — restarts if unhealthy **C-3. Wire port 9090 into OpenShell** ⏸ Not yet implemented   - Port is pre-forwarded under NemoClaw for 8642, 18789, 19119, etc.   - 9090 needs to be added to the OpenShell `forward start` allow-list on sandbox creation (separate from start.sh)

---

### Phase D — Security hardening for production

**D-1. Authenticate GET endpoints** ✅ Already in place

`do_GET()` calls `_require_auth(self)` at line 265 before dispatching to /v1/warroom/* handlers. When `WARROOM_AUTH_TOKEN` is set, every GET returns 401 without a valid Bearer token. No additional change required.

**D-2. Add rate limiting on POST** ✅ Implemented 2026-07-07

Added `_RATE_LIMIT_WINDOW_SECONDS=60`, `_RATE_LIMIT_MAX_POSTS=30`, `_check_rate_limit(client_ip)`. `do_POST()` rejects excess requests with HTTP 429 before any action dispatches. The base HTTPServer is single-threaded, so the plain-dict sliding window is safe without additional locking.

**D-3. Add structured logging for all approve/veto decisions** ✅ Implemented 2026-07-07

`do_POST()` captures `self._operator_identity = _get_operator_identity(self)` (either `token:<prefix>…` or `ip:<addr>`) before dispatching. `_process_decision()` logs `[req_id] DECISION APPROVE/VETO on <action_id> by <identity>` directly alongside handler-side `_log_decision` records.

---

### Phase E — Production UX enhancements

**E-1. Add audit/history view**

Show the last N approve/veto decisions in a new card on `warroom.html`. Source: `decisions.log`.

**E-2. Add action detail modal/drawer**

When clicking a hold-item, expand to show full payload (justification, link_spend_request_id, daily cap remaining, etc.).

**E-3. Add per-item SLA/age indicator**

Color-code items by queue age:
- Green: < 1 hour
- Amber: 1–24 hours
- Red: > 24 hours (SLA breach)
- Pulsing red: > 48 hours

**E-4. Add desktop notifications via War Room Notifier**

When a new item enters the hold queue, fire a desktop notification using the existing `OperatorNotifier` in `milimo-core`.

**E-5. Add keyboard shortcuts to web UI**

Mirror the terminal TUI shortcuts (A=Approve, B=Block, R=Release, ?=Help) in `warroom.html`.

---

### Phase F — Long-term architectural improvements

**F-1. Replace `HTTPServer` with an async ASGI server**

For WebSocket support, migrate to `uvicorn` + `fastapi` or `asyncio` + `websockets`. The server is the last synchronous component in an otherwise async stack.

**F-2. Centralize `resolve_mesh_dir()`**

Remove the duplicate `resolve_mesh_dir()` in `warroom_bridge.py` and have it use `milimo_core.milimo_paths.mesh_dir()` exclusively.

**F-3. Add a replay buffer for WebSocket reconnects**

When a WebSocket client reconnects after a network hiccup, the server should send all current queue state rather than just diffs since the last message.

---

## 8. Execution Order

| Priority | Phase | Effort | Blocks |
|----------|-------|--------|--------|
| P0 | A-1 (install bridge on sys.path) | Small (Dockerfile + import rename) | Everything else |
| P0 | A-2 (stop silent ImportError) | Small | Observability |
| P0 | A-3 (register finance callbacks) | Small | Finance spend approve/veto |
| P0 | A-4 (add `_unsync_warroom` to FinanceApprovalHandler) | Small | Queue hygiene |
| P1 | C-1 + C-2 (auto-start + port forward) | Medium | Operator access |
| P1 | B-1 (fix HTMX outerHTML bug) | Small | UI usability |
| P1 | B-2 (WebSocket push) | Large | Real-time UX |
| P1 | B-3 (filesystem watcher) | Medium | Real-time UX |
| P2 | D-1 (authenticate GET) | Small | Security |
| P2 | D-2 (rate limiting POST) | Small | Security |
| P2 | D-3 (operator logging) | Small | Audit |
| P3 | E-1 through E-5 | Medium | UX |
| P3 | F-1 through F-3 | Large | Architecture |

**Critical path to a working, observable war room:** A-1 → A-2 → A-3 → A-4 → C-1 → C-2 → B-1.

---

## 9. Verification Checklist

### After Phase A
```bash
ls /sandbox/.hermes/mesh/inbox/war_room/ | head -20
# Expected: spend-review-<id>.json, spend-hold-<id>.json, etc.

grep "warroom_bridge unavailable" <logs>
# Expected: no lines (bridge is importable)
```

### After Phase B
- Open war room in two browser tabs
- Click "Approve" in tab A → tab B updates in < 1s without refresh
- Click "Veto" → queue immediately reflects removal

### After Phase C
```bash
curl http://localhost:9090/health
# Expected: {"status": "ok"}
curl http://127.0.0.1:9090/v1/warroom/hold-queue
# Expected: HTML with hold items (or empty state)
```

### After Phase D
```bash
curl http://localhost:9090/v1/warroom/hold-queue
# Expected: 401 Unauthorized
curl -H "Authorization: Bearer <redacted-token>" http://localhost:9090/v1/warroom/hold-queue
# Expected: 401 Unauthorized
```

---

## 10. Status

> All phases below reflect the **post-A/B/C1-2 implementation state** (committed to `develop` / `main` as of 2026-07-06). Nothing has been verified in a live environment yet — awaiting rebuild + fresh Hermes session for end-to-end testing.

### Implemented in code (awaiting rebuild + test)

| Phase | Status |
|-------|--------|
| A-1 — Install bridge on sys.path | **Implemented, awaiting rebuild** |
| A-2 — Remove silent ImportError | **Implemented, awaiting rebuild** |
| A-3 — Register finance callbacks | **Implemented, awaiting rebuild** |
| A-4 — Add `_unsync_warroom` to FinanceApprovalHandler | **Implemented, awaiting rebuild** |
| B-1 — Fix HTMX outerHTML bug | **Implemented, awaiting rebuild** |
| C-1 — Add war room start to `scripts/start.sh` | **Implemented, awaiting rebuild** |
| C-2 — Add socat forwarder for port 9090 | **Implemented as part of C-1** |

### Not yet implemented

| Phase | Status |
|-------|--------|
| B-2 — WebSocket push | **Not started** |
| B-3 — Filesystem watcher | **Not started** |
| C-3 — Wire OpenShell port 9090 forward | **Not started** (requires NemoClaw/OpenShell allow-list change) |
| D-1 — Authenticate GET | **Not started** |
| D-2 — Rate limiting POST | **Not started** |
| D-3 — Operator logging | **Not started** |
| E-1 — Audit/history view | **Not started** |
| E-2 — Action detail modal | **Not started** |
| E-3 — SLA age indicator | **Not started** |
| E-4 — Desktop notifications | **Not started** |
| E-5 — Keyboard shortcuts | **Not started** |
| F-1 — ASGI server | **Not started** |
| F-2 — Centralize resolve_mesh_dir | **Not started** |
| F-3 — WebSocket replay buffer | **Not started** |

### Known current behaviour (pre-fix baseline — do not treat as verified outcomes)

These were observed running the **un-patched** version of the war room before the fixes above were baked into a rebuilt image:

- War Room UI loads at `http://localhost:9090/warroom.html` — page renders in browser
- Claw health panel renders — shows claw status cards
- Cost guard panel renders — shows daily token usage bar
- Hold queue section renders — but **approve / veto buttons do not act reliably after first interaction** — consistent with the `hx-swap="outerHTML"` polling-destruction bug (B-1)
- Server requires **manual start** in a separate terminal: `python3 milimo-hermes-plugin/warroom/server.py 9090` — consistent with C-1/C-2/C-3 not yet implemented in `scripts/start.sh`

**Next implementation step**: B-1 (HTMX outerHTML fix) — the shortest path to a functioning approve/veto flow. C-1/C-2 (auto-start + socat forwarder) follows.

---

## Related Pages

- [[war-room]] — War Room overview
- [[war-room-security]] — Security audit and hardening status
- [[spend-warroom-bridge]] — Finance spend → War Room bridge documentation
- [[spend-handler]] — SpendApprovalHandler implementation
- [[link-cli-setup]] — Stripe Link CLI auth and configuration
- [[approval-thresholds]] — REVIEW/HOLD/AUTO mode definitions
- [[production-spend-flow-fix-plan-2026-07-06]] — Earlier production spend flow fix plan (prompt/context layer)
- [[production-readiness-audit-2026-07-03]] — Earlier line-level code audit (all Phase 1+2 findings closed)

---

## See Also

- `milimo-hermes-sandbox/milimo-hermes-plugin/warroom/server.py` — HTMX server
- `milimo-hermes-sandbox/milimo-hermes-plugin/warroom/warroom_bridge.py` — Bridge layer
- `milimo-hermes-sandbox/milimo-hermes-plugin/warroom/warroom.html` — Dashboard UI
- `milimo-hermes-sandbox/scripts/start.sh` — Container entrypoint
