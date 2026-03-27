import type { PluginLogger, MilimoConfig } from "../index.js";
interface BlueprintListOptions {
    json: boolean;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface BlueprintForkOptions {
    source: string;
    into?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface BlueprintDiffOptions {
    versionA: string;
    versionB: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface BlueprintPublishOptions {
    name?: string;
    price: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface BlueprintRollbackOptions {
    to?: string;
    reason?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliBlueprintList(opts: BlueprintListOptions): Promise<void>;
export declare function cliBlueprintFork(opts: BlueprintForkOptions): Promise<void>;
export declare function cliBlueprintDiff(opts: BlueprintDiffOptions): Promise<void>;
export declare function cliBlueprintPublish(opts: BlueprintPublishOptions): Promise<void>;
export declare function cliBlueprintRollback(opts: BlueprintRollbackOptions): Promise<void>;
export declare function cliBlueprintSearch(opts: {
    query?: string;
    category?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}): Promise<void>;
export declare function cliBlueprintMerge(opts: {
    incoming: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}): Promise<void>;
export declare function cliBlueprintInfo(opts: {
    blueprintId: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}): Promise<void>;
export {};
//# sourceMappingURL=blueprint.d.ts.map