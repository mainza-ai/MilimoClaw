// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Handler for the /milimo slash command (chat interface).
 *
 * Supports subcommands:
 *   /milimo status   - show squad and claw status
 *   /milimo role     - show current claw role details
 *   /milimo finals   - show finals mode status
 *   /milimo          - show help
 */

import type { PluginCommandContext, PluginCommandResult, OpenClawPluginApi } from "../index.js";
import { getPluginConfig, CLAW_ROLES } from "../index.js";
import { loadMilimoState } from "./init.js";

export function handleSlashCommand(
  ctx: PluginCommandContext,
  api: OpenClawPluginApi,
): PluginCommandResult {
  const subcommand = ctx.args?.trim().split(/\s+/)[0] ?? "";

  switch (subcommand) {
    case "status":
      return slashStatus(api);
    case "role":
      return slashRole(api);
    case "finals":
      return slashFinals();
    default:
      return slashHelp();
  }
}

function slashHelp(): PluginCommandResult {
  return {
    text: [
      "**🦀 Milimo Claw**",
      "",
      "Usage: `/milimo <subcommand>`",
      "",
      "Subcommands:",
      "  `status`  - Show squad and claw status",
      "  `role`    - Show your claw role details",
      "  `finals`  - Show Finals Mode status",
      "",
      "For full management use the CLI:",
      "  `openclaw milimo init`           - Initialize squad",
      "  `openclaw milimo squad status`   - Squad topology",
      "  `openclaw milimo squad finals-mode` - Activate Finals Mode",
      "  `openclaw milimo blueprint list` - List blueprints",
    ].join("\n"),
  };
}

function slashStatus(api: OpenClawPluginApi): PluginCommandResult {
  const config = getPluginConfig(api);
  const state = loadMilimoState();

  if (!state) {
    return {
      text: [
        "**🦀 Milimo Claw**: Not initialized yet.",
        "",
        "Run `openclaw milimo init --squad <name> --role <role>` to get started.",
        "",
        "Available roles: " + CLAW_ROLES.join(", "),
      ].join("\n"),
    };
  }

  const lines = [
    "**🦀 Milimo Claw Status**",
    "",
    `**Squad:** ${state.squadName}`,
    `**Role:** ${state.clawRole}`,
    `**Template:** ${state.template}`,
    `**Mode:** ${state.solo ? "Solo" : "Mesh"}`,
    `**Blueprint:** v${state.blueprintVersion}`,
    `**Initialized:** ${state.initializedAt}`,
  ];

  if (!state.solo && state.meshMembers.length > 0) {
    lines.push("", "**Mesh Members:**");
    for (const member of state.meshMembers) {
      lines.push(`  • ${member}`);
    }
  }

  if (config.squadName && config.squadName !== state.squadName) {
    lines.push("", `⚠️ Config squad name (${config.squadName}) differs from state.`);
  }

  return { text: lines.join("\n") };
}

function slashRole(api: OpenClawPluginApi): PluginCommandResult {
  const state = loadMilimoState();

  if (!state) {
    return {
      text: "**🦀 Milimo Claw**: Not initialized. Run `openclaw milimo init` first.",
    };
  }

  const roleDetails: Record<string, string[]> = {
    content: [
      "**🎨 Content Claw**",
      "",
      "**Mount:** `/sandbox/content`",
      "**Responsibility:** All creative output — posts, copy, campaigns, brand voice",
      "",
      "**Inference Routing:**",
      "  • Public drafts → Cloud Nemotron 120B",
      "  • Internal ideation → Local NIM",
      "  • Trend research → Cloud Nemotron 120B",
      "",
      "**Inter-Claw:**",
      "  • Receives briefs from Ops",
      "  • Queries Analytics for performance data",
      "  • Sends drafts to War Room for approval",
    ],
    ops: [
      "**📋 Ops Claw**",
      "",
      "**Mount:** `/sandbox/clients`",
      "**Responsibility:** Client lifecycle — intake, scoping, delivery, follow-up",
      "",
      "**Inference Routing:**",
      "  • Client comms → Cloud Nemotron 120B",
      "  • Internal summaries → Local NIM",
      "  • Contract review → Local NIM",
      "",
      "**Inter-Claw:**",
      "  • Sends briefs to Content/Build",
      "  • Queries Finance for pricing",
      "  • Receives completion signals",
    ],
    analytics: [
      "**📊 Analytics Claw**",
      "",
      "**Mount:** `/sandbox/analytics`",
      "**Responsibility:** Intelligence — performance, trends, opportunities",
      "",
      "**Inference Routing:**",
      "  • Market analysis → Cloud Nemotron 120B",
      "  • Internal synthesis → Local NIM",
      "  • Predictive models → Local NIM",
      "",
      "**Inter-Claw:**",
      "  • Publishes weekly intelligence reports",
      "  • Responds to Content/Build queries",
      "  • Sends revenue alerts to Finance",
    ],
    finance: [
      "**💰 Finance Claw**",
      "",
      "**Mount:** `/sandbox/finance`",
      "**Responsibility:** Financial ops — invoicing, pricing, margins",
      "",
      "**Inference Routing:**",
      "  • ⚠️ ALL data → Local NIM only (no cloud)",
      "",
      "**Inter-Claw:**",
      "  • Responds to Ops pricing queries",
      "  • Sends overdue payment alerts",
      "  • Provides revenue summaries (totals only)",
    ],
    build: [
      "**🔧 Build Claw** *(Tech Squads)*",
      "",
      "**Mount:** `/sandbox/build`",
      "**Responsibility:** Engineering — code, PRs, deploys, monitoring",
      "",
      "**Inference Routing:**",
      "  • Source code → Local NIM (always)",
      "  • Boilerplate/docs → Cloud Nemotron 120B",
      "  • Production logs → Local NIM",
      "",
      "**Inter-Claw:**",
      "  • Receives feature briefs from Ops",
      "  • Queries Analytics for user behavior",
      "  • Sends deploy signals to Ops",
      "  • Sends shipping summaries to Content",
    ],
  };

  const details = roleDetails[state.clawRole];
  if (!details) {
    return { text: `Unknown role: ${state.clawRole}` };
  }

  return { text: details.join("\n") };
}

function slashFinals(): PluginCommandResult {
  // Check finals mode state from disk
  const fs = require("node:fs") as typeof import("node:fs");
  const fpath = require("node:path") as typeof import("node:path");
  const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
  const finalsPath = fpath.join(home, ".milimo", "finals-mode.json");

  if (!fs.existsSync(finalsPath)) {
    return {
      text: [
        "**📚 Finals Mode:** Inactive",
        "",
        "To activate:",
        "```",
        "openclaw milimo squad finals-mode --duration 2weeks",
        "```",
      ].join("\n"),
    };
  }

  try {
    const raw = fs.readFileSync(finalsPath, "utf-8");
    const state = JSON.parse(raw) as { active: boolean; activatedAt: string; duration: string; resumeDate: string | null };

    if (!state.active) {
      return {
        text: "**📚 Finals Mode:** Inactive (previously active, now resumed)",
      };
    }

    return {
      text: [
        "**📚 Finals Mode:** ⚠️ ACTIVE",
        "",
        `**Since:** ${state.activatedAt}`,
        `**Duration:** ${state.duration}`,
        state.resumeDate ? `**Scheduled Resume:** ${state.resumeDate}` : null,
        "",
        "To resume operations:",
        "```",
        "openclaw milimo squad resume",
        "```",
      ]
        .filter(Boolean)
        .join("\n"),
    };
  } catch {
    return { text: "**📚 Finals Mode:** Unable to read state" };
  }
}
