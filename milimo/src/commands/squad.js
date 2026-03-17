"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliSquadStatus = cliSquadStatus;
exports.cliSquadFinalsMode = cliSquadFinalsMode;
exports.cliSquadResume = cliSquadResume;
/**
 * `openclaw milimo squad` — Squad lifecycle management.
 *
 * Subcommands: status, finals-mode, resume.
 */
var fs = require("node:fs");
var path = require("node:path");
var init_js_1 = require("./init.js");
function getFinalsModePath() {
    var _a, _b;
    var home = (_b = (_a = process.env["HOME"]) !== null && _a !== void 0 ? _a : process.env["USERPROFILE"]) !== null && _b !== void 0 ? _b : "/tmp";
    return path.join(home, ".milimo", "finals-mode.json");
}
function loadFinalsMode() {
    var fp = getFinalsModePath();
    if (!fs.existsSync(fp))
        return null;
    try {
        return JSON.parse(fs.readFileSync(fp, "utf-8"));
    }
    catch (_a) {
        return null;
    }
}
function saveFinalsMode(state) {
    var dir = path.dirname(getFinalsModePath());
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(getFinalsModePath(), JSON.stringify(state, null, 2), { mode: 384 });
}
// ── Squad Status ──────────────────────────────────────────────────────
function cliSquadStatus(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state, finalsMode, output, _i, _a, member;
        var _b;
        return __generator(this, function (_c) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.info("No Milimo Claw configuration found.");
                logger.info('Run "openclaw milimo init" to set up your claw.');
                return [2 /*return*/];
            }
            finalsMode = loadFinalsMode();
            if (opts.json) {
                output = {
                    squad: state.squadName,
                    role: state.clawRole,
                    template: state.template,
                    solo: state.solo,
                    meshMembers: state.meshMembers,
                    initializedAt: state.initializedAt,
                    blueprintVersion: state.blueprintVersion,
                    finalsMode: (_b = finalsMode === null || finalsMode === void 0 ? void 0 : finalsMode.active) !== null && _b !== void 0 ? _b : false,
                };
                logger.info(JSON.stringify(output, null, 2));
                return [2 /*return*/];
            }
            logger.info("");
            logger.info("  ┌─────────────────────────────────────────────────────┐");
            logger.info("  │              🦀  SQUAD STATUS  🦀                   │");
            logger.info("  └─────────────────────────────────────────────────────┘");
            logger.info("");
            logger.info("  Squad:       ".concat(state.squadName));
            logger.info("  Role:        ".concat(state.clawRole));
            logger.info("  Template:    ".concat(state.template));
            logger.info("  Mode:        ".concat(state.solo ? "Solo" : "Mesh"));
            logger.info("  Blueprint:   v".concat(state.blueprintVersion));
            logger.info("  Initialized: ".concat(state.initializedAt));
            if (finalsMode === null || finalsMode === void 0 ? void 0 : finalsMode.active) {
                logger.info("");
                logger.info("  ⚠️  FINALS MODE ACTIVE");
                logger.info("  Since:       ".concat(finalsMode.activatedAt));
                logger.info("  Duration:    ".concat(finalsMode.duration));
                if (finalsMode.resumeDate) {
                    logger.info("  Resumes:     ".concat(finalsMode.resumeDate));
                }
            }
            if (!state.solo && state.meshMembers.length > 0) {
                logger.info("");
                logger.info("  Mesh Members:");
                for (_i = 0, _a = state.meshMembers; _i < _a.length; _i++) {
                    member = _a[_i];
                    logger.info("    \u2022 ".concat(member));
                }
            }
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Finals Mode ───────────────────────────────────────────────────────
function cliSquadFinalsMode(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state, existingFinalsMode, resumeDate, durationDays, resume, finalsModeState;
        var _a, _b;
        return __generator(this, function (_c) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
                return [2 /*return*/];
            }
            existingFinalsMode = loadFinalsMode();
            if (existingFinalsMode === null || existingFinalsMode === void 0 ? void 0 : existingFinalsMode.active) {
                logger.warn("Finals Mode is already active.");
                logger.info("  Activated: ".concat(existingFinalsMode.activatedAt));
                logger.info("  Duration:  ".concat(existingFinalsMode.duration));
                logger.info('  To deactivate, run: openclaw milimo squad resume');
                return [2 /*return*/];
            }
            resumeDate = (_a = opts.resumeDate) !== null && _a !== void 0 ? _a : null;
            if (!resumeDate && opts.duration) {
                durationDays = parseDurationDays(opts.duration);
                if (durationDays > 0) {
                    resume = new Date();
                    resume.setDate(resume.getDate() + durationDays);
                    resumeDate = (_b = resume.toISOString().split("T")[0]) !== null && _b !== void 0 ? _b : null;
                }
            }
            finalsModeState = {
                active: true,
                activatedAt: new Date().toISOString(),
                duration: opts.duration,
                resumeDate: resumeDate,
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
            logger.info("  Duration:  ".concat(opts.duration));
            if (resumeDate) {
                logger.info("  Scheduled resume: ".concat(resumeDate));
            }
            logger.info("");
            logger.info("  To resume: openclaw milimo squad resume");
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Resume from Finals Mode ───────────────────────────────────────────
function cliSquadResume(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state, finalsMode;
        return __generator(this, function (_a) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
                return [2 /*return*/];
            }
            finalsMode = loadFinalsMode();
            if (!(finalsMode === null || finalsMode === void 0 ? void 0 : finalsMode.active)) {
                logger.info("Finals Mode is not active. Nothing to resume.");
                return [2 /*return*/];
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
            return [2 /*return*/];
        });
    });
}
// ── Helpers ───────────────────────────────────────────────────────────
function parseDurationDays(duration) {
    var _a, _b;
    var match = /^(\d+)\s*(day|days|week|weeks|month|months)$/i.exec(duration);
    if (!match)
        return 14; // default 2 weeks
    var count = parseInt((_a = match[1]) !== null && _a !== void 0 ? _a : "14", 10);
    var unit = ((_b = match[2]) !== null && _b !== void 0 ? _b : "weeks").toLowerCase();
    if (unit.startsWith("day"))
        return count;
    if (unit.startsWith("week"))
        return count * 7;
    if (unit.startsWith("month"))
        return count * 30;
    return 14;
}
