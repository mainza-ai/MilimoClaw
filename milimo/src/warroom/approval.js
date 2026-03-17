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
exports.ApprovalEngine = void 0;
var fs_1 = require("fs");
var path_1 = require("path");
var os_1 = require("os");
var yaml_1 = require("yaml");
var audit_1 = require("./audit");
var ApprovalEngine = /** @class */ (function () {
    function ApprovalEngine(squadId) {
        this.escalationRules = [];
        var home = process.env.HOME || process.env.USERPROFILE || (0, os_1.homedir)() || '/tmp';
        this.meshDir = (0, path_1.join)(home, '.milimo', 'mesh');
        this.warRoomInbox = (0, path_1.join)(this.meshDir, 'inbox', 'war_room');
        this.audit = new audit_1.AuditLogger(squadId);
        this.loadEscalationRules();
    }
    ApprovalEngine.prototype.loadEscalationRules = function () {
        try {
            var configPath = (0, path_1.join)(process.cwd(), 'milimo-blueprint', 'mesh_config.yaml');
            var content = (0, fs_1.readFileSync)(configPath, 'utf8');
            var config = (0, yaml_1.parse)(content);
            if (config && config.escalation_rules) {
                this.escalationRules = config.escalation_rules.map(function (rule) { return ({
                    trigger: rule.trigger,
                    action: rule.action.toUpperCase(),
                    description: rule.description,
                }); });
            }
        }
        catch (e) {
            console.warn('Failed to load escalation rules from mesh_config.yaml. Using defaults.');
            this.escalationRules = [
                { trigger: 'invoice_over_500', action: 'VETO', description: 'Any invoice >$500 requires squad-wide approval' }
            ];
        }
    };
    ApprovalEngine.prototype.getPendingMessages = function () {
        try {
            var files = (0, fs_1.readdirSync)(this.warRoomInbox).filter(function (f) { return f.endsWith('.json'); });
            var messages = [];
            for (var _i = 0, files_1 = files; _i < files_1.length; _i++) {
                var file = files_1[_i];
                var filePath = (0, path_1.join)(this.warRoomInbox, file);
                try {
                    var content = (0, fs_1.readFileSync)(filePath, 'utf8');
                    var msg = JSON.parse(content);
                    messages.push(__assign(__assign({}, msg), { file_path: filePath }));
                }
                catch (e) {
                    console.error("Error reading message file ".concat(filePath, ":"), e);
                }
            }
            // Sort by timestamp (oldest first)
            return messages.sort(function (a, b) { return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(); });
        }
        catch (e) {
            // Directory might not exist yet if no messages received
            return [];
        }
    };
    ApprovalEngine.prototype.evaluateAction = function (message) {
        // 1. Check escalation triggers based on payload heuristics
        // Example: invoice_over_500
        if (message.message_type === 'deliverable' && message.payload && message.payload.type === 'invoice') {
            var amount = message.payload.amount || 0;
            if (amount > 500) {
                var rule = this.escalationRules.find(function (r) { return r.trigger === 'invoice_over_500'; });
                if (rule) {
                    return { mode: rule.action, trigger: rule.trigger, description: rule.description };
                }
            }
        }
        // Default modes based on needs_approval flag from Contracts
        if (message.needs_approval) {
            return { mode: 'REVIEW' };
        }
        return { mode: 'AUTO' };
    };
    ApprovalEngine.prototype.processDecision = function (message, decision, operatorId, reason) {
        if (operatorId === void 0) { operatorId = 'system'; }
        this.audit.logAction({
            messageId: message.message_id,
            clawRole: message.sender_role,
            actionType: "WAR_ROOM_".concat(decision),
            decision: decision,
            operatorId: operatorId,
            reason: reason,
            details: {
                message_type: message.message_type,
                recipient: message.recipient_role
            }
        });
        if (decision === 'APPROVED') {
            // Move from war_room inbox to actual recipient inbox
            var targetInbox = (0, path_1.join)(this.meshDir, 'inbox', message.recipient_role);
            var fileName = message.file_path.split('/').pop();
            var targetPath = (0, path_1.join)(targetInbox, fileName);
            try {
                (0, fs_1.renameSync)(message.file_path, targetPath);
            }
            catch (e) {
                console.error("Failed to route approved message ".concat(message.message_id, ":"), e);
            }
        }
        else if (decision === 'REJECTED') {
            // Move to rejected queue
            var rejectedDir = (0, path_1.join)(this.meshDir, 'rejected');
            var fileName = message.file_path.split('/').pop();
            var targetPath = (0, path_1.join)(rejectedDir, fileName);
            try {
                (0, fs_1.renameSync)(message.file_path, targetPath);
            }
            catch (e) {
                console.error("Failed to move rejected message ".concat(message.message_id, ":"), e);
            }
        }
        else if (decision === 'DELEGATED') {
            // Leave it in the queue, perhaps tag it somehow in future
            // For now, no file move is strictly needed for HOLD
        }
    };
    ApprovalEngine.prototype.autoProcessEligible = function () {
        var pending = this.getPendingMessages();
        for (var _i = 0, pending_1 = pending; _i < pending_1.length; _i++) {
            var msg = pending_1[_i];
            var evaluation = this.evaluateAction(msg);
            if (evaluation.mode === 'AUTO') {
                this.processDecision(msg, 'APPROVED', 'auto-engine', 'Auto-approved per policy');
            }
        }
    };
    return ApprovalEngine;
}());
exports.ApprovalEngine = ApprovalEngine;
