# SOLO TEMPLATE IMPROVEMENT PLAN

**Document Purpose:** Gap analysis between the MILIMO_CLAW_SOLO_TEMPLATE_SPEC.md and current implementation, with prioritized remediation roadmap.

**Generated:** 2026-03-20
**Status:** Draft for Review

---

## EXECUTIVE SUMMARY

The Milimo Claw solo template is **~75% implemented** compared to the spec. Core abstractions exist (approval modes, evolution cycle, privacy router, message contracts), but several critical integrations are incomplete or missing, particularly around real-time inter-claw communication, revenue tracking, and production gateway integration.

**Priority Fixes Required:**
1. Revenue Widget in War Room TUI
2. Morning Brief / Evening Wrap automation
3. Deep Work Mode CLI integration
4. Gateway integration for real-time inter-claw messaging
5. Actual health data collection mechanism

---

## GAP ANALYSIS BY SPEC SECTION

### 1. THE FIVE CLAWS

| Spec Requirement | Implementation Status | Gap Details |
|------------------|----------------------|-------------|
| Filesystem mounts (`/sandbox/content`, etc.) | PARTIAL | Config defined in solo_sandbox.py, but no actual mount creation automation. Requires sudo, not integrated into onboarding flow. |
| Network egress per claw | IMPLEMENTED | All 5 sandbox policies define network access correctly. |
| Inference routing per claw | IMPLEMENTED | Privacy router handles locked routes for finance/build claws. |
| Inter-claw message routing | PARTIAL | File-based queue works, but no real-time OpenShell gateway connection. |

**Gap Severity: MEDIUM** — Works for testing, but production requires real gateway.

---

### 2. WAR ROOM

| Spec Requirement | Implementation Status | Gap Details |
|------------------|----------------------|-------------|
| Action queue display | IMPLEMENTED | Blessed TUI shows queue with color-coded priorities. |
| Claw health panel | PARTIAL | Data structures exist, but reads from static file. No real-time health collection. |
| Evolution log | IMPLEMENTED | Displays tool deployments, enable/disable works. |
| **Revenue Widget** | **MISSING** | **Not implemented. Spec requires: this week's revenue, invoices paid, invoices pending, week-over-week change.** |
| Morning Brief (07:00) | PARTIAL | Python `solo_warroom.py` generates brief, but no TypeScript integration or scheduler. |
| Evening Wrap (20:00) | PARTIAL | Same as above — Python exists, no TS integration. |
| HOLD/REVIEW/AUTO/VETO modes | IMPLEMENTED | All 4 modes functional with correct escalation. |
| Finals Mode toggle | IMPLEMENTED | Keyboard shortcut 'F' in blessed TUI. |

**Gap Severity: HIGH** — Revenue widget and digest automation are core UX features.

---

### 3. SELF-EVOLUTION CYCLE

| Spec Requirement | Implementation Status | Gap Details |
|------------------|----------------------|-------------|
| Stage 1: OBSERVE | IMPLEMENTED | Reads operational logs, action summaries, cross-signals. |
| Stage 2: IDENTIFY | IMPLEMENTED | Pattern detection with confidence scoring. |
| Stage 3: PROPOSE | IMPLEMENTED | Tool nomination with permission validation. |
| Stage 4: BUILD & TEST | PARTIAL | Skeleton code fallback. No inference-based code generation. Backtesting is simulated. |
| Stage 5: DEPLOY | IMPLEMENTED | Tool registry registration works. |
| Minimum thresholds | IMPLEMENTED | All 5 claws have thresholds defined in evolution_config.yaml. |
| Permission enforcement | IMPLEMENTED | Evolution cannot expand claw permissions — validated at build stage. |

**Gap Severity: MEDIUM** — Evolution logic is sound, but actual tool quality depends on inference integration.

---

### 4. PRIVACY ROUTER

| Spec Requirement | Implementation Status | Gap Details |
|------------------|----------------------|-------------|
| Cloud/Local NIM/vLLM backends | PARTIAL | Routes defined, but no actual backend API integration. |
| Locked routes (financial, source_code) | IMPLEMENTED | `PrivacyPolicyViolationError` raised correctly. |
| Cost guard (100k daily tokens) | IMPLEMENTED | Budget tracking with alerts and fallback. |
| Automatic fallback | IMPLEMENTED | Never blocks claw action — falls back gracefully. |

**Gap Severity: LOW** — Abstraction is correct, integration pending backend selection.

---

### 5. DEEP WORK MODE

| Spec Requirement | Implementation Status | Gap Details |
|------------------|----------------------|-------------|
| Policy hot-reload | PARTIAL | Python `solo_deep_work.py` updates policies, but no CLI command. |
| Auto-response template | IMPLEMENTED | Template matches spec exactly. |
| Resume date handling | IMPLEMENTED | Scheduled resume with policy restoration. |
| **CLI integration** | **MISSING** | **No `milimo squad finals-mode` command in TypeScript.** |

