# War Room TUI

**Summary**: Split-pane terminal UI for viewing pending actions and claw health.

**Sources**:
- `milimo/src/warroom/warroom-tui.ts`

**Last updated**: 2026-04-15

**Tags**: #tui #typescript #warroom

---

## Overview

War Room TUI is a blessed-based terminal UI that displays:
- **Left panel**: Pending action queue (HOLD/REVIEW/AUTO)
- **Right panel**: Claw health status and revenue
- **Bottom bar**: Keyboard shortcuts and status

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `A` | Approve selected action |
| `B` | Block selected action |
| `E` | Edit action payload |
| `Q` | Quit TUI |
| `R` | Refresh queue |
| `H` | Toggle help overlay |
| `F` | Toggle finals mode |
| `D` | Show digest overlay |

---

## Color Coding

| Color | Mode | Meaning |
|-------|------|---------|
| Coral | HOLD | Requires explicit release |
| Amber | REVIEW | Needs operator approval |
| Teal | AUTO | Executed automatically |

---

## Key Classes

### `WarRoomTUI`

```typescript
class WarRoomTUI {
  constructor(options: WarRoomTUIOptions) {}

  // Start the TUI
  async start(): Promise<void>

  // Stop the TUI
  stop(): void

  // Refresh pending queue
  private async refreshQueue(): Promise<void>

  // Handle keyboard input
  private handleKey(ch: string, key: any): void
}
```

### Interfaces

```typescript
interface WarRoomTUIOptions {
  squadId: string;
  operatorId?: string;
  tier?: "free" | "pro";
  blueprintDir?: string;
  digestConfig?: {
    morning_time: { hour: number; minute: number };
    evening_time: { hour: number; minute: number };
  };
}

interface ClawHealth {
  name: string;
  status: "active" | "idle" | "error";
  tools: number;
  lastCycle?: string;
}

interface RevenueSummary {
  week_revenue: number;
  week_over_week_pct: number;
  invoices_paid: number;
  invoices_pending: number;
  last_updated: string;
}
```

---

## Polling

| Data | Interval |
|------|----------|
| Pending queue | 3 seconds |
| Revenue data | 30 seconds |

---

## Integration

### With ApprovalEngine

```typescript
this.engine = new ApprovalEngine(this.squadId, options.tier ?? "free");
const pending = await this.engine.getPending();
```

### With EvolutionManager

```typescript
this.evolution = new EvolutionManager(this.squadId);
const lastCycle = this.evolution.getLastCycle();
```

### With AuditLogger

```typescript
this.audit = new AuditLogger(this.squadId);
this.audit.logAction(action, decision);
```

---

## Finals Mode

When enabled (`F` key), TUI shows only:
- High-priority actions
- Blocking holds
- Critical alerts

---

## Related Pages

- [[war-room]] — War Room overview
- [[approval-handler]] — Approval queue
- [[approval-thresholds]] — Mode definitions
