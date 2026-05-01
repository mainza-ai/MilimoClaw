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
exports.formatResumeDate = formatResumeDate;
exports.calculateResumeDate = calculateResumeDate;
exports.parseDurationDays = parseDurationDays;
/**
 * `openclaw milimo squad` — Squad lifecycle management.
 *
 * Subcommands: status, finals-mode, resume.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const init_js_1 = require("./init.js");
const python_bridge_js_1 = require("../lib/python-bridge.js");
function getFinalsModePath() {
    const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
    return path.join(home, ".openclaw/milimo", "finals-mode.json");
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
function getBlueprintDir() {
    const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
    return path.join(home, "milimo-blueprint");
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
        logger.info(" All claw policies restored to pre-finals configuration.");
    }
}
function cliSquadStatus(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        logger.info("No Milimo Claw configuration found.");
        logger.info('Run "milimo init" to set up your claw.');
        return Promise.resolve();
    }
    const finalsMode = loadFinalsMode();
    const assistant = state.assistant;
    const assistantLine = assistant
        ? `${assistant.name} ${assistant.emoji} (${assistant.creature} · ${assistant.vibe})`
        : "Not configured";
    const activeClawsDisplay = (state.activeClaws || []).join(", ");
    if (opts.json) {
        const output = {
            squad: state.squadName,
            role: state.clawRole,
            template: state.template,
            activeClaws: state.activeClaws || [],
            solo: state.solo,
            meshMembers: state.meshMembers,
            operator: state.operatorName,
            assistant: state.assistant,
            initializedAt: state.initializedAt,
            blueprintVersion: state.blueprintVersion,
            finalsMode: finalsMode?.active ?? false,
        };
        logger.info(JSON.stringify(output, null, 2));
        return Promise.resolve();
    }
    logger.info("");
    logger.info(" ┌─────────────────────────────────────────────────────┐");
    logger.info(" │ 🦀 SQUAD STATUS 🦀 │");
    logger.info(" └─────────────────────────────────────────────────────┘");
    logger.info("");
    logger.info(` Squad: ${state.squadName}`);
    logger.info(` Template: ${state.template}`);
    logger.info(` Active claws: ${activeClawsDisplay}`);
    logger.info(` Mode: ${state.solo ? "Solo" : "Mesh"}`);
    logger.info(` Operator: ${state.operatorName}`);
    logger.info(` Assistant: ${assistantLine}`);
    logger.info(` War Room: ${state.warRoomMode}`);
    logger.info(` Blueprint: v${state.blueprintVersion}`);
    logger.info(` Initialized: ${state.initializedAt?.split("T")[0] ?? "N/A"}`);
    if (finalsMode?.active) {
        logger.info("");
        logger.info(" ⚠️ FINALS MODE ACTIVE");
        logger.info(` Since: ${finalsMode.activatedAt}`);
        logger.info(` Duration: ${finalsMode.duration}`);
        if (finalsMode.resumeDate) {
            logger.info(` Resumes: ${finalsMode.resumeDate}`);
        }
    }
    if (!state.solo && state.meshMembers.length > 0) {
        logger.info("");
        logger.info(" Mesh Members:");
        for (const member of state.meshMembers) {
            logger.info(` • ${member}`);
        }
    }
    logger.info("");
    return Promise.resolve();
}
function cliSquadFinalsMode(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    const existingFinalsMode = loadFinalsMode();
    if (existingFinalsMode?.active) {
        logger.warn("Finals Mode is already active.");
        logger.info(` Activated: ${existingFinalsMode.activatedAt}`);
        logger.info(` Duration: ${existingFinalsMode.duration}`);
        logger.info(" To deactivate, run: openclaw milimo squad resume");
        return Promise.resolve();
    }
    if (!opts.duration && !opts.resumeDate) {
        logger.error("At least one of --duration or --resume-date is required.");
        logger.info(" Usage: openclaw milimo squad finals-mode --duration 2weeks");
        logger.info(" Usage: openclaw milimo squad finals-mode --resume-date 2026-04-01");
        return Promise.resolve();
    }
    let resumeDate = opts.resumeDate ?? null;
    if (!resumeDate && opts.duration) {
        const durationDays = parseDurationDays(opts.duration);
        if (durationDays > 0) {
            const resume = new Date();
            resume.setDate(resume.getDate() + durationDays);
            resumeDate = resume.toISOString().split("T")[0] ?? null;
        }
    }
    if (!resumeDate) {
        logger.error("Could not calculate resume date from duration.");
        return Promise.resolve();
    }
    const blueprintDir = getBlueprintDir();
    const response = (0, python_bridge_js_1.callPythonBridgeSafe)("activate_deep_work", { resume_date: resumeDate }, { blueprintDir });
    if (!response.success) {
        logger.error(`Failed to activate deep work mode: ${response.error}`);
        return Promise.resolve();
    }
    const data = response.data;
    if (!data) {
        logger.error("No data returned from deep work activation");
        return Promise.resolve();
    }
    const finalsModeState = {
        active: true,
        activatedAt: data["activated_at"] ?? new Date().toISOString(),
        duration: opts.duration,
        resumeDate: resumeDate,
        previousPolicies: (data["policy_changes"] ?? []).reduce((acc, change) => {
            acc[change.claw] = change.previous;
            return acc;
        }, {}),
    };
    saveFinalsMode(finalsModeState);
    logger.info("");
    logger.info(" ╔═══════════════════════════════════════════════════════╗");
    logger.info(" ║ 📚 FINALS MODE ACTIVATED 📚                           ║");
    logger.info(" ╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    const policyChanges = data["policy_changes"];
    if (policyChanges && policyChanges.length > 0) {
        logger.info(" Policy Changes:");
        for (const change of policyChanges) {
            const clawName = change.claw.charAt(0).toUpperCase() + change.claw.slice(1);
            logger.info(` → ${clawName}: ${change.previous} → ${change.new}`);
            if (change.blocked_actions && change.blocked_actions.length > 0) {
                logger.info(`   Blocked: ${change.blocked_actions.join(", ")}`);
            }
            if (change.queued_actions && change.queued_actions.length > 0) {
                logger.info(`   Queued: ${change.queued_actions.join(", ")}`);
            }
        }
    }
    else {
        logger.info(" All claws entering maintenance configuration:");
        logger.info(" → Content Claw: drafts paused, no new content");
        logger.info(" → Ops Claw: auto-response active for all clients");
        logger.info(" → Finance Claw: invoice sends continue, no new initiations");
        logger.info(" → Analytics Claw: passive monitoring only");
        if (state.meshMembers.includes("build")) {
            logger.info(" → Build Claw: deployments paused, monitoring only");
        }
    }
    logger.info("");
    logger.info(` Duration: ${opts.duration}`);
    logger.info(` Scheduled resume: ${resumeDate}`);
    logger.info("");
    logger.info(" To resume: openclaw milimo squad resume");
    logger.info("");
    return Promise.resolve();
}
function cliSquadResume(opts) {
    const { logger } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    const finalsMode = loadFinalsMode();
    if (!finalsMode?.active) {
        logger.info("Finals Mode is not active. Nothing to resume.");
        return Promise.resolve();
    }
    const blueprintDir = getBlueprintDir();
    const response = (0, python_bridge_js_1.callPythonBridgeSafe)("resume_deep_work", {}, { blueprintDir });
    if (!response.success) {
        logger.error(`Failed to resume from deep work mode: ${response.error}`);
        return Promise.resolve();
    }
    finalsMode.active = false;
    saveFinalsMode(finalsMode);
    const data = response.data;
    if (!data) {
        logger.info("");
        logger.info("Normal operations resumed.");
        logger.info("");
        return Promise.resolve();
    }
    logger.info("");
    logger.info(" ╔═══════════════════════════════════════════════════════╗");
    logger.info(" ║ 🚀 FINALS MODE DEACTIVATED 🚀                         ║");
    logger.info(" ╚═══════════════════════════════════════════════════════╝");
    logger.info("");
    const policiesRestored = data["policies_restored"];
    if (policiesRestored && policiesRestored.length > 0) {
        logger.info(" Policies Restored:");
        for (const claw of policiesRestored) {
            const clawName = claw.charAt(0).toUpperCase() + claw.slice(1);
            logger.info(` → ${clawName}: normal operations`);
        }
    }
    else {
        logger.info(" All claw policies restored to pre-finals configuration:");
        logger.info(" → Content Claw: draft generation resumed");
        logger.info(" → Ops Claw: reactivation messages sent to clients");
        logger.info(" → Finance Claw: full operations restored");
        logger.info(" → Analytics Claw: active monitoring and experiments resumed");
        if (state.meshMembers.includes("build")) {
            logger.info(" → Build Claw: deployments and sprints resumed");
        }
    }
    logger.info("");
    logger.info(" Welcome back. Let's get it. 💪");
    logger.info("");
    return Promise.resolve();
}
function parseDurationDays(duration) {
    const match = /^(\d+)\s*(day|days|week|weeks|month|months)$/i.exec(duration);
    if (!match)
        return 14;
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
function formatResumeDate(date) {
    return date.toISOString().split("T")[0] ?? "";
}
function calculateResumeDate(duration) {
    const days = parseDurationDays(duration);
    const resume = new Date();
    resume.setDate(resume.getDate() + days);
    return formatResumeDate(resume);
}
//# sourceMappingURL=squad.js.map