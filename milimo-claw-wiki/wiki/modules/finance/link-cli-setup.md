# Link CLI Setup

**Summary**: Step-by-step guide for installing, authenticating, and testing the Stripe Link CLI (`@stripe/link-cli`) inside the Hermes sandbox. Covers the OAuth device flow, approval URL mechanics, config file location, and multi-user considerations for the [[spend-handler]] spend flow.

**Sources**:
- `milimo-blueprint/orchestrator/finance/spend_handler.py`
- `milimo-blueprint/policies/presets/stripe-link.yaml`
- Hermes skill: `official/payments/stripe-link-cli`

**Last updated**: 2026-07-01

**Tags**: #module #finance #stripe #link-cli #oauth #setup #sandbox

---

## Prerequisites

1. Hermes sandbox running (`nemohermes milimo-hermes connect` or `docker compose up`)
2. [[network-egress]] policy loaded — the `stripe-link` preset must be applied (contains `api.link.com` + `/usr/local/bin/link-cli` binary allowlist)
3. `XDG_CONFIG_HOME` set (Hermes gateway daemon sets `HOME=/sandbox`, so `~/.config` resolves to `/sandbox/.config` automatically)

---

## Install the Stripe Link CLI Skill

Install the official Hermes skill that bundles the `link-cli` Node.js binary:

```bash
hermes skills install official/payments/stripe-link-cli
```

Verify the binary is present and on the PATH inside the sandbox:

```bash
which link-cli
# → /usr/local/bin/link-cli
link-cli --version
# → @stripe/link-cli v0.8.2 (or newer)
```

If `which link-cli` returns nothing, ensure `/usr/local/bin` is on `$PATH` in the sandbox shell.

---

## Authenticate: `link-cli auth login`

Run inside the sandbox shell:

```bash
link-cli auth login
```

### What Happens

`link-cli auth login` launches an **OAuth 2.0 device authorization flow**:

1. The CLI prints a **verification URL** and a **user code** to your terminal.
2. Open the URL in a browser on any device (it does not need to be the sandbox host).
3. Log in (or sign up) with your **Stripe account** credentials.
4. Enter the **user code** shown in the terminal (or displayed on the page).
5. Approve the OAuth consent screen.
6. The CLI receives an access token and writes it to disk.

### Example Terminal Output

```
⚠️  Authorize this device at: https://connect.stripe.com/device_auth/...
Enter the code: ABCD-EFGH
Successfully authenticated!
Logged in as you@example.com (account: acct_...)
```

### Approval URL for Another Human

If you are walking a second person through the flow (e.g., a teammate testing their own Link account), give them the **exact same URL** printed by your terminal. Stripe's device flow is account-specific — whoever completes the code entry and logs in owns the resulting token.

---

## Where the Token Lives

After successful auth, `link-cli` stores credentials at:

```
/sandbox/.config/link-cli-nodejs/config.json
```

This path is derived from `$XDG_CONFIG_HOME` (resolves to `$HOME/.config` = `/sandbox/.config` inside the Hermes gateway daemon environment).

**Contents are single-account.** There is one token file, one active session. If a second person runs `link-cli auth login` with different Stripe credentials, it silently overwrites this file.

You can inspect the current session (without exposing the raw token):

```bash
link-cli auth status
# → Logged in as you@example.com (account: acct_...)
```

---

## List Connected Payment Methods

```bash
link-cli payment-methods list --test
```

Shows cards, bank accounts, and wallets connected to the authenticated Stripe Link account. Note the `id` of any payment method you want to use with `--payment-method-id` in spend requests.

To add a test payment method, you can use a Stripe test card:
- Number: `4242 4242 4242 4242`
- Expiry: any future date
- CVC: any 3 digits
- Add via the Stripe Dashboard → Link → Test mode, or use `link-cli payment-methods create` if available in your version.

---

## Create a Test Spend Request

Use `--test` to run in Stripe Link test mode (no real charges):

```bash
link-cli spend-request create \
  --merchant-name "MilimoClaw" \
  --merchant-url "https://milimoclaw.example.com" \
  --context "Test spend request from Finance Claw" \
  --amount 5000 \
  --total "type:total,display_text:Total,amount:5000" \
  --request-approval \
  --test \
  --format json
```

