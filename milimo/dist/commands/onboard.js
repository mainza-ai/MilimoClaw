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
exports.cliOnboard = cliOnboard;
exports.cliOnboardStatus = cliOnboardStatus;
/**
 * `openclaw milimo onboard` — MilimoClaw Onboarding Wizard
 *
 * Interactive setup for squad configuration, template selection,
 * and role assignment. Extends NemoClaw's onboarding foundation.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const index_js_1 = require("../index.js");
const config_js_1 = require("../onboard/config.js");
const prompt_js_1 = require("../onboard/prompt.js");
const validate_js_1 = require("../onboard/validate.js");
const template_js_1 = require("../onboard/template.js");
function showConfig(config, logger) {
    logger.info(` Squad: ${config.squadName}`);
    logger.info(` Role: ${config.clawRole}`);
    logger.info(` Template: ${config.template}`);
    logger.info(` Mode: ${config.solo ? "Solo" : "Mesh"}`);
    logger.info(` War Room: ${config.warRoomMode}`);
    logger.info(` Onboarded: ${config.onboardedAt}`);
}
function isNonInteractive(opts) {
    if (!opts.squad || !opts.role || !opts.template)
        return false;
    if (!opts.warRoomMode)
        return false;
    return true;
}
function createMilimoDirectories() {
    const home = process.env.HOME ?? process.env.USERPROFILE ?? "/tmp";
    const baseDir = path.join(home, ".milimo");
    const dirs = [
        baseDir,
        path.join(baseDir, "blueprints"),
        path.join(baseDir, "audit"),
        path.join(baseDir, "mesh"),
        path.join(baseDir, "evolution"),
        path.join(baseDir, "sandbox"),
    ];
    for (const dir of dirs) {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    }
}
async function cliOnboard(opts) {
    const { logger, pluginConfig } = opts;
    const nonInteractive = isNonInteractive(opts);
    logger.info("");
    logger.info(" ╔═══════════════════════════════════════════════════════╗");
    logger.info(" ║ 🦀 MILIMO CLAW — Onboarding Wizard 🦀 ║");
    logger.info(" ╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    // Step 0: Check NemoClaw onboarding
    if (!(0, config_js_1.isNemoClawOnboarded)()) {
        logger.warn("NemoClaw is not onboarded. Inference configuration is missing.");
        logger.info("");
        logger.info("Please run NemoClaw onboarding first:");
        logger.info("  openclaw nemoclaw onboard");
        logger.info("");
        if (!nonInteractive) {
            const proceed = await (0, prompt_js_1.promptConfirm)("Continue anyway? (Inference will use defaults)", false);
            if (!proceed) {
                return;
            }
        }
        else {
            return;
        }
    }
    else {
        const nemoclawConfig = (0, config_js_1.loadNemoClawConfig)();
        if (nemoclawConfig) {
            logger.info(`Inference: ${nemoclawConfig.model} @ ${nemoclawConfig.endpointUrl}`);
            logger.info("");
        }
    }
    // Step 1: Check existing Milimo configuration
    const existing = (0, config_js_1.loadOnboardConfig)();
    if (existing) {
        logger.info("Existing Milimo configuration found:");
        showConfig(existing, logger);
        logger.info("");
        if (!nonInteractive) {
            const reconfigure = await (0, prompt_js_1.promptConfirm)("Reconfigure?", false);
            if (!reconfigure) {
                logger.info("Keeping existing configuration.");
                return;
            }
        }
    }
    // Step 2: Template Selection
    let template;
    if (opts.template) {
        template = opts.template;
    }
    else {
        const builtInTemplates = (0, template_js_1.getBuiltInTemplates)();
        const discoveredTemplates = (0, template_js_1.discoverTemplates)(pluginConfig.blueprintDir);
        const allTemplates = [...discoveredTemplates, ...builtInTemplates.filter((b) => !discoveredTemplates.some((d) => d.id === b.id))];
        const templateOptions = allTemplates.map((t) => ({
            label: t.displayName,
            value: t.id,
            hint: t.solo ? "solo" : `squad of ${t.squadSize}`,
        }));
        logger.info("Select a squad template:");
        template = await (0, prompt_js_1.promptSelect)("Template:", templateOptions, 0);
    }
    const selectedTemplate = (0, template_js_1.getBuiltInTemplates)().find((t) => t.id === template) ||
        (0, template_js_1.discoverTemplates)(pluginConfig.blueprintDir).find((t) => t.id === template);
    // Step 3: Solo vs Mesh Mode
    const solo = opts.solo ?? selectedTemplate?.solo ?? true;
    if (!opts.solo && !nonInteractive) {
        const soloConfirm = await (0, prompt_js_1.promptConfirm)("Operating solo (no mesh coordination)?", true);
        if (!soloConfirm) {
            logger.info("");
            logger.info("Mesh mode selected. Each squad member will need to:");
            logger.info("  1. Run: openclaw milimo onboard --squad <name> --role <role>");
            logger.info("  2. Share the mesh secret for authentication");
            logger.info("");
        }
    }
    // Step 4: Squad Name
    let squadName;
    if (opts.squad) {
        const validation = (0, validate_js_1.validateSquadName)(opts.squad);
        if (!validation.valid) {
            logger.error(`Invalid squad name: ${validation.error}`);
            return;
        }
        squadName = opts.squad.trim();
    }
    else {
        for (;;) {
            const input = await (0, prompt_js_1.promptInput)("Squad name", "my-squad");
            const validation = (0, validate_js_1.validateSquadName)(input);
            if (validation.valid) {
                squadName = input.trim();
                break;
            }
            logger.error(validation.error || "Invalid squad name");
        }
    }
    // Step 5: Role Assignment
    let clawRole;
    if (opts.role) {
        if (!index_js_1.CLAW_ROLES.includes(opts.role)) {
            logger.error(`Invalid role "${opts.role}". Must be one of: ${index_js_1.CLAW_ROLES.join(", ")}`);
            return;
        }
        clawRole = opts.role;
    }
    else {
        const roleOptions = index_js_1.CLAW_ROLES.map((role) => ({
            label: role,
            value: role,
            hint: (0, template_js_1.getRoleDescription)(role),
        }));
        const defaultIndex = selectedTemplate?.clawsActive?.[0]
            ? index_js_1.CLAW_ROLES.indexOf(selectedTemplate.clawsActive[0])
            : 0;
        const selectedRole = await (0, prompt_js_1.promptSelect)("Your claw role:", roleOptions, defaultIndex);
        clawRole = selectedRole;
    }
    // Step 6: Operator Name
    let operatorName;
    if (opts.operator) {
        const validation = (0, validate_js_1.validateOperatorName)(opts.operator);
        if (!validation.valid) {
            logger.error(`Invalid operator name: ${validation.error}`);
            return;
        }
        operatorName = opts.operator.trim();
    }
    else {
        const defaultOperator = process.env.USER || "operator";
        const input = await (0, prompt_js_1.promptInput)("Operator name", defaultOperator);
        const validation = (0, validate_js_1.validateOperatorName)(input);
        if (!validation.valid) {
            operatorName = defaultOperator;
        }
        else {
            operatorName = input.trim();
        }
    }
    // Step 7: War Room Mode
    let warRoomMode;
    if (opts.warRoomMode) {
        warRoomMode = opts.warRoomMode;
    }
    else {
        const modeOptions = [
            { label: "Full", value: "full", hint: "Complete operator dashboard with all features" },
            { label: "Minimal", value: "minimal", hint: "Essential monitoring only" },
            { label: "Disabled", value: "disabled", hint: "No War Room (headless operation)" },
        ];
        const selected = await (0, prompt_js_1.promptSelect)("War Room mode:", modeOptions, 0);
        warRoomMode = selected;
    }
    // Step 8: Mesh Secret (if mesh mode)
    let meshSecret = null;
    let meshMembers = [];
    if (solo) {
        meshMembers = [clawRole];
    }
    else {
        if (!nonInteractive) {
            const generate = await (0, prompt_js_1.promptConfirm)("Generate a new mesh secret?", true);
            if (generate) {
                meshSecret = (0, validate_js_1.generateMeshSecret)();
                logger.info("");
                logger.info("Generated mesh secret (share with squad members):");
                logger.info(`  ${meshSecret}`);
                logger.info("");
            }
            else {
                meshSecret = await (0, prompt_js_1.promptInput)("Enter existing mesh secret");
            }
        }
        meshMembers = selectedTemplate?.clawsActive || [clawRole];
    }
    // Step 9: Validate Template (if not custom)
    if (template !== "custom") {
        const templatePath = (0, template_js_1.resolveTemplatePath)(template, pluginConfig.blueprintDir);
        if (templatePath) {
            logger.info(`Validating template: ${template}...`);
            const validation = (0, validate_js_1.validateTemplateFile)(templatePath);
            if (!validation.valid) {
                logger.error(`Template validation failed: ${validation.errors.join(", ")}`);
                logger.info("Continuing with default configuration...");
            }
            else {
                logger.info("Template validated successfully.");
            }
        }
    }
    // Step 10: Confirmation
    logger.info("");
    logger.info("Configuration summary:");
    logger.info(` Squad: ${squadName}`);
    logger.info(` Role: ${clawRole} — ${(0, template_js_1.getRoleDescription)(clawRole)}`);
    logger.info(` Template: ${template}`);
    logger.info(` Mode: ${solo ? "Solo" : "Mesh"}`);
    logger.info(` Operator: ${operatorName}`);
    logger.info(` War Room: ${warRoomMode}`);
    if (!solo && meshSecret) {
        logger.info(` Mesh Secret: ${meshSecret.slice(0, 8)}...`);
    }
    logger.info("");
    if (!nonInteractive) {
        const proceed = await (0, prompt_js_1.promptConfirm)("Apply this configuration?");
        if (!proceed) {
            logger.info("Onboarding cancelled.");
            return;
        }
    }
    // Step 11: Apply Configuration
    logger.info("");
    logger.info("Applying configuration...");
    // Create directories
    createMilimoDirectories();
    logger.info(" ✓ Created ~/.milimo/ directory structure");
    // Save configuration
    const config = {
        squadName,
        clawRole,
        template,
        solo,
        meshMembers,
        meshSecret,
        operatorName,
        warRoomMode,
        onboardedAt: new Date().toISOString(),
        initializedAt: new Date().toISOString(),
        blueprintVersion: "0.1.0",
    };
    (0, config_js_1.saveOnboardConfig)(config);
    logger.info(" ✓ Saved configuration to ~/.milimo/config.json");
    // Step 12: Success
    logger.info("");
    logger.info("╔═══════════════════════════════════════════════════════╗");
    logger.info("║ 🎉 Onboarding Complete! 🎉 ║");
    logger.info("╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    logger.info(` Squad: ${squadName}`);
    logger.info(` Role: ${clawRole}`);
    logger.info(` Template: ${template}`);
    logger.info("");
    logger.info("Next steps:");
    logger.info("  openclaw milimo squad status     # View squad configuration");
    logger.info("  openclaw milimo warroom          # Launch the War Room dashboard");
    if (!solo) {
        logger.info("");
        logger.info("For mesh setup:");
        logger.info("  Share the mesh secret with squad members");
        logger.info("  Each member runs: openclaw milimo onboard --squad " + squadName);
    }
    logger.info("");
}
async function cliOnboardStatus(logger) {
    const config = (0, config_js_1.loadOnboardConfig)();
    if (!config) {
        logger.info("");
        logger.info("No Milimo configuration found.");
        logger.info("");
        logger.info("Run the onboard command to set up:");
        logger.info("  openclaw milimo onboard");
        logger.info("");
        return;
    }
    logger.info("");
    logger.info("Milimo Configuration:");
    logger.info(` Squad: ${config.squadName}`);
    logger.info(` Role: ${config.clawRole}`);
    logger.info(` Template: ${config.template}`);
    logger.info(` Mode: ${config.solo ? "Solo" : "Mesh"}`);
    logger.info(` Operator: ${config.operatorName}`);
    logger.info(` War Room: ${config.warRoomMode}`);
    logger.info(` Onboarded: ${config.onboardedAt}`);
    logger.info("");
    if (!config.solo) {
        logger.info("Mesh Members:");
        for (const member of config.meshMembers) {
            logger.info(`  - ${member}`);
        }
        logger.info("");
    }
    logger.info("To reconfigure, run: openclaw milimo onboard");
    logger.info("");
}
//# sourceMappingURL=onboard.js.map