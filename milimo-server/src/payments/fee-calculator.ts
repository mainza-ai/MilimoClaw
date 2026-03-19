// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Platform Fee Calculator
 *
 * Calculates platform fees, seller payouts, and provides detailed
 * fee breakdowns for the Blueprint Marketplace.
 */

// ---------------------------------------------------------------------------

export interface FeeConfig {
  platformFeePercent: number;
  minimumFeeCents: number;
  maximumFeeCents: number | null;
  stripeProcessingFeePercent: number;
  stripeFixedFeeCents: number;
}

export interface FeeBreakdown {
  grossAmount: number;
  platformFee: number;
  stripeProcessingFee: number;
  sellerPayout: number;
  effectivePlatformFeePercent: number;
  netSellerPercent: number;
}

export interface SubscriptionFeeBreakdown extends FeeBreakdown {
  monthlyAmount: number;
  annualAmount: number;
  platformFeeMonthly: number;
  platformFeeAnnual: number;
  sellerPayoutMonthly: number;
  sellerPayoutAnnual: number;
}

// ---------------------------------------------------------------------------

const DEFAULT_CONFIG: FeeConfig = {
  platformFeePercent: 0.10,
  minimumFeeCents: 50,
  maximumFeeCents: null,
  stripeProcessingFeePercent: 0.029,
  stripeFixedFeeCents: 30,
};

let currentConfig = DEFAULT_CONFIG;

// ---------------------------------------------------------------------------

export function setFeeConfig(config: Partial<FeeConfig>): void {
  currentConfig = { ...currentConfig, ...config };
}

export function getFeeConfig(): FeeConfig {
  return { ...currentConfig };
}

// ---------------------------------------------------------------------------

export function calculateFee(amountCents: number, config: FeeConfig = currentConfig): FeeBreakdown {
  let platformFee = Math.round(amountCents * config.platformFeePercent);

  if (platformFee < config.minimumFeeCents) {
    platformFee = config.minimumFeeCents;
  }

  if (config.maximumFeeCents !== null && platformFee > config.maximumFeeCents) {
    platformFee = config.maximumFeeCents;
  }

  const stripeProcessingFee = Math.round(amountCents * config.stripeProcessingFeePercent) + config.stripeFixedFeeCents;

  const sellerPayout = amountCents - platformFee;

  const effectivePlatformFeePercent = amountCents > 0 ? (platformFee / amountCents) * 100 : 0;

  const netSellerPercent = amountCents > 0 ? (sellerPayout / amountCents) * 100 : 0;

  return {
    grossAmount: amountCents,
    platformFee,
    stripeProcessingFee,
    sellerPayout,
    effectivePlatformFeePercent,
    netSellerPercent,
  };
}

// ---------------------------------------------------------------------------

export function calculateSubscriptionFee(monthlyAmountCents: number, config: FeeConfig = currentConfig): SubscriptionFeeBreakdown {
  const monthlyBreakdown = calculateFee(monthlyAmountCents, config);

  const annualAmount = monthlyAmountCents * 12;
  const annualBreakdown = calculateFee(annualAmount, config);

  return {
    grossAmount: monthlyAmountCents,
    platformFee: monthlyBreakdown.platformFee,
    stripeProcessingFee: monthlyBreakdown.stripeProcessingFee,
    sellerPayout: monthlyBreakdown.sellerPayout,
    effectivePlatformFeePercent: monthlyBreakdown.effectivePlatformFeePercent,
    netSellerPercent: monthlyBreakdown.netSellerPercent,
    monthlyAmount: monthlyAmountCents,
    annualAmount,
    platformFeeMonthly: monthlyBreakdown.platformFee,
    platformFeeAnnual: annualBreakdown.platformFee,
    sellerPayoutMonthly: monthlyBreakdown.sellerPayout,
    sellerPayoutAnnual: annualBreakdown.sellerPayout,
  };
}

// ---------------------------------------------------------------------------

export function formatFeeReport(breakdown: FeeBreakdown): string {
  const lines = [
    'Fee Breakdown Report',
    '==================',
    `Gross Amount: $${(breakdown.grossAmount / 100).toFixed(2)}`,
    `Platform Fee: $${(breakdown.platformFee / 100).toFixed(2)} (${breakdown.effectivePlatformFeePercent.toFixed(1)}%)`,
    `Stripe Processing: $${(breakdown.stripeProcessingFee / 100).toFixed(2)}`,
    `Seller Payout: $${(breakdown.sellerPayout / 100).toFixed(2)} (${breakdown.netSellerPercent.toFixed(1)}%)`,
    '==================',
  ];

  return lines.join('\n');
}

// ---------------------------------------------------------------------------

export function validateFeeAmount(amountCents: number): { valid: boolean; error?: string } {
  if (amountCents < 50) {
    return { valid: false, error: 'Minimum transaction amount is $0.50' };
  }

  if (amountCents > 99999999) {
    return { valid: false, error: 'Maximum transaction amount is $999,999.99' };
  }

  if (!Number.isInteger(amountCents)) {
    return { valid: false, error: 'Amount must be in cents (integer)' };
  }

  return { valid: true };
}

// ---------------------------------------------------------------------------

export function calculateBulkFees(amounts: number[]): {
  breakdowns: FeeBreakdown[];
  totals: {
    grossAmount: number;
    platformFees: number;
    sellerPayouts: number;
  };
} {
  const breakdowns = amounts.map((amount) => calculateFee(amount));

  const totals = {
    grossAmount: breakdowns.reduce((sum, b) => sum + b.grossAmount, 0),
    platformFees: breakdowns.reduce((sum, b) => sum + b.platformFee, 0),
    sellerPayouts: breakdowns.reduce((sum, b) => sum + b.sellerPayout, 0),
  };

  return { breakdowns, totals };
}

// ---------------------------------------------------------------------------

export function estimateAnnualRevenue(
  averageBlueprintPrice: number,
  estimatedMonthlySales: number,
  config: FeeConfig = currentConfig
): {
  monthly: { gross: number; platformFees: number };
  annual: { gross: number; platformFees: number };
} {
  const monthlyGross = averageBlueprintPrice * estimatedMonthlySales;
  const monthlyFees = calculateFee(monthlyGross, config);

  const annualGross = monthlyGross * 12;
  const annualFees = calculateFee(annualGross, config);

  return {
    monthly: {
      gross: monthlyGross,
      platformFees: monthlyFees.platformFee,
    },
    annual: {
      gross: annualGross,
      platformFees: annualFees.platformFee,
    },
  };
}

// ---------------------------------------------------------------------------

export {
  DEFAULT_CONFIG,
};
