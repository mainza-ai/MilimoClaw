# Sandbox Isolation

**Summary**: Kernel-level isolation for each claw using Landlock, seccomp, and filesystem mounts.

**Sources**:
- `raw/ARCHITECTURE.md`
- `raw/AGENTS.md`

**Last updated**: 2026-04-14

**Tags**: #architecture #sandbox #isolation #security

---

## Overview

Each claw runs inside a NemoClaw sandbox with **kernel-level isolation**. This ensures that even if a claw is compromised, it cannot access data or resources belonging to other claws.

## Isolation Layers

| Layer | Mechanism | What It Protects |
|-------|-----------|------------------|
| **Filesystem** | Landlock LSM | Each claw can only access its own `/sandbox/<role>` mount |
| **Network** | OpenShell netns + egress policy | Per-claw API allowlists — Finance can't reach social APIs |
| **Process** | seccomp BPF | Blocks privilege escalation, restricts dangerous syscalls |
| **Inference** | Privacy router intercept | Sensitive data routed to local NIM, never to cloud |
| **Communication** | Typed contract validation | Inter-claw messages validated against policy before delivery |

## Filesystem Mounts

### Mount Structure

```
/sandbox/
├── content/           # Content Claw — brand assets, drafts, style guides
├── clients/           # Ops Claw — client records, project histories
├── analytics/         # Analytics Claw — performance data, reports
│   └── reports/       # Read-only cross-mount for Content Claw
├── finance/           # Finance Claw — invoices, revenue, pricing
└── build/             # Build Claw — codebase, secrets, deploy configs
    ├── repo/          # Codebase (GitHub mount)
    ├── context/       # Sprint plans, error patterns, cost tracking
    ├── prs/           # PR state tracking
    ├── deployments/   # Deploy state
    ├── docs/          # Changelog, API docs, devlog
    ├── memory/        # Filesystem memory pattern
    └── logs/          # Operational logs
```

### Access Rules

Each claw has:
- **Read-write** access only to its own mount
- **Read-only** cross-mounts are explicitly declared
- **No access** to any other claw's mount

### Cross-Mount Exception

One exception exists — Analytics Claw's shared read export:

```
/sandbox/analytics/reports/weekly-intelligence.json
```

This file must be configured as a read-only mount in **all five** claw sandbox policies. It's the only file in the entire mesh that all claws can read directly without a message contract.

## Network Isolation

### Egress Policy

Each claw has a specific API allowlist defined in its sandbox policy:

| Claw | Allowed APIs |
|------|--------------|
| Content | Social platforms (Twitter, LinkedIn, TikTok), Gmail |
| Ops | Email APIs, calendly |
| Analytics | Read-only platform analytics, Google Trends |
| Finance | Stripe, payment gateways |
| Build | GitHub, Vercel, Sentry |

### Network Policy Files

Policy files define allowed network access:

```yaml
# Example: content-sandbox.yaml
network_policies:
  twitter_api:
    endpoints:
      - host: api.twitter.com
        port: 443
    binaries:
      - /usr/bin/python3
      - /sandbox/.local/bin/milimo
```

## Process Isolation

### seccomp BPF

Filters dangerous system calls:

- Blocks `execve` for unauthorized binaries
- Restricts `socket` to allowed network operations
- Prevents `ptrace` and debug attempts
- Limits `mount` and `umount`

### Process Tree

Each claw runs as an isolated process tree:

```
claw_launcher.py
├── content_claw.py
│   ├── content_generator.py
│   └── platform_publisher.py
└── scheduler.py
```

## Implementation

### Sandbox Policy Files

Location: `milimo-blueprint/policies/`

| Policy File | Claw |
|-------------|------|
| `content-sandbox.yaml` | [[content-claw]] |
| `ops-sandbox.yaml` | [[ops-claw]] |
| `analytics-sandbox.yaml` | [[analytics-claw]] |
| `finance-sandbox.yaml` | [[finance-claw]] |
| `build-sandbox.yaml` | [[build-claw]] |
| `assistant-sandbox.yaml` | [[assistant-lucy]] |

### Policy Structure

```yaml
version: 1
filesystem_policy:
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
    endpoints:
      - host: api.twitter.com
        port: 443
    binaries:
      - /usr/bin/python3
```

## Verification

### Phase A Tests

Isolation is verified by Phase A tests:

```bash
pytest -m phase_a tests/test_phase_a_isolation.py
```

Tests verify:
- Each claw cannot read other claws' mounts
- Cross-mounts are read-only
- Network egress is restricted to allowed APIs
- Process isolation is enforced

## Related Pages

- [[policy-overview]] — Policy structure details
- [[network-egress]] — Network policy configuration
- [[mesh-coordinator]] — Inter-sandbox communication
- [[privacy-router]] — Inference isolation
