// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import * as readline from "readline";
import { ApprovalEngine, PendingMessage } from "./approval";
import { AuditLogger } from "./audit";
import { EvolutionManager } from "./evolution";

export class WarRoomTUI {
  private rl: readline.Interface;
  private engine: ApprovalEngine;
  private audit: AuditLogger;
  private evolution: EvolutionManager;
  private isRunning: boolean = false;
  private refreshInterval: NodeJS.Timeout | null = null;
  private pendingQueue: PendingMessage[] = [];

  constructor(
    private squadId: string,
    private operatorId: string = "local-operator",
  ) {
    this.engine = new ApprovalEngine(squadId);
    this.audit = new AuditLogger(squadId);
    this.evolution = new EvolutionManager(squadId);

    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
  }

  public start() {
    this.isRunning = true;
    console.clear();
    console.log("--- MILIMO CLAW: WAR ROOM ---");
    console.log(`Squad: ${this.squadId} | Operator: ${this.operatorId}`);
    console.log('Type "help" for commands, "exit" to leave.\n');

    // Initial load
    this.refreshQueue();
    this.displayPrompt();

    // Background poll for new messages
    this.refreshInterval = setInterval(() => {
      const oldLen = this.pendingQueue.length;
      this.refreshQueue();
      if (this.pendingQueue.length > oldLen) {
        process.stdout.write(
          `\n[ALERT] New pending action arrived. (${this.pendingQueue.length} total)\nmilimo> `,
        );
      }
    }, 5000);

    this.rl.on("line", (line) => {
      this.handleCommand(line.trim());
    });
  }

  public stop() {
    this.isRunning = false;
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
    this.rl.close();
    console.log("\nExiting War Room. Claws will continue operating.");
  }

  private refreshQueue() {
    this.pendingQueue = this.engine.getPendingMessages();
  }

  private displayPrompt() {
    if (!this.isRunning) return;
    this.rl.setPrompt("milimo> ");
    this.rl.prompt();
  }

  private handleCommand(cmd: string) {
    const parts = cmd.split(" ");
    const action = parts[0].toLowerCase();

    switch (action) {
      case "help":
        console.log(`
Commands:
  ls          - List pending actions in queue
  view <id>   - View details of a pending action
  approve <id>- Approve an action (sends to recipient)
  veto <id>   - Reject an action (moves to rejected)
  hold <id>   - Defer an action (leaves in queue)
  feed        - View recent audit trail
  evolution   - View squad evolution log and deployed tools
  disable-tool <role> <tool> - Disable an evolved tool
  enable-tool <role> <tool>  - Enable an evolved tool
  flows       - View cross-claw evolution signal flows
  exit        - Leave the War Room
`);
        break;

      case "ls":
        this.listPending();
        break;

      case "view":
        this.viewAction(parts[1]);
        break;

      case "approve":
        this.processAction(parts[1], "APPROVED");
        break;

      case "veto":
        this.processAction(parts[1], "REJECTED");
        break;

      case "hold":
        this.processAction(parts[1], "DELEGATED");
        break;

      case "feed":
        this.showFeed();
        break;

      case "evolution":
      case "tools":
        this.evolution.showEvolutionLog();
        break;

      case "disable-tool":
        this.evolution.toggleTool(parts[1], parts[2], false);
        break;

      case "enable-tool":
        this.evolution.toggleTool(parts[1], parts[2], true);
        break;

      case "flows":
        void this.evolution.showCrossClawFlows();
        break;

      case "exit":
      case "quit":
        this.stop();
        return;

      case "":
        break;

      default:
        console.log(`Unknown command: ${action}`);
    }

    this.displayPrompt();
  }

  private listPending() {
    this.refreshQueue();
    if (this.pendingQueue.length === 0) {
      console.log("No pending actions in queue.");
      return;
    }

    console.log(`\nPENDING ACTIONS (${this.pendingQueue.length}):`);
    this.pendingQueue.forEach((msg) => {
      const evalResult = this.engine.evaluateAction(msg);
      let modeTag = `[${evalResult.mode}]`;
      if (evalResult.trigger) {
        modeTag += `[${evalResult.trigger}]`;
      }
      console.log(
        `${msg.message_id} | ${msg.sender_role} -> ${msg.recipient_role} | ${msg.message_type} ${modeTag}`,
      );
    });
    console.log("");
  }

  private viewAction(id: string) {
    if (!id) {
      console.log("Usage: view <id>");
      return;
    }
    const msg = this.pendingQueue.find((m) => m.message_id === id);
    if (!msg) {
      console.log(`Action ${id} not found pending queue.`);
      return;
    }

    console.log(`\n--- Action ${id} ---`);
    console.log(`Time: ${msg.timestamp}`);
    console.log(`Route: ${msg.sender_role} -> ${msg.recipient_role}`);
    console.log(`Type: ${msg.message_type}`);
    console.log(`Payload:`);

    if (msg.message_type === "tool_proposal") {
      const payload = msg.payload;
      console.log(` Tool Name: ${String(payload?.tool_name)}`);
      const triggerPattern = payload?.trigger_pattern as Record<string, unknown> | undefined;
      console.log(` Trigger: ${String(triggerPattern?.trigger_description)}`);
      console.log(
        ` Expected Uplift: +${String(payload?.estimated_improvement)}% on ${String(payload?.metric_target)}`,
      );
      const dataSources = payload?.data_sources_required as string[] | undefined;
      console.log(`  Data Sources: ${dataSources?.join(", ")}`);
    } else {
      console.log(JSON.stringify(msg.payload, null, 2));
    }

    const evalResult = this.engine.evaluateAction(msg);
    if (evalResult.description) {
      console.log(`Notice: ${evalResult.description}`);
    }
    console.log("------------------\n");
  }

  private processAction(id: string, decision: "APPROVED" | "REJECTED" | "DELEGATED") {
    if (!id) {
      console.log(`Usage: ${decision.toLowerCase()} <id>`);
      return;
    }
    const msg = this.pendingQueue.find((m) => m.message_id === id);
    if (!msg) {
      console.log(`Action ${id} not found in pending queue.`);
      return;
    }

    this.engine.processDecision(msg, decision, this.operatorId);
    console.log(`Action ${id} marked as ${decision}.`);
    this.refreshQueue();
  }

  private showFeed() {
    const logs = this.audit.getRecentLogs(10);
    if (logs.length === 0) {
      console.log("Audit trail is empty.");
      return;
    }

    console.log("\n--- Recent Activity Feed ---");
    logs.forEach((log) => {
      const roleBlock = log.clawRole ? `[${log.clawRole}] ` : "";
      const decisionBlock = log.decision ? ` -> ${log.decision}` : "";
      console.log(
        `${log.timestamp} | ${roleBlock}${log.actionType}${decisionBlock} (Op: ${log.operatorId || "system"})`,
      );
    });
    console.log("----------------------------\n");
  }
}
