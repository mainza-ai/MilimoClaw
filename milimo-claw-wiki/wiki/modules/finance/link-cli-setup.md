# Link CLI Setup

**Summary**: Step-by-step guide for installing, authenticating, and testing the Stripe Link CLI (`@stripe/link-cli`) inside the Hermes sandbox. Covers the OAuth device flow, approval URL mechanics, config file location, and multi-user considerations for the [[spend-handler]] spend flow.

**Sources**:
- `milimo-blueprint/orchestrator/finance/spend_handler.py`
- `milimo-blueprint/policies/presets/stripe-link.yaml`
- Hermes skill: `official/payments/stripe-link-cli`

**Last updated**: 2026-07-03

**Tags**: #module #finance #stripe #link-cli #oauth #setup #sandbox

---

## Prerequisites

1. Hermes sandbox running (`nemohermes milimo-hermes connect` or `docker compose up`)
2. [[network-egress]] policy loaded — the `stripe-link` preset must be applied (contains `api.link.com` + `/usr/local/bin/link-cli` binary allowlist)
3. `MILIMO_OPERATOR` set (see [[war-room]] dashboard). `XDG_CONFIG_HOME` is derived from it automatically: `/sandbox/.config/users/{operator_id}`
4. If running locally inside the sandbox shell, `.bashrc`/`.profile` exports `XDG_CONFIG_HOME` for you — verify with `echo $XDG_CONFIG_HOME`

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

## Where the Token Lives (Per-Operator)

After successful auth, `link-cli` stores credentials at:

```
$XDG_CONFIG_HOME/link-cli-nodejs/config.json
```

For the default system operator, this resolves to `/sandbox/.config/link-cli-nodejs/config.json`. For any named operator (`MILIMO_OPERATOR=<name>`), it resolves to:

```
/sandbox/.config/users/<operator_id>/link-cli-nodejs/config.json
```

This isolation is automatic — the Dockerfile `.bashrc`/`.profile` hook exports:

```bash
if [ -n "$MILIMO_OPERATOR" ]; then
  export XDG_CONFIG_HOME="/sandbox/.config/users/${MILIMO_OPERATOR}"
fi
```

`SpendApprovalHandler.handle_hold_release()` reads `MILIMO_OPERATOR` from the runtime environment and propagates it through the release flow. Each operator has an isolated Link account, isolated approval phone, and isolated spend log — no shared state.

Inspect the current session for a given operator:

```bash
link-cli auth status
# → Logged in as operator@example.com (account: acct_...)
```

---

## List Connected Payment Methods

```bash
link-cli payment-methods list
```

> **Note**: `payment-methods list` does **not** accept `--test`. The card wallet structure is shared across modes; test vs. live mode division happens at `spend-request create` time.

Shows cards, bank accounts, and wallets connected to the authenticated Stripe Link account. Note the `id` of any payment method you want to use with `--payment-method-id` in spend requests.

To add a test payment method, you can use a Stripe test card:
- Number: `4242 4242 4242 4242`
- Expiry: any future date
- CVC: any 3 digits
- Add via the Stripe Dashboard → Link → Test mode, or use `link-cli payment-methods create` if available in your version.

---

## Required Egress Endpoints

For the device auth authorization flow to work, the sandbox egress policy **must** allow outbound HTTPS to both:

| Host | Purpose |
|------|---------|
| `api.link.com` | Spend request creation and retrieval |
| `login.link.com` | Device authorization flow — token issuance and validation |

If `login.link.com` is blocked, `link-cli auth login` returns an `UNKNOWN` request failure and `auth status` cannot validate the session.

Verify the policy is loaded:

```bash
nemohermes milimo-hermes policy-list | grep -E "link|login"
# → should show entries for login.link.com and api.link.com
```

If missing, apply the `stripe-link` preset:

```bash
nemohermes milimo-hermes policy-add --from-dir milimo-blueprint/policies/presets/ --yes
```

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
  --no-request-approval \
  --test \
  --format json
```

> **Note**: The Finance Claw spend handler uses `--no-request-approval` during creation, then fires `link-cli spend-request request-approval <id>` in a separate call. This is the non-blocking pattern: creation returns immediately, and approval is triggered asynchronously.

Expected response:

```json
{
  "id": "lsrq_1ToFQOK2MJSohSIrORocpMZM",
  "status": "pending_approval"
}
```

After creation, trigger approval manually:

```bash
link-cli spend-request request-approval lsrq_1ToFQOK2MJSohSIrORocpMZM
```

This sends the push notification to the user's phone. The `approval_url` is not returned by `create` when using `--no-request-approval`; construct it manually as `https://app.link.com/activity/approve/<id>` if needed.

### The Approval URL

The `https://app.link.com/activity/approve/{id}` URL is the **second human gate**.

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

## Multi-User / Operator Isolation

The sandbox supports **multiple operators with isolated Link accounts**. Isolation is implemented via per-operator `XDG_CONFIG_HOME`:

| Scenario | Behavior |
|----------|----------|
| Operator A sets `MILIMO_OPERATOR=alice` and runs `link-cli auth login` | Token stored at `/sandbox/.config/users/alice/link-cli-nodejs/config.json` |
| Operator B sets `MILIMO_OPERATOR=bob` and runs `link-cli auth login` | Token stored at `/sandbox/.config/users/bob/link-cli-nodejs/config.json` |
| Both operators post spend requests in the same sandbox | Each request routes to the **correct operator's** Link account and phone |
| Operator A inspects state while logged in as A | `link-cli auth status` shows alice's account only |

### How It Works

