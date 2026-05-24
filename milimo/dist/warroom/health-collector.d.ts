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
    /**
     * Collect NemoClaw sandbox diagnostics by wrapping `nemoclaw doctor`.
     *
     * This augments Milimo's claw-level health with NemoClaw's native
     * sandbox-level diagnostics (gateway connectivity, proxy status,
     * credential availability, etc.).
     *
     * Returns a structured summary or null if nemoclaw CLI is unavailable.
     */
    collectNemoClawDiagnostics(): NemoClawDiagnostics | null;
}
/** NemoClaw sandbox diagnostics from `nemoclaw doctor`. */
export interface NemoClawDiagnostics {
    available: boolean;
    checks: DiagnosticCheck[];
    summary: string;
    collectedAt: string;
}
export interface DiagnosticCheck {
    name: string;
    status: "pass" | "fail" | "warn";
}
//# sourceMappingURL=health-collector.d.ts.map