"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AuditLogger = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
const os_1 = require("os");
class AuditLogger {
    auditDir;
    auditFile;
    constructor(squadId) {
        const home = process.env.HOME || process.env.USERPROFILE || (0, os_1.homedir)() || '/tmp';
        this.auditDir = (0, path_1.join)(home, '.milimo', 'audit', squadId);
        this.auditFile = (0, path_1.join)(this.auditDir, 'audit.jsonl');
        this.ensureDirectory();
    }
    ensureDirectory() {
        if (!(0, fs_1.existsSync)(this.auditDir)) {
            (0, fs_1.mkdirSync)(this.auditDir, { recursive: true });
        }
    }
    logAction(entry) {
        const fullEntry = {
            timestamp: new Date().toISOString(),
            ...entry,
        };
        // Append as a single line JSON (JSONL format)
        (0, fs_1.appendFileSync)(this.auditFile, JSON.stringify(fullEntry) + '\n', 'utf8');
    }
    getRecentLogs(limit = 50) {
        if (!(0, fs_1.existsSync)(this.auditFile)) {
            return [];
        }
        try {
            const content = (0, fs_1.readFileSync)(this.auditFile, 'utf8');
            const lines = content.split('\n').filter(line => line.trim() !== '');
            // Get the last `limit` lines
            const recentLines = lines.slice(-limit);
            return recentLines.map(line => JSON.parse(line));
        }
        catch (e) {
            console.error('Failed to read audit log:', e);
            return [];
        }
    }
}
exports.AuditLogger = AuditLogger;
//# sourceMappingURL=audit.js.map