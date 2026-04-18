# Bridge Tools

**Summary**: TypeScript wrapper for Python bridge CLI commands.

**Sources**:
- `milimo/src/lib/bridge-tools.ts`

**Last updated**: 2026-04-15

**Tags**: #typescript #bridge #tools

---

## Overview

BridgeTools provides a typed wrapper around `bridge_cli.py`, exposing all Python commands as discoverable tools for the assistant (Lucy).

---

## Key Class

### `BridgeTools`

```typescript
class BridgeTools {
  constructor(options: BridgeToolsOptions) {}

  // Claw status
  async clawStatus(params: { role: string }): Promise<ClawStatusResult>

  // Send message to claw
  async sendToClaw(params: SendToClawParams): Promise<SendToClawResult>

  // Mesh state
  async meshFlowState(): Promise<MeshFlowStateResult>

  // Ops projects
  async opsProjects(): Promise<OpsProjectsResult>

  // Content drafts
  async contentDrafts(): Promise<ContentDraftsResult>

  // Build PRs
  async buildPrs(): Promise<BuildPrsResult>

  // Analytics report
  async analyticsReport(params: { filename?: string }): Promise<AnalyticsReportResult>

  // Sprint plan
  async sprintPlan(params: SprintPlanParams): Promise<SprintPlanResult>

  // Tool registry
  async toolRegistry(params: { role: string }): Promise<ToolRegistry>
}
```

---

## Response Types

### `ClawStatusResult`

```typescript
interface ClawStatusResult {
  role: string;
  health: Record<string, unknown>;
  tool_count: number;
  last_evolution: string | null;
  pending_messages: Array<{
    message_id: string;
    sender: string;
    type: string;
    timestamp: string;
  }>;
  sandbox_exists: boolean;
  sandbox_contents?: string[];
}
```

### `SendToClawResult`

```typescript
interface SendToClawResult {
  delivered: boolean;
  message_id: string;
  reason: string;
  requires_approval: boolean;
  recipient: string;
  message_type: string;
}
```

### `MeshFlowStateResult`

```typescript
interface MeshFlowStateResult {
  nodes: Record<string, {
    status: string;
    address: string;
    last_heartbeat: string | null;
    pending_messages: number;
  }>;
  total_pending: number;
  delivered_this_week: number;
  pending_by_claw: Record<string, number>;
  transport_mode: string;
  last_updated: string;
}
```

---

## Tool Discovery

BridgeTools exposes metadata for assistant tool discovery:

```typescript
interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, {
    type: string;
    description: string;
    required?: boolean;
  }>;
}

interface ToolRegistry {
  tools: ToolInfo[];
  total: number;
}
```

---

## Usage

```typescript
const tools = new BridgeTools({
  blueprintDir: "/opt/milimo-blueprint"
});

// Get claw status
const status = await tools.clawStatus({ role: "build" });

// Send message
const result = await tools.sendToClaw({
  role: "ops",
  type: "assistant_query",
  payload: { query: "What's the project status?" }
});
```

---

## Integration

### With Python Bridge

```typescript
import { callPythonBridgeSafe } from "./python-bridge.js";

const response = await callPythonBridgeSafe("claw_status", {
  role: "build"
});
```

---

## Related Pages

- [[cli-commands]] — CLI commands
- [[warroom-tui]] — TUI
- [[mesh-gateway-client]] — Gateway client
