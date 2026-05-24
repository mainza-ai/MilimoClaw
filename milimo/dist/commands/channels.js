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
const node_child_process_1 = require("node:child_process");
const channel_notifier_js_1 = require("../hooks/channel-notifier.js");
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
/**
 * Resolve the active sandbox name from NemoClaw state.
 */
function getSandboxName() {
    try {
        const output = (0, node_child_process_1.execFileSync)("nemoclaw", ["list"], {
            encoding: "utf-8",
            timeout: 5000,
            stdio: ["pipe", "pipe", "pipe"],
        });
        // Parse first sandbox name from output
        const lines = output.trim().split("\n");
        for (const line of lines) {
            const cols = line.trim().split(/\s+/);
            if (cols[0] && !cols[0].startsWith("NAME") && !cols[0].startsWith("-")) {
                return cols[0];
            }
        }
    }
    catch {
        // Fall through
    }
    return "openclaw";
}
/**
 * Delegate to a NemoClaw channels subcommand.
 */
function delegateToNemoClaw(subcommand, args = []) {
    const sandboxName = getSandboxName();
    const fullArgs = [sandboxName, "channels", subcommand, ...args];
    console.log(`Delegating to: nemoclaw ${fullArgs.join(" ")}\n`);
    const result = (0, node_child_process_1.spawnSync)("nemoclaw", fullArgs, {
        stdio: "inherit",
        timeout: 30000,
    });
    if (result.error) {
        console.error(`Failed to run nemoclaw channels ${subcommand}:`, result.error.message);
        console.error("Is NemoClaw installed? Run: nemoclaw --version");
        process.exit(1);
    }
    if (result.status !== 0) {
        process.exit(result.status ?? 1);
    }
}
// ---------------------------------------------------------------------------
// CLI command handlers
// ---------------------------------------------------------------------------
/**
 * List available channels via NemoClaw native command.
 */
function cliChannelsList() {
    delegateToNemoClaw("list");
}
/**
 * Add a channel via NemoClaw native command.
 */
function cliChannelsAdd(channelType) {
    delegateToNemoClaw("add", [channelType]);
}
/**
 * Remove a channel via NemoClaw native command.
 */
function cliChannelsRemove(channelType) {
    delegateToNemoClaw("remove", [channelType]);
}
/**
 * Start channel bridges via NemoClaw native command.
 */
function cliChannelsStart() {
    delegateToNemoClaw("start");
}
/**
 * Stop channel bridges via NemoClaw native command.
 */
function cliChannelsStop() {
    delegateToNemoClaw("stop");
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