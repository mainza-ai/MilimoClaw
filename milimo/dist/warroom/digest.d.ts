export interface DigestBrief {
    type: "morning" | "evening";
    overnight_actions?: number;
    queue_summary?: {
        hold: number;
        review: number;
        auto: number;
    };
    pending_actions?: Array<{
        id: string;
        claw: string;
        type: string;
        priority: string;
    }>;
    today_completed?: number;
    auto_executed?: number;
    remaining_pending?: number;
    evolution_updates?: Array<{
        claw: string;
        tool: string;
        timestamp: string;
    }>;
    alerts?: Array<{
        level: string;
        message: string;
    }>;
    generated_at: string;
}
export interface DigestConfig {
    morning_time: {
        hour: number;
        minute: number;
    };
    evening_time: {
        hour: number;
        minute: number;
    };
    squad_id: string;
}
export interface DigestScheduleOptions {
    config: DigestConfig;
    blueprintDir: string;
    onUpdate?: (brief: DigestBrief) => void;
    onError?: (error: Error) => void;
}
export declare class DigestScheduler {
    private config;
    private bridgeOptions;
    private morningTimer;
    private eveningTimer;
    private onUpdate?;
    private onError?;
    private running;
    constructor(options: DigestScheduleOptions);
    start(): void;
    stop(): void;
    private scheduleMorning;
    private scheduleEvening;
    private calculateDelay;
    getMorningBrief(): Promise<DigestBrief | null>;
    getEveningWrap(): Promise<DigestBrief | null>;
    renderBrief(brief: DigestBrief): string[];
    getNextMorningTime(): Date | null;
    getNextEveningTime(): Date | null;
    isRunning(): boolean;
}
//# sourceMappingURL=digest.d.ts.map