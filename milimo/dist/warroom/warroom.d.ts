export declare class WarRoomTUI {
    private squadId;
    private operatorId;
    private rl;
    private engine;
    private audit;
    private evolution;
    private isRunning;
    private refreshInterval;
    private pendingQueue;
    constructor(squadId: string, operatorId?: string);
    start(): void;
    stop(): void;
    private refreshQueue;
    private displayPrompt;
    private handleCommand;
    private listPending;
    private viewAction;
    private processAction;
    private showFeed;
}
//# sourceMappingURL=warroom.d.ts.map