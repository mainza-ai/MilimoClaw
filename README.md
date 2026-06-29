# 🦀 Milimo Claw

<p align="center">
  <img src="assets/Milimo-Claw.png" alt="Milimo Claw Logo" width="800" style="border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

<p align="center">
  <strong>An Autonomous Multi-Agent Hustle Mesh Built on NVIDIA NemoClaw</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square" alt="License" /></a>
  <a href="https://github.com/NVIDIA/NemoClaw"><img src="https://img.shields.io/badge/built_on-NemoClaw-purple.svg?style=flat-square" alt="Built on NemoClaw" /></a>
  <a href="https://github.com/mainza-ai/MilimoClaw/actions"><img src="https://img.shields.io/badge/build-passing-success.svg?style=flat-square" alt="Build Status" /></a>
  <a href="https://github.com/mainza-ai/MilimoClaw/releases"><img src="https://img.shields.io/badge/version-v2.0.0--stable-teal.svg?style=flat-square" alt="Version" /></a>
</p>

> *"Your friend group is a startup. Your laptops and cloud nodes are the infrastructure. Your claws do the work."*

---

**Milimo Claw** (derived from the Tonga word for *"works," "tasks," or "labour"*) is a multi-agent autonomous hustle platform built on [NVIDIA NemoClaw](https://github.com/NVIDIA/NemoClaw). It turns a squad of operators running NemoClaw sandboxes into a coordinated, self-evolving, AI-powered business operation that runs 24/7.

### 🎯 Choose Your Profile

MilimoClaw runs on **NemoClaw** with two profiles:

| Profile | Interface | Best For | Inference |
|---------|-----------|----------|-----------|
| **OpenClaw** (default) | TUI + Bridge Server | Solo operators, local development | NVIDIA NIM / Local |
| **Hermes** | Web Dashboard (port 18789) + OpenAI-compatible API (port 8642) | Teams, headless CI/CD, managed tool gateways | Native `delegate_task` + `cronjob` |

**Decision tree**:
```
Need web search / browser automation / image gen / audio?
  → Yes: Use Hermes profile + Nous Portal OAuth at onboarding (--auth-mode nous_oauth)
  → No:  Use OpenClaw profile (standard API key)

Need durable scheduled jobs (cronjob) that survive restarts?
  → Yes: Use Hermes profile (native cronjob)
  → No:  OpenClaw (threading.Timer works for solo)

Running in CI/CD or headless server?
  → Yes: Hermes profile (non-interactive onboarding, OpenAI-compatible API)
  → No:  OpenClaw profile (TUI-first)

Want zero-config solo setup?
  → Yes: OpenClaw (`./install.sh --solo`)
  → No:  Hermes (Docker + dashboard)
```

### 💡 Solo Operator Mode

For solo founders and edge developers, **Solo Mode** runs all six autonomous claws concurrently within a single sandboxed environment (using any GPU-enabled PC for local inference, or any CPU/GPU system using cloud connections). It delivers the full power of a multi-agent business mesh without multi-host cluster configuration overhead, making it the most popular and streamlined way to run the platform.

---

## Key Highlights & Capabilities

### Hardware & Platform Agnostic

Milimo Claw supports cross-platform environments, freeing operators from specific hardware restrictions:
* **Apple Silicon Macs** (M1/M2/M3/M4) via macOS Docker.
* **Linux CPU & GPU Servers** on-premise or in the cloud.
* **NVIDIA GPU-Enabled PCs** (such as RTX or data center cards) for local NIM inference.

By utilizing NemoClaw's flexible inference router, claws fall back from local containerized NIM microservices to cloud APIs (such as the NVIDIA NIM Cloud API) when running on non-NVIDIA or light hardware.

### Dual-Profile Architecture (New in v0.2.0)

Milimo Claw now runs on **two NemoClaw profiles** sharing a single `milimo-core` library:

| Profile | Interface | Parallelism | Scheduling | Use Case |
|---------|-----------|-------------|------------|----------|
| **OpenClaw** (default) | TUI + Bridge Server | `sessions_spawn` (depth ≤ 2) | Python `threading.Timer` | Terminal-native operators, existing OpenClaw users |
| **Hermes** | Web Dashboard (port 18789) + OpenAI-compatible API (port 8642) | Native `delegate_task` (no depth limit) | Native `cronjob` (durable) | Web-based operators, CI/CD, managed tool gateways |

**Quick decision tree**:

```
Do you want web search / browser automation inside Hermes?
  → Yes: Use Nous Portal OAuth at onboarding (--auth-mode nous_oauth)
  → No:  API-key mode is sufficient

Are you on a headless remote host?
  → Yes: Set CHAT_UI_URL before onboarding, or use SSH port forwarding
  → No (local machine): Dashboard at http://127.0.0.1:18789/

Do you want a web dashboard UI?
  → Yes: nemohermes (Hermes profile)
  → No:  nemoclaw (OpenClaw profile, default)
```

### Stateful Process Supervision

Equipped with **Lucy** (the Assistant Claw) acting as the system orchestration harness:
* **E2E Stall Detection**: Lucy dynamically polls active processes across isolated sandbox pathways.
* **Dual-Delivery Alerts**: When a milestone stalls or times out, Lucy writes conversational warnings to chat channels and injects high-priority `ActionPriority.HOLD` alerts directly into the **Solo War Room TUI**.
* **Intelligent Diagnostics**: Standardized under seccomp-friendly `assistant_query` payloads, Lucy can actively prompt any worker claw for its current REVIEW/HOLD queue sizes and recent operational log snippets.

### Background Task Pipelines

The mesh resolves complex requests asynchronously through standalone pipelines:
* **Threaded Execution**: Worker claws spawn background threads (`build-assistant-task-pipeline`) to resolve engineering sprint issues and deliver code modifications without blocking the inter-sandbox polling queues.
* **Offline Resilience**: The pipeline wraps Git CLI operations in structured try-except blocks, ensuring local execution succeeds even when unauthenticated or offline.
* **Premium Local Fallback Mocks**: If remote NIM APIs are unreachable under sandbox network isolation, the inference client falls back to local mocks, including a pre-seeded, fully playable Pygame Tetris game code generator.

### Dynamic Startup Latency Reduction

Startup and polling wait delays are minimized for sandboxed environments:
* **Signal Polling**: The build claw polls the analytics claw weekly signals using directory-checking loops rather than arbitrary timeouts.
* **Sandbox Calibration**: Polling wait delays scale down from 5 minutes (`300s`) in production to `1.0` second in development and integration test scopes, improving testing feedback loops.

### Unified Sync Script

Developers can easily access and view files generated by the claws:
* **Host Extraction**: Running the synchronization script extracts Stripe invoices, draft posts, and generated source code from all claws to the host folder:
  ```
  ./claws_data/
  ```
* **Git Security**: The data directory is registered in the workspace `.gitignore` file to ensure client records and developer assets are kept secure.

### Native Memory & Context Calibration

The platform maintains infinite conversation execution loops without prompt ceiling crashes:
* **Context Bounding**: registers the provider-level `contextWindow` at **`65536`** (64k) tokens in `openclaw.json` to match hosted NVIDIA NIM API physical limitations.
* **Context Pruning**: Injects native `contextPruning` rules under `agents.defaults` to trim non-essential tool outputs and prune cached inputs after 4 hours.
* **Safeguard Compaction**: Triggers native `compaction` loops and background memory synthesis turns (`memoryFlush`) at a soft threshold of `4096` tokens from limits, writing state summaries directly to `SOUL.md` / `soul.md` via `NO_REPLY` silent turns.

---

## The Six Autonomous Claws

Each claw runs inside its own highly isolated NemoClaw sandbox with kernel-level seccomp, Landlock, and dropped capability protections. Claws communicate through typed inter-sandbox message contracts enforced by the **OpenShell Gateway**.

| Claw | Specialty Role | Isolated Mount Pathway |
| :--- | :--- | :--- |
| 🎨 **Content Claw** | Creative Department: generates posts, copy, email campaigns, and brand assets | `/sandbox/.openclaw-data/milimo/claws/content` |
| 📋 **Ops Claw** | Account & Project Management: scores relationship health, scopes briefs, and runs deadline risk | `/sandbox/.openclaw-data/milimo/claws/ops` |
| 📊 **Analytics Claw** | Intelligence Layer: generates weekly reports, runs anomaly detection, and opportunity scores | `/sandbox/.openclaw-data/milimo/claws/analytics` |
| 💰 **Finance Claw** | Financial Nervous System: Stripe invoicing, pricing floor calculation, tax categorization | `/sandbox/.openclaw-data/milimo/claws/finance` |
| 🔧 **Build Claw** | Technical Execution: scores Github issues, writes code, staged deployments, and dependency audits | `/sandbox/.openclaw-data/milimo/claws/build` |
| 🤖 **Assistant Claw (Lucy)** | Operator Bridge: stateful process supervisor, operator query router, and mesh coordinator | `/sandbox/.openclaw-data/milimo/claws/assistant` |

---

## 📚 The Milimo Knowledge Vault (Obsidian-Powered)

To coordinate and govern a high-leverage multi-agent system, you need a living, interlinked knowledge base. Inside [milimo-claw-wiki/](file:///Users/mck/Desktop/MilimoClaw/milimo-claw-wiki) lives a fully structured, **Obsidian-ready markdown vault** designed on Andrej Karpathy's LLM Wiki pattern.

It serves as the **ultimate source of truth** for human operators and AI assistants alike:

* **Interactive Graph Visualization**: Load the vault into [Obsidian](https://obsidian.md/) to inspect the full agent topology, message contracts, and data-flow pathways visually via the interactive Graph View.
* **LLM-Optimized Architecture**: The vault features an AI-first structure (curated in [CLAUDE.md](file:///Users/mck/Desktop/MilimoClaw/milimo-claw-wiki/CLAUDE.md)) with strict metadata schemas, tags hierarchies, and ground-truth validation rules, allowing LLMs to absorb the complete system context in seconds.
* **Comprehensive Knowledge Base**:
  * 🔒 **Security & Policies**: Documents kernel-level seccomp boundaries, Landlock constraints, and the privacy router.
  * 💬 **Coordination Matrix**: Explains the 27 typed inter-claw message contracts, sequencing rules, and approval modes.
  * 🌱 **Self-Evolution Logs**: Tracks autonomous Sunday tool-generation outcomes, baseline calibrations, and complexity scores.

*To explore the vault locally, simply open the [milimo-claw-wiki/](file:///Users/mck/Desktop/MilimoClaw/milimo-claw-wiki) directory inside Obsidian.*

---

## Quick Start

### Prerequisites

* **NemoClaw**: Core sandboxing runtime (install prior to initializing Milimo Claw)
  ```console
  $ curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
  ```
* **OS**: macOS (Apple Silicon), Linux (Ubuntu 22.04+ recommended), or Windows with WSL2.
* **Containers**: Docker Engine and Docker Compose.
* **Runtime**: Node.js 22.16+ & Python 3.11+.
* **Credentials**:
  - NVIDIA API Key — [build.nvidia.com](https://build.nvidia.com/) (Required for local or cloud NIM inference).
  - Github Personal Access Token (Required for Build Claw automation).

### Installation & Onboarding

#### Option A: OpenClaw Profile (Default)

To run the standard OpenClaw installation, execute:

```console
$ export NVIDIA_API_KEY=nvapi-your-key-here
$ export GITHUB_TOKEN=github_pat_your-token-here
$ git clone https://github.com/mainza-ai/MilimoClaw.git
$ cd MilimoClaw
$ cp .env.example .env
$ ./install.sh --solo --operator-name "your-name" --squad-name "your-squad" --non-interactive
$ nemoclaw my-assistant connect
$ openclaw tui
```

#### Option B: Hermes Profile

To run the Hermes profile installation and onboard the sandbox, execute:

```console
$ export NVIDIA_API_KEY=nvapi-your-key-here
$ export GITHUB_TOKEN=github_pat_your-token-here
$ git clone https://github.com/mainza-ai/MilimoClaw.git
$ cd MilimoClaw
$ cp .env.example .env
# Run the automated Hermes onboarding script
$ ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
# Or onboard manually using the Dockerfile directly
$ nemohermes onboard --name milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile
```

---

## Command Reference

### Platform Commands

Manage the sandboxes and squad deployments:

```console
$ openclaw milimo warroom
$ openclaw milimo squad status
$ openclaw milimo blueprint list
$ openclaw milimo blueprint fork <source-blueprint-id>
$ openclaw milimo blueprint publish
```

### Chat Shortcuts (Inside OpenClaw TUI)

Type these commands directly inside the TUI conversation stream:
* `/milimo status` — Check heartbeats and health metrics across the mesh.
* `/milimo roles` — List active operational permissions.
* `/milimo mesh` — Display visual inter-sandbox gateway topology.
* `/milimo help` — Retrieve the comprehensive interactive handbook.

---

## Architecture & Security Blueprint

```
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                                MILIMO MESH TUI                               │
 │                                                                              │
 │ [Content Claw]  [Ops Claw]  [Analytics]  [Finance Claw]  [Build Claw]        │
 │    Sandboxed     Sandboxed   Sandboxed     Sandboxed      Sandboxed          │
 │                                                                              │
 │        ▲             ▲           ▲             ▲              ▲              │
 │        │             │           │             │              │              │
 │        └─────────────┼───────────┴─────────────┼──────────────┘              │
 │                      ▼                         ▼                             │
 │                         [OpenShell Gateway Store]                            │
 │                       (Typed Message Contract Bus)                           │
 │                                  ▲                                           │
 │                                  │                                           │
 │                                  ▼                                           │
 │                     [Lucy Stateful Orchestrator] ◄──► [Solo War Room TUI]    │
 │                     (Assistant Sandbox Harness)        (Dashboard HOLD Alerts)│
 └──────────────────────────────────────────────────────────────────────────────┘
```

* **Zero-Trust File Isolation**: Sandboxes cannot traverse sibling filesystems. All interaction occurs strictly via typed contracts over localhost gateway sockets.
* **Privacy Router**: Sensitive credentials and operational variables are held in the OpenShell Gateway Store. Local classification filters automatically redact client records and source files.
* **Continuous Self-Evolution**: Claws analyze execution outcomes and autonomously write, test (via sandboxed Pytest backtesting), and register fresh Python tools every Sunday.

---

## Testing and Quality Control

Milimo Claw enforces absolute type safety and robust validation protocols:

```console
# Test standard javascript packages
$ cd milimo && npm test

# Test core Python library
$ .venv/bin/pytest milimo-core/tests/

# Test Hermes plugin
$ .venv/bin/pytest milimo-hermes-plugin/tests/

# Test blueprint orchestrator
$ cd milimo-blueprint && PYTHONPATH=.:orchestrator uv run pytest
```

---

## License & Creator

* **License**: Apache-2.0 — see [LICENSE](LICENSE).
* **Author**: **Mainza Kangombe** — [LinkedIn Profile](https://www.linkedin.com/in/mainza-kangombe-6214295)
