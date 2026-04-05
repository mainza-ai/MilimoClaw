# MilimoClaw Web Application — Complete Requirements Specification

## Document Purpose

This document consolidates every piece of information needed to design and build a web-based UI/UX for MilimoClaw. It covers the War Room, approval workflows, dashboard surfaces, user roles, API contracts, mobile parity, admin panel, message contracts, and the full system architecture.

---

## 1. System Overview

### What MilimoClaw Is

A multi-agent autonomous hustle platform built on NVIDIA NemoClaw. "Milimo" is a Tonga word from Zambia meaning "works, tasks, labour." Tagline: **"The milimo never stops. Work. Without working."**

### Architecture: 5 Specialized Claws

| Claw | Mount | Role | Status |
|---|---|---|---|
| **Content** 🎨 | `/sandbox/content` | Creative output — social posts, campaigns, email copy, content calendars | ✅ Functional |
| **Ops** 📋 | `/sandbox/clients` | Account/project manager — inquiry triage, client lifecycle, deadline tracking | ✅ Functional |
| **Analytics** 📊 | `/sandbox/analytics` | Intelligence layer — weekly reports, anomaly detection, opportunity scoring | ✅ Functional |
| **Finance** 💰 | `/sandbox/finance` | Pricing, invoices (2-stage approval), Stripe monitoring, revenue summaries | ✅ Functional |
| **Build** 🔧 | `/sandbox/build` | Engineering — GitHub issues, sprint planning, code gen, PRs, deploys | ✅ Functional |

### Deployment Model

- MilimoClaw runs **inside the OpenShell secure sandbox** provisioned by NemoClaw
- The sandbox provides Landlock (filesystem restrictions), seccomp (syscall filtering), netns (network isolation)
- The web application connects to the **milimo-server** Fastify API running outside the sandbox
- All claw communication happens via typed message contracts over the OpenShell gateway (Unix socket)

---

## 2. War Room — Primary Operator Interface

### 2.1 Purpose

The War Room is the central oversight layer where the human operator reviews, approves, blocks, or edits actions queued by all 5 claws. It is **not a sandbox** — it sits above the mesh as the human decision point.

### 2.2 Current TUI Layout (Terminal)

```
┌─ WAR ROOM ─────────────────┬─ CLAW HEALTH ──────────────┐
│                            │ CONTENT ● active 11 tools  │
│ 🔴 HOLD BUILD CLAW         │ OPS ● active 8 tools       │
│ PR #52 ready to merge      │ ANALYTICS ● active 9 tools │
│ [A]pprove [B]lock          │ FINANCE ● active 7 tools   │
│                            │ BUILD ● active 12 tools    │
│ 🟡 REVIEW OPS CLAW         ├────────────────────────────┤
│ Proposal for @ArcLight     │ Revenue this week          │
│ $3,200                     │ $4,240 ↑18%                │
│ [A]pprove [E]dit [B]lock   │ 3 paid · 1 pending         │
│                            ├────────────────────────────┤
│ ✓ AUTO CONTENT CLAW        │ Evolution Log              │
│ post_047 published ✓       │ BUILD: PR enforcer built   │
│                            │ 5 days ago · +12% approval │
└────────────────────────────┴────────────────────────────┘
```

### 2.3 Web War Room Requirements

#### Left Panel — Action Queue

| Feature | Detail |
|---|---|
| **Live action feed** | Real-time stream of every claw's activity, polling every 3 seconds |
| **Action cards** | Each card shows: claw source, action type, summary, priority badge, time ago, confidence %, risk level |
| **Expandable details** | Click to expand full action content, payload, metadata |
| **Action buttons** | Approve (A), Block/Reject (B), Edit/Hold (E) — per mode |
| **Filtering** | Filter by claw, mode (HOLD/REVIEW/AUTO), priority, date range |
| **Sorting** | By priority, timestamp, claw, action type |
| **Search** | Full-text search across action summaries and content |
| **Bulk actions** | Select multiple actions → approve all, block all |
| **Empty state** | "All caught up! No pending actions." with refresh button |

#### Right Panel — Dashboard

| Widget | Data Source | Content |
|---|---|---|
| **Claw Health** | `/api/v1/status/claws` | Per-claw status (active/inactive), tool count, last heartbeat |
| **Revenue Snapshot** | Finance claw data | Pipeline value, outstanding invoices, monthly earnings, paid vs pending |
| **Evolution Log** | Evolution cycle data | Last evolution timestamp, tools built, approval rate changes |
| **Activity Feed** | `/api/v1/status/activity` | Recent approved/vetoed actions with timestamps |
| **Rate Limit Status** | `/api/v1/status/rate-limit` | Daily/burst usage vs limits, tier info |

