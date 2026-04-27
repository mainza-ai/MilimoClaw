export interface ClawHealth {
    role: string;
    status: "active" | "idle" | "processing" | "error";
    tool_count: number;
    last_evolution: string | null;
    last_action: string | null;
    actions_this_week: number;
    sparkline: number[];
}
export type ClawHealthMap = Record<string, ClawHealth>;
export interface HealthCollectorOptions {
    squadId: string;
    blueprintDir: string;
    pollInterval?: number;
}
export type HealthUpdateHandler = (health: ClawHealthMap) => void;
export type HealthErrorHandler = (error: Error) => void;
export declare class HealthCollector {
    private squadId;
    private bridgeOptions;
    private pollInterval;
    private intervalId;
    private running;
    constructor(options: HealthCollectorOptions);
    collectAll(): ClawHealthMap;
    startPolling(onUpdate: HealthUpdateHandler, onError?: HealthErrorHandler): () => void;
    stopPolling(): void;
    deriveStatus(health: ClawHealth): "active" | "idle" | "processing" | "error";
    isRunning(): boolean;
}
//# sourceMappingURL=health-collector.d.ts.map