"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChannelNotifier = void 0;
exports.loadNotificationConfig = loadNotificationConfig;
/**
 * Channel Notifier — NemoClaw Channel Bridge Integration
 *
 * Sends Milimo notifications (digest briefs, HOLD alerts, revenue updates)
 * through NemoClaw's native messaging channel bridges (Telegram, Discord, Slack).
 *
 * Architecture:
 *   NemoClaw manages channel lifecycle (add/remove/start/stop) via
 *   `nemoclaw <name> channels <subcommand>`. Milimo's notifier delegates
 *   all channel management to NemoClaw and only handles message formatting
 *   and delivery via the OpenClaw chat interface.
 *
 *   Delivery mechanism: Messages are sent through the OpenClaw agent's
 *   outbound message API. When NemoClaw channels are active, they bridge
 *   agent messages to the configured platform (Telegram/Discord/Slack).
 *
 * Usage:
 *   const notifier = new ChannelNotifier(logger);
 *   notifier.sendDigestBrief(brief);   // Morning/evening digest
 *   notifier.sendHoldAlert(message);   // Finance HOLD escalation
 *   notifier.sendAlert(level, text);   // General alert
 */
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const DEFAULT_CONFIG = {
    channels: [],
    digestEnabled: true,
    holdAlertsEnabled: true,
    costGuardAlertsEnabled: true,
    minAlertLevel: "warning",
};
const ALERT_PRIORITY = {
    info: 0,
    warning: 1,
    critical: 2,
};
// ---------------------------------------------------------------------------
// Channel status detection
// ---------------------------------------------------------------------------
/**
 * Check which NemoClaw channels are currently active by probing
 * for environment variables that indicate configured channel tokens.
 */
function detectActiveChannels() {
    const channels = [];
    const checks = [
        { name: "telegram", envKey: "TELEGRAM_BOT_TOKEN" },
        { name: "discord", envKey: "DISCORD_BOT_TOKEN" },
        { name: "slack", envKey: "SLACK_BOT_TOKEN" },
    ];
    for (const check of checks) {
        channels.push({
            name: check.name,
            active: !!process.env[check.envKey],
            lastCheck: new Date().toISOString(),
        });
    }
    return channels;
}
/**
 * Check channel status using environment variable detection.
 * NemoClaw injects TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, etc.
 * into the sandbox environment when channels are configured.
 */
function probeChannelStatus() {
    return detectActiveChannels();
}
// ---------------------------------------------------------------------------
// Message formatting
// ---------------------------------------------------------------------------
function formatDigestForChannel(brief) {
    const lines = [];
    const header = brief.type === "morning" ? "☀️ Morning Brief" : "🌙 Evening Wrap";
    const date = new Date(brief.generated_at).toLocaleDateString();
    lines.push(`**${header}** — ${date}`);
    lines.push("");
    if (brief.type === "morning") {
        if (brief.overnight_actions && brief.overnight_actions > 0) {
            lines.push(`✅ Auto-executed overnight: ${brief.overnight_actions}`);
        }
        if (brief.queue_summary) {
            lines.push("**Queue Status:**");
            lines.push(`  🔴 HOLD: ${brief.queue_summary.hold}`);
            lines.push(`  🟡 REVIEW: ${brief.queue_summary.review}`);
            lines.push(`  🟢 AUTO: ${brief.queue_summary.auto}`);
        }
        if (brief.pending_actions && brief.pending_actions.length > 0) {
            lines.push("");
            lines.push("**Pending Actions:**");
            for (const action of brief.pending_actions.slice(0, 5)) {
                const emoji = { HOLD: "🔴", REVIEW: "🟡", AUTO: "🟢" };
                lines.push(`  ${emoji[action.priority] ?? "⚪"} [${action.id.slice(0, 8)}] ${action.claw}: ${action.type}`);
            }
        }
    }
    else {
        lines.push("**Today's Summary:**");
        if (brief.today_completed !== undefined) {
            lines.push(`  Total processed: ${brief.today_completed}`);
        }
        if (brief.auto_executed !== undefined) {
            lines.push(`  Auto-executed: ${brief.auto_executed}`);
        }
        if (brief.remaining_pending !== undefined) {
            lines.push(`  Remaining pending: ${brief.remaining_pending}`);
        }
        if (brief.remaining_pending && brief.remaining_pending > 0) {
            lines.push("");
            lines.push("⚠️ Actions still pending for tomorrow");
        }
    }
    return lines.join("\n");
}
function formatHoldAlert(message) {
    const lines = [
        "🔴 **HOLD Alert — Operator Approval Required**",
        "",
        `Action: ${message.message_type}`,
        `From: ${message.sender_role} claw`,
        `ID: ${message.message_id.slice(0, 12)}`,
    ];
    if (message.amount !== undefined) {
        lines.push(`Amount: $${message.amount.toFixed(2)}`);
    }
    lines.push("");
    lines.push("Review in War Room: `openclaw milimo warroom`");
    return lines.join("\n");
}
function formatAlert(level, text) {
    const icons = {
        info: "ℹ️",
        warning: "⚠️",
        critical: "🚨",
    };
    return `${icons[level]} **Milimo ${level.toUpperCase()}**: ${text}`;
}
// ---------------------------------------------------------------------------
// Notification delivery
// ---------------------------------------------------------------------------
/**
 * Deliver a message through the NemoClaw channel bridge.
 *
 * Messages are written to the outbound message queue, which the
 * NemoClaw channel bridge picks up and forwards to the configured
 * messaging platform.
 */
