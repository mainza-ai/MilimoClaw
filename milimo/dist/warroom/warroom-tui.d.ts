interface WarRoomTUIOptions {
    squadId: string;
    operatorId?: string;
    tier?: "free" | "pro";
    blueprintDir?: string;
    digestConfig?: {
        morning_time: {
            hour: number;
            minute: number;
        };
        evening_time: {
            hour: number;
            minute: number;
        };
    };
}
export declare class WarRoomTUI {
    private screen;
    private leftPanel;
    private rightPanel;
    private bottomBar;
    private helpOverlay;
    private digestOverlay;
    private engine;
    private audit;
    private evolution;
    private digestScheduler;
    private pendingQueue;
    private selectedAction;
    private currentIndex;
    private finalsMode;
    private revenueData;
    private revenuePollInterval;
    private currentDigest;
    private hasNewDigest;
    private squadId;
    private operatorId;
    private blueprintDir;
    private refreshInterval;
    private isRunning;
    private readonly COLORS;
    private readonly POLL_INTERVAL;
    private readonly REVENUE_POLL_INTERVAL;
    constructor(options: WarRoomTUIOptions);
    start(): void;
    stop(): void;
    private setupKeyBindings;
    private toggleHelp;
    private toggleDigest;
    private refresh;
    private renderLeftPanel;
    private renderRightPanel;
    private getClawHealth;
    private getModeColor;
    private getModeIcon;
    private updateBottomBar;
    private navigateUp;
    private navigateDown;
    private selectAction;
    private approveAction;
    private blockAction;
    private editAction;
    private fetchRevenueData;
    private formatCurrency;
}
export declare function startWarRoom(squadId: string, operatorId?: string, tier?: "free" | "pro"): void;
export {};
//# sourceMappingURL=warroom-tui.d.ts.map