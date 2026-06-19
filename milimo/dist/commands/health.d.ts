export interface HealthOptions {
    squad?: string;
    detailed?: boolean;
    collect?: boolean;
    watch?: boolean;
    interval?: string;
    json?: boolean;
}
export declare function healthCommand(options: HealthOptions): Promise<void>;
//# sourceMappingURL=health.d.ts.map