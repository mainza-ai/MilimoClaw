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
exports.validateTemplateFile = validateTemplateFile;
exports.getTemplateInfo = getTemplateInfo;
exports.validateSquadName = validateSquadName;
exports.validateOperatorName = validateOperatorName;
exports.generateMeshSecret = generateMeshSecret;
/**
 * Template Validation
 *
 * Validates template configuration by calling Python validation modules.
 */
const node_child_process_1 = require("node:child_process");
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
function validateTemplateFile(templatePath) {
    if (!fs.existsSync(templatePath)) {
        return { valid: false, errors: [`Template file not found: ${templatePath}`] };
    }
    const blueprintDir = findBlueprintDir(templatePath);
    if (!blueprintDir) {
        return { valid: false, errors: ["Could not find blueprint directory"] };
    }
    try {
        const pythonScript = `
import json
import sys
sys.path.insert(0, '${blueprintDir}')
from orchestrator.solo_init import load_solo_founder_template, TemplateValidationError

try:
    config = load_solo_founder_template('${templatePath}')
    print(json.dumps({"valid": True, "config": config}))
except TemplateValidationError as e:
    print(json.dumps({"valid": False, "errors": [str(e)]}))
except Exception as e:
    print(json.dumps({"valid": False, "errors": [f"Unexpected error: {e}"]}))
`;
        const output = (0, node_child_process_1.execFileSync)("python3", ["-c", pythonScript], {
            encoding: "utf-8",
            timeout: 30000,
        });
        const result = JSON.parse(output);
        return result;
    }
    catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return { valid: false, errors: [`Validation failed: ${message}`] };
    }
}
function getTemplateInfo(templatePath) {
    const validation = validateTemplateFile(templatePath);
    if (!validation.valid || !validation.config) {
        return null;
    }
    const template = validation.config.template;
    if (!template) {
        return null;
    }
    return {
        name: template.name,
        displayName: template.display_name,
        category: template.category,
        description: template.description,
        squadSize: template.squad_size,
        clawsActive: template.claws_active,
    };
}
function findBlueprintDir(templatePath) {
    let current = path.dirname(path.resolve(templatePath));
    while (current !== "/") {
        if (path.basename(current) === "milimo-blueprint") {
            return current;
        }
        const orchestratorDir = path.join(current, "orchestrator");
        if (fs.existsSync(orchestratorDir) && fs.statSync(orchestratorDir).isDirectory()) {
            return current;
        }
        current = path.dirname(current);
    }
    return null;
}
function validateSquadName(name) {
    if (!name || name.trim().length === 0) {
        return { valid: false, error: "Squad name cannot be empty" };
    }
    const trimmed = name.trim();
    if (trimmed.length < 2) {
        return { valid: false, error: "Squad name must be at least 2 characters" };
    }
    if (trimmed.length > 50) {
        return { valid: false, error: "Squad name must be at most 50 characters" };
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(trimmed)) {
        return { valid: false, error: "Squad name can only contain letters, numbers, hyphens, and underscores" };
    }
    return { valid: true };
}
function validateOperatorName(name) {
    if (!name || name.trim().length === 0) {
        return { valid: false, error: "Operator name cannot be empty" };
    }
    const trimmed = name.trim();
    if (trimmed.length > 100) {
        return { valid: false, error: "Operator name must be at most 100 characters" };
    }
    return { valid: true };
}
const node_crypto_1 = require("node:crypto");
function generateMeshSecret() {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    const bytes = (0, node_crypto_1.randomBytes)(32);
    let secret = "";
    for (let i = 0; i < 32; i++) {
        secret += chars.charAt(bytes[i] % chars.length);
    }
    return secret;
}
//# sourceMappingURL=validate.js.map
