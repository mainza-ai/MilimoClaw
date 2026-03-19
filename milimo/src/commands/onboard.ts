// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `openclaw milimo onboard` — MilimoClaw Onboarding Wizard
 *
 * Interactive setup for squad configuration, template selection,
 * and role assignment. Extends NemoClaw's onboarding foundation.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { PluginLogger, MilimoConfig, ClawRole } from "../index.js";
import { CLAW_ROLES } from "../index.js";
import {
  loadOnboardConfig,
  saveOnboardConfig,
  isNemoClawOnboarded,
  loadNemoClawConfig,
  type MilimoOnboardConfig,
} from "../onboard/config.js";
import { promptInput, promptConfirm, promptSelect } from "../onboard/prompt.js";
import {
  validateTemplateFile,
  validateSquadName,
  validateOperatorName,
  generateMeshSecret,
} from "../onboard/validate.js";
import {
  getBuiltInTemplates,
  discoverTemplates,
  getRoleDescription,
  resolveTemplatePath,
  type TemplateDiscovery,
} from "../onboard/template.js";

export interface OnboardOptions {
  squad?: string;
  role?: string;
  template?: string;
  solo?: boolean;
  operator?: string;
  warRoomMode?: "full" | "minimal" | "disabled";
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

function showConfig(config: MilimoOnboardConfig, logger: PluginLogger): void {
  logger.info(` Squad: ${config.squadName}`);
  logger.info(` Role: ${config.clawRole}`);
  logger.info(` Template: ${config.template}`);
  logger.info(` Mode: ${config.solo ? "Solo" : "Mesh"}`);
  logger.info(` War Room: ${config.warRoomMode}`);
  logger.info(` Onboarded: ${config.onboardedAt}`);
}

function isNonInteractive(opts: OnboardOptions): boolean {
  if (!opts.squad || !opts.role || !opts.template) return false;
  if (!opts.warRoomMode) return false;
  return true;
}

function createMilimoDirectories(): void {
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

export async function cliOnboard(opts: OnboardOptions): Promise<void> {
  const { logger, pluginConfig } = opts;
  const nonInteractive = isNonInteractive(opts);

  logger.info("");
  logger.info(" ╔═══════════════════════════════════════════════════════╗");
  logger.info(" ║ 🦀 MILIMO CLAW — Onboarding Wizard 🦀 ║");
  logger.info(" ╚═══════════════════════════════════════════════════════╝");
  logger.info("");

  // Step 0: Check NemoClaw onboarding
  if (!isNemoClawOnboarded()) {
    logger.warn("NemoClaw is not onboarded. Inference configuration is missing.");
    logger.info("");
    logger.info("Please run NemoClaw onboarding first:");
    logger.info("  openclaw nemoclaw onboard");
    logger.info("");
    if (!nonInteractive) {
      const proceed = await promptConfirm("Continue anyway? (Inference will use defaults)", false);
      if (!proceed) {
        return;
      }
    } else {
      return;
    }
  } else {
    const nemoclawConfig = loadNemoClawConfig();
    if (nemoclawConfig) {
      logger.info(`Inference: ${nemoclawConfig.model} @ ${nemoclawConfig.endpointUrl}`);
      logger.info("");
    }
  }

  // Step 1: Check existing Milimo configuration
  const existing = loadOnboardConfig();
  if (existing) {
    logger.info("Existing Milimo configuration found:");
    showConfig(existing, logger);
    logger.info("");

    if (!nonInteractive) {
      const reconfigure = await promptConfirm("Reconfigure?", false);
      if (!reconfigure) {
        logger.info("Keeping existing configuration.");
        return;
      }
    }
  }

  // Step 2: Template Selection
  let template: string;
  if (opts.template) {
    template = opts.template;
  } else {
    const builtInTemplates = getBuiltInTemplates();
    const discoveredTemplates = discoverTemplates(pluginConfig.blueprintDir);
    const allTemplates = [...discoveredTemplates, ...builtInTemplates.filter(
      (b) => !discoveredTemplates.some((d) => d.id === b.id)
    )];

    const templateOptions = allTemplates.map((t) => ({
      label: t.displayName,
      value: t.id,
      hint: t.solo ? "solo" : `squad of ${t.squadSize}`,
    }));

    logger.info("Select a squad template:");
    template = await promptSelect("Template:", templateOptions, 0);
  }

  const selectedTemplate = getBuiltInTemplates().find((t) => t.id === template) ||
    discoverTemplates(pluginConfig.blueprintDir).find((t) => t.id === template);

  // Step 3: Solo vs Mesh Mode
  const solo = opts.solo ?? selectedTemplate?.solo ?? true;
  if (!opts.solo && !nonInteractive) {
    const soloConfirm = await promptConfirm("Operating solo (no mesh coordination)?", true);
    if (!soloConfirm) {
      logger.info("");
      logger.info("Mesh mode selected. Each squad member will need to:");
      logger.info("  1. Run: openclaw milimo onboard --squad <name> --role <role>");
      logger.info("  2. Share the mesh secret for authentication");
      logger.info("");
    }
  }

  // Step 4: Squad Name
  let squadName: string;
  if (opts.squad) {
    const validation = validateSquadName(opts.squad);
    if (!validation.valid) {
      logger.error(`Invalid squad name: ${validation.error}`);
      return;
    }
    squadName = opts.squad.trim();
  } else {
    for (;;) {
      const input = await promptInput("Squad name", "my-squad");
      const validation = validateSquadName(input);
      if (validation.valid) {
        squadName = input.trim();
        break;
      }
      logger.error(validation.error || "Invalid squad name");
    }
  }

  // Step 5: Role Assignment
  let clawRole: ClawRole;
  if (opts.role) {
    if (!CLAW_ROLES.includes(opts.role as ClawRole)) {
      logger.error(`Invalid role "${opts.role}". Must be one of: ${CLAW_ROLES.join(", ")}`);
      return;
    }
    clawRole = opts.role as ClawRole;
  } else {
    const roleOptions = CLAW_ROLES.map((role) => ({
      label: role,
      value: role,
      hint: getRoleDescription(role),
    }));

    const defaultIndex = selectedTemplate?.clawsActive?.[0]
      ? CLAW_ROLES.indexOf(selectedTemplate.clawsActive[0] as ClawRole)
      : 0;

    const selectedRole = await promptSelect("Your claw role:", roleOptions, defaultIndex);
    clawRole = selectedRole as ClawRole;
  }

  // Step 6: Operator Name
  let operatorName: string;
  if (opts.operator) {
    const validation = validateOperatorName(opts.operator);
    if (!validation.valid) {
      logger.error(`Invalid operator name: ${validation.error}`);
      return;
    }
    operatorName = opts.operator.trim();
  } else {
    const defaultOperator = process.env.USER || "operator";
    const input = await promptInput("Operator name", defaultOperator);
    const validation = validateOperatorName(input);
    if (!validation.valid) {
      operatorName = defaultOperator;
    } else {
      operatorName = input.trim();
    }
  }

  // Step 7: War Room Mode
  let warRoomMode: "full" | "minimal" | "disabled";
  if (opts.warRoomMode) {
    warRoomMode = opts.warRoomMode;
  } else {
    const modeOptions = [
      { label: "Full", value: "full", hint: "Complete operator dashboard with all features" },
      { label: "Minimal", value: "minimal", hint: "Essential monitoring only" },
      { label: "Disabled", value: "disabled", hint: "No War Room (headless operation)" },
    ];
    const selected = await promptSelect("War Room mode:", modeOptions, 0);
    warRoomMode = selected as "full" | "minimal" | "disabled";
  }

  // Step 8: Mesh Secret (if mesh mode)
  let meshSecret: string | null = null;
  let meshMembers: string[] = [];

  if (solo) {
    meshMembers = [clawRole];
  } else {
    if (!nonInteractive) {
      const generate = await promptConfirm("Generate a new mesh secret?", true);
      if (generate) {
        meshSecret = generateMeshSecret();
        logger.info("");
        logger.info("Generated mesh secret (share with squad members):");
        logger.info(`  ${meshSecret}`);
        logger.info("");
      } else {
        meshSecret = await promptInput("Enter existing mesh secret");
      }
    }
    meshMembers = selectedTemplate?.clawsActive || [clawRole];
  }

  // Step 9: Validate Template (if not custom)
  if (template !== "custom") {
    const templatePath = resolveTemplatePath(template, pluginConfig.blueprintDir);
    if (templatePath) {
      logger.info(`Validating template: ${template}...`);
      const validation = validateTemplateFile(templatePath);
      if (!validation.valid) {
        logger.error(`Template validation failed: ${validation.errors.join(", ")}`);
        logger.info("Continuing with default configuration...");
      } else {
        logger.info("Template validated successfully.");
      }
    }
  }

  // Step 10: Confirmation
  logger.info("");
  logger.info("Configuration summary:");
  logger.info(` Squad: ${squadName}`);
  logger.info(` Role: ${clawRole} — ${getRoleDescription(clawRole)}`);
  logger.info(` Template: ${template}`);
  logger.info(` Mode: ${solo ? "Solo" : "Mesh"}`);
  logger.info(` Operator: ${operatorName}`);
  logger.info(` War Room: ${warRoomMode}`);
  if (!solo && meshSecret) {
    logger.info(` Mesh Secret: ${meshSecret.slice(0, 8)}...`);
  }
  logger.info("");

  if (!nonInteractive) {
    const proceed = await promptConfirm("Apply this configuration?");
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
  const config: MilimoOnboardConfig = {
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

  saveOnboardConfig(config);
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

export async function cliOnboardStatus(logger: PluginLogger): Promise<void> {
  const config = loadOnboardConfig();

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
