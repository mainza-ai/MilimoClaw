"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.CLAW_ROLES = void 0;
exports.getPluginConfig = getPluginConfig;
exports.default = register;
var cli_js_1 = require("./cli.js");
var slash_js_1 = require("./commands/slash.js");
/** All valid claw roles. */
exports.CLAW_ROLES = ["content", "ops", "analytics", "finance", "build"];
var DEFAULT_PLUGIN_CONFIG = {
    squadName: "",
    clawRole: "",
    meshSecret: "",
    blueprintDir: "/opt/milimo-blueprint",
};
function getPluginConfig(api) {
    var _a;
    var raw = (_a = api.pluginConfig) !== null && _a !== void 0 ? _a : {};
    return {
        squadName: typeof raw["squadName"] === "string" ? raw["squadName"] : DEFAULT_PLUGIN_CONFIG.squadName,
        clawRole: typeof raw["clawRole"] === "string" && isValidClawRole(raw["clawRole"])
            ? raw["clawRole"]
            : DEFAULT_PLUGIN_CONFIG.clawRole,
        meshSecret: typeof raw["meshSecret"] === "string" ? raw["meshSecret"] : DEFAULT_PLUGIN_CONFIG.meshSecret,
        blueprintDir: typeof raw["blueprintDir"] === "string"
            ? raw["blueprintDir"]
            : DEFAULT_PLUGIN_CONFIG.blueprintDir,
    };
}
function isValidClawRole(value) {
    return value === "" || exports.CLAW_ROLES.includes(value);
}
// ---------------------------------------------------------------------------
// Plugin entry point
// ---------------------------------------------------------------------------
function register(api) {
    // 1. Register /milimo slash command (chat interface)
    api.registerCommand({
        name: "milimo",
        description: "Milimo Claw squad management (status, roles, mesh).",
        acceptsArgs: true,
        handler: function (ctx) { return (0, slash_js_1.handleSlashCommand)(ctx, api); },
    });
    // 2. Register `openclaw milimo` CLI subcommands (commander.js)
    api.registerCli(function (cliCtx) {
        (0, cli_js_1.registerCliCommands)(cliCtx, api);
    }, { commands: ["milimo"] });
    // 3. Display registration banner
    var config = getPluginConfig(api);
    var roleDisplay = config.clawRole || "not assigned";
    var squadDisplay = config.squadName || "not configured";
    api.logger.info("");
    api.logger.info("  ┌─────────────────────────────────────────────────────┐");
    api.logger.info("  │  Milimo Claw registered                             │");
    api.logger.info("  │                                                     │");
    api.logger.info("  \u2502  Squad:     ".concat(squadDisplay.padEnd(40), "\u2502"));
    api.logger.info("  \u2502  Role:      ".concat(roleDisplay.padEnd(40), "\u2502"));
    api.logger.info("  │  Commands:  openclaw milimo <command>               │");
    api.logger.info("  │  Chat:      /milimo <command>                       │");
    api.logger.info("  └─────────────────────────────────────────────────────┘");
    api.logger.info("");
}
