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

interface InitOptions {
  squad?: string;
  role?: string;
  template?: string;
  solo: boolean;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

/** State file written after successful initialization. */
interface MilimoState {
  squadName: string;
  clawRole: ClawRole;
  template: string;
  solo: boolean;
  meshMembers: string[];
  initializedAt: string;
  blueprintVersion: string;
}

function getMilimoStateDir(): string {
  const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
  return path.join(home, ".milimo");
}

function getMilimoStatePath(): string {
  return path.join(getMilimoStateDir(), "state.json");
}

export function loadMilimoState(): MilimoState | null {
  const statePath = getMilimoStatePath();
  if (!fs.existsSync(statePath)) {
    return null;
  }
  try {
    const raw = fs.readFileSync(statePath, "utf-8");
    return JSON.parse(raw) as MilimoState;
  } catch {
    return null;
  }
}

function saveMilimoState(state: MilimoState): void {
  const dir = getMilimoStateDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(getMilimoStatePath(), JSON.stringify(state, null, 2), { mode: 0o600 });
}

/** List available templates from the blueprint directory. */
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

/** List available role blueprints from the blueprint directory. */
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

  // Check if already initialized
  const existingState = loadMilimoState();
  if (existingState) {
    logger.warn(
      `Already initialized as ${existingState.clawRole} claw in squad "${existingState.squadName}".`,
    );
    logger.info("To reinitialize, remove ~/.milimo/state.json first.");
    return;
  }

  logger.info("");
  logger.info("  ╔═══════════════════════════════════════════════════════╗");
  logger.info("  ║          🦀  MILIMO CLAW — Squad Init  🦀            ║");
  logger.info("  ╚═══════════════════════════════════════════════════════╝");
  logger.info("");

  // Validate squad name
  const squadName = opts.squad ?? pluginConfig.squadName;
  if (!squadName) {
    logger.error("Squad name is required. Use --squad <name> or set squadName in plugin config.");
    logger.info("");
    logger.info("  Example:");
    logger.info('    openclaw milimo init --squad "my-squad" --role content');
    return;
  }

  // Validate role
  const roleStr = opts.role ?? pluginConfig.clawRole;
  if (!roleStr) {
    logger.error("Claw role is required. Use --role <role>.");
    logger.info("");
    logger.info("  Available roles:");
    for (const role of CLAW_ROLES) {
      const desc = getRoleDescription(role);
      logger.info(`    ${role.padEnd(12)} ${desc}`);
    }
    return;
  }

  if (!CLAW_ROLES.includes(roleStr as ClawRole)) {
    logger.error(`Invalid role "${roleStr}". Must be one of: ${CLAW_ROLES.join(", ")}`);
    return;
  }
  const clawRole = roleStr as ClawRole;

  // Check template
  const template = opts.template ?? "custom";
  const blueprintDir = pluginConfig.blueprintDir;

  if (template !== "custom") {
    const availableTemplates = listTemplates(blueprintDir);
    if (availableTemplates.length > 0 && !availableTemplates.includes(template)) {
      logger.error(`Template "${template}" not found.`);
      logger.info(`  Available: ${availableTemplates.join(", ")}`);
      return;
    }
  }

  // Check if role blueprint exists
  const availableRoles = listRoles(blueprintDir);
  if (availableRoles.length > 0 && !availableRoles.includes(clawRole)) {
    logger.warn(
      `Role blueprint "${clawRole}-claw.yaml" not found in ${blueprintDir}/roles/. Using base configuration.`,
    );
  }

  // Initialize
  logger.info(`  Squad:     ${squadName}`);
  logger.info(`  Role:      ${clawRole}`);
  logger.info(`  Template:  ${template}`);
  logger.info(`  Mode:      ${opts.solo ? "Solo" : "Mesh"}`);
  logger.info("");

  // Create Milimo state directory structure
  const stateDir = getMilimoStateDir();
  const dirs = [
    path.join(stateDir, "blueprints"),
    path.join(stateDir, "audit"),
    path.join(stateDir, "mesh"),
    path.join(stateDir, "evolution"),
  ];
  for (const dir of dirs) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // Save state
  const state: MilimoState = {
    squadName,
    clawRole,
    template,
    solo: opts.solo,
    meshMembers: opts.solo ? [clawRole] : [],
    initializedAt: new Date().toISOString(),
    blueprintVersion: "0.1.0",
  };
  saveMilimoState(state);

  logger.info("  ✓ State directory created (~/.milimo/)");
  logger.info("  ✓ Blueprint directories initialized");
  logger.info("  ✓ Claw configuration saved");
  logger.info("");

  if (opts.solo) {
    logger.info("  Solo mode: claw is ready. No mesh formation needed.");
  } else {
    logger.info("  Next steps:");
    logger.info("    1. Have each squad member run: openclaw milimo init --squad");
    logger.info(`       "${squadName}" --role <their-role>`);
    logger.info("    2. Run: openclaw milimo squad status");
    logger.info("       to verify the mesh topology");
  }

  logger.info("");
  logger.info("  Run 'openclaw milimo squad status' to see your configuration.");
  logger.info("");
}

function getRoleDescription(role: ClawRole): string {
  const descriptions: Record<ClawRole, string> = {
    content: "Creative output — posts, copy, campaigns, brand voice",
    ops: "Client lifecycle — intake, scoping, delivery, follow-up",
    analytics: "Intelligence layer — performance, trends, opportunities",
    finance: "Financial ops — invoicing, pricing, margin tracking",
    build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
  };
  return descriptions[role];
}
