interface MeshFlowSignal {
    signal_type: string;
    source_claw: string;
    destination_claw: string;
    last_transmission?: string;
}
interface MeshFlowState {
    signals: MeshFlowSignal[];
    last_transmission?: string;
    signal_count_this_week: number;
}
export declare class EvolutionManager {
    private squadId;
    private toolsDir;
    private blueprintDir;
    constructor(squadId: string, blueprintDir?: string);
    showEvolutionLog(): void;
    toggleTool(role: string, toolName: string, enable: boolean): void;
    showCrossClawFlows(): Promise<void>;
    private getMeshFlowState;
    getMeshFlowData(): Promise<MeshFlowState | null>;
}
export {};
//# sourceMappingURL=evolution.d.ts.map