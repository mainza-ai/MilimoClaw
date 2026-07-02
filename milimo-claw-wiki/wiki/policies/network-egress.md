# Network Egress

**Summary**: Per-claw network egress policies and API allowlists.

**Sources**:
- `milimo-blueprint/policies/*.yaml`
- [NemoClaw Network Policies Reference](https://docs.nvidia.com/nemoclaw/latest/reference/network-policies.html)
- [OpenShell Policy Schema Reference](https://docs.nvidia.com/openshell/latest/reference/policy-schema/)
- [[sandbox-isolation]]

**Last updated**: 2026-06-30

**Tags**: #policies #network #egress

---

## Overview

Each claw has a specific network egress policy that defines which APIs it can access. This prevents data exfiltration and limits attack surface. All endpoints use TLS termination at port 443.

NemoClaw enforces a deny-by-default policy. Only endpoints explicitly listed in the policy are reachable. Unlisted requests are intercepted by OpenShell and surfaced in the TUI for operator approval.

> **GitHub is NOT in the baseline policy.** Apply the `github` preset during onboarding or via `nemoclaw my-assistant policy-add github` if your claw needs GitHub access.

---

## Policy Tiers

During onboarding, the wizard prompts for a policy tier that determines default presets on top of the baseline:

| Tier | Presets | Description |
|------|---------|-------------|
| Restricted | None | Base sandbox only. No third-party access beyond inference. |
| **Balanced** (default) | npm, pypi, huggingface, brew, brave | Full dev tooling and web search. No messaging. |
| Open | npm, pypi, huggingface, brew, brave, slack, discord, telegram, jira, outlook | Broad third-party access including messaging. |

Non-interactive: `NEMOCLAW_POLICY_TIER=balanced nemoclaw onboard --non-interactive --yes-i-accept-third-party-software`

---

## protocol: rest — L7 HTTP Inspection

When an endpoint sets `protocol: rest`, the OpenShell proxy performs L7 HTTP inspection instead of raw TCP passthrough. This enables fine-grained control by HTTP method and path.

### Key Endpoint Fields

| Field | Values | Description |
|-------|--------|-------------|
| `protocol` | `rest` (or omit for TCP) | Enables HTTP request inspection |
| `enforcement` | `enforce`, `audit` | `enforce` blocks violations; `audit` logs only |
| `access` | `read-only`, `read-write`, `full` | Coarse HTTP access level (mutually exclusive with `rules`) |
| `rules` | list of `{allow: {method, path, query?}}` | Fine-grained per-method/path allow rules |
| `deny_rules` | list of `{method, path, command?, query?}` | Deny rules that override allow rules |
| `allowed_ips` | list of CIDRs | SSRF override allowlist |

### Access Levels

| Level | HTTP Methods |
|-------|-------------|
| `read-only` | GET, HEAD, OPTIONS |
| `read-write` | GET, HEAD, OPTIONS, POST, PUT, PATCH |
| `full` | All methods |

### Example — REST API with Deny Rules

```yaml
endpoints:
  - host: api.github.com
    port: 443
    protocol: rest
    enforcement: enforce
    access: read-write
    deny_rules:
      - method: POST
        path: "/repos/*/pulls/*/reviews"
      - method: PUT
        path: "/repos/*/branches/*/protection"
```

---

## Content Claw Egress

```yaml
network_policies:
  # NVIDIA Inference (inference.local proxy — gateway handles credential substitution)
  nvidia_inference:
    endpoints:
    - host: integrate.api.nvidia.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write
    binaries:
    - { path: /usr/bin/python3 }

  # Social Publishing APIs
  twitter_api:
    endpoints:
      - host: api.twitter.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/python3 }

  linkedin_api:
    endpoints:
      - host: api.linkedin.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/python3 }

  tiktok_api:
    endpoints:
      - host: open-api.tiktok.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/python3 }

  # Email APIs
  gmail_api:
    endpoints:
      - host: gmail.googleapis.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Ops Claw Egress

```yaml
network_policies:
  # NVIDIA Inference (inference.local proxy — gateway handles credential substitution)
  nvidia_inference:
    endpoints:
    - host: integrate.api.nvidia.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write

  # Email & Scheduling
  gmail_api:
    endpoints:
      - host: gmail.googleapis.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write

  outlook:
    endpoints:
      - host: outlook.office.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write

  calendly:
    endpoints:
      - host: api.calendly.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-only
```

---

## Analytics Claw Egress

```yaml
network_policies:
  # NVIDIA Inference (inference.local proxy — gateway handles credential substitution)
  nvidia_inference:
    endpoints:
    - host: integrate.api.nvidia.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write
    binaries:
    - { path: /usr/bin/python3 }

  # Platform Analytics (READ-ONLY)
  meta_insights:
    endpoints:
      - host: graph.facebook.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/python3 }

  twitter_analytics:
    endpoints:
      - host: api.twitter.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/python3 }

  # Market Research
  google_trends:
    endpoints:
      - host: trends.google.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Finance Claw Egress

