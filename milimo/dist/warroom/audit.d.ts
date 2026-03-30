export interface AuditEntry {
    timestamp: string;
    messageId?: string;
    clawRole?: string;
    actionType: string;
    decision?: "APPROVED" | "REJECTED" | "DELEGATED" | "AUTO";
    operatorId?: string;
    reason?: string;
    details?: Record<string, unknown>;
}
export interface AuditSearchOptions {
    query?: string;
    from?: string;
    to?: string;
    clawRole?: string;
    decision?: string;
    limit?: number;
}
export interface AuditRotationConfig {
    retentionDays: number;
    compress: boolean;
}
export declare class AuditLogger {
    private auditDir;
    private auditFile;
    private rotationConfig;
    private lastRotationCheck;
    constructor(squadId: string, rotationConfig?: Partial<AuditRotationConfig>);
    private ensureDirectory;
    logAction(entry: Omit<AuditEntry, "timestamp">): void;
    getRecentLogs(limit?: number): AuditEntry[];
    checkRotation(): void;
    private rotateLog;
    private compressLog;
    private cleanupOldLogs;
    searchLogs(options: AuditSearchOptions): AuditEntry[];
    private searchInFile;
    getRotatedLogs(): string[];
}
export declare function createAuditLogger(squadId: string, config?: Partial<AuditRotationConfig>): AuditLogger;
//# sourceMappingURL=audit.d.ts.map