// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Tenant Manager
 *
 * Manages tenant CRUD operations for multi-tenant deployment.
 */

import { randomUUID } from "crypto";

// ---------------------------------------------------------------------------

export type TenantType = "university" | "enterprise" | "accelerator" | "custom";
export type TenantStatus = "active" | "suspended" | "trial" | "cancelled";
export type BillingPlan = "trial" | "starter" | "professional" | "enterprise";

// ---------------------------------------------------------------------------

export interface TenantBranding {
  logoUrl: string;
  primaryColor: string;
  secondaryColor: string;
  fontFamily?: string;
  customCss?: string;
  customDomain?: string;
}

export interface TenantLimits {
  maxSquads: number;
  maxUsersPerSquad: number;
  maxClawsPerSquad: number;
  maxStorageGb: number;
  maxApiCallsPerMonth: number;
  features: string[];
}

export interface TenantBilling {
  plan: BillingPlan;
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
  billingEmail: string;
}

export interface TenantSettings {
  ssoEnabled: boolean;
  ssoProvider?: "saml" | "oidc";
  ssoConfig?: Record<string, unknown>;
  customBlueprintsEnabled: boolean;
  whitelabeledMobileApp: boolean;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  type: TenantType;
  status: TenantStatus;
  branding: TenantBranding;
  limits: TenantLimits;
  billing: TenantBilling;
  settings: TenantSettings;
  createdAt: Date;
  updatedAt: Date;
  expiresAt?: Date;
}

export interface CreateTenantParams {
  name: string;
  slug: string;
  type: TenantType;
  billing: Partial<TenantBilling>;
  limits?: Partial<TenantLimits>;
  settings?: Partial<TenantSettings>;
  branding?: Partial<TenantBranding>;
}

export interface UpdateTenantParams {
  name?: string;
  status?: TenantStatus;
  branding?: Partial<TenantBranding>;
  limits?: Partial<TenantLimits>;
  settings?: Partial<TenantSettings>;
}

// ---------------------------------------------------------------------------

const DEFAULT_BRANDING: TenantBranding = {
  logoUrl: "",
  primaryColor: "#4F46E5",
  secondaryColor: "#10B981",
};

const PLAN_LIMITS: Record<BillingPlan, TenantLimits> = {
  trial: {
    maxSquads: 3,
    maxUsersPerSquad: 3,
    maxClawsPerSquad: 3,
    maxStorageGb: 1,
    maxApiCallsPerMonth: 10000,
    features: ["basic_analytics"],
  },
  starter: {
    maxSquads: 10,
    maxUsersPerSquad: 5,
    maxClawsPerSquad: 4,
    maxStorageGb: 10,
    maxApiCallsPerMonth: 100000,
    features: ["basic_analytics", "email_support"],
  },
  professional: {
    maxSquads: 50,
    maxUsersPerSquad: 10,
    maxClawsPerSquad: 5,
    maxStorageGb: 50,
    maxApiCallsPerMonth: 1000000,
    features: ["basic_analytics", "email_support", "priority_support", "custom_blueprints"],
  },
  enterprise: {
    maxSquads: -1,
    maxUsersPerSquad: -1,
    maxClawsPerSquad: 5,
    maxStorageGb: -1,
    maxApiCallsPerMonth: -1,
    features: [
      "basic_analytics",
      "email_support",
      "priority_support",
      "custom_blueprints",
      "sso",
      "analytics",
      "api_access",
      "dedicated_support",
    ],
  },
};

const DEFAULT_SETTINGS: TenantSettings = {
  ssoEnabled: false,
  customBlueprintsEnabled: false,
  whitelabeledMobileApp: false,
};

// ---------------------------------------------------------------------------

// In-memory tenant store (replace with database in production)
const tenants = new Map<string, Tenant>();
const slugIndex = new Map<string, string>();

// ---------------------------------------------------------------------------

/**
 * Tenant Manager
 *
 * Handles tenant CRUD operations and lookups.
 */
