import type { ClawRole } from "../index.js";
export declare const CONFIG_DIR: string;
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
export declare function clearCache(): void;
export declare class ConfigManager {
    static load(): MilimoConfig | null;
    static save(config: MilimoConfig): void;
    static migrate(): {
        migrated: boolean;
        hadLegacyState: boolean;
    };
    static clear(): void;
    static getConfigDir(): string;
    static ensureDirectories(): void;
    static hasLegacyState(): boolean;
}
export declare function loadOnboardConfig(): MilimoConfig | null;
export declare function saveOnboardConfig(config: MilimoConfig): void;
export declare function clearOnboardConfig(): void;
export { configPath } from "./config-legacy.js";
export declare function loadNemoClawConfig(): {
    model: string;
    endpointUrl: string;
} | null;
export declare function isNemoClawOnboarded(): boolean;
export { MilimoConfig as MilimoOnboardConfig };
//# sourceMappingURL=config.d.ts.map