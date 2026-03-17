# 🦀 Milimo Claw

<p align="center">
  <img src="assets/Milimo-Claw.png" alt="Milimo Claw Logo" width="800" />
</p>

> *"Your friend group is a startup. Your laptops are the infrastructure. Your claws do the work."*

[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-Phase_0_Complete-green)](#roadmap)
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

### Prerequisites

- **Hardware:** RTX-capable NVIDIA GPU laptop (for local inference)
- **Software:** Docker, Node.js ≥ 20, Git
- **NemoClaw:** [NVIDIA NemoClaw](NemoClaw-README.md) installed

### 1. Clone & Install

```bash
git clone https://github.com/mainza-ai/MilimoClaw.git
cd MilimoClaw
npm install
```

### 2. Build the Docker Image

```bash
docker build -t milimo-claw -f Dockerfile .
```

### 3. Initialize Your Squad

```bash
# Inside the container or via the CLI tool
openclaw milimo init --squad my-squad --role content --template content-agency
```

### 4. Launch the War Room

```bash
openclaw milimo warroom
```

> For detailed Docker commands, see [milimo-claw-docs/docker-run-commands.md](milimo-claw-docs/docker-run-commands.md).

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
│   │   ├── commands/            # init, squad, blueprint, warroom, slash
│   │   └── warroom/             # War Room TUI, approval engine, audit
│   ├── openclaw.plugin.json     # Plugin manifest
│   └── package.json
│
├── milimo-blueprint/            # Role blueprints & orchestrator (Python + YAML)
│   ├── roles/                   # 5 claw role blueprints
│   ├── policies/                # 5 per-role sandbox policies
│   ├── templates/               # Pre-built squad templates
│   ├── orchestrator/            # Privacy router, contracts, mesh coordinator
│   ├── claw-schema.yaml         # Blueprint schema definition
│   ├── mesh_config.yaml         # Inter-claw message matrix
│   └── privacy_policy.yaml      # Default sensitivity routing policy
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

### JavaScript Tests (Blueprints, CLI, Contracts)

```bash
npm test
```

Runs 76 tests covering:
- Plugin exports & config parsing
- All 5 role blueprint schema validation
- Filesystem isolation checks
- Inference routing enforcement
- Inter-claw policy verification
- Sandbox policy structure
- Contract validation (valid routes, unauthorized routes, War Room access)
- Approval requirements

### Python Tests (Privacy Router, Mesh Protocol)

```bash
python3 -m unittest discover -s milimo-blueprint/tests -v
```

Runs 73 tests covering:
- Data type → routing decision classification
- Role-specific routing overrides
- Fallback behavior for unknown data types
- Locked route enforcement
- Contract validation & matrix enforcement
- Mesh coordinator (registration, routing, health monitoring)
- Topology persistence

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

### 🔲 Phase 1 — Self-Evolution Engine

- Weekly evolution cycle implementation
- Tool proposal → build → test → deploy pipeline
- Cross-claw evolution signals

### 🔲 Phase 2 — Blueprint Marketplace

- Peer-to-peer blueprint listing & discovery
- Cryptographic provenance verification
- Fork, merge, and inheritance protocols

### 🔲 Phase 3 — Production Hardening

- Multi-region mesh support
- Real-time mesh health monitoring
- Automated failover & recovery

---

## Documentation

| Document | Description |
|---|---|
| [Project Description](milimo-claw-docs/MILIMO_CLAW_PROJECT_DESCRIPTION.md) | Full product spec — architecture, features, user flows |
| [Architecture Guide](milimo-claw-docs/ARCHITECTURE.md) | Technical deep-dive into the multi-sandbox mesh |
| [CLI Reference](milimo-claw-docs/CLI_REFERENCE.md) | Complete command documentation |
| [Privacy & Security](milimo-claw-docs/PRIVACY_AND_SECURITY.md) | Data routing, isolation, and trust model |
| [Blueprint Economy](milimo-claw-docs/BLUEPRINT_ECONOMY.md) | Versioning, marketplace, and inheritance |
| [Squad Setup Guide](milimo-claw-docs/SQUAD_SETUP_GUIDE.md) | Step-by-step squad formation walkthrough |
| [Docker Commands](milimo-claw-docs/docker-run-commands.md) | Docker build, run, and management reference |
| [NemoClaw README](NemoClaw-README.md) | Original upstream NemoClaw documentation |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)

*Milimo (mi-LEE-mo) — from the Tonga people of Zambia, meaning "works," "tasks," or "labour."*
