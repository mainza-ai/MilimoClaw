import type { PluginLogger, MilimoConfig } from "../index.js";
import { type MilimoConfig as FullMilimoConfig } from "../onboard/config.js";
interface InitOptions {
    squad?: string;
    role?: string;
    template?: string;
    solo: boolean;
    assistantName?: string;
    assistantCreature?: string;
    assistantVibe?: string;
    assistantEmoji?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliInit(opts: InitOptions): Promise<void>;
export declare function loadMilimoState(): FullMilimoConfig | null;
export declare function saveMilimoState(state: FullMilimoConfig): void;
export {};
//# sourceMappingURL=init.d.ts.map