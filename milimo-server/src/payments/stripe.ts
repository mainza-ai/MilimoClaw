// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Stripe Connect Integration
 *
 * Handles payment processing for the Blueprint Marketplace using Stripe Connect.
 * Supports connected accounts, platform fees, and automatic payouts.
 *
 * @see https://stripe.com/docs/connect
 */

import Stripe from 'stripe';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Stripe configuration
 * IMPORTANT: Replace placeholder values with actual keys from Stripe Dashboard
 */
const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY || 'sk_test_PLACEHOLDER_REPLACE_ME';
const STRIPE_PUBLISHABLE_KEY = process.env.STRIPE_PUBLISHABLE_KEY || 'pk_test_PLACEHOLDER_REPLACE_ME';
const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET || 'whsec_PLACEHOLDER_REPLACE_ME';

/**
 * Platform fee percentage (10%)
 */
const PLATFORM_FEE_PERCENT = 0.10;

/**
 * Product IDs from Stripe Dashboard
 * @see stripe/docs/PRODUCT_CATALOG.md
 */
const PRODUCT_IDS = {
  MILIMO_PRO_SUBSCRIPTION: 'prod_UAntVVODckBNuK',
  BLUEPRINT_ONE_TIME: 'prod_UAnpw3QcXpyA4K',
} as const;

// ---------------------------------------------------------------------------
// Error Handling
// ---------------------------------------------------------------------------

/**
 * Custom error for missing Stripe configuration
 */
class StripeConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'StripeConfigurationError';
  }
}

/**
 * Validate Stripe configuration before use
 * @throws StripeConfigurationError if keys are placeholders
 */
function validateStripeConfig(): void {
  if (STRIPE_SECRET_KEY.includes('PLACEHOLDER')) {
    throw new StripeConfigurationError(
      'Stripe secret key not configured. Set STRIPE_SECRET_KEY environment variable.'
    );
  }
  if (STRIPE_WEBHOOK_SECRET.includes('PLACEHOLDER')) {
    throw new StripeConfigurationError(
      'Stripe webhook secret not configured. Set STRIPE_WEBHOOK_SECRET environment variable.'
    );
  }
}

// ---------------------------------------------------------------------------
// Stripe Client
// ---------------------------------------------------------------------------

/**
 * Stripe client instance
 * Uses latest API version automatically (2026-02-25.clover)
 */
const stripe = new Stripe(STRIPE_SECRET_KEY, {
  // API version is set automatically by SDK
  typescript: true,
});

// ---------------------------------------------------------------------------
// Connected Account Management
// ---------------------------------------------------------------------------

interface CreateConnectedAccountParams {
  displayName: string;
  contactEmail: string;
  country?: string;
}

interface ConnectedAccountResult {
  accountId: string;
  onboardingUrl?: string;
}

/**
 * Create a connected account for a blueprint seller
 *
 * Uses V2 API with Express dashboard for simplified onboarding.
 * Platform is responsible for pricing and fee collection.
 *
 * @param params - Account creation parameters
 * @returns Connected account ID and optional onboarding URL
 *
 * @example
 * const result = await createConnectedAccount({
 *   displayName: 'My Blueprint Shop',
 *   contactEmail: 'seller@example.com',
 * });
 */
async function createConnectedAccount(
  params: CreateConnectedAccountParams
): Promise<ConnectedAccountResult> {
  validateStripeConfig();

  const { displayName, contactEmail, country = 'us' } = params;

  const account = await stripe.accounts.create({
    type: 'express',
    country: country.toUpperCase(),
    email: contactEmail,
    business_profile: {
      name: displayName,
    },
    capabilities: {
      card_payments: { requested: true },
      transfers: { requested: true },
    },
    settings: {
      payouts: {
        schedule: {
          interval: 'manual',
        },
      },
    },
    tos_acceptance: {
      service_agreement: 'recipient',
    },
  });

  return {
    accountId: account.id,
  };
}

/**
 * Create an account link for onboarding
 *
 * Generates a URL for the seller to complete Stripe onboarding.
 *
 * @param accountId - Connected account ID
 * @param refreshUrl - URL to redirect if onboarding is interrupted
 * @param returnUrl - URL to redirect after onboarding completes
 * @returns Onboarding URL
 */
async function createAccountLink(
  accountId: string,
  refreshUrl: string,
  returnUrl: string
): Promise<string> {
  validateStripeConfig();

  const accountLink = await stripe.accountLinks.create({
    account: accountId,
    refresh_url: refreshUrl,
    return_url: returnUrl,
    type: 'account_onboarding',
  });

  return accountLink.url;
}

/**
 * Get connected account status
 *
 * Retrieves onboarding status from Stripe API directly (not stored in DB).
 *
 * @param accountId - Connected account ID
 * @returns Account status information
 */
