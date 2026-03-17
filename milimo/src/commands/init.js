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
exports.loadMilimoState = loadMilimoState;
exports.cliInit = cliInit;
/**
 * `openclaw milimo init` — Squad initialization wizard.
 *
 * Phase 0.1 scope: template selection, role assignment, and local blueprint
 * deployment. Full mesh formation (0.4) and onboarding wizard (0.6) extend
 * this later.
 */
var fs = require("node:fs");
var path = require("node:path");
var index_js_1 = require("../index.js");
function getMilimoStateDir() {
    var _a, _b;
    var home = (_b = (_a = process.env["HOME"]) !== null && _a !== void 0 ? _a : process.env["USERPROFILE"]) !== null && _b !== void 0 ? _b : "/tmp";
    return path.join(home, ".milimo");
}
function getMilimoStatePath() {
    return path.join(getMilimoStateDir(), "state.json");
}
function loadMilimoState() {
    var statePath = getMilimoStatePath();
    if (!fs.existsSync(statePath)) {
        return null;
    }
    try {
        var raw = fs.readFileSync(statePath, "utf-8");
        return JSON.parse(raw);
    }
    catch (_a) {
        return null;
    }
}
function saveMilimoState(state) {
    var dir = getMilimoStateDir();
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(getMilimoStatePath(), JSON.stringify(state, null, 2), { mode: 384 });
}
/** List available templates from the blueprint directory. */
function listTemplates(blueprintDir) {
    var templatesDir = path.join(blueprintDir, "templates");
    if (!fs.existsSync(templatesDir)) {
        return [];
    }
    return fs
        .readdirSync(templatesDir)
        .filter(function (f) { return f.endsWith(".yaml") || f.endsWith(".yml"); })
        .map(function (f) { return f.replace(/\.ya?ml$/, ""); });
}
/** List available role blueprints from the blueprint directory. */
function listRoles(blueprintDir) {
    var rolesDir = path.join(blueprintDir, "roles");
    if (!fs.existsSync(rolesDir)) {
        return [];
    }
    return fs
        .readdirSync(rolesDir)
        .filter(function (f) { return f.endsWith(".yaml") || f.endsWith(".yml"); })
        .map(function (f) { return f.replace(/-claw\.ya?ml$/, "").replace(/\.ya?ml$/, ""); });
}
function cliInit(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, pluginConfig, existingState, squadName, roleStr, _i, CLAW_ROLES_1, role, desc, clawRole, template, blueprintDir, availableTemplates, availableRoles, stateDir, dirs, _a, dirs_1, dir, state;
        var _b, _c, _d;
        return __generator(this, function (_e) {
            logger = opts.logger, pluginConfig = opts.pluginConfig;
            existingState = loadMilimoState();
            if (existingState) {
                logger.warn("Already initialized as ".concat(existingState.clawRole, " claw in squad \"").concat(existingState.squadName, "\"."));
                logger.info("To reinitialize, remove ~/.milimo/state.json first.");
                return [2 /*return*/];
            }
            logger.info("");
            logger.info("  ╔═══════════════════════════════════════════════════════╗");
            logger.info("  ║          🦀  MILIMO CLAW — Squad Init  🦀            ║");
            logger.info("  ╚═══════════════════════════════════════════════════════╝");
            logger.info("");
            squadName = (_b = opts.squad) !== null && _b !== void 0 ? _b : pluginConfig.squadName;
            if (!squadName) {
                logger.error("Squad name is required. Use --squad <name> or set squadName in plugin config.");
                logger.info("");
                logger.info("  Example:");
                logger.info('    openclaw milimo init --squad "my-squad" --role content');
                return [2 /*return*/];
            }
            roleStr = (_c = opts.role) !== null && _c !== void 0 ? _c : pluginConfig.clawRole;
            if (!roleStr) {
                logger.error("Claw role is required. Use --role <role>.");
                logger.info("");
                logger.info("  Available roles:");
                for (_i = 0, CLAW_ROLES_1 = index_js_1.CLAW_ROLES; _i < CLAW_ROLES_1.length; _i++) {
                    role = CLAW_ROLES_1[_i];
                    desc = getRoleDescription(role);
                    logger.info("    ".concat(role.padEnd(12), " ").concat(desc));
                }
                return [2 /*return*/];
            }
            if (!index_js_1.CLAW_ROLES.includes(roleStr)) {
                logger.error("Invalid role \"".concat(roleStr, "\". Must be one of: ").concat(index_js_1.CLAW_ROLES.join(", ")));
                return [2 /*return*/];
            }
            clawRole = roleStr;
            template = (_d = opts.template) !== null && _d !== void 0 ? _d : "custom";
            blueprintDir = pluginConfig.blueprintDir;
            if (template !== "custom") {
                availableTemplates = listTemplates(blueprintDir);
                if (availableTemplates.length > 0 && !availableTemplates.includes(template)) {
                    logger.error("Template \"".concat(template, "\" not found."));
                    logger.info("  Available: ".concat(availableTemplates.join(", ")));
                    return [2 /*return*/];
                }
            }
            availableRoles = listRoles(blueprintDir);
            if (availableRoles.length > 0 && !availableRoles.includes(clawRole)) {
                logger.warn("Role blueprint \"".concat(clawRole, "-claw.yaml\" not found in ").concat(blueprintDir, "/roles/. Using base configuration."));
            }
            // Initialize
            logger.info("  Squad:     ".concat(squadName));
            logger.info("  Role:      ".concat(clawRole));
            logger.info("  Template:  ".concat(template));
            logger.info("  Mode:      ".concat(opts.solo ? "Solo" : "Mesh"));
            logger.info("");
            stateDir = getMilimoStateDir();
            dirs = [
                path.join(stateDir, "blueprints"),
                path.join(stateDir, "audit"),
                path.join(stateDir, "mesh"),
                path.join(stateDir, "evolution"),
            ];
            for (_a = 0, dirs_1 = dirs; _a < dirs_1.length; _a++) {
                dir = dirs_1[_a];
                fs.mkdirSync(dir, { recursive: true });
            }
            state = {
                squadName: squadName,
                clawRole: clawRole,
                template: template,
                solo: opts.solo,
                meshMembers: opts.solo ? [clawRole] : [],
                initializedAt: new Date().toISOString(),
                blueprintVersion: "0.1.0",
            };
            saveMilimoState(state);
            logger.info("  ✓ State directory created (~/.milimo/)");
            logger.info("  ✓ Blueprint directories initialized");
            logger.info("  ✓ Claw configuration saved");
            logger.info("");
            if (opts.solo) {
                logger.info("  Solo mode: claw is ready. No mesh formation needed.");
            }
            else {
                logger.info("  Next steps:");
                logger.info("    1. Have each squad member run: openclaw milimo init --squad");
                logger.info("       \"".concat(squadName, "\" --role <their-role>"));
                logger.info("    2. Run: openclaw milimo squad status");
                logger.info("       to verify the mesh topology");
            }
            logger.info("");
            logger.info("  Run 'openclaw milimo squad status' to see your configuration.");
            logger.info("");
            return [2 /*return*/];
        });
    });
}
function getRoleDescription(role) {
    var descriptions = {
        content: "Creative output — posts, copy, campaigns, brand voice",
        ops: "Client lifecycle — intake, scoping, delivery, follow-up",
        analytics: "Intelligence layer — performance, trends, opportunities",
        finance: "Financial ops — invoicing, pricing, margin tracking",
        build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
    };
    return descriptions[role];
}
