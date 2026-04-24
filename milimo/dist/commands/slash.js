"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.handleSlashCommand = handleSlashCommand;
const index_js_1 = require("../index.js");
const init_js_1 = require("./init.js");
const approval_js_1 = require("../warroom/approval.js");
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
function handleSlashCommand(ctx, api) {
    const parts = ctx.args?.trim().split(/\s+/) ?? [];
    const subcommand = parts[0] ?? "";
    const arg = parts[1];
    switch (subcommand) {
        case "status":
            return slashStatus(api);
        case "role":
            return slashRole(api);
        case "finals":
            return slashFinals();
        case "approve":
            return slashApprove(arg, api);
        case "veto":
            return slashVeto(arg, api);
        case "health":
            return slashHealth(api);
        case "evolution":
            return slashEvolution(api);
        default:
            return slashHelp();
    }
}
function slashHelp() {
    return {
        text: [
            "**🦀 Milimo Claw**",
            "",
            "Usage: `/milimo <subcommand>`",
            "",
            "Subcommands:",
            " `status` - Show squad and claw status",
            " `role` - Show your claw role details",
            " `finals` - Show Finals Mode status",
            " `approve <id>` - Approve a pending War Room action",
            " `veto <id>` - Block a pending action",
            " `health` - One-line health summary per claw",
            " `evolution` - Last tool built by each claw",
            "",
            "For full management use the CLI:",
            " `openclaw milimo init` - Initialize squad",
            " `openclaw milimo squad status` - Squad topology",
            " `openclaw milimo squad finals-mode` - Activate Finals Mode",
            " `openclaw milimo blueprint list` - List blueprints",
        ].join("\n"),
    };
}
function slashStatus(api) {
    const config = (0, index_js_1.getPluginConfig)(api);
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return {
            text: [
                "**🦀 Milimo Claw**: Not initialized yet.",
                "",
                "Run `openclaw milimo init --squad <name> --role <role>` to get started.",
                "",
                "Available roles: " + index_js_1.CLAW_ROLES.join(", "),
            ].join("\n"),
        };
    }
    const lines = [
        "**🦀 Milimo Claw Status**",
        "",
        `**Squad:** ${state.squadName}`,
        `**Role:** ${state.clawRole}`,
        `**Template:** ${state.template}`,
        `**Mode:** ${state.solo ? "Solo" : "Mesh"}`,
        `**Blueprint:** v${state.blueprintVersion}`,
        `**Initialized:** ${state.initializedAt}`,
    ];
    if (!state.solo && state.meshMembers.length > 0) {
        lines.push("", "**Mesh Members:**");
        for (const member of state.meshMembers) {
            lines.push(`  • ${member}`);
        }
    }
    if (config.squadName && config.squadName !== state.squadName) {
        lines.push("", `⚠️ Config squad name (${config.squadName}) differs from state.`);
    }
    return { text: lines.join("\n") };
}
function slashRole(api) {
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return {
            text: "**🦀 Milimo Claw**: Not initialized. Run `openclaw milimo init` first.",
        };
    }
    const roleDetails = {
        content: [
            "**🎨 Content Claw**",
            "",
            "**Mount:** `/sandbox/content`",
            "**Responsibility:** All creative output — posts, copy, campaigns, brand voice",
            "",
            "**Inference Routing:**",
            " • Public drafts → Cloud (NEMOCLAW_MODEL)",
            " • Internal ideation → Cloud (NEMOCLAW_MODEL)",
            " • Trend research → Cloud (NEMOCLAW_MODEL)",
            "",
            "**Inter-Claw:**",
            " • Receives briefs from Ops",
            " • Queries Analytics for performance data",
            " • Sends drafts to War Room for approval",
        ],
        ops: [
            "**📋 Ops Claw**",
            "",
            "**Mount:** `/sandbox/clients`",
            "**Responsibility:** Client lifecycle — intake, scoping, delivery, follow-up",
            "",
            "**Inference Routing:**",
            " • Client comms → Cloud (NEMOCLAW_MODEL)",
            " • Internal summaries → Cloud (NEMOCLAW_MODEL)",
            " • Contract review → Cloud (NEMOCLAW_MODEL)",
            "",
            "**Inter-Claw:**",
            " • Sends briefs to Content/Build",
            " • Queries Finance for pricing",
            " • Receives completion signals",
        ],
        analytics: [
            "**📊 Analytics Claw**",
            "",
            "**Mount:** `/sandbox/analytics`",
            "**Responsibility:** Intelligence — performance, trends, opportunities",
            "",
            "**Inference Routing:**",
            " • Market analysis → Cloud (NEMOCLAW_MODEL)",
            " • Internal synthesis → Cloud (NEMOCLAW_MODEL)",
            " • Predictive models → Cloud (NEMOCLAW_MODEL)",
            "",
            "**Inter-Claw:**",
            " • Publishes weekly intelligence reports",
            " • Responds to Content/Build queries",
            " • Sends revenue alerts to Finance",
        ],
        finance: [
            "**💰 Finance Claw**",
            "",
            "**Mount:** `/sandbox/finance`",
            "**Responsibility:** Financial ops — invoicing, pricing, margins",
            "",
            "**Inference Routing:**",
            " • ⚠️ ALL data → Cloud (NEMOCLAW_MODEL) — locked route, never external",
            "",
            "**Inter-Claw:**",
            " • Responds to Ops pricing queries",
            " • Sends overdue payment alerts",
            " • Provides revenue summaries (totals only)",
        ],
        build: [
            "**🔧 Build Claw** *(Tech Squads)*",
            "",
            "**Mount:** `/sandbox/build`",
            "**Responsibility:** Engineering — code, PRs, deploys, monitoring",
            "",
            "**Inference Routing:**",
            " • Source code → Cloud (NEMOCLAW_MODEL) — locked route",
            " • Boilerplate/docs → Cloud (NEMOCLAW_MODEL)",
            " • Production logs → Cloud (NEMOCLAW_MODEL)",
            "",
            "**Inter-Claw:**",
            " • Receives feature briefs from Ops",
            " • Queries Analytics for user behavior",
            " • Sends deploy signals to Ops",
            " • Sends shipping summaries to Content",
        ],
        assistant: [
            "**👽 Assistant Claw**",
            "",
            "**Mount:** `/sandbox/.milimo/assistant`",
            "**Responsibility:** Cross-claw coordination, operator bridge (Telegram), research, scheduling",
            "",
            "**Inference Routing:**",
            " • Operator conversations → Cloud (NEMOCLAW_MODEL)",
            " • Cross-claw queries → Cloud (NEMOCLAW_MODEL)",
            " • Internal summaries → Cloud (NEMOCLAW_MODEL)",
            "",
            "**Inter-Claw:**",
            " • Queries all claws for status and data",
            " • Assigns tasks to any claw (operator-approved)",
            " • Receives responses via War Room relay",
            " • Bridges operator messages to/from Telegram",
        ],
    };
    const details = roleDetails[state.clawRole];
    if (!details) {
        return { text: `Unknown role: ${state.clawRole}` };
    }
    return { text: details.join("\n") };
}
function slashFinals() {
    const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
    const finalsPath = (0, node_path_1.join)(home, ".milimo", "finals-mode.json");
    if (!(0, node_fs_1.existsSync)(finalsPath)) {
        return {
            text: [
                "**📚 Finals Mode:** Inactive",
                "",
                "To activate:",
                "```",
                "openclaw milimo squad finals-mode --duration 2weeks",
                "```",
            ].join("\n"),
        };
    }
    try {
        const raw = (0, node_fs_1.readFileSync)(finalsPath, "utf-8");
        const state = JSON.parse(raw);
        if (!state.active) {
            return {
                text: "**📚 Finals Mode:** Inactive (previously active, now resumed)",
            };
        }
        return {
            text: [
                "**📚 Finals Mode:** ⚠️ ACTIVE",
                "",
                `**Since:** ${state.activatedAt}`,
                `**Duration:** ${state.duration}`,
                state.resumeDate ? `**Scheduled Resume:** ${state.resumeDate}` : null,
                "",
                "To resume operations:",
                "```",
                "openclaw milimo squad resume",
                "```",
            ]
                .filter(Boolean)
                .join("\n"),
        };
    }
    catch {
        return { text: "**📚 Finals Mode:** Unable to read state" };
    }
}
function slashApprove(actionId, api) {
    if (!actionId) {
        return { text: "**❌ Error:** Usage: `/milimo approve <action_id>`" };
    }
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return { text: "**❌ Error:** Not initialized. Run `openclaw milimo init` first." };
    }
    try {
        const engine = new approval_js_1.ApprovalEngine(state.squadName);
        const messages = engine.getPendingMessages();
        const msg = messages.find((m) => m.message_id === actionId);
        if (!msg) {
            return { text: `**❌ Error:** Action \`${actionId}\` not found in pending queue.` };
        }
        engine.processDecision(msg, "APPROVED", "chat-operator");
        return {
            text: [
                "**✅ Action Approved**",
                "",
                `**Action:** ${actionId}`,
                `**Type:** ${msg.message_type}`,
                `**From:** ${msg.sender_role} → ${msg.recipient_role}`,
                "",
                "Action has been routed to the recipient.",
            ].join("\n"),
        };
    }
    catch (err) {
        return { text: `**❌ Error:** ${err.message}` };
    }
}
function slashVeto(actionId, api) {
    if (!actionId) {
        return { text: "**❌ Error:** Usage: `/milimo veto <action_id>`" };
    }
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return { text: "**❌ Error:** Not initialized. Run `openclaw milimo init` first." };
    }
    try {
        const engine = new approval_js_1.ApprovalEngine(state.squadName);
        const messages = engine.getPendingMessages();
        const msg = messages.find((m) => m.message_id === actionId);
        if (!msg) {
            return { text: `**❌ Error:** Action \`${actionId}\` not found in pending queue.` };
        }
        engine.processDecision(msg, "REJECTED", "chat-operator");
        return {
            text: [
                "**🚫 Action Vetoed**",
                "",
                `**Action:** ${actionId}`,
                `**Type:** ${msg.message_type}`,
                `**From:** ${msg.sender_role} → ${msg.recipient_role}`,
                "",
                "Action has been moved to the rejected queue.",
            ].join("\n"),
        };
    }
    catch (err) {
        return { text: `**❌ Error:** ${err.message}` };
    }
}
function slashHealth(api) {
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return { text: "**❌ Error:** Not initialized. Run `openclaw milimo init` first." };
    }
    const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
    const lines = ["**🦀 Claw Health Summary**", ""];
    const claws = state.meshMembers.length > 0 ? state.meshMembers : [state.clawRole];
    for (const claw of claws) {
        const registryPath = (0, node_path_1.join)(home, ".milimo", "tools", state.squadName, claw, "registry.json");
        let status = "○";
        let tools = 0;
        try {
            if ((0, node_fs_1.existsSync)(registryPath)) {
                const data = JSON.parse((0, node_fs_1.readFileSync)(registryPath, "utf-8"));
                tools = Object.keys(data.tools ?? {}).length;
                status = tools > 0 ? "●" : "○";
            }
        }
        catch {
            status = "⚠";
        }
        const statusColor = status === "●" ? "active" : status === "⚠" ? "error" : "idle";
        lines.push(` ${status} **${claw.toUpperCase()}** — ${tools} tools`);
    }
    return { text: lines.join("\n") };
}
function slashEvolution(api) {
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return { text: "**❌ Error:** Not initialized. Run `openclaw milimo init` first." };
    }
    const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
    const lines = ["**🔧 Evolution Log**", ""];
    const claws = state.meshMembers.length > 0 ? state.meshMembers : [state.clawRole];
    for (const claw of claws) {
        const registryPath = (0, node_path_1.join)(home, ".milimo", "tools", state.squadName, claw, "registry.json");
        try {
            if ((0, node_fs_1.existsSync)(registryPath)) {
                const data = JSON.parse((0, node_fs_1.readFileSync)(registryPath, "utf-8"));
                const tools = data.tools ?? {};
                const toolNames = Object.keys(tools);
                if (toolNames.length === 0) {
                    lines.push(` **${claw.toUpperCase()}** — No evolved tools yet`);
                    continue;
                }
                const lastTool = toolNames[toolNames.length - 1];
                const toolInfo = tools[lastTool];
                const delta = toolInfo?.performance_delta ?? "?";
                lines.push(` **${claw.toUpperCase()}** — ${lastTool} (+${delta}% uplift)`);
            }
            else {
                lines.push(` **${claw.toUpperCase()}** — No evolution data`);
            }
        }
        catch {
            lines.push(` **${claw.toUpperCase()}** — ⚠ Unable to read`);
        }
    }
    return { text: lines.join("\n") };
}
//# sourceMappingURL=slash.js.map
