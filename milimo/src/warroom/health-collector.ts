// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Health Collector
 *
 * Collects real-time health data from all squad claws.
 * Polls at 3000ms interval for TUI updates.
 */

import { spawnSync } from "node:child_process";
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

  public collectAll(): ClawHealthMap {
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

  public startPolling(onUpdate: HealthUpdateHandler, onError?: HealthErrorHandler): () => void {
    if (this.running) {
      return () => this.stopPolling();
    }

    this.running = true;

    try {
      onUpdate(this.collectAll());
    } catch (error: unknown) {
      if (onError) {
        onError(error as Error);
      }
    }

    this.intervalId = setInterval(() => {
      try {
        onUpdate(this.collectAll());
      } catch (error: unknown) {
        if (onError) {
          onError(error as Error);
        }
      }
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

  /**
   * Collect NemoClaw sandbox diagnostics by wrapping `nemoclaw doctor`.
   *
   * This augments Milimo's claw-level health with NemoClaw's native
   * sandbox-level diagnostics (gateway connectivity, proxy status,
   * credential availability, etc.).
   *
   * Returns a structured summary or null if nemoclaw CLI is unavailable.
   */
  public collectNemoClawDiagnostics(): NemoClawDiagnostics | null {
    try {
      const result = spawnSync("nemoclaw", ["doctor"], {
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
      const lines = (result.stdout || "").split("\n").filter((l: string) => l.trim());
      const checks: DiagnosticCheck[] = [];

      for (const line of lines) {
        if (line.includes("✓") || line.includes("✅")) {
          checks.push({ name: line.replace(/[✓✅]/g, "").trim(), status: "pass" });
        } else if (line.includes("✗") || line.includes("❌")) {
          checks.push({ name: line.replace(/[✗❌]/g, "").trim(), status: "fail" });
        } else if (line.includes("⚠")) {
          checks.push({ name: line.replace(/[⚠️]/g, "").trim(), status: "warn" });
        }
      }

      const failCount = checks.filter((c) => c.status === "fail").length;
      const warnCount = checks.filter((c) => c.status === "warn").length;

      return {
        available: true,
        checks,
        summary:
          failCount > 0
            ? `${failCount} check(s) failed`
            : warnCount > 0
              ? `${warnCount} warning(s)`
              : "All checks passed",
        collectedAt: new Date().toISOString(),
      };
    } catch {
      return null;
    }
  }
}

/** NemoClaw sandbox diagnostics from `nemoclaw doctor`. */
export interface NemoClawDiagnostics {
  available: boolean;
  checks: DiagnosticCheck[];
  summary: string;
  collectedAt: string;
}

export interface DiagnosticCheck {
  name: string;
  status: "pass" | "fail" | "warn";
}
