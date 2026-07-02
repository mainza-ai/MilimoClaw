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

## CLI Implementation

### Stripe CLI Subprocess (MilimoClaw Spend Handler)

The spend path in `milimo-core` invokes the Stripe CLI directly via `subprocess.run`:

```python
cmd = ["stripe", *args, "--api-key", self.api_key, "--format", "json"]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
```

> [!WARNING]
> **Audit Finding F5-1 [Critical]**: Passing the Stripe secret key on the command line as `--api-key` exposes it to all local users via `/proc/*/cmdline` and `ps aux`. The key should be passed via the `STRIPE_API_KEY` environment variable instead of as an argument:
> ```python
> cmd = ["stripe", *args, "--format", "json"]
> env = {**os.environ, "STRIPE_API_KEY": self.api_key}
> proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds, env=env)
> ```

Source: `milimo-core/src/milimo_core/finance/stripe_client.py:L84`.

### Python SDK Path (Direct API)

When Stripe CLI is unavailable, direct REST calls use the `Authorization: Bearer` header in urllib — this does not expose the key to the process table:
```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/x-www-form-urlencoded",
    "Stripe-Version": "2024-12-18.acacia",
}
```

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

> [!WARNING]
> **Audit Finding SA-7.1 [High]**: `webhook_server.py:L89-98` catches all exceptions in inbound handlers, logs the error, and always returns HTTP 200. A malformed or spoofed webhook will be silently dropped rather than causing a visible 5xx, masking delivery failures. Returns should be HTTP 500 when internal execution fails.

Source: `milimo-core/src/milimo_core/ops/webhook_server.py:L89-98`.

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
