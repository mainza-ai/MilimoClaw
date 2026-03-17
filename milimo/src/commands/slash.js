"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.handleSlashCommand = handleSlashCommand;
var index_js_1 = require("../index.js");
var init_js_1 = require("./init.js");
function handleSlashCommand(ctx, api) {
    var _a, _b;
    var subcommand = (_b = (_a = ctx.args) === null || _a === void 0 ? void 0 : _a.trim().split(/\s+/)[0]) !== null && _b !== void 0 ? _b : "";
    switch (subcommand) {
        case "status":
            return slashStatus(api);
        case "role":
            return slashRole(api);
        case "finals":
            return slashFinals();
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
            "  `status`  - Show squad and claw status",
            "  `role`    - Show your claw role details",
            "  `finals`  - Show Finals Mode status",
            "",
            "For full management use the CLI:",
            "  `openclaw milimo init`           - Initialize squad",
            "  `openclaw milimo squad status`   - Squad topology",
            "  `openclaw milimo squad finals-mode` - Activate Finals Mode",
            "  `openclaw milimo blueprint list` - List blueprints",
        ].join("\n"),
    };
}
function slashStatus(api) {
    var config = (0, index_js_1.getPluginConfig)(api);
    var state = (0, init_js_1.loadMilimoState)();
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
    var lines = [
        "**🦀 Milimo Claw Status**",
        "",
        "**Squad:** ".concat(state.squadName),
        "**Role:** ".concat(state.clawRole),
        "**Template:** ".concat(state.template),
        "**Mode:** ".concat(state.solo ? "Solo" : "Mesh"),
        "**Blueprint:** v".concat(state.blueprintVersion),
        "**Initialized:** ".concat(state.initializedAt),
    ];
    if (!state.solo && state.meshMembers.length > 0) {
        lines.push("", "**Mesh Members:**");
        for (var _i = 0, _a = state.meshMembers; _i < _a.length; _i++) {
            var member = _a[_i];
            lines.push("  \u2022 ".concat(member));
        }
    }
    if (config.squadName && config.squadName !== state.squadName) {
        lines.push("", "\u26A0\uFE0F Config squad name (".concat(config.squadName, ") differs from state."));
    }
    return { text: lines.join("\n") };
}
function slashRole(api) {
    var state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        return {
            text: "**🦀 Milimo Claw**: Not initialized. Run `openclaw milimo init` first.",
        };
    }
    var roleDetails = {
        content: [
            "**🎨 Content Claw**",
            "",
            "**Mount:** `/sandbox/content`",
            "**Responsibility:** All creative output — posts, copy, campaigns, brand voice",
            "",
            "**Inference Routing:**",
            "  • Public drafts → Cloud Nemotron 120B",
            "  • Internal ideation → Local NIM",
            "  • Trend research → Cloud Nemotron 120B",
            "",
            "**Inter-Claw:**",
            "  • Receives briefs from Ops",
            "  • Queries Analytics for performance data",
            "  • Sends drafts to War Room for approval",
        ],
        ops: [
            "**📋 Ops Claw**",
            "",
            "**Mount:** `/sandbox/clients`",
            "**Responsibility:** Client lifecycle — intake, scoping, delivery, follow-up",
            "",
            "**Inference Routing:**",
            "  • Client comms → Cloud Nemotron 120B",
            "  • Internal summaries → Local NIM",
            "  • Contract review → Local NIM",
            "",
            "**Inter-Claw:**",
            "  • Sends briefs to Content/Build",
            "  • Queries Finance for pricing",
            "  • Receives completion signals",
        ],
        analytics: [
            "**📊 Analytics Claw**",
            "",
            "**Mount:** `/sandbox/analytics`",
            "**Responsibility:** Intelligence — performance, trends, opportunities",
            "",
            "**Inference Routing:**",
            "  • Market analysis → Cloud Nemotron 120B",
            "  • Internal synthesis → Local NIM",
            "  • Predictive models → Local NIM",
            "",
            "**Inter-Claw:**",
            "  • Publishes weekly intelligence reports",
            "  • Responds to Content/Build queries",
            "  • Sends revenue alerts to Finance",
        ],
        finance: [
            "**💰 Finance Claw**",
            "",
            "**Mount:** `/sandbox/finance`",
            "**Responsibility:** Financial ops — invoicing, pricing, margins",
            "",
            "**Inference Routing:**",
            "  • ⚠️ ALL data → Local NIM only (no cloud)",
            "",
            "**Inter-Claw:**",
            "  • Responds to Ops pricing queries",
            "  • Sends overdue payment alerts",
            "  • Provides revenue summaries (totals only)",
        ],
        build: [
            "**🔧 Build Claw** *(Tech Squads)*",
            "",
            "**Mount:** `/sandbox/build`",
            "**Responsibility:** Engineering — code, PRs, deploys, monitoring",
            "",
            "**Inference Routing:**",
            "  • Source code → Local NIM (always)",
            "  • Boilerplate/docs → Cloud Nemotron 120B",
            "  • Production logs → Local NIM",
            "",
            "**Inter-Claw:**",
            "  • Receives feature briefs from Ops",
            "  • Queries Analytics for user behavior",
            "  • Sends deploy signals to Ops",
            "  • Sends shipping summaries to Content",
        ],
    };
    var details = roleDetails[state.clawRole];
    if (!details) {
        return { text: "Unknown role: ".concat(state.clawRole) };
    }
    return { text: details.join("\n") };
}
function slashFinals() {
    var _a, _b;
    // Check finals mode state from disk
    var fs = require("node:fs");
    var fpath = require("node:path");
    var home = (_b = (_a = process.env["HOME"]) !== null && _a !== void 0 ? _a : process.env["USERPROFILE"]) !== null && _b !== void 0 ? _b : "/tmp";
    var finalsPath = fpath.join(home, ".milimo", "finals-mode.json");
    if (!fs.existsSync(finalsPath)) {
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
        var raw = fs.readFileSync(finalsPath, "utf-8");
        var state = JSON.parse(raw);
        if (!state.active) {
            return {
                text: "**📚 Finals Mode:** Inactive (previously active, now resumed)",
            };
        }
        return {
            text: [
                "**📚 Finals Mode:** ⚠️ ACTIVE",
                "",
                "**Since:** ".concat(state.activatedAt),
                "**Duration:** ".concat(state.duration),
                state.resumeDate ? "**Scheduled Resume:** ".concat(state.resumeDate) : null,
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
    catch (_c) {
        return { text: "**📚 Finals Mode:** Unable to read state" };
    }
}
