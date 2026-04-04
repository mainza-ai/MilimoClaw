export type ApprovalMode = 'AUTO' | 'REVIEW' | 'HOLD' | 'VETO';
export interface PendingMessage {
    message_id: string;
    sender_role: string;
    recipient_role: string;
    message_type: string;
    payload: Record<string, unknown>;
    squad_id: string;
    timestamp: string;
    needs_approval: boolean;
    file_path: string;
}
export interface EscalationRule {
    trigger: string;
    action: ApprovalMode;
    description: string;
}
export declare class ApprovalEngine {
    private meshDir;
    private warRoomInbox;
    private audit;
    private escalationRules;
    private rateLimiter;
    private tier;
    constructor(squadId: string, tier?: string);
    private loadEscalationRules;
    getPendingMessages(): PendingMessage[];
    evaluateAction(message: PendingMessage): {
        mode: ApprovalMode;
        trigger?: string;
        description?: string;
    };
    processDecision(message: PendingMessage, decision: 'APPROVED' | 'REJECTED' | 'DELEGATED', operatorId?: string, reason?: string): void;
    autoProcessEligible(): void;
    /**
     * Get rate limiter status for display in War Room.
     */
    getRateLimitStatus(): {
        tier: string;
        dailyRemaining: number;
        dailyLimit: number;
        burstRemaining: number;
        burstLimit: number;
        dailyResetAt: string;
        burstResetAt: string;
    } | null;
}
//# sourceMappingURL=approval.d.ts.map