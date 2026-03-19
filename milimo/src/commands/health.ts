// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Health Command
 *
 * Display real-time health status of all squad claws.
 */

import { Command } from "commander";
import { spawn } from "child_process";
import { readFile, writeFile } from "fs/promises";
import { existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

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

const STATUS_COLORS: Record<string, string> = {
  healthy: "\x1b[32m",
  good: "\x1b[33m",
  fair: "\x1b[33m",
  degraded: "\x1b[31m",
  critical: "\x1b[31m",
  offline: "\x1b[90m",
};

const STATUS_ICONS: Record<string, string> = {
  healthy: "🟢",
  good: "🟡",
  fair: "🟠",
  degraded: "🔴",
  critical: "⚫",
  offline: "⚪",
};

function getStatusColor(status: string): string {
  return STATUS_COLORS[status] || "\x1b[0m";
}

function getStatusIcon(status: string): string {
  return STATUS_ICONS[status] || "⚪";
}

function formatLatency(ms: number): string {
  if (ms === Infinity) return "∞";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatThroughput(perMin: number): string {
  return `${Math.round(perMin)}/min`;
}

function formatScore(score: number): string {
  const bar = "█".repeat(Math.floor(score / 10)) + "░".repeat(10 - Math.floor(score / 10));
  return `${bar} ${score.toFixed(1)}`;
}

async function getHealthData(squadId?: string): Promise<SquadHealth | null> {
  const healthPath = join(homedir(), ".milimo", "health", "health.json");

  if (!existsSync(healthPath)) {
    return null;
  }

  try {
    const content = await readFile(healthPath, "utf-8");
    const data = JSON.parse(content) as SquadHealth;

    if (squadId && data.squad_id !== squadId) {
      return null;
    }

    return data;
  } catch {
    return null;
  }
}

async function collectHealth(blueprintDir: string, squadId: string): Promise<void> {
  const script = `
import json
from orchestrator.mesh import MeshCoordinator
from orchestrator.health_collector import HealthCollector

mesh = MeshCoordinator.from_config_file("${blueprintDir}/mesh_config.yaml", squad_id="${squadId}")
mesh.register_claw("content", "local://content")
mesh.register_claw("ops", "local://ops")
mesh.register_claw("finance", "local://finance")
mesh.register_claw("build", "local://build")

collector = HealthCollector(mesh)
collector.collect_once("content")
collector.collect_once("ops")
collector.collect_once("finance")
collector.collect_once("build")
collector._calculate_health_scores()
collector._save_health_data()

health = collector.get_squad_health()
print(json.dumps(health.to_dict()))
`;

  return new Promise((resolve, reject) => {
    const proc = spawn("python3", ["-c", script], {
      cwd: blueprintDir,
    });

    proc.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Health collection failed with code ${code}`));
      }
    });

    proc.on("error", reject);
  });
}

function printClawHealth(claw: ClawHealth): void {
  const icon = getStatusIcon(claw.status);
  const color = getStatusColor(claw.status);
  const reset = "\x1b[0m";

  console.log(`  ${icon} ${color}${claw.role.padEnd(12)}${reset} ${claw.score.toFixed(1).padStart(5)}  ${claw.status.padEnd(10)} ${claw.region || "unknown"}`);
}

function printDetailedHealth(health: SquadHealth): void {
  console.log("\n" + "─".repeat(60));
  console.log(`  Squad Health Overview`);
  console.log("─".repeat(60));
  console.log(`  Overall: ${health.overall_score.toFixed(1)} (${health.overall_status})`);
  console.log(`  Squad: ${health.squad_id}`);
  console.log(`  Updated: ${health.last_updated}`);
  console.log("─".repeat(60));
  console.log("  Claw          Score  Status      Region");
  console.log("─".repeat(60));

  for (const claw of health.claws) {
    printClawHealth(claw);
  }

  if (health.alerts.length > 0) {
    console.log("\n" + "─".repeat(60));
    console.log("  Alerts:");
    console.log("─".repeat(60));

    for (const alert of health.alerts) {
      const color = alert.level === "critical" ? "\x1b[31m" : "\x1b[33m";
      console.log(`  ${color}[${alert.level.toUpperCase()}]${reset} ${alert.role}: ${alert.message}`);
    }
  }

  console.log("");
}

function printCompactHealth(health: SquadHealth): void {
  const icon = getStatusIcon(health.overall_status);
  const color = getStatusColor(health.overall_status);
  const reset = "\x1b[0m";

  console.log(`${icon} ${color}${health.overall_status.toUpperCase()}${reset} Squad: ${health.overall_score.toFixed(1)} | Claws: ${health.claws.length}`);

  for (const claw of health.claws) {
    const clawIcon = getStatusIcon(claw.status);
    console.log(`  ${clawIcon} ${claw.role}: ${claw.score.toFixed(1)}`);
  }
}

function printWatch(health: SquadHealth): void {
  console.log("\x1b[2J\x1b[H");
  console.log(`Milimo Claw Health Dashboard - ${new Date().toLocaleTimeString()}`);
  printDetailedHealth(health);
}

export const healthCommand = new Command("health")
  .description("Display health status of squad claws")
  .option("-s, --squad <squad>", "Squad ID to check")
  .option("-d, --detailed", "Show detailed health metrics")
  .option("-c, --collect", "Collect fresh health data before display")
  .option("-w, --watch", "Watch mode - continuously update display")
  .option("-i, --interval <ms>", "Watch interval in milliseconds", "5000")
  .option("-j, --json", "Output as JSON")
  .action(async (options) => {
    const squadId = options.squad || process.env.MILIMO_SQUAD || "default";
    const blueprintDir = process.env.MILIMO_BLUEPRINT_DIR || join(homedir(), ".milimo", "blueprints", squadId);

    if (options.collect) {
      try {
        await collectHealth(blueprintDir, squadId);
      } catch (error) {
        console.error("Failed to collect health data:", error);
      }
    }

    if (options.watch) {
      const interval = parseInt(options.interval, 10);

      const updateLoop = async () => {
        try {
          await collectHealth(blueprintDir, squadId);
          const health = await getHealthData(squadId);
          if (health) {
            printWatch(health);
          }
        } catch (error) {
          console.error("Update failed:", error);
        }

        setTimeout(updateLoop, interval);
      };

      updateLoop();
    } else {
      const health = await getHealthData(squadId);

      if (!health) {
        console.log("No health data available. Run with --collect to gather data.");
        return;
      }

      if (options.json) {
        console.log(JSON.stringify(health, null, 2));
      } else if (options.detailed) {
        printDetailedHealth(health);
      } else {
        printCompactHealth(health);
      }
    }
  });

export default healthCommand;
