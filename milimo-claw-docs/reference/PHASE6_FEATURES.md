# Phase 6: Enterprise & University Tier - Features

> **NemoClaw Compliance Notice (2026-04-28)**
>
> This spec has been updated to comply with NVIDIA NemoClaw v0.0.28 and OpenShell v0.0.26 as documented at [docs.nvidia.com/nemoclaw/latest/](https://docs.nvidia.com/nemoclaw/latest/) and [docs.nvidia.com/openshell/latest/](https://docs.nvidia.com/openshell/latest/).
>
> **Key changes applied:**
>
> - **Filesystem paths migrated** from `/sandbox/<role>/` to `/sandbox/.openclaw-data/milimo/claws/<role>/` — NemoClaw's Landlock LSM makes `/sandbox/` root read-only; only `/sandbox/.openclaw-data/`, `/sandbox/.nemoclaw/`, and `/tmp/` are writable (see [Sandbox Hardening](https://docs.nvidia.com/nemoclaw/latest/deployment/sandbox-hardening.html)).
> - **Shared analytics report path** updated from `/sandbox/analytics/reports/` to `/sandbox/.openclaw-data/milimo/claws/analytics/reports/` — same Landlock compliance reason.
> - **`/sandbox/.openclaw/`** is read-only — contains immutable gateway config (auth tokens, CORS); agents cannot modify it.
> - **`/sandbox/.openclaw/workspace/`** is the canonical workspace files location (SOUL.md, USER.md, AGENTS.md, MEMORY.md, etc.) — persisted via symlink into `.openclaw-data/`.
> - **`/sandbox/.local/bin/milimo` does NOT exist** — was referenced in old policy YAMLs; Milimo bridge CLI is at `python3 /sandbox/.openclaw-data/milimo/orchestrator/bridge_cli.py`.
> - **Credentials** are stored in the OpenShell gateway store only — NOT in `~/.nemoclaw/credentials.json` (which is legacy, auto-migrated and deleted on `nemoclaw onboard`). See [Credential Storage](https://docs.nvidia.com/nemoclaw/latest/security/credential-storage.html).
> - **Network policy** uses `protocol: rest` with `enforcement` and `access`/`rules`/`deny_rules` for L7 HTTP inspection — see [OpenShell Policy Schema](https://docs.nvidia.com/openshell/latest/reference/policy-schema.html).
> - **GitHub is NOT in the baseline policy** — it's a preset only, applied via `nemoclaw <name> policy-add github` or during onboarding tier selection.
> - **`include_workdir: false`** in filesystem_policy — NemoClaw default; `/sandbox/` root is read-only.
> - **Policy tiers**: Restricted / Balanced (default) / Open — determine which presets are included at onboarding.
> - **`openshell policy set` REPLACES** the live policy (does NOT merge) — use `nemoclaw <name> policy-add` for non-destructive merging.
> - **Sandbox process** runs as `sandbox:sandbox` (UID 999), not root — `run_as_user: root` is rejected by OpenShell.
> - **`/sandbox/.openclaw/openclaw.json`** is read-only at runtime — `openclaw channels remove` cannot modify it from inside the sandbox; use `nemoclaw <name> channels remove` from the host.
>
> If this spec conflicts with the official NemoClaw/OpenShell docs, the official docs win. See the [Ground Truth Hierarchy](../../.agents/AGENTS.md) for resolution rules.

**Version:** 1.0
**Date:** March 2026
**Status:** Implemented

---

## Overview

Phase 6 adds multi-tenant architecture for white-label deployment to universities, accelerators, and enterprise organizations. Each tenant operates in isolation with custom branding, user management, and resource allocation.

---

## 6.1 Multi-Tenant Architecture

### Tenant Isolation

| Layer | Isolation Method | Description |
|-------|-----------------|-------------|
| Application | Tenant ID in JWT | All requests scoped to tenant |
| Database | Tenant column | Row-level security per tenant |
| Storage | Tenant-prefixed paths | `tenants/{tenant_id}/files` |
| Cache | Tenant-namespaced keys | `tenant:{id}:key` |
| Queue | Tenant-specific topics | `tenant.{id}.events` |

### Tenant Plans

| Plan | Max Squads | Max Users/Squad | Storage | API Calls/Month |
|------|------------|-----------------|---------|-----------------|
| Trial | 3 | 3 | 1 GB | 10,000 |
| Starter | 10 | 5 | 10 GB | 100,000 |
| Professional | 50 | 10 | 50 GB | 1,000,000 |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited |

### Files

```
milimo-server/src/tenants/
├── manager.ts        # Tenant CRUD operations
├── provisioning.ts   # Resource provisioning
└── limits.ts         # Limit enforcement
```

---

## 6.2 Admin Dashboard

### Dashboard Components

| Component | Description |
|-----------|-------------|
| `Overview.tsx` | Tenant overview - active squads, users, storage |
| `Squads.tsx` | Squad management - create, configure, delete |
| `Analytics.tsx` | Usage analytics - metrics, performance reports |
| `Cohorts.tsx` | Cohort management - bulk creation, progress |

### Branding Components

| Component | Description |
|-----------|-------------|
| `Logo.tsx` | Logo configuration - upload custom logo |
| `Theme.tsx` | Theme configuration - colors, typography |

### Template Management

| Component | Description |
|-----------|-------------|
| `TemplateManager.tsx` | Blueprint template library - CRUD operations |

### Files

```
milimo-admin/src/
├── dashboard/
│   ├── Overview.tsx
│   ├── Squads.tsx
│   ├── Analytics.tsx
│   └── Cohorts.tsx
├── branding/
│   ├── Logo.tsx
│   └── Theme.tsx
└── templates/
    └── TemplateManager.tsx
```

---

## 6.3 Cohort Management

### Cohort Template Schema

Cohort templates define bulk squad creation:

```json
{
  "name": "Fall 2026 Cohort",
  "template": "campus-ai-tool",
  "squads": [
    {
      "name": "Team Alpha",
      "members": [
        {"email": "student1@university.edu", "role": "build"},
        {"email": "student2@university.edu", "role": "content"}
      ]
    }
  ]
}
```

### Role Assignment

Automatic role assignment based on:

- Skill matching (e.g., programming → build role)
- Preference consideration
- Experience history
- Template requirements

### Files

```
milimo-blueprint/
├── schemas/
│   └── cohort.json
└── orchestrator/
    ├── cohort_creator.py
    └── role_assigner.py
```

---

## API Reference

### Tenant Management

```typescript
import { TenantManager } from './tenants/manager';

const manager = new TenantManager();

// Create tenant
const tenant = await manager.createTenant({
  name: 'Stanford Entrepreneurship',
  slug: 'stanford-ent',
  type: 'university',
});

// Get tenant
const tenant = await manager.getTenant('tenant_123');

// Update tenant
await manager.updateTenant('tenant_123', {
  branding: { primaryColor: '#FF5500' },
});

// Delete tenant
await manager.deleteTenant('tenant_123');
```

### Cohort Creation

```python
from orchestrator.cohort_creator import CohortCreator

creator = CohortCreator(tenant_id='stanford-ent')

# Create cohort from template
cohort = await creator.create_from_template({
    'name': 'Fall 2026 Cohort',
    'template': 'campus-ai-tool',
    'squads': [
        {'name': 'Team Alpha', 'members': [...]},
        {'name': 'Team Beta', 'members': [...]},
    ]
})

# Track progress
progress = creator.get_progress(cohort.cohort_id)
print(f"Created {progress.squads_created}/{progress.total_squads} squads")
```

---

## Usage Analytics

### Metrics Collected

| Category | Metrics |
|----------|---------|
| Usage | Active squads, active users, API calls |
| Performance | Average response time, error rate, uptime |
| Engagement | Daily active users, session duration |
| Storage | Bytes used, file count, growth rate |

### Report Generation

```typescript
// Get usage summary
const summary = tenantLimitsEnforcer.getUsageSummary(tenant);

// Check alerts
const alerts = tenantLimitsEnforcer.checkAlerts(tenant);
```

---

## White-Label Configuration

### Branding Options

| Element | Customization |
|---------|--------------|
| Logo | Upload custom logo (SVG/PNG) |
| Colors | Primary, secondary, accent colors |
| Typography | Font family selection |
| Favicon | Custom favicon |
| Email Templates | Custom email branding |
| Mobile App | White-labeled React Native build |

### Custom Domain

```bash
milimo-admin domains add milimo.stanford.edu
milimo-admin domains ssl milimo.stanford.edu --enable
```

---

## References

- [Multi-Tenant Architecture](../../docs/technical/multi-tenant.md)
- [Phase 6 Status Report](../reports/PHASE_6_STATUS.md)
- [Implementation Plan](../reports/MILIMO_CLAW_IMPLEMENTATION_PLAN.md)