```yaml
network_policies:
  # NVIDIA Inference (inference.local proxy — gateway handles credential substitution)
  nvidia_inference:
    endpoints:
    - host: integrate.api.nvidia.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write

  # Stripe Link CLI — device auth flow requires login.link.com
  stripe_link:
    endpoints:
      - host: login.link.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
      - host: api.link.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/link-cli }

  # Stripe API
  stripe_api:
    endpoints:
      - host: api.stripe.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
      # Payment status checks only — no fund transfers
    binaries:
      - { path: /usr/bin/python3 }

  # Payment gateways
  paypal_api:
    endpoints:
      - host: api-m.paypal.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Build Claw Egress

```yaml
network_policies:
  # NVIDIA Inference (inference.local proxy — gateway handles credential substitution)
  nvidia_inference:
    endpoints:
    - host: integrate.api.nvidia.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write

  # GitHub API (applied via 'github' preset, not baseline)
  github_api:
    endpoints:
      - host: api.github.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
      - host: github.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/local/bin/gh }
      - { path: /sandbox/.openclaw/milimo/bin/gh }
      - { path: /usr/bin/git }
      - { path: /usr/bin/python3 }

  # Vercel API
  vercel_api:
    endpoints:
      - host: api.vercel.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/bin/python3 }

  # Sentry API
  sentry_api:
    endpoints:
      - host: sentry.io
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Assistant Egress

```yaml
network_policies:
  # NVIDIA Inference (inference.local proxy — gateway handles credential substitution)
  # Note: integrate.api.nvidia.com is in the network policy because OpenShell needs
  # an explicit egress rule even for proxied traffic. The gateway intercepts requests
  # to inference.local inside the sandbox and forwards to the real provider endpoint.
  nvidia_inference:
    endpoints:
    - host: integrate.api.nvidia.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write

  # GitHub API (applied via 'github' preset, not baseline)
  github_api:
    endpoints:
    - host: api.github.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write
    binaries:
    - { path: /usr/local/bin/gh }
    - { path: /sandbox/.openclaw/milimo/bin/gh }
    - { path: /usr/bin/git }
    - { path: /usr/local/bin/node }
    - { path: /usr/bin/python3 }

  # Vercel API (deployments)
  vercel_api:
    endpoints:
    - host: api.vercel.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write

  # Sentry API (error monitoring, read-only)
  sentry_api:
    endpoints:
    - host: sentry.io
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-only

  # Stripe API (payments, read-only)
  stripe_api:
    endpoints:
    - host: api.stripe.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-only

  # Telegram Bot API (channel messaging via OpenShell)
  telegram_api:
    endpoints:
    - host: api.telegram.org
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write

  # npm and PyPI registries (from 'balanced' tier presets)
  npm_registry:
    endpoints:
    - host: registry.npmjs.org
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-only
  pypi_registry:
    endpoints:
    - host: pypi.org
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-only
```

---

---

## Hermes Profile: Binary-Scoped Policy

The Hermes profile uses **binary-scoped** network policies — each rule specifies the binary that may open the connection in addition to the host/port. Unlike OpenClaw policies (hostname-only allowlists), Hermes policies require a `binaries` array per endpoint group.

### Hermes Egress (milimo-mcp policy)

```yaml
network_policies:
  # Nous Portal — OAuth login and Tool Gateway setup
  # Uses access: full + tls: skip (L4 tunnel) because the hermes CLI
  # binary makes raw TLS connections that the L7 proxy cannot terminate.
  nous_portal:
    endpoints:
      - host: portal.nousresearch.com
        port: 443
        access: full
        tls: skip
    binaries:
      - { path: /usr/local/bin/hermes }
      - { path: /opt/hermes/.venv/bin/python }

  # Nous Inference API - chat completions after portal login
  # Also L4 tunnel with tls: skip — required for E2E TLS.
  nous_inference:
    endpoints:
      - host: inference-api.nousresearch.com
        port: 443
        access: full
        tls: skip
    binaries:
      - { path: /usr/local/bin/hermes }
      - { path: /opt/hermes/.venv/bin/python }

  # Stripe Link CLI — device auth requires login.link.com + api.link.com
  stripe_link:
    endpoints:
      - host: login.link.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
      - host: api.link.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/local/bin/link-cli }
      - { path: /usr/local/bin/node }
      - { path: /opt/hermes/.venv/bin/python }

  # NVIDIA NIM inference
  nvidia_inference:
    endpoints:
      - host: integrate.api.nvidia.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /opt/hermes/.venv/bin/python }
```

