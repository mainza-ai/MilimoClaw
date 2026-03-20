"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.CLAW_ROLES = void 0;
exports.getPluginConfig = getPluginConfig;
exports.default = register;
const cli_js_1 = require("./cli.js");
const slash_js_1 = require("./commands/slash.js");
const squad_js_1 = require("./commands/squad.js");
const config_js_1 = require("./onboard/config.js");
/** All valid claw roles. */
exports.CLAW_ROLES = ["content", "ops", "analytics", "finance", "build"];
const DEFAULT_PLUGIN_CONFIG = {
    squadName: "",
    clawRole: "",
    meshSecret: "",
    blueprintDir: "/opt/milimo-blueprint",
};
function getPluginConfig(api) {
    const raw = api.pluginConfig ?? {};
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
        handler: (ctx) => (0, slash_js_1.handleSlashCommand)(ctx, api),
    });
    // 2. Register `openclaw milimo` CLI subcommands (commander.js)
    api.registerCli((cliCtx) => {
        (0, cli_js_1.registerCliCommands)(cliCtx, api);
    }, { commands: ["milimo"] });
    // 3. Load onboarding config for banner display
    const onboardConfig = (0, config_js_1.loadOnboardConfig)();
    const config = getPluginConfig(api);
    // 4. Auto-resume check for Finals mode
    (0, squad_js_1.checkFinalsModeAutoResume)(api.logger);
    // 5. Display registration banner with onboarding status
    const roleDisplay = onboardConfig?.clawRole || config.clawRole || "not assigned";
    const squadDisplay = onboardConfig?.squadName || config.squadName || "not configured";
    const templateDisplay = onboardConfig?.template || "not selected";
    api.logger.info("");
    api.logger.info(" ┌─────────────────────────────────────────────────────┐");
    api.logger.info(" │ Milimo Claw registered │");
    api.logger.info(" │ │");
    api.logger.info(` │ Squad: ${squadDisplay.padEnd(40)}│`);
    api.logger.info(` │ Role: ${roleDisplay.padEnd(40)}│`);
    api.logger.info(` │ Template: ${templateDisplay.padEnd(38)}│`);
    api.logger.info(" │ Commands: openclaw milimo <command> │");
    api.logger.info(" │ Chat: /milimo <command> │");
    api.logger.info(" └─────────────────────────────────────────────────────┘");
    api.logger.info("");
    if (!onboardConfig) {
        api.logger.info(" ⚠ Not onboarded. Run: openclaw milimo onboard");
        api.logger.info("");
    }
}
//# sourceMappingURL=index.js.map