async function getAccountStatus(accountId: string): Promise<{
  onboardingComplete: boolean;
  readyToReceivePayments: boolean;
  requirementsStatus?: string;
}> {
  validateStripeConfig();

  const account = await stripe.accounts.retrieve(accountId);

  const readyToReceivePayments = account.capabilities?.transfers === 'active';
  const chargesEnabled = account.charges_enabled;
  const detailsSubmitted = account.details_submitted;
  const requirementsStatus = account.requirements?.disabled_reason ?? undefined;
  const onboardingComplete = detailsSubmitted && chargesEnabled;

  return {
    onboardingComplete,
    readyToReceivePayments,
    requirementsStatus,
  };
}

// ---------------------------------------------------------------------------
// Product Management
// ---------------------------------------------------------------------------

interface CreateProductParams {
  name: string;
  description: string;
  priceInCents: number;
  currency?: string;
  connectedAccountId: string;
}

interface ProductResult {
  productId: string;
  priceId: string;
}

/**
 * Create a product for a blueprint listing
 *
 * Creates product at platform level (not on connected account).
 * Stores mapping to connected account in metadata.
 *
 * @param params - Product creation parameters
 * @returns Product and price IDs
 */
async function createProduct(params: CreateProductParams): Promise<ProductResult> {
  validateStripeConfig();

  const { name, description, priceInCents, currency = 'usd', connectedAccountId } = params;

  const product = await stripe.products.create({
    name,
    description,
    default_price_data: {
      unit_amount: priceInCents,
      currency,
    },
    // Store connected account mapping in metadata
    metadata: {
      connected_account_id: connectedAccountId,
      platform: 'milimo-claw',
    },
  });

  const priceId = product.default_price as string;

  return {
    productId: product.id,
    priceId,
  };
}

/**
 * List all products with their connected accounts
 *
 * @returns List of products with seller information
 */
async function listProducts(): Promise<
  Array<{
    id: string;
    name: string;
    description: string;
    price: number;
    connectedAccountId: string;
  }>
> {
  validateStripeConfig();

  const products = await stripe.products.list({
    active: true,
    expand: ['data.default_price'],
  });

  return products.data.map((product) => ({
    id: product.id,
    name: product.name,
    description: product.description || '',
    price: (product.default_price as Stripe.Price)?.unit_amount || 0,
    connectedAccountId: product.metadata?.connected_account_id || '',
  }));
}

// ---------------------------------------------------------------------------
// Payment Processing
// ---------------------------------------------------------------------------

interface CreateCheckoutSessionParams {
  priceId: string;
  connectedAccountId: string;
  quantity?: number;
  successUrl: string;
  cancelUrl: string;
}

interface CheckoutSessionResult {
  sessionId: string;
  url: string;
}

/**
 * Create a checkout session for blueprint purchase
 *
 * Uses destination charge with application fee (10% platform fee).
 *
 * @param params - Checkout parameters
 * @returns Checkout session URL
 */
async function createCheckoutSession(
  params: CreateCheckoutSessionParams
): Promise<CheckoutSessionResult> {
  validateStripeConfig();

  const { priceId, connectedAccountId, quantity = 1, successUrl, cancelUrl } = params;

  // Get price to calculate platform fee
  const price = await stripe.prices.retrieve(priceId);
  const amount = price.unit_amount || 0;
  const platformFee = Math.round(amount * PLATFORM_FEE_PERCENT);

  const session = await stripe.checkout.sessions.create({
    line_items: [
      {
        price: priceId,
        quantity,
      },
    ],
    mode: 'payment',
    payment_intent_data: {
      application_fee_amount: platformFee,
      transfer_data: {
        destination: connectedAccountId,
      },
    },
    success_url: successUrl,
    cancel_url: cancelUrl,
    // Store metadata for webhook processing
    metadata: {
      connected_account_id: connectedAccountId,
      platform_fee_amount: platformFee.toString(),
    },
  });

  return {
    sessionId: session.id,
    url: session.url || '',
  };
}

/**
 * Retrieve checkout session after payment
 *
 * @param sessionId - Checkout session ID
 * @returns Session details including payment status
 */
async function getCheckoutSession(sessionId: string): Promise<{
  paymentStatus: string;
  customerId?: string;
  amountTotal: number;
  connectedAccountId?: string;
}> {
  validateStripeConfig();

  const session = await stripe.checkout.sessions.retrieve(sessionId, {
    expand: ['payment_intent'],
  });

  return {
    paymentStatus: session.payment_status,
    customerId: session.customer as string | undefined,
    amountTotal: session.amount_total || 0,
    connectedAccountId: session.metadata?.connected_account_id,
  };
}

// ---------------------------------------------------------------------------
// Fee Calculation
// ---------------------------------------------------------------------------

interface FeeBreakdown {
  priceInCents: number;
  platformFee: number;
  sellerPayout: number;
  platformFeePercent: number;
}

/**
 * Calculate platform fee and seller payout
 *
 * @param priceInCents - Total price in cents
 * @returns Fee breakdown
 */
