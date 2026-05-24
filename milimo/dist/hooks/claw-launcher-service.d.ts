import type { OpenClawPluginApi, PluginLogger, MilimoConfig, OpenClawConfig } from "../index.js";
/**
 * Create the claw launcher service definition for OpenClaw registration.
 */
export declare function createClawLauncherService(pluginConfig: MilimoConfig): {
    id: string;
    start: (ctx: {
        config: OpenClawConfig;
        logger: PluginLogger;
    }) => void;
    stop: (ctx: {
        config: OpenClawConfig;
        logger: PluginLogger;
    }) => Promise<void>;
};
/**
 * Register the claw launcher as a managed OpenClaw service.
 *
 * This is called from the plugin's register() function if the OpenClaw
 * host supports service registration.
 */
export declare function registerClawLauncherService(api: OpenClawPluginApi, pluginConfig: MilimoConfig): void;
//# sourceMappingURL=claw-launcher-service.d.ts.map