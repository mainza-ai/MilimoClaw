# Multi-Tenant Architecture

**Version:** 1.0
**Date:** March 2026
**Status:** Implemented

---

## Overview

The Milimo Claw multi-tenant architecture enables white-label deployment for universities, accelerators, and enterprise organizations. Each tenant operates in isolation with custom branding, user management, and resource allocation.

---

## Architecture

### Tenant Isolation Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    MILIMO CLAW PLATFORM                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    TENANT LAYER                              ││
│  │                                                              ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         ││
│  │  │  Tenant A   │  │  Tenant B   │  │  Tenant C   │         ││
│  │  │  University │  │  Enterprise │  │  Accelerator│         ││
│  │  │  ─────────  │  │  ─────────  │  │  ─────────  │         ││
│  │  │  • 50 squads│  │  • 10 squads│  │  • 25 squads│         ││
│  │  │  • Custom   │  │  • Custom   │  │  • Custom   │         ││
│  │  │    branding │  │    branding │  │    branding │         ││
│  │  │  • Isolated │  │  • Isolated │  │  • Isolated │         ││
│  │  │    data     │  │    data     │  │    data     │         ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    SHARED SERVICES                           ││
│  │  • Authentication (JWT with tenant claims)                  ││
│  │  • Payment Processing (Stripe Connect per tenant)           ││
│  │  • Push Notifications (FCM/APNs per tenant)                 ││
│  │  • Blueprint Marketplace (tenant-specific catalogs)         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Data Isolation

| Layer | Isolation Method | Description |
|-------|-----------------|-------------|
| Application | Tenant ID in JWT | All requests scoped to tenant |
| Database | Tenant column | Row-level security per tenant |
| Storage | Tenant-prefixed paths | `tenants/{tenant_id}/files` |
| Cache | Tenant-namespaced keys | `tenant:{id}:key` |
| Queue | Tenant-specific topics | `tenant.{id}.events` |

---

## Tenant Configuration

### Tenant Schema

```typescript
interface Tenant {
  id: string;                    // Unique tenant identifier
  name: string;                  // Display name
  slug: string;                  // URL-safe identifier
  type: 'university' | 'enterprise' | 'accelerator' | 'custom';
  status: 'active' | 'suspended' | 'trial' | 'cancelled';
  
  // Branding
  branding: {
    logoUrl: string;
    primaryColor: string;
    secondaryColor: string;
    fontFamily?: string;
    customCss?: string;
    customDomain?: string;
  };
  
  // Limits
  limits: {
    maxSquads: number;
    maxUsersPerSquad: number;
    maxClawsPerSquad: number;
    maxStorageGb: number;
    maxApiCallsPerMonth: number;
    features: string[];
  };
  
  // Billing
  billing: {
    plan: 'trial' | 'starter' | 'professional' | 'enterprise';
    stripeCustomerId?: string;
    stripeSubscriptionId?: string;
    billingEmail: string;
  };
  
  // Settings
  settings: {
    ssoEnabled: boolean;
    ssoProvider?: 'saml' | 'oidc';
    ssoConfig?: object;
    customBlueprintsEnabled: boolean;
    whitelabeledMobileApp: boolean;
  };
  
  // Metadata
  createdAt: Date;
  updatedAt: Date;
  expiresAt?: Date;
}
```

### Tenant Limits

| Plan | Max Squads | Max Users/Squad | Storage | API Calls/Month |
|------|------------|-----------------|---------|-----------------|
| Trial | 3 | 3 | 1 GB | 10,000 |
| Starter | 10 | 5 | 10 GB | 100,000 |
| Professional | 50 | 10 | 50 GB | 1,000,000 |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited |

---

## Tenant Management

### Creating a Tenant

```typescript
import { TenantManager } from './tenants/manager';

const manager = new TenantManager();

const tenant = await manager.createTenant({
  name: 'Stanford Entrepreneurship',
  slug: 'stanford-ent',
  type: 'university',
  billing: {
    plan: 'enterprise',
    billingEmail: 'billing@stanford.edu',
  },
  limits: {
    maxSquads: 500,
    maxUsersPerSquad: 6,
    maxClawsPerSquad: 5,
    maxStorageGb: 500,
    maxApiCallsPerMonth: 10000000,
    features: ['sso', 'custom_blueprints', 'analytics', 'support'],
  },
});
```

### Provisioning Resources

```typescript
import { TenantProvisioning } from './tenants/provisioning';

const provisioning = new TenantProvisioning();

// Provision tenant infrastructure
await provisioning.provision(tenant.id, {
  database: true,
  storage: true,
  messaging: true,
  monitoring: true,
});

// Set up custom domain
await provisioning.configureDomain(tenant.id, 'milimo.stanford.edu');

// Configure SSO
await provisioning.configureSSO(tenant.id, {
  provider: 'saml',
  metadataUrl: 'https://sso.stanford.edu/metadata',
});
```

---

## Admin Dashboard