#### Keyboard Shortcuts (Web Parity)

| Key | Action |
|-----|--------|
| `↑`/`↓` | Navigate through actions |
| `Enter` | Select/expand action |
| `A` | Approve selected action |
| `B` | Block (reject) selected action |
| `E` | Edit (hold) selected action |
| `R` | Refresh queue |
| `H` | Toggle help overlay |
| `F` | Toggle Finals Mode |

#### Color Coding

| Color | Mode | Meaning |
|---|---|---|
| 🔴 Coral | HOLD / VETO | Requires manual approval — action is paused |
| 🟡 Amber | REVIEW | Recommended for review before execution |
| 🟢 Teal | AUTO | Auto-approval eligible — runs and logs |

### 2.4 WebSocket Real-Time Updates

- **Endpoint:** `ws://host:3000/ws?token=<jwt>`
- **Events:** `ping`/`pong` (heartbeat), `subscribe` (channel-based subscriptions)
- **Channels:** `actions`, `claws`, `mesh`, `notifications`
- **Max payload:** 1MB
- **Reconnection:** Automatic with exponential backoff

---

## 3. Approval Workflows

### 3.1 Four Approval Modes

| Mode | Behavior | Use Case |
|---|---|---|
| **AUTO** | Claw acts immediately, logs for morning digest | Low-stakes routine actions, finance summaries |
| **REVIEW** | Queued for human approval before execution | Client communications, PR creation, draft content |
| **HOLD** | Paused, requires explicit squad confirmation | PR merge, deployment, large invoices |
| **VETO** | Any squad member can block, requires re-vote | Invoices >$500, payment execution |

### 3.2 Build Claw Two-Stage Approval (Critical Correctness)

This is the most complex approval flow and must be implemented exactly:

```
Issue Created → Code Generated → PR Created
                                      ↓
                              REVIEW approval
                                      ↓
                              PR moves to HOLD (NOT merged)
                                      ↓
                              HOLD released by operator
                                      ↓
                              PR merges to main
                                      ↓
                              Deploy triggered (SEPARATE HOLD)
                                      ↓
                              Deploy HOLD released
                                      ↓
                              Deployment executes
```

**Key rule:** REVIEW approval does NOT merge. Merge requires a separate HOLD release. Deploy is its OWN separate HOLD — merge ≠ deploy.

### 3.3 Finance Claw Two-Stage Invoice Approval

```
Invoice Generated → Stage 1 Approval → Stage 2 Approval → Transmission
```

Two separate operator approvals required before any invoice is transmitted.

### 3.4 Content Claw Review Gating

Nothing publishes without operator REVIEW approval. Drafts are queued for review.

### 3.5 Ops Claw Pricing Gate

`pricing_query` MUST be sent and `pricing_response` received BEFORE `project_brief` is sent to any creative claw.

### 3.6 Analytics Claw Observer Pattern

Analytics observes everything, acts on nothing directly. Shared `weekly-intelligence.json` feeds all claws.

### 3.7 Rate Limiting

| Tier | Daily Limit | Burst Limit | Burst Window |
|------|-------------|-------------|--------------|
| Free | 10 | 3 | 1 hour |
| Pro | Unlimited | N/A | N/A |

### 3.8 Escalation Rules

Configurable thresholds per claw:
- Invoices >$500 require squad-wide approval
- Production deployments require squad lead approval
- Blueprint marketplace listings require review

---

## 4. API Endpoints (milimo-server)

### 4.1 Authentication

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/token` | Generate JWT (requires `squad_id`, `device_id`) | None |
| `POST` | `/api/v1/auth/refresh` | Refresh token (rotates refresh token) | Refresh token |
| `GET` | `/api/v1/auth/verify` | Verify current token | JWT |
| `POST` | `/api/v1/auth/logout` | Invalidate all refresh tokens | JWT |

### 4.2 Pending Actions (War Room)

| Method | Endpoint | Auth | Rate Limit | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/pending` | JWT | 100/min | List pending actions (paginated) |
| `GET` | `/api/v1/pending/:id` | JWT | — | Get action details |
| `POST` | `/api/v1/pending` | Internal | — | Create pending action (claw → server) |
| `POST` | `/api/v1/pending/:id/approve` | JWT | 20/min | Approve action (optional `biometric_verified`, `notes`) |
| `POST` | `/api/v1/pending/:id/veto` | JWT | 20/min | Veto action (requires `reason`) |
| `GET` | `/api/v1/pending/:id/decision` | JWT | — | Get decision history |

