# Bridge Tools

**Summary**: TypeScript wrapper for Python bridge CLI commands.

**Sources**:
- `milimo/src/lib/bridge-tools.ts`
- `milimo/src/lib/python-bridge.ts`
- `milimo/src/lib/rpc-bridge.ts`

**Last updated**: 2026-06-19

**Tags**: #typescript #bridge #tools

---

## Overview

BridgeTools provides a typed wrapper around `bridge_cli.py`, exposing all Python commands as discoverable tools for the assistant (Lucy). Communication flows through the persistent Python RPC server (`bridge_server.py`) via `rpc-bridge.ts`.

---

## Key Class

### `BridgeTools`

```typescript
class BridgeTools {
  constructor(options: BridgeToolsOptions) {}

  async clawStatus(params: { role: string }): Promise<ClawStatusResult>
  async sendToClaw(params: SendToClawParams): Promise<SendToClawResult>
  async meshFlowState(): Promise<MeshFlowStateResult>
  async opsProjects(): Promise<OpsProjectsResult>
  async contentDrafts(): Promise<ContentDraftsResult>
  async buildPrs(): Promise<BuildPrsResult>
  async analyticsReport(params: { filename?: string }): Promise<AnalyticsReportResult>
  async sprintPlan(params: SprintPlanParams): Promise<SprintPlanResult>
  async toolRegistry(params: { role: string }): Promise<ToolRegistry>
}
```

---

## Integration

### RPC-Based Communication (Current)

All bridge calls go through the persistent Python RPC server at `127.0.0.1:19999`:

```
BridgeTools.callPythonBridgeSafe()
  └── rpc-bridge.ts (HTTP fetch to bridge_server.py)
      └── bridge_server.py (persistent Python process)
          └── bridge_cli.py (command handler)
```

No `child_process` is involved in the TypeScript plugin — the Python server runs as a persistent background process managed by OpenClaw's service manager or the install script.

---

## Related Pages

- [[cli-commands]] — CLI commands
- [[warroom-tui]] — TUI
- [[mesh-gateway-client]] — Gateway client
