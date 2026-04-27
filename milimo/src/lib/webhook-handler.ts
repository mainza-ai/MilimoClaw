// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Stripe Webhook Handler
 *
 * Handles Stripe webhook events for subscription management:
 * - customer.subscription.created → upgrade to PRO
 * - customer.subscription.deleted → downgrade to FREE
 * - invoice.payment_failed → War Room alert
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

export interface WebhookEvent {
  id: string;
  type: string;
  data: {
    object: {
      id: string;
      customer?: string;
      status?: string;
      metadata?: Record<string, string>;
    };
  };
}

export interface SubscriptionChange {
  customerId: string;
  tier: "free" | "pro";
  previousTier: "free" | "pro";
  reason: string;
  timestamp: string;
}

export interface PaymentFailureAlert {
  customerId: string;
  invoiceId: string;
  amount: number;
  currency: string;
  timestamp: string;
}

export interface WebhookHandlerOptions {
  configPath?: string;
  alertDir?: string;
}

const DEFAULT_CONFIG_PATH = join(homedir(), ".openclaw-data/milimo", "config.json");
const DEFAULT_ALERT_DIR = join(homedir(), ".openclaw-data/milimo", "alerts");

export class StripeWebhookHandler {
  private configPath: string;
  private alertDir: string;

  constructor(options?: WebhookHandlerOptions) {
    this.configPath = options?.configPath || DEFAULT_CONFIG_PATH;
    this.alertDir = options?.alertDir || DEFAULT_ALERT_DIR;
  }

  public handleEvent(event: WebhookEvent): SubscriptionChange | PaymentFailureAlert | null {
    switch (event.type) {
      case "customer.subscription.created":
        return this.handleSubscriptionCreated(event);

      case "customer.subscription.deleted":
        return this.handleSubscriptionDeleted(event);

      case "invoice.payment_failed":
        return this.handlePaymentFailed(event);

      default:
        return null;
    }
  }

  private handleSubscriptionCreated(event: WebhookEvent): SubscriptionChange {
    const subscription = event.data.object;
    const customerId = subscription.customer || subscription.id;
    const previousTier = this.getCurrentTier();

    // Upgrade to PRO
    this.updateTier("pro", {
      stripeCustomerId: customerId,
      subscriptionId: subscription.id,
      subscriptionStatus: subscription.status,
      upgradedAt: new Date().toISOString(),
    });

    return {
      customerId,
      tier: "pro",
      previousTier: previousTier as "free" | "pro",
      reason: "Subscription created",
      timestamp: new Date().toISOString(),
    };
  }

  private handleSubscriptionDeleted(event: WebhookEvent): SubscriptionChange {
    const subscription = event.data.object;
    const customerId = subscription.customer || subscription.id;
    const previousTier = this.getCurrentTier();

    // Downgrade to FREE
    this.updateTier("free", {
      stripeCustomerId: customerId,
      subscriptionId: subscription.id,
      subscriptionStatus: "canceled",
      canceledAt: new Date().toISOString(),
    });

    return {
      customerId,
      tier: "free",
      previousTier: previousTier as "free" | "pro",
      reason: "Subscription canceled",
      timestamp: new Date().toISOString(),
    };
  }

  private handlePaymentFailed(event: WebhookEvent): PaymentFailureAlert {
    const invoice = event.data.object;
    const customerId = invoice.customer || invoice.id;

    // Create alert for War Room
    this.createAlert({
      type: "payment_failed",
      customerId,
      invoiceId: invoice.id,
      message: `Payment failed for customer ${customerId}`,
      timestamp: new Date().toISOString(),
    });

    return {
      customerId,
      invoiceId: invoice.id,
      amount: 0,
      currency: "usd",
      timestamp: new Date().toISOString(),
    };
  }

  private getCurrentTier(): string {
    try {
      if (!existsSync(this.configPath)) {
        return "free";
      }

      const content = readFileSync(this.configPath, "utf-8");
      const config = JSON.parse(content);

      return config.tier || "free";
    } catch {
      return "free";
    }
  }

  private updateTier(tier: "free" | "pro", metadata: Record<string, unknown>): void {
    try {
      // Ensure config directory exists
      const configDir = join(this.configPath, "..");
      if (!existsSync(configDir)) {
        mkdirSync(configDir, { recursive: true });
      }

      // Load existing config or create new
      let config: Record<string, unknown> = {};
      if (existsSync(this.configPath)) {
        try {
          const content = readFileSync(this.configPath, "utf-8");
          config = JSON.parse(content);
        } catch {
          config = {};
        }
      }

      // Update tier
      config.tier = tier;
      config.tierMetadata = {
        ...(config.tierMetadata as Record<string, unknown>),
        ...metadata,
        updatedAt: new Date().toISOString(),
      };

      // Save config
      writeFileSync(this.configPath, JSON.stringify(config, null, 2));
    } catch (error) {
      console.error("Failed to update tier:", error);
    }
  }

  private createAlert(alert: Record<string, unknown>): void {
    try {
      // Ensure alert directory exists
      if (!existsSync(this.alertDir)) {
        mkdirSync(this.alertDir, { recursive: true });
      }

      // Write alert file
      const alertPath = join(this.alertDir, `payment-${Date.now()}.json`);
      writeFileSync(alertPath, JSON.stringify(alert, null, 2));
    } catch (error) {
      console.error("Failed to create alert:", error);
    }
  }
}

export function createWebhookHandler(options?: WebhookHandlerOptions): StripeWebhookHandler {
  return new StripeWebhookHandler(options);
}