### 4.3 Status & Health

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/status` | JWT | War Room status (mesh, pending count, rate limit) |
| `GET` | `/api/v1/status/claws` | JWT | Per-claw health (role, status, region, heartbeat, actions_today) |
| `GET` | `/api/v1/status/mesh` | JWT | Mesh health (regional status, latency matrix) |
| `GET` | `/api/v1/status/rate-limit` | JWT | Rate limit status (tier, daily/burst usage) |
| `GET` | `/api/v1/status/activity` | JWT | Activity log (approved/vetoed actions) |

### 4.4 Webhooks

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/webhooks/stripe` | Stripe V1 webhook (checkout, payouts, account updates) |
| `POST` | `/webhooks/stripe/v2` | Stripe V2 thin event webhook |

### 4.5 Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server health check (no auth) |

### 4.6 WebSocket

- **Endpoint:** `/ws?token=<jwt>`
- **Events:** `ping`/`pong`, `subscribe` (channel-based)

---

## 5. User Roles and Permissions

### 5.1 Squad Model

- Squad size: **2–6 members**
- Each member owns one or more claw roles
- **No hierarchy** — every member has War Room access and equal approval weight by default
- Optional **Squad Lead** designation — required for Finance actions above threshold, Build production deployments, Blueprint Marketplace listings

### 5.2 Solo Mode

Single operator runs all 5 claws on one machine. No role selection — all claws active simultaneously.

### 5.3 Tier-Based Permissions

| Plan | Max Squads | Max Users/Squad | Max Claws/Squad | Storage | API Calls/Month |
|------|-----------|-----------------|-----------------|---------|-----------------|
| Trial | 3 | 3 | 3 | 1 GB | 10,000 |
| Starter | 10 | 5 | 4 | 10 GB | 100,000 |
| Professional | 50 | 10 | 5 | 50 GB | 1,000,000 |
| Enterprise | Unlimited | Unlimited | 5 | Unlimited | Unlimited |

### 5.4 Multi-Tenant Isolation

- Application: Tenant ID in JWT
- Database: Row-level security per tenant
- Storage: Tenant-prefixed paths
- Cache: Tenant-namespaced keys
- Queue: Tenant-specific topics

---

## 6. Mobile App Parity (React Native Reference)

### 6.1 Current Mobile Structure

| Screen | Purpose |
|---|---|
| **PendingList** | FlatList of ActionCards, pull-to-refresh, empty state |
| **ActionDetail** | Full action details, approve/veto with biometric prompt |
| **Settings** | Notifications toggle, biometric toggle, offline mode, logout |

### 6.2 ActionCard Component

Each card displays:
- Claw role (Content/Ops/Analytics/Finance/Build)
- Action type (draft_ready, invoice_ready, etc.)
- Risk badge (low/medium/high)
- Confidence percentage
- Time ago
- Approve/Veto buttons

### 6.3 Push Notification Types

| Type | Title | Priority |
|---|---|---|
| `pending_action` | "Action Requires Approval" | High if risk=high |
| `action_approved` | "Action Approved" | Normal |
| `action_vetoed` | "Action Vetoed" | Normal |
| `claw_offline` | "Claw Offline" | High |
| `rate_limit_warning` | "Rate Limit Warning" | High |

### 6.4 Web App Should Include

- All mobile features plus the full War Room dashboard
- Push notification preferences page
- Biometric authentication settings (if WebAuthn is supported)
- Offline mode indicator with queued actions

---

## 7. Message Contracts

### 7.1 Core Data Model

```python
@dataclass
class ClawMessage:
    sender_role: str       # content, ops, analytics, finance, build
    recipient_role: str    # content, ops, analytics, finance, build, war_room
    message_type: str      # typed contract (see below)
    payload: dict
    squad_id: str
    message_id: str        # auto-generated UUID
    timestamp: str         # ISO 8601
```

### 7.2 Valid Message Types (32 defined)

