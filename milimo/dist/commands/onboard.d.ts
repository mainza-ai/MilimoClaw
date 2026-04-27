import type { PluginLogger, MilimoConfig } from "../index.js";
import { type MilimoOnboardConfig } from "../onboard/config.js";
export interface OnboardOptions {
    squad?: string;
    role?: string;
    template?: string;
    solo?: boolean;
    operator?: string;
    warRoomMode?: "full" | "minimal" | "disabled";
    noSandbox?: boolean;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
declare function formatRoleDisplay(config: MilimoOnboardConfig): string;
export { formatRoleDisplay };
export declare function cliOnboard(opts: OnboardOptions): Promise<void>;
export declare function cliOnboardStatus(logger: PluginLogger): Promise<void>;
//# sourceMappingURL=onboard.d.ts.map