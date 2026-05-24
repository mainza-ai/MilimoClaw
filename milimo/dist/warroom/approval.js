"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApprovalEngine = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
const os_1 = require("os");
const yaml_1 = require("yaml");
const audit_1 = require("./audit");
const rate_limiter_1 = require("./rate-limiter");
class ApprovalEngine {
    meshDir;
    warRoomInbox;
    audit;
    escalationRules = [];
    rateLimiter = null;
    tier = rate_limiter_1.Tier.FREE;
    constructor(squadId, tier = "free") {
        const home = process.env.HOME || process.env.USERPROFILE || (0, os_1.homedir)() || "/tmp";
        // Mesh data directory — supports both host and container environments
        // Container: /sandbox/.openclaw/milimo/mesh/ (Path.home() in Python)
        // Host: ~/.openclaw/milimo/mesh/
        const sandboxMesh = (0, path_1.join)("/sandbox", ".openclaw/milimo", "mesh");
        const homeMesh = (0, path_1.join)(home, ".openclaw/milimo", "mesh");
        this.meshDir = (0, fs_1.existsSync)(sandboxMesh) ? sandboxMesh : homeMesh;
        this.warRoomInbox = (0, path_1.join)(this.meshDir, "inbox", "war_room");
        this.audit = new audit_1.AuditLogger(squadId);
        this.tier = (0, rate_limiter_1.getTierFromString)(tier);
        // Initialize rate limiter
        try {
            this.rateLimiter = new rate_limiter_1.RateLimiter(this.tier, (0, path_1.join)(home, ".openclaw/milimo"));
        }
        catch (_e) {
            console.warn("Failed to initialize rate limiter:", _e);
        }
        this.loadEscalationRules();
    }
    loadEscalationRules() {
        try {
            // Try multiple locations: host, container blueprint, container sandbox
            const candidates = [
                (0, path_1.join)(process.cwd(), "milimo-blueprint", "mesh_config.yaml"),
                (0, path_1.join)(process.cwd(), "..", "milimo-blueprint", "mesh_config.yaml"),
                (0, path_1.join)("/sandbox", ".openclaw/milimo", "milimo-blueprint", "mesh_config.yaml"),
                (0, path_1.join)("/sandbox", ".openclaw/milimo", "blueprints", "0.1.0", "mesh_config.yaml"),
                (0, path_1.join)(process.cwd(), "mesh_config.yaml"),
            ];
            const configPath = candidates.find((p) => (0, fs_1.existsSync)(p));
            if (!configPath) {
                throw new Error("Config not found");
            }
            const content = (0, fs_1.readFileSync)(configPath, "utf8");
            const config = (0, yaml_1.parse)(content);
            if (config && config.escalation_rules) {
                this.escalationRules = config.escalation_rules.map((rule) => ({
                    trigger: rule.trigger,
                    action: rule.action.toUpperCase(),
                    description: rule.description,
                }));
            }
        }
        catch {
            console.warn("Failed to load escalation rules from mesh_config.yaml. Using defaults.");
            this.escalationRules = [
                {
                    trigger: "invoice_over_500",
                    action: "VETO",
                    description: "Any invoice >$500 requires squad-wide approval",
                },
            ];
        }
    }
    getPendingMessages() {
        try {
            const files = (0, fs_1.readdirSync)(this.warRoomInbox).filter((f) => f.endsWith(".json"));
            const messages = [];
            for (const file of files) {
                const filePath = (0, path_1.join)(this.warRoomInbox, file);
                try {
                    const content = (0, fs_1.readFileSync)(filePath, "utf8");
                    const msg = JSON.parse(content);
                    messages.push({
                        ...msg,
                        file_path: filePath,
                    });
                }
                catch (e) {
                    console.error(`Error reading message file ${filePath}:`, e);
                }
            }
            // Sort by timestamp (oldest first)
            return messages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        }
        catch {
            // Directory might not exist yet if no messages received
            return [];
        }
    }
    evaluateAction(message) {
        // 1. Check escalation triggers based on payload heuristics
        // Example: invoice_over_500
        if (message.message_type === "deliverable" &&
            message.payload &&
            message.payload.type === "invoice") {
            const amount = message.payload.amount || 0;
            if (amount > 500) {
                const rule = this.escalationRules.find((r) => r.trigger === "invoice_over_500");
                if (rule) {
                    return { mode: rule.action, trigger: rule.trigger, description: rule.description };
                }
            }
        }
        // Handle tool proposals based on evolution config
        if (message.message_type === "tool_proposal") {
            let requireApproval = false;
            try {
                const configPath = (0, path_1.join)(process.cwd(), "milimo-blueprint", "evolution_config.yaml");
                const content = (0, fs_1.readFileSync)(configPath, "utf8");
                const config = (0, yaml_1.parse)(content);
                if (config &&
                    config.deployment &&
                    typeof config.deployment.require_proposal_approval === "boolean") {
                    requireApproval = config.deployment.require_proposal_approval;
                }
            }
            catch {
                // Default to false if config not found
            }
            return requireApproval
                ? { mode: "REVIEW", description: "Tool proposal review" }
                : { mode: "AUTO" };
        }
        // Default modes based on needs_approval flag from Contracts
        if (message.needs_approval) {
            return { mode: "REVIEW" };
        }
        return { mode: "AUTO" };
    }
    processDecision(message, decision, operatorId = "system", reason) {
        this.audit.logAction({
            messageId: message.message_id,
            clawRole: message.sender_role,
            actionType: `WAR_ROOM_${decision}`,
            decision,
            operatorId,
            reason,
            details: {
                message_type: message.message_type,
                recipient: message.recipient_role,
            },
        });
        if (decision === "APPROVED") {
            // Move from war_room inbox to actual recipient inbox
            const targetInbox = (0, path_1.join)(this.meshDir, "inbox", message.recipient_role);
            const fileName = message.file_path.split("/").pop();
            const targetPath = (0, path_1.join)(targetInbox, fileName);
            try {
                (0, fs_1.renameSync)(message.file_path, targetPath);
            }
            catch (e) {
                console.error(`Failed to route approved message ${message.message_id}:`, e);
            }
        }
        else if (decision === "REJECTED") {
            // Move to rejected queue
            const rejectedDir = (0, path_1.join)(this.meshDir, "rejected");
            const fileName = message.file_path.split("/").pop();
            const targetPath = (0, path_1.join)(rejectedDir, fileName);
            try {
                (0, fs_1.renameSync)(message.file_path, targetPath);
            }
            catch (e) {
                console.error(`Failed to move rejected message ${message.message_id}:`, e);
            }
        }
        else if (decision === "DELEGATED") {
            // Leave it in the queue, perhaps tag it somehow in future
            // For now, no file move is strictly needed for HOLD
        }
    }
    autoProcessEligible() {
        const pending = this.getPendingMessages();
        for (const msg of pending) {
            const evaluation = this.evaluateAction(msg);
            if (evaluation.mode === "AUTO") {
                // Check rate limit before auto-approving
                if (this.rateLimiter) {
                    const rateResult = this.rateLimiter.tryConsume();
                    if (!rateResult.allowed) {
                        console.log(`Rate limit reached for auto-approval. Message ${msg.message_id} requires manual review.`);
                        this.audit.logAction({
                            messageId: msg.message_id,
                            clawRole: msg.sender_role,
                            actionType: "RATE_LIMITED",
                            decision: "DELEGATED",
                            operatorId: "rate-limiter",
                            reason: rateResult.reason || "Daily auto-approval limit exceeded",
                            details: {
                                remaining: rateResult.remaining,
                                resetAt: rateResult.resetAt,
                            },
                        });
                        continue; // Skip to next message, leave this for manual review
                    }
                }
                this.processDecision(msg, "APPROVED", "auto-engine", "Auto-approved per policy");
            }
        }
    }
    /**
     * Get rate limiter status for display in War Room.
     */
    getRateLimitStatus() {
        if (!this.rateLimiter) {
            return null;
        }
        const status = this.rateLimiter.getStatus();
        return {
            tier: status.tier,
            dailyRemaining: status.dailyRemaining,
            dailyLimit: status.dailyLimit,
            burstRemaining: status.burstRemaining,
            burstLimit: status.burstLimit,
            dailyResetAt: status.dailyResetAt,
            burstResetAt: status.burstResetAt,
        };
    }
}
exports.ApprovalEngine = ApprovalEngine;
//# sourceMappingURL=approval.js.map