// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

// MilimoClaw Hermes Config Generator
// Adapted from NemoHermes generate-config.ts to include milimo-hermes plugin

import { randomBytes } from "node:crypto";
import { Buffer } from "node:buffer";
import { chmodSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { toYaml } from "./config/yaml.ts";

const API_SERVER_TOOLSETS = [
  "web",
  "browser",
  "terminal",
  "file",
  "code_execution",
  "vision",
  "image_gen",
  "skills",
  "todo",
  "memory",
  "session_search",
  "delegation",
  "cronjob",
  "nemoclaw",
  "milimo-hermes",
  "audio",
];

type MessagingAllowedIds = Record<string, (string | number)[]>;
type DiscordGuilds = Record<string, { requireMention?: boolean; users?: (string | number)[] }>;
type TelegramConfig = { requireMention?: boolean };
type WechatConfig = { accountId?: string; baseUrl?: string; userId?: string };
type SlackConfig = { allowedChannels?: string[] };

type HermesBuildSettings = {
  model: string;
  inferenceProviderId: string;
  baseUrl: string;
  providerKey: string;
  inferenceApi: string;
  managedToolGateways: {
    brokerEnabled: boolean;
    presets: string[];
  };
  messaging: {
    enabledChannels: Set<string>;
    allowedIds: MessagingAllowedIds;
    discordGuilds: DiscordGuilds;
    telegramConfig: TelegramConfig;
    wechatConfig: WechatConfig;
    slackConfig: SlackConfig;
  };
};

function readRequiredEnv(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

function readBase64Json<T>(env: NodeJS.ProcessEnv, name: string, defaultValue: string): T {
  const encoded = env[name] || defaultValue;
  return JSON.parse(Buffer.from(encoded, "base64").toString("utf-8")) as T;
}

function readHermesBuildSettings(env: NodeJS.ProcessEnv): HermesBuildSettings {
  const model = readRequiredEnv(env, "NEMOCLAW_MODEL");
  const baseUrl = readRequiredEnv(env, "NEMOCLAW_INFERENCE_BASE_URL");

  return {
    model,
    inferenceProviderId: env.NEMOCLAW_INFERENCE_PROVIDER_ID || "custom",
    baseUrl,
    providerKey: env.NEMOCLAW_PROVIDER_KEY || "custom",
    inferenceApi: env.NEMOCLAW_INFERENCE_API || "",
    managedToolGateways: {
      brokerEnabled: env.NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER === "1",
      presets: readBase64Json<string[]>(
        env,
        "NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64",
        "W10=",
      ),
    },
    messaging: {
      enabledChannels: new Set(
        readBase64Json<string[]>(env, "NEMOCLAW_MESSAGING_CHANNELS_B64", "W10="),
      ),
      allowedIds: readBase64Json<MessagingAllowedIds>(
        env,
        "NEMOCLAW_MESSAGING_ALLOWED_IDS_B64",
        "e30=",
      ),
      discordGuilds: readBase64Json<DiscordGuilds>(env, "NEMOCLAW_DISCORD_GUILDS_B64", "e30="),
      telegramConfig: readBase64Json<TelegramConfig>(
        env,
        "NEMOCLAW_TELEGRAM_CONFIG_B64",
        "e30=",
      ),
      wechatConfig: readBase64Json<WechatConfig>(env, "NEMOCLAW_WECHAT_CONFIG_B64", "e30="),
      slackConfig: readBase64Json<SlackConfig>(env, "NEMOCLAW_SLACK_CONFIG_B64", "e30="),
    },
  };
}

function buildDiscordConfig(guilds: DiscordGuilds): Record<string, unknown> {
  const guildEntries = Object.entries(guilds);
  if (guildEntries.length === 0) {
    return {};
  }
  return {
    guilds: guildEntries.map(([guildId, config]) => ({
      id: guildId,
      require_mention: config.requireMention ?? false,
      users: config.users ?? [],
    })),
  };
}

function loadManagedToolGatewayMatrix(): Record<string, { config: Record<string, unknown> }> {
  // In production this would load from /opt/nemoclaw-hermes-config/managed-tool-gateway-matrix.json
  // For build-time config generation, we return an empty matrix
  // The actual presets are applied at runtime via the Hermes gateway
  return {};
}

function applyManagedToolConfig(
  config: Record<string, unknown>,
  managedConfig: Record<string, unknown>,
): void {
  for (const [key, value] of Object.entries(managedConfig)) {
    config[key] = value;
  }
}

function buildHermesConfig(settings: HermesBuildSettings): Record<string, unknown> {
  const apiServerToolsets = [...API_SERVER_TOOLSETS];
  const config: Record<string, unknown> = {
    _config_version: 12,
    model: {
      default: settings.model,
      provider: "custom",
      base_url: settings.baseUrl,
    },
    terminal: {
      backend: "local",
      timeout: 180,
    },
    agent: {
      max_turns: 60,
      reasoning_effort: "medium",
      environment_probe: false,
      tool_use_enforcement: "strict",
    },
    memory: {
      memory_enabled: true,
      user_profile_enabled: true,
    },
    skills: {
      creation_nudge_interval: 15,
    },
    display: {
      compact: false,
      tool_progress: "all",
    },
    plugins: {
      enabled: ["nemoclaw", "milimo-hermes"],
    },
    platform_toolsets: {
      api_server: apiServerToolsets,
    },
  };

  if (settings.messaging.enabledChannels.has("discord")) {
    config.discord = buildDiscordConfig(settings.messaging.discordGuilds);
  }

  if (settings.managedToolGateways.brokerEnabled) {
    const matrix = loadManagedToolGatewayMatrix();
    for (const preset of settings.managedToolGateways.presets) {
      const entry = matrix[preset];
      if (!entry) {
        throw new Error(`Unknown Hermes managed-tool gateway preset: ${preset}`);
      }
      applyManagedToolConfig(config, entry.config);
    }
    if (
      settings.managedToolGateways.presets.includes("nous-audio") &&
      !apiServerToolsets.includes("tts")
    ) {
      apiServerToolsets.push("tts");
    }
  }

  const telegramConfig = settings.messaging.telegramConfig;
  if (
    settings.messaging.enabledChannels.has("telegram") &&
    typeof telegramConfig.requireMention === "boolean"
  ) {
    config.telegram = {
      require_mention: telegramConfig.requireMention,
    };
  }

  config.platforms = {
    api_server: {
      enabled: true,
      extra: {
        port: 18642,
        host: "127.0.0.1",
      },
    },
  };

  return config;
}

function writeConfigFiles(
  config: Record<string, unknown>,
  envLines: string[],
): { configPath: string; envPath: string; envEntryCount: number } {
  const homeDir = homedir();
  const configPath = join(homeDir, ".hermes", "config.yaml");
  writeFileSync(configPath, toYaml(config));
  chmodSync(configPath, 0o600);

  const envPath = join(homeDir, ".hermes", ".env");
  writeFileSync(envPath, envLines.length > 0 ? `${envLines.join("\n")}\n` : "");
  chmodSync(envPath, 0o600);

  return {
    configPath,
    envPath,
    envEntryCount: envLines.length,
  };
}

function main(): void {
  const settings = readHermesBuildSettings(process.env);
  const config = buildHermesConfig(settings);

  const envLines: string[] = [];
  const apiServerKey = process.env.API_SERVER_KEY || randomBytes(32).toString("hex");
  envLines.push(`API_SERVER_KEY=${apiServerKey}`);
  envLines.push(`NEMOCLAW_MODEL=${settings.model}`);
  envLines.push(`NEMOCLAW_INFERENCE_BASE_URL=${settings.baseUrl}`);

  // Milimo-specific runtime defaults (can be overridden at build time)
  envLines.push(`MILIMO_SPEND_TEST_MODE=${process.env.MILIMO_SPEND_TEST_MODE || "false"}`);
  envLines.push(`MILIMO_DAILY_SPEND_CAP_CENTS=${process.env.MILIMO_DAILY_SPEND_CAP_CENTS || "10000"}`);
  envLines.push(`MILIMO_OPERATOR=${process.env.MILIMO_OPERATOR || ""}`);

  const result = writeConfigFiles(config, envLines);
  console.log(`Generated ${result.configPath} and ${result.envPath}`);
}

main();
