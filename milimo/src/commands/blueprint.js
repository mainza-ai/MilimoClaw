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
exports.cliBlueprintList = cliBlueprintList;
exports.cliBlueprintFork = cliBlueprintFork;
exports.cliBlueprintDiff = cliBlueprintDiff;
exports.cliBlueprintPublish = cliBlueprintPublish;
exports.cliBlueprintRollback = cliBlueprintRollback;
/**
 * `openclaw milimo blueprint` — Blueprint operations.
 *
 * Subcommands: list, fork, diff, publish, rollback.
 * Phase 0 implements list and stubs for fork/diff/publish/rollback.
 * Full marketplace integration arrives in Phase 3.
 */
var fs = require("node:fs");
var path = require("node:path");
var index_js_1 = require("../index.js");
var init_js_1 = require("./init.js");
function discoverBlueprints(blueprintDir) {
    var blueprints = [];
    // Discover role blueprints
    var rolesDir = path.join(blueprintDir, "roles");
    if (fs.existsSync(rolesDir)) {
        for (var _i = 0, _a = fs.readdirSync(rolesDir); _i < _a.length; _i++) {
            var file = _a[_i];
            if (!file.endsWith(".yaml") && !file.endsWith(".yml"))
                continue;
            var roleName = file.replace(/-claw\.ya?ml$/, "");
            blueprints.push({
                name: "".concat(roleName, "-claw"),
                type: "role",
                file: path.join(rolesDir, file),
                description: getRoleBlurb(roleName),
            });
        }
    }
    // Discover templates
    var templatesDir = path.join(blueprintDir, "templates");
    if (fs.existsSync(templatesDir)) {
        for (var _b = 0, _c = fs.readdirSync(templatesDir); _b < _c.length; _b++) {
            var file = _c[_b];
            if (!file.endsWith(".yaml") && !file.endsWith(".yml"))
                continue;
            var templateName = file.replace(/\.ya?ml$/, "");
            blueprints.push({
                name: templateName,
                type: "template",
                file: path.join(templatesDir, file),
                description: getTemplateBlurb(templateName),
            });
        }
    }
    return blueprints;
}
// ── Blueprint List ────────────────────────────────────────────────────
function cliBlueprintList(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, pluginConfig, blueprintDir, blueprints, roles, _i, roles_1, bp, _a, CLAW_ROLES_1, role, templates, _b, templates_1, bp;
        return __generator(this, function (_c) {
            logger = opts.logger, pluginConfig = opts.pluginConfig;
            blueprintDir = pluginConfig.blueprintDir;
            blueprints = discoverBlueprints(blueprintDir);
            if (opts.json) {
                logger.info(JSON.stringify(blueprints, null, 2));
                return [2 /*return*/];
            }
            logger.info("");
            logger.info("  ┌─────────────────────────────────────────────────────┐");
            logger.info("  │           🦀  AVAILABLE BLUEPRINTS  🦀              │");
            logger.info("  └─────────────────────────────────────────────────────┘");
            logger.info("");
            roles = blueprints.filter(function (b) { return b.type === "role"; });
            if (roles.length > 0) {
                logger.info("  Claw Roles:");
                for (_i = 0, roles_1 = roles; _i < roles_1.length; _i++) {
                    bp = roles_1[_i];
                    logger.info("    ".concat(bp.name.padEnd(20), " ").concat(bp.description));
                }
            }
            else {
                logger.info("  Claw Roles:");
                logger.info("    (built-in roles available)");
                for (_a = 0, CLAW_ROLES_1 = index_js_1.CLAW_ROLES; _a < CLAW_ROLES_1.length; _a++) {
                    role = CLAW_ROLES_1[_a];
                    logger.info("    ".concat((role + "-claw").padEnd(20), " ").concat(getRoleBlurb(role)));
                }
            }
            logger.info("");
            templates = blueprints.filter(function (b) { return b.type === "template"; });
            if (templates.length > 0) {
                logger.info("  Squad Templates:");
                for (_b = 0, templates_1 = templates; _b < templates_1.length; _b++) {
                    bp = templates_1[_b];
                    logger.info("    ".concat(bp.name.padEnd(20), " ").concat(bp.description));
                }
            }
            else {
                logger.info("  Squad Templates:");
                logger.info("    (no templates deployed yet — coming in Phase 0.6)");
            }
            logger.info("");
            logger.info("  Blueprint directory: ".concat(blueprintDir));
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Blueprint Fork ────────────────────────────────────────────────────
function cliBlueprintFork(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state, targetName, home, forkDir, forkMeta;
        var _a, _b, _c;
        return __generator(this, function (_d) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
                return [2 /*return*/];
            }
            targetName = (_a = opts.into) !== null && _a !== void 0 ? _a : "".concat(opts.source, "-fork");
            logger.info("");
            logger.info("  Forking blueprint: ".concat(opts.source));
            logger.info("  Into:              ".concat(targetName));
            logger.info("");
            home = (_c = (_b = process.env["HOME"]) !== null && _b !== void 0 ? _b : process.env["USERPROFILE"]) !== null && _c !== void 0 ? _c : "/tmp";
            forkDir = path.join(home, ".milimo", "blueprints", targetName);
            fs.mkdirSync(forkDir, { recursive: true });
            forkMeta = {
                name: targetName,
                forkedFrom: opts.source,
                forkedAt: new Date().toISOString(),
                version: "0.1.0",
                squad: state.squadName,
            };
            fs.writeFileSync(path.join(forkDir, "fork.json"), JSON.stringify(forkMeta, null, 2));
            logger.info("  \u2713 Fork metadata created at ~/.milimo/blueprints/".concat(targetName, "/"));
            logger.info("");
            logger.info("  Note: Full blueprint forking with marketplace integration");
            logger.info("  will be available in Phase 3 (Blueprint Economy).");
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Blueprint Diff ────────────────────────────────────────────────────
function cliBlueprintDiff(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state;
        return __generator(this, function (_a) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
                return [2 /*return*/];
            }
            logger.info("");
            logger.info("  Comparing blueprint versions: ".concat(opts.versionA, " \u2194 ").concat(opts.versionB));
            logger.info("");
            // Phase 0: stub — real diffing requires versioned blueprint storage
            logger.info("  Blueprint diff will show:");
            logger.info("    • Tool inventory changes");
            logger.info("    • Policy modifications");
            logger.info("    • Learned prior deltas");
            logger.info("    • Configuration drift");
            logger.info("");
            logger.info("  Note: Full blueprint diffing will be available once");
            logger.info("  blueprint versioning is implemented (Phase 1).");
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Blueprint Publish ─────────────────────────────────────────────────
function cliBlueprintPublish(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state, displayName;
        var _a;
        return __generator(this, function (_b) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
                return [2 /*return*/];
            }
            displayName = (_a = opts.name) !== null && _a !== void 0 ? _a : "".concat(state.squadName, "-").concat(state.clawRole, "-blueprint");
            logger.info("");
            logger.info("  📦 Blueprint Publish (Preview)");
            logger.info("");
            logger.info("  Name:     ".concat(displayName));
            logger.info("  Price:    ".concat(opts.price));
            logger.info("  Squad:    ".concat(state.squadName));
            logger.info("  Role:     ".concat(state.clawRole));
            logger.info("  Version:  v".concat(state.blueprintVersion));
            logger.info("");
            logger.info("  Note: Blueprint Marketplace launches in Phase 3.");
            logger.info("  Your blueprint will be publishable once the marketplace is live.");
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Blueprint Rollback ────────────────────────────────────────────────
function cliBlueprintRollback(opts) {
    return __awaiter(this, void 0, void 0, function () {
        var logger, state;
        return __generator(this, function (_a) {
            logger = opts.logger;
            state = (0, init_js_1.loadMilimoState)();
            if (!state) {
                logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
                return [2 /*return*/];
            }
            if (!opts.to) {
                logger.error("--to <version> is required for rollback.");
                return [2 /*return*/];
            }
            logger.info("");
            logger.info("  Rolling back blueprint to v".concat(opts.to));
            if (opts.reason) {
                logger.info("  Reason: ".concat(opts.reason));
            }
            logger.info("");
            // Phase 0: stub — real rollback requires versioned blueprint history
            logger.info("  Note: Full blueprint rollback requires version history.");
            logger.info("  This feature will be fully functional in Phase 1.");
            logger.info("");
            return [2 /*return*/];
        });
    });
}
// ── Helpers ───────────────────────────────────────────────────────────
function getRoleBlurb(role) {
    var _a;
    var blurbs = {
        content: "Creative output — posts, copy, brand voice",
        ops: "Client lifecycle — intake, delivery, follow-up",
        analytics: "Intelligence — performance, trends, signals",
        finance: "Financial ops — invoicing, pricing, margins",
        build: "Engineering — code, PRs, deploys, monitoring",
    };
    return (_a = blurbs[role]) !== null && _a !== void 0 ? _a : "Custom claw role";
}
function getTemplateBlurb(template) {
    var _a;
    var blurbs = {
        "content-agency": "Content + Ops + Analytics (social media agency)",
        "design-studio": "Content + Ops + Finance (design services)",
        "ai-micro-saas": "Build + Ops + Analytics + Finance (AI product)",
        "campus-ai-tool": "Build + Content + Ops (campus utility)",
    };
    return (_a = blurbs[template]) !== null && _a !== void 0 ? _a : "Custom squad template";
}
