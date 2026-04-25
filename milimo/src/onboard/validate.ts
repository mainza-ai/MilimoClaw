// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Template Validation
 *
 * Validates template configuration by calling Python validation modules.
 */

import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";

export interface TemplateValidationResult {
  valid: boolean;
  errors: string[];
  config?: Record<string, unknown>;
}

export interface TemplateInfo {
  name: string;
  displayName: string;
  category: string;
  description: string;
  squadSize: number;
  clawsActive: string[];
}

export function validateTemplateFile(templatePath: string): TemplateValidationResult {
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

    const output = execFileSync("python3", ["-c", pythonScript], {
      encoding: "utf-8",
      timeout: 30000,
    });

    const result = JSON.parse(output) as TemplateValidationResult;
    return result;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { valid: false, errors: [`Validation failed: ${message}`] };
  }
}

export function getTemplateInfo(templatePath: string): TemplateInfo | null {
  const validation = validateTemplateFile(templatePath);
  if (!validation.valid || !validation.config) {
    return null;
  }

  const template = validation.config.template as Record<string, unknown>;
  if (!template) {
    return null;
  }

  return {
    name: template.name as string,
    displayName: template.display_name as string,
    category: template.category as string,
    description: template.description as string,
    squadSize: template.squad_size as number,
    clawsActive: template.claws_active as string[],
  };
}

function findBlueprintDir(templatePath: string): string | null {
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

export function validateSquadName(name: string): { valid: boolean; error?: string } {
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
    return {
      valid: false,
      error: "Squad name can only contain letters, numbers, hyphens, and underscores",
    };
  }

  return { valid: true };
}

export function validateOperatorName(name: string): { valid: boolean; error?: string } {
  if (!name || name.trim().length === 0) {
    return { valid: false, error: "Operator name cannot be empty" };
  }

  const trimmed = name.trim();

  if (trimmed.length > 100) {
    return { valid: false, error: "Operator name must be at most 100 characters" };
  }

  return { valid: true };
}

import { randomBytes } from "node:crypto";

export function generateMeshSecret(): string {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  const bytes = randomBytes(32);
  let secret = "";
  for (let i = 0; i < 32; i++) {
    secret += chars.charAt(bytes[i] % chars.length);
  }
  return secret;
}
