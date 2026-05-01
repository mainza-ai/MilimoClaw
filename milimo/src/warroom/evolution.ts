// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { readdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { callPythonBridgeSafe } from "../lib/python-bridge.js";

interface MeshFlowSignal {
  signal_type: string;
  source_claw: string;
  destination_claw: string;
  last_transmission?: string;
}

interface MeshFlowState {
  signals: MeshFlowSignal[];
  last_transmission?: string;
  signal_count_this_week: number;
}

export class EvolutionManager {
  private toolsDir: string;
  private blueprintDir: string;

  constructor(
    private squadId: string,
    blueprintDir?: string,
  ) {
    const home = process.env.HOME || process.env.USERPROFILE || homedir() || "/tmp";
    this.toolsDir = join(home, ".openclaw/milimo", "tools", squadId);
    this.blueprintDir = blueprintDir || process.env.MILIMO_BLUEPRINT_DIR || "/opt/milimo-blueprint";
  }

  public showEvolutionLog(): void {
    console.log("\n--- SQUAD EVOLUTION LOG ---");
    try {
      const roles = readdirSync(this.toolsDir);
      for (const role of roles) {
        if (role.startsWith(".")) continue;

        const regPath = join(this.toolsDir, role, "registry.json");
        try {
          const content = readFileSync(regPath, "utf8");
          const registry = JSON.parse(content);
          const tools = registry.tools || {};

          console.log(`\n[${role.toUpperCase()} CLAW]`);
          if (Object.keys(tools).length === 0) {
            console.log(" No evolved tools yet.");
            continue;
          }

          for (const [name, tool] of Object.entries<any>(tools)) {
            const statusMark = tool.status === "deployed" ? "🟢" : "🔴";
            const trigger =
              tool.proposal?.trigger_pattern?.trigger_description || "Unknown trigger";
            console.log(
              ` ${statusMark} ${name} v${tool.version || "1.0.0"} | ${statusMark === "🟢" ? "ACTIVE" : "DISABLED"}`,
            );
            console.log(` Trigger: ${trigger}`);
            console.log(` Impact: +${tool.performance_delta?.toFixed(1) || "?"}% uplift`);
          }
        } catch {
          // ignore missing registry or unreadable file for this role
        }
      }
    } catch {
      console.log("No evolution data found. Claws are still gathering observations.");
    }
    console.log("\n---------------------------\n");
  }

  public toggleTool(role: string, toolName: string, enable: boolean): void {
    if (!role || !toolName) {
      console.log("Usage: enable-tool/disable-tool <role> <tool_name>");
      return;
    }

    const regPath = join(this.toolsDir, role, "registry.json");
    try {
      const content = readFileSync(regPath, "utf8");
      const registry = JSON.parse(content);

      if (!registry.tools || !registry.tools[toolName]) {
        console.log(`Tool '${toolName}' not found for role '${role}'.`);
        return;
      }

      registry.tools[toolName].status = enable ? "deployed" : "disabled";
      writeFileSync(regPath, JSON.stringify(registry, null, 2));
      console.log(`Tool '${toolName}' has been ${enable ? "ENABLED" : "DISABLED"}.`);
    } catch (e) {
      console.log(`Failed to toggle tool: ${String(e)}`);
    }
  }

  public showCrossClawFlows(): void {
    console.log("\n--- CROSS-CLAW EVOLUTION FLOWS ---");
    console.log("Visualizing signal routing between claws based on mesh configurations.");
    console.log("");

    const flowState = this.getMeshFlowState();

    if (!flowState || flowState.signals.length === 0) {
      console.log(" Signal data unavailable.");
      console.log("");
      console.log(" [Analytics Claw] ===(Retention Signals)===> [Content Claw]");
      console.log(" [Finance Claw] ===(Risk Annotations)===> [Ops Claw]");
      console.log(" [Ops Claw] ===(Engagement Flags)===> [Content Claw]");
      console.log("");
      console.log(" (Showing default flow diagram - connect to mesh for live data)");
    } else {
      console.log(` Signal count this week: ${flowState.signal_count_this_week}`);
      console.log("");
      for (const signal of flowState.signals) {
        const lastTx = signal.last_transmission ? ` (${signal.last_transmission})` : "";
        console.log(
          ` [${signal.source_claw.toUpperCase()} Claw] ===(${signal.signal_type})===> [${signal.destination_claw.toUpperCase()} Claw]${lastTx}`,
        );
      }
      if (flowState.last_transmission) {
        console.log("");
        console.log(` Last mesh transmission: ${flowState.last_transmission}`);
      }
    }

    console.log("");
    console.log("Signals are ingested during the OBSERVE stage to trigger new tool proposals.");
    console.log("----------------------------------\n");
  }

  private getMeshFlowState(): MeshFlowState | null {
    try {
      const response = callPythonBridgeSafe<MeshFlowState>(
        "mesh_flow_state",
        { squad: this.squadId },
        { blueprintDir: this.blueprintDir },
      );

      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch {
      return null;
    }
  }

  public getMeshFlowData(): MeshFlowState | null {
    return this.getMeshFlowState();
  }
}
