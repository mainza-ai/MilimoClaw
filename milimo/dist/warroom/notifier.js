"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.OperatorNotifier = void 0;
exports.createNotifier = createNotifier;
/**
 * Operator Notifier — System notifications when TUI is closed
 *
 * Platform-specific notification delivery:
 * - macOS: osascript (no new deps)
 * - Linux: notify-send (no new deps)
 * - Fallback: write to ~/.openclaw/milimo/notifications/pending.json
 */
const node_child_process_1 = require("node:child_process");
const node_path_1 = require("node:path");
const node_os_1 = require("node:os");
const node_fs_1 = require("node:fs");
const NOTIFICATION_DIR = ".openclaw/milimo/notifications";
const PENDING_FILE = "pending.json";
class OperatorNotifier {
    notificationDir;
    pendingFile;
    enabled;
    constructor(enabled = true) {
        const home = (0, node_os_1.homedir)();
        this.notificationDir = (0, node_path_1.join)(home, NOTIFICATION_DIR);
        this.pendingFile = (0, node_path_1.join)(this.notificationDir, PENDING_FILE);
        this.enabled = enabled;
        this.ensureNotificationDir();
    }
    notify(payload) {
        if (!this.enabled) {
            return { delivered: false, method: "disabled" };
        }
        if (payload.priority !== "HOLD") {
            return { delivered: false, method: "disabled" };
        }
        const title = "🦀 WAR ROOM";
        const subtitle = `${payload.claw.toUpperCase()} CLAW`;
        const message = `${subtitle} | ${payload.summary}`;
        switch (process.platform) {
            case "darwin":
                return this.notifyMacOS(title, message, payload);
            case "linux":
                return this.notifyLinux(title, message, payload);
            default:
                return this.notifyPendingFile(payload);
        }
    }
    notifyHoldRelease(actionId) {
        if (!this.enabled) {
            return { delivered: false, method: "disabled" };
        }
        const title = "🦀 WAR ROOM";
        const message = `HOLD released — action ${actionId} approved`;
        switch (process.platform) {
            case "darwin":
                return this.notifyMacOS(title, message, { action_id: actionId });
            case "linux":
                return this.notifyLinux(title, message, { action_id: actionId });
            default:
                return { delivered: true, method: "pending_file" };
        }
    }
    notifyMacOS(title, message, _payload) {
        const script = `display notification "${this.escapeAppleScript(message)}" with title "${this.escapeAppleScript(title)}"`;
        try {
            const result = (0, node_child_process_1.spawnSync)("osascript", ["-e", script], {
                encoding: "utf-8",
                timeout: 5000,
            });
            if (result.status === 0) {
                return { delivered: true, method: "osascript" };
            }
            return this.notifyPendingFile(_payload);
        }
        catch (error) {
            return {
                delivered: false,
                method: "osascript",
                error: error.message,
            };
        }
    }
    notifyLinux(title, message, _payload) {
        try {
            const result = (0, node_child_process_1.spawnSync)("notify-send", [title, message], {
                encoding: "utf-8",
                timeout: 5000,
            });
            if (result.status === 0) {
                return { delivered: true, method: "notify-send" };
            }
            return this.notifyPendingFile(_payload);
        }
        catch (error) {
            return {
                delivered: false,
                method: "notify-send",
                error: error.message,
            };
        }
    }
    notifyPendingFile(payload) {
        try {
            let pending = [];
            if ((0, node_fs_1.existsSync)(this.pendingFile)) {
                try {
                    const content = (0, node_fs_1.readFileSync)(this.pendingFile, "utf-8");
                    pending = JSON.parse(content);
                    if (!Array.isArray(pending)) {
                        pending = [];
                    }
                }
                catch {
                    pending = [];
                }
            }
            pending.push(payload);
            (0, node_fs_1.writeFileSync)(this.pendingFile, JSON.stringify(pending, null, 2));
            return { delivered: true, method: "pending_file" };
        }
        catch (error) {
            return {
                delivered: false,
                method: "pending_file",
                error: error.message,
            };
        }
    }
    getPendingNotifications() {
        if (!(0, node_fs_1.existsSync)(this.pendingFile)) {
            return [];
        }
        try {
            const content = (0, node_fs_1.readFileSync)(this.pendingFile, "utf-8");
            const pending = JSON.parse(content);
            return Array.isArray(pending) ? pending : [];
        }
        catch {
            return [];
        }
    }
    clearPendingNotification(actionId) {
        if (!(0, node_fs_1.existsSync)(this.pendingFile)) {
            return;
        }
        try {
            const content = (0, node_fs_1.readFileSync)(this.pendingFile, "utf-8");
            let pending = JSON.parse(content);
            if (!Array.isArray(pending)) {
                pending = [];
            }
            pending = pending.filter((n) => n.action_id !== actionId);
            if (pending.length === 0) {
                (0, node_fs_1.unlinkSync)(this.pendingFile);
            }
            else {
                (0, node_fs_1.writeFileSync)(this.pendingFile, JSON.stringify(pending, null, 2));
            }
        }
        catch {
            // Ignore errors
        }
    }
    clearAllPending() {
        if ((0, node_fs_1.existsSync)(this.pendingFile)) {
            try {
                (0, node_fs_1.unlinkSync)(this.pendingFile);
            }
            catch {
                // Ignore errors
            }
        }
    }
    ensureNotificationDir() {
        if (!(0, node_fs_1.existsSync)(this.notificationDir)) {
            try {
                (0, node_fs_1.mkdirSync)(this.notificationDir, { recursive: true });
            }
            catch {
                // Ignore errors
            }
        }
    }
    escapeAppleScript(str) {
        return str.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    }
}
exports.OperatorNotifier = OperatorNotifier;
function createNotifier(enabled = true) {
    return new OperatorNotifier(enabled);
}
//# sourceMappingURL=notifier.js.map