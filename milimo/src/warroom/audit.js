"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AuditLogger = void 0;
var fs_1 = require("fs");
var path_1 = require("path");
var os_1 = require("os");
var AuditLogger = /** @class */ (function () {
    function AuditLogger(squadId) {
        var home = process.env.HOME || process.env.USERPROFILE || (0, os_1.homedir)() || '/tmp';
        this.auditDir = (0, path_1.join)(home, '.milimo', 'audit', squadId);
        this.auditFile = (0, path_1.join)(this.auditDir, 'audit.jsonl');
        this.ensureDirectory();
    }
    AuditLogger.prototype.ensureDirectory = function () {
        if (!(0, fs_1.existsSync)(this.auditDir)) {
            (0, fs_1.mkdirSync)(this.auditDir, { recursive: true });
        }
    };
    AuditLogger.prototype.logAction = function (entry) {
        var fullEntry = __assign({ timestamp: new Date().toISOString() }, entry);
        // Append as a single line JSON (JSONL format)
        (0, fs_1.appendFileSync)(this.auditFile, JSON.stringify(fullEntry) + '\n', 'utf8');
    };
    AuditLogger.prototype.getRecentLogs = function (limit) {
        if (limit === void 0) { limit = 50; }
        if (!(0, fs_1.existsSync)(this.auditFile)) {
            return [];
        }
        try {
            var content = (0, fs_1.readFileSync)(this.auditFile, 'utf8');
            var lines = content.split('\n').filter(function (line) { return line.trim() !== ''; });
            // Get the last `limit` lines
            var recentLines = lines.slice(-limit);
            return recentLines.map(function (line) { return JSON.parse(line); });
        }
        catch (e) {
            console.error('Failed to read audit log:', e);
            return [];
        }
    };
    return AuditLogger;
}());
exports.AuditLogger = AuditLogger;
