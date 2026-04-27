"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.AuditLogger = void 0;
exports.createAuditLogger = createAuditLogger;
const fs_1 = require("fs");
const path_1 = require("path");
const os_1 = require("os");
const zlib_1 = require("zlib");
const DEFAULT_RETENTION_DAYS = 90;
class AuditLogger {
    auditDir;
    auditFile;
    rotationConfig;
    lastRotationCheck = null;
    constructor(squadId, rotationConfig) {
        const home = process.env.HOME || process.env.USERPROFILE || (0, os_1.homedir)() || "/tmp";
        this.auditDir = (0, path_1.join)(home, ".openclaw-data/milimo", "audit", squadId);
        this.auditFile = (0, path_1.join)(this.auditDir, "warroom.log");
        this.rotationConfig = {
            retentionDays: rotationConfig?.retentionDays ?? DEFAULT_RETENTION_DAYS,
            compress: rotationConfig?.compress ?? true,
        };
        this.ensureDirectory();
    }
    ensureDirectory() {
        if (!(0, fs_1.existsSync)(this.auditDir)) {
            (0, fs_1.mkdirSync)(this.auditDir, { recursive: true });
        }
    }
    logAction(entry) {
        // Check for rotation at midnight
        this.checkRotation();
        const fullEntry = {
            timestamp: new Date().toISOString(),
            ...entry,
        };
        // Append as a single line JSON (JSONL format)
        (0, fs_1.appendFileSync)(this.auditFile, JSON.stringify(fullEntry) + "\n", "utf8");
    }
    getRecentLogs(limit = 50) {
        if (!(0, fs_1.existsSync)(this.auditFile)) {
            return [];
        }
        try {
            const content = (0, fs_1.readFileSync)(this.auditFile, "utf8");
            const lines = content.split("\n").filter((line) => line.trim() !== "");
            // Get the last `limit` lines
            const recentLines = lines.slice(-limit);
            return recentLines.map((line) => JSON.parse(line));
        }
        catch {
            return [];
        }
    }
    // ── Log Rotation ───────────────────────────────────────────────────
    checkRotation() {
        const now = new Date();
        // Only check once per hour at most
        if (this.lastRotationCheck) {
            const hoursSinceCheck = (now.getTime() - this.lastRotationCheck.getTime()) / (1000 * 60 * 60);
            if (hoursSinceCheck < 1) {
                return;
            }
        }
        this.lastRotationCheck = now;
        // Check if we need to rotate (midnight crossing)
        if (!(0, fs_1.existsSync)(this.auditFile)) {
            return;
        }
        const stats = (0, fs_1.statSync)(this.auditFile);
        const fileDate = stats.mtime.toISOString().split("T")[0];
        const today = now.toISOString().split("T")[0];
        if (fileDate !== today) {
            this.rotateLog(fileDate);
        }
        // Clean up old logs
        this.cleanupOldLogs();
    }
    rotateLog(dateStr) {
        if (!(0, fs_1.existsSync)(this.auditFile)) {
            return;
        }
        const rotatedName = `warroom-${dateStr}.log`;
        const rotatedPath = (0, path_1.join)(this.auditDir, rotatedName);
        try {
            // Rename current log to dated log
            (0, fs_1.renameSync)(this.auditFile, rotatedPath);
            // Compress if enabled
            if (this.rotationConfig.compress) {
                this.compressLog(rotatedPath);
            }
            // Create new empty log
            (0, fs_1.writeFileSync)(this.auditFile, "");
        }
        catch (error) {
            console.error("Failed to rotate log:", error);
        }
    }
    compressLog(logPath) {
        try {
            const content = (0, fs_1.readFileSync)(logPath);
            const compressed = (0, zlib_1.gzipSync)(content);
            const gzPath = `${logPath}.gz`;
            (0, fs_1.writeFileSync)(gzPath, compressed);
            (0, fs_1.unlinkSync)(logPath);
        }
        catch (error) {
            console.error("Failed to compress log:", error);
        }
    }
    cleanupOldLogs() {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - this.rotationConfig.retentionDays);
        try {
            const files = (0, fs_1.readdirSync)(this.auditDir);
            for (const file of files) {
                if (file === "warroom.log" || file === "audit.jsonl") {
                    continue;
                }
                const filePath = (0, path_1.join)(this.auditDir, file);
                const stats = (0, fs_1.statSync)(filePath);
                if (stats.mtime < cutoffDate) {
                    (0, fs_1.unlinkSync)(filePath);
                }
            }
        }
        catch (error) {
            console.error("Failed to cleanup old logs:", error);
        }
    }
    // ── Search ─────────────────────────────────────────────────────────
    searchLogs(options) {
        const results = [];
        const fromDate = options.from ? new Date(options.from) : null;
        const toDate = options.to ? new Date(options.to) : null;
        const query = options.query?.toLowerCase();
        const limit = options.limit ?? 100;
        // Search in current log
        this.searchInFile(this.auditFile, fromDate, toDate, query, options, results);
        // Search in rotated logs
        try {
            const files = (0, fs_1.readdirSync)(this.auditDir)
                .filter((f) => f.startsWith("warroom-") && (f.endsWith(".log") || f.endsWith(".gz")))
                .sort()
                .reverse();
            for (const file of files) {
                if (results.length >= limit)
                    break;
                const filePath = (0, path_1.join)(this.auditDir, file);
                this.searchInFile(filePath, fromDate, toDate, query, options, results, file.endsWith(".gz"));
            }
        }
        catch {
            // Ignore errors reading directory
        }
        return results.slice(0, limit);
    }
    searchInFile(filePath, fromDate, toDate, query, options, results, compressed = false) {
        if (!(0, fs_1.existsSync)(filePath))
            return;
        try {
            let content;
            if (compressed) {
                const compressedData = (0, fs_1.readFileSync)(filePath);
                content = (0, zlib_1.gunzipSync)(compressedData).toString("utf8");
            }
            else {
                content = (0, fs_1.readFileSync)(filePath, "utf8");
            }
            const lines = content.split("\n").filter((l) => l.trim() !== "");
            for (const line of lines) {
                try {
                    const entry = JSON.parse(line);
                    // Filter by date range
                    const entryDate = new Date(entry.timestamp);
                    if (fromDate && entryDate < fromDate)
                        continue;
                    if (toDate && entryDate > toDate)
                        continue;
                    // Filter by claw role
                    if (options.clawRole && entry.clawRole !== options.clawRole)
                        continue;
                    // Filter by decision
                    if (options.decision && entry.decision !== options.decision)
                        continue;
                    // Filter by query
                    if (query) {
                        const entryStr = JSON.stringify(entry).toLowerCase();
                        if (!entryStr.includes(query))
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
    getRotatedLogs() {
        try {
            return (0, fs_1.readdirSync)(this.auditDir)
                .filter((f) => f.startsWith("warroom-") && (f.endsWith(".log") || f.endsWith(".gz")))
                .sort()
                .reverse();
        }
        catch {
            return [];
        }
    }
}
exports.AuditLogger = AuditLogger;
function createAuditLogger(squadId, config) {
    return new AuditLogger(squadId, config);
}
//# sourceMappingURL=audit.js.map