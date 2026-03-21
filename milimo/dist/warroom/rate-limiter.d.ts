import { EventEmitter } from "node:events";
export declare enum Tier {
    FREE = "free",
    PRO = "pro"
}
export interface RateLimitConfig {
    tier: Tier;
    dailyLimit: number;
    burstLimit: number;
    burstWindowMs: number;
}
export interface RateLimitState {
    tokens: number;
    lastRefill: string;
    burstTokens: number;
    lastBurstRefill: string;
}
export interface RateLimitMetrics {
    totalRequests: number;
    allowedRequests: number;
    deniedRequests: number;
    lastReset: string;
}
export interface RateLimitResult {
    allowed: boolean;
    remaining: number;
    resetAt: string;
    reason?: string;
}
export interface TierCacheEntry {
    tier: Tier;
    verifiedAt: string;
    expiresAt: string;
}
export declare function getEffectiveTier(configPath?: string): Tier;
export declare function invalidateTierCache(): void;
export declare class RateLimiter extends EventEmitter {
    private config;
    private state;
    private metrics;
    private statePath;
    constructor(tier: Tier, stateDir?: string);
    /**
     * Try to consume a token for an auto-approval.
     * Returns true if the request is allowed, false if rate limited.
     */
    tryConsume(): RateLimitResult;
    /**
     * Get current rate limit status without consuming.
     */
    getStatus(): {
        tier: Tier;
        dailyLimit: number;
        dailyRemaining: number;
        burstLimit: number;
        burstRemaining: number;
        dailyResetAt: string;
        burstResetAt: string;
    };
    /**
     * Get metrics for monitoring.
     */
    getMetrics(): RateLimitMetrics;
    /**
     * Reset the rate limiter (admin operation).
     */
    reset(): void;
    /**
     * Refill tokens if needed based on time elapsed.
     */
    private refillIfNeeded;
    /**
     * Get the next daily reset time (midnight UTC).
     */
    private getNextReset;
    /**
     * Get the next burst reset time.
     */
    private getBurstReset;
    /**
     * Load state from disk.
     */
    private loadState;
    /**
     * Save state to disk.
     */
    private saveState;
}
export declare class RateLimitMetricsTracker {
    private limiter;
    private intervalId;
    private history;
    constructor(limiter: RateLimiter);
    /**
     * Start tracking metrics at regular intervals.
     */
    start(intervalMs?: number): void;
    /**
     * Stop tracking metrics.
     */
    stop(): void;
    /**
     * Record current metrics.
     */
    private record;
    /**
     * Get metrics history.
     */
    getHistory(): Array<{
        timestamp: string;
        metrics: RateLimitMetrics;
    }>;
    /**
     * Get utilization percentage.
     */
    getUtilization(): number;
}
export declare function createRateLimiter(tier: Tier, stateDir?: string): RateLimiter;
export declare function getTierFromString(tier: string): Tier;
//# sourceMappingURL=rate-limiter.d.ts.map