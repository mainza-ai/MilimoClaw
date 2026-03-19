// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * CLI registrar for `openclaw milimo <subcommand>`.
 *
 * Wires commander.js subcommands for squad management, blueprint operations,
 * and claw deployment.
 */

import type { OpenClawPluginApi, PluginCliContext } from "./index.js";
import { getPluginConfig } from "./index.js";
import { cliOnboard, cliOnboardStatus } from "./commands/onboard.js";
import { cliInit } from "./commands/init.js";
import { cliSquadStatus, cliSquadFinalsMode, cliSquadResume } from "./commands/squad.js";
import {
  cliBlueprintFork,
  cliBlueprintDiff,
  cliBlueprintPublish,
  cliBlueprintRollback,
  cliBlueprintList,
  cliBlueprintSearch,
  cliBlueprintMerge,
  cliBlueprintInfo,
} from "./commands/blueprint.js";
import { cliWarRoom } from "./commands/warroom.js";

export function registerCliCommands(ctx: PluginCliContext, api: OpenClawPluginApi): void {
  const { program, logger } = ctx;
  const pluginConfig = getPluginConfig(api);

  const milimo = program.command("milimo").description("Milimo Claw squad management");

  // ── openclaw milimo onboard ───────────────────────────────────────
  milimo
    .command("onboard")
    .description("Interactive setup: configure squad, template, role, and War Room")
    .option("--squad <name>", "Squad name")
    .option("--role <role>", "Claw role: content, ops, analytics, finance, build")
    .option("--template <template>", "Squad template (e.g., solo-founder, content-agency)")
    .option("--solo", "Initialize as a solo operator (no mesh)", false)
    .option("--operator <name>", "Operator name")
    .option(
      "--war-room-mode <mode>",
      "War Room mode: full, minimal, disabled",
      "full" as const,
    )
    .action(async (opts: {
      squad?: string;
      role?: string;
      template?: string;
      solo: boolean;
      operator?: string;
      warRoomMode: "full" | "minimal" | "disabled";
    }) => {
      await cliOnboard({ ...opts, logger, pluginConfig });
    });

  // ── openclaw milimo init ──────────────────────────────────────────
  milimo
    .command("init")
    .description("Initialize a new squad or join an existing mesh")
    .option("--squad <name>", "Squad name")
    .option("--role <role>", "Claw role: content, ops, analytics, finance, build")
    .option("--template <template>", "Squad template to use (e.g., content-agency, design-studio)")
    .option("--solo", "Initialize as a solo operator (no mesh)", false)
    .action(async (opts: { squad?: string; role?: string; template?: string; solo: boolean }) => {
      await cliInit({ ...opts, logger, pluginConfig });
    });

  // ── openclaw milimo squad ─────────────────────────────────────────
  const squad = milimo.command("squad").description("Squad lifecycle management");

  squad
    .command("status")
    .description("Show squad topology, claw health, and mesh state")
    .option("--json", "Output as JSON", false)
    .action(async (opts: { json: boolean }) => {
      await cliSquadStatus({ json: opts.json, logger, pluginConfig });
    });

  squad
    .command("onboard-status")
    .description("Show current onboarding configuration")
    .action(async () => {
      await cliOnboardStatus(logger);
    });

  squad
    .command("finals-mode")
    .description("Activate Finals Mode — all claws enter maintenance configuration")
    .option("--duration <duration>", "Duration (e.g., 2weeks, 10days)", "2weeks")
    .option("--resume-date <date>", "Scheduled resume date (ISO format)")
    .action(async (opts: { duration: string; resumeDate?: string }) => {
      await cliSquadFinalsMode({ ...opts, logger, pluginConfig });
    });

  squad
    .command("resume")
    .description("Resume from Finals Mode — restore all claw policies")
    .action(async () => {
      await cliSquadResume({ logger, pluginConfig });
    });

  // ── openclaw milimo blueprint ─────────────────────────────────────
  const blueprint = milimo.command("blueprint").description("Blueprint operations");

  blueprint
    .command("list")
    .description("List available role blueprints and templates")
    .option("--json", "Output as JSON", false)
    .action(async (opts: { json: boolean }) => {
      await cliBlueprintList({ json: opts.json, logger, pluginConfig });
    });

  blueprint
    .command("fork <source>")
    .description("Fork a public blueprint as your starting point")
    .option("--into <name>", "Name for the forked blueprint")
    .action(async (source: string, opts: { into?: string }) => {
      await cliBlueprintFork({ source, into: opts.into, logger, pluginConfig });
    });

  blueprint
    .command("diff <versionA> <versionB>")
    .description("Compare two blueprint versions")
    .action(async (versionA: string, versionB: string) => {
      await cliBlueprintDiff({ versionA, versionB, logger, pluginConfig });
    });

  blueprint
    .command("publish")
    .description("Export your evolved blueprint to the marketplace")
    .option("--name <name>", "Display name for the listing")
    .option("--price <price>", "Price (e.g., 0.05eth, $25, free)", "free")
    .action(async (opts: { name?: string; price: string }) => {
      await cliBlueprintPublish({ ...opts, logger, pluginConfig });
    });

  blueprint
    .command("rollback")
    .description("Roll back to a previous blueprint version")
    .option("--to <version>", "Version to roll back to")
    .option("--reason <reason>", "Reason for rollback")
    .action(async (opts: { to?: string; reason?: string }) => {
      await cliBlueprintRollback({ ...opts, logger, pluginConfig });
    });

  blueprint
    .command("search")
    .description("Search the blueprint marketplace")
    .option("--query <query>", "Search query")
    .option("--category <category>", "Filter by business category")
    .action(async (opts: { query?: string; category?: string }) => {
      await cliBlueprintSearch({ ...opts, logger, pluginConfig });
    });

  blueprint
    .command("info <blueprintId>")
    .description("Show detailed information for a marketplace blueprint")
    .action(async (blueprintId: string) => {
      await cliBlueprintInfo({ blueprintId, logger, pluginConfig });
    });

  blueprint
    .command("merge <incoming>")
    .description("Merge an external blueprint into your local workspace")
    .action(async (incoming: string) => {
      await cliBlueprintMerge({ incoming, logger, pluginConfig });
    });

  // ── openclaw milimo warroom ───────────────────────────────────────
  milimo
    .command("warroom")
    .description("Launch the War Room interactive operator dashboard")
    .option("-o, --operator <name>", "Override operator ID", "local-operator")
    .action(async (opts: { operator: string }) => {
      await cliWarRoom({ operator: opts.operator, logger, pluginConfig });
    });
}
