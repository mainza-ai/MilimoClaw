---
title: NemoClaw × Milimo Integration Map
tags: [reference, nemoclaw, milimo, integration]
created: 2026-05-11
updated: 2026-05-11
---

# NemoClaw × Milimo Integration Map

> Cross-reference of every NemoClaw capability against Milimo's usage status.

## Current Integration Points ✅

| NemoClaw API | Milimo Usage | File | Status |
|-------------|-------------|------|--------|
| `api.registerCommand()` | `/milimo` slash command | `milimo/src/index.ts` | ✅ Active |
| `api.registerCli()` | `openclaw milimo *` (16 subgroups) | `milimo/src/cli.ts` | ✅ Active |
| `api.pluginConfig` | Squad name, role, blueprint dir | `milimo/src/index.ts` | ✅ Active |
| `api.logger` | Registration banner, status | `milimo/src/index.ts` | ✅ Active |
| `api.on("before_agent_start")` | Squad context injection | `milimo/src/hooks/runtime-context.ts` | ✅ **NEW** |
| `api.on("before_tool_call")` | Cost guard enforcement | `milimo/src/hooks/runtime-context.ts` | ✅ **NEW** |
| `api.registerService()` | Claw launcher lifecycle | `milimo/src/hooks/claw-launcher-service.ts` | ✅ **NEW** |
| `nemoclaw onboard --from` | Dockerfile-based install | `install.sh` | ✅ Active |
| `nemoclaw channels *` | Channel bridge management | `milimo/src/commands/channels.ts` | ✅ **NEW** |
| `nemoclaw list` | Sandbox detection | `install.sh` | ⚠️ Fragile grep |
| `nemoclaw connect` | Assistant start | `commands/assistant.ts` | ✅ Active |

## Redundancies Resolved ✅

| Area | Was | Now | Status |
|------|-----|-----|--------|
| **Inference HTTP** | `inference_client.py` (urllib + manual proxy) | httpx through L7 proxy | ✅ Fixed |
| **Credential injection** | `/etc/environment` writes | Process env + NemoClaw guidance | ✅ Fixed |
| **Sandbox status** | grep parsing of `nemoclaw list` | Unchanged (P4 backlog) | ⚠️ Deferred |

## Harness Opportunities 🎯

### P0–P1 — Completed ✅

| NemoClaw Feature | Implementation | File |
|-----------------|---------------|------|
| **`before_agent_start` hook** | Injects `<milimo-squad>` context | `hooks/runtime-context.ts` |
| **`before_tool_call` hook** | Enforces cost guard + budget warnings | `hooks/runtime-context.ts` |
| **L7 proxy routing** | Replaced urllib with httpx through proxy | `inference_client.py` |
| **Credential store** | Removed /etc/environment writes | `install.sh` |
| **Channel bridges** | Full CLI + digest/HOLD notification delivery | `hooks/channel-notifier.ts` + `commands/channels.ts` |

### P2 — Completed ✅

| NemoClaw Feature | Implementation | File |
|-----------------|---------------|------|
| **Policy presets** | Shipped `stripe.yaml`, `vercel.yaml`, `sentry.yaml` | `milimo-blueprint/policies/presets/` |
| **`registerService()`** | Claw launcher managed by OpenClaw lifecycle | `hooks/claw-launcher-service.ts` |

### P3 — Future

| NemoClaw Feature | Integration Plan |
|-----------------|-----------------|
| **Sandbox snapshots** | Snapshot before blueprint publish / finals mode |
| **`api.resolvePath()`** | Use in bridge-tools.ts for SSRF-safe path resolution |
| **Sandbox rebuild/recover** | Coordinate with ClawLauncher ProcessSupervisor |
| **`nemoclaw doctor`** | Augment `openclaw milimo health --collect` |

## Milimo-Only Systems (No NemoClaw Equivalent)

These systems are **unique to Milimo** and must be preserved:

| System | Why It's Unique |
|--------|----------------|
| **Cost Guard** | NemoClaw has zero token/cost tracking |
| **Eight Sequencing Rules** | NemoClaw has no contract validation |
| **Finance REVIEW→HOLD** | NemoClaw approval is network-only |
| **War Room TUI** | Different purpose than `openshell term` |
| **Mesh Coordinator** | NemoClaw has no inter-agent messaging |
| **Claw Launcher** | NemoClaw has no process supervision for agents |
| **Blueprint Marketplace** | NemoClaw has no marketplace |
| **Evolution Scheduler** | NemoClaw has no tool evolution system |
| **Provenance Signing** | Complementary to NemoClaw digest (different scope) |
| **Lucy/Nova Persona** | NemoClaw has no assistant identity system |

## Integration Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────┐
│  OpenClaw Host                                               │
│  ├── NemoClaw Plugin                                        │
│  │   ├── before_agent_start → <nemoclaw-runtime> context    │
│  │   ├── before_tool_call → secret scanner                  │
│  │   └── registerProvider → inference routing               │
│  │                                                          │
│  ├── Milimo Plugin                                          │
│  │   ├── before_agent_start → <milimo-squad> context  ✅DONE │
│  │   ├── before_tool_call → cost guard enforcement    ✅DONE │
│  │   ├── registerCommand → /milimo                          │
│  │   ├── registerCli → openclaw milimo *                    │
│  │   └── registerService → claw launcher              ✅DONE │
│  │                                                          │
│  └── OpenShell Sandbox                                      │
│      ├── L7 Proxy ← inference_client.py routes through ✅DONE │
│      ├── Credential Store ← install.sh migrates to    ✅DONE │
│      ├── Policy Engine ← Milimo presets added         ✅DONE │
│      └── Channel Bridges ← assistant notifications    ✅DONE │
└─────────────────────────────────────────────────────────────┘
```

## See Also

- [[NemoClaw Reference]]
- [[Milimo Claw Architecture]]
- [[Claw Audit — 2026-05-11]]
