"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerCliCommands = registerCliCommands;
const index_js_1 = require("./index.js");
const onboard_js_1 = require("./commands/onboard.js");
const init_js_1 = require("./commands/init.js");
const squad_js_1 = require("./commands/squad.js");
const blueprint_js_1 = require("./commands/blueprint.js");
const warroom_js_1 = require("./commands/warroom.js");
const payment_js_1 = require("./commands/payment.js");
const verify_js_1 = require("./commands/verify.js");
const badge_js_1 = require("./commands/badge.js");
const action_js_1 = require("./commands/action.js");
const logs_js_1 = require("./commands/logs.js");
const assistant_js_1 = require("./commands/assistant.js");
const channels_js_1 = require("./commands/channels.js");
function registerCliCommands(ctx, api) {
    const { program, logger } = ctx;
    const pluginConfig = (0, index_js_1.getPluginConfig)(api);
    const milimo = program.command("milimo").description("Milimo Claw squad management");
    // ── openclaw milimo onboard ───────────────────────────────────────
    milimo
        .command("onboard")
        .description("Interactive setup: configure squad, template, role, and War Room")
        .option("--squad <name>", "Squad name")
        .option("--role <role>", "Claw role: content, ops, analytics, finance, build, assistant")
        .option("--template <template>", "Squad template (e.g., solo-founder, content-agency)")
        .option("--solo", "Initialize as a solo operator (no mesh)", false)
        .option("--operator <name>", "Operator name")
        .option("--no-sandbox", "Skip automatic NemoClaw sandbox creation", false)
        .option("--war-room-mode <mode>", "War Room mode: full, minimal, disabled", "full")
        .action(async (opts) => {
        await (0, onboard_js_1.cliOnboard)({ ...opts, logger, pluginConfig });
    });
    // ── openclaw milimo init ──────────────────────────────────────────
    milimo
        .command("init")
        .description("Initialize a new squad or join an existing mesh")
        .option("--squad <name>", "Squad name")
        .option("--role <role>", "Claw role: content, ops, analytics, finance, build, assistant")
        .option("--template <template>", "Squad template to use (e.g., content-agency, design-studio)")
        .option("--solo", "Initialize as a solo operator (no mesh)", false)
        .option("--assistant-name <name>", "Assistant name", "Nova")
        .option("--assistant-creature <creature>", "Assistant creature", "a claw")
        .option("--assistant-vibe <vibe>", "Assistant vibe", "sharp and unhurried")
        .option("--assistant-emoji <emoji>", "Assistant emoji", "🦀")
        .action(async (opts) => {
        await (0, init_js_1.cliInit)({ ...opts, logger, pluginConfig });
    });
    // ── openclaw milimo squad ─────────────────────────────────────────
    const squad = milimo.command("squad").description("Squad lifecycle management");
    squad
        .command("status")
        .description("Show squad topology, claw health, and mesh state")
        .option("--json", "Output as JSON", false)
        .action(async (opts) => {
        await (0, squad_js_1.cliSquadStatus)({ json: opts.json, logger, pluginConfig });
    });
    squad
        .command("onboard-status")
        .description("Show current onboarding configuration")
        .action(async () => {
        await (0, onboard_js_1.cliOnboardStatus)(logger);
    });
    squad
        .command("finals-mode")
        .description("Activate Finals Mode — all claws enter maintenance configuration")
        .option("--duration <duration>", "Duration (e.g., 2weeks, 10days)", "2weeks")
        .option("--resume-date <date>", "Scheduled resume date (ISO format)")
        .action(async (opts) => {
        await (0, squad_js_1.cliSquadFinalsMode)({ ...opts, logger, pluginConfig });
    });
    squad
        .command("resume")
        .description("Resume from Finals Mode — restore all claw policies")
        .action(async () => {
        await (0, squad_js_1.cliSquadResume)({ logger, pluginConfig });
    });
    // ── openclaw milimo blueprint ─────────────────────────────────────
    const blueprint = milimo.command("blueprint").description("Blueprint operations");
    blueprint
        .command("list")
        .description("List available role blueprints and templates")
        .option("--json", "Output as JSON", false)
        .action(async (opts) => {
        await (0, blueprint_js_1.cliBlueprintList)({ json: opts.json, logger, pluginConfig });
    });
    blueprint
        .command("fork <source>")
        .description("Fork a public blueprint as your starting point")
        .option("--into <name>", "Name for the forked blueprint")
        .action(async (source, opts) => {
        await (0, blueprint_js_1.cliBlueprintFork)({ source, into: opts.into, logger, pluginConfig });
    });
    blueprint
        .command("diff <versionA> <versionB>")
        .description("Compare two blueprint versions")
        .action(async (versionA, versionB) => {
        await (0, blueprint_js_1.cliBlueprintDiff)({ versionA, versionB, logger, pluginConfig });
    });
    blueprint
        .command("publish")
        .description("Export your evolved blueprint to the marketplace")
        .option("--name <name>", "Display name for the listing")
        .option("--price <price>", "Price (e.g., 0.05eth, $25, free)", "free")
        .action(async (opts) => {
        await (0, blueprint_js_1.cliBlueprintPublish)({ ...opts, logger, pluginConfig });
    });
    blueprint
        .command("rollback")
        .description("Roll back to a previous blueprint version")
        .option("--to <version>", "Version to roll back to")
        .option("--reason <reason>", "Reason for rollback")
        .action(async (opts) => {
        await (0, blueprint_js_1.cliBlueprintRollback)({ ...opts, logger, pluginConfig });
    });
    blueprint
        .command("search")
        .description("Search the blueprint marketplace")
        .option("--query <query>", "Search query")
        .option("--category <category>", "Filter by business category")
        .action(async (opts) => {
        await (0, blueprint_js_1.cliBlueprintSearch)({ ...opts, logger, pluginConfig });
    });
    blueprint
        .command("info <blueprintId>")
        .description("Show detailed information for a marketplace blueprint")
        .action(async (blueprintId) => {
        await (0, blueprint_js_1.cliBlueprintInfo)({ blueprintId, logger, pluginConfig });
    });
    blueprint
        .command("merge <incoming>")
        .description("Merge an external blueprint into your local workspace")
        .action(async (incoming) => {
        await (0, blueprint_js_1.cliBlueprintMerge)({ incoming, logger, pluginConfig });
    });
    // ── openclaw milimo warroom ───────────────────────────────────────
    milimo
        .command("warroom")
        .description("Launch the War Room interactive operator dashboard")
        .option("-o, --operator <name>", "Override operator ID", "local-operator")
        .option("--list", "List pending messages without TUI (non-interactive)")
        .action((opts) => {
        (0, warroom_js_1.cliWarRoom)({ operator: opts.operator, logger, pluginConfig, list: opts.list });
    });
    // ── openclaw milimo health ────────────────────────────────────────
    milimo
        .command("health")
        .description("Display health status of squad claws")
        .option("-s, --squad <squad>", "Squad ID to check")
        .option("-d, --detailed", "Show detailed health metrics")
        .option("-c, --collect", "Collect fresh health data before display")
        .option("-w, --watch", "Watch mode - continuously update display")
        .option("-i, --interval <ms>", "Watch interval in milliseconds", "5000")
        .option("-j, --json", "Output as JSON")
        .action(async (opts) => {
        const path = await import("node:path");
        const os = await import("node:os");
        const { existsSync } = await import("node:fs");
        const { readFile } = await import("node:fs/promises");
        const squadId = opts.squad || process.env.MILIMO_SQUAD || "default";
        const healthPath = path.join(os.homedir(), ".openclaw/milimo", "health", "health.json");
        if (!existsSync(healthPath)) {
            logger.info("No health data available. Run with --collect to gather data.");
            return;
        }
        try {
            const content = await readFile(healthPath, "utf-8");
            const health = JSON.parse(content);
            if (opts.json) {
                logger.info(JSON.stringify(health, null, 2));
            }
            else if (opts.detailed) {
                logger.info("");
                logger.info(" ┌─────────────────────────────────────────────────────┐");
                logger.info(" │ 🏥 SQUAD HEALTH DASHBOARD 🏥                        │");
                logger.info(" └─────────────────────────────────────────────────────┘");
                logger.info("");
                logger.info(` Overall: ${health.overall_score?.toFixed(1) || "N/A"} (${health.overall_status || "unknown"})`);
                logger.info(` Squad: ${health.squad_id || squadId}`);
                logger.info(` Updated: ${health.last_updated || "never"}`);
                logger.info("");
                if (health.claws) {
                    logger.info(" Claw Status:");
                    for (const claw of health.claws) {
                        const icon = claw.status === "healthy" ? "🟢" : claw.status === "degraded" ? "🔴" : "🟡";
                        logger.info(`  ${icon} ${claw.role?.padEnd(12) || "unknown"} ${claw.score?.toFixed(1) || "N/A"} ${claw.status || "unknown"}`);
                    }
                }
                if (health.alerts?.length > 0) {
                    logger.info("");
                    logger.info(" Alerts:");
                    for (const alert of health.alerts) {
                        logger.info(`  [${alert.level}] ${alert.role}: ${alert.message}`);
                    }
                }
            }
            else {
                logger.info(`Squad Health: ${health.overall_status || "unknown"} (${health.overall_score?.toFixed(1) || "N/A"})`);
                if (health.claws) {
                    for (const claw of health.claws) {
                        logger.info(`  ${claw.role}: ${claw.score?.toFixed(1) || "N/A"}`);
                    }
                }
            }
        }
        catch (err) {
            logger.error(`Failed to read health data: ${err.message}`);
        }
    });
    // ── openclaw milimo payment ───────────────────────────────────────
    const payment = milimo.command("payment").description("Payment and marketplace operations");
    payment
        .command("checkout <blueprintId>")
        .description("Purchase a blueprint from the marketplace")
        .option("--success-url <url>", "Success redirect URL")
        .option("--cancel-url <url>", "Cancel redirect URL")
        .action(async (blueprintId, opts) => {
        await (0, payment_js_1.cliPaymentCheckout)({ blueprintId, ...opts, logger, pluginConfig });
    });
    payment
        .command("status")
        .description("Check payment session status")
        .option("--session <id>", "Session ID")
        .action(async (opts) => {
        await (0, payment_js_1.cliPaymentStatus)({ ...opts, logger, pluginConfig });
    });
    payment
        .command("balance")
        .description("Show seller balance and payout info")
        .action(async () => {
        await (0, payment_js_1.cliPaymentBalance)({ logger, pluginConfig });
    });
    payment
        .command("history")
        .description("Show transaction history")
        .option("--limit <n>", "Number of transactions", "10")
        .action(async (opts) => {
        await (0, payment_js_1.cliPaymentHistory)({
            limit: opts.limit ? parseInt(opts.limit, 10) : 10,
            logger,
            pluginConfig,
        });
    });
    payment
        .command("invoice <sessionId>")
        .description("Generate invoice for a completed payment")
        .option("--format <format>", "Output format: text, json, html", "text")
        .action(async (sessionId, opts) => {
        await (0, payment_js_1.cliPaymentInvoice)({
            sessionId,
            format: opts.format,
            logger,
            pluginConfig,
        });
    });
    payment
        .command("connect")
        .description("Connect Stripe account for seller payouts")
        .requiredOption("--display-name <name>", "Display name for Stripe account")
        .requiredOption("--email <email>", "Email for Stripe account")
        .action(async (opts) => {
        await (0, payment_js_1.cliPaymentConnect)({ ...opts, logger, pluginConfig });
    });
    // ── openclaw milimo verify ────────────────────────────────────────
    milimo
        .command("verify")
        .description("Verify blueprint provenance and integrity")
        .option("--blueprint <id>", "Blueprint ID to verify")
        .option("--version <v>", "Blueprint version", "latest")
        .option("--chain", "Validate full provenance chain", false)
        .option("--strict", "Enable strict validation mode", false)
        .option("--json", "Output as JSON", false)
        .action(async (opts) => {
        await (0, verify_js_1.cliVerify)({ ...opts, logger, pluginConfig });
    });
    milimo
        .command("provenance-keygen")
        .description("Generate Ed25519 key pair for blueprint signing")
        .requiredOption("--squad <name>", "Squad name for key identification")
        .option("--force", "Overwrite existing key", false)
        .action(async (opts) => {
        await (0, verify_js_1.cliProvenanceKeygen)({ ...opts, logger, pluginConfig });
    });
    // ── openclaw milimo badge ─────────────────────────────────────────
    milimo
        .command("badge")
        .description("Generate and verify performance attestations")
        .option("--blueprint <id>", "Blueprint ID")
        .option("--performance", "Generate performance attestation", false)
        .option("--auditor <email>", "Request auditor verification")
        .option("--verify <file>", "Verify an attestation file")
        .option("--list", "List all attestations", false)
        .option("--json", "Output as JSON", false)
        .action(async (opts) => {
        await (0, badge_js_1.cliBadge)({ ...opts, logger, pluginConfig });
    });
    // ── openclaw milimo action ────────────────────────────────────────
    const action = milimo.command("action").description("Action queue management");
    action
        .command("approve <actionId>")
        .description("Approve a pending action without opening TUI")
        .action(async (actionId) => {
        await (0, action_js_1.cliActionApprove)({ actionId, logger, pluginConfig });
    });
    action
        .command("block <actionId>")
        .description("Block (reject) a pending action without opening TUI")
        .option("--reason <reason>", "Reason for blocking")
        .action(async (actionId, opts) => {
        await (0, action_js_1.cliActionBlock)({ actionId, reason: opts.reason, logger, pluginConfig });
    });
    action
        .command("list")
        .description("List pending actions in the queue")
        .option("--json", "Output as JSON", false)
        .action((opts) => {
        const pending = (0, action_js_1.listPendingActions)();
        if (opts.json) {
            logger.info(JSON.stringify(pending, null, 2));
        }
        else if (pending.length === 0) {
            logger.info("No pending actions in queue.");
        }
        else {
            logger.info(`Pending actions (${pending.length}):`);
            for (const action of pending) {
                const priority = (action.priority ?? action.needs_approval) ? "REVIEW" : "AUTO";
                logger.info(` [${priority}] ${action.message_id} - ${action.sender_role}: ${action.message_type}`);
            }
        }
    });
    // ── openclaw milimo logs ────────────────────────────────────────────
    const logs = milimo.command("logs").description("Audit log management");
    logs
        .command("search")
        .description("Search audit logs")
        .option("--query <text>", "Search query text")
        .option("--from <date>", "Start date (YYYY-MM-DD)")
        .option("--to <date>", "End date (YYYY-MM-DD)")
        .option("--claw <role>", "Filter by claw role")
        .option("--decision <decision>", "Filter by decision (APPROVED, REJECTED, etc.)")
        .option("--limit <n>", "Maximum results", "50")
        .option("--json", "Output as JSON", false)
        .option("--squad <squad>", "Squad ID")
        .action(async (opts) => {
        await (0, logs_js_1.cliLogsSearch)({
            ...opts,
            limit: opts.limit ? parseInt(opts.limit, 10) : 50,
            logger,
            pluginConfig,
        });
    });
    logs
        .command("list")
        .description("List available log files")
        .option("--squad <squad>", "Squad ID")
        .action(async (opts) => {
        await (0, logs_js_1.cliLogsList)({ ...opts, logger, pluginConfig });
    });
    // ── openclaw milimo assistant ────────────────────────────────────────
    const assistant = milimo.command("assistant").description("Squad assistant management");
    assistant
        .command("setup")
        .description("Render and install the assistant system prompt")
        .action(async () => {
        await (0, assistant_js_1.assistantSetup)();
    });
    assistant
        .command("verify")
        .description("Verify assistant setup is complete")
        .action(async () => {
        await (0, assistant_js_1.assistantVerify)();
    });
    assistant
        .command("start")
        .description("Start the assistant in NemoClaw terminal")
        .action(() => {
        (0, assistant_js_1.assistantStart)();
    });
    // ── openclaw milimo channels ─────────────────────────────────────────
    const channels = milimo
        .command("channels")
        .description("NemoClaw channel bridges (Telegram, Discord, Slack)");
    channels
        .command("list")
        .description("List available messaging channels")
        .action(() => {
        (0, channels_js_1.cliChannelsList)();
    });
    channels
        .command("add <type>")
        .description("Add a messaging channel (telegram, discord, slack)")
        .action((type) => {
        (0, channels_js_1.cliChannelsAdd)(type);
    });
    channels
        .command("remove <type>")
        .description("Remove a messaging channel")
        .action((type) => {
        (0, channels_js_1.cliChannelsRemove)(type);
    });
    channels
        .command("start")
        .description("Start channel bridges")
        .action(() => {
        (0, channels_js_1.cliChannelsStart)();
    });
    channels
        .command("stop")
        .description("Stop channel bridges")
        .action(() => {
        (0, channels_js_1.cliChannelsStop)();
    });
    channels
        .command("status")
        .description("Show Milimo notification delivery status")
        .action(() => {
        (0, channels_js_1.cliChannelsStatus)(logger);
    });
    channels
        .command("test")
        .description("Send a test notification through active channels")
        .action(() => {
        (0, channels_js_1.cliChannelsTest)(logger);
    });
}
//# sourceMappingURL=cli.js.map