export interface Logger {
    info: (message: string) => void;
    error: (message: string) => void;
    warn: (message: string) => void;
}
export interface LogsSearchOptions {
    query?: string;
    from?: string;
    to?: string;
    clawRole?: string;
    decision?: string;
    limit?: number;
    json?: boolean;
    squad?: string;
    logger: Logger;
    pluginConfig: {
        blueprintDir: string;
    };
}
export declare function cliLogsSearch(options: LogsSearchOptions): Promise<void>;
export declare function cliLogsList(options: {
    squad?: string;
    logger: Logger;
    pluginConfig: {
        blueprintDir: string;
    };
}): Promise<void>;
//# sourceMappingURL=logs.d.ts.map