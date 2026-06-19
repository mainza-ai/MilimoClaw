"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliChannelsList = cliChannelsList;
exports.cliChannelsAdd = cliChannelsAdd;
exports.cliChannelsRemove = cliChannelsRemove;
exports.cliChannelsStart = cliChannelsStart;
exports.cliChannelsStop = cliChannelsStop;
exports.cliChannelsStatus = cliChannelsStatus;
exports.cliChannelsTest = cliChannelsTest;
/**
 * `milimo channels` — NemoClaw channel bridge management.
 *
 * Thin wrappers around NemoClaw's native `nemoclaw <name> channels *`
 * commands, plus Milimo-specific notification configuration.
 *
 * Commands:
 *   list     — List available messaging channels and their status
 *   status   — Show notification delivery status
 *   test     — Send a test notification through active channels
 *   config   — View/update notification preferences
 */
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const node_os_1 = require("node:os");
const channel_notifier_js_1 = require("../hooks/channel-notifier.js");
/**
 * Resolve the active sandbox name from NemoClaw state file.
 */
function getSandboxName() {
    try {
        const sandboxesPath = (0, node_path_1.join)((0, node_os_1.homedir)(), ".nemoclaw/sandboxes.json");
        if (!(0, node_fs_1.existsSync)(sandboxesPath))
            return "openclaw";
        const data = JSON.parse((0, node_fs_1.readFileSync)(sandboxesPath, "utf-8"));
        if (data.defaultSandbox)
            return data.defaultSandbox;
        if (data.sandboxes?.[0]?.name)
            return data.sandboxes[0].name;
        return "openclaw";
    }
    catch {
        return "openclaw";
    }
}
/**
 * Print instructions for the user to run NemoClaw channel commands directly.
 */
function printChannelInstructions(subcommand, args = []) {
    const sandboxName = getSandboxName();
    const fullCmd = `nemoclaw ${sandboxName} channels ${subcommand} ${args.join(" ")}`.trim();
    console.log(`\n  To manage channels, run the NemoClaw command directly:\n`);
    console.log(`    ${fullCmd}\n`);
    console.log(`  Or use the interactive channel setup:\n`);
    console.log(`    nemoclaw ${sandboxName} channels add telegram\n`);
}
// ---------------------------------------------------------------------------
// CLI command handlers
// ---------------------------------------------------------------------------
/**
 * List available channels via NemoClaw native command.
 */
function cliChannelsList() {
    printChannelInstructions("list");
}
/**
 * Add a channel via NemoClaw native command.
 */
function cliChannelsAdd(channelType) {
    printChannelInstructions("add", [channelType]);
}
/**
 * Remove a channel via NemoClaw native command.
 */
function cliChannelsRemove(channelType) {
    printChannelInstructions("remove", [channelType]);
}
/**
 * Start channel bridges via NemoClaw native command.
 */
function cliChannelsStart() {
    printChannelInstructions("start");
}
/**
 * Stop channel bridges via NemoClaw native command.
 */
function cliChannelsStop() {
    printChannelInstructions("stop");
}
/**
 * Show Milimo notification status.
 */
function cliChannelsStatus(logger) {
    const config = (0, channel_notifier_js_1.loadNotificationConfig)();
    const notifier = new channel_notifier_js_1.ChannelNotifier(logger, config);
    console.log("\n  Milimo Channel Notification Status\n");
    const channels = notifier.getActiveChannels();
    for (const ch of channels) {
        const icon = ch.active ? "✅" : "❌";
        console.log(`  ${icon} ${ch.name}: ${ch.active ? "active" : "not configured"}`);
    }
    console.log("");
    console.log(`  Digest notifications: ${config.digestEnabled !== false ? "enabled" : "disabled"}`);
    console.log(`  HOLD alerts:          ${config.holdAlertsEnabled !== false ? "enabled" : "disabled"}`);
    console.log(`  Cost guard alerts:    ${config.costGuardAlertsEnabled !== false ? "enabled" : "disabled"}`);
    console.log(`  Min alert level:      ${config.minAlertLevel ?? "warning"}`);
    console.log("");
    if (!notifier.hasActiveChannels()) {
        console.log("  No active channels. To add one:");
        console.log("    openclaw milimo channels add telegram");
        console.log("    openclaw milimo channels add discord");
        console.log("    openclaw milimo channels add slack");
        console.log("");
    }
}
/**
 * Send a test notification through active channels.
 */
function cliChannelsTest(logger) {
    const config = (0, channel_notifier_js_1.loadNotificationConfig)();
    const notifier = new channel_notifier_js_1.ChannelNotifier(logger, config);
    if (!notifier.hasActiveChannels()) {
        console.error("No active channels. Add one first:");
        console.error("  openclaw milimo channels add telegram");
        process.exit(1);
    }
    console.log("Sending test notification...");
    const success = notifier.sendAlert("info", "Test notification from Milimo Claw. Channel bridge is working! 🦀");
    if (success) {
        console.log("✅ Test notification queued successfully.");
        console.log(`Active channels: ${notifier.activeChannelNames().join(", ")}`);
    }
    else {
        console.error("❌ Failed to queue test notification.");
    }
}
//# sourceMappingURL=channels.js.map