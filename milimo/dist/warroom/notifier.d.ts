export interface NotificationPayload {
    action_id: string;
    claw: string;
    action_type: string;
    summary: string;
    priority: "HOLD" | "REVIEW" | "AUTO";
    timestamp: string;
}
export interface NotificationResult {
    delivered: boolean;
    method: "osascript" | "notify-send" | "pending_file" | "disabled";
    error?: string;
}
export declare class OperatorNotifier {
    private notificationDir;
    private pendingFile;
    private enabled;
    constructor(enabled?: boolean);
    notify(payload: NotificationPayload): NotificationResult;
    notifyHoldRelease(actionId: string): NotificationResult;
    private notifyMacOS;
    private notifyLinux;
    private notifyPendingFile;
    getPendingNotifications(): NotificationPayload[];
    clearPendingNotification(actionId: string): void;
    clearAllPending(): void;
    private ensureNotificationDir;
    private escapeAppleScript;
}
export declare function createNotifier(enabled?: boolean): OperatorNotifier;
//# sourceMappingURL=notifier.d.ts.map