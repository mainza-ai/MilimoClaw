// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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

import * as blessed from "blessed";
import { ApprovalEngine, ApprovalMode, PendingMessage } from "./approval.js";
import { AuditLogger } from "./audit.js";
import { EvolutionManager } from "./evolution.js";
import { DigestScheduler, type DigestBrief } from "./digest.js";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

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

export class WarRoomTUI {
  private screen: blessed.Widgets.Screen;
  private leftPanel: blessed.Widgets.BoxElement;
  private rightPanel: blessed.Widgets.BoxElement;
  private bottomBar: blessed.Widgets.BoxElement;
  private helpOverlay: blessed.Widgets.BoxElement | null = null;
  private digestOverlay: blessed.Widgets.BoxElement | null = null;

  private engine: ApprovalEngine;
  private audit: AuditLogger;
  private evolution: EvolutionManager;
  private digestScheduler: DigestScheduler | null = null;

  private pendingQueue: PendingMessage[] = [];
  private selectedAction: PendingMessage | null = null;
  private currentIndex: number = 0;
  private finalsMode: boolean = false;
  private revenueData: RevenueSummary | null = null;
  private revenuePollInterval: NodeJS.Timeout | null = null;
  private currentDigest: DigestBrief | null = null;
  private hasNewDigest: boolean = false;

  private squadId: string;
  private operatorId: string;
  private blueprintDir: string;
  private refreshInterval: NodeJS.Timeout | null = null;
  private isRunning: boolean = false;

  private readonly COLORS = {
    coral: "#FF6B6B",
    amber: "#FFB347",
    teal: "#20B2AA",
    success: "#50C878",
    error: "#FF4444",
    header: "#87CEEB",
    text: "#FFFFFF",
    dim: "#888888",
  };

  private readonly POLL_INTERVAL = 3000;
  private readonly REVENUE_POLL_INTERVAL = 30000;

