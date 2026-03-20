interface WarRoomTUIOptions {
    squadId: string;
    operatorId?: string;
    tier?: "free" | "pro";
}
export declare class WarRoomTUI {
    private screen;
    private leftPanel;
    private rightPanel;
    private bottomBar;
    private helpOverlay;
    private engine;
    private audit;
    private evolution;
    private pendingQueue;
    private selectedAction;
    private currentIndex;
    private finalsMode;
    private squadId;
    private operatorId;
    private refreshInterval;
    private isRunning;
    private readonly COLORS;
    private readonly POLL_INTERVAL;
    constructor(options: WarRoomTUIOptions);
    start(): void;
    stop(): void;
    private setupKeyBindings;
    private toggleHelp;
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
}
export declare function startWarRoom(squadId: string, operatorId?: string, tier?: "free" | "pro"): void;
export {};
//# sourceMappingURL=warroom-tui.d.ts.map