function calculateFees(priceInCents: number): FeeBreakdown {
  const platformFee = Math.round(priceInCents * PLATFORM_FEE_PERCENT);
  const sellerPayout = priceInCents - platformFee;

  return {
    priceInCents,
    platformFee,
    sellerPayout,
    platformFeePercent: PLATFORM_FEE_PERCENT * 100,
  };
}

// ---------------------------------------------------------------------------
// Webhook Handling
// ---------------------------------------------------------------------------

interface WebhookEvent {
  id: string;
  type: string;
  data: unknown;
}

/**
 * Parse and verify a Stripe webhook event
 *
 * @param payload - Raw request body
 * @param signature - Stripe-Signature header
 * @returns Parsed event or null if invalid
 */
function parseWebhookEvent(payload: string | Buffer, signature: string): WebhookEvent | null {
  try {
    const event = stripe.webhooks.constructEvent(payload, signature, STRIPE_WEBHOOK_SECRET);
    return {
      id: event.id,
      type: event.type,
      data: event.data,
    };
  } catch (err) {
    console.error('Webhook signature verification failed:', err);
    return null;
  }
}

/**
 * Parse a thin event for V2 account webhooks
 *
 * @param payload - Raw request body
 * @param signature - Stripe-Signature header
 * @returns Thin event or null if invalid
 */
function parseThinEvent(payload: string | Buffer, signature: string): Stripe.ThinEvent | null {
  try {
    const thinEvent = stripe.parseThinEvent(payload, signature, STRIPE_WEBHOOK_SECRET);
    return thinEvent;
  } catch (err) {
    console.error('Thin event parsing failed:', err);
    return null;
  }
}

/**
 * Handle account requirement changes (V2 webhook)
 *
 * @param accountId - Connected account ID
 */
async function handleAccountRequirementsUpdated(accountId: string): Promise<void> {
  console.log(`Account requirements updated: ${accountId}`);
  // Fetch latest account status
  const status = await getAccountStatus(accountId);
  console.log('Account status:', status);

  // In production, update local database with status
  // and notify seller if additional information needed
}

/**
 * Handle successful payment
 *
 * @param sessionId - Checkout session ID
 */
async function handlePaymentSuccess(sessionId: string): Promise<void> {
  const session = await getCheckoutSession(sessionId);
  console.log(`Payment successful: ${sessionId}`);
  console.log('Amount:', session.amountTotal);
  console.log('Connected account:', session.connectedAccountId);

  // In production:
  // 1. Update order status in database
  // 2. Grant buyer access to blueprint
  // 3. Send confirmation email
  // 4. Update seller analytics
}

// ---------------------------------------------------------------------------
// Invoice Generation
// ---------------------------------------------------------------------------

interface InvoiceData {
  sessionId: string;
  buyerEmail: string;
  productName: string;
  amount: number;
  platformFee: number;
  sellerPayout: number;
  purchaseDate: Date;
}

/**
 * Generate invoice data for a purchase
 *
 * @param sessionId - Checkout session ID
 * @returns Invoice data for rendering
 */
async function generateInvoice(sessionId: string): Promise<InvoiceData | null> {
  validateStripeConfig();

  const session = await stripe.checkout.sessions.retrieve(sessionId, {
    expand: ['line_items', 'customer'],
  });

  if (!session) {
    return null;
  }

  const lineItems = session.line_items?.data || [];
  const firstItem = lineItems[0];

  const amount = session.amount_total || 0;
  const fees = calculateFees(amount);

  return {
    sessionId,
    buyerEmail: (session.customer as Stripe.Customer)?.email || session.customer_email || '',
    productName: firstItem?.description || 'Blueprint',
    amount,
    platformFee: fees.platformFee,
    sellerPayout: fees.sellerPayout,
    purchaseDate: new Date(session.created * 1000),
  };
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export {
  // Configuration
  STRIPE_PUBLISHABLE_KEY,
  PLATFORM_FEE_PERCENT,
  PRODUCT_IDS,
  // Errors
  StripeConfigurationError,
  validateStripeConfig,
  // Account Management
  createConnectedAccount,
  createAccountLink,
  getAccountStatus,
  // Product Management
  createProduct,
  listProducts,
  // Payment Processing
  createCheckoutSession,
  getCheckoutSession,
  // Fee Calculation
  calculateFees,
  // Webhook Handling
  parseWebhookEvent,
  parseThinEvent,
  handleAccountRequirementsUpdated,
  handlePaymentSuccess,
  // Invoice
  generateInvoice,
  // Stripe Client
  stripe,
};

export type {
  CreateConnectedAccountParams,
  ConnectedAccountResult,
  CreateProductParams,
  ProductResult,
  CreateCheckoutSessionParams,
  CheckoutSessionResult,
  FeeBreakdown,
  WebhookEvent,
  InvoiceData,
};
