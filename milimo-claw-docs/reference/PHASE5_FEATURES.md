# Phase 5: Blueprint Economy Features

**Status:** Complete
**Date:** March 2026

---

## Overview

Phase 5 implements a production-ready marketplace with real payment processing, cryptographic provenance verification, and performance attestations for blueprints.

---

## 5.1 Payment Integration

### Stripe Connect Integration

The marketplace uses Stripe Connect for payment processing with the following architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    PAYMENT FLOW                              │
│                                                              │
│  Buyer ──► Checkout Session ──► Stripe ──► Webhook         │
│              │                    │           │              │
│              │                    ▼           │              │
│              │            ┌─────────────┐    │              │
│              │            │ Connected   │    │              │
│              │            │ Account     │◄───┘              │
│              │            │ (Seller)    │                    │
│              │            └─────────────┘                    │
│              │                    │                          │
│              ▼                    ▼                          │
│        ┌─────────────┐     ┌─────────────┐                  │
│        │ Platform    │     │ Payout      │                  │
│        │ Fee (10%)   │     │ (90%)       │                  │
│        └─────────────┘     └─────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| Connected Accounts | Sellers link Stripe accounts via Express onboarding |
| Checkout Sessions | Hosted payment pages with platform fees |
| Platform Fees | 10% automatic deduction via `application_fee_amount` |
| Payouts | Scheduled payouts on 1st and 15th of each month |
| Invoices | PDF/HTML/JSON invoice generation |
| Webhooks | Real-time payment event handling |

### CLI Commands

```bash
# Payment operations
openclaw milimo payment checkout --blueprint <id>
openclaw milimo payment status --session <id>
openclaw milimo payment balance
openclaw milimo payment history [--limit 10]
openclaw milimo payment invoice --session <id>
openclaw milimo payment connect --display-name "My Shop" --email seller@example.com
```

### Configuration

| Setting | Value |
|---------|-------|
| Platform Fee | 10% |
| Minimum Payout | $10.00 |
| Payout Schedule | 1st and 15th |
| Retention Period | 7 days |

---

## 5.2 Cryptographic Provenance

### Ed25519 Signing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  PROVENANCE CHAIN                            │
│                                                              │
│  Genesis (v0.1.0) ──► Evolution (v1.0.0) ──► Current       │
│       │                     │                    │          │
│       ▼                     ▼                    ▼          │
│  ┌─────────┐          ┌─────────┐          ┌─────────┐     │
│  │ Signed  │          │ Signed  │          │ Signed  │     │
│  │ Attest. │─────────►│ Attest. │─────────►│ Attest. │     │
│  │ #1      │  parent  │ #2      │  parent  │ #3      │     │
│  └─────────┘          └─────────┘          └─────────┘     │
│                                                              │
│  Each attestation contains:                                 │
│  - Blueprint content hash (SHA-256)                         │
│  - Ed25519 signature                                        │
│  - Parent attestation reference                             │
│  - Evolution summary (tools added/removed)                  │
└─────────────────────────────────────────────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| Key Generation | Ed25519 key pairs stored in `~/.milimo/keys/` |
| Content Hashing | SHA-256 hash of tools, policies, evolution config |
| Signature Verification | Cryptographic proof of authenticity |
| Chain Validation | Full provenance chain verification |
| Tamper Detection | Any modification invalidates signature |

### CLI Commands

```bash
# Provenance operations
openclaw milimo verify                    # Verify current blueprint
openclaw milimo verify --chain            # Validate full chain
openclaw milimo verify --strict           # Warnings = errors
openclaw milimo provenance keygen         # Generate signing key
```

---

## 5.3 Performance Verification

### Badge System

```
┌─────────────────────────────────────────────────────────────┐
│                  BADGE LEVELS                                │
│                                                              │
│  ✅ Verified    0%+    Self-attested baseline               │
│  🥉 Bronze      5%+    Measurable improvement               │
│  🥈 Silver     10%+    Significant gains                    │
│  🥇 Gold       15%+    Strong performance                    │
│  💎 Platinum   25%+    Exceptional results                   │
│  👑 Elite      40%+    Top-tier performance                  │
│                                                              │
│  Badges require:                                             │
│  - Signed performance attestation                           │
│  - Minimum sample size (1000 operations)                    │
│  - Minimum measurement period (30 days)                     │
└─────────────────────────────────────────────────────────────┘
```

### Verification Methods

| Method | Trust Level | Description |
|--------|-------------|-------------|
| Self-Attested | ⭐⭐ | Seller's own claims |
| Backtest | ⭐⭐⭐ | Historical simulation |
| Live Measurement | ⭐⭐⭐⭐ | Real-time tracking |
| Auditor Verified | ⭐⭐⭐⭐⭐ | Third-party audit |

### CLI Commands

```bash
# Badge operations
openclaw milimo badge                    # Show current badge
openclaw milimo badge --performance      # Generate attestation
openclaw milimo badge --list             # List attestations
openclaw milimo badge --verify <file>    # Verify attestation
openclaw milimo badge --auditor <email>  # Request audit
```

---

## Files Created

### Payment Integration

| File | Purpose |
|------|---------|
| `stripe.ts` | Stripe client & core functions |
| `fee-calculator.ts` | Platform fee calculation |
| `payouts.ts` | Seller payout processing |
| `invoices.ts` | Invoice generation |
| `webhooks.ts` | Stripe webhook handler |
| `payment.ts` | Payment CLI commands |
| `.env` / `.env.example` | Environment configuration |

### Provenance Verification

| File | Purpose |
|------|---------|
| `provenance_signer.py` | Ed25519 signing |
| `provenance_verifier.py` | Signature verification |
| `chain_validator.py` | Chain validation |
| `verify.ts` | Verification CLI |

### Performance Verification

| File | Purpose |
|------|---------|
| `attestation_generator.py` | Attestation creation |
| `performance-attestation.json` | Attestation schema |
| `badge.ts` | Badge CLI |
| `third-party-verification.md` | Auditor framework |

---

## Test Results

All 166 tests pass:

```
# tests 166
# suites 39
# pass 166
# fail 0
```

### Stripe Integration Tests

| Test | Result |
|------|--------|
| API Key Verification | ✅ |
| List Products | ✅ |
| Create Customer | ✅ |
| Create Connected Account | ✅ |
| Create Account Link | ✅ |
| Create Test Product | ✅ |
| Checkout Session | ✅ (requires onboarding) |
| Connected Account Balance | ✅ |

---

## Security

### Key Storage

- Keys stored in `~/.milimo/keys/`
- File permissions: 0600 (owner read/write only)
- Never committed to git

### Environment Variables

- `.env` files are git-ignored
- `.env.example` templates committed
- Production keys via deployment platform

### Stripe Security

- Test keys for development
- Webhook signature verification
- Platform fee enforced at Stripe level

---

## Next Steps

Phase 6: Enterprise & University Tier

1. Multi-tenant architecture
2. White-label deployment
3. Tenant management
4. Admin dashboard
5. Cohort automation