1. **Dockerfile `.bashrc`/`.profile` hook** exports `XDG_CONFIG_HOME=/sandbox/.config/users/${MILIMO_OPERATOR}` if `MILIMO_OPERATOR` is set.
2. **`SpendApprovalHandler.handle_hold_release(operator_id=...)`** reads the operator ID at runtime and sets `XDG_CONFIG_HOME` in the subprocess environment before calling `link-cli`.
3. **`finance_claw.py` and `spend_warroom_bridge.py`** propagate the operator name through the release flow so the right token is used automatically.
4. **The HTMX War Room server** (`milimo-hermes-plugin/warroom/server.py`) scopes approval sessions per operator in its own session store, so `/v1/warroom/approve/{action_id}` routes to the correct operator's approval action.

### Operator-Aware Spend Release

```python
# spend_handler.py
def handle_hold_release(self, action_id: str, operator_id: str) -> SpendRequest:
    spend_id = action_id.replace("spend-hold-", "")
    request = self._get_request(spend_id)

    env = os.environ.copy()
    if operator_id and operator_id not in ("system", "operator", "sandbox", ""):
        env["XDG_CONFIG_HOME"] = f"/sandbox/.config/users/{operator_id}"
    else:
        env["XDG_CONFIG_HOME"] = "/sandbox/.config"

    cmd = [
        self.link_cli_path,
        "spend-request",
        "create",
        ...
        "--test",
        "--format", "json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=310, env=env)
```

### Default / System Operator Fallback

When `operator_id` is missing, empty, or one of the default system IDs (`system`, `operator`, `sandbox`), `XDG_CONFIG_HOME` falls back to `/sandbox/.config`. This prevents the orchestrator daemon (which may run as `root` with no `HOME=/sandbox`) from silently using `/root/.config/link-cli-nodejs/config.json`, which is unauthenticated and causes Stripe Link API failures.

Verified behavior:
```bash
# System operator (no MILIMO_OPERATOR set)
link-cli auth status
# → uses /sandbox/.config/link-cli-nodejs/config.json

# Named operator
MILIMO_OPERATOR=alice link-cli auth status
# → uses /sandbox/.config/users/alice/link-cli-nodejs/config.json
```

### When to Use Named Operators

- **Hackathons / demos** — each tester uses their own `MILIMO_OPERATOR` handle; their approvals hit their own phone
- **Multi-operator production** — each human operator has a persistent Link account scoped to their identity
- **CI / automated tests** — use `MILIMO_OPERATOR=system` (or omit) to use the default shared config; test mode (`--test`) prevents real charges

### Verifying Isolation

```bash
# As alice
MILIMO_OPERATOR=alice link-cli auth status
# → Logged in as alice@example.com

# As bob
MILIMO_OPERATOR=bob link-cli auth status
# → Logged in as bob@example.com

# Create spend request as alice
MILIMO_OPERATOR=alice link-cli spend-request create ... --request-approval --test
# → Approval URL goes to alice's phone
```

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

### Policy blocks `api.link.com` or `login.link.com`

The `stripe-link` preset is not loaded.

```bash
nemohermes milimo-hermes policy-add --from-dir milimo-blueprint/policies/presets/ --yes
nemohermes milimo-hermes policy-list | grep -E "link|login"
```

Both `api.link.com` and `login.link.com` must be present. `login.link.com` is required for the device authorization flow — if it is missing, `link-cli auth login` returns `UNKNOWN` and `auth status` cannot validate the session.

Also verify the OpenShell proxy is not intercepting TLS (the preset uses `access: full` + `tls: skip`).

### `Unknown flag: --test` on `payment-methods list`

`link-cli payment-methods list` does not accept `--test`. Test mode only applies to `spend-request create`.

Use: `link-cli payment-methods list`

### Approval URL does not open / app says "request not found"

- Confirm the spend request status is `pending_approval`: `link-cli spend-request get lsrq_...`
- Ensure you are logged in to the **same** Stripe Link account that created the request — cross-account approval is not supported
- Check that test mode matches: a `--test` request must be approved in the Stripe **test** Dashboard; a live request must be approved in the **live** Dashboard

---

## Related Pages

- [[spend-handler]] — SpendApprovalHandler implementation, two-stage gate, and per-operator isolation
- [[finance-claw]] — Finance Claw entry point and inbound message handlers
- [[spend-warroom-bridge]] — Bridges spend handler into SoloWarRoom action queue
- [[approval-thresholds]] — REVIEW/HOLD/AUTO rules for spend actions
- [[war-room]] — War Room TUI and HTMX dashboard server
- [[network-egress]] — Policy configuration and preset management
- [[stripe-client]] — Stripe API client (invoices, customers, charges)

---

## See Also

- Stripe Link documentation: https://docs.stripe.com/link
- `link-cli` reference: https://docs.stripe.com/link/cli
- Policy preset: `milimo-blueprint/policies/presets/stripe-link.yaml`
- HTMX War Room server: `milimo-hermes-plugin/warroom/server.py`
- Environment config: `/sandbox/.hermes/.env` — `MILIMO_SPEND_TEST_MODE`, `MILIMO_OPERATOR`, `XDG_CONFIG_HOME`
- Container code paths: inside a running Hermes sandbox, the active orchestrator code may be at `/sandbox/.nemoclaw/blueprints/0.1.0/orchestrator/finance/`, `/opt/nemoclaw-blueprint/orchestrator/finance/`, or `/opt/milimo-core/src/milimo_core/finance/` — sync host changes with `docker cp` if the container does not bind-mount `/sandbox`
