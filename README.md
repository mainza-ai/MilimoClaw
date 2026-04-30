# 🦀 Milimo Claw

<p align="center">
  <img src="assets/Milimo-Claw.png" alt="Milimo Claw Logo" width="800" />
</p>

> *"Your friend group is a startup. Your laptops are the infrastructure. Your claws do the work."*

[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](LICENSE)
[![Built on NemoClaw](https://img.shields.io/badge/built_on-NemoClaw-purple)](https://github.com/NVIDIA/NemoClaw)

**Milimo Claw** is a multi-agent autonomous hustle platform built on [NVIDIA NemoClaw](https://github.com/NVIDIA/NemoClaw). It turns a squad of college students — each running a NemoClaw sandbox on their RTX laptop — into a coordinated AI-powered business operation that runs 24/7.

> **On the name:** *Milimo* (mi-LEE-mo) is a name from the Tonga language of Zambia, meaning **"works," "tasks," or "labour."**

---

## Quick Start

### Prerequisites

- **macOS** (Apple Silicon) or **Linux** with Docker
- **Node.js** 22.16+
- **Python 3.11+**
- **NVIDIA API Key** — get one at [build.nvidia.com](https://build.nvidia.com/)
- **GitHub Personal Access Token** (for Build Claw) — [github.com/settings/tokens](https://github.com/settings/tokens)

### Installation

```bash
# 1. Install NemoClaw (export your NVIDIA API key first)
export NVIDIA_API_KEY=nvapi-your-key
curl -fsSL https://www.nemoclaw.sh | bash

# 2. Clone and configure environment
git clone https://github.com/mainza-ai/MilimoClaw.git
cd MilimoClaw
cp .env.example .env
# Edit .env and add your API keys (NVIDIA_API_KEY, GITHUB_TOKEN, GITHUB_REPO, etc.)

# 3. Install Milimo Claw (Dockerfile mode — bakes plugin into custom sandbox image)
./install.sh --solo --operator-name "your-name" --squad-name "your-squad" --non-interactive

# Alternative: runtime-deploy mode (inject into a running sandbox without rebuilding)
# ./install.sh --solo --operator-name "your-name" --squad-name "your-squad" --runtime-deploy

# 4. Connect NemoClaw assistant
nemoclaw my-assistant connect

# 5. Open the chat UI (approve device if prompted)
openclaw tui
# If needed: openclaw devices approve --latest
```

That's it. Your six autonomous claws (Content, Ops, Analytics, Finance, Build, Assistant) are now running.

---

## The Six Claws

| Claw | Role | Mount |
|------|------|-------|
| 🎨 **Content** | Posts, copy, campaigns | `/sandbox/content` |
| 📋 **Ops** | Client lifecycle, delivery | `/sandbox/clients` |
| 📊 **Analytics** | Intelligence, reports | `/sandbox/analytics` |
| 💰 **Finance** | Invoicing, pricing | `/sandbox/finance` |
| 🔧 **Build** | Code, PRs, deploys | `/sandbox/build` |
| 🤖 **Assistant** | Coordination, mesh dispatch | `/sandbox/assistant` |

Each claw has its own sandbox, network policy, and self-evolution cycle. Claws communicate through typed inter-sandbox messages — not shared files.

---

## Key Commands

```bash
# War Room (approval dashboard)
openclaw milimo warroom

# Squad status
openclaw milimo squad status

# Blueprint operations
openclaw milimo blueprint list
openclaw milimo blueprint fork <source>
openclaw milimo blueprint publish

# Chat commands (inside openclaw tui)
/milimo status    # Squad status
/milimo roles     # Available claw roles
/milimo mesh      # Mesh topology
/milimo help      # Full command list
```

---

## Architecture

Milimo Claw runs on top of the NemoClaw stack, inheriting its security sandbox (OpenShell + Landlock + seccomp + capability drops) while adding multi-agent coordination:

- **Each claw = isolated sandbox** with kernel-level filesystem and network isolation
- **Privacy router** — sensitive data (finance, source code, client contacts) never leaves the device
- **Self-evolving** — claws build and deploy new tools weekly through a backtested evolution pipeline
- **Blueprint versioning** — every claw's state is a versioned, forkable artifact
- **Assistant claw (Lucy)** — coordinates all claws via mesh dispatch, accessible through TUI or Telegram

### Two Deployment Models

| Model | Description | When to Use |
|-------|-------------|-------------|
| **Dockerfile (default)** | `install.sh` generates a Dockerfile and runs `nemoclaw onboard --from` to bake the plugin into a custom sandbox image | **Recommended** — official NemoClaw plugin path |
| **Runtime Deploy** | `install.sh --runtime-deploy` injects files into a running sandbox via `docker cp` + `kubectl cp` | Quick updates without rebuilding |
| **Docker Compose** | Each claw runs in its own container (`docker-compose up`) | Alternative for isolated deployments |

For full technical details, see [milimo-claw-docs/ARCHITECTURE.md](milimo-claw-docs/ARCHITECTURE.md).

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](milimo-claw-docs/CLI_REFERENCE.md) | All commands |
| [Architecture](milimo-claw-docs/ARCHITECTURE.md) | Technical deep-dive |
| [Privacy & Security](milimo-claw-docs/PRIVACY_AND_SECURITY.md) | Data routing, isolation |
| [Blueprint Economy](milimo-claw-docs/BLUEPRINT_ECONOMY.md) | Versioning, marketplace |
| [Project Description](milimo-claw-docs/MILIMO_CLAW_PROJECT_DESCRIPTION.md) | Full product spec |
| [Sandbox File Sharing](milimo-claw-docs/guides/SANDBOX_FILE_SHARING.md) | How to share files with claws |
| [Contributing](milimo-claw-docs/guides/CONTRIBUTING.md) | Dev guidelines |

### Wiki

| Section | Description |
|---------|-------------|
| [Security Best Practices](milimo-claw-wiki/wiki/security/best-practices.md) | Policy tiers, posture profiles, hardening |
| [Sandbox Hardening](milimo-claw-wiki/wiki/security/sandbox-hardening.md) | Landlock, seccomp, capability drops |
| [Credential Storage](milimo-claw-wiki/wiki/security/credential-storage.md) | Gateway store, env vars, rotation |
| [OpenClaw Controls](milimo-claw-wiki/wiki/security/openclaw-controls.md) | Device auth, secret redaction, memory scanner |

---

## Testing

```bash
# TypeScript (Jest) — 318 tests
cd milimo && npm test

# Python (pytest) — 1,192 tests
cd milimo-blueprint && python3 -m pytest tests/ -v
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
