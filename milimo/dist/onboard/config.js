"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.configPath = exports.ConfigManager = exports.CONFIG_DIR = void 0;
exports.clearCache = clearCache;
exports.loadOnboardConfig = loadOnboardConfig;
exports.saveOnboardConfig = saveOnboardConfig;
exports.clearOnboardConfig = clearOnboardConfig;
exports.loadNemoClawConfig = loadNemoClawConfig;
exports.isNemoClawOnboarded = isNemoClawOnboarded;
/**
 * MilimoClaw Configuration Manager
 *
 * Single source of truth for all Milimo configuration.
 * Consolidates former state.json and config.json into one file.
 * Provides migration from legacy dual-file system.
 */
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const config_encryption_js_1 = require("../lib/config-encryption.js");
exports.CONFIG_DIR = (0, node_path_1.join)(process.env.HOME ?? "/tmp", ".milimo");
const CONFIG_FILE = "config.json";
const LEGACY_STATE_FILE = "state.json";
const DEFAULT_CONFIG = {
    squadName: "",
    clawRole: "",
    template: "",
    solo: true,
    meshMembers: [],
    meshSecret: null,
    operatorName: "operator",
    warRoomMode: "full",
    onboardedAt: null,
    initializedAt: new Date().toISOString(),
    blueprintVersion: "0.1.0",
};
let configCache = null;
function clearCache() {
    configCache = null;
}
function getConfigPath() {
    return (0, node_path_1.join)(exports.CONFIG_DIR, CONFIG_FILE);
}
function getLegacyStatePath() {
    return (0, node_path_1.join)(exports.CONFIG_DIR, LEGACY_STATE_FILE);
}
function ensureConfigDir() {
    if (!(0, node_fs_1.existsSync)(exports.CONFIG_DIR)) {
        (0, node_fs_1.mkdirSync)(exports.CONFIG_DIR, { recursive: true });
    }
}
function validateConfig(data) {
    if (typeof data !== "object" || data === null)
        return false;
    const cfg = data;
    return (typeof cfg["squadName"] === "string" &&
        typeof cfg["clawRole"] === "string" &&
        typeof cfg["template"] === "string" &&
        typeof cfg["solo"] === "boolean" &&
        Array.isArray(cfg["meshMembers"]));
}
function loadLegacyState() {
    const statePath = getLegacyStatePath();
    if (!(0, node_fs_1.existsSync)(statePath))
        return null;
    try {
        const raw = (0, node_fs_1.readFileSync)(statePath, "utf-8");
        return JSON.parse(raw);
    }
    catch {
        return null;
    }
}
function loadLegacyConfig() {
    const configPath = getConfigPath();
    if (!(0, node_fs_1.existsSync)(configPath))
        return null;
    try {
        const raw = (0, node_fs_1.readFileSync)(configPath, "utf-8");
        return JSON.parse(raw);
    }
    catch {
        return null;
    }
}
class ConfigManager {
    static load() {
        if (configCache)
            return configCache;
        ensureConfigDir();
        const legacyState = loadLegacyState();
        const legacyConfig = loadLegacyConfig();
        if (!legacyConfig && !legacyState) {
            return null;
        }
        const merged = {
            ...DEFAULT_CONFIG,
            ...(legacyState ?? {}),
            ...(legacyConfig ?? {}),
        };
        if (legacyState && !legacyConfig?.onboardedAt) {
            merged.onboardedAt = legacyState.initializedAt;
        }
        const decrypted = (0, config_encryption_js_1.decryptConfig)(merged);
        configCache = decrypted;
        return decrypted;
    }
    static save(config) {
        ensureConfigDir();
        const configPath = getConfigPath();
        const encrypted = (0, config_encryption_js_1.encryptConfig)(config);
        (0, node_fs_1.writeFileSync)(configPath, JSON.stringify(encrypted, null, 2), { mode: 0o600 });
        configCache = config;
    }
    static migrate() {
        ensureConfigDir();
        const legacyState = loadLegacyState();
        const legacyConfig = loadLegacyConfig();
        const statePath = getLegacyStatePath();
        const hadLegacyState = (0, node_fs_1.existsSync)(statePath);
        if (!legacyState && !legacyConfig) {
            return { migrated: false, hadLegacyState: false };
        }
        const merged = {
            ...DEFAULT_CONFIG,
            ...(legacyState ?? {}),
            ...(legacyConfig ?? {}),
        };
        if (legacyState && !legacyConfig?.onboardedAt) {
            merged.onboardedAt = legacyState.initializedAt;
        }
        ConfigManager.save(merged);
        if ((0, node_fs_1.existsSync)(statePath)) {
            (0, node_fs_1.unlinkSync)(statePath);
        }
        return { migrated: true, hadLegacyState };
    }
    static clear() {
        const configPath = getConfigPath();
        const statePath = getLegacyStatePath();
        if ((0, node_fs_1.existsSync)(configPath)) {
            (0, node_fs_1.unlinkSync)(configPath);
        }
        if ((0, node_fs_1.existsSync)(statePath)) {
            (0, node_fs_1.unlinkSync)(statePath);
        }
        configCache = null;
    }
    static getConfigDir() {
        return exports.CONFIG_DIR;
    }
    static ensureDirectories() {
        ensureConfigDir();
        const subdirs = ["blueprints", "audit", "mesh", "evolution", "tools", "attestations", "keys", "health"];
        for (const subdir of subdirs) {
            const dir = (0, node_path_1.join)(exports.CONFIG_DIR, subdir);
            if (!(0, node_fs_1.existsSync)(dir)) {
                (0, node_fs_1.mkdirSync)(dir, { recursive: true });
            }
        }
    }
    static hasLegacyState() {
        return (0, node_fs_1.existsSync)(getLegacyStatePath());
    }
}
exports.ConfigManager = ConfigManager;
function loadOnboardConfig() {
    return ConfigManager.load();
}
function saveOnboardConfig(config) {
    ConfigManager.save(config);
}
function clearOnboardConfig() {
    ConfigManager.clear();
}
var config_legacy_js_1 = require("./config-legacy.js");
Object.defineProperty(exports, "configPath", { enumerable: true, get: function () { return config_legacy_js_1.configPath; } });
function loadNemoClawConfig() {
    const nemoclawDir = (0, node_path_1.join)(process.env.HOME ?? "/tmp", ".nemoclaw");
    const nemoclawPath = (0, node_path_1.join)(nemoclawDir, "config.json");
    if ((0, node_fs_1.existsSync)(nemoclawPath)) {
        try {
            const raw = (0, node_fs_1.readFileSync)(nemoclawPath, "utf-8");
            const config = JSON.parse(raw);
            if (config.model && config.endpointUrl) {
                return { model: config.model, endpointUrl: config.endpointUrl };
            }
        }
        catch {
            // Fall through to OpenClaw config
        }
    }
    const openclawPath = (0, node_path_1.join)(process.env.HOME ?? "/tmp", ".openclaw", "openclaw.json");
    if ((0, node_fs_1.existsSync)(openclawPath)) {
        try {
            const raw = (0, node_fs_1.readFileSync)(openclawPath, "utf-8");
            const config = JSON.parse(raw);
            const primaryModel = config.agents?.defaults?.model?.primary;
            const providerId = primaryModel?.split("/")[0];
            const baseUrl = providerId ? config.models?.providers?.[providerId]?.baseUrl : undefined;
            if (primaryModel && baseUrl) {
                return { model: primaryModel, endpointUrl: baseUrl };
            }
        }
        catch {
            // Config parse error
        }
    }
    return null;
}
function isNemoClawOnboarded() {
    return loadNemoClawConfig() !== null;
}
//# sourceMappingURL=config.js.map