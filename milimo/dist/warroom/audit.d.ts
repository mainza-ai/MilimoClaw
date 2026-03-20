export interface AuditEntry {
    timestamp: string;
    messageId?: string;
    clawRole?: string;
    actionType: string;
    decision?: 'APPROVED' | 'REJECTED' | 'DELEGATED' | 'AUTO';
    operatorId?: string;
    reason?: string;
    details?: Record<string, any>;
}
export declare class AuditLogger {
    private auditDir;
    private auditFile;
    constructor(squadId: string);
    private ensureDirectory;
    logAction(entry: Omit<AuditEntry, 'timestamp'>): void;
    getRecentLogs(limit?: number): AuditEntry[];
}
//# sourceMappingURL=audit.d.ts.map