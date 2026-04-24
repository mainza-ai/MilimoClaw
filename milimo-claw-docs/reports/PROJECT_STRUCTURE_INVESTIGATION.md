> ⚠️ **DEPRECATED** — Historical status report. All phases complete. See [README.md](../../README.md) for current state.

---
# Project Structure Investigation Report

**Date:** March 2026
**Project:** MilimoClaw

---

## Project Overview

MilimoClaw is a **multi-agent autonomous hustle platform** built as an OpenClaw plugin that extends NemoClaw. It runs on top of NVIDIA OpenShell for sandbox isolation and inference routing.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OpenShell (Host)                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                           OpenClaw CLI                                 │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │  │
│  │  │  NemoClaw       │  │  MilimoClaw     │  │  Other Plugins       │  │  │
│  │  │  Plugin         │  │  Plugin         │  │  (discord, slack...) │  │  │
│  │  │  (base)         │  │  (extension)    │  │                      │  │  │
│  │  └────────┬────────┘  └────────┬────────┘  └──────────────────────┘  │  │
│  │           │                    │                                      │  │
│  │           ▼                    ▼                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      Sandbox (Docker)                          │  │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐   │  │  │
│  │  │  │  OpenClaw Agent Runtime                                  │   │  │  │
│  │  │  │  - Python Orchestrator (blueprint)                      │   │  │  │
│  │  │  │  - TypeScript CLI Commands                              │   │  │  │
│  │  │  │  - War Room TUI                                         │   │  │  │
│  │  │  └─────────────────────────────────────────────────────────┘   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Inference Routing:  Agent → OpenShell Gateway → Provider                   │
│  ├── NVIDIA Cloud (build.nvidia.com)                                        │
│  ├── Local NIM Service                                                      │
│  └── vLLM                                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

### Project Root

```
MilimoClaw/
├── milimo/                    # MilimoClaw TypeScript plugin
├── milimo-blueprint/          # Python orchestrator & blueprints
├── nemoclaw/                  # NemoClaw TypeScript plugin (base)
├── nemoclaw-blueprint/        # NemoClaw Python orchestrator
├── milimo-server/             # War Room API server (Fastify)
├── milimo-mobile/             # Mobile War Room app (React Native)
├── milimo-admin/              # Admin dashboard (React)
├── docs/                      # Documentation (NemoClaw docs)
├── milimo-claw-docs/          # MilimoClaw documentation
├── scripts/                   # Utility scripts
├── test/                      # Test suite
├── Dockerfile                 # Docker image definition
└── docker-compose.yml         # Docker compose configuration
```

---

## Component Breakdown

### 1. NemoClaw (Base Plugin)

**Purpose:** Foundation plugin that provides OpenClaw sandbox management inside OpenShell.

**Location:** `nemoclaw/` and `nemoclaw-blueprint/`

**Key Files:**

| File | Purpose |
|------|---------|
| `nemoclaw/src/index.ts` | Plugin entry point, registers slash commands and CLI |
| `nemoclaw/src/cli.ts` | Registers `openclaw nemoclaw` CLI commands |
| `nemoclaw/src/commands/*.ts` | Individual command implementations |
| `nemoclaw-blueprint/orchestrator/runner.py` | Blueprint runner for sandbox lifecycle |
| `nemoclaw-blueprint/blueprint.yaml` | Blueprint manifest with inference profiles |

**Commands Provided:**

| Command | Description |
|---------|-------------|
| `openclaw nemoclaw launch` | Bootstrap OpenClaw in OpenShell |
| `openclaw nemoclaw status` | Show sandbox and inference state |
| `openclaw nemoclaw connect` | Interactive shell into sandbox |
| `openclaw nemoclaw logs` | Stream sandbox logs |
| `openclaw nemoclaw eject` | Rollback to host installation |
| `openclaw nemoclaw onboard` | Configure inference endpoint |
| `/nemoclaw status` | Chat slash command |

---

### 2. MilimoClaw (Extension Plugin)

**Purpose:** Multi-agent hustle platform with squad mesh, claw roles, War Room, and blueprint economy.

**Location:** `milimo/` and `milimo-blueprint/`

**Key Files:**

| File | Purpose |
|------|---------|
| `milimo/src/index.ts` | Plugin entry point |
| `milimo/src/cli.ts` | Registers `openclaw milimo` CLI commands |
| `milimo/src/commands/init.ts` | Squad initialization |
| `milimo/src/commands/squad.ts` | Squad management, finals mode |
| `milimo/src/commands/blueprint.ts` | Blueprint operations |
| `milimo/src/commands/warroom.ts` | War Room TUI |
| `milimo/src/commands/health.ts` | Health dashboard |
| `milimo/src/commands/badge.ts` | Performance badges |
| `milimo/src/commands/payment.ts` | Stripe integration |
| `milimo/src/commands/verify.ts` | Provenance verification |

**Blueprint Orchestrator:** `milimo-blueprint/orchestrator/`

| File | Purpose |
|------|---------|
| `evolution_cycle.py` | Weekly self-evolution pipeline |
| `mesh.py` | Mesh coordinator with gateway |
| `privacy_router.py` | Sensitivity classification & routing |
| `blueprint_manager.py` | Blueprint lifecycle management |
| `marketplace_manager.py` | Blueprint marketplace |
| `provenance_signer.py` | Ed25519 blueprint signing |
| `provenance_verifier.py` | Signature verification |
| `chain_validator.py` | Provenance chain validation |
| `attestation_generator.py` | Performance attestation |
| `tool_generator.py` | LLM-based tool generation |
| `cohort_creator.py` | Bulk squad creation |
| `role_assigner.py` | Role assignment |
| `solo_init.py` | Solo founder template loader |
| `solo_sandbox.py` | Solo sandbox initializer |
| `solo_warroom.py` | Solo War Room queue |
| `solo_privacy.py` | Solo inference router |
| `solo_evolution.py` | Solo evolution scheduler |
| `solo_deep_work.py` | Deep work mode |

