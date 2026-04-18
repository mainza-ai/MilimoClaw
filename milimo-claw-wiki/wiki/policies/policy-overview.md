# Policy Overview

**Summary**: Sandbox policy structure and enforcement for MilimoClaw.

**Sources**:
- `milimo-blueprint/policies/`

**Last updated**: 2026-04-14

**Tags**: #policies #sandbox #security

---

## Overview

Sandbox policies define what each claw can access — filesystem, network, and process permissions. Policies are enforced by the NemoClaw runtime.

## Policy Files

| Policy | Claw | Purpose |
|--------|------|---------|
| `content-sandbox.yaml` | [[content-claw]] | Content Claw permissions |
| `ops-sandbox.yaml` | [[ops-claw]] | Ops Claw permissions |
| `analytics-sandbox.yaml` | [[analytics-claw]] | Analytics Claw permissions |
| `finance-sandbox.yaml` | [[finance-claw]] | Finance Claw permissions |
| `build-sandbox.yaml` | [[build-claw]] | Build Claw permissions |
| `assistant-sandbox.yaml` | [[assistant-lucy]] | Assistant permissions |

---

## Policy Structure

```yaml
version: 1

filesystem_policy:
  include_workdir: true
  read_only:
    - /usr
    - /lib
    - /sandbox/analytics/reports  # Cross-mount
  read_write:
    - /sandbox/content

landlock:
  compatibility: best_effort

process:
  run_as_user: sandbox
  run_as_group: sandbox

network_policies:
  twitter_api:
    name: twitter_api
    endpoints:
      - host: api.twitter.com
        port: 443
        protocol: rest
    binaries:
      - { path: /usr/bin/python3 }
      - { path: /sandbox/.local/bin/milimo }
```

---

## Filesystem Policy

### Read-Write Paths

Each claw has full access to its own mount:

| Claw | Mount |
|------|-------|
| Content | `/sandbox/content` |
| Ops | `/sandbox/clients` |
| Analytics | `/sandbox/analytics` |
| Finance | `/sandbox/finance` |
| Build | `/sandbox/build` |

### Read-Only Cross-Mounts

Analytics Claw's shared report:

```yaml
read_only:
  - /sandbox/analytics/reports  # All claws can read
```

---

## Network Policy

### API Allowlists

Each claw has specific API access:

| Claw | Allowed APIs |
|------|--------------|
| Content | Twitter, LinkedIn, TikTok, Gmail |
| Ops | Email APIs, Calendly |
| Analytics | Read-only platform analytics, Google Trends |
| Finance | Stripe, payment gateways |
| Build | GitHub, Vercel, Sentry |
| Assistant | NVIDIA, GitHub, Vercel, Sentry, Stripe |

### Binary Allowlists

Only specific binaries can make network requests:

```yaml
binaries:
  - { path: /usr/bin/python3 }
  - { path: /sandbox/.local/bin/milimo }
  - { path: /usr/local/bin/node }  # For Assistant
```

---

## Process Policy

### seccomp BPF

Filters dangerous syscalls:
- `execve` restricted to allowed binaries
- `socket` restricted to allowed network operations
- `ptrace` blocked (no debugging)
- `mount`/`umount` blocked

---

## Updating Policies

### Dynamic Update

```bash
openshell policy set policies/assistant-sandbox.yaml
```

### Via install.sh

Policies are deployed during `./install.sh` execution.

---

## Verification

### Phase A Tests

```bash
pytest -m phase_a tests/test_phase_a_isolation.py
```

Tests verify:
- Filesystem isolation
- Network egress restrictions
- Cross-mount permissions

---

## Related Pages

- [[sandbox-isolation]] — Isolation details
- [[network-egress]] — Network policy
- [[ground-truth-hierarchy]] — Policy authority
