import type { PluginLogger, MilimoConfig } from "../index.js";
export interface OnboardOptions {
    squad?: string;
    role?: string;
    template?: string;
    solo?: boolean;
    operator?: string;
    warRoomMode?: "full" | "minimal" | "disabled";
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliOnboard(opts: OnboardOptions): Promise<void>;
export declare function cliOnboardStatus(logger: PluginLogger): Promise<void>;
//# sourceMappingURL=onboard.d.ts.map