function deliverToOutbox(message, logger) {
    try {
        const sandboxOutbox = "/sandbox/.openclaw/milimo/mesh/outbox/notifications";
        const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
        const homeOutbox = (0, node_path_1.join)(home, ".openclaw/milimo", "mesh", "outbox", "notifications");
        const outbox = (0, node_fs_1.existsSync)(sandboxOutbox) ? sandboxOutbox : homeOutbox;
        if (!(0, node_fs_1.existsSync)(outbox)) {
            (0, node_fs_1.mkdirSync)(outbox, { recursive: true });
        }
        const filename = `notification_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.json`;
        const payload = {
            type: "channel_notification",
            content: message,
            timestamp: new Date().toISOString(),
            delivered: false,
        };
        (0, node_fs_1.writeFileSync)((0, node_path_1.join)(outbox, filename), JSON.stringify(payload, null, 2));
        logger.debug(`[milimo] Notification queued: ${filename}`);
        return true;
    }
    catch (err) {
        logger.warn(`[milimo] Failed to queue notification: ${err instanceof Error ? err.message : String(err)}`);
        return false;
    }
}
// ---------------------------------------------------------------------------
// ChannelNotifier class
// ---------------------------------------------------------------------------
class ChannelNotifier {
    logger;
    config;
    channelCache = null;
    cacheExpiry = 0;
    constructor(logger, config) {
        this.logger = logger;
        this.config = { ...DEFAULT_CONFIG, ...config };
    }
    /** Get active channels (cached for 5 minutes). */
    getActiveChannels() {
        const now = Date.now();
        if (this.channelCache && now < this.cacheExpiry) {
            return this.channelCache;
        }
        this.channelCache = probeChannelStatus();
        this.cacheExpiry = now + 5 * 60 * 1000;
        return this.channelCache;
    }
    /** Check if any notification channel is available. */
    hasActiveChannels() {
        return this.getActiveChannels().some((c) => c.active);
    }
    /** Get names of active channels. */
    activeChannelNames() {
        return this.getActiveChannels()
            .filter((c) => c.active)
            .map((c) => c.name);
    }
    /**
     * Send a digest brief (morning/evening) through active channels.
     */
    sendDigestBrief(brief) {
        if (!this.config.digestEnabled) {
            this.logger.debug("[milimo] Digest notifications disabled.");
            return false;
        }
        if (!this.hasActiveChannels()) {
            this.logger.debug("[milimo] No active channels for digest delivery.");
            return false;
        }
        const message = formatDigestForChannel(brief);
        return deliverToOutbox(message, this.logger);
    }
    /**
     * Send a HOLD alert when a Finance action requires operator approval.
     */
    sendHoldAlert(holdMessage) {
        if (!this.config.holdAlertsEnabled) {
            return false;
        }
        if (!this.hasActiveChannels()) {
            return false;
        }
        const message = formatHoldAlert(holdMessage);
        return deliverToOutbox(message, this.logger);
    }
    /**
     * Send a general alert through active channels.
     */
    sendAlert(level, text) {
        if (ALERT_PRIORITY[level] < ALERT_PRIORITY[this.config.minAlertLevel]) {
            return false;
        }
        if (!this.hasActiveChannels()) {
            return false;
        }
        const message = formatAlert(level, text);
        return deliverToOutbox(message, this.logger);
    }
    /**
     * Send a cost guard warning.
     */
    sendCostGuardWarning(remaining, limit) {
        if (!this.config.costGuardAlertsEnabled) {
            return false;
        }
        const pct = Math.round((remaining / limit) * 100);
        const level = remaining <= 0 ? "critical" : "warning";
        const text = remaining <= 0
            ? `Daily token budget exhausted (${limit} tokens). Auto-approvals paused until midnight UTC.`
            : `Token budget low: ${remaining}/${limit} remaining (${pct}%).`;
        return this.sendAlert(level, text);
    }
    /**
     * Get a status summary for display in the War Room TUI.
     */
    getStatusSummary() {
        const active = this.activeChannelNames();
        if (active.length === 0) {
            return "No channels configured. Run: nemoclaw <name> channels add telegram";
        }
        return `Active: ${active.join(", ")}`;
    }
    /**
     * Update notification config at runtime.
     */
    updateConfig(updates) {
        this.config = { ...this.config, ...updates };
    }
    /**
     * Invalidate the channel cache (e.g. after channel add/remove).
     */
    refreshChannels() {
        this.channelCache = null;
        this.cacheExpiry = 0;
    }
}
exports.ChannelNotifier = ChannelNotifier;
/**
 * Load notification config from the Milimo config file.
 */
function loadNotificationConfig() {
    try {
        const sandboxConfig = "/sandbox/.openclaw/milimo/config.json";
        const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
        const homeConfig = (0, node_path_1.join)(home, ".openclaw/milimo", "config.json");
        const configPath = (0, node_fs_1.existsSync)(sandboxConfig) ? sandboxConfig : homeConfig;
        if (!(0, node_fs_1.existsSync)(configPath))
            return {};
        const config = JSON.parse((0, node_fs_1.readFileSync)(configPath, "utf-8"));
        const notifications = config?.notifications;
        if (!notifications || typeof notifications !== "object")
            return {};
        return {
            digestEnabled: notifications.digestEnabled ?? true,
            holdAlertsEnabled: notifications.holdAlertsEnabled ?? true,
            costGuardAlertsEnabled: notifications.costGuardAlertsEnabled ?? true,
            minAlertLevel: notifications.minAlertLevel ?? "warning",
        };
    }
    catch {
        return {};
    }
}
//# sourceMappingURL=channel-notifier.js.map