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
  <a href="https://github.com/mainza-ai/MilimoClaw/releases"><img src="https://img.shields.io/badge/version-v1.1.0--stable-teal.svg?style=flat-square" alt="Version" /></a>
</p>

> *"Your friend group is a startup. Your laptops and cloud nodes are the infrastructure. Your claws do the work."*

---

**Milimo Claw** (derived from the Tonga word for *"works," "tasks," or "labour"*) is a multi-agent autonomous hustle platform built on [NVIDIA NemoClaw](https://github.com/NVIDIA/NemoClaw). It turns a squad of operators running NemoClaw sandboxes into a coordinated, self-evolving, AI-powered business operation that runs 24/7.

---

## ⚡ Key Highlights & Capabilities

### 🌐 1. Hardware & Platform Agnostic (New!)
Milimo Claw is **no longer limited to running strictly on NVIDIA RTX laptops**. It has been fully liberated to support:
* 🍏 **Apple Silicon Macs** (M1/M2/M3/M4) via macOS Docker.
* 🐧 **Linux CPU & GPU Servers** on-premise or in the cloud.
* 💻 **Traditional NVIDIA RTX Systems** for local NIM inference.

By utilizing NemoClaw's flexible, multi-backend inference router, claws gracefully fall back from local containerized NIM microservices to cloud APIs (such as NVIDIA NIM Cloud API) when running on non-NVIDIA or light hardware, ensuring maximum agility and accessibility.

### 🛡️ 2. Stateful Active Process Supervision
Equipped with **Lucy** (the Assistant Claw) acting as the ultimate system orchestration harness:
* **E2E Stall Detection**: Lucy dynamically polls active processes (such as scoping tasks or engineering sprints) across isolated sandbox pathways.
* **Dual-Delivery Alerts**: When a milestone stalls or times out, Lucy simultaneously writes conversational warnings to chat channels (Telegram/Discord/TUI) and injects high-priority `ActionPriority.HOLD` alerts directly into the **Solo War Room TUI**.
* **Intelligent Diagnostics**: Standardized under seccomp-friendly `assistant_query` payloads, Lucy can actively prompt any worker claw for its current REVIEW/HOLD queue sizes and recent operational log snippets.

---

## ⚙️ The Six Autonomous Claws

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

## 🚀 Quick Start

### 📋 Prerequisites

* **OS**: macOS (Apple Silicon), Linux (Ubuntu 22.04+ recommended), or Windows with WSL2.
* **Containers**: Docker Engine and Docker Compose.
* **Runtime**: Node.js 22.16+ & Python 3.11+.
* **Credentials**:
  - NVIDIA API Key — [build.nvidia.com](https://build.nvidia.com/) (Required for local or cloud NIM inference).
  - Github Personal Access Token (Required for Build Claw automation).

### 🛠️ Installation & Onboarding

```bash
# 1. Export your API keys
export NVIDIA_API_KEY=nvapi-your-key-here
export GITHUB_TOKEN=github_pat_your-token-here

# 2. Clone the repository and enter workspace
git clone https://github.com/mainza-ai/MilimoClaw.git
cd MilimoClaw
cp .env.example .env

# 3. Trigger Solo Mode installation (Dockerfile mode)
# This registers the custom plugins and builds the sandbox container image
./install.sh --solo --operator-name "your-name" --squad-name "your-squad" --non-interactive

# 4. Connect your NemoClaw Assistant
nemoclaw my-assistant connect

# 5. Launch the conversational and War Room console
openclaw tui
```

---

## 🖥️ Command Reference

### Platform Commands
```bash
# Start the Solo War Room Dashboard TUI
openclaw milimo warroom

# Query the status and heartbeat cycles of all active claws
openclaw milimo squad status

# Version, fork, or publish your custom claw blueprints
openclaw milimo blueprint list
openclaw milimo blueprint fork <source-blueprint-id>
openclaw milimo blueprint publish
```

### Chat Shortcuts (Inside OpenClaw TUI)
* `/milimo status` — Check heartbeats and health metrics across the mesh.
* `/milimo roles` — List active operational permissions.
* `/milimo mesh` — Display visual inter-sandbox gateway topology.
* `/milimo help` — Retrieve the comprehensive interactive handbook.

---

## 📐 Architecture & Security Blueprint

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                             MILIMO MESH TUI                            │
 │                                                                        │
 │   [Content Claw]        [Ops Claw]       [Analytics]      [Finance]    │
 │       Sandboxed          Sandboxed        Sandboxed       Sandboxed    │
 │                                                                        │
 │          ▲                   ▲                ▲               ▲        │
 │          │                   │                │               │        │
 │          └───────────┬───────┴────────────────┴───────────────┘        │
 │                      ▼                                                 │
 │             [OpenShell Gateway Store]                                  │
 │           (Typed Message Contract Bus)                                 │
 │                      ▲                                                 │
 │                      │                                                 │
 │                      ▼                                                 │
 │         [Lucy Stateful Orchestrator] ◄────────► [Solo War Room TUI]    │
 │             (Assistant Sandbox Harness)          (Dashboard HOLD Alerts)│
 └────────────────────────────────────────────────────────────────────────┘
```

* **Zero-Trust File Isolation**: Sandboxes cannot traverse sibling filesystems. All interaction occurs strictly via typed contracts over localhost gateway sockets.
* **Privacy Router**: Sensitive credentials and operational variables are held in the OpenShell Gateway Store. Local classification filters automatically redact client records and source files.
* **Continuous Self-Evolution**: Claws analyze execution outcomes and autonomously write, test (via sandboxed Pytest backtesting), and register fresh Python tools every Sunday.

---

## 🧪 Testing and Quality Control

Milimo Claw enforces absolute type safety and robust validation protocols:

```bash
# Run the TypeScript Plugin Engine Test Suite (Vitest)
cd milimo && npm test

# Run the Python Orchestration & Pipeline Test Suite (Pytest)
# (Ensure PYTHONPATH maps to the local workspace)
cd milimo-blueprint && PYTHONPATH=.:orchestrator uv run pytest
```

---

## 📄 License & Creator

* **License**: Apache-2.0 — see [LICENSE](LICENSE).
* **Author**: **Mainza Kangombe** — [LinkedIn Profile](https://www.linkedin.com/in/mainza-kangombe-6214295)
