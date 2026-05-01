// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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

import * as fs from "node:fs";
import * as path from "node:path";
import { EventEmitter } from "node:events";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export enum Tier {
  FREE = "free",
  PRO = "pro",
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

// ---------------------------------------------------------------------------
// Tier Verification
// ---------------------------------------------------------------------------

const TIER_CACHE_TTL_MS = 3600000; // 1 hour

let tierCache: TierCacheEntry | null = null;

export function getEffectiveTier(configPath?: string): Tier {
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

interface MilimoConfig {
  tier?: string;
  serverUrl?: string;
  squadName?: string;
  clawRole?: string;
  meshSecret?: string;
}

function loadConfig(configPath?: string): MilimoConfig | null {
  const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
  const configPathResolved = configPath || path.join(home, ".openclaw/milimo", "config.json");

  try {
    if (!fs.existsSync(configPathResolved)) {
      return null;
    }

    const content = fs.readFileSync(configPathResolved, "utf-8");
    const config = JSON.parse(content) as MilimoConfig;

    return config;
  } catch {
    return null;
  }
}

export function invalidateTierCache(): void {
  tierCache = null;
}

// ---------------------------------------------------------------------------
// Default Configurations
// ---------------------------------------------------------------------------

const DEFAULT_CONFIGS: Record<Tier, RateLimitConfig> = {
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

export class RateLimiter extends EventEmitter {
  private config: RateLimitConfig;
  private state: RateLimitState;
  private metrics: RateLimitMetrics;
  private statePath: string;

  constructor(tier: Tier, stateDir?: string) {
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
  tryConsume(): RateLimitResult {
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
  getStatus(): {
    tier: Tier;
    dailyLimit: number;
    dailyRemaining: number;
    burstLimit: number;
    burstRemaining: number;
    dailyResetAt: string;
    burstResetAt: string;
  } {
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
  getMetrics(): RateLimitMetrics {
    return { ...this.metrics };
  }

  /**
   * Reset the rate limiter (admin operation).
   */
  reset(): void {
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
  private refillIfNeeded(): void {
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
  private getNextReset(from?: Date): Date {
    const base = from || new Date();
    const reset = new Date(base);
    reset.setUTCDate(reset.getUTCDate() + 1);
    reset.setUTCHours(0, 0, 0, 0);
    return reset;
  }

  /**
   * Get the next burst reset time.
   */
  private getBurstReset(from?: Date): Date {
    const base = from || new Date();
    return new Date(base.getTime() + this.config.burstWindowMs);
  }

  /**
   * Load state from disk.
   */
  private loadState(): void {
    try {
      const stateFile = path.join(this.statePath, `${this.config.tier}.json`);

      if (fs.existsSync(stateFile)) {
        const data = JSON.parse(fs.readFileSync(stateFile, "utf-8"));
        this.state = { ...this.state, ...data.state };
        this.metrics = { ...this.metrics, ...data.metrics };
      }
    } catch {
      // Use defaults if load fails
    }
  }

  /**
   * Save state to disk.
   */
  private saveState(): void {
    try {
      if (!fs.existsSync(this.statePath)) {
        fs.mkdirSync(this.statePath, { recursive: true });
      }

      const stateFile = path.join(this.statePath, `${this.config.tier}.json`);
      fs.writeFileSync(
        stateFile,
        JSON.stringify(
          {
            state: this.state,
            metrics: this.metrics,
          },
          null,
          2,
        ),
      );
    } catch (err) {
      this.emit("error", err);
    }
  }
}

// ---------------------------------------------------------------------------
// Rate Limit Metrics Tracker
// ---------------------------------------------------------------------------

export class RateLimitMetricsTracker {
  private limiter: RateLimiter;
  private intervalId: NodeJS.Timeout | null = null;
  private history: Array<{ timestamp: string; metrics: RateLimitMetrics }> = [];

  constructor(limiter: RateLimiter) {
    this.limiter = limiter;
  }

  /**
   * Start tracking metrics at regular intervals.
   */
  start(intervalMs: number = 60000): void {
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
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * Record current metrics.
   */
  private record(): void {
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
  getHistory(): Array<{ timestamp: string; metrics: RateLimitMetrics }> {
    return [...this.history];
  }

  /**
   * Get utilization percentage.
   */
  getUtilization(): number {
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

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export function createRateLimiter(tier: Tier, stateDir?: string): RateLimiter {
  return new RateLimiter(tier, stateDir);
}

export function getTierFromString(tier: string): Tier {
  if (tier.toLowerCase() === "pro") {
    return Tier.PRO;
  }
  return Tier.FREE;
}
