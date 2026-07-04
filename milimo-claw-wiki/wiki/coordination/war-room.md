# War Room

**Summary**: Terminal UI for viewing all pending actions from every claw. Also includes the dynamic HTMX server for a web-based War Room dashboard with per-operator approval routing.

**Sources**:
- `milimo-hermes-plugin/warroom/server.py`
- `milimo-hermes-plugin/warroom/warroom.html`
- `milimo-hermes-plugin/warroom/warroom_bridge.py`
- `raw/AGENTS.md`

**Last updated**: 2026-07-04

**Tags**: #coordination #warroom #tui

---

## Overview

The War Room surfaces every pending action from every claw in one prioritized queue. It's the human interface for monitoring and controlling MilimoClaw.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ WAR ROOM TUI                                                    │
├─────────────────────────────────────────────────────────────────┤
│ 🔴 HOLD QUEUE                                                   │
│   ├─ Invoice send - Finance Claw - $2,400                       │
│   └─ Deadline critical - Ops Claw - Acme Project                │
├─────────────────────────────────────────────────────────────────┤
│ 🟡 REVIEW QUEUE                                                 │
│   ├─ Social post draft - Content Claw - Twitter thread          │
│   ├─ PR review - Build Claw - Fix login bug                     │
│   └─ Client proposal - Ops Claw - New Project                   │
├─────────────────────────────────────────────────────────────────┤
│ ✓ AUTO LOG (today)                                              │
│   ├─ Expense logged - Finance Claw                              │
│   ├─ Health score calculated - Ops Claw                         │
│   └─ Daily report generated - Analytics Claw                    │
└─────────────────────────────────────────────────────────────────┘
         ↕ HTTPS (HTMX polling)
┌─────────────────────────────────────────────────────────────────┐
│ HTMX WAR ROOM SERVER (port 9090)                                 │
│   POST /v1/warroom/hold-queue/{id}/approve  →  Bearer auth req  │
│   POST /v1/warroom/hold-queue/{id}/veto     →  Origin check    │
│   GET  /health                              →  {"status":"ok"}  │
│   GET  /warroom.html                        →  Dashboard shell  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### War Room TUI

The terminal UI for the War Room is provided by the [[solo-warroom]] module. It surfaces every pending action from every claw in one prioritized queue.

### HTMX War Room Server

Location: `milimo-hermes-plugin/warroom/server.py`

Dynamic HTTP server that serves the static `warroom.html` dashboard and handles dynamic `/v1/warroom/...` HTMX endpoints. Approvals route directly into the inter-claw gateway mailboxes. The server is hardened for production use: Bearer auth, path traversal protection, graceful SIGTERM shutdown, security headers, and per-operator isolation.

```bash
# Start the HTMX War Room dashboard (port 9090; 8080 is reserved for
# the OpenShell gateway)
python3 milimo-hermes-plugin/warroom/server.py
# → http://localhost:9090/warroom.html
```

**Environment variables**:

| Variable | Purpose | Default |
|----------|---------|---------|
| `WARROOM_AUTH_TOKEN` | Bearer token required for all POST endpoints | unset (server starts but POSTs return 500) |
| `MILIMO_CORE_PATH` | Override path to `milimo_core` package | resolved relative to `server.py` |

Key endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Server liveness check — returns `{"status": "ok"}` |
| `/warroom.html` | GET | No | Full dashboard shell |
| `/v1/warroom/claw-status` | GET | No | Live claw status (auto-refresh 5s) |
| `/v1/warroom/hold-queue` | GET | No | Live action queue (auto-refresh 5s) |
| `/v1/warroom/cost-guard` | GET | No | Daily token usage (auto-refresh 10s) |
| `/v1/warroom/last-updated` | GET | No | Server timestamp (auto-refresh 30s) |
| `/v1/warroom/hold-queue/{action_id}/approve` | POST | Bearer | Approve a REVIEW or release a HOLD |
| `/v1/warroom/hold-queue/{action_id}/veto` | POST | Bearer | Veto / block an action |

**Security**:
- All POST endpoints require `Authorization: Bearer <WARROOM_AUTH_TOKEN>`.
- `Origin` header is checked on POST; cross-origin requests are rejected with 403.
- `action_id` is validated against `^[a-zA-Z0-9_-]+$`; path traversal payloads return 400.
- Responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`.

**Graceful shutdown**: `SIGTERM` and `SIGINT` trigger `server.shutdown()` from a signal handler, allowing in-flight approvals to complete cleanly. Shutdown completes in ~0.5s.

### War Room Bridge

Location: `milimo-hermes-plugin/warroom/warroom_bridge.py`

`SpendWarRoomBridge` connects `SpendApprovalHandler` to the existing `SoloWarRoom` action queue. Claws call the bridge instead of touching `SpendApprovalHandler` directly. See [[spend-warroom-bridge]] for details.

### Audit Trail

Location: `milimo-hermes-plugin/warroom/` (shared with [[spend-handler]])

All approval decisions are logged to `decisions.log` (same format as `FinanceApprovalHandler`), with stage vocabulary (`review`, `hold`) and action types (`queued`, `approve`, `block`, `release`, `cancel`, `purchase_approved`, `purchase_denied`).

Queue state is persisted to `agent-spend.log` so that pending REVIEW and HOLD entries survive process restarts.

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| **A** | Approve | Approve current REVIEW item |
| **B** | Block | Block current item |
| **E** | Edit | Edit item inline |
| **R** | Release / Refresh | Release current HOLD if selected item is in HOLD mode; otherwise refresh the queue |
| **D** | Digest | Toggle morning/evening digest |
| **F** | Finals | Toggle Deep Work Mode |
| **H** | Help | Show help overlay |
| **Q** | Quit | Exit War Room |

> **Note**: `R` is context-sensitive. If the current selected message is in HOLD mode (e.g. `spend_hold_decision` or `hold_release`), pressing `R` invokes the approval/release flow. Otherwise it falls back to a standard queue refresh. This avoids accidental refreshes when the operator meant to release a spend.

## Daily Schedule

### Morning Brief (07:00)

Shows:
- Overnight AUTO log
- Pending queue summary
- SLA violations
- Health alerts

### Evening Wrap (20:00)

Shows:
- Today's activity summary
- Tomorrow's queue preview
- Pending HOLD items

## Deep Work Mode

When enabled:

```bash
milimo squad finals-mode --duration 2weeks --resume-date 2026-05-12
```

### Per-Claw Behavior

| Claw | Still Runs | Paused |
|------|------------|--------|
| Content | Nothing | Draft generation, publishing |
| Ops | Auto-responses to active clients | New client intake |
| Analytics | Passive data collection | New experiments, opportunity scoring |
| Finance | Invoice sends, payment monitoring | New project initiations |
| Build | Issue triage, error monitoring | New PRs, deploys, code generation |
| Assistant | Query responses, digest delivery | Proactive notifications, outbound queries |

### Auto-Response (Ops Claw)

> "Hey [client_name], I'm heads-down on a focused sprint until [resume_date]. Your project is on track — I'll be back in full swing then. 🙏"

## Related Pages

- [[approval-thresholds]] — Approval modes
- [[sequencing-rules]] — Ordering constraints
- [[spend-handler]] — Stripe Link spend approval and operator isolation
- [[link-cli-setup]] — Stripe Link CLI auth and per-operator tokens
- [[content-claw]] — Content actions
- [[ops-claw]] — Ops actions
- [[finance-claw]] — Finance actions
- [[build-claw]] — Build actions
- [[assistant-lucy]] — Assistant actions
