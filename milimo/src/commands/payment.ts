// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `openclaw milimo payment` — Payment and marketplace operations.
 *
 * Subcommands: checkout, status, balance, history, invoice, connect.
 */

import type { PluginLogger, MilimoConfig } from "../index.js";

// ---------------------------------------------------------------------------

interface PaymentCheckoutOptions {
  blueprintId: string;
  successUrl?: string;
  cancelUrl?: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface PaymentStatusOptions {
  sessionId?: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface PaymentBalanceOptions {
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface PaymentHistoryOptions {
  limit?: number;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface PaymentInvoiceOptions {
  sessionId: string;
  format?: "text" | "json" | "html";
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface PaymentConnectOptions {
  displayName: string;
  email: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

// ---------------------------------------------------------------------------

const API_BASE = process.env.MILIMO_SERVER_URL || "http://localhost:3001";

async function apiRequest(
  endpoint: string,
  options: {
    method?: "GET" | "POST";
    body?: Record<string, unknown>;
    token?: string;
  } = {}
): Promise<{ ok: boolean; data?: unknown; error?: string }> {
  const { method = "GET", body, token } = options;

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        ok: false,
        error: (data as any).error?.message || "Request failed",
      };
    }

    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      error: (err as Error).message,
    };
  }
}

// ---------------------------------------------------------------------------
// Checkout
// ---------------------------------------------------------------------------

export async function cliPaymentCheckout(opts: PaymentCheckoutOptions): Promise<void> {
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

  const result = await apiRequest("/api/payments/checkout", {
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

  const data = result.data as {
    sessionId: string;
    url: string;
    amount: number;
    fee: number;
  };

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

export async function cliPaymentStatus(opts: PaymentStatusOptions): Promise<void> {
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

  const result = await apiRequest(`/api/payments/session/${opts.sessionId}`);

  if (!result.ok) {
    logger.error(`  ✗ Failed to get status: ${result.error}`);
    logger.info("");
    return;
  }

  const data = result.data as {
    sessionId: string;
    status: string;
    amount: number;
    blueprintId?: string;
    createdAt: string;
  };

  const statusEmoji: Record<string, string> = {
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
  } else if (data.status === "unpaid") {
    logger.info("  ⏳ Payment pending. Complete checkout in your browser.");
  } else {
    logger.info("  ⚠ Payment not completed. Try checkout again.");
  }

  logger.info("");
}

// ---------------------------------------------------------------------------
// Balance
// ---------------------------------------------------------------------------

export async function cliPaymentBalance(opts: PaymentBalanceOptions): Promise<void> {
  const { logger } = opts;

  logger.info("");
  logger.info("  ┌─────────────────────────────────────────────────────┐");
  logger.info("  │          💰  SELLER BALANCE  💰           │");
  logger.info("  └─────────────────────────────────────────────────────┘");
  logger.info("");

  const result = await apiRequest("/api/payments/balance");

  if (!result.ok) {
    logger.error(`  ✗ Failed to get balance: ${result.error}`);
    logger.info("  Note: Make sure you have connected a Stripe account.");
    logger.info("    Run: openclaw milimo payment connect");
    logger.info("");
    return;
  }

  const data = result.data as {
    availableBalanceCents: number;
    pendingBalanceCents: number;
    totalEarnedCents: number;
    nextPayoutDate?: string;
    nextPayoutAmountCents?: number;
  };

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

export async function cliPaymentHistory(opts: PaymentHistoryOptions): Promise<void> {
  const { logger } = opts;
  const limit = opts.limit || 10;

  logger.info("");
  logger.info("  ┌─────────────────────────────────────────────────────┐");
  logger.info("  │          📜  TRANSACTION HISTORY  📜           │");
  logger.info("  └─────────────────────────────────────────────────────┘");
  logger.info("");

  const result = await apiRequest(`/api/payments/history?limit=${limit}`);

  if (!result.ok) {
    logger.error(`  ✗ Failed to get history: ${result.error}`);
    logger.info("");
    return;
  }

  const data = result.data as Array<{
    id: string;
    amount: number;
    status: string;
    createdAt: string;
    description?: string;
  }>;

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

export async function cliPaymentInvoice(opts: PaymentInvoiceOptions): Promise<void> {
  const { logger } = opts;
  const format = opts.format || "text";

  logger.info("");
  logger.info("  ┌─────────────────────────────────────────────────────┐");
  logger.info("  │          🧾  INVOICE  🧾           │");
  logger.info("  └─────────────────────────────────────────────────────┘");
  logger.info("");

  const result = await apiRequest(
    `/api/payments/invoice/${opts.sessionId}?format=${format}`
  );

  if (!result.ok) {
    logger.error(`  ✗ Failed to get invoice: ${result.error}`);
    logger.info("");
    return;
  }

  if (format === "json") {
    logger.info(JSON.stringify(result.data, null, 2));
  } else {
    const data = result.data as { invoice: string };
    logger.info(data.invoice);
  }

  logger.info("");
}

// ---------------------------------------------------------------------------
// Connect (Stripe Onboarding)
// ---------------------------------------------------------------------------

export async function cliPaymentConnect(opts: PaymentConnectOptions): Promise<void> {
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

  const result = await apiRequest("/api/payments/connect", {
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

  const data = result.data as {
    accountId: string;
    onboardingUrl: string;
  };

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