**Gap Severity: HIGH** — Spec explicitly documents CLI command that doesn't exist.

---

### 6. INTER-CLAW COORDINATION

| Spec Requirement | Implementation Status | Gap Details |
|------------------|----------------------|-------------|
| Message contracts | IMPLEMENTED | All 15+ message types defined in contracts.py. |
| Message routing table | IMPLEMENTED | Matrix validation in mesh.py. |
| Gateway adapter | PARTIAL | Defined (Unix socket, WebSocket, file), but not connected to OpenShell. |
| Real-time delivery | MISSING | File-based polling only. No event-driven gateway. |
| Message encryption | MISSING | Not implemented. |

**Gap Severity: MEDIUM** — Works for solo mode, critical for squad deployment.

---

## DETAILED FILE-BY-FILE GAPS

### TypeScript Files (milimo/src/)

| File | Implemented | Missing |
|------|-------------|---------|
| `commands/onboard.ts` | Template selection, role assignment, config persistence | Filesystem mount creation integration, cost guard setup UI |
| `commands/warroom.ts` | Basic launcher | `--tier`, `--operator` flags, onboarding validation |
| `warroom/warroom-tui.ts` | Split-pane, keyboard shortcuts, color coding | **Revenue Widget**, morning brief panel |
| `warroom/approval.ts` | All 4 modes, escalation rules | Gateway integration, operator notification delivery |
| `warroom/audit.ts` | JSONL logging, append-only | Log rotation, search, external integration |
| `warroom/evolution.ts` | Log display, tool toggle | Proposal approval workflow, backtest results |
| `warroom/health-dashboard.ts` | Data structures, rendering | **Actual health collection**, heartbeat mechanism |
| `warroom/rate-limiter.ts` | Token bucket, FREE/PRO tiers | Stripe verification for PRO tier |
| `onboard/template.ts` | Discovery, metadata loading | Template validation, custom creation wizard |

### Python Files (milimo-blueprint/orchestrator/)

| File | Implemented | Missing |
|------|-------------|---------|
| `solo_init.py` | YAML loading, validation | Actual mount creation calls |
| `solo_warroom.py` | Queue, brief/wrap generation | **TS integration**, WebSocket for real-time |
| `solo_privacy.py` | Routing, locked routes, cost guard | Inference backend API calls |
| `evolution_cycle.py` | All 5 stages | Inference-based code generation, sandbox backtesting |
| `pattern_detector.py` | All pattern types | ML-based semantic detection |
| `tool_builder.py` | Build flow, backtest simulation | Real execution, sandbox isolation |
| `mesh.py` | Topology, routing, validation | **OpenShell gateway connection**, encryption |
| `contracts.py` | Message types, matrix validation | Payload schema validation, versioning |
| `solo_deep_work.py` | Policy updates, resume handling | **CLI command integration** |

---

## MISSING CONFIGURATION

| Config File | Status | Notes |
|-------------|--------|-------|
| `templates/solo-founder.yaml` | IMPLEMENTED | Comprehensive, matches spec. |
| `roles/*.yaml` (5 files) | IMPLEMENTED | All 5 claw blueprints exist. |
| `policies/*.yaml` (5 files) | IMPLEMENTED | All 5 sandbox policies exist. |
| `mesh_config.yaml` | IMPLEMENTED | Message matrix and escalation rules. |
| `evolution_config.yaml` | IMPLEMENTED | Cycle scheduling and thresholds. |
| `privacy_policy.yaml` | IMPLEMENTED | Locked routes and fallbacks. |

---

## PRIORITIZED REMEDIATION ROADMAP

### PHASE 1: Critical UX Gaps (Week 1-2)

**Priority: P0 — User-Facing Missing Features**

| Task | Effort | Impact |
|------|--------|--------|
| 1.1 Revenue Widget in War Room TUI | 2 days | HIGH — Core War Room feature |
| 1.2 Morning Brief automation | 1 day | HIGH — Daily operator touchpoint |
| 1.3 Evening Wrap automation | 1 day | HIGH — Daily operator touchpoint |
| 1.4 Deep Work Mode CLI command (`milimo squad finals-mode`) | 2 days | HIGH — Explicitly documented in spec |
| 1.5 Health data collection mechanism | 2 days | MEDIUM — Currently static |

**Deliverables:**
- `warroom/warroom-tui.ts`: Add revenue widget to right panel
- `warroom/digest.ts`: New file for brief/wrap generation and scheduling
- `commands/finals-mode.ts`: New CLI command
- `warroom/health-collector.ts`: New file for real health monitoring

