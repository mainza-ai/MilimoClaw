import { EventEmitter } from "events";
interface HealthMetrics {
    claw_role: string;
    heartbeat_latency_ms: number;
    message_throughput_per_min: number;
    evolution_status: string;
    approval_backlog: number;
    error_rate_per_hour: number;
    last_updated: string;
}
interface ClawHealth {
    role: string;
    status: string;
    score: number;
    metrics: HealthMetrics;
    region: string;
    squad_id: string;
    last_heartbeat: string;
}
interface SquadHealth {
    squad_id: string;
    overall_score: number;
    overall_status: string;
    claws: ClawHealth[];
    alerts: Array<{
        role: string;
        level: string;
        message: string;
        timestamp: string;
    }>;
    last_updated: string;
}
declare const STATUS_ICONS: Record<string, string>;
declare const STATUS_COLORS: Record<string, string>;
declare class HealthDashboard extends EventEmitter {
    private squadId;
    private blueprintDir;
    private healthPath;
    private updateInterval;
    private lastHealth;
    private cachedData;
    constructor(squadId?: string);
    start(intervalMs?: number): void;
    stop(): void;
    private update;
    private loadHealthData;
    getHealth(): SquadHealth | null;
    getClawHealth(role: string): ClawHealth | null;
    getAlerts(): SquadHealth["alerts"];
    renderCompact(): string;
    renderDetailed(): string;
    renderScoreBar(score: number): string;
    formatLatency(ms: number): string;
    getStatusColor(status: string): string;
    getStatusIcon(status: string): string;
    toJSON(): string;
}
declare function createHealthWidget(health: SquadHealth): string;
declare function renderMetricGauge(value: number, max: number, label: string): string;
export { HealthDashboard, createHealthWidget, renderMetricGauge, STATUS_ICONS, STATUS_COLORS };
export type { SquadHealth, ClawHealth, HealthMetrics };
//# sourceMappingURL=health-dashboard.d.ts.map