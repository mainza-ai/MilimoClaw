"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliInit = cliInit;
exports.loadMilimoState = loadMilimoState;
exports.saveMilimoState = saveMilimoState;
/**
 * `openclaw milimo init` — Squad initialization wizard.
 *
 * Phase 0.1 scope: template selection, role assignment, and local blueprint
 * deployment. Full mesh formation (0.4) and onboarding wizard (0.6) extend
 * this later.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const index_js_1 = require("../index.js");
const config_js_1 = require("../onboard/config.js");
const assistant_js_1 = require("./assistant.js");
function listTemplates(blueprintDir) {
    const templatesDir = path.join(blueprintDir, "templates");
    if (!fs.existsSync(templatesDir)) {
        return [];
    }
    return fs
        .readdirSync(templatesDir)
        .filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"))
        .map((f) => f.replace(/\.ya?ml$/, ""));
}
function listRoles(blueprintDir) {
    const rolesDir = path.join(blueprintDir, "roles");
    if (!fs.existsSync(rolesDir)) {
        return [];
    }
    return fs
        .readdirSync(rolesDir)
        .filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"))
        .map((f) => f.replace(/-claw\.ya?ml$/, "").replace(/\.ya?ml$/, ""));
}
async function cliInit(opts) {
    const { logger, pluginConfig } = opts;
    config_js_1.ConfigManager.migrate();
    const existingConfig = config_js_1.ConfigManager.load();
    if (existingConfig && existingConfig.squadName) {
        logger.warn(`Already initialized as ${existingConfig.clawRole} claw in squad "${existingConfig.squadName}".`);
        logger.info("To reinitialize, run: openclaw milimo squad clear");
        return;
    }
    logger.info("");
    logger.info(" ╔═══════════════════════════════════════════════════════╗");
    logger.info(" ║ 🦀 MILIMO CLAW — Squad Init 🦀                         ║");
    logger.info(" ╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    const squadName = opts.squad ?? pluginConfig.squadName;
    if (!squadName) {
        logger.error("Squad name is required. Use --squad <name> or set squadName in plugin config.");
        logger.info("");
        logger.info(" Example:");
        logger.info(' openclaw milimo init --squad "my-squad" --role content');
        return;
    }
    const roleStr = opts.role ?? pluginConfig.clawRole;
    if (!roleStr) {
        logger.error("Claw role is required. Use --role <role>.");
        logger.info("");
        logger.info(" Available roles:");
        for (const role of index_js_1.CLAW_ROLES) {
            const desc = getRoleDescription(role);
            logger.info(` ${role.padEnd(12)} ${desc}`);
        }
        return;
    }
    if (!index_js_1.CLAW_ROLES.includes(roleStr)) {
        logger.error(`Invalid role "${roleStr}". Must be one of: ${index_js_1.CLAW_ROLES.join(", ")}`);
        return;
    }
    const clawRole = roleStr;
    const template = opts.template ?? "custom";
    const blueprintDir = pluginConfig.blueprintDir;
    if (template !== "custom") {
        const availableTemplates = listTemplates(blueprintDir);
        if (availableTemplates.length > 0 && !availableTemplates.includes(template)) {
            logger.error(`Template "${template}" not found.`);
            logger.info(` Available: ${availableTemplates.join(", ")}`);
            return;
        }
    }
    const availableRoles = listRoles(blueprintDir);
    if (availableRoles.length > 0 && !availableRoles.includes(clawRole)) {
        logger.warn(`Role blueprint "${clawRole}-claw.yaml" not found in ${blueprintDir}/roles/. Using base configuration.`);
    }
    logger.info(` Squad: ${squadName}`);
    logger.info(` Role: ${clawRole}`);
    logger.info(` Template: ${template}`);
    logger.info(` Mode: ${opts.solo ? "Solo" : "Mesh"}`);
    logger.info("");
    config_js_1.ConfigManager.ensureDirectories();
    const config = {
        squadName,
        clawRole,
        template,
        solo: opts.solo,
        meshMembers: opts.solo ? [clawRole] : [],
        meshSecret: null,
        operatorName: process.env.USER ?? "operator",
        warRoomMode: "full",
        onboardedAt: null,
        initializedAt: new Date().toISOString(),
        blueprintVersion: "0.1.0",
        assistant: {
            name: opts.assistantName || "Nova",
            creature: opts.assistantCreature || "a claw",
            vibe: opts.assistantVibe || "sharp and unhurried",
            emoji: opts.assistantEmoji || "🦀",
        },
        activeClaws: (0, config_js_1.getActiveClawsForTemplate)(template),
    };
    config_js_1.ConfigManager.save(config);
    logger.info(" ✓ State directory created (~/.openclaw-data/milimo/)");
    logger.info(" ✓ Blueprint directories initialized");
    logger.info(" ✓ Claw configuration saved");
    logger.info("");
    // Run assistant setup automatically
    logger.info("Configuring squad assistant...");
    try {
        await (0, assistant_js_1.assistantSetup)();
    }
    catch {
        logger.warn("Assistant setup skipped — run 'milimo assistant setup' manually.");
    }
    if (opts.solo) {
        logger.info(" Solo mode: claw is ready. No mesh formation needed.");
    }
    else {
        logger.info(" Next steps:");
        logger.info(" 1. Have each squad member run: openclaw milimo init --squad");
        logger.info(` "${squadName}" --role <their-role>`);
        logger.info(" 2. Run: openclaw milimo squad status");
        logger.info(" to verify the mesh topology");
    }
    logger.info("");
    logger.info(" Run 'openclaw milimo squad status' to see your configuration.");
    logger.info("");
}
function getRoleDescription(role) {
    const descriptions = {
        content: "Creative output — posts, copy, campaigns, brand voice",
        ops: "Client lifecycle — intake, scoping, delivery, follow-up",
        analytics: "Intelligence layer — performance, trends, opportunities",
        finance: "Financial ops — invoicing, pricing, margin tracking",
        build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
        assistant: "AI helper — scheduling, research, cross-claw coordination, operator support",
        solo: "All claws active on this machine (solo mode)",
    };
    return descriptions[role];
}
function loadMilimoState() {
    return config_js_1.ConfigManager.load();
}
function saveMilimoState(state) {
    config_js_1.ConfigManager.save(state);
}
//# sourceMappingURL=init.js.map