import type { PluginLogger, MilimoConfig } from "../index.js";
interface BadgeOptions {
    blueprint?: string;
    performance?: boolean;
    auditor?: string;
    verify?: string;
    list?: boolean;
    json?: boolean;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliBadge(opts: BadgeOptions): Promise<void>;
export {};
//# sourceMappingURL=badge.d.ts.map