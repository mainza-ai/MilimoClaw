"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.StripeWebhookHandler = void 0;
exports.createWebhookHandler = createWebhookHandler;
/**
 * Stripe Webhook Handler
 *
 * Handles Stripe webhook events for subscription management:
 * - customer.subscription.created → upgrade to PRO
 * - customer.subscription.deleted → downgrade to FREE
 * - invoice.payment_failed → War Room alert
 */
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const node_os_1 = require("node:os");
const DEFAULT_CONFIG_PATH = (0, node_path_1.join)((0, node_os_1.homedir)(), ".openclaw-data/milimo", "config.json");
const DEFAULT_ALERT_DIR = (0, node_path_1.join)((0, node_os_1.homedir)(), ".openclaw-data/milimo", "alerts");
class StripeWebhookHandler {
    configPath;
    alertDir;
    constructor(options) {
        this.configPath = options?.configPath || DEFAULT_CONFIG_PATH;
        this.alertDir = options?.alertDir || DEFAULT_ALERT_DIR;
    }
    handleEvent(event) {
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
    handleSubscriptionCreated(event) {
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
            previousTier: previousTier,
            reason: "Subscription created",
            timestamp: new Date().toISOString(),
        };
    }
    handleSubscriptionDeleted(event) {
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
            previousTier: previousTier,
            reason: "Subscription canceled",
            timestamp: new Date().toISOString(),
        };
    }
    handlePaymentFailed(event) {
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
    getCurrentTier() {
        try {
            if (!(0, node_fs_1.existsSync)(this.configPath)) {
                return "free";
            }
            const content = (0, node_fs_1.readFileSync)(this.configPath, "utf-8");
            const config = JSON.parse(content);
            return config.tier || "free";
        }
        catch {
            return "free";
        }
    }
    updateTier(tier, metadata) {
        try {
            // Ensure config directory exists
            const configDir = (0, node_path_1.join)(this.configPath, "..");
            if (!(0, node_fs_1.existsSync)(configDir)) {
                (0, node_fs_1.mkdirSync)(configDir, { recursive: true });
            }
            // Load existing config or create new
            let config = {};
            if ((0, node_fs_1.existsSync)(this.configPath)) {
                try {
                    const content = (0, node_fs_1.readFileSync)(this.configPath, "utf-8");
                    config = JSON.parse(content);
                }
                catch {
                    config = {};
                }
            }
            // Update tier
            config.tier = tier;
            config.tierMetadata = {
                ...config.tierMetadata,
                ...metadata,
                updatedAt: new Date().toISOString(),
            };
            // Save config
            (0, node_fs_1.writeFileSync)(this.configPath, JSON.stringify(config, null, 2));
        }
        catch (error) {
            console.error("Failed to update tier:", error);
        }
    }
    createAlert(alert) {
        try {
            // Ensure alert directory exists
            if (!(0, node_fs_1.existsSync)(this.alertDir)) {
                (0, node_fs_1.mkdirSync)(this.alertDir, { recursive: true });
            }
            // Write alert file
            const alertPath = (0, node_path_1.join)(this.alertDir, `payment-${Date.now()}.json`);
            (0, node_fs_1.writeFileSync)(alertPath, JSON.stringify(alert, null, 2));
        }
        catch (error) {
            console.error("Failed to create alert:", error);
        }
    }
}
exports.StripeWebhookHandler = StripeWebhookHandler;
function createWebhookHandler(options) {
    return new StripeWebhookHandler(options);
}
//# sourceMappingURL=webhook-handler.js.map