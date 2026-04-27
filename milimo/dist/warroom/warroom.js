"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.WarRoomTUI = void 0;
const readline = __importStar(require("readline"));
const approval_1 = require("./approval");
const audit_1 = require("./audit");
const evolution_1 = require("./evolution");
class WarRoomTUI {
    squadId;
    operatorId;
    rl;
    engine;
    audit;
    evolution;
    isRunning = false;
    refreshInterval = null;
    pendingQueue = [];
    constructor(squadId, operatorId = "local-operator") {
        this.squadId = squadId;
        this.operatorId = operatorId;
        this.engine = new approval_1.ApprovalEngine(squadId);
        this.audit = new audit_1.AuditLogger(squadId);
        this.evolution = new evolution_1.EvolutionManager(squadId);
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
        });
    }
    start() {
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
                process.stdout.write(`\n[ALERT] New pending action arrived. (${this.pendingQueue.length} total)\nmilimo> `);
            }
        }, 5000);
        this.rl.on("line", (line) => {
            this.handleCommand(line.trim());
        });
    }
    stop() {
        this.isRunning = false;
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.rl.close();
        console.log("\nExiting War Room. Claws will continue operating.");
    }
    refreshQueue() {
        this.pendingQueue = this.engine.getPendingMessages();
    }
    displayPrompt() {
        if (!this.isRunning)
            return;
        this.rl.setPrompt("milimo> ");
        this.rl.prompt();
    }
    handleCommand(cmd) {
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
                this.evolution.showCrossClawFlows();
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
    listPending() {
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
            console.log(`${msg.message_id} | ${msg.sender_role} -> ${msg.recipient_role} | ${msg.message_type} ${modeTag}`);
        });
        console.log("");
    }
    viewAction(id) {
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
            const triggerPattern = payload?.trigger_pattern;
            console.log(` Trigger: ${String(triggerPattern?.trigger_description)}`);
            console.log(` Expected Uplift: +${String(payload?.estimated_improvement)}% on ${String(payload?.metric_target)}`);
            const dataSources = payload?.data_sources_required;
            console.log(`  Data Sources: ${dataSources?.join(", ")}`);
        }
        else {
            console.log(JSON.stringify(msg.payload, null, 2));
        }
        const evalResult = this.engine.evaluateAction(msg);
        if (evalResult.description) {
            console.log(`Notice: ${evalResult.description}`);
        }
        console.log("------------------\n");
    }
    processAction(id, decision) {
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
    showFeed() {
        const logs = this.audit.getRecentLogs(10);
        if (logs.length === 0) {
            console.log("Audit trail is empty.");
            return;
        }
        console.log("\n--- Recent Activity Feed ---");
        logs.forEach((log) => {
            const roleBlock = log.clawRole ? `[${log.clawRole}] ` : "";
            const decisionBlock = log.decision ? ` -> ${log.decision}` : "";
            console.log(`${log.timestamp} | ${roleBlock}${log.actionType}${decisionBlock} (Op: ${log.operatorId || "system"})`);
        });
        console.log("----------------------------\n");
    }
}
exports.WarRoomTUI = WarRoomTUI;
//# sourceMappingURL=warroom.js.map