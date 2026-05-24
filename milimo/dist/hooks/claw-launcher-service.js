"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.createClawLauncherService = createClawLauncherService;
exports.registerClawLauncherService = registerClawLauncherService;
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
const node_child_process_1 = require("node:child_process");
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const channel_notifier_js_1 = require("./channel-notifier.js");
// ---------------------------------------------------------------------------
// Blueprint directory resolution
// ---------------------------------------------------------------------------
function resolveBlueprintDir(pluginConfig) {
    const candidates = [
        pluginConfig.blueprintDir,
        "/opt/milimo-blueprint",
        "/sandbox/.openclaw/milimo/milimo-blueprint",
        (0, node_path_1.join)(process.env.HOME || "/tmp", ".openclaw/milimo/milimo-blueprint"),
        (0, node_path_1.join)(process.cwd(), "milimo-blueprint"),
    ];
    for (const dir of candidates) {
        if (dir && (0, node_fs_1.existsSync)((0, node_path_1.join)(dir, "orchestrator", "bridge_cli.py"))) {
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
function createClawLauncherService(pluginConfig) {
    let launcherProcess = null;
    let healthInterval = null;
    return {
        id: "milimo-claw-launcher",
        start: ({ logger }) => {
            const blueprintDir = resolveBlueprintDir(pluginConfig);
            const launcherScript = (0, node_path_1.join)(blueprintDir, "orchestrator", "claw_launcher.py");
            if (!(0, node_fs_1.existsSync)(launcherScript)) {
                logger.warn(`[milimo] Claw launcher service: claw_launcher.py not found at ${launcherScript}. ` +
                    "Claws will need to be launched manually.");
                return;
            }
            logger.info("[milimo] Starting claw launcher service...");
            // Launch the orchestrator with the "--all" flag
            const pythonPath = (0, node_path_1.join)(blueprintDir, ".venv", "bin", "python3");
            const pythonBin = (0, node_fs_1.existsSync)(pythonPath) ? pythonPath : "python3";
            try {
                launcherProcess = (0, node_child_process_1.spawn)(pythonBin, [launcherScript, "--all"], {
                    cwd: blueprintDir,
                    env: {
                        ...process.env,
                        PYTHONPATH: blueprintDir,
                        MILIMO_SQUAD_ID: pluginConfig.squadName || "default",
                        MILIMO_CLAW_ROLE: pluginConfig.clawRole || "solo",
                    },
                    stdio: ["pipe", "pipe", "pipe"],
                    detached: false,
                });
                launcherProcess.stdout?.on("data", (data) => {
                    const msg = data.toString().trim();
                    if (msg)
                        logger.debug(`[milimo-launcher] ${msg}`);
                });
                launcherProcess.stderr?.on("data", (data) => {
                    const msg = data.toString().trim();
                    // Filter harmless NemoClaw sandbox permission noise
                    if (msg && !msg.includes("oom_score_adj")) {
                        logger.warn(`[milimo-launcher] ${msg}`);
                    }
                });
                launcherProcess.on("exit", (code, signal) => {
                    logger.info(`[milimo] Claw launcher process exited (code=${code}, signal=${signal}).`);
                    launcherProcess = null;
                    // Notify via channels if unexpected exit
                    if (code !== 0 && code !== null) {
                        const notifier = new channel_notifier_js_1.ChannelNotifier(logger, (0, channel_notifier_js_1.loadNotificationConfig)());
                        notifier.sendAlert("critical", `Claw launcher exited unexpectedly (code=${code}). Claws may be offline.`);
                    }
                });
                launcherProcess.on("error", (err) => {
                    logger.error(`[milimo] Claw launcher failed to start: ${err.message}`);
                    launcherProcess = null;
                });
                logger.info("[milimo] Claw launcher service started.");
                // Start periodic health check
                healthInterval = setInterval(() => {
                    if (!launcherProcess || launcherProcess.exitCode !== null) {
                        logger.warn("[milimo] Claw launcher process is not running. " +
                            "Restart via: openclaw milimo squad status");
                    }
                }, 60_000);
            }
            catch (err) {
                logger.error(`[milimo] Failed to start claw launcher: ${err instanceof Error ? err.message : String(err)}`);
            }
        },
        stop: async ({ logger }) => {
            logger.info("[milimo] Stopping claw launcher service...");
            // Clear health check interval
            if (healthInterval) {
                clearInterval(healthInterval);
                healthInterval = null;
            }
            // Gracefully terminate the launcher process
            if (launcherProcess && launcherProcess.exitCode === null) {
                try {
                    // Send SIGTERM for graceful shutdown
                    launcherProcess.kill("SIGTERM");
                    // Wait up to 10 seconds for graceful exit
                    await new Promise((resolve) => {
                        const timeout = setTimeout(() => {
                            if (launcherProcess && launcherProcess.exitCode === null) {
                                logger.warn("[milimo] Claw launcher did not exit gracefully, sending SIGKILL.");
                                launcherProcess.kill("SIGKILL");
                            }
                            resolve();
                        }, 10_000);
                        launcherProcess.on("exit", () => {
                            clearTimeout(timeout);
                            resolve();
                        });
                    });
                }
                catch (err) {
                    logger.warn(`[milimo] Error stopping claw launcher: ${err instanceof Error ? err.message : String(err)}`);
                }
            }
            launcherProcess = null;
            logger.info("[milimo] Claw launcher service stopped.");
        },
    };
}
/**
 * Register the claw launcher as a managed OpenClaw service.
 *
 * This is called from the plugin's register() function if the OpenClaw
 * host supports service registration.
 */
function registerClawLauncherService(api, pluginConfig) {
    // Only register if registerService is available on the API
    if (!api.registerService) {
        api.logger.debug("[milimo] api.registerService not available — claw launcher must be managed externally.");
        return;
    }
    try {
        const service = createClawLauncherService(pluginConfig);
        api.registerService(service);
        api.logger.debug("[milimo] Registered claw launcher as managed OpenClaw service.");
    }
    catch (err) {
        api.logger.warn(`[milimo] Could not register claw launcher service: ${err instanceof Error ? err.message : String(err)}`);
    }
}
//# sourceMappingURL=claw-launcher-service.js.map