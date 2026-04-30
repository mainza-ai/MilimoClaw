# Sandbox Isolation

**Summary**: Kernel-level isolation for each claw using Landlock, process limits, capability dropping, and filesystem mounts within a shared NemoClaw sandbox.

**Sources**:
- `raw/ARCHITECTURE.md`
- `raw/AGENTS.md`

**Last updated**: 2026-04-29

**Tags**: #architecture #sandbox #isolation #security

---

## Overview

Each claw runs inside a **shared** NemoClaw sandbox with **kernel-level isolation** enforced per-path. All claws share the same sandbox instance; per-claw data isolation is enforced by Landlock writable-path rules and the Python orchestrator's path conventions. Even if a claw is compromised, it cannot access data belonging to other claws at the Landlock level.

## Isolation Layers

| Layer | Mechanism | What It Protects |
|-------|-----------|------------------|
| **Filesystem** | Landlock LSM | Each claw can only access its own `/sandbox/.openclaw-data/milimo/claws/<role>` mount |
| **Network** | OpenShell netns + egress policy | Per-claw API allowlists — Finance can't reach social APIs |
| **Process** | ulimit + cap-drop + capsh + no-new-privileges | `ulimit -u 512` limits processes, `--cap-drop=ALL` + entrypoint `capsh` drops 8 capabilities, 5 retained for `gosu` (`CHOWN`, `SETUID`, `SETGID`, `FOWNER`, `KILL`), `no-new-privileges` prevents escalation, non-root sandbox user (UID 999), PATH hardening |
| **Inference** | Privacy router intercept | Sensitive data routed to local NIM (NEMOCLAW_MODEL), never to cloud |
| **Communication** | Typed contract validation | Inter-claw messages validated against policy before delivery |

## Filesystem Mounts

### Mount Structure

> **Note:** All claws share a single NemoClaw sandbox. Per-claw isolation is enforced by path conventions and the Python orchestrator, not separate sandbox instances. `/sandbox` is writable at the container mount level; the only read-only exception is `/sandbox/.openclaw/` (root-owned, immutable). Writable claw data is under `/sandbox/.openclaw-data/milimo/claws/`.

```
/sandbox/.openclaw-data/milimo/claws/
├── content/ # Content Claw — brand assets, drafts, style guides
├── ops/ # Ops Claw — client records, project histories
├── analytics/ # Analytics Claw — performance data, reports
│ └── reports/ # Read-only cross-mount for all claws
├── finance/ # Finance Claw — invoices, revenue, pricing
├── build/ # Build Claw — codebase, secrets, deploy configs
│ ├── repo/ # Codebase (GitHub mount)
│ ├── context/ # Sprint plans, error patterns, cost tracking
│ ├── prs/ # PR state tracking
│ ├── deployments/ # Deploy state
│ ├── docs/ # Changelog, API docs, devlog
│ ├── memory/ # Filesystem memory pattern
│ └── logs/ # Operational logs
└── assistant/ # Assistant Claw — sessions, context, logs
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
/sandbox/.openclaw-data/milimo/claws/analytics/reports/weekly-intelligence.json
```

This file must be configured as a read-only mount in **all six** claw sandbox policies. It's the only file in the entire mesh that all claws can read directly without a message contract.

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
| [[assistant-lucy\|Assistant]] | Inference proxy (`inference.local`), GitHub, Vercel, Sentry, Stripe (read-only) |

> **Note:** The sandbox never calls `api.telegram.org` directly. Telegram is managed by OpenShell's channel messaging subsystem — the L7 proxy intercepts and delivers messages to the agent.

### Network Policy Files

Policy files define allowed network access:

```yaml
# Example: content-sandbox.yaml
network_policies:
  twitter_api:
    endpoints:
    - host: api.twitter.com
      port: 443
      protocol: rest
      enforcement: enforce
      access: read-write
    binaries:
    - { path: /usr/bin/python3 }
```

## Process Isolation

### NemoClaw Process Controls

NemoClaw enforces process isolation through multiple mechanisms (seccomp filtering is provided by OpenShell internally, not configured by NemoClaw):

- **`ulimit -u 512`** — Limits max processes per user, preventing fork bombs
- **`--cap-drop=ALL`** — Drops all Linux capabilities at the container runtime level
- **Entrypoint `capsh` drops** — The entrypoint additionally drops: `cap_net_raw`, `cap_dac_override`, `cap_sys_chroot`, `cap_fsetid`, `cap_setfcap`, `cap_mknod`, `cap_audit_write`, `cap_net_bind_service`
- **Retained capabilities** — 5 capabilities kept for `gosu` user switching: `cap_chown`, `cap_setuid`, `cap_setgid`, `cap_fowner`, `cap_kill`
- **`no-new-privileges`** — Prevents privilege escalation via setuid/setgid binaries (`PR_SET_NO_NEW_PRIVS` via `prctl()`)
- **Non-root sandbox user** — All processes run as `sandbox:sandbox` (UID 999), never root
- **PATH hardening** — Restricted PATH prevents executing arbitrary binaries
- **OpenShell seccomp** — OpenShell applies seccomp filters internally for `PR_SET_NO_NEW_PRIVS`; this is not a NemoClaw-configured layer

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
  - /sandbox/.openclaw-data/milimo/claws/analytics/reports # Cross-mount
  read_write:
  - /sandbox/.openclaw-data/milimo/claws/content

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
      protocol: rest
      enforcement: enforce
      access: read-write
    binaries:
    - { path: /usr/bin/python3 }
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
- Process limits and capability drops are enforced

## Related Pages

- [[policy-overview]] — Policy structure details
- [[network-egress]] — Network policy configuration
- [[mesh-coordinator]] — Inter-sandbox communication
- [[privacy-router]] — Inference isolation
- [[assistant-lucy]] — Assistant Claw sandbox details
