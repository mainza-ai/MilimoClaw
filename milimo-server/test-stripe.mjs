#!/usr/bin/env node
// Stripe Integration Test
// Tests the Milimo Claw payment integration with Stripe sandbox

import Stripe from 'stripe';
import dotenv from 'dotenv';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment
dotenv.config({ path: join(__dirname, '.env') });

const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY;

if (!STRIPE_SECRET_KEY || STRIPE_SECRET_KEY.includes('PLACEHOLDER')) {
  console.error('❌ STRIPE_SECRET_KEY not configured in .env');
  process.exit(1);
}

const stripe = new Stripe(STRIPE_SECRET_KEY);

console.log('');
console.log('┌─────────────────────────────────────────────────────┐');
console.log('│        Stripe Integration Test Suite               │');
console.log('└─────────────────────────────────────────────────────┘');
console.log('');

async function runTests() {
  const results = [];
  let testCustomer = null;
  let connectedAccount = null;
  let testProduct = null;

  // Test 1: Verify API Key
  console.log('Test 1: Verify Stripe API Key...');
  try {
    const balance = await stripe.balance.retrieve();
    console.log(`  ✅ API key valid`);
    console.log(`  Available: ${balance.available[0]?.amount || 0} ${balance.available[0]?.currency || 'usd'}`);
    results.push({ test: 'API Key', passed: true });
  } catch (err) {
    console.log(`  ❌ API key invalid: ${err.message}`);
    results.push({ test: 'API Key', passed: false, error: err.message });
  }

  // Test 2: List Products
  console.log('');
  console.log('Test 2: List Products...');
  try {
    const products = await stripe.products.list({ limit: 10 });
    console.log(`  ✅ Found ${products.data.length} products`);

    for (const product of products.data) {
      const price = product.default_price;
      let priceStr = 'no price';
      if (price && typeof price === 'object' && price.unit_amount) {
        priceStr = `$${(price.unit_amount / 100).toFixed(2)}`;
      }
      console.log(`     - ${product.name} (${product.id}): ${priceStr}`);
    }
    results.push({ test: 'List Products', passed: true });
  } catch (err) {
    console.log(`  ❌ Failed: ${err.message}`);
    results.push({ test: 'List Products', passed: false, error: err.message });
  }

  // Test 3: Create Test Customer
  console.log('');
  console.log('Test 3: Create Test Customer...');
  try {
    testCustomer = await stripe.customers.create({
      email: 'testaccount@example.com',
      name: 'Test Account',
      metadata: {
        test: 'true',
        created_by: 'milimo-test-suite'
      }
    });
    console.log(`  ✅ Customer created: ${testCustomer.id}`);
    console.log(`     Email: ${testCustomer.email}`);
    results.push({ test: 'Create Customer', passed: true });
  } catch (err) {
    console.log(`  ❌ Failed: ${err.message}`);
    results.push({ test: 'Create Customer', passed: false, error: err.message });
  }

  // Test 4: Create Connected Account (Express)
  console.log('');
  console.log('Test 4: Create Connected Account...');
  try {
    connectedAccount = await stripe.accounts.create({
      type: 'express',
      email: 'testaccount@example.com',
      metadata: {
        test: 'true',
        created_by: 'milimo-test-suite'
      }
    });
    console.log(`  ✅ Connected account created: ${connectedAccount.id}`);
    console.log(`     Type: ${connectedAccount.type}`);
    console.log(`     Details submitted: ${connectedAccount.details_submitted}`);
    results.push({ test: 'Create Connected Account', passed: true });
  } catch (err) {
    console.log(`  ❌ Failed: ${err.message}`);
    results.push({ test: 'Create Connected Account', passed: false, error: err.message });
  }

  // Test 5: Create Account Link (for onboarding)
  if (connectedAccount) {
    console.log('');
    console.log('Test 5: Create Account Link...');
    try {
      const accountLink = await stripe.accountLinks.create({
        account: connectedAccount.id,
        refresh_url: 'http://localhost:3001/stripe/refresh',
        return_url: 'http://localhost:3001/stripe/return',
        type: 'account_onboarding',
      });
      console.log(`  ✅ Account link created`);
      console.log(`     URL: ${accountLink.url.substring(0, 50)}...`);
      results.push({ test: 'Create Account Link', passed: true });
    } catch (err) {
      console.log(`  ❌ Failed: ${err.message}`);
      results.push({ test: 'Create Account Link', passed: false, error: err.message });
    }
  }

  // Test 6: Create Test Product
  console.log('');
  console.log('Test 6: Create Test Product...');
  try {
    testProduct = await stripe.products.create({
      name: 'Test Blueprint',
      description: 'A test blueprint for integration testing',
      metadata: {
        test: 'true',
        created_by: 'milimo-test-suite'
      },
      default_price_data: {
        unit_amount: 2500, // $25.00
        currency: 'usd',
      }
    });
    console.log(`  ✅ Product created: ${testProduct.id}`);
    console.log(`     Name: ${testProduct.name}`);
    const priceAmount = testProduct.default_price_data?.unit_amount || 0;
    console.log(`     Price: $${priceAmount / 100}`);
    results.push({ test: 'Create Product', passed: true });
  } catch (err) {
    console.log(`  ❌ Failed: ${err.message}`);
    results.push({ test: 'Create Product', passed: false, error: err.message });
  }

  // Test 7: Create Checkout Session
  if (testProduct && connectedAccount) {
    console.log('');
    console.log('Test 7: Create Checkout Session...');
    try {
      const priceId = testProduct.default_price;
      const platformFee = Math.round(2500 * 0.10); // 10% fee

      const session = await stripe.checkout.sessions.create({
        payment_method_types: ['card'],
        line_items: [{
          price: priceId,
          quantity: 1,
        }],
        mode: 'payment',
        success_url: 'http://localhost:3001/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: 'http://localhost:3001/cancel',
        payment_intent_data: {
          application_fee_amount: platformFee,
          transfer_data: {
            destination: connectedAccount.id,
          },
        },
        metadata: {
          test: 'true',
          connected_account_id: connectedAccount.id,
        }
      });
      console.log(`  ✅ Checkout session created: ${session.id}`);
      console.log(`     URL: ${session.url?.substring(0, 50)}...`);
      console.log(`     Platform fee: $${platformFee / 100}`);
      results.push({ test: 'Create Checkout Session', passed: true });
    } catch (err) {
      console.log(`  ❌ Failed: ${err.message}`);
      results.push({ test: 'Create Checkout Session', passed: false, error: err.message });
    }
  }

  // Test 8: Retrieve Balance for Connected Account
  if (connectedAccount) {
    console.log('');
    console.log('Test 8: Connected Account Balance...');
    try {
      const accountBalance = await stripe.balance.retrieve({
        stripeAccount: connectedAccount.id
      });
      console.log(`  ✅ Balance retrieved`);
      console.log(`     Available: ${accountBalance.available[0]?.amount || 0} ${accountBalance.available[0]?.currency || 'usd'}`);
      console.log(`     Pending: ${accountBalance.pending[0]?.amount || 0} ${accountBalance.pending[0]?.currency || 'usd'}`);
      results.push({ test: 'Connected Account Balance', passed: true });
    } catch (err) {
      console.log(`  ❌ Failed: ${err.message}`);
      results.push({ test: 'Connected Account Balance', passed: false, error: err.message });
    }
  }

  // Cleanup: Delete test resources
  console.log('');
  console.log('Cleaning up test resources...');
  try {
    if (testCustomer) await stripe.customers.del(testCustomer.id);
    if (testProduct) await stripe.products.update(testProduct.id, { active: false });
    console.log('  ✅ Test resources cleaned up');
  } catch (err) {
    console.log(`  ⚠️ Cleanup warning: ${err.message}`);
  }

  // Summary
  console.log('');
  console.log('┌─────────────────────────────────────────────────────┐');
  console.log('│                    Test Summary                     │');
  console.log('└─────────────────────────────────────────────────────┘');

  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;

  console.log('');
  console.log(`Total: ${results.length} tests`);
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log('');

  if (failed > 0) {
    console.log('Failed tests:');
    results.filter(r => !r.passed).forEach(r => {
      console.log(`  - ${r.test}: ${r.error}`);
    });
  }

  return failed === 0;
}

runTests()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(err => {
    console.error('Test suite error:', err);
    process.exit(1);
  });
