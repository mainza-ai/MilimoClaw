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
  type AssistantPersona,
  getActiveClawsForTemplate,
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
import { assistantSetup } from "./assistant.js";

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

function formatRoleDisplay(config: MilimoOnboardConfig): string {
  if (config.clawRole === "solo") {
    const claws = config.activeClaws?.join(", ") ?? "all claws";
    return `Solo (${claws})`;
  }
  return config.clawRole;
}

export { formatRoleDisplay };

function showConfig(config: MilimoOnboardConfig, logger: PluginLogger): void {
  logger.info(` Squad: ${config.squadName}`);
  logger.info(` Role: ${formatRoleDisplay(config)}`);
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
    logger.info(" openclaw nemoclaw onboard");
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
  // If the template declares solo: true, skip the confirmation entirely.
  // Asking "Operating solo?" for a template named "Solo Founder" is redundant
  // and causes readline race conditions with sequential prompts.
  let solo = opts.solo ?? selectedTemplate?.solo ?? true;
  if (selectedTemplate?.solo) {
    // Template is definitively solo — no confirmation needed
    if (!nonInteractive) {
      logger.info("");
      logger.info(`Template "${selectedTemplate.displayName}" runs all claws on one machine.`);
      logger.info("");
    }
  } else if (!opts.solo && !nonInteractive) {
    const soloConfirm = await promptConfirm("Operating solo (no mesh coordination)?", true);
    if (!soloConfirm) {
      solo = false;
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

  // Step 5: Role Assignment — conditional on operating mode
  let clawRole: ClawRole;
  if (solo) {
    // Solo mode: all claws run on this machine.
    // Role selection is meaningless — skip it entirely.
    clawRole = "solo" as ClawRole;
    const templateClaws = selectedTemplate?.clawsActive || getActiveClawsForTemplate(template);
    const activeClawsDisplay = templateClaws.join(" · ");
    logger.info("");
    logger.info(`✓ Solo mode — all claws will run on this machine:`);
    logger.info(`    ${activeClawsDisplay}`);
    logger.info("");
  } else {
    // Mesh mode: operator runs exactly one claw on this machine.
    // Role selection is correct and necessary here.
    if (opts.role) {
      if (!CLAW_ROLES.includes(opts.role as ClawRole)) {
        logger.error(`Invalid role "${opts.role}". Must be one of: ${CLAW_ROLES.join(", ")}`);
        return;
      }
      clawRole = opts.role as ClawRole;
    } else {
      logger.info("");
      logger.info("Mesh mode — which claw are you running on this machine?");
      logger.info("");

      // Only offer roles that are active in the selected template
      const templateActiveClaws = selectedTemplate?.clawsActive || getActiveClawsForTemplate(template);
      const roleOptions = CLAW_ROLES
        .filter((role) => templateActiveClaws.includes(role))
        .map((role) => ({
          label: role,
          value: role,
          hint: getRoleDescription(role),
        }));

      const defaultIndex = 0;
      const selectedRole = await promptSelect("Your claw role:", roleOptions, defaultIndex);
      clawRole = selectedRole as ClawRole;

      const others = templateActiveClaws.filter((c) => c !== clawRole).join(", ");
      logger.info("");
      logger.info(`✓ You are running the ${clawRole} claw on this machine.`);
      if (others) {
        logger.info(`    Other squad members will run: ${others}`);
      }
      logger.info("");
    }
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

  // Step 6a: Assistant Persona
  let assistant: AssistantPersona;
  if (!nonInteractive) {
    logger.info("");
    logger.info("── Assistant Persona ─────────────────────────────────");
    logger.info("Your squad assistant is your conversational interface to");
    logger.info("all your claws. Give it a name, a creature, and a vibe.");
    logger.info("");
    logger.info("Examples:");
    logger.info('  Name: Nova · Creature: a hawk · Vibe: fast and precise · 🦅');
    logger.info('  Name: Rex · Creature: a wolf · Vibe: direct and loyal · 🐺');
    logger.info('  Name: Sage · Creature: an owl · Vibe: measured and wise · 🦉');
    logger.info('  Name: Moyo · Creature: a claw · Vibe: sharp and unhurried · 🦀');
    logger.info("");

    const nameInput = await promptInput("Assistant name", "Nova");
    const creatureInput = await promptInput("Creature (e.g. a claw, a hawk, an owl)", "a claw");
    const vibeInput = await promptInput("Vibe (e.g. sharp and unhurried, warm and direct)", "sharp and unhurried");
    const emojiInput = await promptInput("Signature emoji", "🦀");

    assistant = {
      name: nameInput || "Nova",
      creature: creatureInput || "a claw",
      vibe: vibeInput || "sharp and unhurried",
      emoji: emojiInput || "🦀",
    };
  } else {
    assistant = {
      name: "Nova",
      creature: "a claw",
      vibe: "sharp and unhurried",
      emoji: "🦀",
    };
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
    // In solo mode, meshMembers contains all active claws
    meshMembers = selectedTemplate?.clawsActive || getActiveClawsForTemplate(template);
  } else {
    if (!nonInteractive) {
      const generate = await promptConfirm("Generate a new mesh secret?", true);
      if (generate) {
        meshSecret = generateMeshSecret();
        logger.info("");
        logger.info("Generated mesh secret (share with squad members):");
        logger.info(` ${meshSecret}`);
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
  const activeClaws = getActiveClawsForTemplate(template);
  const clawsDisplay = activeClaws.join(", ");

  logger.info("");
  logger.info("Configuration summary:");
  logger.info(` Squad: ${squadName}`);
  logger.info(` Template: ${template} (${clawsDisplay})`);
  logger.info(` Mode: ${solo ? "Solo" : "Mesh"}`);
  logger.info(` Operator: ${operatorName}`);
  logger.info(` Assistant: ${assistant.name} (${assistant.creature} · ${assistant.vibe} · ${assistant.emoji})`);
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
    assistant,
    activeClaws,
  };

  saveOnboardConfig(config);
  logger.info(" ✓ Saved configuration to ~/.milimo/config.json");

  // Run assistant setup automatically
  logger.info("");
  logger.info("Configuring squad assistant...");
  try {
    await assistantSetup();
  } catch (err) {
    logger.warn("Assistant setup skipped — run 'milimo assistant setup' manually.");
    logger.warn(err instanceof Error ? err.message : String(err));
  }

  // Step 12: Success
  const { name, emoji } = assistant;
  logger.info("");
  logger.info("╔═══════════════════════════════════════════════════════╗");
  logger.info(`║ ${emoji} Onboarding Complete! ${emoji} ║`);
  logger.info("╚═══════════════════════════════════════════════════════╝");
  logger.info("");
  logger.info(` Squad: ${squadName}`);

  logger.info(` Template: ${template}`);
  logger.info(` Assistant: ${name} ${emoji}`);
  logger.info("");
  logger.info("Next steps:");
  logger.info(`    milimo assistant start    # Talk to ${name}`);
  logger.info("    milimo warroom            # Open the War Room");
  logger.info("    milimo squad status       # View squad configuration");
  if (!solo) {
    logger.info("");
    logger.info("For mesh setup:");
    logger.info("    Share the mesh secret with squad members");
    logger.info(`    Each member runs: milimo onboard --squad ${squadName}`);
  }
  logger.info("");
  logger.info("The milimo never stops. Work. Without working.");
  logger.info("");
}

export async function cliOnboardStatus(logger: PluginLogger): Promise<void> {
  const config = loadOnboardConfig();

  if (!config) {
    logger.info("");
    logger.info("No Milimo configuration found.");
    logger.info("");
    logger.info("Run the onboard command to set up:");
    logger.info("    milimo onboard");
    logger.info("");
    return;
  }

  const assistant = config.assistant;
  const assistantLine = assistant
    ? `${assistant.name} ${assistant.emoji} (${assistant.creature} · ${assistant.vibe})`
    : "Not configured";

  logger.info("");
  logger.info("Milimo Configuration:");
  logger.info(`    Squad: ${config.squadName}`);
  logger.info(`    Template: ${config.template}`);
  logger.info(`    Active claws: ${(config.activeClaws || []).join(", ")}`);
  logger.info(`    Mode: ${config.solo ? "Solo" : "Mesh"}`);
  logger.info(`    Operator: ${config.operatorName}`);
  logger.info(`    Assistant: ${assistantLine}`);
  logger.info(`    War Room: ${config.warRoomMode}`);
  logger.info(`    Onboarded: ${config.onboardedAt}`);
  logger.info("");

  if (!config.solo) {
    logger.info("Mesh Members:");
    for (const member of config.meshMembers) {
      logger.info(`    - ${member}`);
    }
    logger.info("");
  }

  logger.info("To reconfigure, run: milimo onboard");
  logger.info("");
}