For the full Hermes policy, see `milimo-blueprint/policies/milimo-mcp.yaml`.

### Custom Policy Presets

The Hermes profile supports custom policy presets in the OpenShell policy preset format:

```yaml
preset:
  name: nous-portal
  description: "Allow access to Nous Portal OAuth, inference API, and managed tool gateways"

network_policies:
  nous-portal:
    name: nous-portal
    endpoints:
      - host: portal.nousresearch.com
        port: 443
        access: full
        tls: skip          # REQUIRED — L4 tunnel for raw TLS
      - host: inference-api.nousresearch.com
        port: 443
        access: full
        tls: skip          # REQUIRED — chat completions
    binaries:
      - { path: /usr/local/bin/hermes }
      - { path: /opt/hermes/.venv/bin/python }
```

### Stripe Link Preset

```yaml
preset:
  name: stripe-link
  description: "Allow Stripe Link CLI device auth and spend request creation"

network_policies:
  stripe-link:
    name: stripe-link
    endpoints:
      - host: login.link.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
      - host: api.link.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: read-write
    binaries:
      - { path: /usr/local/bin/link-cli }
      - { path: /usr/local/bin/node }
      - { path: /opt/hermes/.venv/bin/python }
```

`login.link.com` is required for the OAuth device authorization flow. `api.link.com` is required for spend request creation and retrieval. Both must be present; if `login.link.com` is missing, `link-cli auth login` returns `UNKNOWN` and `auth status` cannot validate the session.

Key differences from raw policy YAML:
- Requires `preset:` wrapper at top level
- Endpoints use `access: full` + `tls: skip` (L4 tunnel) for raw TLS instead of `protocol: rest`
- `tls: skip` is **required** — without it, the OpenShell proxy attempts to terminate TLS at L7 and rejects the CONNECT tunnel with 403
- Valid protocols for L7 inspection: `rest`, `websocket`, `graphql`, `sql` (not `https`)
- Place preset files in `policies/presets/` subdirectory

Apply at runtime:
```bash
nemohermes milimo-hermes policy-add --from-dir milimo-blueprint/policies/presets/ --yes
```

---

## Blocked Requests

When a claw attempts to access a non-allowed endpoint:

```
[OCSF] NET:OPEN [MED] DENIED /usr/local/bin/node -> api.github.com:443 [policy:- engine:opa]
```

### Common Fixes

1. Add binary to allowlist
2. Add endpoint to policy (with `protocol: rest` + `enforcement: enforce`)
3. Check policy is loaded (`nemoclaw my-assistant policy-list`)
4. Approve the request in the TUI (`openshell term`)

---

## Updating Network Policy

### Recommended: nemoclaw policy-add (non-destructive merge)

```bash
# Add a built-in preset — merges into live policy without dropping existing presets
nemoclaw my-assistant policy-add github --yes

# Add a custom preset file
nemoclaw my-assistant policy-add --from-file ./presets/my-internal-api.yaml --yes

# Add all presets in a directory
nemoclaw my-assistant policy-add --from-dir ./presets/ --yes

# Remove a preset
nemoclaw my-assistant policy-remove github --yes

# List currently applied presets
nemoclaw my-assistant policy-list
```

### Static Changes (persist across recreations)

```bash
# Edit baseline policy
vim milimo-blueprint/policies/assistant-sandbox.yaml

# Re-run onboarding to apply
nemoclaw onboard
```

### Advanced: openshell policy set (full replacement)

> **WARNING**: `openshell policy set` REPLACES the entire live policy — it does NOT merge. Always snapshot the live policy first:

```bash
openshell policy get --full my-assistant > live-policy.yaml
# Edit live-policy.yaml, then:
openshell policy set --policy live-policy.yaml my-assistant
```

### One-off Approval via TUI

```bash
openshell term
```

---

## Related Pages

- [[policy-overview]] — Policy structure
- [[sandbox-isolation]] — Isolation model
- [[assistant-lucy]] — Assistant policy
