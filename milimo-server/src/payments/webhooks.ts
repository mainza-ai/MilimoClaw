// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Stripe Webhook Handler
 *
 * Processes incoming webhooks from Stripe for payment events,
 * account updates, and payout notifications.
 */

import Stripe from 'stripe';
import { FastifyRequest, FastifyReply } from 'fastify';
import { handlePaymentSuccess, handleAccountRequirementsUpdated } from './stripe.js';
import { generateInvoiceFromSession, renderInvoice } from './invoices.js';

// ---------------------------------------------------------------------------

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY || 'sk_test_PLACEHOLDER_REPLACE_ME';
const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET || 'whsec_PLACEHOLDER_REPLACE_ME';

const stripe = new Stripe(STRIPE_SECRET_KEY, {
  typescript: true,
});

// ---------------------------------------------------------------------------

export interface WebhookHandlers {
  onPaymentSuccess?: (sessionId: string, metadata: Record<string, string>) => Promise<void>;
  onPaymentFailed?: (sessionId: string, metadata: Record<string, string>) => Promise<void>;
  onAccountUpdated?: (accountId: string, status: { onboardingComplete: boolean }) => Promise<void>;
  onPayoutCreated?: (payoutId: string, accountId: string, amount: number) => Promise<void>;
  onPayoutFailed?: (payoutId: string, accountId: string) => Promise<void>;
}

let webhookHandlers: WebhookHandlers = {};

// ---------------------------------------------------------------------------

export function setWebhookHandlers(handlers: WebhookHandlers): void {
  webhookHandlers = { ...webhookHandlers, ...handlers };
}

// ---------------------------------------------------------------------------

export async function handleWebhook(
  request: FastifyRequest<{ Body: string }>,
  reply: FastifyReply
): Promise<FastifyReply> {
  const signature = request.headers['stripe-signature'];

  if (!signature || typeof signature !== 'string') {
    return reply.code(400).send({ error: 'Missing stripe-signature header' });
  }

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(request.body, signature, STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    console.error('[Webhook] Signature verification failed:', err);
    return reply.code(400).send({ error: 'Webhook signature verification failed' });
  }

  console.log(`[Webhook] Received event: ${event.type} (${event.id})`);

  try {
    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutCompleted(event);
        break;

      case 'checkout.session.expired':
        await handleCheckoutExpired(event);
        break;

      case 'payment_intent.succeeded':
        await handlePaymentIntentSucceeded(event);
        break;

      case 'payment_intent.payment_failed':
        await handlePaymentIntentFailed(event);
        break;

      case 'payout.created':
        await handlePayoutCreated(event);
        break;

      case 'payout.failed':
        await handlePayoutFailed(event);
        break;

      case 'payout.paid':
        await handlePayoutPaid(event);
        break;

      case 'account.updated':
        await handleAccountUpdated(event);
        break;

      default:
        console.log(`[Webhook] Unhandled event type: ${event.type}`);
    }

    return reply.send({ received: true, eventId: event.id });
  } catch (err) {
    console.error(`[Webhook] Error processing ${event.type}:`, err);
    return reply.code(500).send({ error: 'Webhook processing failed' });
  }
}

// ---------------------------------------------------------------------------

async function handleCheckoutCompleted(event: Stripe.Event): Promise<void> {
  const session = event.data.object as Stripe.Checkout.Session;

  console.log(`[Webhook] Checkout completed: ${session.id}`);

  const metadata = session.metadata || {};

  if (webhookHandlers.onPaymentSuccess) {
    await webhookHandlers.onPaymentSuccess(session.id, metadata);
  }

  await handlePaymentSuccess(session.id);

  if (session.payment_status === 'paid') {
    const invoice = await generateInvoiceFromSession(session.id);
    if (invoice) {
      console.log(`[Webhook] Generated invoice: ${invoice.invoiceNumber}`);
    }
  }
}

// ---------------------------------------------------------------------------

