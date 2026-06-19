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
exports.cliBlueprintList = cliBlueprintList;
exports.cliBlueprintFork = cliBlueprintFork;
exports.cliBlueprintDiff = cliBlueprintDiff;
exports.cliBlueprintPublish = cliBlueprintPublish;
exports.cliBlueprintRollback = cliBlueprintRollback;
exports.cliBlueprintSearch = cliBlueprintSearch;
exports.cliBlueprintMerge = cliBlueprintMerge;
exports.cliBlueprintInfo = cliBlueprintInfo;
/**
 * `openclaw milimo blueprint` — Blueprint operations.
 *
 * Subcommands: list, fork, diff, publish, rollback, search, merge, info.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const init_js_1 = require("./init.js");
const python_bridge_1 = require("../lib/python-bridge");
/**
 * Helper to call Python logic via RPC bridge.
 */
async function callPython(blueprintDir, code) {
    const safeCode = `import sys; sys.path.insert(0, ${JSON.stringify(blueprintDir)}); ${code}`;
    const result = await (0, python_bridge_1.callPython)(blueprintDir, safeCode);
    return result;
}
function discoverBlueprints(blueprintDir) {
    const blueprints = [];
    // Discover role blueprints
    const rolesDir = path.join(blueprintDir, "roles");
    if (fs.existsSync(rolesDir)) {
        for (const file of fs.readdirSync(rolesDir)) {
            if (!file.endsWith(".yaml") && !file.endsWith(".yml"))
                continue;
            const roleName = file.replace(/-claw\.ya?ml$/, "").replace(/\.ya?ml$/, "");
            blueprints.push({
                name: `${roleName}-claw`,
                type: "role",
                file: path.join(rolesDir, file),
                description: getRoleBlurb(roleName),
            });
        }
    }
    // Discover templates
    const templatesDir = path.join(blueprintDir, "templates");
    if (fs.existsSync(templatesDir)) {
        for (const file of fs.readdirSync(templatesDir)) {
            if (!file.endsWith(".yaml") && !file.endsWith(".yml"))
                continue;
            const templateName = file.replace(/\.ya?ml$/, "");
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
async function cliBlueprintList(opts) {
    const { logger, pluginConfig } = opts;
    const blueprintDir = pluginConfig.blueprintDir;
    const blueprints = discoverBlueprints(blueprintDir);
    const state = (0, init_js_1.loadMilimoState)();
    let activeInventory = null;
    let currentVersion = "0.1.0";
    if (state) {
        try {
            const code = `from orchestrator.blueprint_manager import BlueprintManager; from orchestrator.tool_registry import ToolRegistry; reg = ToolRegistry('${state.squadName}', '${state.clawRole}'); mgr = BlueprintManager('${state.squadName}', '${state.clawRole}', '${blueprintDir}', tool_registry=reg); import json; print(json.dumps({'version': mgr.current_version(), 'tools': reg.get_inventory()}))`;
            const result = await callPython(blueprintDir, code);
            const output = JSON.parse(result);
            currentVersion = output.version;
            activeInventory = output.tools;
        }
        catch (err) {
            logger.debug(`Could not load active blueprint state: ${err.message}`);
        }
    }
    if (opts.json) {
        logger.info(JSON.stringify({ catalog: blueprints, active: { version: currentVersion, tools: activeInventory } }, null, 2));
        return Promise.resolve();
    }
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │           🦀  MILIMO BLUEPRINT STATUS  🦀           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    if (state) {
        logger.info(`  Active Squad:  ${state.squadName}`);
        logger.info(`  Claw Role:     ${state.clawRole}`);
        logger.info(`  Current Ver:   v${currentVersion}`);
        logger.info("");
        logger.info("  Evolved Tools:");
        if (activeInventory && Object.keys(activeInventory).length > 0) {
            for (const [name, tool] of Object.entries(activeInventory)) {
                const mark = tool.status === "deployed" ? "🟢" : "🔴";
                logger.info(`    ${mark} ${name.padEnd(20)} v${tool.version} (+${tool.performance_delta.toFixed(1)}% uplift)`);
            }
        }
        else {
            logger.info("    (no evolved tools deployed yet)");
        }
        logger.info("");
    }
    logger.info("  Blueprint Catalog:");
    // List roles
    const roles = blueprints.filter((b) => b.type === "role");
    if (roles.length > 0) {
        logger.info("    Claw Roles:");
        for (const bp of roles) {
            logger.info(`      ${bp.name.padEnd(18)} ${bp.description}`);
        }
    }
    // List templates
    const templates = blueprints.filter((b) => b.type === "template");
    if (templates.length > 0) {
        logger.info("    Squad Templates:");
        for (const bp of templates) {
            logger.info(`      ${bp.name.padEnd(18)} ${bp.description}`);
        }
    }
    logger.info("");
    logger.info(` Blueprint directory: ${blueprintDir}`);
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Fork ────────────────────────────────────────────────────
async function cliBlueprintFork(opts) {
    const { logger, pluginConfig } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    const blueprintDir = pluginConfig.blueprintDir;
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    const targetName = opts.into ?? `${opts.source.replace(/^@/, "").replace(/\//, "-")}-fork`;
    logger.info("");
    logger.info(`  Forking blueprint: ${opts.source}`);
    logger.info(`  Into:              ${targetName}`);
    logger.info("");
    try {
        const code = `from orchestrator.marketplace_manager import MarketplaceManager; mgr = MarketplaceManager(); snapshot = mgr.download('${opts.source}'); import json; print(json.dumps(snapshot.to_dict()) if snapshot else 'None')`;
        const result = await callPython(blueprintDir, code);
        if (result === "None") {
            logger.error(` ✗ Blueprint ${opts.source} not found in marketplace.`);
            return Promise.resolve();
        }
        const snapshot = JSON.parse(result);
        // Locally save the forked blueprint
        const home = process.env["HOME"] ?? process.env["USERPROFILE"] ?? "/tmp";
        const forkDir = path.join(home, ".openclaw/milimo", "blueprints", targetName);
        fs.mkdirSync(forkDir, { recursive: true });
        fs.writeFileSync(path.join(forkDir, "v0.1.0.json"), JSON.stringify(snapshot, null, 2));
        logger.info(` ✓ Blueprint forked and saved to ~/.openclaw/milimo/blueprints/${targetName}/`);
    }
    catch (err) {
        logger.error(`  ✗ Error forking blueprint: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Diff ────────────────────────────────────────────────────
async function cliBlueprintDiff(opts) {
    const { logger, pluginConfig } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    const blueprintDir = pluginConfig.blueprintDir;
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    logger.info("");
    logger.info(" ┌─────────────────────────────────────────────────────┐");
    logger.info(" │ 🦀 BLUEPRINT DIFF 🦀 │");
    logger.info(" └─────────────────────────────────────────────────────┘");
    logger.info("");
    logger.info(`  Versions: ${opts.versionA} ↔ ${opts.versionB}`);
    logger.info("");
    try {
        const code = `from orchestrator.blueprint_manager import BlueprintManager; mgr = BlueprintManager('${state.squadName}', '${state.clawRole}', '${blueprintDir}'); diff = mgr.diff('${opts.versionA}', '${opts.versionB}'); import json; print(json.dumps({'tools_added': diff.tools_added, 'tools_removed': diff.tools_removed, 'tools_modified': diff.tools_modified, 'policy_changes': diff.policy_changes, 'config_changes': diff.config_changes}))`;
        const result = await callPython(blueprintDir, code);
        const diff = JSON.parse(result);
        if (diff.tools_added.length > 0) {
            logger.info("  Tools Added:");
            for (const t of diff.tools_added)
                logger.info(`    + ${t}`);
        }
        if (diff.tools_removed.length > 0) {
            logger.info("  Tools Removed:");
            for (const t of diff.tools_removed)
                logger.info(`    - ${t}`);
        }
        if (diff.tools_modified.length > 0) {
            logger.info("  Tools Modified:");
            for (const t of diff.tools_modified)
                logger.info(`    ~ ${t}`);
        }
        if (Object.keys(diff.policy_changes).length > 0) {
            logger.info("");
            logger.info("  Policy Changes:");
            for (const [k, v] of Object.entries(diff.policy_changes)) {
                logger.info(`    ${k}: ${JSON.stringify(v.from)} → ${JSON.stringify(v.to)}`);
            }
        }
        if (Object.keys(diff.config_changes).length > 0) {
            logger.info("");
            logger.info("  Config Changes:");
            for (const [k, v] of Object.entries(diff.config_changes)) {
                logger.info(`    ${k}: ${JSON.stringify(v.from)} → ${JSON.stringify(v.to)}`);
            }
        }
        if (diff.tools_added.length === 0 &&
            diff.tools_removed.length === 0 &&
            diff.tools_modified.length === 0 &&
            Object.keys(diff.policy_changes).length === 0) {
            logger.info("  No significant changes detected.");
        }
    }
    catch (err) {
        logger.error(`  ✗ Error diffing blueprints: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Publish ─────────────────────────────────────────────────
async function cliBlueprintPublish(opts) {
    const { logger, pluginConfig } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    const blueprintDir = pluginConfig.blueprintDir;
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    const displayName = opts.name ?? `${state.squadName}-${state.clawRole}-blueprint`;
    logger.info("");
    logger.info("  📦 Blueprint Publish");
    logger.info("");
    logger.info(`  Name:     ${displayName}`);
    logger.info(`  Price:    ${opts.price}`);
    logger.info(`  Squad:    ${state.squadName}`);
    logger.info(`  Role:     ${state.clawRole}`);
    logger.info(`  Version:  v${state.blueprintVersion}`);
    logger.info("");
    try {
        const code = `from orchestrator.blueprint_manager import BlueprintManager; from orchestrator.marketplace_manager import MarketplaceManager; mgr = BlueprintManager('${state.squadName}', '${state.clawRole}', '${blueprintDir}'); market = MarketplaceManager(); snapshot = mgr.export(); id = market.publish(snapshot, '${opts.price}', '${displayName}', '${state.squadName}'); print(id)`;
        const result = await callPython(blueprintDir, code);
        logger.info(`  ✓ Published to marketplace with ID: ${result}`);
    }
    catch (err) {
        logger.error(`  ✗ Error publishing blueprint: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Rollback ────────────────────────────────────────────────
async function cliBlueprintRollback(opts) {
    const { logger, pluginConfig } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    const blueprintDir = pluginConfig.blueprintDir;
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    if (!opts.to) {
        logger.error("--to <version> is required for rollback.");
        return Promise.resolve();
    }
    logger.info("");
    logger.info(`  Rolling back blueprint to v${opts.to}`);
    if (opts.reason) {
        logger.info(`  Reason: ${opts.reason}`);
    }
    logger.info("");
    try {
        const code = `from orchestrator.blueprint_manager import BlueprintManager; mgr = BlueprintManager('${state.squadName}', '${state.clawRole}', '${blueprintDir}'); print(mgr.rollback('${opts.to}', '${opts.reason || ""}'))`;
        const result = await callPython(blueprintDir, code);
        if (result === "True") {
            // Sync local state
            state.blueprintVersion = opts.to;
            (0, init_js_1.saveMilimoState)(state);
            logger.info(`  ✓ Successfully rolled back to v${opts.to}`);
        }
        else {
            logger.error(`  ✗ Rollback failed. Version v${opts.to} might not exist.`);
        }
    }
    catch (err) {
        logger.error(`  ✗ Error during rollback: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Search ─────────────────────────────────────────────────
async function cliBlueprintSearch(opts) {
    const { logger, pluginConfig } = opts;
    const blueprintDir = pluginConfig.blueprintDir;
    logger.info("");
    logger.info("  🔍 Searching Blueprint Marketplace...");
    if (opts.query)
        logger.info(`     Query:    ${opts.query}`);
    if (opts.category)
        logger.info(`     Category: ${opts.category}`);
    logger.info("");
    try {
        const code = `from orchestrator.marketplace_manager import MarketplaceManager; mgr = MarketplaceManager(); results = mgr.search('${opts.query || ""}', '${opts.category || ""}'); import json; print(json.dumps(results))`;
        const result = await callPython(blueprintDir, code);
        const listings = JSON.parse(result);
        if (listings.length === 0) {
            logger.info("  No blueprints found matching your criteria.");
        }
        else {
            logger.info("  ID".padEnd(35) + "Author".padEnd(15) + "Price".padEnd(10) + "Verified");
            logger.info("  " + "─".repeat(70));
            for (const l of listings) {
                const verified = l.verified ? "✅" : "❌";
                logger.info(`  ${l.id.padEnd(33)} ${l.author.padEnd(14)} ${l.price.padEnd(9)} ${verified}`);
            }
        }
    }
    catch (err) {
        logger.error(`  ✗ Error searching marketplace: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Merge ──────────────────────────────────────────────────
async function cliBlueprintMerge(opts) {
    const { logger, pluginConfig } = opts;
    const state = (0, init_js_1.loadMilimoState)();
    const blueprintDir = pluginConfig.blueprintDir;
    if (!state) {
        logger.error("No Milimo Claw configuration found. Run 'openclaw milimo init' first.");
        return Promise.resolve();
    }
    logger.info("");
    logger.info(`  🤝 Merging blueprint: ${opts.incoming}`);
    logger.info("");
    try {
        const code = `from orchestrator.blueprint_manager import BlueprintManager; from orchestrator.blueprint_merger import BlueprintMerger; from orchestrator.marketplace_manager import MarketplaceManager; mgr = BlueprintManager('${state.squadName}', '${state.clawRole}', '${blueprintDir}'); market = MarketplaceManager(); base = mgr._load_snapshot(mgr.current_version()); incoming_snap = market.download('${opts.incoming}') or mgr._load_snapshot('${opts.incoming}'); merged = BlueprintMerger.merge(base, incoming_snap); mgr.bump_version('merged with ${opts.incoming}'); import json; snapshot_file = mgr._versions_dir / f'v{mgr.current_version()}.json'; merged.meta.version = mgr.current_version(); with snapshot_file.open("w") as f: json.dump(merged.to_dict(), f, indent=2, default=str); print(mgr.current_version())`;
        const result = await callPython(blueprintDir, code);
        logger.info(`  ✓ Successfully merged. New version: v${result}`);
    }
    catch (err) {
        logger.error(`  ✗ Error during merge: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Blueprint Info ───────────────────────────────────────────────────
async function cliBlueprintInfo(opts) {
    const { logger, pluginConfig } = opts;
    const blueprintDir = pluginConfig.blueprintDir;
    logger.info("");
    logger.info(`  ℹ️  Fetching blueprint details: ${opts.blueprintId}`);
    logger.info("");
    try {
        const code = `from orchestrator.marketplace_manager import MarketplaceManager; mgr = MarketplaceManager(); info = mgr.get_listing('${opts.blueprintId}'); import json; print(json.dumps(info) if info else 'None')`;
        const result = await callPython(blueprintDir, code);
        if (result === "None") {
            logger.error(` ✗ Blueprint ${opts.blueprintId} not found.`);
            return Promise.resolve();
        }
        const info = JSON.parse(result);
        logger.info(`  ID:          ${info.id}`);
        logger.info(`  Name:        ${info.name}`);
        logger.info(`  Author:      ${info.author}`);
        logger.info(`  Version:     v${info.version}`);
        logger.info(`  Price:       ${info.price}`);
        logger.info(`  Tools:       ${info.tool_count}`);
        logger.info(`  Forks:       ${info.fork_count}`);
        logger.info(`  Published:   ${info.published_at}`);
        logger.info(`  Verified:    ${info.verified ? "YES ✅" : "NO ❌"}`);
        if (info.tags && info.tags.length > 0) {
            logger.info(`  Tags:        ${info.tags.join(", ")}`);
        }
    }
    catch (err) {
        logger.error(` ✗ Error fetching info: ${err.message}`);
    }
    logger.info("");
    return Promise.resolve();
}
// ── Helpers ───────────────────────────────────────────────────────────
function getRoleBlurb(role) {
    const blurbs = {
        content: "Creative output — posts, copy, brand voice",
        ops: "Client lifecycle — intake, delivery, follow-up",
        analytics: "Intelligence — performance, trends, signals",
        finance: "Financial ops — invoicing, pricing, margins",
        build: "Engineering — code, PRs, deploys, monitoring",
    };
    return blurbs[role] ?? "Custom claw role";
}
function getTemplateBlurb(template) {
    const blurbs = {
        "content-agency": "Content + Ops + Analytics (social media agency)",
        "design-studio": "Content + Ops + Finance (design services)",
        "ai-micro-saas": "Build + Ops + Analytics + Finance (AI product)",
        "campus-ai-tool": "Build + Content + Ops (campus utility)",
    };
    return blurbs[template] ?? "Custom squad template";
}
//# sourceMappingURL=blueprint.js.map