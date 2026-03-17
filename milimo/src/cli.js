"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
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
exports.registerCliCommands = registerCliCommands;
var index_js_1 = require("./index.js");
var init_js_1 = require("./commands/init.js");
var squad_js_1 = require("./commands/squad.js");
var blueprint_js_1 = require("./commands/blueprint.js");
var warroom_js_1 = require("./commands/warroom.js");
function registerCliCommands(ctx, api) {
    var _this = this;
    var program = ctx.program, logger = ctx.logger;
    var pluginConfig = (0, index_js_1.getPluginConfig)(api);
    var milimo = program.command("milimo").description("Milimo Claw squad management");
    // ── openclaw milimo init ──────────────────────────────────────────
    milimo
        .command("init")
        .description("Initialize a new squad or join an existing mesh")
        .option("--squad <name>", "Squad name")
        .option("--role <role>", "Claw role: content, ops, analytics, finance, build")
        .option("--template <template>", "Squad template to use (e.g., content-agency, design-studio)")
        .option("--solo", "Initialize as a solo operator (no mesh)", false)
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, init_js_1.cliInit)(__assign(__assign({}, opts), { logger: logger, pluginConfig: pluginConfig }))];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    // ── openclaw milimo squad ─────────────────────────────────────────
    var squad = milimo.command("squad").description("Squad lifecycle management");
    squad
        .command("status")
        .description("Show squad topology, claw health, and mesh state")
        .option("--json", "Output as JSON", false)
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, squad_js_1.cliSquadStatus)({ json: opts.json, logger: logger, pluginConfig: pluginConfig })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    squad
        .command("finals-mode")
        .description("Activate Finals Mode — all claws enter maintenance configuration")
        .option("--duration <duration>", "Duration (e.g., 2weeks, 10days)", "2weeks")
        .option("--resume-date <date>", "Scheduled resume date (ISO format)")
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, squad_js_1.cliSquadFinalsMode)(__assign(__assign({}, opts), { logger: logger, pluginConfig: pluginConfig }))];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    squad
        .command("resume")
        .description("Resume from Finals Mode — restore all claw policies")
        .action(function () { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, squad_js_1.cliSquadResume)({ logger: logger, pluginConfig: pluginConfig })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    // ── openclaw milimo blueprint ─────────────────────────────────────
    var blueprint = milimo.command("blueprint").description("Blueprint operations");
    blueprint
        .command("list")
        .description("List available role blueprints and templates")
        .option("--json", "Output as JSON", false)
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, blueprint_js_1.cliBlueprintList)({ json: opts.json, logger: logger, pluginConfig: pluginConfig })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    blueprint
        .command("fork <source>")
        .description("Fork a public blueprint as your starting point")
        .option("--into <name>", "Name for the forked blueprint")
        .action(function (source, opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, blueprint_js_1.cliBlueprintFork)({ source: source, into: opts.into, logger: logger, pluginConfig: pluginConfig })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    blueprint
        .command("diff <versionA> <versionB>")
        .description("Compare two blueprint versions")
        .action(function (versionA, versionB) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, blueprint_js_1.cliBlueprintDiff)({ versionA: versionA, versionB: versionB, logger: logger, pluginConfig: pluginConfig })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    blueprint
        .command("publish")
        .description("Export your evolved blueprint to the marketplace")
        .option("--name <name>", "Display name for the listing")
        .option("--price <price>", "Price (e.g., 0.05eth, $25, free)", "free")
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, blueprint_js_1.cliBlueprintPublish)(__assign(__assign({}, opts), { logger: logger, pluginConfig: pluginConfig }))];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    blueprint
        .command("rollback")
        .description("Roll back to a previous blueprint version")
        .option("--to <version>", "Version to roll back to")
        .option("--reason <reason>", "Reason for rollback")
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, blueprint_js_1.cliBlueprintRollback)(__assign(__assign({}, opts), { logger: logger, pluginConfig: pluginConfig }))];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
    // ── openclaw milimo warroom ───────────────────────────────────────
    milimo
        .command("warroom")
        .description("Launch the War Room interactive operator dashboard")
        .option("-o, --operator <name>", "Override operator ID", "local-operator")
        .action(function (opts) { return __awaiter(_this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, (0, warroom_js_1.cliWarRoom)({ operator: opts.operator, logger: logger, pluginConfig: pluginConfig })];
                case 1:
                    _a.sent();
                    return [2 /*return*/];
            }
        });
    }); });
}