---

### PHASE 2: Gateway Integration (Week 3-4)

**Priority: P1 — Production Infrastructure**

| Task | Effort | Impact |
|------|--------|--------|
| 2.1 OpenShell gateway connection | 3 days | HIGH — Real-time messaging foundation |
| 2.2 Message encryption | 2 days | MEDIUM — Security requirement |
| 2.3 WebSocket adapter for War Room | 2 days | HIGH — Real-time queue updates |
| 2.4 Operator notification delivery | 2 days | MEDIUM — Urgent item escalation |

**Deliverables:**
- `mesh/gateway-client.ts`: TypeScript gateway client
- `mesh/message-encryption.ts`: End-to-end encryption
- Update `warroom-tui.ts` for WebSocket events

---

### PHASE 3: Evolution Enhancement (Week 5-6)

**Priority: P2 — Quality Improvement**

| Task | Effort | Impact |
|------|--------|--------|
| 3.1 Inference-based tool generation | 3 days | MEDIUM — Improves tool quality |
| 3.2 Real backtesting in sandbox | 3 days | HIGH — Validates tools properly |
| 3.3 Tool provenance signing | 2 days | MEDIUM — Audit trail |
| 3.4 Automatic rollback on regression | 2 days | MEDIUM — Safety mechanism |

**Deliverables:**
- Update `tool_builder.py` for inference generation
- `evolution/sandbox-runner.py`: Isolated backtest execution
- `tool_registry.py`: Provenance tracking

---

### PHASE 4: Polish & Production Hardening (Week 7-8)

**Priority: P3 — Operational Excellence**

| Task | Effort | Impact |
|------|--------|--------|
| 4.1 Audit log rotation and archival | 1 day | LOW — Maintenance |
| 4.2 Log search functionality | 1 day | LOW — Operator convenience |
| 4.3 Filesystem mount automation | 3 days | MEDIUM — Setup automation |
| 4.4 Template validation wizard | 2 days | LOW — Developer experience |
| 4.5 Stripe integration for PRO tier | 2 days | MEDIUM — Revenue enablement |

---

## SPEC DEVIATIONS REQUIRING DISCUSSION

The following implementation choices differ from spec and need stakeholder input:

1. **Evolution time**: Spec says 02:00 Sunday, config says 03:00 Sunday. Which is correct?

2. **Revenue Widget data source**: Spec shows "week's revenue" but no Finance Claw → War Room message type defined. Need to add `finance_summary` message type.

3. **Morning Brief format**: Spec mentions "digest" but format not specified. Python generates brief, but display format in TUI undefined.

4. **Cost guard token counting**: Spec says "tokens" but actual tokenization requires tokenizer library. Currently uses character approximation.

5. **Health collection interval**: Spec doesn't define how often health should refresh. Currently 3-second polling.

---

## SUCCESS CRITERIA

The solo template is considered "spec-complete" when:

1. ✅ War Room shows all 4 panels: queue, health, evolution log, **revenue widget**
2. ✅ Morning Brief arrives at 07:00 without manual trigger
3. ✅ Evening Wrap arrives at 20:00 without manual trigger
4. ✅ `milimo squad finals-mode` command works as documented
5. ✅ Inter-claw messages route through OpenShell gateway (not just file queues)
6. ✅ Health panel shows real-time data, not static file reads
7. ✅ Evolution Cycle generates working tools (not skeletons)
8. ✅ Privacy router raises `PrivacyPolicyViolationError` on locked route violations
9. ✅ Cost guard enforces 100k daily token budget with fallback
10. ✅ Deep Work Mode hot-reloads policies and sends auto-responses

---

## APPENDIX: Implementation Status Summary

```
IMPLEMENTATION COMPLETION MATRIX
================================

Core Systems:
  [████████░░] 80% — Onboarding
  [██████░░░░] 60% — War Room TUI
  [████████░░] 80% — Approval Engine
  [████████░░] 80% — Evolution Cycle
  [█████████░] 90% — Privacy Router
  [██████░░░░] 60% — Inter-Claw Messaging

Missing Features:
  [░░░░░░░░░░]  0% — Revenue Widget
  [░░░░░░░░░░]  0% — Morning Brief Automation
  [░░░░░░░░░░]  0% — Deep Work CLI
  [░░░░░░░░░░]  0% — Gateway Integration

Configuration:
  [██████████] 100% — solo-founder.yaml
  [██████████] 100% — Role blueprints (5/5)
  [██████████] 100% — Sandbox policies (5/5)
  [██████████] 100% — Mesh config
  [██████████] 100% — Evolution config
  [██████████] 100% — Privacy policy

OVERALL: [███████░░░] ~75%
```

---

*Document generated from spec comparison. Update as gaps are closed.*
