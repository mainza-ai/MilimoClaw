// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Milimo Claw — Multi-Agent Autonomous Hustle Platform
 *
 * OpenClaw plugin that extends NemoClaw with squad mesh coordination,
 * role-specific claw blueprints, privacy routing, and the War Room TUI.
 *
 * Uses the real OpenClaw plugin API. Types are imported from the NemoClaw
 * plugin's type definitions since they mirror the OpenClaw SDK interfaces.
 */

import type { Command } from "commander";
import { registerCliCommands } from "./cli.js";
import { handleSlashCommand } from "./commands/slash.js";
import { checkFinalsModeAutoResume } from "./commands/squad.js";
import { loadOnboardConfig, type MilimoOnboardConfig } from "./onboard/config.js";
import { formatRoleDisplay } from "./commands/onboard.js";

// ---------------------------------------------------------------------------
// OpenClaw Plugin SDK compatible types (mirrors openclaw/plugin-sdk)
// Duplicated from NemoClaw — both plugins must be independently loadable.
// ---------------------------------------------------------------------------

/** Subset of OpenClawConfig that we actually read. */
export interface OpenClawConfig {
  [key: string]: unknown;
}

/** Logger provided by the plugin host. */
export interface PluginLogger {
  info(message: string): void;
  warn(message: string): void;
  error(message: string): void;
  debug(message: string): void;
}

/** Context passed to slash-command handlers. */
export interface PluginCommandContext {
  senderId?: string;
  channel: string;
  isAuthorizedSender: boolean;
  args?: string;
  commandBody: string;
  config: OpenClawConfig;
  from?: string;
  to?: string;
  accountId?: string;
}

/** Return value from a slash-command handler. */
export interface PluginCommandResult {
  text?: string;
  mediaUrl?: string;
  mediaUrls?: string[];
}

/** Registration shape for a slash command. */
export interface PluginCommandDefinition {
  name: string;
  description: string;
  acceptsArgs?: boolean;
  requireAuth?: boolean;
  handler: (ctx: PluginCommandContext) => PluginCommandResult | Promise<PluginCommandResult>;
}

/** Context passed to the CLI registrar callback. */
export interface PluginCliContext {
  program: Command;
  config: OpenClawConfig;
  workspaceDir?: string;
  logger: PluginLogger;
}

/** CLI registrar callback type. */
export type PluginCliRegistrar = (ctx: PluginCliContext) => void | Promise<void>;

/**
 * The API object injected into the plugin's register function by the OpenClaw
 * host. Only the methods we actually call are listed here.
 */
export interface OpenClawPluginApi {
  id: string;
  name: string;
  version?: string;
  config: OpenClawConfig;
  pluginConfig?: Record<string, unknown>;
  logger: PluginLogger;
  registerCommand: (command: PluginCommandDefinition) => void;
  registerCli: (registrar: PluginCliRegistrar, opts?: { commands?: string[] }) => void;
  resolvePath: (input: string) => string;
  on: (hookName: string, handler: (...args: unknown[]) => void) => void;
}

// ---------------------------------------------------------------------------
// Milimo-specific config (read from pluginConfig in openclaw.plugin.json)
// ---------------------------------------------------------------------------

/** Valid claw role identifiers. "solo" indicates all claws run on one machine. */
export type ClawRole = "content" | "ops" | "analytics" | "finance" | "build" | "assistant" | "solo";

/** All valid claw roles (excluding "solo" which is a mode indicator). */
export const CLAW_ROLES: ClawRole[] = [
  "content",
  "ops",
  "analytics",
  "finance",
  "build",
  "assistant",
];

/** Milimo plugin configuration. */
export interface MilimoConfig {
  squadName: string;
  clawRole: ClawRole | "";
  meshSecret: string;
  blueprintDir: string;
  serverUrl?: string;
}

const DEFAULT_PLUGIN_CONFIG: MilimoConfig = {
  squadName: "",
  clawRole: "",
  meshSecret: "",
  blueprintDir: "/opt/milimo-blueprint",
};

export function getPluginConfig(api: OpenClawPluginApi): MilimoConfig {
  const raw = api.pluginConfig ?? {};
  return {
    squadName:
      typeof raw["squadName"] === "string" ? raw["squadName"] : DEFAULT_PLUGIN_CONFIG.squadName,
    clawRole:
      typeof raw["clawRole"] === "string" && isValidClawRole(raw["clawRole"])
        ? raw["clawRole"]
        : DEFAULT_PLUGIN_CONFIG.clawRole,
    meshSecret:
      typeof raw["meshSecret"] === "string" ? raw["meshSecret"] : DEFAULT_PLUGIN_CONFIG.meshSecret,
    blueprintDir:
      typeof raw["blueprintDir"] === "string"
        ? raw["blueprintDir"]
        : DEFAULT_PLUGIN_CONFIG.blueprintDir,
  };
}

function isValidClawRole(value: string): value is ClawRole | "" {
  return value === "" || CLAW_ROLES.includes(value as ClawRole) || value === "solo";
}

// ---------------------------------------------------------------------------
// Plugin entry point
// ---------------------------------------------------------------------------

let _bannerDisplayed = false;

export default function register(api: OpenClawPluginApi): void {
  // 1. Register /milimo slash command (chat interface)
  api.registerCommand({
    name: "milimo",
    description: "Milimo Claw squad management (status, roles, mesh).",
    acceptsArgs: true,
    handler: (ctx) => handleSlashCommand(ctx, api),
  });

  // 2. Register `openclaw milimo` CLI subcommands (commander.js)
  api.registerCli(
    (cliCtx) => {
      registerCliCommands(cliCtx, api);
    },
    { commands: ["milimo"] },
  );

  // 3. Load onboarding config for banner display
  const onboardConfig = loadOnboardConfig();
  const config = getPluginConfig(api);

  // 4. Auto-resume check for Finals mode
  checkFinalsModeAutoResume(api.logger);

  // 5. Display registration banner with onboarding status (once per process)
  if (!_bannerDisplayed) {
    _bannerDisplayed = true;
    const roleDisplay =
      formatRoleDisplay(
        (onboardConfig ?? { clawRole: config.clawRole, activeClaws: [] }) as MilimoOnboardConfig,
      ) || "not assigned";
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
}
