export interface Logger {
    info: (message: string) => void;
    error: (message: string) => void;
    warn: (message: string) => void;
}
export interface ActionCliOptions {
    logger: Logger;
    pluginConfig: {
        blueprintDir: string;
    };
}
export interface PendingAction {
    message_id: string;
    sender_role: string;
    recipient_role: string;
    message_type: string;
    payload: Record<string, unknown>;
    squad_id: string;
    timestamp: string;
    needs_approval: boolean;
    file_path: string;
    priority?: string;
}
export declare function cliActionApprove(options: ActionCliOptions & {
    actionId: string;
}): Promise<void>;
export declare function cliActionBlock(options: ActionCliOptions & {
    actionId: string;
    reason?: string;
}): Promise<void>;
export declare function listPendingActions(): PendingAction[];
//# sourceMappingURL=action.d.ts.map