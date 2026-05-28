"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerMilimoRuntimeContext = registerMilimoRuntimeContext;
/**
 * Milimo Runtime Context — NemoClaw Lifecycle Hook Integration
 *
 * Registers `before_agent_start` and `before_tool_call` hooks via the
 * OpenClaw plugin API to inject squad context and enforce the cost guard.
 *
 * The `before_agent_start` hook prepends a <milimo-squad> context block
 * to each agent turn, giving the agent awareness of:
 * - Active claws and their health status
 * - Pending action queue depth
 * - Token budget remaining (cost guard)
 * - Current approval mode
 *
 * The `before_tool_call` hook enforces the daily token budget by blocking
 * tool calls when the cost guard limit is exceeded.
 *
 * Both hooks follow the same contract as NemoClaw's native hooks
 * (see nemoclaw/src/runtime-context.ts and nemoclaw/src/index.ts).
 */
const fs_1 = require("fs");
const path_1 = require("path");
// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const DEFAULT_TOKEN_BUDGET = 50_000;
const HEARTBEAT_STALE_MS = 120_000; // 2 minutes
// ---------------------------------------------------------------------------
// Data loaders (best-effort, never throw)
// ---------------------------------------------------------------------------
function resolveMeshDir() {
    const sandboxMesh = "/sandbox/.openclaw/milimo/mesh";
    const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
    const homeMesh = (0, path_1.join)(home, ".openclaw/milimo", "mesh");
    return (0, fs_1.existsSync)(sandboxMesh) ? sandboxMesh : homeMesh;
}
function resolveDataDir() {
    const sandboxData = "/sandbox/.openclaw/milimo";
    const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
    const homeData = (0, path_1.join)(home, ".openclaw/milimo");
    return (0, fs_1.existsSync)(sandboxData) ? sandboxData : homeData;
}
/**
 * Count pending messages in the war_room inbox.
 */
function countPendingActions() {
    try {
        const inbox = (0, path_1.join)(resolveMeshDir(), "inbox", "war_room");
        if (!(0, fs_1.existsSync)(inbox))
            return 0;
        return (0, fs_1.readdirSync)(inbox).filter((f) => f.endsWith(".json")).length;
    }
    catch {
        return 0;
    }
}
/**
 * Read token usage from the cost guard state file.
 * Returns [remaining, limit] — defaults to [50000, 50000] if unavailable.
 */
function readTokenBudget() {
    try {
        const dataDir = resolveDataDir();
        // Check rate-limiter state (free tier daily tokens)
        const stateFile = (0, path_1.join)(dataDir, "rate-limits", "free.json");
        if ((0, fs_1.existsSync)(stateFile)) {
            const data = JSON.parse((0, fs_1.readFileSync)(stateFile, "utf-8"));
            const remaining = data?.state?.tokens ?? DEFAULT_TOKEN_BUDGET;
            return [remaining, DEFAULT_TOKEN_BUDGET];
        }
        // Check cost guard usage file from Python orchestrator
        const usageFile = (0, path_1.join)(dataDir, "cost_guard_usage.json");
        if ((0, fs_1.existsSync)(usageFile)) {
            const usage = JSON.parse((0, fs_1.readFileSync)(usageFile, "utf-8"));
            const tokensUsed = usage?.tokens_used ?? 0;
            const limit = usage?.daily_limit ?? DEFAULT_TOKEN_BUDGET;
            return [Math.max(0, limit - tokensUsed), limit];
        }
    }
    catch {
        // Fall through to default
    }
    return [DEFAULT_TOKEN_BUDGET, DEFAULT_TOKEN_BUDGET];
}
/**
 * Read claw health status from health.json files.
 */
function readClawHealth() {
    const claws = [];
    const roles = ["content", "ops", "analytics", "finance", "build", "assistant"];
    const now = Date.now();
    try {
        const dataDir = resolveDataDir();
        const healthDir = (0, path_1.join)(dataDir, "health");
        if (!(0, fs_1.existsSync)(healthDir))
            return claws;
        for (const role of roles) {
            const healthFile = (0, path_1.join)(healthDir, `${role}.json`);
            if (!(0, fs_1.existsSync)(healthFile)) {
                claws.push({ role, status: "stopped", lastHeartbeat: null });
                continue;
            }
            try {
                const data = JSON.parse((0, fs_1.readFileSync)(healthFile, "utf-8"));
                const lastHeartbeat = data?.timestamp || data?.last_heartbeat || null;
                let status = "unknown";
                if (lastHeartbeat) {
                    const age = now - new Date(lastHeartbeat).getTime();
                    status = age < HEARTBEAT_STALE_MS ? "running" : "stale";
                }
                claws.push({ role, status, lastHeartbeat });
            }
            catch {
                claws.push({ role, status: "unknown", lastHeartbeat: null });
            }
        }
    }
    catch {
        // Return empty if health dir is inaccessible
    }
    return claws;
}
/**
 * Read current approval mode from config.
 */