**Commands Provided:**

| Command | Description |
|---------|-------------|
| `openclaw milimo init` | Initialize squad with template |
| `openclaw milimo squad status` | Show squad status |
| `openclaw milimo squad assign-role` | Assign claw role |
| `openclaw milimo squad finals-mode` | Activate deep work mode |
| `openclaw milimo blueprint list` | List available blueprints |
| `openclaw milimo blueprint publish` | Publish to marketplace |
| `openclaw milimo warroom` | Launch War Room TUI |
| `openclaw milimo health` | Health dashboard |
| `/milimo status` | Chat slash command |

---

### 3. War Room API Server

**Purpose:** REST/WebSocket API for War Room operations.

**Location:** `milimo-server/`

**Key Files:**

| File | Purpose |
|------|---------|
| `src/server.ts` | Fastify server entry point |
| `src/routes/auth.ts` | Authentication routes |
| `src/routes/pending.ts` | Pending actions |
| `src/routes/actions.ts` | Approve/veto actions |
| `src/routes/status.ts` | Squad status |
| `src/payments/stripe.ts` | Stripe integration |
| `src/tenants/manager.ts` | Tenant management |
| `src/tenants/provisioning.ts` | Resource provisioning |
| `src/tenants/limits.ts` | Limit enforcement |

---

### 4. Mobile App

**Purpose:** Mobile War Room for on-the-go approvals.

**Location:** `milimo-mobile/`

**Screens:**
- Pending actions list
- Action details & approve/veto
- Settings

---

### 5. Admin Dashboard

**Purpose:** Enterprise admin interface for tenant management.

**Location:** `milimo-admin/`

**Components:**
- Overview (tenant stats)
- Squads (squad management)
- Analytics (usage analytics)
- Cohorts (bulk creation)
- Logo (branding)
- Theme (theme configuration)
- TemplateManager (blueprint templates)

---

## Docker Setup

### Container Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Desktop (macOS)                    │
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │ openshell-cluster-  │    │        MilimoClaw           │ │
│  │ nemoclaw            │    │  (milimo-claw:latest)       │ │
│  │ (k3s cluster)       │    │                              │ │
│  │                     │    │  - OpenClaw 2026.3.11       │ │
│  │ Port: 8080          │    │  - Milimo Plugin v0.1.0     │ │
│  │                     │    │  - NemoClaw Plugin v0.1.0   │ │
│  └─────────────────────┘    │  - Python Orchestrator      │ │
│                              │  - Solo Founder Template    │ │
│                              └─────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dockerfile Key Points

```dockerfile
# Base image
FROM node:22-slim

# Install OpenClaw CLI
RUN npm install -g openclaw@2026.3.11

# Install Python dependencies
RUN pip3 install --break-system-packages pyyaml pytest

# Copy plugin and blueprint
COPY milimo/dist/ /opt/milimo/dist/
COPY milimo-blueprint/ /opt/milimo-blueprint/

# Install plugin
RUN openclaw plugins install /opt/milimo

# Configure inference (NVIDIA cloud)
# API key injected at runtime via NVIDIA_API_KEY env var
```

---

## Configuration Files

### ~/.nemoclaw/

```
~/.nemoclaw/
├── credentials.json    # NVIDIA API credentials
└── sandboxes.json      # Sandbox configurations
```

### ~/.openclaw/openclaw.json

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "${NEMOCLAW_MODEL}"
      }
    }
  },
  "models": {
    "providers": {
      "nvidia": {
        "baseUrl": "https://integrate.api.nvidia.com/v1",
        "api": "openai-completions",
        "models": [...]
      }
    }
  },
  "plugins": {
    "entries": {
      "milimo": { "enabled": true }
    }
  }
}
```

---

## Inference Profiles

| Profile | Provider | Endpoint | Model | Use Case |
|---------|----------|----------|-------|----------|
| default | nvidia | build.nvidia.com | the NEMOCLAW_MODEL default | Production |
| ncp | nvidia | Dynamic | the NEMOCLAW_MODEL default | NVIDIA Cloud Partner |
| nim-local | openai | nim-service.local:8000 | the NEMOCLAW_MODEL default | On-prem NIM |
| vllm | openai | localhost:8000 | Nemotron 30B | Local dev |

---

## Key Differences: NemoClaw vs MilimoClaw

| Feature | NemoClaw | MilimoClaw |
|---------|----------|------------|
| Purpose | Sandbox management | Multi-agent hustle platform |
| Slash Command | `/nemoclaw` | `/milimo` |
| Squad Mesh | ❌ | ✅ |
| Claw Roles | ❌ | ✅ (5 roles) |
| War Room TUI | ❌ | ✅ |
| Blueprint Economy | ❌ | ✅ |
| Payment Integration | ❌ | ✅ (Stripe) |
| Provenance | ❌ | ✅ (Ed25519) |
| Solo Founder | ❌ | ✅ |
| Deep Work Mode | ❌ | ✅ |
| Multi-tenant | ❌ | ✅ |

---

## References

- [NemoClaw Docs](docs/index.md)
- [MilimoClaw Docs](milimo-claw-docs/)
- [Solo Founder Template](milimo-blueprint/templates/solo-founder.yaml)
- [Quick Start Guide](milimo-claw-docs/guides/QUICK_START_MACOS.md)