| Type | Sender → Recipient | Priority | Requires Approval |
|---|---|---|---|
| `brief` / `project_brief` | Ops → Content/Build | REVIEW | Yes |
| `query` / `pricing_query` | Various | AUTO | No |
| `response` / `pricing_response` | Various | AUTO | No |
| `signal` / `performance_signal` | Various | AUTO | No |
| `deliverable` / `deliverable_complete` | Content → Ops | AUTO | No |
| `summary` / `finance_summary` / `revenue_summary` | Various | AUTO | No |
| `draft_ready` | Content → War Room | REVIEW | Yes |
| `invoice_ready` | Finance → Ops | REVIEW | Yes |
| `payment_overdue` | Finance → Ops | REVIEW | Yes |
| `overdue_alert` | Finance → War Room | REVIEW | Yes |
| `feature_brief` | Ops → Build | REVIEW | Yes |
| `deploy_complete` | Build → Ops | AUTO | No |
| `client_health_alert` | Analytics → Ops | REVIEW | Yes |
| `tool_proposal` | Any → Any | — | — |

### 7.3 SLA Timers

| Message Type | SLA |
|---|---|
| `brief_acknowledged` | 5 min |
| `content_performance_response` | 2 min |
| `behavior_query_response` | 2 min |
| `pricing_query` | 10 min |
| `feature_brief_acknowledged` | 10 min |

### 7.4 Validation Pipeline

1. Validate sender role
2. Validate recipient role
3. Validate message type against `VALID_MESSAGE_TYPES`
4. Check message matrix authorization (sender→recipient→message_type)
5. Validate payload against schema (required fields, sender/recipient role match)

Messages not in the matrix are **dropped and logged**.

---

## 8. Admin Dashboard (Multi-Tenant)

### 8.1 Purpose

Management interface for universities, accelerators, and enterprise organizations running multiple squads.

### 8.2 Components

| Component | Purpose |
|---|---|
| **Tenant Overview** | Active squads/users, storage, API calls, utilization bars, recent activity table |
| **Squad Management** | Search/filter, create/suspend/activate/delete squads, template selection |
| **Analytics** | Time-range charts (Area/Line/Bar), squad performance table, CSV/PDF export |
| **Cohort Management** | Bulk squad deployment for programs (1–100 squads), progress tracking, error reporting |
| **Template Manager** | Blueprint template CRUD, categories (agency/saas/ecommerce/content/custom), role selection, public/private visibility, usage tracking |
| **Theme Config** | Primary/secondary color pickers, font selection, live preview |
| **Logo Config** | Logo upload (PNG/SVG/JPG, max 5MB), preview, remove |

### 8.3 Tenant Types

`university`, `enterprise`, `accelerator`, `custom`

### 8.4 Cohort Creation Flow

1. Admin creates cohort with name, template, and number of squads (1–100)
2. System auto-generates squad names (`{cohortName} - Team {N}`)
3. Progress tracked: squads created/pending/failed, members invited/joined
4. Error reporting per squad

---

## 9. Self-Evolution Cycle

Every Sunday at 02:00, each claw runs a 5-stage pipeline:

```
OBSERVE → IDENTIFY → PROPOSE → BUILD → DEPLOY
```

New tools are built and deployed automatically based on performance data. The web app should display:

- Last evolution timestamp per claw
- Tools built during last cycle
- Approval rate changes
- Performance metrics before/after evolution

---

## 10. Security Requirements

### 10.1 Authentication

- JWT-based authentication with refresh token rotation
- WebSocket connections require JWT via query parameter
- Refresh tokens stored and validated (not just any UUID)
- Rate limiting per endpoint (100 req/min general, 20/min for approve/veto)

### 10.2 CORS

- Restricted to specific origins via `ALLOWED_ORIGINS` env var
- NOT `origin: true` (allows all origins)

### 10.3 Mesh Encryption

- AES-256-GCM with HKDF key derivation (not byte-cycling)
- Fallback file messages encrypted at rest

### 10.4 Kubernetes Security

- Capabilities: `drop: ALL`, `add: [SYSLOG]` only
- No `SYS_ADMIN`, `NET_ADMIN`, or `SYS_PTRACE`

---

## 11. Technical Stack Recommendations

### Frontend

