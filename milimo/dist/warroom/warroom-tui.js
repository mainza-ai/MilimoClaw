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
exports.startWarRoom = startWarRoom;
/**
 * War Room TUI — Blessed Implementation
 *
 * Split-pane terminal UI with:
 * - Left panel: War Room actions queue
 * - Right panel: Claw health status
 * - Keyboard shortcuts: A/B/E/Q/R/H/F
 * - Color coding: coral (HOLD), amber (REVIEW), teal (AUTO)
 * - 3 second polling interval
 */
const blessed = __importStar(require("blessed"));
const approval_js_1 = require("./approval.js");
const audit_js_1 = require("./audit.js");
const evolution_js_1 = require("./evolution.js");
const digest_js_1 = require("./digest.js");
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
class WarRoomTUI {
    screen;
    leftPanel;
    rightPanel;
    bottomBar;
    helpOverlay = null;
    digestOverlay = null;
    engine;
    audit;
    evolution;
    digestScheduler = null;
    pendingQueue = [];
    selectedAction = null;
    currentIndex = 0;
    finalsMode = false;
    revenueData = null;
    revenuePollInterval = null;
    currentDigest = null;
    hasNewDigest = false;
    squadId;
    operatorId;
    blueprintDir;
    refreshInterval = null;
    isRunning = false;
    COLORS = {
        coral: "#FF6B6B",
        amber: "#FFB347",
        teal: "#20B2AA",
        success: "#50C878",
        error: "#FF4444",
        header: "#87CEEB",
        text: "#FFFFFF",
        dim: "#888888",
    };
    POLL_INTERVAL = 3000;
    REVENUE_POLL_INTERVAL = 30000;
    constructor(options) {
        this.squadId = options.squadId;
        this.operatorId = options.operatorId ?? "local-operator";
        this.blueprintDir = options.blueprintDir ?? process.cwd();
        this.engine = new approval_js_1.ApprovalEngine(this.squadId, options.tier ?? "free");
        this.audit = new audit_js_1.AuditLogger(this.squadId);
        this.evolution = new evolution_js_1.EvolutionManager(this.squadId);
        if (options.digestConfig) {
            this.digestScheduler = new digest_js_1.DigestScheduler({
                config: {
                    ...options.digestConfig,
                    squad_id: this.squadId,
                },
                blueprintDir: this.blueprintDir,
                onUpdate: (brief) => {
                    this.currentDigest = brief;
                    this.hasNewDigest = true;
                    this.updateBottomBar();
                    this.screen.render();
                },
                onError: (error) => {
                    this.rightPanel.setContent(`{red-fg}Digest error: ${error.message}{/red-fg}`);
                    this.screen.render();
                },
            });
        }
        this.screen = blessed.screen({
            smartCSR: true,
            title: `Milimo War Room — ${this.squadId}`,
            fullUnicode: true,
        });
        this.leftPanel = blessed.box({
            top: 0,
            left: 0,
            width: "60%",
            height: "90%",
            label: " WAR ROOM ",
            border: { type: "line" },
            style: {
                border: { fg: this.COLORS.header },
                label: { fg: this.COLORS.header },
            },
            scrollable: true,
            alwaysScroll: true,
            keys: true,
            vi: true,
            tags: true,
        });
        this.rightPanel = blessed.box({
            top: 0,
            left: "60%",
            width: "40%",
            height: "90%",
            label: " CLAW HEALTH ",
            border: { type: "line" },
            style: {
                border: { fg: this.COLORS.header },
                label: { fg: this.COLORS.header },
            },
            scrollable: true,
            alwaysScroll: true,
            tags: true,
        });
        this.bottomBar = blessed.box({
            bottom: 0,
            left: 0,
            width: "100%",
            height: 3,
            content: "{bold}[Q]{/bold}uit  {bold}[R]{/bold}efresh  {bold}[H]{/bold}elp  {bold}[F]{/bold}inals Mode: OFF",
            tags: true,
            style: {
                bg: "#333333",
                fg: this.COLORS.text,
            },
        });
        this.screen.append(this.leftPanel);
        this.screen.append(this.rightPanel);
        this.screen.append(this.bottomBar);
        this.setupKeyBindings();
    }
    start() {
        this.isRunning = true;
        this.refresh();
        this.fetchRevenueData();
        this.screen.render();
        this.refreshInterval = setInterval(() => {
            this.refresh();
            this.screen.render();
        }, this.POLL_INTERVAL);
        this.revenuePollInterval = setInterval(() => {
            this.fetchRevenueData();
            this.screen.render();
        }, this.REVENUE_POLL_INTERVAL);
        if (this.digestScheduler) {
            this.digestScheduler.start();
        }
    }
    stop() {
        this.isRunning = false;
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        if (this.revenuePollInterval) {
            clearInterval(this.revenuePollInterval);
            this.revenuePollInterval = null;
        }
        if (this.digestScheduler) {
            this.digestScheduler.stop();
        }
        this.screen.destroy();
    }
    setupKeyBindings() {
        this.screen.key(["q", "Q"], () => this.stop());
        this.screen.key(["r", "R"], () => {
            this.refresh();
            this.screen.render();
        });
        this.screen.key(["h", "H"], () => this.toggleHelp());
        this.screen.key(["f", "F"], () => {
            this.finalsMode = !this.finalsMode;
            this.updateBottomBar();
            this.screen.render();
        });
        this.screen.key(["d", "D"], () => this.toggleDigest());
        this.screen.key(["a", "A"], () => this.approveAction());
        this.screen.key(["b", "B"], () => this.blockAction());
        this.screen.key(["e", "E"], () => this.editAction());
        this.screen.key(["up"], () => this.navigateUp());
        this.screen.key(["down"], () => this.navigateDown());
        this.screen.key(["enter"], () => this.selectAction());
    }
    toggleHelp() {
        if (this.helpOverlay) {
            this.helpOverlay.destroy();
            this.helpOverlay = null;
        }
        else {
            this.helpOverlay = blessed.box({
                top: "center",
                left: "center",
                width: "60%",
                height: "70%",
                label: " HELP ",
                border: { type: "line" },
                style: {
                    border: { fg: "yellow" },
                    label: { fg: "yellow" },
                },
                content: `
{bold}KEYBOARD SHORTCUTS{/bold}

{bold}Navigation:{/bold}
↑/↓ Navigate through actions
Enter Select/expand action

{bold}Actions:{/bold}
A Approve selected action
B Block (reject) selected action
E Edit (hold) selected action

{bold}General:{/bold}
Q Quit War Room
R Refresh queue
H Toggle this help overlay
F Toggle Finals Mode (auto-process all)
D Toggle digest panel (morning/evening)

{bold}COLOR CODING:{/bold}
{coral-fg}● HOLD{/coral-fg} Requires manual approval
{amber-fg}● REVIEW{/amber-fg} Recommended for review
{teal-fg}● AUTO{/teal-fg} Auto-approval eligible

{bold}FINALS MODE:{/bold}
When enabled, all AUTO actions are
automatically approved without operator input.

{bold}DIGEST PANEL:{/bold}
Morning brief at 07:00, Evening wrap at 20:00.
Press D to view latest digest.

Press H to close this help.
`,
                tags: true,
            });
            this.screen.append(this.helpOverlay);
        }
        this.screen.render();
    }
    toggleDigest() {
        if (this.digestOverlay) {
            this.digestOverlay.destroy();
            this.digestOverlay = null;
        }
        else {
            let content = "";
            if (this.currentDigest && this.digestScheduler) {
                const lines = this.digestScheduler.renderBrief(this.currentDigest);
                content = lines.join("\n");
            }
            else {
                content =
                    "\n{bold}No digest available yet{/bold}\n\n{dim-fg}Morning brief at 07:00{/dim-fg}\n{dim-fg}Evening wrap at 20:00{/dim-fg}\n\nPress D to close.";
            }
            this.digestOverlay = blessed.box({
                top: "center",
                left: "center",
                width: "60%",
                height: "70%",
                label: " DIGEST ",
                border: { type: "line" },
                style: {
                    border: { fg: "cyan" },
                    label: { fg: "cyan" },
                },
                content: content,
                tags: true,
                scrollable: true,
                alwaysScroll: true,
                keys: true,
                vi: true,
            });
            this.screen.append(this.digestOverlay);
            this.hasNewDigest = false;
            this.updateBottomBar();
        }
        this.screen.render();
    }
    refresh() {
        this.pendingQueue = this.engine.getPendingMessages();
        this.renderLeftPanel();
        this.renderRightPanel();
    }
    renderLeftPanel() {
        const lines = [];
        if (this.pendingQueue.length === 0) {
            lines.push("");
            lines.push("  {bold}No pending actions{/bold}");
            lines.push("");
            lines.push("  Queue is empty. Claws are operating");
            lines.push("  autonomously within approved limits.");
        }
        else {
            for (let i = 0; i < this.pendingQueue.length; i++) {
                const msg = this.pendingQueue[i];
                const evalResult = this.engine.evaluateAction(msg);
                const isSelected = i === this.currentIndex;
                const modeColor = this.getModeColor(evalResult.mode);
                const modeIcon = this.getModeIcon(evalResult.mode);
                const selector = isSelected ? "▶" : " ";
                lines.push("");
                if (this.finalsMode && evalResult.mode === "AUTO") {
                    lines.push(`  {bold}${selector} {green-fg}✓ AUTO-PROCESSING{/green-fg}{/bold}`);
                }
                lines.push(`  {bold}${selector} ${modeIcon} {${modeColor}-fg}${evalResult.mode}{/${modeColor}-fg}{/bold} ${msg.sender_role.toUpperCase()} CLAW`);
                if (msg.message_type === "tool_proposal") {
                    const toolName = msg.payload?.tool_name ?? "unknown";
                    lines.push(` Tool: ${JSON.stringify(toolName)}`);
                    if (msg.payload?.estimated_improvement) {
                        lines.push(` Expected: +${JSON.stringify(msg.payload.estimated_improvement)}% uplift`);
                    }
                }
                else if (msg.message_type === "deliverable") {
                    lines.push(` Type: ${JSON.stringify(msg.payload?.type ?? msg.message_type)}`);
                    if (msg.payload?.amount) {
                        lines.push(` Amount: $${JSON.stringify(msg.payload.amount)}`);
                    }
                }
                else {
                    lines.push(`      Type: ${msg.message_type}`);
                }
                if (isSelected) {
                    lines.push(`      {dim-fg}[A]pprove  [B]lock  [E]dit{/dim-fg}`);
                }
                if (evalResult.trigger) {
                    lines.push(`      {amber-fg}⚠ ${evalResult.description ?? evalResult.trigger}{/amber-fg}`);
                }
            }
        }
        this.leftPanel.setContent(lines.join("\n"));
    }
    renderRightPanel() {
        const lines = [];
        lines.push("");
        lines.push(" {bold}Squad Status{/bold}");
        lines.push(` Squad: ${this.squadId}`);
        lines.push("");
        const clawRoles = ["content", "ops", "analytics", "finance", "build", "assistant"];
        for (const role of clawRoles) {
            const health = this.getClawHealth(role);
            const statusColor = health.status === "active"
                ? this.COLORS.teal
                : health.status === "error"
                    ? this.COLORS.error
                    : this.COLORS.dim;
            const statusIcon = health.status === "active" ? "●" : health.status === "error" ? "●" : "○";
            lines.push(` {${statusColor}-fg}${statusIcon}{/${statusColor}-fg} ${role.toUpperCase().padEnd(10)} ${health.tools} tools`);
        }
        lines.push("");
        lines.push(" {bold}Revenue This Week{/bold}");
        if (this.revenueData) {
            const wowColor = this.revenueData.week_over_week_pct >= 0 ? this.COLORS.teal : this.COLORS.coral;
            const wowIcon = this.revenueData.week_over_week_pct >= 0 ? "↑" : "↓";
            const revenueFormatted = this.formatCurrency(this.revenueData.week_revenue);
            lines.push(` ${revenueFormatted}`);
            lines.push(` {${wowColor}-fg}${wowIcon} ${this.revenueData.week_over_week_pct >= 0 ? "+" : ""}${this.revenueData.week_over_week_pct.toFixed(1)}% WoW{/${wowColor}-fg}`);
            lines.push("");
            lines.push(` Paid: ${this.revenueData.invoices_paid} | Pending: ${this.revenueData.invoices_pending}`);
        }
        else {
            lines.push(" {dim-fg}No revenue data yet{/dim-fg}");
        }
        lines.push("");
        lines.push(" {bold}Rate Limits{/bold}");
        const rateLimitStatus = this.engine.getRateLimitStatus();
        if (rateLimitStatus) {
            lines.push(` Tier: ${rateLimitStatus.tier}`);
            lines.push(` Auto-approvals: ${rateLimitStatus.dailyRemaining}/${rateLimitStatus.dailyLimit}`);
        }
        lines.push("");
        lines.push(" {bold}Evolution Log{/bold}");
        lines.push(" {dim-fg}Recent tool deployments...{/dim-fg}");
        this.rightPanel.setContent(lines.join("\n"));
    }
    getClawHealth(role) {
        const status = {
            name: role,
            status: "idle",
            tools: 0,
        };
        try {
            const home = process.env.HOME ?? process.env.USERPROFILE ?? "/tmp";
            const sandboxMesh = (0, node_path_1.join)("/sandbox", ".openclaw-data/milimo");
            const homeMesh = (0, node_path_1.join)(home, ".openclaw-data/milimo");
            const meshRoot = (0, node_fs_1.existsSync)(sandboxMesh) ? sandboxMesh : homeMesh;
            const registryPath = (0, node_path_1.join)(meshRoot, "tools", this.squadId, role, "registry.json");
            if ((0, node_fs_1.existsSync)(registryPath)) {
                const data = JSON.parse((0, node_fs_1.readFileSync)(registryPath, "utf-8"));
                status.tools = Object.keys(data.tools ?? {}).length;
                status.status = status.tools > 0 ? "active" : "idle";
            }
            // Also check heartbeats for live status
            const heartbeatPath = (0, node_path_1.join)(meshRoot, "mesh", "heartbeats", `${role}.json`);
            if ((0, node_fs_1.existsSync)(heartbeatPath)) {
                const hb = JSON.parse((0, node_fs_1.readFileSync)(heartbeatPath, "utf-8"));
                const lastBeat = new Date(hb.timestamp).getTime();
                const now = Date.now();
                if (now - lastBeat < 60000) {
                    status.status = "active";
                    status.lastCycle = hb.timestamp;
                }
            }
        }
        catch {
            status.status = "error";
        }
        return status;
    }
    getModeColor(mode) {
        switch (mode) {
            case "HOLD":
            case "VETO":
                return "coral";
            case "REVIEW":
                return "amber";
            case "AUTO":
            default:
                return "teal";
        }
    }
    getModeIcon(mode) {
        switch (mode) {
            case "HOLD":
                return "🔴";
            case "VETO":
                return "⛔";
            case "REVIEW":
                return "🟡";
            case "AUTO":
                return "✓";
            default:
                return "○";
        }
    }
    updateBottomBar() {
        const finalsText = this.finalsMode
            ? "{bold}{green-fg}ON{/green-fg}{/bold}"
            : "{red-fg}OFF{/red-fg}";
        const digestIndicator = this.hasNewDigest ? "{cyan-fg}●{/cyan-fg} " : "";
        this.bottomBar.setContent(`{bold}[Q]{/bold}uit {bold}[R]{/bold}efresh {bold}[H]{/bold}elp {bold}[F]{/bold}inals Mode: ${finalsText} {bold}[D]{/bold}igest ${digestIndicator}`);
    }
    navigateUp() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.refresh();
            this.screen.render();
        }
    }
    navigateDown() {
        if (this.currentIndex < this.pendingQueue.length - 1) {
            this.currentIndex++;
            this.refresh();
            this.screen.render();
        }
    }
    selectAction() {
        if (this.pendingQueue.length > 0 && this.currentIndex < this.pendingQueue.length) {
            this.selectedAction = this.pendingQueue[this.currentIndex];
            this.refresh();
            this.screen.render();
        }
    }
    approveAction() {
        if (this.pendingQueue.length > 0 && this.currentIndex < this.pendingQueue.length) {
            const msg = this.pendingQueue[this.currentIndex];
            this.engine.processDecision(msg, "APPROVED", this.operatorId);
            this.pendingQueue.splice(this.currentIndex, 1);
            if (this.currentIndex >= this.pendingQueue.length && this.currentIndex > 0) {
                this.currentIndex--;
            }
            this.refresh();
            this.screen.render();
        }
    }
    blockAction() {
        if (this.pendingQueue.length > 0 && this.currentIndex < this.pendingQueue.length) {
            const msg = this.pendingQueue[this.currentIndex];
            this.engine.processDecision(msg, "REJECTED", this.operatorId);
            this.pendingQueue.splice(this.currentIndex, 1);
            if (this.currentIndex >= this.pendingQueue.length && this.currentIndex > 0) {
                this.currentIndex--;
            }
            this.refresh();
            this.screen.render();
        }
    }
    editAction() {
        if (this.pendingQueue.length > 0 && this.currentIndex < this.pendingQueue.length) {
            const msg = this.pendingQueue[this.currentIndex];
            this.engine.processDecision(msg, "DELEGATED", this.operatorId);
            this.pendingQueue.splice(this.currentIndex, 1);
            if (this.currentIndex >= this.pendingQueue.length && this.currentIndex > 0) {
                this.currentIndex--;
            }
            this.refresh();
            this.screen.render();
        }
    }
    fetchRevenueData() {
        try {
            const home = process.env.HOME ?? process.env.USERPROFILE ?? "/tmp";
            const sandboxMesh = (0, node_path_1.join)("/sandbox", ".openclaw-data/milimo");
            const homeMesh = (0, node_path_1.join)(home, ".openclaw-data/milimo");
            const meshRoot = (0, node_fs_1.existsSync)(sandboxMesh) ? sandboxMesh : homeMesh;
            const summaryPath = (0, node_path_1.join)(meshRoot, "finance", "revenue", "weekly_summary.json");
            if ((0, node_fs_1.existsSync)(summaryPath)) {
                const data = JSON.parse((0, node_fs_1.readFileSync)(summaryPath, "utf-8"));
                const currentWeek = data.current_week || {};
                const previousWeek = data.previous_week || {};
                const weekRevenue = parseFloat(currentWeek.total_revenue) || 0.0;
                const previousRevenue = parseFloat(previousWeek.total_revenue) || 0.0;
                let weekOverWeekPct = 0.0;
                if (previousRevenue > 0) {
                    weekOverWeekPct = ((weekRevenue - previousRevenue) / previousRevenue) * 100;
                }
                this.revenueData = {
                    week_revenue: weekRevenue,
                    week_over_week_pct: Math.round(weekOverWeekPct * 100) / 100,
                    invoices_paid: parseInt(currentWeek.invoices_paid, 10) || 0,
                    invoices_pending: parseInt(data.pending_invoices, 10) || 0,
                    last_updated: data.last_updated || "",
                };
            }
            else {
                this.revenueData = null;
            }
        }
        catch {
            this.revenueData = null;
        }
    }
    formatCurrency(amount) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    }
}
exports.WarRoomTUI = WarRoomTUI;
function startWarRoom(squadId, operatorId, tier) {
    const tui = new WarRoomTUI({ squadId, operatorId, tier });
    process.on("SIGINT", () => {
        tui.stop();
        process.exit(0);
    });
    tui.start();
}
//# sourceMappingURL=warroom-tui.js.map