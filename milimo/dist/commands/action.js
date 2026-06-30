"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliActionApprove = cliActionApprove;
exports.cliActionBlock = cliActionBlock;
exports.listPendingActions = listPendingActions;
/**
 * Action CLI Commands
 *
 * milimo action approve <action_id>
 * milimo action block <action_id>
 *
 * Work without opening TUI. Read pending queue from file,
 * update decision, trigger downstream execution.
 */
/* eslint-disable @typescript-eslint/await-thenable */
const node_path_1 = require("node:path");
const node_os_1 = require("node:os");
const node_fs_1 = require("node:fs");
function cliActionApprove(options) {
    const { logger, actionId } = options;
    const home = (0, node_os_1.homedir)();
    const meshDir = (0, node_path_1.join)(home, ".openclaw/milimo", "mesh");
    const warRoomInbox = (0, node_path_1.join)(meshDir, "inbox", "war_room");
    const approvedDir = (0, node_path_1.join)(meshDir, "approved");
    const logsDir = (0, node_path_1.join)(home, ".openclaw/milimo", "logs");
    if (!(0, node_fs_1.existsSync)(warRoomInbox)) {
        logger.error("No pending actions found. War Room inbox does not exist.");
        process.exit(1);
    }
    const action = findActionById(warRoomInbox, actionId);
    if (!action) {
        logger.error(`Action not found: ${actionId}`);
        process.exit(1);
    }
    (0, node_fs_1.mkdirSync)(approvedDir, { recursive: true });
    const fileName = action.file_path.split("/").pop();
    const targetPath = (0, node_path_1.join)(approvedDir, fileName);
    try {
        (0, node_fs_1.renameSync)(action.file_path, targetPath);
        logDecision(logsDir, {
            action_id: actionId,
            decision: "APPROVED",
            operator: "cli",
            timestamp: new Date().toISOString(),
            claw: action.sender_role,
            action_type: action.message_type,
        });
        logger.info(`✓ Action approved: ${actionId}`);
        logger.info(` Claw: ${action.sender_role.toUpperCase()}`);
        logger.info(` Type: ${action.message_type}`);
        if (action.message_type === "tool_proposal" && action.payload?.tool_name) {
            logger.info(` Tool: ${action.payload.tool_name}`);
        }
        if (action.payload?.amount) {
            logger.info(` Amount: $${action.payload.amount}`);
        }
    }
    catch (error) {
        logger.error(`Failed to approve action: ${error.message}`);
        process.exit(1);
    }
    return Promise.resolve();
}
function cliActionBlock(options) {
    const { logger, actionId, reason } = options;
    const home = (0, node_os_1.homedir)();
    const meshDir = (0, node_path_1.join)(home, ".openclaw/milimo", "mesh");
    const warRoomInbox = (0, node_path_1.join)(meshDir, "inbox", "war_room");
    const rejectedDir = (0, node_path_1.join)(meshDir, "rejected");
    const logsDir = (0, node_path_1.join)(home, ".openclaw/milimo", "logs");
    if (!(0, node_fs_1.existsSync)(warRoomInbox)) {
        logger.error("No pending actions found. War Room inbox does not exist.");
        process.exit(1);
    }
    const action = findActionById(warRoomInbox, actionId);
    if (!action) {
        logger.error(`Action not found: ${actionId}`);
        process.exit(1);
    }
    (0, node_fs_1.mkdirSync)(rejectedDir, { recursive: true });
    const fileName = action.file_path.split("/").pop();
    const targetPath = (0, node_path_1.join)(rejectedDir, fileName);
    try {
        const rejectedAction = {
            ...action,
            rejected_at: new Date().toISOString(),
            rejection_reason: reason ?? "Blocked via CLI",
        };
        (0, node_fs_1.writeFileSync)(targetPath, JSON.stringify(rejectedAction, null, 2));
        (0, node_fs_1.unlinkSync)(action.file_path);
        logDecision(logsDir, {
            action_id: actionId,
            decision: "BLOCKED",
            operator: "cli",
            timestamp: new Date().toISOString(),
            claw: action.sender_role,
            action_type: action.message_type,
            reason: reason,
        });
        logger.info(`✗ Action blocked: ${actionId}`);
        logger.info(` Claw: ${action.sender_role.toUpperCase()}`);
        logger.info(` Type: ${action.message_type}`);
        if (reason) {
            logger.info(` Reason: ${reason}`);
        }
    }
    catch (error) {
        logger.error(`Failed to block action: ${error.message}`);
        process.exit(1);
    }
    return Promise.resolve();
}
function listPendingActions() {
    const home = (0, node_os_1.homedir)();
    const warRoomInbox = (0, node_path_1.join)(home, ".openclaw/milimo", "mesh", "inbox", "war_room");
    if (!(0, node_fs_1.existsSync)(warRoomInbox)) {
        return [];
    }
    const actions = [];
    try {
        const files = (0, node_fs_1.readdirSync)(warRoomInbox).filter((f) => f.endsWith(".json"));
        for (const file of files) {
            const filePath = (0, node_path_1.join)(warRoomInbox, file);
            try {
                const content = (0, node_fs_1.readFileSync)(filePath, "utf-8");
                const msg = JSON.parse(content);
                actions.push({
                    ...msg,
                    file_path: filePath,
                });
            }
            catch {
                // Ignore parse errors
            }
        }
    }
    catch {
        // Ignore read errors
    }
    return actions.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
}
function findActionById(inboxDir, actionId) {
    try {
        const files = (0, node_fs_1.readdirSync)(inboxDir).filter((f) => f.endsWith(".json"));
        for (const file of files) {
            const filePath = (0, node_path_1.join)(inboxDir, file);
            try {
                const content = (0, node_fs_1.readFileSync)(filePath, "utf-8");
                const msg = JSON.parse(content);
                if (msg.message_id === actionId || file.includes(actionId)) {
                    return {
                        ...msg,
                        file_path: filePath,
                    };
                }
            }
            catch {
                // Ignore parse errors
            }
        }
    }
    catch {
        // Ignore read errors
    }
    return null;
}
function logDecision(logsDir, entry) {
    try {
        const logFile = (0, node_path_1.join)(logsDir, "warroom.log");
        const logLine = `${new Date().toISOString()} - cli - INFO - Decision: ${JSON.stringify(entry)}\n`;
        (0, node_fs_1.mkdirSync)(logsDir, { recursive: true });
        (0, node_fs_1.writeFileSync)(logFile, logLine, { flag: "a" });
    }
    catch {
        // Ignore logging errors
    }
}
//# sourceMappingURL=action.js.map