| Layer | Recommendation | Rationale |
|---|---|---|
| **Framework** | Next.js 14 (App Router) | SSR for initial load, API routes, React ecosystem |
| **UI Library** | shadcn/ui + Tailwind CSS | Accessible, themeable, matches dark theme (#1a1a2e) |
| **State Management** | Zustand or React Query | Lightweight, server-state focused |
| **Real-time** | WebSocket client with auto-reconnect | Matches existing `/ws` endpoint |
| **Charts** | Recharts or Tremor | Revenue, analytics, performance charts |
| **Tables** | TanStack Table | Sorting, filtering, pagination for action queue |
| **Forms** | React Hook Form + Zod | Validation matching backend schemas |
| **Auth** | JWT stored in httpOnly cookies | Secure, no XSS risk |

### Backend (milimo-server — existing)

| Layer | Current | Notes |
|---|---|---|
| **Framework** | Fastify (TypeScript) | Already implemented |
| **Auth** | JWT with refresh tokens | Implemented, needs DB integration |
| **Payments** | Stripe Connect | Implemented, needs production credentials |
| **Notifications** | APNs + FCM | Implemented, needs device token management |
| **Database** | Not yet integrated | Needs PostgreSQL or similar |

### Mobile (milimo-mobile — existing scaffold)

| Layer | Current | Status |
|---|---|---|
| **Framework** | React Native 0.73.0 | Scaffold only, mock data |
| **Navigation** | React Navigation | Stack configured |
| **Auth** | Mock useAuth hook | Needs real implementation |
| **API Client** | Hardcoded URL + mock token | Needs real integration |

---

## 12. Page/Route Map

### Public Routes

| Route | Description |
|---|---|
| `/` | Landing page |
| `/login` | Squad login (squad_id + device_id → JWT) |
| `/register` | New squad registration (if self-service enabled) |

### Authenticated Routes (War Room)

| Route | Description |
|---|---|
| `/dashboard` | War Room — main view (action queue + dashboard) |
| `/dashboard/actions` | Full action queue with filters |
| `/dashboard/actions/:id` | Action detail view |
| `/dashboard/claws` | Per-claw health and configuration |
| `/dashboard/evolution` | Evolution cycle status and history |
| `/dashboard/revenue` | Financial overview (pipeline, invoices, earnings) |
| `/dashboard/activity` | Activity log (approved/vetoed actions) |
| `/settings` | User settings, notifications, preferences |
| `/settings/team` | Squad member management |

### Admin Routes (Multi-Tenant)

| Route | Description |
|---|---|
| `/admin` | Tenant overview |
| `/admin/squads` | Squad management (CRUD) |
| `/admin/analytics` | Cross-tenant analytics |
| `/admin/cohorts` | Cohort management |
| `/admin/templates` | Blueprint template management |
| `/admin/branding` | Theme and logo configuration |

---

## 13. Key Design Decisions

1. **Dark theme by default** — The existing mobile app uses `#1a1a2e` background. The web app should match.
2. **Mobile-first responsive** — The War Room TUI is dense; the web version needs progressive disclosure (collapse details, expand on demand).
3. **Real-time by default** — WebSocket connection for live action feed, with polling fallback.
4. **Approval actions are irreversible** — Once approved/vetoed, the decision is logged and cannot be undone (audit trail).
5. **Offline support** — Queue approval actions locally when offline, sync when connection restored.
6. **Accessibility** — Keyboard shortcuts must work, color-blind safe alternatives to coral/amber/teal.

---

## 14. Known Limitations & Gaps

| Area | Current State | Gap |
|---|---|---|
| **milimo-server database** | In-memory stores | Needs PostgreSQL for production |
| **milimo-mobile** | Mock data, hardcoded URL | Needs real API integration |
| **Stripe credentials** | Placeholder keys | Needs production Stripe Connect setup |
| **OpenAPI spec** | None | Needed for frontend code generation |
| **Request validation** | No JSON schema on Fastify routes | Needs schema validation |
| **Pagination** | Not implemented on fetch endpoints | Needed for large action queues |
| **Error response format** | Inconsistent | Needs standardization |
| **Biometric auth (web)** | Not implemented | Consider WebAuthn for parity with mobile |

---

## 15. File Paths Reference

| Component | Path |
|---|---|
| TypeScript plugin | `milimo/src/` |
| Python orchestrator | `milimo-blueprint/orchestrator/` |
| Build Claw modules | `milimo-blueprint/orchestrator/build/` |
| Role blueprints | `milimo-blueprint/roles/` |
| Sandbox policies | `milimo-blueprint/policies/` |
| Message contracts | `milimo-blueprint/orchestrator/contracts.py` |
| Fastify API server | `milimo-server/src/` |
| React Native app | `milimo-mobile/src/` |
| Admin dashboard | `milimo-admin/src/` |
| Specifications | `milimo-claw-docs/` |
| Install script | `install.sh` |
| Dockerfile | `Dockerfile` |
| Kubernetes manifests | `k8s/` |
