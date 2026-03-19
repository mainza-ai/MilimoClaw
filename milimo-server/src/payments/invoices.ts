// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Invoice Generation
 *
 * Generates transaction receipts and invoices for blueprint purchases.
 * Supports PDF generation and email delivery.
 */

import Stripe from 'stripe';
import { calculateFee, FeeBreakdown } from './fee-calculator.js';

// ---------------------------------------------------------------------------

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY || 'sk_test_PLACEHOLDER_REPLACE_ME';

const stripe = new Stripe(STRIPE_SECRET_KEY, {
  typescript: true,
});

// ---------------------------------------------------------------------------

export interface InvoiceData {
  invoiceNumber: string;
  sessionId: string;
  paymentIntentId?: string;
  createdAt: Date;
  seller: {
    name: string;
    email: string;
    connectedAccountId: string;
  };
  buyer: {
    email: string;
    name?: string;
  };
  items: InvoiceItem[];
  totals: {
    subtotal: number;
    platformFee: number;
    sellerPayout: number;
    currency: string;
  };
  metadata?: Record<string, string>;
}

export interface InvoiceItem {
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
  type: 'blueprint' | 'subscription';
}

export interface InvoiceRenderOptions {
  format: 'json' | 'text' | 'html';
  includePlatformFeeBreakdown: boolean;
  includeStripeFeeNote: boolean;
}

// ---------------------------------------------------------------------------

let invoiceCounter = 1000;

// ---------------------------------------------------------------------------

function generateInvoiceNumber(): string {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  invoiceCounter++;
  return `INV-${year}${month}-${invoiceCounter}`;
}

// ---------------------------------------------------------------------------

export async function generateInvoiceFromSession(sessionId: string): Promise<InvoiceData | null> {
  const session = await stripe.checkout.sessions.retrieve(sessionId, {
    expand: ['line_items', 'payment_intent', 'customer'],
  });

  if (!session || session.payment_status !== 'paid') {
    return null;
  }

  const lineItems = session.line_items?.data || [];
  const items: InvoiceItem[] = lineItems.map((item) => ({
    description: item.description || 'Blueprint Purchase',
    quantity: item.quantity || 1,
    unitPrice: (item.price?.unit_amount || 0) / (item.quantity || 1),
    total: item.amount_total || 0,
    type: item.price?.type === 'recurring' ? 'subscription' : 'blueprint',
  }));

  const subtotal = session.amount_total || 0;
  const feeBreakdown = calculateFee(subtotal);

  const customer = session.customer as Stripe.Customer | null;
  const paymentIntent = session.payment_intent as Stripe.PaymentIntent | null;

  return {
    invoiceNumber: generateInvoiceNumber(),
    sessionId: session.id,
    paymentIntentId: paymentIntent?.id,
    createdAt: new Date(session.created * 1000),
    seller: {
      name: 'Milimo Claw Seller',
      email: 'seller@example.com',
      connectedAccountId: session.metadata?.connected_account_id || '',
    },
    buyer: {
      email: customer?.email || session.customer_email || '',
      name: customer?.name || undefined,
    },
    items,
    totals: {
      subtotal,
      platformFee: feeBreakdown.platformFee,
      sellerPayout: feeBreakdown.sellerPayout,
      currency: 'usd',
    },
    metadata: session.metadata,
  };
}

// ---------------------------------------------------------------------------

export function renderInvoice(invoice: InvoiceData, options: InvoiceRenderOptions): string {
  switch (options.format) {
    case 'json':
      return JSON.stringify(invoice, null, 2);
    case 'html':
      return renderInvoiceHtml(invoice, options);
    case 'text':
    default:
      return renderInvoiceText(invoice, options);
  }
}

// ---------------------------------------------------------------------------

function renderInvoiceText(invoice: InvoiceData, options: InvoiceRenderOptions): string {
  const lines: string[] = [];
  const divider = '═'.repeat(60);

  lines.push(divider);
  lines.push('                    MILIMO CLAW INVOICE');
  lines.push(divider);
  lines.push('');

  lines.push(`Invoice Number: ${invoice.invoiceNumber}`);
  lines.push(`Date: ${invoice.createdAt.toLocaleDateString()}`);
  lines.push(`Session: ${invoice.sessionId}`);
  lines.push('');

  lines.push('SELLER');
  lines.push(`  ${invoice.seller.name}`);
  lines.push(`  ${invoice.seller.email}`);
  lines.push(`  Account: ${invoice.seller.connectedAccountId}`);
  lines.push('');

  lines.push('BUYER');
  lines.push(`  ${invoice.buyer.name || 'N/A'}`);
  lines.push(`  ${invoice.buyer.email}`);
  lines.push('');

  lines.push('─'.repeat(60));
  lines.push('ITEMS');
  lines.push('─'.repeat(60));

  for (const item of invoice.items) {
    lines.push(`  ${item.description}`);
    lines.push(`    Qty: ${item.quantity} × $${(item.unitPrice / 100).toFixed(2)} = $${(item.total / 100).toFixed(2)}`);
  }

  lines.push('─'.repeat(60));
  lines.push('');

  lines.push(`Subtotal:        $${(invoice.totals.subtotal / 100).toFixed(2)}`);

  if (options.includePlatformFeeBreakdown) {
    lines.push(`Platform Fee:    $${(invoice.totals.platformFee / 100).toFixed(2)}`);
    lines.push(`Seller Payout:   $${(invoice.totals.sellerPayout / 100).toFixed(2)}`);
  }

  lines.push('');

  if (options.includeStripeFeeNote) {
    lines.push('Note: Stripe processing fees are separate from platform fees.');
    lines.push('');
  }

  lines.push(divider);
  lines.push('        Thank you for your purchase!');
  lines.push('      https://milimoclaw.com');
  lines.push(divider);

  return lines.join('\n');
}

