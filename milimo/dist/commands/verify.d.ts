import type { PluginLogger, MilimoConfig } from "../index.js";
interface VerifyOptions {
    blueprintId?: string;
    version?: string;
    chain?: boolean;
    strict?: boolean;
    json?: boolean;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliVerify(opts: VerifyOptions): Promise<void>;
interface KeygenOptions {
    squad: string;
    force?: boolean;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliProvenanceKeygen(opts: KeygenOptions): Promise<void>;
export {};
//# sourceMappingURL=verify.d.ts.map