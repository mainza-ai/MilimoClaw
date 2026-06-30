"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.healthCommand = healthCommand;
const node_os_1 = require("node:os");
const node_path_1 = require("node:path");
const node_fs_1 = require("node:fs");
const promises_1 = require("node:fs/promises");
const rpc_bridge_1 = require("../lib/rpc-bridge");
const STATUS_COLORS = {
    healthy: "\x1b[32m",
    good: "\x1b[33m",
    fair: "\x1b[33m",
    degraded: "\x1b[31m",
    critical: "\x1b[31m",
    offline: "\x1b[90m",
};
const STATUS_ICONS = {
    healthy: "\u{1F7E2}",
    good: "\u{1F7E1}",
    fair: "\u{1F7E0}",
    degraded: "\u{1F534}",
    critical: "\u{26AB}",
    offline: "\u{26AA}",
};
function getStatusColor(status) {
    return STATUS_COLORS[status] || "\x1b[0m";
}
function getStatusIcon(status) {
    return STATUS_ICONS[status] || "\u{26AA}";
}
// function formatLatency(ms: number): string {
//   if (ms === Infinity) return "\u221E";
//   if (ms < 1000) return `${Math.round(ms)}ms`;
//   return `${(ms / 1000).toFixed(1)}s`;
// }
// function formatThroughput(perMin: number): string {
//   return `${Math.round(perMin)}/min`;
// }
// function formatScore(score: number): string {
//   const bar =
//     "\u2588".repeat(Math.floor(score / 10)) + "\u2591".repeat(10 - Math.floor(score / 10));
//   return `${bar} ${score.toFixed(1)}`;
// }
async function getHealthData(squadId) {
    const healthPath = (0, node_path_1.join)((0, node_os_1.homedir)(), ".milimo", "health", "health.json");
    if (!(0, node_fs_1.existsSync)(healthPath)) {
        return null;
    }
    try {
        const content = await (0, promises_1.readFile)(healthPath, "utf-8");
        const data = JSON.parse(content);
        if (squadId && data.squad_id !== squadId) {
            return null;
        }
        return data;
    }
    catch {
        return null;
    }
}
async function collectHealth(blueprintDir, squadId) {
    const rpc = (0, rpc_bridge_1.getRpcClient)();
    await rpc.call("collect_health", { blueprintDir, squadId });
}
function printClawHealth(claw) {
    const icon = getStatusIcon(claw.status);
    const color = getStatusColor(claw.status);
    const reset = "\x1b[0m";
    console.log(` ${icon} ${color}${claw.role.padEnd(12)}${reset} ${claw.score.toFixed(1).padStart(5)} ${claw.status.padEnd(10)} ${claw.region || "unknown"}`);
    void reset;
}
function printDetailedHealth(health) {
    const reset = "\x1b[0m";
    console.log("\n" + "\u2500".repeat(60));
    console.log(" Squad Health Overview");
    console.log("\u2500".repeat(60));
    console.log(` Overall: ${health.overall_score.toFixed(1)} (${health.overall_status})`);
    console.log(` Squad: ${health.squad_id}`);
    console.log(` Updated: ${health.last_updated}`);
    console.log("\u2500".repeat(60));
    console.log(" Claw Score Status Region");
    console.log("\u2500".repeat(60));
    for (const claw of health.claws) {
        printClawHealth(claw);
    }
    if (health.alerts.length > 0) {
        console.log("\n" + "\u2500".repeat(60));
        console.log(" Alerts:");
        console.log("\u2500".repeat(60));
        for (const alert of health.alerts) {
            const color = alert.level === "critical" ? "\x1b[31m" : "\x1b[33m";
            console.log(` ${color}[${alert.level.toUpperCase()}]${reset} ${alert.role}: ${alert.message}`);
        }
    }
    console.log("");
    void reset;
}
function printCompactHealth(health) {
    const icon = getStatusIcon(health.overall_status);
    const color = getStatusColor(health.overall_status);
    const reset = "\x1b[0m";
    console.log(`${icon} ${color}${health.overall_status.toUpperCase()}${reset} Squad: ${health.overall_score.toFixed(1)} | Claws: ${health.claws.length}`);
    for (const claw of health.claws) {
        const clawIcon = getStatusIcon(claw.status);
        console.log(` ${clawIcon} ${claw.role}: ${claw.score.toFixed(1)}`);
    }
    void reset;
}
function printWatch(health) {
    console.log("\x1b[2J\x1b[H");
    console.log(`Milimo Claw Health Dashboard - ${new Date().toLocaleTimeString()}`);
    printDetailedHealth(health);
}
async function healthCommand(options) {
    const squadId = options.squad || process.env.MILIMO_SQUAD || "default";
    const blueprintDir = process.env.MILIMO_BLUEPRINT_DIR || (0, node_path_1.join)((0, node_os_1.homedir)(), ".milimo", "blueprints", squadId);
    if (options.collect) {
        try {
            await collectHealth(blueprintDir, squadId);
        }
        catch (error) {
            console.error("Failed to collect health data:", error);
        }
    }
    if (options.watch) {
        const interval = parseInt(options.interval || "5000", 10);
        const updateLoop = async () => {
            try {
                await collectHealth(blueprintDir, squadId);
                const health = await getHealthData(squadId);
                if (health) {
                    printWatch(health);
                }
            }
            catch (error) {
                console.error("Update failed:", error);
            }
            // Use void to suppress floating promise warning
            void setTimeout(() => void updateLoop(), interval);
        };
        void updateLoop();
    }
    else {
        const health = await getHealthData(squadId);
        if (!health) {
            console.log("No health data available. Run with --collect to gather data.");
            return;
        }
        if (options.json) {
            console.log(JSON.stringify(health, null, 2));
        }
        else if (options.detailed) {
            printDetailedHealth(health);
        }
        else {
            printCompactHealth(health);
        }
    }
}
//# sourceMappingURL=health.js.map