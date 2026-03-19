// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * MilimoClaw Onboarding State Persistence
 *
 * Manages the ~/.milimo/config.json file for onboarding state.
 * Extends NemoClaw's config structure with squad-specific fields.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import type { ClawRole } from "../index.js";

export const CONFIG_DIR = join(process.env.HOME ?? "/tmp", ".milimo");

export interface MilimoOnboardConfig {
  squadName: string;
  clawRole: ClawRole;
  template: string;
  solo: boolean;
  meshMembers: string[];
  meshSecret: string | null;
  operatorName: string;
  warRoomMode: "full" | "minimal" | "disabled";
  onboardedAt: string;
  initializedAt: string;
  blueprintVersion: string;
}

let configDirCreated = false;

export function ensureConfigDir(): void {
  if (configDirCreated) return;
  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }
  configDirCreated = true;
}

export function configPath(): string {
  return join(CONFIG_DIR, "config.json");
}

export function loadOnboardConfig(): MilimoOnboardConfig | null {
  ensureConfigDir();
  const path = configPath();
  if (!existsSync(path)) {
    return null;
  }
  try {
    const raw = readFileSync(path, "utf-8");
    return JSON.parse(raw) as MilimoOnboardConfig;
  } catch {
    return null;
  }
}

export function saveOnboardConfig(config: MilimoOnboardConfig): void {
  ensureConfigDir();
  writeFileSync(configPath(), JSON.stringify(config, null, 2), { mode: 0o600 });
}

export function clearOnboardConfig(): void {
  const path = configPath();
  if (existsSync(path)) {
    unlinkSync(path);
  }
}

export function loadNemoClawConfig(): { model: string; endpointUrl: string } | null {
  // First, check NemoClaw's config
  const nemoclawDir = join(process.env.HOME ?? "/tmp", ".nemoclaw");
  const nemoclawPath = join(nemoclawDir, "config.json");
  
  if (existsSync(nemoclawPath)) {
    try {
      const raw = readFileSync(nemoclawPath, "utf-8");
      const config = JSON.parse(raw) as { model?: string; endpointUrl?: string };
      if (config.model && config.endpointUrl) {
        return { model: config.model, endpointUrl: config.endpointUrl };
      }
    } catch {
      // Fall through to OpenClaw config
    }
  }
  
  // Fall back to OpenClaw config (for Docker containers with pre-configured inference)
  const openclawPath = join(process.env.HOME ?? "/tmp", ".openclaw", "openclaw.json");
  if (existsSync(openclawPath)) {
    try {
      const raw = readFileSync(openclawPath, "utf-8");
      const config = JSON.parse(raw) as {
        agents?: { defaults?: { model?: { primary?: string } } };
        models?: { providers?: Record<string, { baseUrl?: string }> };
      };
      const primaryModel = config.agents?.defaults?.model?.primary;
      const providerId = primaryModel?.split("/")[0];
      const baseUrl = providerId ? config.models?.providers?.[providerId]?.baseUrl : undefined;
      
      if (primaryModel && baseUrl) {
        return { model: primaryModel, endpointUrl: baseUrl };
      }
    } catch {
      // Config parse error
    }
  }
  
  return null;
}

export function isNemoClawOnboarded(): boolean {
  return loadNemoClawConfig() !== null;
}
