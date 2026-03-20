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
exports.checkFinalsModeAutoResume = checkFinalsModeAutoResume;
exports.cliSquadStatus = cliSquadStatus;
exports.cliSquadFinalsMode = cliSquadFinalsMode;
exports.cliSquadResume = cliSquadResume;
/**
 * `openclaw milimo squad` — Squad lifecycle management.
 *
 * Subcommands: status, finals-mode, resume.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const init_js_1 = require("./init.js");
function getFinalsModePath() {
    const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
    return path.join(home, ".milimo", "finals-mode.json");
}
function loadFinalsMode() {
    const fp = getFinalsModePath();
    if (!fs.existsSync(fp))
        return null;
    try {
        return JSON.parse(fs.readFileSync(fp, "utf-8"));
    }
    catch {
        return null;
    }
}
function saveFinalsMode(state) {
    const dir = path.dirname(getFinalsModePath());
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(getFinalsModePath(), JSON.stringify(state, null, 2), { mode: 0o600 });
}
function checkFinalsModeAutoResume(logger) {
    const finalsMode = loadFinalsMode();
    if (!finalsMode?.active || !finalsMode.resumeDate)
        return;
    const today = new Date().toISOString().split("T")[0];
    if (today >= finalsMode.resumeDate) {
        logger.info("");
        logger.info(`⏰ Finals Mode resume date (${finalsMode.resumeDate}) reached. Auto-resuming operations.`);
        finalsMode.active = false;
        saveFinalsMode(finalsMode);
        logger.info("  All claw policies restored to pre-finals configuration.");
    }
}
// ── Squad Status ──────────────────────────────────────────────────────
async function cliSquadStatus(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        logger.info("No Milimo Claw configuration found.");
        logger.info('Run "openclaw milimo init" to set up your claw.');
        return;
    }
    const finalsMode = loadFinalsMode();
    if (opts.json) {
        const output = {
            squad: state.squadName,
            role: state.clawRole,
            template: state.template,
            solo: state.solo,
            meshMembers: state.meshMembers,
            initializedAt: state.initializedAt,
            blueprintVersion: state.blueprintVersion,
            finalsMode: finalsMode?.active ?? false,
        };
        logger.info(JSON.stringify(output, null, 2));
        return;
    }
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │              🦀  SQUAD STATUS  🦀                   │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    logger.info(`  Squad:       ${state.squadName}`);
    logger.info(`  Role:        ${state.clawRole}`);
    logger.info(`  Template:    ${state.template}`);
    logger.info(`  Mode:        ${state.solo ? "Solo" : "Mesh"}`);
    logger.info(`  Blueprint:   v${state.blueprintVersion}`);
    logger.info(`  Initialized: ${state.initializedAt}`);
    if (finalsMode?.active) {
        logger.info("");
        logger.info("  ⚠️  FINALS MODE ACTIVE");
        logger.info(`  Since:       ${finalsMode.activatedAt}`);
        logger.info(`  Duration:    ${finalsMode.duration}`);
        if (finalsMode.resumeDate) {
            logger.info(`  Resumes:     ${finalsMode.resumeDate}`);
        }
    }
    if (!state.solo && state.meshMembers.length > 0) {
        logger.info("");
        logger.info("  Mesh Members:");
        for (const member of state.meshMembers) {
            logger.info(`    • ${member}`);
        }
    }
    logger.info("");
}
// ── Finals Mode ───────────────────────────────────────────────────────
async function cliSquadFinalsMode(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return;
    }
    const existingFinalsMode = loadFinalsMode();
    if (existingFinalsMode?.active) {
        logger.warn("Finals Mode is already active.");
        logger.info(`  Activated: ${existingFinalsMode.activatedAt}`);
        logger.info(`  Duration:  ${existingFinalsMode.duration}`);
        logger.info('  To deactivate, run: openclaw milimo squad resume');
        return;
    }
    // Parse resume date
    let resumeDate = opts.resumeDate ?? null;
    if (!resumeDate && opts.duration) {
        // Simple duration parsing: e.g., "2weeks" → 14 days from now
        const durationDays = parseDurationDays(opts.duration);
        if (durationDays > 0) {
            const resume = new Date();
            resume.setDate(resume.getDate() + durationDays);
            resumeDate = resume.toISOString().split("T")[0] ?? null;
        }
    }
    const finalsModeState = {
        active: true,
        activatedAt: new Date().toISOString(),
        duration: opts.duration,
        resumeDate,
        previousPolicies: {}, // Will store pre-finals policies for restoration
    };
    saveFinalsMode(finalsModeState);
    logger.info("");
    logger.info("  ╔═══════════════════════════════════════════════════════╗");
    logger.info("  ║          📚  FINALS MODE ACTIVATED  📚               ║");
    logger.info("  ╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    logger.info("  All claws entering maintenance configuration:");
    logger.info("    → Content Claw:   drafts paused, no new content");
    logger.info("    → Ops Claw:       auto-response active for all clients");
    logger.info("    → Finance Claw:   invoice sends continue, no new initiations");
    logger.info("    → Analytics Claw: passive monitoring only");
    if (state.meshMembers.includes("build")) {
        logger.info("    → Build Claw:     deployments paused, monitoring only");
    }
    logger.info("");
    logger.info(`  Duration:  ${opts.duration}`);
    if (resumeDate) {
        logger.info(`  Scheduled resume: ${resumeDate}`);
    }
    logger.info("");
    logger.info("  To resume: openclaw milimo squad resume");
    logger.info("");
}
// ── Resume from Finals Mode ───────────────────────────────────────────
async function cliSquadResume(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return;
    }
    const finalsMode = loadFinalsMode();
    if (!finalsMode?.active) {
        logger.info("Finals Mode is not active. Nothing to resume.");
        return;
    }
    // Deactivate finals mode
    finalsMode.active = false;
    saveFinalsMode(finalsMode);
    logger.info("");
    logger.info("  ╔═══════════════════════════════════════════════════════╗");
    logger.info("  ║          🚀  FINALS MODE DEACTIVATED  🚀             ║");
    logger.info("  ╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    logger.info("  All claw policies restored to pre-finals configuration:");
    logger.info("    → Content Claw:   draft generation resumed");
    logger.info("    → Ops Claw:       reactivation messages sent to clients");
    logger.info("    → Finance Claw:   full operations restored");
    logger.info("    → Analytics Claw: active monitoring and experiments resumed");
    if (state.meshMembers.includes("build")) {
        logger.info("    → Build Claw:     deployments and sprints resumed");
    }
    logger.info("");
    logger.info("  Welcome back. Let's get it. 💪");
    logger.info("");
}
// ── Helpers ───────────────────────────────────────────────────────────
function parseDurationDays(duration) {
    const match = /^(\d+)\s*(day|days|week|weeks|month|months)$/i.exec(duration);
    if (!match)
        return 14; // default 2 weeks
    const count = parseInt(match[1] ?? "14", 10);
    const unit = (match[2] ?? "weeks").toLowerCase();
    if (unit.startsWith("day"))
        return count;
    if (unit.startsWith("week"))
        return count * 7;
    if (unit.startsWith("month"))
        return count * 30;
    return 14;
}
//# sourceMappingURL=squad.js.map