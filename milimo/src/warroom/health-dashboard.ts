// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Health Dashboard for War Room
 *
 * Real-time health visualization for all squad claws.
 */

import { readFile } from "fs/promises";
import { existsSync } from "fs";
import { join, homedir } from "os";
import { EventEmitter } from "events";

interface HealthMetrics {
  claw_role: string;
  heartbeat_latency_ms: number;
  message_throughput_per_min: number;
  evolution_status: string;
  approval_backlog: number;
  error_rate_per_hour: number;
  last_updated: string;
}

interface ClawHealth {
  role: string;
  status: string;
  score: number;
  metrics: HealthMetrics;
  region: string;
  squad_id: string;
  last_heartbeat: string;
}

interface SquadHealth {
  squad_id: string;
  overall_score: number;
  overall_status: string;
  claws: ClawHealth[];
  alerts: Array<{
    role: string;
    level: string;
    message: string;
    timestamp: string;
  }>;
  last_updated: string;
}

type HealthEventHandler = (health: SquadHealth) => void;
type AlertEventHandler = (alert: SquadHealth["alerts"][0]) => void;

const STATUS_ICONS: Record<string, string> = {
  healthy: "🟢",
  good: "🟡",
  fair: "🟠",
  degraded: "🔴",
  critical: "⚫",
  offline: "⚪",
};

const STATUS_COLORS: Record<string, string> = {
  healthy: "#22c55e",
  good: "#eab308",
  fair: "#f97316",
  degraded: "#ef4444",
  critical: "#1f2937",
  offline: "#9ca3af",
};

class HealthDashboard extends EventEmitter {
  private squadId: string;
  private blueprintDir: string;
  private healthPath: string;
  private updateInterval: NodeJS.Timeout | null = null;
  private lastHealth: SquadHealth | null = null;
  private cachedData: Map<string, ClawHealth> = new Map();

  constructor(squadId: string = "default") {
    super();
    this.squadId = squadId;
    this.blueprintDir = process.env.MILIMO_BLUEPRINT_DIR || join(homedir(), ".milimo", "blueprints", squadId);
    this.healthPath = join(homedir(), ".milimo", "health", "health.json");
  }

  start(intervalMs: number = 5000): void {
    if (this.updateInterval) {
      return;
    }

    this.updateInterval = setInterval(() => {
      this.update();
    }, intervalMs);

    this.update();
  }

