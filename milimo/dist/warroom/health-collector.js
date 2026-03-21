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
    async collectAll() {
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
        this.collectAll()
            .then(onUpdate)
            .catch((error) => {
            if (onError) {
                onError(error);
            }
        });
        this.intervalId = setInterval(() => {
            this.collectAll()
                .then(onUpdate)
                .catch((error) => {
                if (onError) {
                    onError(error);
                }
            });
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
}
exports.HealthCollector = HealthCollector;
//# sourceMappingURL=health-collector.js.map