Expected response:

```json
{
  "id": "lsrq_1ToFQOK2MJSohSIrORocpMZM",
  "status": "pending_approval",
  "approval_url": "https://app.link.com/activity/approve/lsrq_1ToFQOK2MJSohSIrORocpMZM"
}
```

### The Approval URL

The `approval_url` (or the `https://app.link.com/activity/approve/{id}` pattern) is the **second human gate**.

- The operator clicks (or opens on their phone) the approval URL.
- They log in to their Stripe Link account if not already authenticated.
- They tap **Approve** or **Deny**.
- The `link-cli` spend request transitions to `approved` or `denied`.
- `link-cli spend-request get lsrq_...` shows the updated status.

> **Important**: This is the same URL mechanism used by [[spend-handler]] in its HOLD release stage. The Hermes agent never approves its own spend — Gate 1 is the War Room HOLD release; Gate 2 is the human tapping Approve in the Stripe Link app.

---

## Test Mode vs. Live Mode

| Flag | Behavior |
|------|----------|
| `--test` (or `MILIMO_SPEND_TEST_MODE=true`) | Uses Stripe test environment; `link-cli` prints `lsrq_*` IDs that do not move real money |
| Omit `--test` | Live environment; requires a live Stripe Link account with real funding sources |

`SpendApprovalHandler` default:

```python
test_mode = os.environ.get("MILIMO_SPEND_TEST_MODE", "true").lower() == "true"
```

To run live in production, set `MILIMO_SPEND_TEST_MODE=false` and authenticate against your live Stripe account.

---

## Multi-User / Shared Sandbox

The sandbox is **single-account by design**:

| Scenario | Behavior |
|----------|----------|
| Two operators, same sandbox, same auth | Both use the same Stripe Link account; approvals hit the same phone |
| Two operators, same sandbox, different auth | The second `auth login` silently overwrites the first person's token |
| Two operators, separate sandboxes | Each sandbox has its own `/sandbox/.config/link-cli-nodejs/` volume; accounts are isolated |

For hackathos or demos with multiple testers, prefer **separate sandbox containers** (separate Docker volumes) so each tester has an isolated Link account and approval flow.

---

## Troubleshooting

### `link-cli: command not found`

The Hermes skill did not install the binary, or `/usr/local/bin` is not on `$PATH`.

```bash
hermes skills list | grep stripe
hermes skills install official/payments/stripe-link-cli
which link-cli
```

### `Not authenticated` / `401 Unauthorized`

The token in `/sandbox/.config/link-cli-nodejs/config.json` is missing or expired.

```bash
link-cli auth status    # confirm current account
link-cli auth login     # re-authenticate
```

### Policy blocks `api.link.com`

The `stripe-link` preset is not loaded.

```bash
nemohermes milimo-hermes policy-add --from-dir milimo-blueprint/policies/presets/ --yes
nemohermes milimo-hermes policy-list | grep stripe
```

Also verify the OpenShell proxy is not intercepting TLS (the preset uses `access: full` + `tls: skip`).

### Approval URL does not open / app says "request not found"

- Confirm the spend request status is `pending_approval`: `link-cli spend-request get lsrq_...`
- Ensure you are logged in to the **same** Stripe Link account that created the request — cross-account approval is not supported
- Check that test mode matches: a `--test` request must be approved in the Stripe **test** Dashboard; a live request must be approved in the **live** Dashboard

---

## Related Pages

- [[spend-handler]] — SpendApprovalHandler implementation and two-stage gate
- [[finance-claw]] — Finance Claw entry point and inbound message handlers
- [[approval-thresholds]] — REVIEW/HOLD/AUTO rules for spend actions
- [[network-egress]] — Policy configuration and preset management
- [[stripe-client]] — Stripe API client (invoices, customers, charges)

---

## See Also

- Stripe Link documentation: https://docs.stripe.com/link
- `link-cli` reference: https://docs.stripe.com/link/cli
- Policy preset: `milimo-blueprint/policies/presets/stripe-link.yaml`
- Environment config: `/sandbox/.hermes/.env` — `MILIMO_SPEND_TEST_MODE`, `XDG_CONFIG_HOME`
