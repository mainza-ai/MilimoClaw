---
title: Milimo Claw Architecture
tags: [architecture, milimo, claws, mesh]
created: 2026-05-11
updated: 2026-05-11
---

# Milimo Claw Architecture

> Post-audit architecture document reflecting NemoClaw integration status.

## System Overview

Milimo Claw is an OpenClaw plugin that provides a **multi-agent squad** architecture on top of NemoClaw sandboxes. It consists of six specialized claws (Content, Ops, Analytics, Finance, Build, Assistant), coordinated through a file-based mesh, supervised by a process launcher, and operated through the War Room TUI.

```
┌─────────────────────────────────────────────────────────────┐
│  OPERATOR                                                    │
│  ├── openclaw milimo onboard (setup wizard)                 │
│  ├── openclaw milimo warroom (interactive TUI)              │
│  └── openclaw milimo squad status (topology view)           │
├─────────────────────────────────────────────────────────────┤
│  MILIMO PLUGIN (TypeScript — milimo/src/)                   │
│  ├── /milimo slash command                                  │
│  ├── 15 CLI subcommand groups                               │
│  ├── War Room TUI (blessed)                                 │
│  └── NemoClaw hooks: before_agent_start, before_tool_call   │
├─────────────────────────────────────────────────────────────┤
│  BLUEPRINT ORCHESTRATOR (Python — milimo-blueprint/)        │
│  ├── Bridge CLI (TypeScript ↔ Python)                       │
│  ├── Claw Launcher (process supervisor)                     │
│  ├── Mesh Coordinator (inter-claw messaging)                │
│  ├── Approval Engine (HOLD / REVIEW / AUTO)                 │
│  ├── Evolution Scheduler (tool lifecycle)                   │
│  ├── Cost Guard (50k daily token budget)                    │
│  └── Blueprint Manager (versioning, marketplace)            │
├─────────────────────────────────────────────────────────────┤
│  THE FIVE CLAWS + ASSISTANT                                 │
│  ├── 🎨 Content Claw (content strategy, drafts)            │
│  ├── ⚙️ Ops Claw (infrastructure, monitoring)              │
│  ├── 📊 Analytics Claw (metrics, insights)                 │
│  ├── 💰 Finance Claw (invoicing, payments — REVIEW→HOLD)   │
│  ├── 🔧 Build Claw (GitHub, Vercel, Sentry)                │
│  └── 🤖 Assistant Claw (Lucy/Nova persona)                 │
├─────────────────────────────────────────────────────────────┤
│  NEMOCLAW SANDBOX (OpenShell)                               │
│  ├── L7 Proxy (inference routing)                           │
│  ├── Credential Store (gateway-managed)                     │
│  ├── Network Policies (deny-by-default + presets)           │
│  └── Channel Bridges (Telegram/Discord/Slack)               │
└─────────────────────────────────────────────────────────────┘
```

## Module Map

### Plugin Layer (TypeScript)

| Module | Path | Purpose |
|--------|------|---------|
| Entry | `milimo/src/index.ts` | Plugin registration, hook wiring |
| CLI | `milimo/src/cli.ts` | 15 subcommand groups |
| Slash | `milimo/src/commands/slash.ts` | Chat command dispatch |
| War Room TUI | `milimo/src/warroom/warroom-tui.ts` | Blessed interactive dashboard |
| Approval Engine | `milimo/src/warroom/approval.ts` | HOLD/REVIEW/AUTO classification |
| Audit Logger | `milimo/src/warroom/audit.ts` | Decision audit trail |
| Evolution | `milimo/src/warroom/evolution.ts` | Tool lifecycle management |
| Digest | `milimo/src/warroom/digest.ts` | Morning/evening briefs |
| Health | `milimo/src/warroom/health-collector.ts` | Claw health aggregation |
| Bridge | `milimo/src/lib/bridge-tools.ts` | TypeScript → Python IPC |
| Mesh Client | `milimo/src/mesh/gateway-client.ts` | Gateway communication |
| Encryption | `milimo/src/mesh/message-encryption.ts` | AES-256-GCM for mesh messages |

### Orchestrator Layer (Python)

| Module | Path | Purpose |
|--------|------|---------|
| Bridge CLI | `orchestrator/bridge_cli.py` | JSON-RPC interface for TS→Python |
| Claw Launcher | `orchestrator/claw_launcher.py` | Process supervisor with heartbeats |
| Mesh | `orchestrator/mesh.py` | Inter-claw message routing |
| Gateway Adapter | `orchestrator/gateway_adapter.py` | Unix/WebSocket/File transport |
| Contracts | `orchestrator/contracts.py` | Message validation (8 rules) |
| Inference Client | `orchestrator/inference_client.py` | NVIDIA NIM API client |
| Blueprint Manager | `orchestrator/blueprint_manager.py` | Version management |
| Marketplace | `orchestrator/marketplace_manager.py` | Blueprint marketplace |
| Provenance | `orchestrator/provenance_signer.py` | Ed25519 blueprint signing |
| Privacy Router | `orchestrator/privacy_router.py` | Data classification |
| Solo War Room | `orchestrator/solo_warroom.py` | Solo operator mode |
| Deep Work | `orchestrator/solo_deep_work.py` | Finals/deep work mode |

## Sacred Constraints

These constraints are **non-negotiable** and must survive any refactoring:

### 1. Cost Guard (50k Daily Token Budget)
- Enforced by `rate-limiter.ts` and `cost_guard.py`
- `lighter_prompt` fallback activates when approaching limit
- No NemoClaw equivalent exists

### 2. Finance REVIEW→HOLD Two-Stage Approval
- All Finance Claw actions require operator REVIEW
- Payments above threshold escalate to HOLD
- Cannot be collapsed into a single approval step
- NemoClaw's approval (network requests) is a different system

### 3. Eight Sequencing Rules
- Defined in `contracts.py` via `ContractValidator`
- Govern valid message flows between claws
- No NemoClaw equivalent — this is Milimo's core protocol

### 4. Mesh Encryption (AES-256-GCM)
- Inter-claw messages encrypted when `mesh_secret` is configured
- NemoClaw has no inter-agent messaging at all

## NemoClaw Integration Status

| API | Status | Notes |
|-----|--------|-------|
| `registerCommand` | ✅ Active | `/milimo` slash command |
| `registerCli` | ✅ Active | 15 subcommand groups |
| `pluginConfig` | ✅ Active | Squad/role/blueprint config |
| `logger` | ✅ Active | Throughout |
| `on("before_agent_start")` | 🎯 Planned | Squad context injection |
| `on("before_tool_call")` | 🎯 Planned | Cost guard enforcement |
| `registerService` | 🎯 Planned | Claw launcher lifecycle |
| `registerProvider` | ❌ Not used | NemoClaw handles inference provider |
| `resolvePath` | 🎯 Planned | SSRF-safe path resolution |

## Data Flow

```
Operator → War Room TUI
              │
              ▼
         Approval Engine ─────────────── Audit Log
              │
              ▼
         Mesh Coordinator
         ┌────┼────┐────┐────┐────┐
         ▼    ▼    ▼    ▼    ▼    ▼
      Content Ops  Ana  Fin  Build Asst
         │    │    │    │    │    │
         └────┴────┴────┴────┴────┘
                   │
                   ▼
            L7 Proxy (NemoClaw)
                   │
                   ▼
            NVIDIA NIM API
```

## See Also

- [[NemoClaw Reference]]
- [[NemoClaw × Milimo Integration Map]]
- [[Claw Audit — 2026-05-11]]
- [[War Room TUI]]
- [[Mesh Coordinator]]
