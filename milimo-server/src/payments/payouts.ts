// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Seller Payout Processing
 *
 * Handles payouts to connected accounts for blueprint sales.
 * Manages payout scheduling, minimum thresholds, and payout history.
 */

import Stripe from 'stripe';
import { calculateFee, FeeBreakdown, getFeeConfig } from './fee-calculator.js';

// ---------------------------------------------------------------------------

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY || 'sk_test_PLACEHOLDER_REPLACE_ME';

const stripe = new Stripe(STRIPE_SECRET_KEY, {
  typescript: true,
});

// ---------------------------------------------------------------------------

export interface PayoutConfig {
  minimumPayoutAmountCents: number;
  payoutScheduleDays: number[];
  retentionDays: number;
}

export interface PayoutRecord {
  id: string;
  connectedAccountId: string;
  amountCents: number;
  status: 'pending' | 'in_transit' | 'paid' | 'failed' | 'canceled';
  createdAt: Date;
  estimatedArrival?: Date;
  transactions: string[];
}

export interface SellerBalance {
  connectedAccountId: string;
  availableBalanceCents: number;
  pendingBalanceCents: number;
  totalEarnedCents: number;
  totalPaidOutCents: number;
  nextPayoutDate?: Date;
  nextPayoutAmountCents?: number;
}

// ---------------------------------------------------------------------------

const DEFAULT_PAYOUT_CONFIG: PayoutConfig = {
  minimumPayoutAmountCents: 1000,
  payoutScheduleDays: [1, 15],
  retentionDays: 7,
};

let payoutConfig = DEFAULT_PAYOUT_CONFIG;

// ---------------------------------------------------------------------------

export function setPayoutConfig(config: Partial<PayoutConfig>): void {
  payoutConfig = { ...payoutConfig, ...config };
}

export function getPayoutConfig(): PayoutConfig {
  return { ...payoutConfig };
}

// ---------------------------------------------------------------------------

export async function getSellerBalance(connectedAccountId: string): Promise<SellerBalance> {
  const balance = await stripe.balance.retrieve({
    stripeAccount: connectedAccountId,
  });

  const available = balance.available.find((b) => b.currency === 'usd')?.amount || 0;
  const pending = balance.pending.find((b) => b.currency === 'usd')?.amount || 0;

  return {
    connectedAccountId,
    availableBalanceCents: available,
    pendingBalanceCents: pending,
    totalEarnedCents: available + pending,
    totalPaidOutCents: 0,
    nextPayoutDate: calculateNextPayoutDate(),
    nextPayoutAmountCents: available >= payoutConfig.minimumPayoutAmountCents ? available : 0,
  };
}

// ---------------------------------------------------------------------------

export function calculateNextPayoutDate(): Date {
  const now = new Date();
  const currentDay = now.getDate();

  const sortedDays = [...payoutConfig.payoutScheduleDays].sort((a, b) => a - b);

  for (const day of sortedDays) {
    if (day > currentDay) {
      return new Date(now.getFullYear(), now.getMonth(), day);
    }
  }

  return new Date(now.getFullYear(), now.getMonth() + 1, sortedDays[0]);
}

// ---------------------------------------------------------------------------

export async function createPayout(
  connectedAccountId: string,
  amountCents?: number
): Promise<PayoutRecord> {
  const balance = await getSellerBalance(connectedAccountId);

  const payoutAmount = amountCents || balance.availableBalanceCents;

  if (payoutAmount < payoutConfig.minimumPayoutAmountCents) {
    throw new Error(
      `Payout amount ${payoutAmount} cents is below minimum threshold of ${payoutConfig.minimumPayoutAmountCents} cents`
    );
  }

  if (payoutAmount > balance.availableBalanceCents) {
    throw new Error(
      `Payout amount ${payoutAmount} cents exceeds available balance ${balance.availableBalanceCents} cents`
    );
  }

  const payout = await stripe.payouts.create(
    {
      amount: payoutAmount,
      currency: 'usd',
    },
    {
      stripeAccount: connectedAccountId,
    }
  );

  return {
    id: payout.id,
    connectedAccountId,
    amountCents: payoutAmount,
    status: payout.status as PayoutRecord['status'],
    createdAt: new Date(),
    estimatedArrival: payout.arrival_date ? new Date(payout.arrival_date * 1000) : undefined,
    transactions: [],
  };
}

// ---------------------------------------------------------------------------

export async function getPayoutHistory(
  connectedAccountId: string,
  limit: number = 10
): Promise<PayoutRecord[]> {
  const payouts = await stripe.payouts.list(
    {
      limit,
    },
    {
      stripeAccount: connectedAccountId,
    }
  );

  return payouts.data.map((payout) => ({
    id: payout.id,
    connectedAccountId,
    amountCents: payout.amount,
    status: payout.status as PayoutRecord['status'],
    createdAt: new Date(payout.created * 1000),
    estimatedArrival: payout.arrival_date ? new Date(payout.arrival_date * 1000) : undefined,
    transactions: [],
  }));
}

// ---------------------------------------------------------------------------

export async function processScheduledPayouts(): Promise<{
  processed: number;
  skipped: number;
  failed: number;
  payouts: PayoutRecord[];
}> {
  const today = new Date().getDate();

  if (!payoutConfig.payoutScheduleDays.includes(today)) {
    return {
      processed: 0,
      skipped: 0,
      failed: 0,
      payouts: [],
    };
  }

  return {
    processed: 0,
    skipped: 0,
    failed: 0,
    payouts: [],
  };
}

// ---------------------------------------------------------------------------

export function shouldProcessPayout(balance: SellerBalance): boolean {
  return balance.availableBalanceCents >= payoutConfig.minimumPayoutAmountCents;
}

// ---------------------------------------------------------------------------

export function formatPayoutSchedule(): string {
  const days = payoutConfig.payoutScheduleDays
    .map((d) => {
      const suffix = d === 1 || d === 21 || d === 31 ? 'st' : d === 2 || d === 22 ? 'nd' : d === 3 || d === 23 ? 'rd' : 'th';
      return `${d}${suffix}`;
    })
    .join(' and ');

  return `Payouts are processed on the ${days} of each month. ` +
    `Minimum payout: $${(payoutConfig.minimumPayoutAmountCents / 100).toFixed(2)}. ` +
    `${payoutConfig.retentionDays} day retention for new sales.`;
}

// ---------------------------------------------------------------------------

export {
  DEFAULT_PAYOUT_CONFIG,
};