  stop(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  private async update(): Promise<void> {
    const health = await this.loadHealthData();

    if (!health) {
      return;
    }

    const previousHealth = this.lastHealth;
    this.lastHealth = health;

    this.emit("update", health);

    if (previousHealth) {
      for (const alert of health.alerts) {
        const isNew = !previousHealth.alerts.some(
          (a) => a.role === alert.role && a.level === alert.level
        );

        if (isNew) {
          this.emit("alert", alert);
        }
      }
    }
  }

  private async loadHealthData(): Promise<SquadHealth | null> {
    if (!existsSync(this.healthPath)) {
      return null;
    }

    try {
      const content = await readFile(this.healthPath, "utf-8");
      return JSON.parse(content) as SquadHealth;
    } catch {
      return null;
    }
  }

  getHealth(): SquadHealth | null {
    return this.lastHealth;
  }

  getClawHealth(role: string): ClawHealth | null {
    if (!this.lastHealth) {
      return null;
    }

    return this.lastHealth.claws.find((c) => c.role === role) || null;
  }

  getAlerts(): SquadHealth["alerts"] {
    return this.lastHealth?.alerts || [];
  }

  renderCompact(): string {
    if (!this.lastHealth) {
      return "No health data available";
    }

    const icon = STATUS_ICONS[this.lastHealth.overall_status] || "⚪";
    const lines: string[] = [];

    lines.push(`${icon} Squad Health: ${this.lastHealth.overall_score.toFixed(1)} (${this.lastHealth.overall_status})`);
    lines.push(`Squad: ${this.lastHealth.squad_id}`);
    lines.push("");

    for (const claw of this.lastHealth.claws) {
      const clawIcon = STATUS_ICONS[claw.status] || "⚪";
      lines.push(`${clawIcon} ${claw.role.padEnd(12)} ${claw.score.toFixed(1).padStart(5)}  ${claw.status}`);
    }

    if (this.lastHealth.alerts.length > 0) {
      lines.push("");
      lines.push("Alerts:");
      for (const alert of this.lastHealth.alerts) {
        lines.push(`  [${alert.level.toUpperCase()}] ${alert.role}: ${alert.message}`);
      }
    }

    return lines.join("\n");
  }

  renderDetailed(): string {
    if (!this.lastHealth) {
      return "No health data available";
    }

    const lines: string[] = [];
    const divider = "─".repeat(60);

    lines.push(divider);
    lines.push("Squad Health Dashboard");
    lines.push(divider);
    lines.push(`Overall Score: ${this.lastHealth.overall_score.toFixed(1)}`);
    lines.push(`Status: ${this.lastHealth.overall_status.toUpperCase()}`);
    lines.push(`Squad ID: ${this.lastHealth.squad_id}`);
    lines.push(`Last Updated: ${this.lastHealth.last_updated}`);
    lines.push(divider);
    lines.push("");

    for (const claw of this.lastHealth.claws) {
      const icon = STATUS_ICONS[claw.status] || "⚪";
      const bar = this.renderScoreBar(claw.score);

      lines.push(`${icon} ${claw.role.toUpperCase()} (${claw.region || "unknown"})`);
      lines.push(`   Score: ${bar} ${claw.score.toFixed(1)}`);
      lines.push(`   Status: ${claw.status}`);
      lines.push(`   Heartbeat: ${this.formatLatency(claw.metrics.heartbeat_latency_ms)}`);
      lines.push(`   Throughput: ${claw.metrics.message_throughput_per_min.toFixed(1)}/min`);
      lines.push(`   Backlog: ${claw.metrics.approval_backlog} pending`);
      lines.push(`   Errors: ${claw.metrics.error_rate_per_hour.toFixed(1)}/hour`);
      lines.push("");
    }

    if (this.lastHealth.alerts.length > 0) {
      lines.push(divider);
      lines.push("ALERTS");
      lines.push(divider);

      for (const alert of this.lastHealth.alerts) {
        lines.push(`[${alert.level.toUpperCase()}] ${alert.role}: ${alert.message}`);
        lines.push(`  Timestamp: ${alert.timestamp}`);
        lines.push("");
      }
    }

    return lines.join("\n");
  }

  renderScoreBar(score: number): string {
    const filled = Math.floor(score / 10);
    const empty = 10 - filled;
    return "█".repeat(filled) + "░".repeat(empty);
  }

  formatLatency(ms: number): string {
    if (ms === Infinity) return "∞ (offline)";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  getStatusColor(status: string): string {
    return STATUS_COLORS[status] || "#9ca3af";
  }

  getStatusIcon(status: string): string {
    return STATUS_ICONS[status] || "⚪";
  }

  toJSON(): string {
    return JSON.stringify(this.lastHealth, null, 2);
  }
}

function createHealthWidget(health: SquadHealth): string {
  const lines: string[] = [];

  lines.push("┌─────────────────────────────────────────┐");
  lines.push(`│  Squad Health          ${STATUS_ICONS[health.overall_status]} ${health.overall_status.toUpperCase().padEnd(10)}│`);
  lines.push(`│  Score: ${health.overall_score.toFixed(1).padEnd(33)}│`);
  lines.push("├─────────────────────────────────────────┤");

  for (const claw of health.claws) {
    const icon = STATUS_ICONS[claw.status];
    const score = claw.score.toFixed(1).padStart(5);
    const status = claw.status.padEnd(10);
    const region = (claw.region || "unknown").padEnd(12);

    lines.push(`│  ${icon} ${(claw.role + ":").padEnd(10)} ${score}  ${status} ${region}│`);
  }

  lines.push("└─────────────────────────────────────────┘");

  return lines.join("\n");
}

function renderMetricGauge(value: number, max: number, label: string): string {
  const percentage = Math.min((value / max) * 100, 100);
  const filled = Math.floor(percentage / 5);
  const empty = 20 - filled;

  return `${label.padEnd(15)} [${"=".repeat(filled)}${" ".repeat(empty)}] ${value.toFixed(1)}/${max}`;
}

export {
  HealthDashboard,
  createHealthWidget,
  renderMetricGauge,
  STATUS_ICONS,
  STATUS_COLORS,
};

export type { SquadHealth, ClawHealth, HealthMetrics };
