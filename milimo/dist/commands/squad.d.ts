import type { PluginLogger, MilimoConfig } from "../index.js";
interface SquadStatusOptions {
    json: boolean;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface FinalsModeOptions {
    duration: string;
    resumeDate?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface ResumeOptions {
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function checkFinalsModeAutoResume(logger: PluginLogger): void;
export declare function cliSquadStatus(opts: SquadStatusOptions): Promise<void>;
export declare function cliSquadFinalsMode(opts: FinalsModeOptions): Promise<void>;
export declare function cliSquadResume(opts: ResumeOptions): Promise<void>;
declare function parseDurationDays(duration: string): number;
export declare function formatResumeDate(date: Date): string;
export declare function calculateResumeDate(duration: string): string;
export { parseDurationDays };
//# sourceMappingURL=squad.d.ts.map