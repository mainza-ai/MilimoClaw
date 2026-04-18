# Stripe Client

Wraps Stripe API for payment processing and invoice management.

## Purpose

Provides Python interface to Stripe via CLI or direct API calls. Falls back to curl-based API calls when Stripe CLI is unavailable.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `STRIPE_API_KEY` | Secret key for API |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret |
| `STRIPE_CURRENCY` | Default currency (default: usd) |

## Operations

### Invoice Operations

| Method | Purpose |
|--------|---------|
| `create_invoice()` | Create invoice for customer |
| `send_invoice()` | Send invoice via email |
| `get_invoice()` | Get invoice details |
| `list_invoices()` | List invoices with filters |
| `finalize_invoice()` | Finalize draft invoice |

### Customer Operations

| Method | Purpose |
|--------|---------|
| `create_customer()` | Create new customer |
| `get_customer()` | Get customer details |
| `list_customers()` | List customers |

### Payment Operations

| Method | Purpose |
|--------|---------|
| `create_payment_intent()` | Create payment intent |
| `confirm_payment_intent()` | Confirm payment |
| `get_payment_intent()` | Get payment status |

### Subscription Operations

| Method | Purpose |
|--------|---------|
| `create_subscription()` | Create subscription |
| `cancel_subscription()` | Cancel subscription |
| `get_subscription()` | Get subscription details |

### Reporting

| Method | Purpose |
|--------|---------|
| `get_balance()` | Get account balance |
| `list_charges()` | List charges |
| `get_revenue_summary()` | Revenue over N days |

## Webhook Handling

```python
def verify_webhook(payload: str, sig_header: str) -> dict | None:
    # Uses Stripe SDK if available
    # Falls back to manual HMAC verification
```

Manual verification:
1. Parse signature header for timestamp and signature
2. Reject events older than 5 minutes (replay attack prevention)
3. Verify HMAC-SHA256 signature

## API Fallback

When Stripe CLI unavailable:
```python
# Direct API call via urllib
url = f"https://api.stripe.com/v1{endpoint}"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/x-www-form-urlencoded",
    "Stripe-Version": "2024-12-18.acacia",
}
```

## Error Handling

All methods return `{"error": "message"}` on failure instead of raising exceptions.

## Relationships

- Used by: [[invoice-generator]] — Create and send invoices
- Used by: [[payment-monitor]] — Check payment status

## Source

`milimo-blueprint/orchestrator/finance/stripe_client.py`
