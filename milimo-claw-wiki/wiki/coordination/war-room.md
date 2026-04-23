# War Room

**Summary**: Terminal UI for viewing all pending actions from every claw.

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
| **R** | Release | Release current HOLD |
| **D** | Digest | Toggle morning/evening digest |
| **F** | Finals | Toggle Deep Work Mode |
| **H** | Help | Show help overlay |
| **Q** | Quit | Exit War Room |

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
- [[content-claw]] — Content actions
- [[ops-claw]] — Ops actions
- [[finance-claw]] — Finance actions
- [[build-claw]] — Build actions
- [[assistant-lucy]] — Assistant actions
