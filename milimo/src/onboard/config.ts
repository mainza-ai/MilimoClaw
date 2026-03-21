// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * MilimoClaw Configuration Manager
 *
 * Single source of truth for all Milimo configuration.
 * Consolidates former state.json and config.json into one file.
 * Provides migration from legacy dual-file system.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import type { ClawRole } from "../index.js";
import { encryptConfig, decryptConfig } from "../lib/config-encryption.js";

export const CONFIG_DIR = join(process.env.HOME ?? "/tmp", ".milimo");
const CONFIG_FILE = "config.json";
const LEGACY_STATE_FILE = "state.json";

export interface MilimoConfig {
    squadName: string;
    clawRole: ClawRole;
    template: string;
    solo: boolean;
    meshMembers: string[];
    meshSecret: string | null;
    operatorName: string;
    warRoomMode: "full" | "minimal" | "disabled";
    onboardedAt: string | null;
    initializedAt: string;
    blueprintVersion: string;
    serverUrl?: string;
    deep_work?: {
        active: boolean;
        activated_at: string;
        resume_date: string;
    };
}

export interface LegacyState {
  squadName: string;
  clawRole: ClawRole;
  template: string;
  solo: boolean;
  meshMembers: string[];
  initializedAt: string;
  blueprintVersion: string;
}

const DEFAULT_CONFIG: MilimoConfig = {
  squadName: "",
  clawRole: "" as ClawRole,
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

let configCache: MilimoConfig | null = null;

export function clearCache(): void {
  configCache = null;
}

function getConfigPath(): string {
  return join(CONFIG_DIR, CONFIG_FILE);
}

function getLegacyStatePath(): string {
  return join(CONFIG_DIR, LEGACY_STATE_FILE);
}

function ensureConfigDir(): void {
  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }
}

function validateConfig(data: unknown): data is MilimoConfig {
  if (typeof data !== "object" || data === null) return false;
  const cfg = data as Record<string, unknown>;
  return (
    typeof cfg["squadName"] === "string" &&
    typeof cfg["clawRole"] === "string" &&
    typeof cfg["template"] === "string" &&
    typeof cfg["solo"] === "boolean" &&
    Array.isArray(cfg["meshMembers"])
  );
}

function loadLegacyState(): LegacyState | null {
  const statePath = getLegacyStatePath();
  if (!existsSync(statePath)) return null;
  try {
    const raw = readFileSync(statePath, "utf-8");
    return JSON.parse(raw) as LegacyState;
  } catch {
    return null;
  }
}

function loadLegacyConfig(): Partial<MilimoConfig> | null {
  const configPath = getConfigPath();
  if (!existsSync(configPath)) return null;
  try {
    const raw = readFileSync(configPath, "utf-8");
    return JSON.parse(raw) as Partial<MilimoConfig>;
  } catch {
    return null;
  }
}

		export class ConfigManager {
	static load(): MilimoConfig | null {
		if (configCache) return configCache;

		ensureConfigDir();

		const legacyState = loadLegacyState();
		const legacyConfig = loadLegacyConfig();

		if (!legacyConfig && !legacyState) {
			return null;
		}

		const merged: MilimoConfig = {
			...DEFAULT_CONFIG,
			...(legacyState ?? {}),
			...(legacyConfig ?? {}),
		};

		if (legacyState && !legacyConfig?.onboardedAt) {
			merged.onboardedAt = legacyState.initializedAt;
		}

		const decrypted = decryptConfig(merged as unknown as Record<string, unknown>) as unknown as MilimoConfig;
		configCache = decrypted;
		return decrypted;
	}

	static save(config: MilimoConfig): void {
		ensureConfigDir();
		const configPath = getConfigPath();
		const encrypted = encryptConfig(config as unknown as Record<string, unknown>) as unknown as MilimoConfig;
		writeFileSync(configPath, JSON.stringify(encrypted, null, 2), { mode: 0o600 });
		configCache = config;
	}

  static migrate(): { migrated: boolean; hadLegacyState: boolean } {
    ensureConfigDir();

    const legacyState = loadLegacyState();
    const legacyConfig = loadLegacyConfig();
    const statePath = getLegacyStatePath();

    const hadLegacyState = existsSync(statePath);

    if (!legacyState && !legacyConfig) {
      return { migrated: false, hadLegacyState: false };
    }

    const merged: MilimoConfig = {
      ...DEFAULT_CONFIG,
      ...(legacyState ?? {}),
      ...(legacyConfig ?? {}),
    };

    if (legacyState && !legacyConfig?.onboardedAt) {
      merged.onboardedAt = legacyState.initializedAt;
    }

    ConfigManager.save(merged);

    if (existsSync(statePath)) {
      unlinkSync(statePath);
    }

    return { migrated: true, hadLegacyState };
  }

  static clear(): void {
    const configPath = getConfigPath();
    const statePath = getLegacyStatePath();
    if (existsSync(configPath)) {
      unlinkSync(configPath);
    }
    if (existsSync(statePath)) {
      unlinkSync(statePath);
    }
    configCache = null;
  }

  static getConfigDir(): string {
    return CONFIG_DIR;
  }

  static ensureDirectories(): void {
    ensureConfigDir();
    const subdirs = ["blueprints", "audit", "mesh", "evolution", "tools", "attestations", "keys", "health"];
    for (const subdir of subdirs) {
      const dir = join(CONFIG_DIR, subdir);
      if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
      }
    }
  }

  static hasLegacyState(): boolean {
    return existsSync(getLegacyStatePath());
  }
}

export function loadOnboardConfig(): MilimoConfig | null {
  return ConfigManager.load();
}

export function saveOnboardConfig(config: MilimoConfig): void {
  ConfigManager.save(config);
}

export function clearOnboardConfig(): void {
  ConfigManager.clear();
}

export { configPath } from "./config-legacy.js";

export function loadNemoClawConfig(): { model: string; endpointUrl: string } | null {
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

export { MilimoConfig as MilimoOnboardConfig };
