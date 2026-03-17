// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `openclaw milimo blueprint` — Blueprint operations.
 *
 * Subcommands: list, fork, diff, publish, rollback.
 * Phase 0 implements list and stubs for fork/diff/publish/rollback.
 * Full marketplace integration arrives in Phase 3.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { PluginLogger, MilimoConfig } from "../index.js";
import { CLAW_ROLES } from "../index.js";
import { loadMilimoState } from "./init.js";

interface BlueprintListOptions {
  json: boolean;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface BlueprintForkOptions {
  source: string;
  into?: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface BlueprintDiffOptions {
  versionA: string;
  versionB: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface BlueprintPublishOptions {
  name?: string;
  price: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface BlueprintRollbackOptions {
  to?: string;
  reason?: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

/** Blueprint metadata discovered from the filesystem. */
interface BlueprintInfo {
  name: string;
  type: "role" | "template";
  file: string;
  description: string;
}

function discoverBlueprints(blueprintDir: string): BlueprintInfo[] {
  const blueprints: BlueprintInfo[] = [];

  // Discover role blueprints
  const rolesDir = path.join(blueprintDir, "roles");
  if (fs.existsSync(rolesDir)) {
    for (const file of fs.readdirSync(rolesDir)) {
      if (!file.endsWith(".yaml") && !file.endsWith(".yml")) continue;
      const roleName = file.replace(/-claw\.ya?ml$/, "");
      blueprints.push({
        name: `${roleName}-claw`,
        type: "role",
        file: path.join(rolesDir, file),
        description: getRoleBlurb(roleName),
      });
    }
  }

  // Discover templates
  const templatesDir = path.join(blueprintDir, "templates");
  if (fs.existsSync(templatesDir)) {
    for (const file of fs.readdirSync(templatesDir)) {
      if (!file.endsWith(".yaml") && !file.endsWith(".yml")) continue;
      const templateName = file.replace(/\.ya?ml$/, "");
      blueprints.push({
        name: templateName,
        type: "template",
        file: path.join(templatesDir, file),
        description: getTemplateBlurb(templateName),
      });
    }
  }

  return blueprints;
}

// ── Blueprint List ────────────────────────────────────────────────────

export async function cliBlueprintList(opts: BlueprintListOptions): Promise<void> {
  const { logger, pluginConfig } = opts;
  const blueprintDir = pluginConfig.blueprintDir;
  const blueprints = discoverBlueprints(blueprintDir);

  if (opts.json) {
    logger.info(JSON.stringify(blueprints, null, 2));
    return;
  }

  logger.info("");
  logger.info("  ┌─────────────────────────────────────────────────────┐");
  logger.info("  │           🦀  AVAILABLE BLUEPRINTS  🦀              │");
  logger.info("  └─────────────────────────────────────────────────────┘");
  logger.info("");

  // List roles
  const roles = blueprints.filter((b) => b.type === "role");
  if (roles.length > 0) {
    logger.info("  Claw Roles:");
    for (const bp of roles) {
      logger.info(`    ${bp.name.padEnd(20)} ${bp.description}`);
    }
  } else {
    logger.info("  Claw Roles:");
    logger.info("    (built-in roles available)");
    for (const role of CLAW_ROLES) {
      logger.info(`    ${(role + "-claw").padEnd(20)} ${getRoleBlurb(role)}`);
    }
  }
  logger.info("");

  // List templates
  const templates = blueprints.filter((b) => b.type === "template");
  if (templates.length > 0) {
    logger.info("  Squad Templates:");
    for (const bp of templates) {
      logger.info(`    ${bp.name.padEnd(20)} ${bp.description}`);
    }
  } else {
    logger.info("  Squad Templates:");
    logger.info("    (no templates deployed yet — coming in Phase 0.6)");
  }

  logger.info("");
  logger.info(`  Blueprint directory: ${blueprintDir}`);
  logger.info("");
}

// ── Blueprint Fork ────────────────────────────────────────────────────

export async function cliBlueprintFork(opts: BlueprintForkOptions): Promise<void> {
  const { logger } = opts;
  const state = loadMilimoState();

  if (!state) {
    logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
    return;
  }

  const targetName = opts.into ?? `${opts.source}-fork`;

  logger.info("");
  logger.info(`  Forking blueprint: ${opts.source}`);
  logger.info(`  Into:              ${targetName}`);
  logger.info("");

  // Phase 0: stub — real forking requires blueprint marketplace (Phase 3)
  const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
  const forkDir = path.join(home, ".milimo", "blueprints", targetName);
  fs.mkdirSync(forkDir, { recursive: true });

  const forkMeta = {
    name: targetName,
    forkedFrom: opts.source,
    forkedAt: new Date().toISOString(),
    version: "0.1.0",
    squad: state.squadName,
  };
  fs.writeFileSync(path.join(forkDir, "fork.json"), JSON.stringify(forkMeta, null, 2));

  logger.info(`  ✓ Fork metadata created at ~/.milimo/blueprints/${targetName}/`);
  logger.info("");
  logger.info("  Note: Full blueprint forking with marketplace integration");
  logger.info("  will be available in Phase 3 (Blueprint Economy).");
  logger.info("");
}

// ── Blueprint Diff ────────────────────────────────────────────────────

export async function cliBlueprintDiff(opts: BlueprintDiffOptions): Promise<void> {
  const { logger } = opts;
  const state = loadMilimoState();

  if (!state) {
    logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
    return;
  }

  logger.info("");
  logger.info(`  Comparing blueprint versions: ${opts.versionA} ↔ ${opts.versionB}`);
  logger.info("");

  // Phase 0: stub — real diffing requires versioned blueprint storage
  logger.info("  Blueprint diff will show:");
  logger.info("    • Tool inventory changes");
  logger.info("    • Policy modifications");
  logger.info("    • Learned prior deltas");
  logger.info("    • Configuration drift");
  logger.info("");
  logger.info("  Note: Full blueprint diffing will be available once");
  logger.info("  blueprint versioning is implemented (Phase 1).");
  logger.info("");
}

// ── Blueprint Publish ─────────────────────────────────────────────────

export async function cliBlueprintPublish(opts: BlueprintPublishOptions): Promise<void> {
  const { logger } = opts;
  const state = loadMilimoState();

  if (!state) {
    logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
    return;
  }

  const displayName = opts.name ?? `${state.squadName}-${state.clawRole}-blueprint`;

  logger.info("");
  logger.info("  📦 Blueprint Publish (Preview)");
  logger.info("");
  logger.info(`  Name:     ${displayName}`);
  logger.info(`  Price:    ${opts.price}`);
  logger.info(`  Squad:    ${state.squadName}`);
  logger.info(`  Role:     ${state.clawRole}`);
  logger.info(`  Version:  v${state.blueprintVersion}`);
  logger.info("");
  logger.info("  Note: Blueprint Marketplace launches in Phase 3.");
  logger.info("  Your blueprint will be publishable once the marketplace is live.");
  logger.info("");
}

// ── Blueprint Rollback ────────────────────────────────────────────────

export async function cliBlueprintRollback(opts: BlueprintRollbackOptions): Promise<void> {
  const { logger } = opts;
  const state = loadMilimoState();

  if (!state) {
    logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
    return;
  }

  if (!opts.to) {
    logger.error("--to <version> is required for rollback.");
    return;
  }

  logger.info("");
  logger.info(`  Rolling back blueprint to v${opts.to}`);
  if (opts.reason) {
    logger.info(`  Reason: ${opts.reason}`);
  }
  logger.info("");

  // Phase 0: stub — real rollback requires versioned blueprint history
  logger.info("  Note: Full blueprint rollback requires version history.");
  logger.info("  This feature will be fully functional in Phase 1.");
  logger.info("");
}

// ── Helpers ───────────────────────────────────────────────────────────

function getRoleBlurb(role: string): string {
  const blurbs: Record<string, string> = {
    content: "Creative output — posts, copy, brand voice",
    ops: "Client lifecycle — intake, delivery, follow-up",
    analytics: "Intelligence — performance, trends, signals",
    finance: "Financial ops — invoicing, pricing, margins",
    build: "Engineering — code, PRs, deploys, monitoring",
  };
  return blurbs[role] ?? "Custom claw role";
}

function getTemplateBlurb(template: string): string {
  const blurbs: Record<string, string> = {
    "content-agency": "Content + Ops + Analytics (social media agency)",
    "design-studio": "Content + Ops + Finance (design services)",
    "ai-micro-saas": "Build + Ops + Analytics + Finance (AI product)",
    "campus-ai-tool": "Build + Content + Ops (campus utility)",
  };
  return blurbs[template] ?? "Custom squad template";
}
