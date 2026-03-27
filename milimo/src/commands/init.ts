// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `openclaw milimo init` — Squad initialization wizard.
 *
 * Phase 0.1 scope: template selection, role assignment, and local blueprint
 * deployment. Full mesh formation (0.4) and onboarding wizard (0.6) extend
 * this later.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { PluginLogger, MilimoConfig, ClawRole } from "../index.js";
import { CLAW_ROLES } from "../index.js";
import { ConfigManager, type MilimoConfig as FullMilimoConfig, getActiveClawsForTemplate } from "../onboard/config.js";
import { assistantSetup } from "./assistant.js";

interface InitOptions {
  squad?: string;
  role?: string;
  template?: string;
  solo: boolean;
  assistantName?: string;
  assistantCreature?: string;
  assistantVibe?: string;
  assistantEmoji?: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

function listTemplates(blueprintDir: string): string[] {
  const templatesDir = path.join(blueprintDir, "templates");
  if (!fs.existsSync(templatesDir)) {
    return [];
  }
  return fs
    .readdirSync(templatesDir)
    .filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"))
    .map((f) => f.replace(/\.ya?ml$/, ""));
}

function listRoles(blueprintDir: string): string[] {
  const rolesDir = path.join(blueprintDir, "roles");
  if (!fs.existsSync(rolesDir)) {
    return [];
  }
  return fs
    .readdirSync(rolesDir)
    .filter((f) => f.endsWith(".yaml") || f.endsWith(".yml"))
    .map((f) => f.replace(/-claw\.ya?ml$/, "").replace(/\.ya?ml$/, ""));
}

export async function cliInit(opts: InitOptions): Promise<void> {
  const { logger, pluginConfig } = opts;

  ConfigManager.migrate();

  const existingConfig = ConfigManager.load();
  if (existingConfig && existingConfig.squadName) {
    logger.warn(
      `Already initialized as ${existingConfig.clawRole} claw in squad "${existingConfig.squadName}".`,
    );
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
    for (const role of CLAW_ROLES) {
      const desc = getRoleDescription(role);
      logger.info(` ${role.padEnd(12)} ${desc}`);
    }
    return;
  }

  if (!CLAW_ROLES.includes(roleStr as ClawRole)) {
    logger.error(`Invalid role "${roleStr}". Must be one of: ${CLAW_ROLES.join(", ")}`);
    return;
  }
  const clawRole = roleStr as ClawRole;

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
    logger.warn(
      `Role blueprint "${clawRole}-claw.yaml" not found in ${blueprintDir}/roles/. Using base configuration.`,
    );
  }

  logger.info(` Squad: ${squadName}`);
  logger.info(` Role: ${clawRole}`);
  logger.info(` Template: ${template}`);
  logger.info(` Mode: ${opts.solo ? "Solo" : "Mesh"}`);
  logger.info("");

  ConfigManager.ensureDirectories();

  const config: FullMilimoConfig = {
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
    activeClaws: getActiveClawsForTemplate(template),
  };

  ConfigManager.save(config);

  logger.info(" ✓ State directory created (~/.milimo/)");
  logger.info(" ✓ Blueprint directories initialized");
  logger.info(" ✓ Claw configuration saved");
  logger.info("");

  // Run assistant setup automatically
  logger.info("Configuring squad assistant...");
  try {
    await assistantSetup();
  } catch (err) {
    logger.warn("Assistant setup skipped — run 'milimo assistant setup' manually.");
  }

  if (opts.solo) {
    logger.info(" Solo mode: claw is ready. No mesh formation needed.");
  } else {
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

function getRoleDescription(role: ClawRole): string {
  const descriptions: Record<ClawRole, string> = {
    content: "Creative output — posts, copy, campaigns, brand voice",
    ops: "Client lifecycle — intake, scoping, delivery, follow-up",
    analytics: "Intelligence layer — performance, trends, opportunities",
    finance: "Financial ops — invoicing, pricing, margin tracking",
    build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
    solo: "All claws active on this machine (solo mode)",
  };
  return descriptions[role];
}

export function loadMilimoState(): FullMilimoConfig | null {
  return ConfigManager.load();
}

export function saveMilimoState(state: FullMilimoConfig): void {
  ConfigManager.save(state);
}