  constructor(options: WarRoomTUIOptions) {
    this.squadId = options.squadId;
    this.operatorId = options.operatorId ?? "local-operator";
    this.blueprintDir = options.blueprintDir ?? process.cwd();

    this.engine = new ApprovalEngine(this.squadId, options.tier ?? "free");
    this.audit = new AuditLogger(this.squadId);
    this.evolution = new EvolutionManager(this.squadId);

    if (options.digestConfig) {
      this.digestScheduler = new DigestScheduler({
        config: {
          ...options.digestConfig,
          squad_id: this.squadId,
        },
        blueprintDir: this.blueprintDir,
        onUpdate: (brief: DigestBrief) => {
          this.currentDigest = brief;
          this.hasNewDigest = true;
          this.updateBottomBar();
          this.screen.render();
        },
        onError: (error: Error) => {
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
      content:
        "{bold}[Q]{/bold}uit  {bold}[R]{/bold}efresh  {bold}[H]{/bold}elp  {bold}[F]{/bold}inals Mode: OFF",
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

  public start(): void {
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

  public stop(): void {
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

  private setupKeyBindings(): void {
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

  private toggleHelp(): void {
    if (this.helpOverlay) {
      this.helpOverlay.destroy();
      this.helpOverlay = null;
    } else {
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

  private toggleDigest(): void {
    if (this.digestOverlay) {
      this.digestOverlay.destroy();
      this.digestOverlay = null;
    } else {
      let content = "";
      if (this.currentDigest && this.digestScheduler) {
        const lines = this.digestScheduler.renderBrief(this.currentDigest);
        content = lines.join("\n");
      } else {
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

  private refresh(): void {
    this.pendingQueue = this.engine.getPendingMessages();
    this.renderLeftPanel();
    this.renderRightPanel();
  }

  private renderLeftPanel(): void {
    const lines: string[] = [];

    if (this.pendingQueue.length === 0) {
      lines.push("");
      lines.push("  {bold}No pending actions{/bold}");
      lines.push("");
      lines.push("  Queue is empty. Claws are operating");
      lines.push("  autonomously within approved limits.");
    } else {
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

        lines.push(
          `  {bold}${selector} ${modeIcon} {${modeColor}-fg}${evalResult.mode}{/${modeColor}-fg}{/bold} ${msg.sender_role.toUpperCase()} CLAW`,
        );

        if (msg.message_type === "tool_proposal") {
          const toolName = msg.payload?.tool_name ?? "unknown";
          lines.push(` Tool: ${JSON.stringify(toolName)}`);
          if (msg.payload?.estimated_improvement) {
            lines.push(` Expected: +${JSON.stringify(msg.payload.estimated_improvement)}% uplift`);
          }
        } else if (msg.message_type === "deliverable") {
          lines.push(` Type: ${JSON.stringify(msg.payload?.type ?? msg.message_type)}`);
          if (msg.payload?.amount) {
            lines.push(` Amount: $${JSON.stringify(msg.payload.amount)}`);
          }
        } else {
          lines.push(`      Type: ${msg.message_type}`);
        }

        if (isSelected) {
          lines.push(`      {dim-fg}[A]pprove  [B]lock  [E]dit{/dim-fg}`);
        }

        if (evalResult.trigger) {
          lines.push(
            `      {amber-fg}⚠ ${evalResult.description ?? evalResult.trigger}{/amber-fg}`,
          );
        }
      }
    }

    this.leftPanel.setContent(lines.join("\n"));
  }

  private renderRightPanel(): void {
    const lines: string[] = [];

    lines.push("");
    lines.push(" {bold}Squad Status{/bold}");
    lines.push(` Squad: ${this.squadId}`);
    lines.push("");

    const clawRoles = ["content", "ops", "analytics", "finance", "build", "assistant"];

    for (const role of clawRoles) {
      const health = this.getClawHealth(role);
      const statusColor =
        health.status === "active"
          ? this.COLORS.teal
          : health.status === "error"
            ? this.COLORS.error
            : this.COLORS.dim;
      const statusIcon = health.status === "active" ? "●" : health.status === "error" ? "●" : "○";

      lines.push(
        ` {${statusColor}-fg}${statusIcon}{/${statusColor}-fg} ${role.toUpperCase().padEnd(10)} ${health.tools} tools`,
      );
    }

    lines.push("");
    lines.push(" {bold}Revenue This Week{/bold}");

    if (this.revenueData) {
      const wowColor =
        this.revenueData.week_over_week_pct >= 0 ? this.COLORS.teal : this.COLORS.coral;
      const wowIcon = this.revenueData.week_over_week_pct >= 0 ? "↑" : "↓";
      const revenueFormatted = this.formatCurrency(this.revenueData.week_revenue);

      lines.push(` ${revenueFormatted}`);
      lines.push(
        ` {${wowColor}-fg}${wowIcon} ${this.revenueData.week_over_week_pct >= 0 ? "+" : ""}${this.revenueData.week_over_week_pct.toFixed(1)}% WoW{/${wowColor}-fg}`,
      );
      lines.push("");
      lines.push(
        ` Paid: ${this.revenueData.invoices_paid} | Pending: ${this.revenueData.invoices_pending}`,
      );
    } else {
      lines.push(" {dim-fg}No revenue data yet{/dim-fg}");
    }

    lines.push("");
    lines.push(" {bold}Rate Limits{/bold}");

    const rateLimitStatus = this.engine.getRateLimitStatus();
    if (rateLimitStatus) {
      lines.push(` Tier: ${rateLimitStatus.tier}`);
      lines.push(
        ` Auto-approvals: ${rateLimitStatus.dailyRemaining}/${rateLimitStatus.dailyLimit}`,
      );
    }

    lines.push("");
    lines.push(" {bold}Evolution Log{/bold}");
    lines.push(" {dim-fg}Recent tool deployments...{/dim-fg}");

    this.rightPanel.setContent(lines.join("\n"));
  }
  private getClawHealth(role: string): ClawHealth {
    const status: ClawHealth = {
      name: role,
      status: "idle",
      tools: 0,
    };

    try {
      const home = process.env.HOME ?? process.env.USERPROFILE ?? "/tmp";
      const sandboxMesh = join("/sandbox", ".openclaw/milimo");
      const homeMesh = join(home, ".openclaw/milimo");
      const meshRoot = existsSync(sandboxMesh) ? sandboxMesh : homeMesh;
      const registryPath = join(meshRoot, "tools", this.squadId, role, "registry.json");
      if (existsSync(registryPath)) {
        const data = JSON.parse(readFileSync(registryPath, "utf-8"));
        status.tools = Object.keys(data.tools ?? {}).length;
        status.status = status.tools > 0 ? "active" : "idle";
      }

      // Also check heartbeats for live status
      const heartbeatPath = join(meshRoot, "mesh", "heartbeats", `${role}.json`);
      if (existsSync(heartbeatPath)) {
        const hb = JSON.parse(readFileSync(heartbeatPath, "utf-8"));
        const lastBeat = new Date(hb.timestamp).getTime();
        const now = Date.now();
        if (now - lastBeat < 60000) {
          status.status = "active";
          status.lastCycle = hb.timestamp;
        }
      }
    } catch {
      status.status = "error";
    }

    return status;
  }

  private getModeColor(mode: ApprovalMode): string {
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

  private getModeIcon(mode: ApprovalMode): string {
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

  private updateBottomBar(): void {
    const finalsText = this.finalsMode
      ? "{bold}{green-fg}ON{/green-fg}{/bold}"
      : "{red-fg}OFF{/red-fg}";
    const digestIndicator = this.hasNewDigest ? "{cyan-fg}●{/cyan-fg} " : "";
    this.bottomBar.setContent(
      `{bold}[Q]{/bold}uit {bold}[R]{/bold}efresh {bold}[H]{/bold}elp {bold}[F]{/bold}inals Mode: ${finalsText} {bold}[D]{/bold}igest ${digestIndicator}`,
    );
  }

  private navigateUp(): void {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.refresh();
      this.screen.render();
    }
  }

  private navigateDown(): void {
    if (this.currentIndex < this.pendingQueue.length - 1) {
      this.currentIndex++;
      this.refresh();
      this.screen.render();
    }
  }

  private selectAction(): void {
    if (this.pendingQueue.length > 0 && this.currentIndex < this.pendingQueue.length) {
      this.selectedAction = this.pendingQueue[this.currentIndex];
      this.refresh();
      this.screen.render();
    }
  }

  private approveAction(): void {
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

  private blockAction(): void {
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

  private editAction(): void {
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

  private fetchRevenueData(): void {
    try {
      const home = process.env.HOME ?? process.env.USERPROFILE ?? "/tmp";
      const sandboxMesh = join("/sandbox", ".openclaw/milimo");
      const homeMesh = join(home, ".openclaw/milimo");
      const meshRoot = existsSync(sandboxMesh) ? sandboxMesh : homeMesh;
      const summaryPath = join(meshRoot, "finance", "revenue", "weekly_summary.json");

      if (existsSync(summaryPath)) {
        const data = JSON.parse(readFileSync(summaryPath, "utf-8"));
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
      } else {
        this.revenueData = null;
      }
    } catch {
      this.revenueData = null;
    }
  }

  private formatCurrency(amount: number): string {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }
}

export function startWarRoom(squadId: string, operatorId?: string, tier?: "free" | "pro"): void {
  const tui = new WarRoomTUI({ squadId, operatorId, tier });

  process.on("SIGINT", () => {
    tui.stop();
    process.exit(0);
  });

  tui.start();
}
