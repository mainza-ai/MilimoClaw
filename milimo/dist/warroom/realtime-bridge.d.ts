export interface RealtimeEvent {
    type: "action_queued" | "status_change" | "evolution_event" | "revenue_update";
    timestamp: string;
    data: RealtimeEventData;
}
export type RealtimeEventData = ActionQueuedEvent | StatusChangeEvent | EvolutionEvent | RevenueUpdateEvent;
export interface ActionQueuedEvent {
    action_id: string;
    claw: string;
    action_type: string;
    priority: "HOLD" | "REVIEW" | "AUTO";
    message_type: string;
    payload: Record<string, unknown>;
}
export interface StatusChangeEvent {
    claw: string;
    previous_status: "active" | "idle" | "processing" | "error";
    new_status: "active" | "idle" | "processing" | "error";
    tool_count: number;
}
export interface EvolutionEvent {
    claw: string;
    stage: "observe" | "identify" | "propose" | "build" | "deploy";
    status: "started" | "completed" | "failed";
    tool_id?: string;
    improvement_pct?: number;
}
export interface RevenueUpdateEvent {
    week_revenue: number;
    week_over_week_pct: number;
    invoices_paid: number;
    invoices_pending: number;
}
export interface RealtimeBridgeOptions {
    port?: number;
    squadId: string;
    blueprintDir?: string;
}
type ActionHandler = (event: ActionQueuedEvent) => void;
type StatusHandler = (event: StatusChangeEvent) => void;
type EvolutionHandler = (event: EvolutionEvent) => void;
type RevenueHandler = (event: RevenueUpdateEvent) => void;
export declare class RealtimeBridge {
    private port;
    private squadId;
    private blueprintDir;
    private server;
    private wss;
    private clients;
    private actionHandlers;
    private statusHandlers;
    private evolutionHandlers;
    private revenueHandlers;
    private fileWatchers;
    private clawStatusCache;
    private running;
    constructor(options: RealtimeBridgeOptions);
    start(): void;
    stop(): void;
    onAction(handler: ActionHandler): void;
    onHealthUpdate(handler: StatusHandler): void;
    onEvolutionEvent(handler: EvolutionHandler): void;
    onRevenueUpdate(handler: RevenueHandler): void;
    broadcast(event: RealtimeEvent): void;
    private sendInitialState;
    private setupFileWatchers;
    private handleFileChange;
    private checkForNewAction;
    private checkClawStatusChange;
    private checkForRevenueUpdate;
    private getPendingActions;
    private getClawStatuses;
    getConnectedClients(): number;
    isRunning(): boolean;
}
export declare function createRealtimeBridge(options: RealtimeBridgeOptions): RealtimeBridge;
export {};
//# sourceMappingURL=realtime-bridge.d.ts.map