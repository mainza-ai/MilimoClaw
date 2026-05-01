"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliLogsSearch = cliLogsSearch;
exports.cliLogsList = cliLogsList;
/**
 * Logs CLI Commands
 *
 * milimo logs search --query <text> --from <date> --to <date>
 */
const node_path_1 = require("node:path");
const node_os_1 = require("node:os");
const node_fs_1 = require("node:fs");
const node_zlib_1 = require("node:zlib");
function cliLogsSearch(options) {
    const { logger, query, from, to, clawRole, decision, limit = 100, json, squad } = options;
    const squadId = squad || process.env.MILIMO_SQUAD || "default";
    const home = (0, node_os_1.homedir)();
    const auditDir = (0, node_path_1.join)(home, ".openclaw/milimo", "audit", squadId);
    if (!(0, node_fs_1.existsSync)(auditDir)) {
        logger.error(`No audit logs found for squad: ${squadId}`);
        return Promise.resolve();
    }
    const results = [];
    const fromDate = from ? new Date(from) : null;
    const toDate = to ? new Date(to) : null;
    // Search in current log
    const currentLog = (0, node_path_1.join)(auditDir, "warroom.log");
    if ((0, node_fs_1.existsSync)(currentLog)) {
        searchInFile(currentLog, fromDate, toDate, query, clawRole, decision, limit, results, false);
    }
    // Search in rotated logs
    try {
        const files = (0, node_fs_1.readdirSync)(auditDir)
            .filter((f) => f.startsWith("warroom-") && (f.endsWith(".log") || f.endsWith(".gz")))
            .sort()
            .reverse();
        for (const file of files) {
            if (results.length >= limit)
                break;
            const filePath = (0, node_path_1.join)(auditDir, file);
            searchInFile(filePath, fromDate, toDate, query, clawRole, decision, limit, results, file.endsWith(".gz"));
        }
    }
    catch (error) {
        logger.error(`Failed to read rotated logs: ${error.message}`);
    }
    if (json) {
        logger.info(JSON.stringify(results.slice(0, limit), null, 2));
    }
    else if (results.length === 0) {
        logger.info("No matching log entries found.");
    }
    else {
        logger.info(`Found ${results.length} matching entries:\n`);
        for (const entry of results.slice(0, limit)) {
            const timestamp = entry.timestamp;
            const claw = entry.clawRole?.toUpperCase().padEnd(10) || "UNKNOWN   ";
            const action = entry.actionType.padEnd(20);
            const dec = entry.decision?.padEnd(10) || "N/A       ";
            const msg = entry.messageId?.substring(0, 8) || "N/A";
            logger.info(`${timestamp} | ${claw} | ${action} | ${dec} | ${msg}`);
            if (entry.reason) {
                logger.info(`  Reason: ${entry.reason}`);
            }
            if (entry.details && Object.keys(entry.details).length > 0) {
                logger.info(`  Details: ${JSON.stringify(entry.details)}`);
            }
        }
    }
    return Promise.resolve();
}
function searchInFile(filePath, fromDate, toDate, query, clawRole, decision, limit, results, compressed) {
    try {
        let content;
        if (compressed) {
            const compressedData = (0, node_fs_1.readFileSync)(filePath);
            content = (0, node_zlib_1.gunzipSync)(compressedData).toString("utf8");
        }
        else {
            content = (0, node_fs_1.readFileSync)(filePath, "utf8");
        }
        const lines = content.split("\n").filter((l) => l.trim() !== "");
        for (const line of lines) {
            if (results.length >= limit)
                break;
            try {
                const entry = JSON.parse(line);
                // Filter by date range
                const entryDate = new Date(entry.timestamp);
                if (fromDate && entryDate < fromDate)
                    continue;
                if (toDate && entryDate > toDate)
                    continue;
                // Filter by claw role
                if (clawRole && entry.clawRole !== clawRole)
                    continue;
                // Filter by decision
                if (decision && entry.decision !== decision)
                    continue;
                // Filter by query
                if (query) {
                    const entryStr = JSON.stringify(entry).toLowerCase();
                    if (!entryStr.includes(query.toLowerCase()))
                        continue;
                }
                results.push(entry);
            }
            catch {
                // Skip malformed entries
            }
        }
    }
    catch {
        // Ignore errors reading file
    }
}
function cliLogsList(options) {
    const { logger, squad } = options;
    const squadId = squad || process.env.MILIMO_SQUAD || "default";
    const home = (0, node_os_1.homedir)();
    const auditDir = (0, node_path_1.join)(home, ".openclaw/milimo", "audit", squadId);
    if (!(0, node_fs_1.existsSync)(auditDir)) {
        logger.error(`No audit logs found for squad: ${squadId}`);
        return Promise.resolve();
    }
    try {
        const files = (0, node_fs_1.readdirSync)(auditDir)
            .filter((f) => f.startsWith("warroom") && (f.endsWith(".log") || f.endsWith(".gz")))
            .sort()
            .reverse();
        if (files.length === 0) {
            logger.info("No log files found.");
            return Promise.resolve();
        }
        logger.info(`Log files for squad ${squadId}:\n`);
        for (const file of files) {
            const filePath = (0, node_path_1.join)(auditDir, file);
            const stats = (0, node_fs_1.statSync)(filePath);
            const sizeKB = Math.round(stats.size / 1024);
            const modified = stats.mtime.toISOString().split("T")[0];
            logger.info(`  ${file.padEnd(30)} ${sizeKB.toString().padStart(6)} KB  ${modified}`);
        }
    }
    catch (error) {
        logger.error(`Failed to list logs: ${error.message}`);
    }
    return Promise.resolve();
}
//# sourceMappingURL=logs.js.map