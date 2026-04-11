"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliPaymentCheckout = cliPaymentCheckout;
exports.cliPaymentStatus = cliPaymentStatus;
exports.cliPaymentBalance = cliPaymentBalance;
exports.cliPaymentHistory = cliPaymentHistory;
exports.cliPaymentInvoice = cliPaymentInvoice;
exports.cliPaymentConnect = cliPaymentConnect;
// ---------------------------------------------------------------------------
const DEFAULT_API_BASE = "https://api.milimoclaw.com";
function getApiBase(pluginConfig) {
    const envUrl = process.env.MILIMO_SERVER_URL;
    const configUrl = pluginConfig.serverUrl;
    if (envUrl) {
        return envUrl;
    }
    if (configUrl) {
        return configUrl;
    }
    return DEFAULT_API_BASE;
}
// ---------------------------------------------------------------------------
async function apiRequest(endpoint, pluginConfig, options = {}) {
    const { method = "GET", body, token } = options;
    const apiBase = getApiBase(pluginConfig);
    try {
        const headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        const response = await fetch(`${apiBase}${endpoint}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({ error: { message: response.statusText } }));
            return {
                ok: false,
                error: data.error?.message || "Request failed",
            };
        }
        const data = await response.json();
        return { ok: true, data };
    }
    catch (err) {
        return {
            ok: false,
            error: err.message,
        };
    }
}
// ---------------------------------------------------------------------------
// Checkout
// ---------------------------------------------------------------------------
async function cliPaymentCheckout(opts) {
    const { logger } = opts;
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │          💳  CHECKOUT  💳           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    logger.info(`  Blueprint: ${opts.blueprintId}`);
    logger.info("");
    const successUrl = opts.successUrl || "milimo://checkout/success";
    const cancelUrl = opts.cancelUrl || "milimo://checkout/cancel";
    logger.info("  Creating checkout session...");
    const result = await apiRequest("/api/payments/checkout", opts.pluginConfig, {
        method: "POST",
        body: {
            blueprintId: opts.blueprintId,
            successUrl,
            cancelUrl,
        },
    });
    if (!result.ok) {
        logger.error(`  ✗ Failed to create checkout: ${result.error}`);
        logger.info("");
        return;
    }
    const data = result.data;
    logger.info(`  Session: ${data.sessionId}`);
    logger.info(`  Amount: $${(data.amount / 100).toFixed(2)}`);
    logger.info(`  Platform fee: $${(data.fee / 100).toFixed(2)}`);
    logger.info("");
    logger.info("  ▶ Open this URL to complete payment:");
    logger.info("");
    logger.info(`    ${data.url}`);
    logger.info("");
    logger.info("  After payment, verify with:");
    logger.info(`    openclaw milimo payment status --session ${data.sessionId}`);
    logger.info("");
}
// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------
async function cliPaymentStatus(opts) {
    const { logger } = opts;
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │          📊  PAYMENT STATUS  📊           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    if (!opts.sessionId) {
        logger.error("  ✗ --session <id> is required");
        logger.info("");
        return;
    }
    const result = await apiRequest(`/api/payments/session/${opts.sessionId}`, opts.pluginConfig);
    if (!result.ok) {
        logger.error(`  ✗ Failed to get status: ${result.error}`);
        logger.info("");
        return;
    }
    const data = result.data;
    const statusEmoji = {
        paid: "✅",
        unpaid: "⏳",
        canceled: "❌",
        expired: "⏰",
    };
    const emoji = statusEmoji[data.status] || "❓";
    logger.info(`  Session: ${data.sessionId}`);
    logger.info(`  Status: ${emoji} ${data.status.toUpperCase()}`);
    logger.info(`  Amount: $${(data.amount / 100).toFixed(2)}`);
    if (data.blueprintId) {
        logger.info(`  Blueprint: ${data.blueprintId}`);
    }
    logger.info(`  Created: ${new Date(data.createdAt).toLocaleString()}`);
    logger.info("");
    if (data.status === "paid") {
        logger.info("  ✓ Payment complete! Access has been granted.");
        logger.info(`    Run: openclaw milimo payment invoice --session ${opts.sessionId}`);
    }
    else if (data.status === "unpaid") {
        logger.info("  ⏳ Payment pending. Complete checkout in your browser.");
    }
    else {
        logger.info("  ⚠ Payment not completed. Try checkout again.");
    }
    logger.info("");
}
// ---------------------------------------------------------------------------
// Balance
// ---------------------------------------------------------------------------
async function cliPaymentBalance(opts) {
    const { logger } = opts;
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │          💰  SELLER BALANCE  💰           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    const result = await apiRequest("/api/payments/balance", opts.pluginConfig);
    if (!result.ok) {
        logger.error(`  ✗ Failed to get balance: ${result.error}`);
        logger.info("  Note: Make sure you have connected a Stripe account.");
        logger.info("    Run: openclaw milimo payment connect");
        logger.info("");
        return;
    }
    const data = result.data;
    logger.info(`  Available: $${(data.availableBalanceCents / 100).toFixed(2)}`);
    logger.info(`  Pending:   $${(data.pendingBalanceCents / 100).toFixed(2)}`);
    logger.info(`  Total:     $${(data.totalEarnedCents / 100).toFixed(2)}`);
    logger.info("");
    if (data.nextPayoutDate) {
        logger.info(`  Next Payout: ${new Date(data.nextPayoutDate).toLocaleDateString()}`);
        if (data.nextPayoutAmountCents) {
            logger.info(`  Payout Amount: $${(data.nextPayoutAmountCents / 100).toFixed(2)}`);
        }
    }
    logger.info("");
}
// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------
async function cliPaymentHistory(opts) {
    const { logger } = opts;
    const limit = opts.limit || 10;
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │          📜  TRANSACTION HISTORY  📜           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    const result = await apiRequest(`/api/payments/history?limit=${limit}`, opts.pluginConfig);
    if (!result.ok) {
        logger.error(`  ✗ Failed to get history: ${result.error}`);
        logger.info("");
        return;
    }
    const data = result.data;
    if (data.length === 0) {
        logger.info("  No transactions found.");
        logger.info("");
        return;
    }
    logger.info(`  ${"ID".padEnd(30)} ${"Amount".padEnd(12)} ${"Status".padEnd(10)} Date`);
    logger.info(`  ${"─".repeat(70)}`);
    for (const tx of data) {
        const id = tx.id.substring(0, 28);
        const amount = `$${(tx.amount / 100).toFixed(2)}`.padEnd(12);
        const status = tx.status.toUpperCase().padEnd(10);
        const date = new Date(tx.createdAt).toLocaleDateString();
        logger.info(`  ${id} ${amount} ${status} ${date}`);
    }
    logger.info("");
    logger.info(`  Showing last ${data.length} transactions.`);
    logger.info("");
}
// ---------------------------------------------------------------------------
// Invoice
// ---------------------------------------------------------------------------
async function cliPaymentInvoice(opts) {
    const { logger } = opts;
    const format = opts.format || "text";
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │          🧾  INVOICE  🧾           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    const result = await apiRequest(`/api/payments/invoice/${opts.sessionId}?format=${format}`, opts.pluginConfig);
    if (!result.ok) {
        logger.error(`  ✗ Failed to get invoice: ${result.error}`);
        logger.info("");
        return;
    }
    if (format === "json") {
        logger.info(JSON.stringify(result.data, null, 2));
    }
    else {
        const data = result.data;
        logger.info(data.invoice);
    }
    logger.info("");
}
// ---------------------------------------------------------------------------
// Connect (Stripe Onboarding)
// ---------------------------------------------------------------------------
async function cliPaymentConnect(opts) {
    const { logger } = opts;
    logger.info("");
    logger.info("  ┌─────────────────────────────────────────────────────┐");
    logger.info("  │          🔗  CONNECT STRIPE ACCOUNT  🔗           │");
    logger.info("  └─────────────────────────────────────────────────────┘");
    logger.info("");
    logger.info(`  Display Name: ${opts.displayName}`);
    logger.info(`  Email: ${opts.email}`);
    logger.info("");
    logger.info("  Creating connected account...");
    const result = await apiRequest("/api/payments/connect", opts.pluginConfig, {
        method: "POST",
        body: {
            displayName: opts.displayName,
            email: opts.email,
        },
    });
    if (!result.ok) {
        logger.error(`  ✗ Failed to create account: ${result.error}`);
        logger.info("");
        return;
    }
    const data = result.data;
    logger.info(`  Account ID: ${data.accountId}`);
    logger.info("");
    logger.info("  ▶ Complete onboarding at:");
    logger.info("");
    logger.info(`    ${data.onboardingUrl}`);
    logger.info("");
    logger.info("  After onboarding, verify with:");
    logger.info(`    openclaw milimo payment status --account ${data.accountId}`);
    logger.info("");
}
//# sourceMappingURL=payment.js.map
