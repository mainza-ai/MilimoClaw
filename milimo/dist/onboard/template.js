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
exports.getRoleDescription = getRoleDescription;
exports.discoverTemplates = discoverTemplates;
exports.loadTemplateMetadata = loadTemplateMetadata;
exports.discoverRoleBlueprints = discoverRoleBlueprints;
exports.getTemplateCategories = getTemplateCategories;
exports.filterTemplatesByCategory = filterTemplatesByCategory;
exports.getBuiltInTemplates = getBuiltInTemplates;
exports.resolveTemplatePath = resolveTemplatePath;
/**
 * Template Loading Utilities
 *
 * Discovers and loads templates from blueprint directories.
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const yaml = __importStar(require("yaml"));
const index_js_1 = require("../index.js");
const ROLE_DESCRIPTIONS = {
    content: "Creative output — posts, copy, campaigns, brand voice",
    ops: "Client lifecycle — intake, scoping, delivery, follow-up",
    analytics: "Intelligence layer — performance, trends, opportunities",
    finance: "Financial ops — invoicing, pricing, margin tracking",
    build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
    assistant: "AI helper — scheduling, research, cross-claw coordination, operator support",
    solo: "All claws active on this machine (solo mode)",
};
function getRoleDescription(role) {
    return ROLE_DESCRIPTIONS[role];
}
function discoverTemplates(blueprintDir) {
    const templatesDir = path.join(blueprintDir, "templates");
    if (!fs.existsSync(templatesDir)) {
        return [];
    }
    const templates = [];
    const files = fs.readdirSync(templatesDir);
    for (const file of files) {
        if (!file.endsWith(".yaml") && !file.endsWith(".yml")) {
            continue;
        }
        const templatePath = path.join(templatesDir, file);
        const template = loadTemplateMetadata(templatePath);
        if (template) {
            templates.push(template);
        }
    }
    return templates.sort((a, b) => a.name.localeCompare(b.name));
}
function loadTemplateMetadata(templatePath) {
    if (!fs.existsSync(templatePath)) {
        return null;
    }
    try {
        const content = fs.readFileSync(templatePath, "utf-8");
        const doc = yaml.parse(content);
        const template = doc?.template;
        if (!template) {
            return null;
        }
        const id = path.basename(templatePath, path.extname(templatePath));
        const clawsActive = (template.claws_active || []);
        return {
            id,
            name: template.name || id,
            displayName: template.display_name || template.name || id,
            description: template.description || "",
            category: template.category || "custom",
            path: templatePath,
            squadSize: template.squad_size || 1,
            clawsActive,
            solo: template.squad_size === 1 || clawsActive.length === 1,
        };
    }
    catch {
        return null;
    }
}
function discoverRoleBlueprints(blueprintDir) {
    const rolesDir = path.join(blueprintDir, "roles");
    if (!fs.existsSync(rolesDir)) {
        return getDefaultRoleBlueprints();
    }
    const blueprints = [];
    const files = fs.readdirSync(rolesDir);
    for (const file of files) {
        if (!file.endsWith(".yaml") && !file.endsWith(".yml")) {
            continue;
        }
        const blueprintPath = path.join(rolesDir, file);
        const roleMatch = file.match(/^([a-z]+)-claw\.ya?ml$/);
        if (roleMatch && index_js_1.CLAW_ROLES.includes(roleMatch[1])) {
            const role = roleMatch[1];
            blueprints.push({
                role,
                description: ROLE_DESCRIPTIONS[role],
                path: blueprintPath,
            });
        }
    }
    for (const role of index_js_1.CLAW_ROLES) {
        if (!blueprints.find((b) => b.role === role)) {
            blueprints.push({
                role,
                description: ROLE_DESCRIPTIONS[role],
                path: "",
            });
        }
    }
    return blueprints.sort((a, b) => a.role.localeCompare(b.role));
}
function getDefaultRoleBlueprints() {
    return index_js_1.CLAW_ROLES.map((role) => ({
        role,
        description: ROLE_DESCRIPTIONS[role],
        path: "",
    }));
}
function getTemplateCategories(templates) {
    const categories = new Set();
    for (const template of templates) {
        categories.add(template.category);
    }
    return Array.from(categories).sort();
}
function filterTemplatesByCategory(templates, category) {
    return templates.filter((t) => t.category === category);
}
function getBuiltInTemplates() {
    return [
        {
            id: "solo-founder",
            name: "solo-founder",
            displayName: "Solo Founder",
            description: "All 6 claws on one machine. One operator. The full product.",
            category: "solo",
            path: "",
            squadSize: 1,
            clawsActive: index_js_1.CLAW_ROLES.slice(),
            solo: true,
        },
        {
            id: "content-agency",
            name: "content-agency",
            displayName: "Content Agency",
            description: "Creative output, client management, and performance intelligence.",
            category: "creative",
            path: "",
            squadSize: 3,
            clawsActive: ["content", "ops", "analytics"],
            solo: false,
        },
        {
            id: "design-studio",
            name: "design-studio",
            displayName: "Design Studio",
            description: "Creative output, client lifecycle, and financial tracking.",
            category: "creative",
            path: "",
            squadSize: 3,
            clawsActive: ["content", "ops", "finance"],
            solo: false,
        },
        {
            id: "event-promotion",
            name: "event-promotion",
            displayName: "Event Promotion",
            description: "Content, operations, and audience intelligence for events.",
            category: "creative",
            path: "",
            squadSize: 3,
            clawsActive: ["content", "ops", "analytics"],
            solo: false,
        },
        {
            id: "freelance-collective",
            name: "freelance-collective",
            displayName: "Freelance Collective",
            description: "Client management, analytics, and financial operations.",
            category: "commerce",
            path: "",
            squadSize: 3,
            clawsActive: ["ops", "analytics", "finance"],
            solo: false,
        },
        {
            id: "ai-micro-saas",
            name: "ai-micro-saas",
            displayName: "AI Micro-SaaS",
            description: "Full engineering, operations, analytics, and financial stack.",
            category: "tech",
            path: "",
            squadSize: 4,
            clawsActive: ["build", "ops", "analytics", "finance"],
            solo: false,
        },
        {
            id: "campus-ai-tool",
            name: "campus-ai-tool",
            displayName: "Campus AI Tool",
            description: "Engineering, content, and operations for campus products.",
            category: "tech",
            path: "",
            squadSize: 3,
            clawsActive: ["build", "content", "ops"],
            solo: false,
        },
        {
            id: "custom",
            name: "custom",
            displayName: "Custom Configuration",
            description: "Manual configuration from scratch",
            category: "custom",
            path: "",
            squadSize: 0,
            clawsActive: [],
            solo: false,
        },
    ];
}
function resolveTemplatePath(templateId, blueprintDir) {
    const builtIn = getBuiltInTemplates().find((t) => t.id === templateId);
    if (builtIn && builtIn.id === "custom") {
        return null;
    }
    const templatesDir = path.join(blueprintDir, "templates");
    const candidates = [
        path.join(templatesDir, `${templateId}.yaml`),
        path.join(templatesDir, `${templateId}.yml`),
    ];
    for (const candidate of candidates) {
        if (fs.existsSync(candidate)) {
            return candidate;
        }
    }
    return null;
}
//# sourceMappingURL=template.js.map