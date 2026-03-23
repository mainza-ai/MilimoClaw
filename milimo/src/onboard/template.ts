// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Template Loading Utilities
 *
 * Discovers and loads templates from blueprint directories.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import * as yaml from "yaml";
import type { ClawRole } from "../index.js";
import { CLAW_ROLES } from "../index.js";
import type { TemplateInfo } from "./validate.js";

export interface TemplateDiscovery {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: string;
  path: string;
  squadSize: number;
  clawsActive: ClawRole[];
  solo: boolean;
}

export interface RoleBlueprint {
  role: ClawRole;
  description: string;
  path: string;
}

const ROLE_DESCRIPTIONS: Record<ClawRole, string> = {
  content: "Creative output — posts, copy, campaigns, brand voice",
  ops: "Client lifecycle — intake, scoping, delivery, follow-up",
  analytics: "Intelligence layer — performance, trends, opportunities",
  finance: "Financial ops — invoicing, pricing, margin tracking",
  build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
  solo: "All claws active on this machine (solo mode)",
};

export function getRoleDescription(role: ClawRole): string {
  return ROLE_DESCRIPTIONS[role];
}

export function discoverTemplates(blueprintDir: string): TemplateDiscovery[] {
  const templatesDir = path.join(blueprintDir, "templates");
  
  if (!fs.existsSync(templatesDir)) {
    return [];
  }

  const templates: TemplateDiscovery[] = [];
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

export function loadTemplateMetadata(templatePath: string): TemplateDiscovery | null {
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
    const clawsActive = (template.claws_active || []) as ClawRole[];

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
  } catch {
    return null;
  }
}

export function discoverRoleBlueprints(blueprintDir: string): RoleBlueprint[] {
  const rolesDir = path.join(blueprintDir, "roles");

  if (!fs.existsSync(rolesDir)) {
    return getDefaultRoleBlueprints();
  }

  const blueprints: RoleBlueprint[] = [];
  const files = fs.readdirSync(rolesDir);

  for (const file of files) {
    if (!file.endsWith(".yaml") && !file.endsWith(".yml")) {
      continue;
    }

    const blueprintPath = path.join(rolesDir, file);
    const roleMatch = file.match(/^([a-z]+)-claw\.ya?ml$/);

    if (roleMatch && CLAW_ROLES.includes(roleMatch[1] as ClawRole)) {
      const role = roleMatch[1] as ClawRole;
      blueprints.push({
        role,
        description: ROLE_DESCRIPTIONS[role],
        path: blueprintPath,
      });
    }
  }

  for (const role of CLAW_ROLES) {
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

function getDefaultRoleBlueprints(): RoleBlueprint[] {
  return CLAW_ROLES.map((role) => ({
    role,
    description: ROLE_DESCRIPTIONS[role],
    path: "",
  }));
}

export function getTemplateCategories(templates: TemplateDiscovery[]): string[] {
  const categories = new Set<string>();
  for (const template of templates) {
    categories.add(template.category);
  }
  return Array.from(categories).sort();
}

export function filterTemplatesByCategory(
  templates: TemplateDiscovery[],
  category: string,
): TemplateDiscovery[] {
  return templates.filter((t) => t.category === category);
}

export function getBuiltInTemplates(): TemplateDiscovery[] {
  return [
    {
      id: "solo-founder",
      name: "solo-founder",
      displayName: "Solo Founder",
      description: "All 5 claws on one machine. One operator. The full product.",
      category: "solo",
      path: "",
      squadSize: 1,
      clawsActive: CLAW_ROLES.slice() as ClawRole[],
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
      clawsActive: ["content", "ops", "analytics"] as ClawRole[],
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
      clawsActive: ["content", "ops", "finance"] as ClawRole[],
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
      clawsActive: ["content", "ops", "analytics"] as ClawRole[],
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
      clawsActive: ["ops", "analytics", "finance"] as ClawRole[],
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
      clawsActive: ["build", "ops", "analytics", "finance"] as ClawRole[],
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
      clawsActive: ["build", "content", "ops"] as ClawRole[],
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

export function resolveTemplatePath(
  templateId: string,
  blueprintDir: string,
): string | null {
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
