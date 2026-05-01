"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.STATUS_COLORS = exports.STATUS_ICONS = exports.HealthDashboard = void 0;
exports.createHealthWidget = createHealthWidget;
exports.renderMetricGauge = renderMetricGauge;
/**
 * Health Dashboard for War Room
 *
 * Real-time health visualization for all squad claws.
 */
const promises_1 = require("fs/promises");
const fs_1 = require("fs");
const os_1 = require("os");
const path_1 = require("path");
const events_1 = require("events");
const STATUS_ICONS = {
    healthy: "🟢",
    good: "🟡",
    fair: "🟠",
    degraded: "🔴",
    critical: "⚫",
    offline: "⚪",
};
exports.STATUS_ICONS = STATUS_ICONS;
const STATUS_COLORS = {
    healthy: "#22c55e",
    good: "#eab308",
    fair: "#f97316",
    degraded: "#ef4444",
    critical: "#1f2937",
    offline: "#9ca3af",
};
exports.STATUS_COLORS = STATUS_COLORS;
class HealthDashboard extends events_1.EventEmitter {
    squadId;
    blueprintDir;
    healthPath;
    updateInterval = null;
    lastHealth = null;
    cachedData = new Map();
    constructor(squadId = "default") {
        super();
        this.squadId = squadId;
        this.blueprintDir =
            process.env.MILIMO_BLUEPRINT_DIR ||
                (0, path_1.join)((0, os_1.homedir)(), ".openclaw/milimo", "blueprints", squadId);
        this.healthPath = (0, path_1.join)((0, os_1.homedir)(), ".openclaw/milimo", "health", "health.json");
    }
    start(intervalMs = 5000) {
        if (this.updateInterval) {
            return;
        }
        this.updateInterval = setInterval(() => {
            void this.update();
        }, intervalMs);
        void this.update();
    }
    stop() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    async update() {
        const health = await this.loadHealthData();
        if (!health) {
            return;
        }
        const previousHealth = this.lastHealth;
        this.lastHealth = health;
        this.emit("update", health);
        if (previousHealth) {
            for (const alert of health.alerts) {
                const isNew = !previousHealth.alerts.some((a) => a.role === alert.role && a.level === alert.level);
                if (isNew) {
                    this.emit("alert", alert);
                }
            }
        }
    }
    async loadHealthData() {
        if (!(0, fs_1.existsSync)(this.healthPath)) {
            return null;
        }
        try {
            const content = await (0, promises_1.readFile)(this.healthPath, "utf-8");
            return JSON.parse(content);
        }
        catch {
            return null;
        }
    }
    getHealth() {
        return this.lastHealth;
    }
    getClawHealth(role) {
        if (!this.lastHealth) {
            return null;
        }
        return this.lastHealth.claws.find((c) => c.role === role) || null;
    }
    getAlerts() {
        return this.lastHealth?.alerts || [];
    }
    renderCompact() {
        if (!this.lastHealth) {
            return "No health data available";
        }
        const icon = STATUS_ICONS[this.lastHealth.overall_status] || "⚪";
        const lines = [];
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
    renderDetailed() {
        if (!this.lastHealth) {
            return "No health data available";
        }
        const lines = [];
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
    renderScoreBar(score) {
        const filled = Math.floor(score / 10);
        const empty = 10 - filled;
        return "█".repeat(filled) + "░".repeat(empty);
    }
    formatLatency(ms) {
        if (ms === Infinity)
            return "∞ (offline)";
        if (ms < 1000)
            return `${Math.round(ms)}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    }
    getStatusColor(status) {
        return STATUS_COLORS[status] || "#9ca3af";
    }
    getStatusIcon(status) {
        return STATUS_ICONS[status] || "⚪";
    }
    toJSON() {
        return JSON.stringify(this.lastHealth, null, 2);
    }
}
exports.HealthDashboard = HealthDashboard;
function createHealthWidget(health) {
    const lines = [];
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
function renderMetricGauge(value, max, label) {
    const percentage = Math.min((value / max) * 100, 100);
    const filled = Math.floor(percentage / 5);
    const empty = 20 - filled;
    return `${label.padEnd(15)} [${"=".repeat(filled)}${" ".repeat(empty)}] ${value.toFixed(1)}/${max}`;
}
//# sourceMappingURL=health-dashboard.js.map