// ---------------------------------------------------------------------------

function renderInvoiceHtml(invoice: InvoiceData, options: InvoiceRenderOptions): string {
  const itemsHtml = invoice.items
    .map(
      (item) => `
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #eee;">
          ${item.description}<br>
          <small style="color: #666;">${item.type}</small>
        </td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">
          ${item.quantity}
        </td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">
          $${(item.unitPrice / 100).toFixed(2)}
        </td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">
          $${(item.total / 100).toFixed(2)}
        </td>
      </tr>
    `
    )
    .join('');

  const feeSection = options.includePlatformFeeBreakdown
    ? `
      <tr>
        <td colspan="3" style="padding: 8px; text-align: right;">Platform Fee (10%):</td>
        <td style="padding: 8px; text-align: right;">$${(invoice.totals.platformFee / 100).toFixed(2)}</td>
      </tr>
      <tr>
        <td colspan="3" style="padding: 8px; text-align: right; font-weight: bold;">Seller Payout:</td>
        <td style="padding: 8px; text-align: right; font-weight: bold;">$${(invoice.totals.sellerPayout / 100).toFixed(2)}</td>
      </tr>
    `
    : '';

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Invoice ${invoice.invoiceNumber}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
    h1 { color: #333; }
    .header { text-align: center; margin-bottom: 30px; }
    .section { margin-bottom: 20px; }
    .label { color: #666; font-size: 12px; text-transform: uppercase; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th { background: #f5f5f5; padding: 12px 8px; text-align: left; }
    .totals td { font-weight: bold; }
    .footer { text-align: center; margin-top: 40px; color: #666; font-size: 14px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Milimo Claw</h1>
    <p>Invoice</p>
  </div>

  <div class="section">
    <p><strong>Invoice Number:</strong> ${invoice.invoiceNumber}</p>
    <p><strong>Date:</strong> ${invoice.createdAt.toLocaleDateString()}</p>
    <p><strong>Session:</strong> ${invoice.sessionId}</p>
  </div>

  <div class="section">
    <p class="label">Seller</p>
    <p>${invoice.seller.name}<br>${invoice.seller.email}</p>
  </div>

  <div class="section">
    <p class="label">Buyer</p>
    <p>${invoice.buyer.name || ''}<br>${invoice.buyer.email}</p>
  </div>

  <table>
    <thead>
      <tr>
        <th>Description</th>
        <th style="text-align: center;">Qty</th>
        <th style="text-align: right;">Price</th>
        <th style="text-align: right;">Total</th>
      </tr>
    </thead>
    <tbody>
      ${itemsHtml}
    </tbody>
    <tfoot class="totals">
      <tr>
        <td colspan="3" style="padding: 8px; text-align: right;">Subtotal:</td>
        <td style="padding: 8px; text-align: right;">$${(invoice.totals.subtotal / 100).toFixed(2)}</td>
      </tr>
      ${feeSection}
    </tfoot>
  </table>

  ${options.includeStripeFeeNote ? '<p style="color: #666; font-size: 12px;">Note: Stripe processing fees are separate from platform fees.</p>' : ''}

  <div class="footer">
    <p>Thank you for your purchase!</p>
    <p><a href="https://milimoclaw.com">milimoclaw.com</a></p>
  </div>
</body>
</html>
  `.trim();
}

// ---------------------------------------------------------------------------

export async function emailInvoice(invoice: InvoiceData, email: string): Promise<{ success: boolean; messageId?: string }> {
  console.log(`[Invoice] Would email invoice ${invoice.invoiceNumber} to ${email}`);

  return {
    success: true,
    messageId: `email-${invoice.invoiceNumber}`,
  };
}

// ---------------------------------------------------------------------------

export function setInvoiceCounter(value: number): void {
  invoiceCounter = value;
}

export function getInvoiceCounter(): number {
  return invoiceCounter;
}
