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
const runtime_context_js_1 = require("./hooks/runtime-context.js");
const claw_launcher_service_js_1 = require("./hooks/claw-launcher-service.js");
const config_js_1 = require("./onboard/config.js");
const onboard_js_1 = require("./commands/onboard.js");
const rpc_bridge_1 = require("./lib/rpc-bridge");
/** All valid claw roles (excluding "solo" which is a mode indicator). */
exports.CLAW_ROLES = [
    "content",
    "ops",
    "analytics",
    "finance",
    "build",
    "assistant",
];
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
    return value === "" || exports.CLAW_ROLES.includes(value) || value === "solo";
}
// ---------------------------------------------------------------------------
// Plugin entry point
// ---------------------------------------------------------------------------
let _bannerDisplayed = false;
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
    // 4. Register NemoClaw lifecycle hooks (squad context + cost guard)
    try {
        (0, runtime_context_js_1.registerMilimoRuntimeContext)(api, config);
    }
    catch (err) {
        api.logger.warn(`[milimo] Could not register runtime hooks: ${err instanceof Error ? err.message : String(err)}`);
    }
    // 4b. Register claw launcher as managed OpenClaw service
    (0, claw_launcher_service_js_1.registerClawLauncherService)(api, config);
    // 5. Auto-resume check for Finals mode
    (0, squad_js_1.checkFinalsModeAutoResume)(api.logger);
    // 6. Display registration banner with onboarding status (once per process)
    if (!_bannerDisplayed) {
        _bannerDisplayed = true;
        const roleDisplay = (0, onboard_js_1.formatRoleDisplay)((onboardConfig ?? { clawRole: config.clawRole, activeClaws: [] })) || "not assigned";
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
    // 7. Check Python RPC server availability
    const rpc = (0, rpc_bridge_1.getRpcClient)();
    rpc.ping().then((alive) => {
        if (alive) {
            api.logger.debug("[milimo] Python RPC server connected.");
        }
        else {
            api.logger.warn("[milimo] Python RPC server not reachable on 127.0.0.1:19999. " +
                "Start it with: python3 -m orchestrator.bridge_server");
        }
    });
}
//# sourceMappingURL=index.js.map