export class TenantManager {
  /**
   * Create a new tenant.
   */
  async createTenant(params: CreateTenantParams): Promise<Tenant> {
    const id = `tenant_${randomUUID().replace(/-/g, "").substring(0, 12)}`;
    const now = new Date();

    const plan = params.billing?.plan || "trial";
    const defaultLimits = PLAN_LIMITS[plan];

    const tenant: Tenant = {
      id,
      name: params.name,
      slug: params.slug.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
      type: params.type,
      status: plan === "trial" ? "trial" : "active",
      branding: { ...DEFAULT_BRANDING, ...params.branding },
      limits: { ...defaultLimits, ...params.limits },
      billing: {
        plan,
        billingEmail: params.billing?.billingEmail || "",
        stripeCustomerId: params.billing?.stripeCustomerId,
        stripeSubscriptionId: params.billing?.stripeSubscriptionId,
      },
      settings: { ...DEFAULT_SETTINGS, ...params.settings },
      createdAt: now,
      updatedAt: now,
    };

    if (slugIndex.has(tenant.slug)) {
      throw new Error(`Tenant with slug '${tenant.slug}' already exists`);
    }

    tenants.set(id, tenant);
    slugIndex.set(tenant.slug, id);

    return tenant;
  }

  /**
   * Get a tenant by ID.
   */
  async getTenant(id: string): Promise<Tenant | null> {
    return tenants.get(id) || null;
  }

  /**
   * Get a tenant by slug.
   */
  async getTenantBySlug(slug: string): Promise<Tenant | null> {
    const id = slugIndex.get(slug.toLowerCase());
    return id ? tenants.get(id) || null : null;
  }

  /**
   * Update a tenant.
   */
  async updateTenant(id: string, params: UpdateTenantParams): Promise<Tenant | null> {
    const tenant = tenants.get(id);
    if (!tenant) {
      return null;
    }

    if (params.name) tenant.name = params.name;
    if (params.status) tenant.status = params.status;
    if (params.branding) tenant.branding = { ...tenant.branding, ...params.branding };
    if (params.limits) tenant.limits = { ...tenant.limits, ...params.limits };
    if (params.settings) tenant.settings = { ...tenant.settings, ...params.settings };

    tenant.updatedAt = new Date();

    return tenant;
  }

  /**
   * Delete a tenant.
   */
  async deleteTenant(id: string): Promise<boolean> {
    const tenant = tenants.get(id);
    if (!tenant) {
      return false;
    }

    tenants.delete(id);
    slugIndex.delete(tenant.slug);

    return true;
  }

  /**
   * List all tenants.
   */
  async listTenants(options?: {
    type?: TenantType;
    status?: TenantStatus;
    limit?: number;
    offset?: number;
  }): Promise<Tenant[]> {
    let results = Array.from(tenants.values());

    if (options?.type) {
      results = results.filter((t) => t.type === options.type);
    }

    if (options?.status) {
      results = results.filter((t) => t.status === options.status);
    }

    const offset = options?.offset || 0;
    const limit = options?.limit || results.length;

    return results.slice(offset, offset + limit);
  }

  /**
   * Check if a tenant exists.
   */
  async tenantExists(id: string): Promise<boolean> {
    return tenants.has(id);
  }

  /**
   * Get tenant count.
   */
  async getTenantCount(): Promise<number> {
    return tenants.size;
  }

  /**
   * Suspend a tenant.
   */
  async suspendTenant(id: string): Promise<Tenant | null> {
    return this.updateTenant(id, { status: "suspended" });
  }

  /**
   * Activate a tenant.
   */
  async activateTenant(id: string): Promise<Tenant | null> {
    return this.updateTenant(id, { status: "active" });
  }

  /**
   * Upgrade tenant plan.
   */
  async upgradePlan(id: string, plan: BillingPlan): Promise<Tenant | null> {
    const tenant = tenants.get(id);
    if (!tenant) {
      return null;
    }

    tenant.billing.plan = plan;
    tenant.limits = { ...PLAN_LIMITS[plan], ...tenant.limits };
    tenant.updatedAt = new Date();

    return tenant;
  }
}

// ---------------------------------------------------------------------------

/**
 * Get default limits for a plan.
 */
export function getDefaultLimits(plan: BillingPlan): TenantLimits {
  return { ...PLAN_LIMITS[plan] };
}

/**
 * Validate a slug format.
 */
export function isValidSlug(slug: string): boolean {
  return /^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$/.test(slug);
}

/**
 * Generate a slug from a name.
 */
export function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .substring(0, 63);
}

// ---------------------------------------------------------------------------

export const tenantManager = new TenantManager();
