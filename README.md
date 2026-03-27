# 🦀 Milimo Claw

<p align="center">
  <img src="assets/Milimo-Claw.png" alt="Milimo Claw Logo" width="800" />
</p>

> *"Your friend group is a startup. Your laptops are the infrastructure. Your claws do the work."*

[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-Phase_6_Complete-brightgreen)](#roadmap)
[![Built on NemoClaw](https://img.shields.io/badge/built_on-NemoClaw-purple)](NemoClaw-README.md)

**Milimo Claw** is a multi-agent autonomous hustle platform built on [NVIDIA NemoClaw](NemoClaw-README.md). It turns a squad of college students — each running a NemoClaw sandbox on their RTX laptop — into a coordinated AI-powered business operation that runs 24/7.

> **On the name:** *Milimo* (mi-LEE-mo) is a Zambian name from the Tonga people, meaning **"works," "tasks," or "labour."**

---

## Table of Contents

- [Why Milimo Claw](#why-milimo-claw)
- [Architecture](#architecture)
- [The Five Claws](#the-five-claws)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Privacy & Security](#privacy--security)
- [Blueprint Economy](#blueprint-economy)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Why Milimo Claw

Current AI tools are assistants — you prompt them, they respond, they forget. They don't grow, they don't specialize, they don't run without you.

Milimo Claw is different:

| Feature | Traditional AI Tools | Milimo Claw |
|---|---|---|
| **Memory** | Resets every session | Blueprint versioning preserves everything |
| **Specialization** | Generic, one-size-fits-all | 5 role-specific claws, each with domain expertise |
| **Autonomy** | Reactive — waits for prompts | Proactive — claws operate 24/7 |
| **Growth** | Static | Self-evolving — claws build new tools weekly |
| **Collaboration** | Single-user | Squad mesh — distributed across laptops |
| **Privacy** | Data goes to cloud | Privacy router keeps sensitive data on-device |
| **Portability** | Locked to a platform | Blueprint export — your intelligence is forkable |

---

## Architecture

Milimo Claw exploits every layer of the NemoClaw stack for a consumer use case:

```
┌──────────────────────────────────────────────────────────────────┐
│                        MILIMO CLAW MESH                          │
│                                                                  │
│  [Laptop A]           [Laptop B]           [Laptop C]            │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │ CONTENT CLAW │     │   OPS CLAW   │     │  ANALYTICS   │     │
│  │ /sandbox/    │     │  /sandbox/   │     │    CLAW      │     │
│  │ content      │     │  clients     │     │  /sandbox/   │     │
│  │ OpenShell GW─┼─────┼─ OpenShell GW┼─────┼─ analytics   │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│          │                    │                     │             │
│          └────────────────────┼─────────────────────┘             │
│                               │                                  │
│                ╔══════════════╧══════════════╗                   │
│                ║   INTER-SANDBOX CHANNEL      ║                   │
│                ║  typed contracts · logged ·   ║                   │
│                ║  policy-enforced by OpenShell ║                   │
│                ╚══════════════╤══════════════╝                   │
│                               │                                  │
│                      [Laptop D]                                  │
│                 ┌──────────────┐                                 │
│                 │ FINANCE CLAW │                                 │
│                 │ /sandbox/    │                                 │
│                 │ finance      │                                 │
│                 └──────────────┘                                 │
│                                                                  │
│  ════════════════════════════════════════════════════════════════ │
│                        WAR ROOM (TUI)                            │
│          Every squad member · every pending action · one view    │
└──────────────────────────────────────────────────────────────────┘
```

**Key architectural primitives:**

| NemoClaw Layer | Milimo Claw Exploitation |
|---|---|
| Multi-sandbox mesh | Each claw = a department in your company |
| Inter-sandbox gateway | Typed contract messaging between claws |
| Landlock + seccomp | Kernel-level trust boundaries between squad members |
| Blueprint versioning | Institutional memory + tradeable intelligence |
| Inference routing | Privacy router — sensitive data never leaves the laptop |
| Operator TUI | War Room — squad-wide approval dashboard |

---

## The Five Claws

Every squad is assembled from 5 specialized claw roles. Creative/commerce squads typically run 4; tech squads unlock all 5.

| Claw | Role | Filesystem Mount | Key Capability |
|---|---|---|---|
| 🎨 **Content** | Creative output — posts, copy, campaigns | `/sandbox/content` | Platform-calibrated content with evolved style |
| 📋 **Ops** | Client lifecycle — intake to offboarding | `/sandbox/clients` | 24/7 client communications & project management |
| 📊 **Analytics** | Intelligence — performance, trends, signals | `/sandbox/analytics` | Weekly cross-claw intelligence reports |
| 💰 **Finance** | Revenue — invoicing, pricing, margins | `/sandbox/finance` | All data stays local — zero cloud inference |
| 🔨 **Build** | Engineering — code, PRs, deploys, monitoring | `/sandbox/build` | Autonomous PR cycle & production monitoring |

Each claw has its own **network egress policy**, **inference routing rules**, **inter-claw messaging policy**, and **self-evolution cycle**.

> See the full claw specification in [milimo-claw-docs/MILIMO_CLAW_PROJECT_DESCRIPTION.md](milimo-claw-docs/MILIMO_CLAW_PROJECT_DESCRIPTION.md#6-product-features).

---

## Quick Start

> **IMPORTANT**: On macOS and Linux, you must use native NemoClaw onboarding first. See [docs/QUICK_START.md](docs/QUICK_START.md) for the definitive setup guide.

### The 4-Phase Installation Flow

MilimoClaw requires proper NemoClaw infrastructure before use. The setup must occur in this exact order:

```
HOST MACHINE                         SANDBOX (Inside k3s)
    │                                   │
    ▼                                   │
┌─────────────────┐                     │
│ 1. Clean Slate  │                     │
│    (Optional)   │                     │
└────────┬────────┘                     │
         ▼                              │
┌─────────────────┐                     │
│ 2. Run Native   │                     │
│    NemoClaw     │                     │
│    Onboarding   │                     │
└────────┬────────┘                     │
         │                              │
         │  Creates:                    │
         │  ├─ Gateway container        │
         │  ├─ k3s cluster              │
         │  └─ Sandbox pod ────────────▶│
         │                              │
         │                              ▼
         │                     ┌─────────────────┐
         │                     │ 3. Build &      │
         │                     │    Install      │
         │                     │    MilimoClaw   │
         │                     └────────┬────────┘
         │                              │
         │                              ▼
         │                     ┌─────────────────┐
         │                     │ 4. Run Milimo   │
         │                     │    Onboarding   │
         └─────────────────────┴─────────────────┘
```

> **Full definitive guide**: [docs/QUICK_START.md](docs/QUICK_START.md)

---

## CLI Reference

### Squad Management

```bash
openclaw milimo init                              # Initialize squad / join mesh
openclaw milimo squad status [--json]              # Show topology & claw health
openclaw milimo squad finals-mode --duration 2w    # Activate Finals Mode
openclaw milimo squad resume                       # Resume from Finals Mode
```

### Blueprint Operations

```bash
openclaw milimo blueprint list [--json]            # List role blueprints & templates
openclaw milimo blueprint fork <source> [--into]   # Fork a public blueprint
openclaw milimo blueprint diff <v1> <v2>           # Compare blueprint versions
openclaw milimo blueprint publish [--name] [--price] # Export to marketplace
openclaw milimo blueprint rollback --to <version>  # Roll back to previous version
```

### War Room

```bash
openclaw milimo warroom [-o operator-name]         # Launch interactive dashboard
```

Inside the War Room TUI:

| Command | Action |
|---|---|
| `ls` | List pending actions in queue |
| `view <id>` | View details of a pending action |
| `approve <id>` | Approve an action |
| `veto <id>` | Reject an action |
| `hold <id>` | Defer an action |
| `feed` | View recent audit trail |
| `exit` | Leave the War Room |

### Chat Interface

```
/milimo status     — Squad status
/milimo roles      — Available claw roles
/milimo mesh       — Mesh topology
/milimo help       — Full command list
```

> Full CLI documentation: [milimo-claw-docs/CLI_REFERENCE.md](milimo-claw-docs/CLI_REFERENCE.md)

---

## Privacy & Security

Milimo Claw adds a **privacy router** on top of NemoClaw's existing security layers:

| Data Type | Routing Decision | Rationale |
|---|---|---|
| Client proposals, public drafts | ☁️ Cloud Nemotron 120B | Max quality for client-facing work |
| Internal comms, client contacts | 🔒 Local NIM | Business data stays on device |
| Financial records, payment details | 🔒 Local NIM only | Zero cloud touch for financial data |
| Personal notes, private context | 🔐 Local vLLM | Tightest isolation |
| Source code, API keys | 🔒 Local NIM | Code is IP — never leaves the machine |

**Security layers:**

| Layer | Protection | Enforcement |
|---|---|---|
| **Landlock** | Kernel-level filesystem isolation per claw | Cannot be bypassed by any instruction |
| **seccomp** | Blocks privilege escalation & dangerous syscalls | Locked at sandbox creation |
| **Network egress** | Per-claw API allowlists | Hot-reloadable at runtime |
| **Privacy router** | Sensitivity classification → routing | Transparent to the claw |
| **Typed contracts** | Inter-claw messages validated against policy | Unauthorized types dropped & logged |
| **War Room** | Human oversight for REVIEW/HOLD/VETO actions | All decisions audit-logged |

> Full details: [milimo-claw-docs/PRIVACY_AND_SECURITY.md](milimo-claw-docs/PRIVACY_AND_SECURITY.md)

---

## Blueprint Economy

Every claw's state is a **versioned blueprint** — a cryptographically verified artifact encoding months of accumulated intelligence:

- **Fork** — take someone's evolved blueprint as your starting point
- **Diff** — compare two blueprint versions side-by-side
- **Publish** — list your evolved blueprint on the marketplace
- **Rollback** — revert to a previous version
- **Handoff** — export your claw when graduating, the next person inherits your intelligence

> Full details: [milimo-claw-docs/BLUEPRINT_ECONOMY.md](milimo-claw-docs/BLUEPRINT_ECONOMY.md)

---

## Project Structure

```
MilimoClaw/
├── milimo/                      # Milimo Claw plugin (TypeScript)
│   ├── src/
│   │   ├── index.ts             # Plugin entry point
│   │   ├── cli.ts               # CLI registrar
│   │   ├── commands/            # init, squad, blueprint, warroom, health, slash
│   │   └── warroom/             # War Room TUI, approval engine, audit, rate limiter, health dashboard
│   ├── openclaw.plugin.json     # Plugin manifest
│   └── package.json
│
├── milimo-blueprint/ # Role blueprints & orchestrator (Python + YAML)
│   ├── roles/ # 5 claw role blueprints
│   ├── policies/ # 5 per-role sandbox policies
│   ├── templates/ # Pre-built squad templates
│   ├── orchestrator/ # Core engine components
│   │   ├── privacy_router.py # Sensitivity classification & routing
│   │   ├── contracts.py # Inter-claw message contracts
│   │   ├── mesh.py # Mesh coordinator with gateway support
│   │   ├── gateway_adapter.py # Multi-transport gateway (Unix/WS/File)
│   │   ├── mesh_relay.py # Relay client/server for NAT traversal
│   │   ├── region_detector.py # Region detection via IP/latency
│   │   ├── latency_monitor.py # Inter-region latency tracking
│   │   ├── mesh_failover.py # Failover & split-brain resolution
│   │   ├── health_collector.py # Health metric collection
│   │   ├── provenance_signer.py # Ed25519 blueprint signing
│   │   ├── provenance_verifier.py # Signature verification
│   │   ├── chain_validator.py # Provenance chain validation
│   │   ├── attestation_generator.py # Performance attestation generation
│   │   ├── tool_generator.py # LLM-based tool code generation
│   │   ├── tool_validator.py # AST security validation
│   │   ├── tool_sandbox.py # Isolated tool execution
│   │   └── evolution_cycle.py # Weekly self-evolution pipeline
│   ├── schemas/ # JSON schemas
│   │   ├── tool-spec.json # Tool specification schema
│   │   └── performance-attestation.json # Attestation schema
│   ├── prompts/ # LLM prompt templates
│   │   └── tool-generation/ # Tool generation prompts
│   ├── claw-schema.yaml # Blueprint schema definition
│   ├── mesh_config.yaml # Inter-claw message matrix
│   ├── privacy_policy.yaml # Default sensitivity routing policy
│   ├── regions.yaml # Multi-region configuration
│   └── rate-limits.yaml # Tier-based rate limit config
│
├── milimo-server/ # War Room API Server (TypeScript/Fastify)
│   ├── src/
│   │   ├── server.ts # Fastify server entry point
│   │   ├── routes/ # REST API routes
│   │   │   ├── auth.ts # Authentication routes
│   │   │   ├── pending.ts # Pending actions
│   │   │   ├── actions.ts # Approve/veto actions
│   │   │   └── status.ts # Squad status
│   │   ├── notifications/ # Push notifications
│   │   │   ├── firebase.ts # Firebase Cloud Messaging
│   │   │   └── apns.ts # Apple Push Notifications
│   │   ├── auth/ # Authentication
│   │   │   ├── jwt.ts # JWT token utilities
│   │   │   └── biometric.ts # Biometric verification
│   │   └── payments/ # Stripe Connect integration
│   │       ├── stripe.ts # Stripe client & core functions
│   │       ├── fee-calculator.ts # Platform fee calculation
│   │       ├── payouts.ts # Seller payout processing
│   │       ├── invoices.ts # Invoice generation
│   │       └── webhooks.ts # Stripe webhook handler
│   ├── .env # Environment variables (git-ignored)
│   ├── .env.example # Environment template
│   ├── package.json
│   └── tsconfig.json
│
├── milimo-mobile/ # Mobile War Room App (React Native)
│   ├── src/
│   │   ├── App.tsx # Main application
│   │   ├── screens/ # App screens
│   │   │   ├── PendingList.tsx # Pending actions list
│   │   │   ├── ActionDetail.tsx # Action details & approve/veto
│   │   │   └── Settings.tsx # App settings
│   │   ├── components/ # UI components
│   │   │   └── ActionCard.tsx # Action card component
│   │   ├── hooks/ # React hooks
│   │   │   └── useAuth.ts # Authentication hook
│   │   └── api/ # API client
│   │       └── warroom.ts # War Room API client
│   ├── package.json
│   └── app.json
│
├── test/                        # Test suite
│   ├── milimo-*.test.js         # Unit tests
│   └── integration/             # Integration tests
│       ├── harness.js           # Test harness
│       ├── blueprint-manager.test.js
│       ├── mesh-coordinator.test.js
│       ├── privacy-router.test.js
│       ├── evolution-cycle.test.js
│       └── multi-region.test.js
│
├── docs/technical/              # Technical documentation
│   ├── openshell-ipc.md         # OpenShell IPC documentation
│   ├── multi-region-mesh.md     # Multi-region architecture
│   ├── war-room-api.md          # War Room API spec
│   └── health-metrics.md        # Health metrics spec
│
├── milimo-claw-docs/            # Project documentation
├── nemoclaw/                    # NemoClaw plugin (upstream)
├── nemoclaw-blueprint/          # NemoClaw base blueprint (upstream)
├── .github/workflows/           # CI/CD pipelines
├── Dockerfile                   # Sandbox image
├── Dockerfile.tool              # CLI tool image
└── NemoClaw-README.md           # Original NemoClaw README
```
MilimoClaw/
├── milimo/                    # Milimo Claw plugin (TypeScript)
│   ├── src/
│   │   ├── index.ts           # Plugin entry point
│   │   ├── cli.ts             # CLI registrar
│   │   ├── commands/          # init, squad, blueprint, warroom, slash
│   │   └── warroom/           # War Room TUI, approval engine, audit, rate limiter
│   ├── openclaw.plugin.json   # Plugin manifest
│   └── package.json
│
├── milimo-blueprint/          # Role blueprints & orchestrator (Python + YAML)
│   ├── roles/                 # 5 claw role blueprints
│   ├── policies/              # 5 per-role sandbox policies
│   ├── templates/             # Pre-built squad templates
│   ├── orchestrator/          # Core engine components
│   │   ├── privacy_router.py  # Sensitivity classification & routing
│   │   ├── contracts.py       # Inter-claw message contracts
│   │   ├── mesh.py            # Mesh coordinator with gateway support
│   │   ├── gateway_adapter.py # Multi-transport gateway (Unix/WS/File)
│   │   ├── tool_generator.py  # LLM-based tool code generation
│   │   ├── tool_validator.py  # AST security validation
│   │   ├── tool_sandbox.py    # Isolated tool execution
│   │   ├── evolution_cycle.py # Weekly self-evolution pipeline
│   │   └── ...
│   ├── schemas/               # JSON schemas
│   │   └── tool-spec.json     # Tool specification schema
│   ├── prompts/               # LLM prompt templates
│   │   └── tool-generation/   # Tool generation prompts
│   ├── claw-schema.yaml       # Blueprint schema definition
│   ├── mesh_config.yaml       # Inter-claw message matrix
│   ├── privacy_policy.yaml    # Default sensitivity routing policy
│   └── rate-limits.yaml       # Tier-based rate limit config
│
├── test/                      # Test suite
│   ├── milimo-*.test.js       # Unit tests
│   └── integration/           # Integration tests
│       ├── harness.js         # Test harness
│       ├── blueprint-manager.test.js
│       ├── mesh-coordinator.test.js
│       ├── privacy-router.test.js
│       └── evolution-cycle.test.js
│
├── docs/                      # NemoClaw documentation
├── milimo-claw-docs/          # Project documentation
├── nemoclaw/                  # NemoClaw plugin (upstream)
├── nemoclaw-blueprint/        # NemoClaw base blueprint (upstream)
├── .github/workflows/         # CI/CD pipelines
├── Dockerfile                 # Sandbox image
├── Dockerfile.tool            # CLI tool image
└── NemoClaw-README.md         # Original NemoClaw README
```
MilimoClaw/
├── milimo/                      # Milimo Claw plugin (TypeScript)
│   ├── src/
│   │   ├── index.ts             # Plugin entry point
│   │   ├── cli.ts               # CLI registrar
│   │   ├── commands/            # init, squad, blueprint, warroom, slash
│   │   └── warroom/             # War Room TUI, approval engine, audit
│   ├── openclaw.plugin.json     # Plugin manifest
│   └── package.json
│
├── milimo-blueprint/            # Role blueprints & orchestrator (Python + YAML)
│   ├── roles/                   # 5 claw role blueprints
│   ├── policies/                # 5 per-role sandbox policies
│   ├── templates/               # Pre-built squad templates
│   ├── orchestrator/ # Core engine components
│   │   ├── privacy_router.py # Sensitivity classification & routing
│   │   ├── contracts.py # Inter-claw message contracts
│   │   ├── mesh.py # Mesh coordinator with gateway support
│   │   ├── gateway_adapter.py # Multi-transport gateway (Unix/WS/File)
│   │   ├── mesh_relay.py # Relay client/server for NAT traversal
│   │   ├── region_detector.py # Region detection via IP/latency
│   │   ├── latency_monitor.py # Inter-region latency tracking
│   │   ├── mesh_failover.py # Failover & split-brain resolution
│   │   ├── health_collector.py # Health metric collection
│   │   ├── provenance_signer.py # Ed25519 blueprint signing
│   │   ├── provenance_verifier.py # Signature verification
│   │   ├── chain_validator.py # Provenance chain validation
│   │   ├── attestation_generator.py # Performance attestation generation
│   │   ├── tool_generator.py # LLM-based tool code generation
│   │   ├── tool_validator.py # AST security validation
│   │   ├── tool_sandbox.py # Isolated tool execution
│   │   └── evolution_cycle.py # Weekly self-evolution pipeline
│   ├── schemas/ # JSON schemas
│   │   ├── tool-spec.json # Tool specification schema
│   │   └── performance-attestation.json # Attestation schema
│
├── milimo-claw-docs/            # Project documentation
├── nemoclaw/                    # NemoClaw plugin (upstream)
├── nemoclaw-blueprint/          # NemoClaw base blueprint (upstream)
├── test/                        # Test suite (JS + Python)
├── Dockerfile                   # Sandbox image
├── Dockerfile.tool              # CLI tool image
└── NemoClaw-README.md           # Original NemoClaw README
```

---

## Testing

### TypeScript Tests (Jest)

```bash
cd milimo && npm test
```

Runs 68 tests covering:
- **ConfigManager** (17 tests) — load, save, migrate, clear
- **Config Encryption** (18 tests) — encrypt/decrypt round trip, backwards compat
- **ApprovalEngine** (19 tests) — queue handling, escalation rules, rate limiting
- **WarRoomTUI** (22 tests) — commands, queue rendering, action handling
- **Blueprint Commands** (24 tests) — fork, merge, publish, rollback, spawnSync safety

All tests mock filesystem and child_process — no real disk/Python execution.

### Python Tests (pytest)

```bash
cd milimo-blueprint && python3 -m pytest tests/ -v
```

Runs 73+ tests covering:
- Data type → routing decision classification
- Role-specific routing overrides
- Fallback behavior for unknown data types
- Locked route enforcement
- Contract validation & matrix enforcement
- Mesh coordinator (registration, routing, health monitoring)
- Topology persistence
- Tool generation and validation
- Bridge CLI command routing

### Integration Tests (TS ↔ Python Boundary)

```bash
node --test test/integration/*.test.js
```

Integration tests verify:
- Blueprint manager operations
- Mesh coordinator with gateway
- Privacy router classification
- Evolution cycle stages
- Rate limiter integration
- Multi-region mesh (region detection, latency, failover)
- Health monitoring
- Python bridge CLI

### CI/CD Pipeline

GitHub Actions workflow runs on every push:

```bash
# View workflow
cat .github/workflows/integration.yml
```

Pipeline includes:
- **Lint:** ESLint (JS) + Ruff (Python)
- **Unit Tests:** Node.js 18/20 + Python 3.11/3.12
- **Integration Tests:** Full boundary coverage
- **Security Scan:** npm audit + bandit

---

## Roadmap

### ✅ Phase 0 — Foundation (Complete)

| Sub-Phase | Status |
|---|---|
| 0.1 Milimo CLI Foundation | ✅ |
| 0.2 Claw Role Blueprints | ✅ |
| 0.3 Privacy Router | ✅ |
| 0.4 Squad Mesh Protocol | ✅ |
| 0.5 War Room TUI | ✅ |
| 0.6 Milimo Templates | ✅ |
| 0.7 Build Claw Alpha | ✅ |
| 0.8 Integration & Verification | ✅ |

### ✅ Phase 1 — Self-Evolution Engine (Complete)

- Weekly evolution cycle implementation ✅
- Tool proposal → build → test → deploy pipeline ✅
- Cross-claw evolution signals ✅

### ✅ Phase 2 — Blueprint Marketplace (Complete)

- Peer-to-peer blueprint listing & discovery ✅
- Cryptographic provenance verification ✅
- Fork, merge, and inheritance protocols ✅

### ✅ Phase 3 — Production Hardening (Complete)

| Feature | Status |
|---|---|
| OpenShell Gateway Integration | ✅ |
| Multi-transport mesh (Unix, WebSocket, File) | ✅ |
| Tool Code Generation (LLM-based) | ✅ |
| Tool Security Validation (AST-based) | ✅ |
| Tool Sandbox (Isolated Execution) | ✅ |
| Integration Test Suite | ✅ |
| CI/CD Pipeline (GitHub Actions) | ✅ |
| Rate Limiting (Free/Pro tiers) | ✅ |

### ✅ Phase 4 — Scale & Distribution (Complete)

| Feature | Status |
|---|---|
| Multi-Region Mesh Support | ✅ |
| Region Detection (IP geolocation + latency) | ✅ |
| Relay Server (NAT traversal) | ✅ |
| Latency Monitoring (P95/P99) | ✅ |
| Failover & Split-brain Resolution | ✅ |
| Mobile War Room Companion | ✅ |
| REST/WebSocket API | ✅ |
| Push Notifications (FCM/APNs) | ✅ |
| Biometric Authentication | ✅ |
| Real-time Health Monitoring | ✅ |
| Health Score Calculation | ✅ |
| Alert Generation | ✅ |

### ✅ Phase 5 — Blueprint Economy (Complete)

| Feature | Status |
|---|---|
| Stripe Connect Integration | ✅ |
| Connected Account Management | ✅ |
| Checkout Session Creation | ✅ |
| Platform Fee Processing (10%) | ✅ |
| Seller Payout Scheduling | ✅ |
| Invoice Generation | ✅ |
| Webhook Handling | ✅ |
| Ed25519 Blueprint Signing | ✅ |
| Provenance Chain Validation | ✅ |
| Performance Attestations | ✅ |
| Verification Badges | ✅ |
| Third-party Auditor Framework | ✅ |

### ✅ Phase 6 — Enterprise & University Tier (Complete)

| Feature | Status |
|---|---|
| Multi-Tenant Architecture | ✅ |
| Tenant Management (CRUD) | ✅ |
| Custom Branding (White-label) | ✅ |
| Admin Dashboard | ✅ |
| Usage Analytics | ✅ |
| Cohort Templates | ✅ |
| Batch Squad Creation | ✅ |
| Role Assignment | ✅ |

### ✅ Audit Remediation (Complete — 2026-03-20)

| Issue | Priority | Status |
|-------|----------|--------|
| Consolidate dual configuration files | HIGH | ✅ |
| Register missing CLI commands | HIGH | ✅ |
| Fix shell command injection risk | HIGH | ✅ |
| Add TypeScript unit tests | HIGH | ✅ |
| Improve Python bridge | MEDIUM | ✅ |
| Upgrade War Room TUI | MEDIUM | ✅ |
| Encrypt sensitive config fields | MEDIUM | ✅ |
| Expand slash commands | LOW | ✅ |
| Fix payment API default URL | LOW | ✅ |
| Fix evolution manager static data | LOW | ✅ |

**Key improvements:**
- Single `config.json` with automatic migration from `state.json`
- All CLI commands registered: `health`, `payment`, `verify`, `badge`, `provenance-keygen`
- Shell injection eliminated: `spawnSync` with array args throughout
- 68 Jest tests covering core functionality
- Structured Python bridge with JSON CLI
- Blessed-based split-pane War Room TUI with keyboard shortcuts
- AES-256-GCM encryption for sensitive fields (meshSecret, API keys)
- Slash commands: `approve`, `veto`, `health`, `evolution`
- Production default API URL with fallback chain

---

## Documentation

### Getting Started

| Document | Description |
|---|---|
| [Quick Start Guide](docs/QUICK_START.md) | **START HERE** — Proper setup flow for macOS |
| [Setup Guide](docs/setup-guide.md) | Detailed Docker and gateway configuration |
| [Troubleshooting](docs/troubleshooting/TROUBLESHOOTING.md) | Common issues and solutions |
| [Native vs Plugin Onboarding](docs/troubleshooting/NATIVE_VS_PLUGIN_ONBOARDING.md) | Critical difference explained |

### Core Documentation

| Document | Description |
|---|---|
| [Project Description](milimo-claw-docs/MILIMO_CLAW_PROJECT_DESCRIPTION.md) | Full product spec — architecture, features, user flows |
| [Architecture Guide](milimo-claw-docs/ARCHITECTURE.md) | Technical deep-dive into the multi-sandbox mesh |
| [CLI Reference](milimo-claw-docs/CLI_REFERENCE.md) | Complete command documentation |
| [Privacy & Security](milimo-claw-docs/PRIVACY_AND_SECURITY.md) | Data routing, isolation, and trust model |
| [Blueprint Economy](milimo-claw-docs/BLUEPRINT_ECONOMY.md) | Versioning, marketplace, and inheritance |

### Technical Specs

| Document | Description |
|---|---|
| [Multi-Region Mesh](docs/technical/multi-region-mesh.md) | Multi-region architecture |
| [War Room API](docs/technical/war-room-api.md) | REST/WebSocket API specification |
| [Health Metrics](docs/technical/health-metrics.md) | Health scoring specification |
| [Payment Provider](docs/technical/payment-provider-selection.md) | Stripe Connect integration |

### Reports & Status

| Document | Description |
|---|---|
| [Implementation Plan](milimo-claw-docs/reports/MILIMO_CLAW_IMPLEMENTATION_PLAN.md) | Full implementation roadmap |
| [NemoClaw Comparison](milimo-claw-docs/reports/nemoclaw-comparison-insights.md) | Differences from upstream |
| [Phase Reports](milimo-claw-docs/reports/) | Phase completion reports |

---

## Contributing

See [CONTRIBUTING.md](milimo-claw-docs/guides/CONTRIBUTING.md) for contribution guidelines.

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)

