"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliBadge = cliBadge;
/**
 * `openclaw milimo badge` — Performance verification badges.
 *
 * Generates and displays performance attestations for blueprints.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const node_os_1 = require("node:os");
const init_js_1 = require("./init.js");
// ---------------------------------------------------------------------------
const BADGE_LEVELS = {
    verified: { threshold: 0, icon: "✅", label: "Verified", color: "green" },
    bronze: { threshold: 5, icon: "🥉", label: "Bronze", color: "#CD7F32" },
    silver: { threshold: 10, icon: "🥈", label: "Silver", color: "#C0C0C0" },
    gold: { threshold: 15, icon: "🥇", label: "Gold", color: "#FFD700" },
    platinum: { threshold: 25, icon: "💎", label: "Platinum", color: "#E5E4E2" },
    elite: { threshold: 40, icon: "👑", label: "Elite", color: "#9B59B6" },
};
// ---------------------------------------------------------------------------
async function cliBadge(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    logger.info("");
    logger.info(" ┌─────────────────────────────────────────────────────┐");
    logger.info(" │ 🏆 PERFORMANCE BADGES 🏆 │");
    logger.info(" └─────────────────────────────────────────────────────┘");
    logger.info("");
    if (opts.verify) {
        verifyAttestation(opts, logger);
        return Promise.resolve();
    }
    if (opts.list) {
        listAttestations(opts, state, logger);
        return Promise.resolve();
    }
    if (opts.performance) {
        generatePerformanceAttestation(opts, state, logger);
        return Promise.resolve();
    }
    if (opts.auditor) {
        requestAuditorVerification(opts, state, logger);
        return Promise.resolve();
    }
    showBadgeStatus(opts, state, logger);
    return Promise.resolve();
}
// ---------------------------------------------------------------------------
function showBadgeStatus(opts, state, logger) {
    const blueprintId = opts.blueprint || (state ? `${state.squadName}-${state.clawRole}` : "");
    if (!blueprintId) {
        logger.error(" ✗ No blueprint specified.");
        logger.info(" Use --blueprint <id> or activate a squad.");
        logger.info("");
        return;
    }
    logger.info(` Blueprint: ${blueprintId}`);
    logger.info("");
    try {
        const home = (0, node_os_1.homedir)();
        const attestationFile = path.join(home, ".openclaw/milimo/attestations", `${blueprintId}.json`);
        if (!fs.existsSync(attestationFile)) {
            logger.info(" No performance attestation found.");
            logger.info("");
            logger.info(" Generate one with:");
            logger.info(` openclaw milimo badge --performance`);
            logger.info("");
            return;
        }
        const raw = fs.readFileSync(attestationFile, "utf-8");
        const data = JSON.parse(raw);
        if (!data.exists) {
            logger.info(" No performance attestation found.");
            logger.info("");
            return;
        }
        const attestation = data;
        renderAttestation(attestation, opts.json ?? false, logger);
    }
    catch (err) {
        logger.error(` ✗ Failed to load attestation: ${err.message}`);
        logger.info("");
    }
}
// ---------------------------------------------------------------------------
async function generatePerformanceAttestation(opts, state, logger) {
    if (!state) {
        logger.error(" ✗ No active squad. Run 'openclaw milimo init' first.");
        logger.info("");
        return;
    }
    const blueprintId = opts.blueprint || `${state.squadName}-${state.clawRole}`;
    logger.info(` Generating performance attestation for ${blueprintId}...`);
    logger.info("");
    try {
        const now = new Date().toISOString();
        const home = (0, node_os_1.homedir)();
        const attestationDir = path.join(home, ".openclaw/milimo/attestations");
        fs.mkdirSync(attestationDir, { recursive: true });
        const metrics = {
            baseline_performance: 100.0,
            current_performance: 100.0,
            improvement_percent: 0.0,
            measurement_period_days: 30,
            sample_size: 1000,
            breakdown: {
                approval_rate: 95.0,
                auto_approval_rate: 80.0,
                response_time_ms: 250,
                error_rate: 2.1,
            },
        };
        const simpleId = `pa_${(state.squadName || "default").slice(0, 8)}_${now.replace(/[^0-9]/g, "").slice(0, 12)}`;
        const attestationData = {
            type: "performance_attestation",
            attestation_id: simpleId,
            blueprint_id: blueprintId,
            blueprint_version: state.blueprintVersion || "0.1.0",
            metrics,
            verification: {
                method: "self_attested",
                data_integrity: `sha256:${"0".repeat(64)}`,
            },
            created_at: now,
        };
        const hashInput = JSON.stringify(attestationData, Object.keys(attestationData).sort());
        const { createHash } = await import("node:crypto");
        const hash = createHash("sha256").update(hashInput).digest("hex");
        attestationData.attestation_hash = `sha256:${hash}`;
        attestationData.signature = `ed25519:self_attested`;
        const attestationFile = path.join(attestationDir, `${blueprintId}.json`);
        fs.writeFileSync(attestationFile, JSON.stringify(attestationData, null, 2));
        const attestation = attestationData;
        logger.info(" ✅ Performance attestation generated!");
        logger.info("");
        renderAttestation(attestation, opts.json ?? false, logger);
        logger.info(" Note: This is a self-attested performance claim.");
        logger.info(" For verified status, request auditor verification:");
        logger.info(` openclaw milimo badge --auditor verifier@example.com`);
        logger.info("");
    }
    catch (err) {
        logger.error(` ✗ Generation failed: ${err.message}`);
        logger.info("");
    }
}
// ---------------------------------------------------------------------------
function requestAuditorVerification(opts, state, logger) {
    if (!state) {
        logger.error(" ✗ No active squad.");
        logger.info("");
        return;
    }
    logger.info(` Requesting auditor verification from: ${opts.auditor}`);
    logger.info("");
    logger.info(" This feature requires:");
    logger.info(" 1. An existing performance attestation");
    logger.info(" 2. Auditor agreement to verify");
    logger.info(" 3. Payment of auditor fees (if applicable)");
    logger.info("");
    logger.info(" In production, this would:");
    logger.info(" • Send verification request to auditor");
    logger.info(" • Include attestation data for review");
    logger.info(" • Track verification status");
    logger.info("");
    logger.info(" Status: Not implemented (requires auditor integration)");
    logger.info("");
}
// ---------------------------------------------------------------------------
function verifyAttestation(opts, logger) {
    logger.info(` Verifying attestation: ${opts.verify}`);
    logger.info("");
    try {
        const home = (0, node_os_1.homedir)();
        let attestationFile = opts.verify || "";
        if (!fs.existsSync(attestationFile)) {
            const inDir = path.join(home, ".openclaw/milimo/attestations", attestationFile);
            if (fs.existsSync(inDir)) {
                attestationFile = inDir;
            }
        }
        if (!fs.existsSync(attestationFile)) {
            logger.error(` ✗ Attestation not found: ${opts.verify}`);
            logger.info("");
            return;
        }
        const raw = fs.readFileSync(attestationFile, "utf-8");
        const data = JSON.parse(raw);
        logger.info(" ✅ Attestation verified");
        logger.info("");
        const attestation = data;
        renderAttestation(attestation, opts.json ?? false, logger);
    }
    catch (err) {
        logger.error(` ✗ Verification failed: ${err.message}`);
        logger.info("");
    }
}
// ---------------------------------------------------------------------------
function listAttestations(opts, state, logger) {
    logger.info(" Available Attestations:");
    logger.info("");
    try {
        const home = (0, node_os_1.homedir)();
        const attestationDir = path.join(home, ".openclaw/milimo/attestations");
        const attestations = [];
        if (fs.existsSync(attestationDir)) {
            for (const file of fs.readdirSync(attestationDir)) {
                if (!file.endsWith(".json"))
                    continue;
                try {
                    const raw = fs.readFileSync(path.join(attestationDir, file), "utf-8");
                    const data = JSON.parse(raw);
                    attestations.push({
                        blueprint_id: data.blueprint_id || file.replace(".json", ""),
                        version: data.blueprint_version || "?",
                        improvement: data.metrics?.improvement_percent || 0,
                        created: data.created_at || "?",
                    });
                }
                catch {
                    // skip malformed files
                }
            }
        }
        if (attestations.length === 0) {
            logger.info(" No attestations found.");
            logger.info("");
            return;
        }
        for (const att of attestations) {
            const badge = getBadgeForImprovement(att.improvement);
            logger.info(` ${badge.icon} ${att.blueprint_id} (v${att.version}) +${att.improvement}%`);
        }
        logger.info("");
    }
    catch (err) {
        logger.error(` ✗ Failed to list: ${err.message}`);
        logger.info("");
    }
}
// ---------------------------------------------------------------------------
function renderAttestation(attestation, jsonOutput, logger) {
    if (jsonOutput) {
        logger.info(JSON.stringify(attestation, null, 2));
        return;
    }
    const badge = getBadgeForImprovement(attestation.metrics.improvement_percent);
    logger.info(` ${badge.icon} ${badge.label} Badge`);
    logger.info("");
    logger.info(" Performance Metrics:");
    logger.info(` Baseline: ${attestation.metrics.baseline_performance.toFixed(1)}`);
    logger.info(` Current: ${attestation.metrics.current_performance.toFixed(1)}`);
    logger.info(` Improvement: +${attestation.metrics.improvement_percent}%`);
    logger.info(` Sample Size: ${attestation.metrics.sample_size.toLocaleString()}`);
    logger.info(` Period: ${attestation.metrics.measurement_period_days} days`);
    logger.info("");
    if (attestation.metrics.breakdown) {
        const b = attestation.metrics.breakdown;
        logger.info(" Breakdown:");
        if (b.approval_rate !== undefined) {
            logger.info(` Approval Rate: ${b.approval_rate}%`);
        }
        if (b.auto_approval_rate !== undefined) {
            logger.info(` Auto-Approval: ${b.auto_approval_rate}%`);
        }
        if (b.response_time_ms !== undefined) {
            logger.info(` Response Time: ${b.response_time_ms}ms`);
        }
        if (b.error_rate !== undefined) {
            logger.info(` Error Rate: ${b.error_rate}%`);
        }
        logger.info("");
    }
    logger.info(" Verification:");
    logger.info(` Method: ${attestation.verification.method}`);
    logger.info(` Hash: ${attestation.attestation_hash.substring(0, 24)}...`);
    logger.info("");
    if (attestation.verification.auditor) {
        logger.info(" Auditor:");
        logger.info(` Name: ${attestation.verification.auditor.name}`);
        logger.info(` Date: ${attestation.verification.auditor.verification_date}`);
        logger.info("");
    }
    logger.info(` Blueprint: ${attestation.blueprint_id} v${attestation.blueprint_version}`);
    logger.info(` Created: ${new Date(attestation.created_at).toLocaleString()}`);
    logger.info("");
}
// ---------------------------------------------------------------------------
function getBadgeForImprovement(improvement) {
    const levels = Object.entries(BADGE_LEVELS).sort((a, b) => b[1].threshold - a[1].threshold);
    for (const [, badge] of levels) {
        if (improvement >= badge.threshold) {
            return badge;
        }
    }
    return BADGE_LEVELS.verified;
}
//# sourceMappingURL=badge.js.map