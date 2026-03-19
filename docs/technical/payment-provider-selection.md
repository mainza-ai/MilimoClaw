# Payment Provider Selection

**Version:** 1.0
**Date:** March 18, 2026
**Decision:** Stripe Connect

---

## Decision Summary

Milimo Claw will use **Stripe Connect** for payment processing in the Blueprint Marketplace.

---

## Evaluation Criteria

| Criteria | Weight | Stripe | PayPal | Crypto |
|----------|--------|--------|--------|--------|
| Marketplace support | 30% | ✅ Excellent | ⚠️ Good | ❌ Limited |
| Platform fees | 25% | ✅ Native | ⚠️ Manual | ⚠️ Manual |
| Payout automation | 20% | ✅ Automatic | ✅ Automatic | ❌ Manual |
| Developer experience | 15% | ✅ Excellent | ⚠️ Good | ⚠️ Complex |
| Global availability | 10% | ✅ 46 countries | ✅ 200+ countries | ✅ Global |

---

## Selected Provider: Stripe Connect

### Why Stripe Connect

1. **Built for Marketplaces**: Native support for platform fees, connected accounts, and split payments
2. **V2 API**: Modern API with improved account management
3. **Express Dashboard**: Simplified onboarding for blueprint sellers
4. **Automatic Payouts**: Sellers receive payouts automatically
5. **Webhook Integration**: Real-time payment events for audit trail
6. **Comprehensive Testing**: Full sandbox environment with test cards

### Stripe Connect Features Used

| Feature | Purpose |
|---------|---------|
| Connected Accounts | Each seller gets a Stripe account |
| Account Links | Onboarding flow for sellers |
| Destination Charges | Payment splits to seller + platform |
| Application Fees | 10% platform fee per transaction |
| Checkout Sessions | Hosted payment flow |
| Webhooks | Payment event notifications |

---

## Product Catalog

### Subscriptions

**Milimo Claw Pro** - $12/month
- Product ID: `prod_UAntVVODckBNuK`
- Full platform access for squad
- Unlimited auto-approvals
- Blueprint Marketplace access
- War Room dashboard
- Finals Mode support

### One-Time Purchases

**Milimo Claw Blueprint** - $25.00
- Product ID: `prod_UAnpw3QcXpyA4K`
- Community-built AI agent configuration
- Evolved from real operational data
- Includes content strategies, communication patterns, pricing calibration

---

## Fee Structure

| Item | Amount | Recipient |
|------|--------|-----------|
| Blueprint Price | $25.00 | - |
| Platform Fee (10%) | $2.50 | Milimo Claw |
| Seller Payout | $22.50 | Blueprint Creator |

### Calculation

```typescript
const PLATFORM_FEE_PERCENT = 0.10; // 10%

function calculateFees(priceInCents: number): {
  platformFee: number;
  sellerPayout: number;
} {
  const platformFee = Math.round(priceInCents * PLATFORM_FEE_PERCENT);
  const sellerPayout = priceInCents - platformFee;
  return { platformFee, sellerPayout };
}
```

---

## Integration Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Milimo Claw Platform                          │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Blueprint   │    │  Payment     │    │  Webhook     │       │
│  │  Marketplace │───▶│  Service     │◀───│  Handler     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                              │                                    │
│                              ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Stripe Connect                         │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │   │
│  │  │ Platform   │  │ Connected  │  │ Checkout   │         │   │
│  │  │ Account    │  │ Accounts   │  │ Sessions   │         │   │
│  │  └────────────┘  └────────────┘  └────────────┘         │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### API Key Management

- **Publishable Key**: Safe for frontend (test: `pk_test_51TCRy0...`)
- **Secret Key**: Server-side only (test: `sk_test_51TCRy0...`)
- **Webhook Secret**: Verify webhook signatures

### PCI Compliance

Stripe handles PCI compliance. Milimo Claw:
- Never stores credit card numbers
- Uses Stripe-hosted Checkout
- Processes via Stripe SDK

### Fraud Prevention

- Stripe Radar for fraud detection
- 3D Secure for European cards
- Address verification (AVS)

---

## Testing

### Test Cards

| Card Number | Result |
|-------------|--------|
| `4242424242424242` | Success |
| `4000000000000002` | Decline |
| `4000002500003155` | 3D Secure |

### Test Clock

Use Stripe test clocks for subscription testing:
- Simulate time passage
- Test renewal flows
- Verify invoice generation

### Webhook Testing

```bash
stripe listen --thin-events 'v2.core.account[requirements].updated' \
  --forward-thin-to http://localhost:3000/webhooks/stripe
```

---

## References

- [Stripe Connect Documentation](https://stripe.com/docs/connect)
- [V2 Accounts API](https://docs.stripe.com/api/v2/core/accounts)
- [Destination Charges](https://stripe.com/docs/connect/destination-charges)
- [Webhook Best Practices](https://stripe.com/docs/webhooks/best-practices)
