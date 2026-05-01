"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.RateLimitMetricsTracker = exports.RateLimiter = exports.Tier = void 0;
exports.getEffectiveTier = getEffectiveTier;
exports.invalidateTierCache = invalidateTierCache;
exports.createRateLimiter = createRateLimiter;
exports.getTierFromString = getTierFromString;
/**
 * Rate Limiter for Auto-Approvals
 *
 * Implements token bucket algorithm for rate limiting auto-approvals
 * in the free tier. Enforces daily limits and burst protection.
 *
 * PRO tier verification:
 * - Reads from config file
 * - 1-hour cache TTL to avoid repeated checks
 * - Falls back to FREE tier on error
 *
 * Usage:
 * import { RateLimiter, Tier, getTierFromString } from "./rate-limiter";
 *
 * const limiter = new RateLimiter(Tier.FREE);
 * if (limiter.tryConsume()) {
 * // Allow auto-approval
 * } else {
 * // Require manual approval
 * }
 */
const fs = __importStar(require("node:fs"));
const path = __importStar(require("node:path"));
const node_events_1 = require("node:events");
// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
var Tier;
(function (Tier) {
    Tier["FREE"] = "free";
    Tier["PRO"] = "pro";
})(Tier || (exports.Tier = Tier = {}));
// ---------------------------------------------------------------------------
// Tier Verification
// ---------------------------------------------------------------------------
const TIER_CACHE_TTL_MS = 3600000; // 1 hour
let tierCache = null;
function getEffectiveTier(configPath) {
    // Check cache first
    if (tierCache) {
        const now = new Date();
        const expiresAt = new Date(tierCache.expiresAt);
        if (now < expiresAt) {
            return tierCache.tier;
        }
    }
    // Verify tier from config
    const config = loadConfig(configPath);
    if (!config) {
        return Tier.FREE;
    }
    const tier = config.tier === "pro" ? Tier.PRO : Tier.FREE;
    // Update cache
    const now = new Date();
    const expiresAt = new Date(now.getTime() + TIER_CACHE_TTL_MS);
    tierCache = {
        tier,
        verifiedAt: now.toISOString(),
        expiresAt: expiresAt.toISOString(),
    };
    return tier;
}
function loadConfig(configPath) {
    const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
    const configPathResolved = configPath || path.join(home, ".openclaw/milimo", "config.json");
    try {
        if (!fs.existsSync(configPathResolved)) {
            return null;
        }
        const content = fs.readFileSync(configPathResolved, "utf-8");
        const config = JSON.parse(content);
        return config;
    }
    catch {
        return null;
    }
}
function invalidateTierCache() {
    tierCache = null;
}
// ---------------------------------------------------------------------------
// Default Configurations
// ---------------------------------------------------------------------------
const DEFAULT_CONFIGS = {
    [Tier.FREE]: {
        tier: Tier.FREE,
        dailyLimit: 10,
        burstLimit: 3,
        burstWindowMs: 3600000, // 1 hour
    },
    [Tier.PRO]: {
        tier: Tier.PRO,
        dailyLimit: Infinity,
        burstLimit: Infinity,
        burstWindowMs: 0,
    },
};
// ---------------------------------------------------------------------------
// Rate Limiter
// ---------------------------------------------------------------------------
class RateLimiter extends node_events_1.EventEmitter {
    config;
    state;
    metrics;
    statePath;
    constructor(tier, stateDir) {
        super();
        this.config = DEFAULT_CONFIGS[tier];
        // Initialize state
        const now = new Date().toISOString();
        this.state = {
            tokens: this.config.dailyLimit === Infinity ? Infinity : this.config.dailyLimit,
            lastRefill: now,
            burstTokens: this.config.burstLimit === Infinity ? Infinity : this.config.burstLimit,
            lastBurstRefill: now,
        };
        this.metrics = {
            totalRequests: 0,
            allowedRequests: 0,
            deniedRequests: 0,
            lastReset: now,
        };
        // Setup state persistence
        const baseDir = stateDir || process.env.HOME || "/tmp";
        this.statePath = path.join(baseDir, ".openclaw/milimo", "rate-limits");
        this.loadState();
    }
    /**
     * Try to consume a token for an auto-approval.
     * Returns true if the request is allowed, false if rate limited.
     */
    tryConsume() {
        this.refillIfNeeded();
        new Date();
        // Pro tier has unlimited
        if (this.config.tier === Tier.PRO) {
            this.metrics.totalRequests++;
            this.metrics.allowedRequests++;
            this.saveState();
            return {
                allowed: true,
                remaining: Infinity,
                resetAt: this.getNextReset().toISOString(),
            };
        }
        this.metrics.totalRequests++;
        // Check burst limit first
        if (this.state.burstTokens !== Infinity && this.state.burstTokens <= 0) {
            this.metrics.deniedRequests++;
            this.saveState();
            this.emit("limited", {
                reason: "burst",
                burstResetAt: this.getBurstReset().toISOString(),
            });
            return {
                allowed: false,
                remaining: 0,
                resetAt: this.getBurstReset().toISOString(),
                reason: `Burst limit exceeded. Max ${this.config.burstLimit} per hour.`,
            };
        }
        // Check daily limit
        if (this.state.tokens !== Infinity && this.state.tokens <= 0) {
            this.metrics.deniedRequests++;
            this.saveState();
            this.emit("limited", {
                reason: "daily",
                dailyResetAt: this.getNextReset().toISOString(),
            });
            return {
                allowed: false,
                remaining: 0,
                resetAt: this.getNextReset().toISOString(),
                reason: `Daily limit exceeded. Max ${this.config.dailyLimit} per day.`,
            };
        }
        // Consume tokens
        if (this.state.tokens !== Infinity) {
            this.state.tokens--;
        }
        if (this.state.burstTokens !== Infinity) {
            this.state.burstTokens--;
        }
        this.metrics.allowedRequests++;
        this.saveState();
        this.emit("consumed", {
            remaining: this.state.tokens,
            burstRemaining: this.state.burstTokens,
        });
        return {
            allowed: true,
            remaining: this.state.tokens,
            resetAt: this.getNextReset().toISOString(),
        };
    }
    /**
     * Get current rate limit status without consuming.
     */
    getStatus() {
        this.refillIfNeeded();
        return {
            tier: this.config.tier,
            dailyLimit: this.config.dailyLimit === Infinity ? -1 : this.config.dailyLimit,
            dailyRemaining: this.state.tokens === Infinity ? -1 : this.state.tokens,
            burstLimit: this.config.burstLimit === Infinity ? -1 : this.config.burstLimit,
            burstRemaining: this.state.burstTokens === Infinity ? -1 : this.state.burstTokens,
            dailyResetAt: this.getNextReset().toISOString(),
            burstResetAt: this.getBurstReset().toISOString(),
        };
    }
    /**
     * Get metrics for monitoring.
     */
    getMetrics() {
        return { ...this.metrics };
    }
    /**
     * Reset the rate limiter (admin operation).
     */
    reset() {
        const now = new Date().toISOString();
        this.state = {
            tokens: this.config.dailyLimit === Infinity ? Infinity : this.config.dailyLimit,
            lastRefill: now,
            burstTokens: this.config.burstLimit === Infinity ? Infinity : this.config.burstLimit,
            lastBurstRefill: now,
        };
        this.metrics.lastReset = now;
        this.saveState();
        this.emit("reset");
    }
    /**
     * Refill tokens if needed based on time elapsed.
     */
    refillIfNeeded() {
        const now = new Date();
        // Check if we need to refill daily tokens
        const lastRefillDate = new Date(this.state.lastRefill);
        const nextReset = this.getNextReset(lastRefillDate);
        if (now >= nextReset) {
            this.state.tokens = this.config.dailyLimit === Infinity ? Infinity : this.config.dailyLimit;
            this.state.lastRefill = now.toISOString();
            this.emit("refill", { type: "daily", tokens: this.state.tokens });
        }
        // Check if we need to refill burst tokens
        const lastBurstRefillDate = new Date(this.state.lastBurstRefill);
        const nextBurstReset = this.getBurstReset(lastBurstRefillDate);
        if (now >= nextBurstReset) {
            this.state.burstTokens =
                this.config.burstLimit === Infinity ? Infinity : this.config.burstLimit;
            this.state.lastBurstRefill = now.toISOString();
            this.emit("refill", { type: "burst", tokens: this.state.burstTokens });
        }
    }
    /**
     * Get the next daily reset time (midnight UTC).
     */
    getNextReset(from) {
        const base = from || new Date();
        const reset = new Date(base);
        reset.setUTCDate(reset.getUTCDate() + 1);
        reset.setUTCHours(0, 0, 0, 0);
        return reset;
    }
    /**
     * Get the next burst reset time.
     */
    getBurstReset(from) {
        const base = from || new Date();
        return new Date(base.getTime() + this.config.burstWindowMs);
    }
    /**
     * Load state from disk.
     */
    loadState() {
        try {
            const stateFile = path.join(this.statePath, `${this.config.tier}.json`);
            if (fs.existsSync(stateFile)) {
                const data = JSON.parse(fs.readFileSync(stateFile, "utf-8"));
                this.state = { ...this.state, ...data.state };
                this.metrics = { ...this.metrics, ...data.metrics };
            }
        }
        catch {
            // Use defaults if load fails
        }
    }
    /**
     * Save state to disk.
     */
    saveState() {
        try {
            if (!fs.existsSync(this.statePath)) {
                fs.mkdirSync(this.statePath, { recursive: true });
            }
            const stateFile = path.join(this.statePath, `${this.config.tier}.json`);
            fs.writeFileSync(stateFile, JSON.stringify({
                state: this.state,
                metrics: this.metrics,
            }, null, 2));
        }
        catch (err) {
            this.emit("error", err);
        }
    }
}
exports.RateLimiter = RateLimiter;
// ---------------------------------------------------------------------------
// Rate Limit Metrics Tracker
// ---------------------------------------------------------------------------
class RateLimitMetricsTracker {
    limiter;
    intervalId = null;
    history = [];
    constructor(limiter) {
        this.limiter = limiter;
    }
    /**
     * Start tracking metrics at regular intervals.
     */
    start(intervalMs = 60000) {
        if (this.intervalId) {
            return;
        }
        this.intervalId = setInterval(() => {
            this.record();
        }, intervalMs);
        this.record(); // Record initial state
    }
    /**
     * Stop tracking metrics.
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    /**
     * Record current metrics.
     */
    record() {
        this.history.push({
            timestamp: new Date().toISOString(),
            metrics: this.limiter.getMetrics(),
        });
        // Keep only last 24 hours of history
        const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
        this.history = this.history.filter((h) => new Date(h.timestamp) >= cutoff);
    }
    /**
     * Get metrics history.
     */
    getHistory() {
        return [...this.history];
    }
    /**
     * Get utilization percentage.
     */
    getUtilization() {
        if (this.history.length === 0) {
            return 0;
        }
        const status = this.limiter.getStatus();
        if (status.dailyLimit === -1) {
            return 0; // Unlimited
        }
        const used = status.dailyLimit - status.dailyRemaining;
        return Math.round((used / status.dailyLimit) * 100);
    }
}
exports.RateLimitMetricsTracker = RateLimitMetricsTracker;
// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------
function createRateLimiter(tier, stateDir) {
    return new RateLimiter(tier, stateDir);
}
function getTierFromString(tier) {
    if (tier.toLowerCase() === "pro") {
        return Tier.PRO;
    }
    return Tier.FREE;
}
//# sourceMappingURL=rate-limiter.js.map