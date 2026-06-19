import * as fs from "node:fs";
import * as path from "node:path";
import { randomBytes } from "node:crypto";
import { parse as parseYaml } from "yaml";

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

  try {
    const raw = fs.readFileSync(templatePath, "utf-8");
    const config = parseYaml(raw) as Record<string, unknown>;

    if (!config || typeof config !== "object") {
      return { valid: false, errors: ["Template file is empty or invalid"] };
    }

    const errors: string[] = [];

    // Validate required top-level fields
    const template = config.template as Record<string, unknown> | undefined;
    if (!template || typeof template !== "object") {
      errors.push("Missing 'template' section");
    } else {
      const requiredFields = [
        "name",
        "display_name",
        "category",
        "description",
        "squad_size",
        "claws_active",
      ];
      for (const field of requiredFields) {
        if (!(field in template)) {
          errors.push(`Missing template field: ${field}`);
        }
      }
    }

    if (errors.length > 0) {
      return { valid: false, errors };
    }

    return { valid: true, errors: [], config };
  } catch (err) {
    return {
      valid: false,
      errors: [`Validation failed: ${err instanceof Error ? err.message : String(err)}`],
    };
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

export function generateMeshSecret(): string {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  const bytes = randomBytes(32);
  let secret = "";
  for (let i = 0; i < 32; i++) {
    secret += chars.charAt(bytes[i] % chars.length);
  }
  return secret;
}
