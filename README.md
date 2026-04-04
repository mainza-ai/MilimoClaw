# 🦀 Milimo Claw

<p align="center">
  <img src="assets/Milimo-Claw.png" alt="Milimo Claw Logo" width="800" />
</p>

> *"Your friend group is a startup. Your laptops are the infrastructure. Your claws do the work."*

[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-v2.0-brightgreen)](#roadmap)
[![Built on NemoClaw](https://img.shields.io/badge/built_on-NemoClaw-purple)](https://github.com/NVIDIA/NemoClaw)

**Milimo Claw** is a multi-agent autonomous hustle platform built on [NVIDIA NemoClaw](https://github.com/NVIDIA/NemoClaw). It turns a squad of college students — each running a NemoClaw sandbox on their RTX laptop — into a coordinated AI-powered business operation that runs 24/7.

> **On the name:** *Milimo* (mi-LEE-mo) is a name from the Tonga language of Zambia, meaning **"works," "tasks," or "labour."**

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

Milimo Claw runs as an extension on top of the NemoClaw stack, inheriting its security sandbox (OpenShell + Landlock + seccomp) while adding multi-agent coordination:

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
| 🔧 **Build** | Engineering — code, PRs, deploys, monitoring | `/sandbox/build` | Autonomous PR cycle & production monitoring |

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
├── milimo/                          # Milimo Claw plugin (TypeScript)
│   ├── src/
│   │   ├── index.ts                 # Plugin entry point
│   │   ├── cli.ts                   # CLI registrar
│   │   ├── commands/                # init, squad, blueprint, warroom, health, slash
│   │   ├── lib/                     # Config, encryption, python bridge
│   │   ├── mesh/                    # Gateway client, mesh encryption
│   │   ├── onboard/                 # Onboarding config & wizard
│   │   └── warroom/                 # TUI, approval engine, audit, rate limiter
│   ├── openclaw.plugin.json         # Plugin manifest
│   └── package.json
│
├── milimo-blueprint/                # Role blueprints & orchestrator (Python + YAML)
│   ├── roles/                       # 5 claw role blueprints (YAML)
│   ├── policies/                    # 5 per-role sandbox policies (YAML)
│   ├── templates/                   # Pre-built squad templates
│   ├── orchestrator/                # Core engine components (Python)
│   │   ├── content/                 # Content Claw (11 modules)
│   │   ├── ops/                     # Ops Claw (11 modules)
│   │   ├── analytics/               # Analytics Claw (12 modules)
│   │   ├── finance/                 # Finance Claw (12 modules)
│   │   ├── build/                   # Build Claw (13 modules)
│   │   │   ├── build_init.py        # Filesystem init, inference fallback chain
│   │   │   ├── signal_dispatcher.py # Event normalization, renderer/sink separation
│   │   │   ├── approval_handler.py  # Two-stage REVIEW→HOLD, task persistence
│   │   │   ├── issue_manager.py     # Sprint planning, velocity tracking
│   │   │   ├── code_generator.py    # Hash-anchored code generation
│   │   │   ├── pr_manager.py        # PR lifecycle with status validation
│   │   │   ├── deploy_manager.py    # Deploy lifecycle, background execution
│   │   │   ├── error_monitor.py     # ErrorPattern/ErrorEvent, tmux monitoring
│   │   │   ├── cost_monitor.py      # Baseline calculation, drift detection
│   │   │   ├── dependency_auditor.py# Vulnerability assessment, security PRs
│   │   │   ├── doc_maintainer.py    # Changelog/devlog generation
│   │   │   ├── build_scheduler.py   # Timer-based scheduling, missed job recovery
│   │   │   └── build_claw.py        # Main entry point
│   │   ├── privacy_router.py        # Sensitivity classification & routing
│   │   ├── contracts.py             # Inter-claw message contracts
│   │   ├── mesh.py                  # Mesh coordinator with gateway support
│   │   ├── gateway_adapter.py       # Multi-transport gateway (Unix/WS/File)
│   │   ├── mesh_relay.py            # Relay client/server for NAT traversal
│   │   ├── region_detector.py       # Region detection via IP/latency
│   │   ├── latency_monitor.py       # Inter-region latency tracking
│   │   ├── mesh_failover.py         # Failover & split-brain resolution
│   │   ├── health_collector.py      # Health metric collection
│   │   ├── provenance_signer.py     # Ed25519 blueprint signing
│   │   ├── provenance_verifier.py   # Signature verification
│   │   ├── chain_validator.py       # Provenance chain validation
│   │   ├── attestation_generator.py # Performance attestation generation
│   │   ├── tool_generator.py        # LLM-based tool code generation
│   │   ├── tool_validator.py        # AST security validation
│   │   ├── tool_sandbox.py          # Isolated tool execution
│   │   ├── evolution_cycle.py       # Weekly self-evolution pipeline
│   │   ├── assistant_setup.py       # Assistant system prompt rendering
│   │   └── solo_init.py             # Solo mode initialization
│   ├── schemas/                     # JSON schemas
│   │   ├── tool-spec.json           # Tool specification schema
│   │   └── performance-attestation.json
│   ├── prompts/                     # LLM prompt templates
│   │   └── tool-generation/         # Tool generation prompts
│   ├── claw-schema.yaml             # Blueprint schema definition
│   ├── mesh_config.yaml             # Inter-claw message matrix
│   ├── privacy_policy.yaml          # Default sensitivity routing policy
│   ├── regions.yaml                 # Multi-region configuration
│   └── rate-limits.yaml             # Tier-based rate limit config
│
├── milimo-server/                   # War Room API Server (TypeScript/Fastify)
│   ├── src/
│   │   ├── server.ts                # Fastify server entry point
│   │   ├── routes/                  # REST API routes (auth, pending, actions, status)
│   │   ├── notifications/           # Push notifications (FCM, APNs)
│   │   ├── auth/                    # JWT, biometric auth
│   │   └── payments/                # Stripe Connect integration
│   ├── .env.example                 # Environment template
│   ├── package.json
│   └── tsconfig.json
│
├── milimo-mobile/                   # Mobile War Room App (React Native)
│   ├── src/
│   │   ├── App.tsx                  # Main application
│   │   ├── screens/                 # PendingList, ActionDetail, Settings
│   │   ├── components/              # ActionCard
│   │   ├── hooks/                   # useAuth
│   │   └── api/                     # War Room API client
│   ├── package.json
│   └── app.json
│
├── milimo-admin/                    # Enterprise/University Tier Dashboard
├── milimo-claw-docs/                # Project documentation (specs, guides, reports)
│   ├── reference/                   # Claw specifications
│   ├── prompts/                     # Implementation prompts
│   ├── reports/                     # Audit reports, implementation plans
│   ├── guides/                      # Contributing guide
│   ├── troubleshooting/             # Plugin deployment, quick deploy commands
│   ├── stripe/                      # Stripe integration docs
│   └── specs/                       # Build Claw spec
│
├── test/                            # Test suite
│   ├── milimo-*.test.js             # Unit tests
│   ├── milimo-*.sh                  # E2E smoke tests
│   └── integration/                 # Integration tests (blueprint, mesh, privacy, evolution)
│
├── k8s/                             # Kubernetes manifests
│   ├── sandbox-pod.yaml             # Sandbox pod spec (Landlock, seccomp)
│   └── ...
├── scripts/                         # Build & deployment scripts
│   ├── milimo-start.sh              # Sandbox entrypoint
│   └── check-coverage-ratchet.sh    # Coverage enforcement
├── ci/                              # CI configuration
├── .github/workflows/               # GitHub Actions pipelines
├── Dockerfile                       # Sandbox image (NemoClaw base + Milimo layers)
├── install.sh                       # MilimoClaw installer (checks NemoClaw prerequisite)
├── uninstall.sh                     # MilimoClaw uninstaller
├── Makefile                         # Lint, format, test targets
├── package.json                     # Root package (milimo-claw)
├── pyproject.toml                   # Python docs project (milimo-claw-docs)
├── vitest.config.ts                 # Vitest configuration
└── commitlint.config.js             # Commit message conventions
```

---

## Testing

### TypeScript Tests (Jest)

```bash
cd milimo && npm test
```

Runs **318 tests** covering:
- **ConfigManager** (17 tests) — load, save, migrate, clear
- **Config Encryption** (18 tests) — encrypt/decrypt round trip, backwards compat
- **ApprovalEngine** (19 tests) — queue handling, escalation rules, rate limiting
- **WarRoomTUI** (22 tests) — commands, queue rendering, action handling
- **Blueprint Commands** (24 tests) — fork, merge, publish, rollback, spawnSync safety
- **Gateway Client** — mesh communication, encryption, fallback
- **Mesh Encryption** — HKDF key derivation, AES-256-GCM
- **Audit Logger** — action logging, query, export
- **Rate Limiter** — tier-based enforcement
- **Health Dashboard** — claw health collection & display

All unit tests mock filesystem and child_process — no real disk/Python execution.

### Python Tests (pytest)

```bash
cd milimo-blueprint && python3 -m pytest tests/ -v
```

Runs **1,192 tests** covering:
- All 5 claws (Content, Ops, Analytics, Finance, Build)
- Build Claw: 116 tests (101 unit + 15 MVR integration)
- Privacy router classification & routing
- Mesh coordination with gateway support
- Evolution cycle stages
- Tool generation and validation
- Bridge CLI command routing
- Assistant setup & solo initialization
- Finance operational log & payment events

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
- **Unit Tests:** Node.js 22.x + Python 3.12
- **Integration Tests:** Full boundary coverage
- **Security Scan:** npm audit (direct deps only) + bandit

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
| 0.7 Build Claw | ✅ Complete (13 modules, 116 tests, OmO/Clawhip enhancements) |
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
| Mobile War Room Companion | ✅ (scaffold — auth & API client pending) |
| REST/WebSocket API | ✅ |
| Push Notifications (FCM/APNs) | ✅ |
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
- 318 Jest tests covering core functionality
- Structured Python bridge with JSON CLI
- Blessed-based split-pane War Room TUI with keyboard shortcuts
- AES-256-GCM encryption with HKDF key derivation for sensitive fields
- Slash commands: `approve`, `veto`, `health`, `evolution`
- Production default API URL with fallback chain

### ✅ NemoClaw Rebuild (Complete — 2026-04-04)

| Task | Status |
|---|---|
| Strip NemoClaw duplicate code (nemoclaw/, nemoclaw-blueprint/, bin/, docs/) | ✅ |
| Rewrite Dockerfile — NemoClaw as base, Milimo layers on top | ✅ |
| Create Milimo-branded install.sh / uninstall.sh | ✅ |
| Security fixes (JWT, CORS, refresh tokens, HKDF, k8s capabilities) | ✅ |
| Build Claw implementation (13 modules, 3,921 lines) | ✅ |
| Fix all pre-existing test failures (19 → 0) | ✅ |
| Integrate oh-my-openagent patterns (fallback chain, task deps, hash-anchored gen) | ✅ |
| Integrate clawhip patterns (event normalization, renderer/sink, tmux monitoring) | ✅ |
| CI pipeline fixed (lockfile sync, smart audit) | ✅ |

---

## Documentation

### Getting Started

| Document | Description |
|---|---|
| [Quick Start Guide](docs/QUICK_START.md) | **START HERE** — Proper setup flow for macOS |
| [Plugin Deployment Troubleshooting](milimo-claw-docs/troubleshooting/PLUGIN_DEPLOYMENT_TROUBLESHOOTING.md) | Common deployment issues and solutions |
| [Quick Deploy Commands](milimo-claw-docs/troubleshooting/QUICK_DEPLOY_COMMANDS.md) | Fast reference for deployment commands |

### Core Documentation

| Document | Description |
|---|---|
| [Project Description](milimo-claw-docs/MILIMO_CLAW_PROJECT_DESCRIPTION.md) | Full product spec — architecture, features, user flows |
| [Architecture Guide](milimo-claw-docs/ARCHITECTURE.md) | Technical deep-dive into the multi-sandbox mesh |
| [CLI Reference](milimo-claw-docs/CLI_REFERENCE.md) | Complete command documentation |
| [Privacy & Security](milimo-claw-docs/PRIVACY_AND_SECURITY.md) | Data routing, isolation, and trust model |
| [Blueprint Economy](milimo-claw-docs/BLUEPRINT_ECONOMY.md) | Versioning, marketplace, and inheritance |
| [Changelog](milimo-claw-docs/CHANGELOG.md) | Release history and changes |

### Technical Specs

| Document | Description |
|---|---|
| [Multi-Region Mesh](docs/technical/multi-region-mesh.md) | Multi-region architecture |
| [War Room API](docs/technical/war-room-api.md) | REST/WebSocket API specification |
| [Health Metrics](docs/technical/health-metrics.md) | Health scoring specification |

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
