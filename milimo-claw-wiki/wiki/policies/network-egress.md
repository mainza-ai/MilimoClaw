# Network Egress

**Summary**: Per-claw network egress policies and API allowlists.

**Sources**:
- `milimo-blueprint/policies/*.yaml`
- [[sandbox-isolation]]

**Last updated**: 2026-04-14

**Tags**: #policies #network #egress

---

## Overview

Each claw has a specific network egress policy that defines which APIs it can access. This prevents data exfiltration and limits attack surface.

---

## Content Claw Egress

```yaml
network_policies:
  # Social Publishing APIs
  twitter_api:
    endpoints:
      - host: api.twitter.com
        port: 443
    binaries:
      - { path: /usr/bin/python3 }
      - { path: /sandbox/.local/bin/milimo }

  linkedin_api:
    endpoints:
      - host: api.linkedin.com
        port: 443
    binaries:
      - { path: /usr/bin/python3 }

  tiktok_api:
    endpoints:
      - host: open-api.tiktok.com
        port: 443
    binaries:
      - { path: /usr/bin/python3 }

  # Email APIs
  gmail_api:
    endpoints:
      - host: gmail.googleapis.com
        port: 443
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Ops Claw Egress

```yaml
network_policies:
  # Email & Scheduling
  gmail_api:
    endpoints:
      - host: gmail.googleapis.com
        port: 443

  outlook:
    endpoints:
      - host: outlook.office.com
        port: 443

  calendly:
    endpoints:
      - host: api.calendly.com
        port: 443
```

---

## Analytics Claw Egress

```yaml
network_policies:
  # Platform Analytics (READ-ONLY)
  meta_insights:
    endpoints:
      - host: graph.facebook.com
        port: 443
    rules:
      - allow: { method: GET }

  twitter_analytics:
    endpoints:
      - host: api.twitter.com
        port: 443
    rules:
      - allow: { method: GET }

  # Market Research
  google_trends:
    endpoints:
      - host: trends.google.com
        port: 443
```

---

## Finance Claw Egress

```yaml
network_policies:
  # Stripe API
  stripe_api:
    endpoints:
      - host: api.stripe.com
        port: 443
    binaries:
      - { path: /usr/bin/python3 }
      - { path: /sandbox/.local/bin/milimo }

  # Payment gateways
  paypal_api:
    endpoints:
      - host: api-m.paypal.com
        port: 443
```

---

## Build Claw Egress

```yaml
network_policies:
  # GitHub API
  github_api:
    endpoints:
      - host: api.github.com
        port: 443
      - host: github.com
        port: 443
    binaries:
      - { path: /usr/bin/gh }
      - { path: /usr/bin/git }
      - { path: /sandbox/.local/bin/gh }
      - { path: /usr/bin/python3 }

  # Vercel API
  vercel_api:
    endpoints:
      - host: api.vercel.com
        port: 443
    binaries:
      - { path: /usr/bin/python3 }

  # Sentry API
  sentry_api:
    endpoints:
      - host: sentry.io
        port: 443
    binaries:
      - { path: /usr/bin/python3 }
```

---

## Assistant Egress

```yaml
network_policies:
  # NVIDIA NIM (inference)
  nvidia:
    endpoints:
      - host: integrate.api.nvidia.com
        port: 443
    binaries:
      - { path: /usr/local/bin/openclaw }
      - { path: /usr/bin/python3 }
      - { path: /usr/local/bin/node }
      - { path: /sandbox/.local/bin/milimo }

  # GitHub API
  github_api:
    endpoints:
      - host: api.github.com
        port: 443
    binaries:
      - { path: /usr/bin/gh }
      - { path: /usr/bin/git }
      - { path: /sandbox/.local/bin/gh }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Vercel, Sentry, Stripe (read-only)
  [additional APIs...]
```

---

## Blocked Requests

When a claw attempts to access a non-allowed endpoint:

```
[OCSF] NET:OPEN [MED] DENIED /usr/local/bin/node -> api.github.com:443 [policy:- engine:opa]
```

### Common Fixes

1. Add binary to allowlist
2. Add endpoint to policy
3. Check policy is loaded

---

## Updating Network Policy

```bash
# Edit policy file
vim milimo-blueprint/policies/assistant-sandbox.yaml

# Apply dynamically
openshell policy set policies/assistant-sandbox.yaml

# Or redeploy via install.sh
./install.sh
```

---

## Related Pages

- [[policy-overview]] — Policy structure
- [[sandbox-isolation]] — Isolation model
- [[assistant-lucy]] — Assistant policy