### Dashboard Components

```
milimo-admin/
├── src/
│   ├── dashboard/
│   │   ├── Overview.tsx       # Tenant overview
│   │   ├── Squads.tsx         # Squad management
│   │   ├── Analytics.tsx      # Usage analytics
│   │   └── Cohorts.tsx        # Cohort management
│   ├── branding/
│   │   ├── Logo.tsx           # Logo configuration
│   │   └── Theme.tsx          # Theme configuration
│   └── templates/
│       └── TemplateManager.tsx # Blueprint templates
├── package.json
└── tsconfig.json
```

### Dashboard Features

| Feature | Description |
|---------|-------------|
| Tenant Overview | Active squads, users, storage usage |
| Squad Management | Create, configure, delete squads |
| User Management | Invite users, assign roles, revoke access |
| Analytics | Usage metrics, performance reports |
| Cohort Management | Bulk squad creation, progress tracking |
| Billing | Subscription status, invoices, usage |

---

## Authentication & Authorization

### JWT Claims

```json
{
  "sub": "user_abc123",
  "tenant_id": "tenant_stanford",
  "role": "admin",
  "squads": ["squad_1", "squad_2"],
  "permissions": ["read", "write", "admin"],
  "iat": 1700000000,
  "exp": 1700086400
}
```

### Role Hierarchy

| Role | Permissions |
|------|-------------|
| Platform Admin | All tenants, all operations |
| Tenant Admin | All operations within tenant |
| Squad Admin | Manage single squad |
| Squad Member | Use assigned claw |
| Observer | Read-only access |

---

## Cohort Management

### Cohort Template Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "squads"],
  "properties": {
    "name": { "type": "string" },
    "description": { "type": "string" },
    "tenant_id": { "type": "string" },
    "template": { "type": "string" },
    "squads": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "members"],
        "properties": {
          "name": { "type": "string" },
          "members": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["email", "role"],
              "properties": {
                "email": { "type": "string", "format": "email" },
                "role": { "type": "string", "enum": ["content", "ops", "analytics", "finance", "build"] },
                "is_admin": { "type": "boolean" }
              }
            }
          }
        }
      }
    }
  }
}
```

### Bulk Squad Creation

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
        # ... 50 more squads
    ]
})

# Track progress
progress = await creator.get_progress(cohort.id)
print(f"Created {progress.squads_created} squads")
print(f"Pending: {progress.squads_pending}")
print(f"Failed: {progress.squads_failed}")
```

---

## Analytics & Reporting

### Metrics Collected

| Category | Metrics |
|----------|---------|
| Usage | Active squads, active users, API calls |
| Performance | Average response time, error rate, uptime |
| Engagement | Daily active users, session duration, actions/approvals |
| Storage | Bytes used, file count, growth rate |
| Billing | Revenue, churn rate, subscription status |

### Report Generation

```typescript
import { Analytics } from './admin/analytics';

const analytics = new Analytics(tenantId);

// Generate monthly report
const report = await analytics.generateReport({
  period: 'monthly',
  startDate: '2026-03-01',
  endDate: '2026-03-31',
  metrics: ['usage', 'performance', 'engagement'],
});

// Export to CSV
await analytics.exportCSV(report, 'march-2026-report.csv');
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

### Custom Domain Setup

```bash
# Add custom domain
milimo-admin domains add milimo.stanford.edu

# Configure DNS
# CNAME milimo.stanford.edu -> tenant.milimoclaw.com

# Enable SSL (automatic via Let's Encrypt)
milimo-admin domains ssl milimo.stanford.edu --enable
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `docs/technical/multi-tenant.md` | This documentation |
| `milimo-server/tenants/manager.ts` | Tenant CRUD operations |
| `milimo-server/tenants/provisioning.ts` | Resource provisioning |
| `milimo-server/tenants/limits.ts` | Limit enforcement |
| `milimo-admin/src/dashboard/*.tsx` | Admin UI components |
| `milimo-admin/src/branding/*.tsx` | Branding configuration |
| `milimo-blueprint/schemas/cohort.json` | Cohort schema |
| `milimo-blueprint/orchestrator/cohort_creator.py` | Bulk creation |
| `milimo-blueprint/orchestrator/role_assigner.py` | Role assignment |

---

## Security Considerations

### Tenant Isolation

- All API requests validated against tenant JWT claim
- Database queries automatically scoped to tenant
- File storage paths include tenant ID
- Cache keys namespaced by tenant

### Data Protection

- Tenant data encrypted at rest
- Separate encryption keys per tenant (optional)
- Audit logging for cross-tenant operations
- GDPR compliance for data deletion

### Access Control

- Platform admins require MFA
- Tenant admins can enforce password policies
- SSO integration for enterprise authentication
- Session timeout configurable per tenant

---

## References

- [Tenant Management API](#tenant-management)
- [Cohort Schema](#cohort-template-schema)
- [Admin Dashboard](#admin-dashboard)
