// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tenant Limits
 *
 * Enforces resource limits per tenant.
 */

import type { Tenant, TenantLimits } from "./manager.js";

// ---------------------------------------------------------------------------

export interface UsageMetrics {
  squads: number;
  users: number;
  claws: number;
  storageBytes: number;
  apiCalls: number;
}

export interface LimitCheckResult {
  allowed: boolean;
  resource: string;
  current: number;
  limit: number;
  remaining: number;
  message?: string;
}

export interface UsageAlert {
  tenantId: string;
  resource: string;
  currentUsage: number;
  limit: number;
  percentageUsed: number;
  severity: "warning" | "critical";
}

// ---------------------------------------------------------------------------

const WARNING_THRESHOLD = 0.8;
const CRITICAL_THRESHOLD = 0.95;

// ---------------------------------------------------------------------------

/**
 * Tenant Limits Enforcer
 *
 * Checks and enforces resource limits for tenants.
 */
export class TenantLimitsEnforcer {
  private usageStore = new Map<string, UsageMetrics>();

  /**
   * Check if a resource usage is within limits.
   */
  checkLimit(
    tenant: Tenant,
    resource: keyof UsageMetrics,
    increment: number = 1
  ): LimitCheckResult {
    const limits = tenant.limits;
    const usage = this.getUsage(tenant.id);
    const current = usage[resource];

    const limitKey = this.getLimitKey(resource);
    const limit = limits[limitKey as keyof TenantLimits] as number;

    if (limit === -1) {
      return {
        allowed: true,
        resource,
        current,
        limit: -1,
        remaining: -1,
        message: "Unlimited",
      };
    }

    const newTotal = current + increment;
    const allowed = newTotal <= limit;
    const remaining = Math.max(0, limit - current);

    return {
      allowed,
      resource,
      current,
      limit,
      remaining,
      message: allowed
        ? undefined
        : `Limit exceeded: ${resource} (${current}/${limit})`,
    };
  }

  /**
   * Record usage for a tenant.
   */
  recordUsage(
    tenantId: string,
    resource: keyof UsageMetrics,
    amount: number = 1
  ): void {
    const usage = this.usageStore.get(tenantId) || this.getDefaultUsage();
    usage[resource] += amount;
    this.usageStore.set(tenantId, usage);
  }

  /**
   * Get current usage for a tenant.
   */
  getUsage(tenantId: string): UsageMetrics {
    return this.usageStore.get(tenantId) || this.getDefaultUsage();
  }

  /**
   * Reset usage for a tenant (e.g., monthly reset).
   */
  resetUsage(tenantId: string, resource?: keyof UsageMetrics): void {
    if (resource) {
      const usage = this.usageStore.get(tenantId);
      if (usage) {
        usage[resource] = 0;
      }
    } else {
      this.usageStore.set(tenantId, this.getDefaultUsage());
    }
  }

  /**
   * Check if usage is approaching limits and generate alerts.
   */
  checkAlerts(tenant: Tenant): UsageAlert[] {
    const alerts: UsageAlert[] = [];
    const usage = this.getUsage(tenant.id);
    const limits = tenant.limits;

    const resources: (keyof UsageMetrics)[] = [
      "squads",
      "users",
      "claws",
      "storageBytes",
      "apiCalls",
    ];

    for (const resource of resources) {
      const limitKey = this.getLimitKey(resource);
      const limit = limits[limitKey as keyof TenantLimits] as number;

      if (limit === -1) continue;

      const current = usage[resource];
      const percentage = current / limit;

      if (percentage >= CRITICAL_THRESHOLD) {
        alerts.push({
          tenantId: tenant.id,
          resource,
          currentUsage: current,
          limit,
          percentageUsed: percentage * 100,
          severity: "critical",
        });
      } else if (percentage >= WARNING_THRESHOLD) {
        alerts.push({
          tenantId: tenant.id,
          resource,
          currentUsage: current,
          limit,
          percentageUsed: percentage * 100,
          severity: "warning",
        });
      }
    }

    return alerts;
  }

  /**
   * Get usage percentage for a resource.
   */
  getUsagePercentage(
    tenant: Tenant,
    resource: keyof UsageMetrics
  ): number {
    const usage = this.getUsage(tenant.id);
    const limitKey = this.getLimitKey(resource);
    const limit = tenant.limits[limitKey as keyof TenantLimits] as number;

    if (limit === -1) return 0;

    return (usage[resource] / limit) * 100;
  }

  /**
   * Get usage summary for a tenant.
   */
  getUsageSummary(tenant: Tenant): {
    resource: string;
    current: number;
    limit: number;
    percentage: number;
    status: "ok" | "warning" | "critical";
  }[] {
    const usage = this.getUsage(tenant.id);
    const limits = tenant.limits;
    const summary: Array<{
      resource: string;
      current: number;
      limit: number;
      percentage: number;
      status: "ok" | "warning" | "critical";
    }> = [];

    const resources: Array<{
      key: keyof UsageMetrics;
      label: string;
      limitKey: string;
    }> = [
      { key: "squads", label: "Squads", limitKey: "maxSquads" },
      { key: "users", label: "Users", limitKey: "maxUsersPerSquad" },
      { key: "claws", label: "Claws", limitKey: "maxClawsPerSquad" },
      { key: "storageBytes", label: "Storage (GB)", limitKey: "maxStorageGb" },
      { key: "apiCalls", label: "API Calls", limitKey: "maxApiCallsPerMonth" },
    ];

    for (const { key, label, limitKey } of resources) {
      const limit = limits[limitKey as keyof TenantLimits] as number;
      const current = usage[key];

      let percentage = 0;
      let status: "ok" | "warning" | "critical" = "ok";

      if (limit !== -1) {
        percentage = (current / limit) * 100;
        status =
          percentage >= CRITICAL_THRESHOLD * 100
            ? "critical"
            : percentage >= WARNING_THRESHOLD * 100
            ? "warning"
            : "ok";
      }

      summary.push({
        resource: label,
        current: key === "storageBytes" ? Math.ceil(current / (1024 * 1024 * 1024)) : current,
        limit,
        percentage,
        status,
      });
    }

    return summary;
  }

  /**
   * Check if a feature is enabled for a tenant.
   */
  hasFeature(tenant: Tenant, feature: string): boolean {
    return tenant.limits.features.includes(feature);
  }

  /**
   * Validate feature access.
   */
  requireFeature(tenant: Tenant, feature: string): void {
    if (!this.hasFeature(tenant, feature)) {
      throw new Error(
        `Feature '${feature}' is not available on your plan. ` +
          `Current plan: ${tenant.billing.plan}`
      );
    }
  }

  /**
   * Get default empty usage.
   */
  private getDefaultUsage(): UsageMetrics {
    return {
      squads: 0,
      users: 0,
      claws: 0,
      storageBytes: 0,
      apiCalls: 0,
    };
  }

  /**
   * Map usage resource to limit key.
   */
  private getLimitKey(resource: keyof UsageMetrics): string {
    const mapping: Record<keyof UsageMetrics, string> = {
      squads: "maxSquads",
      users: "maxUsersPerSquad",
      claws: "maxClawsPerSquad",
      storageBytes: "maxStorageGb",
      apiCalls: "maxApiCallsPerMonth",
    };
    return mapping[resource];
  }
}

// ---------------------------------------------------------------------------

export const tenantLimitsEnforcer = new TenantLimitsEnforcer();
