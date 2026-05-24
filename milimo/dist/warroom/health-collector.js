"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.HealthCollector = void 0;
/**
 * Health Collector
 *
 * Collects real-time health data from all squad claws.
 * Polls at 3000ms interval for TUI updates.
 */
const node_child_process_1 = require("node:child_process");
const python_bridge_1 = require("../lib/python-bridge");
class HealthCollector {
    squadId;
    bridgeOptions;
    pollInterval;
    intervalId = null;
    running = false;
    constructor(options) {
        this.squadId = options.squadId;
        this.bridgeOptions = { blueprintDir: options.blueprintDir };
        this.pollInterval = options.pollInterval ?? 3000;
    }
    collectAll() {
        const response = (0, python_bridge_1.callPythonBridgeSafe)("collect_health", { squad_id: this.squadId }, this.bridgeOptions);
        if (!response.success || !response.data) {
            throw new Error(response.error ?? "Health collection failed");
        }
        return response.data;
    }
    startPolling(onUpdate, onError) {
        if (this.running) {
            return () => this.stopPolling();
        }
        this.running = true;
        try {
            onUpdate(this.collectAll());
        }
        catch (error) {
            if (onError) {
                onError(error);
            }
        }
        this.intervalId = setInterval(() => {
            try {
                onUpdate(this.collectAll());
            }
            catch (error) {
                if (onError) {
                    onError(error);
                }
            }
        }, this.pollInterval);
        return () => this.stopPolling();
    }
    stopPolling() {
        this.running = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    deriveStatus(health) {
        if (health.status === "error") {
            return "error";
        }
        if (health.status === "processing") {
            return "processing";
        }
        if (health.last_action) {
            try {
                const lastAction = new Date(health.last_action);
                const now = new Date();
                const diffMs = now.getTime() - lastAction.getTime();
                const diffSec = diffMs / 1000;
                if (diffSec < 60) {
                    return "active";
                }
            }
            catch {
                // Invalid date, fall through
            }
        }
        return "idle";
    }
    isRunning() {
        return this.running;
    }
    /**
     * Collect NemoClaw sandbox diagnostics by wrapping `nemoclaw doctor`.
     *
     * This augments Milimo's claw-level health with NemoClaw's native
     * sandbox-level diagnostics (gateway connectivity, proxy status,
     * credential availability, etc.).
     *
     * Returns a structured summary or null if nemoclaw CLI is unavailable.
     */
    collectNemoClawDiagnostics() {
        try {
            const result = (0, node_child_process_1.spawnSync)("nemoclaw", ["doctor"], {
                encoding: "utf-8",
                timeout: 10000,
                stdio: ["pipe", "pipe", "pipe"],
            });
            if (result.error || result.status !== 0) {
                return {
                    available: false,
                    checks: [],
                    summary: "nemoclaw doctor not available",
                    collectedAt: new Date().toISOString(),
                };
            }
            // Parse the doctor output into structured checks
            const lines = (result.stdout || "").split("\n").filter((l) => l.trim());
            const checks = [];
            for (const line of lines) {
                if (line.includes("✓") || line.includes("✅")) {
                    checks.push({ name: line.replace(/[✓✅]/g, "").trim(), status: "pass" });
                }
                else if (line.includes("✗") || line.includes("❌")) {
                    checks.push({ name: line.replace(/[✗❌]/g, "").trim(), status: "fail" });
                }
                else if (line.includes("⚠")) {
                    checks.push({ name: line.replace(/[⚠️]/g, "").trim(), status: "warn" });
                }
            }
            const failCount = checks.filter((c) => c.status === "fail").length;
            const warnCount = checks.filter((c) => c.status === "warn").length;
            return {
                available: true,
                checks,
                summary: failCount > 0
                    ? `${failCount} check(s) failed`
                    : warnCount > 0
                        ? `${warnCount} warning(s)`
                        : "All checks passed",
                collectedAt: new Date().toISOString(),
            };
        }
        catch {
            return null;
        }
    }
}
exports.HealthCollector = HealthCollector;
//# sourceMappingURL=health-collector.js.map