function readApprovalMode() {
    try {
        const dataDir = resolveDataDir();
        const configFile = (0, path_1.join)(dataDir, "config.json");
        if ((0, fs_1.existsSync)(configFile)) {
            const config = JSON.parse((0, fs_1.readFileSync)(configFile, "utf-8"));
            return config?.approvalMode || config?.approval_mode || "REVIEW";
        }
    }
    catch {
        // Fall through
    }
    return "REVIEW";
}
// ---------------------------------------------------------------------------
// Context builders
// ---------------------------------------------------------------------------
function getSquadSummary(pluginConfig) {
    const [remaining, limit] = readTokenBudget();
    return {
        squadName: pluginConfig.squadName || "default",
        clawRole: pluginConfig.clawRole || "solo",
        activeClaws: readClawHealth(),
        pendingActions: countPendingActions(),
        tokenBudgetRemaining: remaining,
        tokenBudgetLimit: limit,
        approvalMode: readApprovalMode(),
    };
}
function buildSquadContextText(summary) {
    const runningClaws = summary.activeClaws.filter((c) => c.status === "running").map((c) => c.role);
    const staleClaws = summary.activeClaws.filter((c) => c.status === "stale").map((c) => c.role);
    const lines = [
        "<milimo-squad>",
        `You are part of Milimo squad "${summary.squadName}", role: ${summary.clawRole}.`,
        `Active claws: ${runningClaws.length > 0 ? runningClaws.join(", ") : "none detected"}.`,
    ];
    if (staleClaws.length > 0) {
        lines.push(`⚠ Stale claws (no heartbeat >2min): ${staleClaws.join(", ")}.`);
    }
    lines.push(`Pending actions in queue: ${summary.pendingActions}.`, `Token budget: ${summary.tokenBudgetRemaining}/${summary.tokenBudgetLimit} remaining today.`, `Approval mode: ${summary.approvalMode}.`);
    if (summary.tokenBudgetRemaining < summary.tokenBudgetLimit * 0.1) {
        lines.push("⚠ Token budget critically low — prefer lighter prompts.");
    }
    lines.push("Behavior:", "- Route financial operations through the Finance claw (REVIEW→HOLD flow).", "- Do not bypass the mesh — use inter-claw messaging for cross-role work.", "- Report cost guard limits when they block operations.", "</milimo-squad>");
    return lines.join("\n");
}
// ---------------------------------------------------------------------------
// Hook registration
// ---------------------------------------------------------------------------
/**
 * Register Milimo's lifecycle hooks with the OpenClaw plugin API.
 *
 * Hooks:
 * 1. `before_agent_start` — injects <milimo-squad> context block
 * 2. `before_tool_call` — enforces cost guard daily token budget
 *
 * Both hooks are wrapped in try/catch to ensure the plugin still loads
 * even if the OpenClaw host changes the hook contract.
 */
function registerMilimoRuntimeContext(api, pluginConfig) {
    // Hook 1: Inject squad context before each agent turn
    try {
        api.on("before_agent_start", () => {
            try {
                const summary = getSquadSummary(pluginConfig);
                const contextText = buildSquadContextText(summary);
                return { prependContext: contextText };
            }
            catch (err) {
                api.logger.warn(`[milimo] Squad context injection failed: ${err instanceof Error ? err.message : String(err)}`);
                // Minimal fallback context
                return {
                    prependContext: [
                        "<milimo-squad>",
                        `You are part of Milimo squad "${pluginConfig.squadName || "default"}".`,
                        "Squad state could not be loaded — proceed with caution.",
                        "</milimo-squad>",
                    ].join("\n"),
                };
            }
        });
        api.logger.debug("[milimo] Registered before_agent_start hook (squad context).");
    }
    catch (err) {
        api.logger.warn(`[milimo] Could not register before_agent_start hook: ${err instanceof Error ? err.message : String(err)}`);
    }
    // Hook 2: Enforce cost guard on tool calls
    try {
        api.on("before_tool_call", (..._args) => {
            try {
                const [remaining] = readTokenBudget();
                // Only block when budget is fully exhausted
                if (remaining <= 0) {
                    api.logger.warn("[milimo] Cost guard: daily token budget exhausted. Blocking tool call.");
                    return {
                        block: true,
                        blockReason: "Milimo cost guard: daily token budget (50,000) exhausted. " +
                            "Wait for the daily reset at midnight UTC, or ask an operator to " +
                            "increase the budget via `openclaw milimo config set cost_guard_budget <n>`.",
                    };
                }
                // Warn when budget is low (< 10%)
                if (remaining < DEFAULT_TOKEN_BUDGET * 0.1) {
                    api.logger.warn(`[milimo] Cost guard: token budget low (${remaining}/${DEFAULT_TOKEN_BUDGET}). ` +
                        "Consider using lighter prompts.");
                }
                return undefined;
            }
            catch {
                // Never block on cost guard read errors — fail open
                return undefined;
            }
        });
        api.logger.debug("[milimo] Registered before_tool_call hook (cost guard).");
    }
    catch (err) {
        api.logger.warn(`[milimo] Could not register before_tool_call hook: ${err instanceof Error ? err.message : String(err)}`);
    }
}
//# sourceMappingURL=runtime-context.js.map