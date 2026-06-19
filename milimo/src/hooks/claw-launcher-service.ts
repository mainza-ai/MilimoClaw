// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Claw Launcher Service — OpenClaw Managed Service Registration
 *
 * Registers the Milimo Claw Launcher as a background service with the
 * OpenClaw plugin host via `api.registerService()`. This lets OpenClaw
 * manage the launcher lifecycle (start/stop) instead of relying on
 * manual PID file management and external script triggers.
 *
 * The launcher service:
 * 1. Starts the Python claw_launcher.py via the bridge CLI on service start
 * 2. Monitors claw health via periodic health checks
 * 3. Gracefully stops all claws on service stop
 * 4. Reports claw status through the digest scheduler and channel notifier
 *
 * Architecture:
 *   OpenClaw plugin host
 *     └── registerService("milimo-claw-launcher")
 *           ├── start() → bridge_cli.py launch_claws
 *           └── stop()  → bridge_cli.py stop_claws
 */

import { existsSync } from "node:fs";
import { join } from "node:path";
import type { OpenClawPluginApi, PluginLogger, MilimoConfig, OpenClawConfig } from "../index.js";
import { ChannelNotifier, loadNotificationConfig } from "./channel-notifier.js";
import { getRpcClient } from "../lib/rpc-bridge";

// ---------------------------------------------------------------------------
// Blueprint directory resolution
// ---------------------------------------------------------------------------

function resolveBlueprintDir(pluginConfig: MilimoConfig): string {
  const candidates = [
    pluginConfig.blueprintDir,
    "/opt/milimo-blueprint",
    "/sandbox/.openclaw/milimo/milimo-blueprint",
    join(process.env.HOME || "/tmp", ".openclaw/milimo/milimo-blueprint"),
    join(process.cwd(), "milimo-blueprint"),
  ];

  for (const dir of candidates) {
    if (dir && existsSync(join(dir, "orchestrator", "bridge_cli.py"))) {
      return dir;
    }
  }

  return pluginConfig.blueprintDir || "/opt/milimo-blueprint";
}

// ---------------------------------------------------------------------------
// Claw Launcher Service
// ---------------------------------------------------------------------------

/**
 * Create the claw launcher service definition for OpenClaw registration.
 */
export function createClawLauncherService(pluginConfig: MilimoConfig): {
  id: string;
  start: (ctx: { config: OpenClawConfig; logger: PluginLogger }) => void;
  stop: (ctx: { config: OpenClawConfig; logger: PluginLogger }) => Promise<void>;
} {
  let healthInterval: NodeJS.Timeout | null = null;

  return {
    id: "milimo-claw-launcher",

    start: ({ logger }: { config: OpenClawConfig; logger: PluginLogger }) => {
      const blueprintDir = resolveBlueprintDir(pluginConfig);
      const launcherScript = join(blueprintDir, "orchestrator", "claw_launcher.py");

      if (!existsSync(launcherScript)) {
        logger.warn(
          `[milimo] Claw launcher service: claw_launcher.py not found at ${launcherScript}. ` +
            "Claws will need to be launched manually.",
        );
        return;
      }

      logger.info("[milimo] Starting claw launcher service via RPC...");

      try {
        const rpc = getRpcClient();
        rpc
          .call("start_launcher", {
            blueprintDir,
            squadId: pluginConfig.squadName || "default",
            clawRole: pluginConfig.clawRole || "solo",
          })
          .catch((err) => {
            logger.warn(`[milimo] Claw launcher RPC start failed: ${err.message}`);
            logger.warn("[milimo] Ensure the Python RPC server is running (bridge_server.py)");
          });

        // Periodic health check — verifies RPC server is reachable
        healthInterval = setInterval(async () => {
          try {
            const rpc = getRpcClient();
            await rpc.call("ping", {});
          } catch {
            logger.warn(
              "[milimo] Python RPC server not reachable. " + "Claw launcher may not be running.",
            );
          }
        }, 60_000);
      } catch (err) {
        logger.error(
          `[milimo] Failed to start claw launcher: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    },

    stop: async ({ logger }: { config: OpenClawConfig; logger: PluginLogger }) => {
      logger.info("[milimo] Stopping claw launcher service...");

      if (healthInterval) {
        clearInterval(healthInterval);
        healthInterval = null;
      }

      try {
        const rpc = getRpcClient();
        await rpc.call("stop_launcher", {});
        logger.info("[milimo] Claw launcher service stopped.");
      } catch (err) {
        logger.warn(
          `[milimo] Error stopping claw launcher: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
    },
  };
}

/**
 * Register the claw launcher as a managed OpenClaw service.
 *
 * This is called from the plugin's register() function if the OpenClaw
 * host supports service registration.
 */
export function registerClawLauncherService(
  api: OpenClawPluginApi,
  pluginConfig: MilimoConfig,
): void {
  // Only register if registerService is available on the API
  if (!(api as any).registerService) {
    api.logger.debug(
      "[milimo] api.registerService not available — claw launcher must be managed externally.",
    );
    return;
  }

  try {
    const service = createClawLauncherService(pluginConfig);
    (api as any).registerService(service);
    api.logger.debug("[milimo] Registered claw launcher as managed OpenClaw service.");
  } catch (err) {
    api.logger.warn(
      `[milimo] Could not register claw launcher service: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
}
