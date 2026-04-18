# War Room Modules

**Summary**: TypeScript modules for the War Room TUI including digest scheduler, audit logger, health collector, notifier, rate limiter, and real-time bridge.

**Sources**:
- `milimo/src/warroom/digest.ts`
- `milimo/src/warroom/audit.ts`
- `milimo/src/warroom/health-collector.ts`
- `milimo/src/warroom/notifier.ts`
- `milimo/src/warroom/rate-limiter.ts`
- `milimo/src/warroom/realtime-bridge.ts`
- `milimo/src/warroom/evolution.ts`
- `milimo/src/warroom/health-dashboard.ts`
- `milimo/src/warroom/approval.ts`

**Last updated**: 2026-04-17

**Tags**: #tui #typescript #warroom

---

## Digest Scheduler

**File**: `milimo/src/warroom/digest.ts`

Schedules morning brief (07:00) and evening wrap (20:00) digests using setTimeout with recalculated delay.

```typescript
const scheduler = new DigestScheduler({
  config: {
    morning_time: { hour: 7, minute: 0 },
    evening_time: { hour: 20, minute: 0 },
    squad_id: "my-squad"
  },
  blueprintDir: "/path/to/blueprint",
  onUpdate: (brief) => console.log(brief),
});

scheduler.start();
scheduler.getMorningBrief();
scheduler.getEveningWrap();
```

### Digest Types

| Type | Time | Content |
|------|------|---------|
| `morning` | 07:00 | Overnight actions, queue status, pending actions, evolution updates |
| `evening` | 20:00 | Today's completed, auto-executed, remaining pending |

---

## Audit Logger

**File**: `milimo/src/warroom/audit.ts`

Append-only audit log with automatic rotation at midnight and gzip compression.

```typescript
const audit = createAuditLogger("my-squad");

audit.logAction({
  actionType: "pr_review",
  decision: "APPROVED",
  operatorId: "cli",
  reason: "Looks good",
});

const recent = audit.getRecentLogs(50);
const results = audit.searchLogs({ clawRole: "build", decision: "APPROVED" });
```

### Audit Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `string` | ISO timestamp |
| `messageId` | `string` | Message ID |
| `clawRole` | `string` | Source claw |
| `actionType` | `string` | Action type |
| `decision` | `APPROVED \| REJECTED \| DELEGATED \| AUTO` | Decision |
| `operatorId` | `string` | Operator identifier |
| `reason` | `string` | Reason for decision |
| `details` | `Record<string, unknown>` | Additional details |

### Log Rotation

- Rotates at midnight (creates `warroom-YYYY-MM-DD.log`)
- Compresses rotated logs with gzip
- Retention: 90 days (configurable)
- Location: `~/.milimo/audit/{squad_id}/`

---

## Health Collector

**File**: `milimo/src/warroom/health-collector.ts`

Collects real-time health data from all squad claws. Polls at 3000ms interval.

```typescript
const collector = new HealthCollector({
  squadId: "my-squad",
  blueprintDir: "/path/to/blueprint",
  pollInterval: 3000,
});

const stop = collector.startPolling(
  (health) => console.log(health),
  (error) => console.error(error)
);

// Stop polling when done
stop();

// One-time collection
const healthMap = await collector.collectAll();
```

### ClawHealth Interface

| Field | Type | Description |
|-------|------|-------------|
| `role` | `string` | Claw role name |
| `status` | `active \| idle \| processing \| error` | Current status |
| `tool_count` | `number` | Number of tools deployed |
| `last_evolution` | `string \| null` | Last evolution timestamp |
| `last_action` | `string \| null` | Last action timestamp |
| `actions_this_week` | `number` | Actions this week |
| `sparkline` | `number[]` | Activity sparkline data |

---

## Notifier

**File**: `milimo/src/warroom/notifier.ts`

Desktop notification handler for War Room alerts.

---

## Rate Limiter

**File**: `milimo/src/warroom/rate-limiter.ts`

Rate limiting for API calls and message dispatching.

---

## Realtime Bridge

**File**: `milimo/src/warroom/realtime-bridge.ts`

Real-time communication bridge between War Room and Python backend.

---

## Evolution

**File**: `milimo/src/warroom/evolution.ts`

Evolution cycle status and controls for the War Room.

---

## Health Dashboard

**File**: `milimo/src/warroom/health-dashboard.ts`

Health metrics dashboard component for the War Room TUI.

---

## Approval

**File**: `milimo/src/warroom/approval.ts`

Approval queue management and display for the War Room.

---

## Related Pages

- [[warroom-tui]] — War Room TUI overview
- [[cli-commands]] — CLI command reference
- [[bridge-tools]] — Python bridge wrapper
