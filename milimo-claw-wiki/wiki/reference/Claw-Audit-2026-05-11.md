---
title: "Claw Audit — 2026-05-11"
tags: [audit, nemoclaw, milimo, redundancy, harness]
created: 2026-05-11
updated: 2026-05-11
---

# Claw Audit — 2026-05-11

> NemoClaw v0.0.38 × Milimo Claw — Full Architectural Audit

## Audit Scope

| Dimension | Value |
|-----------|-------|
| **NemoClaw Version** | v0.0.38 (Alpha) |
| **Source** | `~/.nemoclaw/source/` |
| **Milimo Source** | `/Users/mck/Desktop/MilimoClaw/` |
| **Phases Completed** | 1–7 (Full) |
| **Redundancies Found** | 5 (2 actionable, 1 complementary, 2 cosmetic) |
| **Harness Gaps Found** | 10 (3 high, 5 medium, 2 low) |

## Key Findings

### 🔴 Critical: Inference Client Bypasses L7 Proxy (R1)

`inference_client.py` makes direct `urllib.request` calls to `integrate.api.nvidia.com`, manually configuring proxy settings and disabling SSL verification. NemoClaw's L7 proxy handles all of this transparently.

**Impact:** Duplicated code (194 lines), security risk (SSL disabled), inconsistent routing.
**Action:** Replace HTTP transport with OpenAI-compatible SDK calls through the proxy. Keep `InferenceUsage` and `CATEGORY_MODELS` (no NemoClaw equivalent).

### 🔴 Critical: Lifecycle Hooks Unused (H1)

NemoClaw provides `before_agent_start` and `before_tool_call` hooks. NemoClaw itself uses both (runtime context injection + secret scanning). Milimo registers NEITHER.

**Impact:** Missed opportunity to inject squad context, enforce cost guard at the agent level, and intercept expensive operations.
**Action:** Register both hooks in `milimo/src/index.ts`.

### 🔴 Critical: Credential Store Ignored (H3/R2)

NemoClaw's credential store manages 15 credential types with in-memory staging + gateway registration. Milimo writes directly to `/etc/environment` in the container, which doesn't survive sandbox rebuild.

**Impact:** Credentials lost on rebuild, plaintext in container filesystem.
**Action:** Use `nemoclaw credentials set` for all credential injection.

### 🟡 Medium: Channel Bridges Untapped (H5)

NemoClaw supports Telegram, Discord, and Slack bridges. Milimo's assistant persona could push notifications through these channels for morning briefs, HOLD alerts, and revenue updates.

### 🟡 Medium: Policy Presets Not Shipped (H4)

NemoClaw has 12 built-in policy presets. Milimo claws need access to Stripe, Vercel, and Sentry APIs — these should be shipped as Milimo-specific presets.

### 🟡 Medium: Service Registration Not Used (H10)

NemoClaw's `registerService()` API could manage the Claw Launcher lifecycle, replacing manual PID file management.

## Preserved Constraints

| Constraint | Status |
|-----------|--------|
| Cost Guard (50k daily tokens) | ✅ SACRED — no NemoClaw equivalent |
| Finance REVIEW→HOLD flow | ✅ PRESERVED — NemoClaw approval is network-only |
| Eight Sequencing Rules | ✅ PRESERVED — unique Milimo IP |
| War Room TUI | ✅ PRESERVED — different purpose than openshell term |
| Mesh Coordinator | ✅ PRESERVED — no NemoClaw equivalent |

## Sprint Plan

| Sprint | Items | Effort |
|--------|-------|--------|
| **Sprint 1 (P0-P1)** | H1 (hooks), R1 (inference), H3 (credentials), H5 (channels) | ~12-15 hrs |
| **Sprint 2 (P2)** | R2 (install.sh), H4 (presets), H10 (service) | ~5-7 hrs |
| **Sprint 3 (P3-P4)** | H2, H6, H8, H9, R4, H7 | ~10-12 hrs |

## Methodology

1. **Phase 1:** Verified NemoClaw v0.0.38 installation and mapped directory structure
2. **Phase 2:** Read all 67+ NemoClaw lib modules, plugin source, and blueprint definition
3. **Phase 3:** Read all 44 Milimo orchestrator modules, plugin source, and install script
4. **Phase 4:** Cross-referenced every Milimo module against NemoClaw equivalents
5. **Phase 5:** Identified all NemoClaw APIs/hooks not used by Milimo
6. **Phase 6:** Ranked findings by Impact × Ease into priority tiers
7. **Phase 7:** Generated wiki pages and audit report

## Files Examined

### NemoClaw (Key Files)
- `~/.nemoclaw/source/src/nemoclaw.ts` — Main CLI dispatch
- `~/.nemoclaw/source/nemoclaw/src/index.ts` — Plugin entry (436 lines)
- `~/.nemoclaw/source/nemoclaw/src/runtime-context.ts` — Lifecycle hooks (502 lines)
- `~/.nemoclaw/source/src/lib/credentials/store.ts` — Credential management (767 lines)
- `~/.nemoclaw/source/src/lib/inference/health.ts` — Health probes (328 lines)
- `~/.nemoclaw/source/src/lib/state/gateway.ts` — Gateway state (175 lines)
- `~/.nemoclaw/source/nemoclaw/openclaw.plugin.json` — Plugin manifest
- `~/.nemoclaw/source/nemoclaw-blueprint/blueprint.yaml` — Blueprint definition
- `~/.nemoclaw/source/AGENTS.md` — Architecture reference

### Milimo Claw (Key Files)
- `milimo/src/index.ts` — Plugin entry (209 lines)
- `milimo/src/cli.ts` — CLI registrar (515 lines)
- `milimo/src/warroom/warroom-tui.ts` — War Room TUI (663 lines)
- `milimo-blueprint/orchestrator/bridge_cli.py` — Bridge CLI (2088 lines)
- `milimo-blueprint/orchestrator/claw_launcher.py` — Process supervisor (1559 lines)
- `milimo-blueprint/orchestrator/mesh.py` — Mesh coordinator (646 lines)
- `milimo-blueprint/orchestrator/gateway_adapter.py` — Gateway adapter (763 lines)
- `milimo-blueprint/orchestrator/inference_client.py` — Inference client (282 lines)
- `install.sh` — Installer (1263 lines)
- `milimo/openclaw.plugin.json` — Plugin manifest

## See Also

- [[NemoClaw Reference]]
- [[NemoClaw × Milimo Integration Map]]
- [[Milimo Claw Architecture]]
