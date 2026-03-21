// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Health Collector
 *
 * Collects real-time health data from all squad claws.
 * Polls at 3000ms interval for TUI updates.
 */

import { callPythonBridgeSafe, type BridgeCommandOptions } from "../lib/python-bridge";

export interface ClawHealth {
    role: string;
    status: "active" | "idle" | "processing" | "error";
    tool_count: number;
    last_evolution: string | null;
    last_action: string | null;
    actions_this_week: number;
    sparkline: number[];
}

export type ClawHealthMap = Record<string, ClawHealth>;

export interface HealthCollectorOptions {
    squadId: string;
    blueprintDir: string;
    pollInterval?: number;
}

export type HealthUpdateHandler = (health: ClawHealthMap) => void;
export type HealthErrorHandler = (error: Error) => void;

export class HealthCollector {
    private squadId: string;
    private bridgeOptions: BridgeCommandOptions;
    private pollInterval: number;
    private intervalId: NodeJS.Timeout | null = null;
    private running: boolean = false;

    constructor(options: HealthCollectorOptions) {
        this.squadId = options.squadId;
        this.bridgeOptions = { blueprintDir: options.blueprintDir };
        this.pollInterval = options.pollInterval ?? 3000;
    }

    public async collectAll(): Promise<ClawHealthMap> {
        const response = callPythonBridgeSafe<ClawHealthMap>(
            "collect_health",
            { squad_id: this.squadId },
            this.bridgeOptions,
        );

        if (!response.success || !response.data) {
            throw new Error(response.error ?? "Health collection failed");
        }

        return response.data;
    }

    public startPolling(
        onUpdate: HealthUpdateHandler,
        onError?: HealthErrorHandler,
    ): () => void {
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

    public stopPolling(): void {
        this.running = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    public deriveStatus(health: ClawHealth): "active" | "idle" | "processing" | "error" {
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
            } catch {
                // Invalid date, fall through
            }
        }

        return "idle";
    }

    public isRunning(): boolean {
        return this.running;
    }
}