async function handleCheckoutExpired(event: Stripe.Event): Promise<void> {
  const session = event.data.object as Stripe.Checkout.Session;

  console.log(`[Webhook] Checkout expired: ${session.id}`);

  const metadata = session.metadata || {};

  if (webhookHandlers.onPaymentFailed) {
    await webhookHandlers.onPaymentFailed(session.id, metadata);
  }
}

// ---------------------------------------------------------------------------

async function handlePaymentIntentSucceeded(event: Stripe.Event): Promise<void> {
  const paymentIntent = event.data.object as Stripe.PaymentIntent;

  console.log(`[Webhook] Payment intent succeeded: ${paymentIntent.id}`);
}

// ---------------------------------------------------------------------------

async function handlePaymentIntentFailed(event: Stripe.Event): Promise<void> {
  const paymentIntent = event.data.object as Stripe.PaymentIntent;

  console.log(`[Webhook] Payment intent failed: ${paymentIntent.id}`);
  console.log(`[Webhook] Failure message: ${paymentIntent.last_payment_error?.message}`);
}

// ---------------------------------------------------------------------------

async function handlePayoutCreated(event: Stripe.Event): Promise<void> {
  const payout = event.data.object as Stripe.Payout;

  console.log(`[Webhook] Payout created: ${payout.id}`);
  console.log(`[Webhook] Amount: $${(payout.amount / 100).toFixed(2)}`);

  if (webhookHandlers.onPayoutCreated) {
    await webhookHandlers.onPayoutCreated(payout.id, payout.id, payout.amount);
  }
}

// ---------------------------------------------------------------------------

async function handlePayoutFailed(event: Stripe.Event): Promise<void> {
  const payout = event.data.object as Stripe.Payout;

  console.log(`[Webhook] Payout failed: ${payout.id}`);
  console.log(`[Webhook] Failure message: ${payout.failure_message}`);

  if (webhookHandlers.onPayoutFailed) {
    await webhookHandlers.onPayoutFailed(payout.id, payout.id);
  }
}

// ---------------------------------------------------------------------------

async function handlePayoutPaid(event: Stripe.Event): Promise<void> {
  const payout = event.data.object as Stripe.Payout;

  console.log(`[Webhook] Payout completed: ${payout.id}`);
}

// ---------------------------------------------------------------------------

async function handleAccountUpdated(event: Stripe.Event): Promise<void> {
  const account = event.data.object as Stripe.Account;

  console.log(`[Webhook] Account updated: ${account.id}`);

  const onboardingComplete = account.details_submitted || false;

  if (webhookHandlers.onAccountUpdated) {
    await webhookHandlers.onAccountUpdated(account.id, { onboardingComplete });
  }

  await handleAccountRequirementsUpdated(account.id);
}

// ---------------------------------------------------------------------------

export async function handleV2ThinEvent(
  request: FastifyRequest<{ Body: string }>,
  reply: FastifyReply
): Promise<FastifyReply> {
  const signature = request.headers['stripe-signature'];

  if (!signature || typeof signature !== 'string') {
    return reply.code(400).send({ error: 'Missing stripe-signature header' });
  }

  let thinEvent: Stripe.V2.Event;

  try {
    thinEvent = stripe.v2.core.events.parseThinEvent(request.body, signature, STRIPE_WEBHOOK_SECRET);
  } catch (err) {
    console.error('[Webhook] Thin event parsing failed:', err);
    return reply.code(400).send({ error: 'Thin event parsing failed' });
  }

  console.log(`[Webhook] Received V2 thin event: ${thinEvent.type} (${thinEvent.id})`);

  return reply.send({ received: true, eventId: thinEvent.id });
}

// ---------------------------------------------------------------------------

export function createWebhookRoute(fastify: any): void {
  fastify.post('/webhooks/stripe', {
    config: {
      rawBody: true,
    },
  }, handleWebhook);

  fastify.post('/webhooks/stripe/v2', {
    config: {
      rawBody: true,
    },
  }, handleV2ThinEvent);
}
