# War Room

**Summary**: Terminal UI for viewing all pending actions from every claw. Also includes the dynamic HTMX server for a web-based War Room dashboard with per-operator approval routing.

**Sources**:
- `milimo/src/warroom/warroom-tui.ts`
- `raw/AGENTS.md`

**Last updated**: 2026-04-23

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
```

## Components

### War Room TUI

Location: `milimo/src/warroom/warroom-tui.ts`

Terminal UI built with blessed.

```typescript
class WarRoomTUI {
  // Main entry point
  start(): void;

  // Render queue
  renderQueue(): void;

  // Handle keyboard input
  handleInput(key: string): void;
}
```

### Approval Engine

Location: `milimo/src/warroom/approval.ts`

Handles REVIEW/HOLD/AUTO decisions.

```typescript
class ApprovalEngine {
  // Process approval decision
  processApproval(itemId: string, decision: 'approve' | 'block'): void;

  // Release HOLD
  releaseHold(itemId: string): void;

  // Queue new action
  queueAction(action: PendingAction): void;
}
```

### HTMX War Room Server

Location: `milimo-hermes-plugin/warroom/server.py`

Dynamic HTTP server that replaces the static `python3 -m http.server`. Serves the static `warroom.html` dashboard and handles dynamic `/v1/warroom/...` HTMX endpoints. Approvals route directly into the inter-claw gateway mailboxes.

```bash
# Start the HTMX War Room dashboard (default port 9090 to avoid
# conflicts with the OpenClaw/OpenShell gateway on 8080)
python3 milimo-hermes-plugin/warroom/server.py
# → http://localhost:9090/warroom.html
```

Key endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server liveness check |
| `/warroom.html` | GET | Full dashboard shell |
| `/v1/warroom/claw-status` | GET | Live claw status (auto-refresh 5s) |
| `/v1/warroom/hold-queue` | GET | Live action queue (auto-refresh 5s) |
| `/v1/warroom/cost-guard` | GET | Daily token usage (auto-refresh 10s) |
| `/v1/warroom/last-updated` | GET | Server timestamp (auto-refresh 30s) |
| `/v1/warroom/hold-queue/{action_id}/approve` | POST | Approve a REVIEW or release a HOLD |
| `/v1/warroom/hold-queue/{action_id}/veto` | POST | Veto / block an action |

The server scopes approval sessions per operator (by `MILIMO_OPERATOR`), so concurrent operators do not interfere with each other's queue state.

### Audit Trail

Location: `milimo/src/warroom/audit.ts`

Logs all approval decisions.

```typescript
class AuditTrail {
  // Log approval decision
  logDecision(decision: ApprovalDecision): void;

  // Get audit history
  getHistory(filters: AuditFilters): AuditEntry[];
}
```

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
