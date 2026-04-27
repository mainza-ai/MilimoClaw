# MilimoClaw Wiki — Index

**Summary**: Master table of contents for the MilimoClaw knowledge base.

**Last updated**: 2026-04-23

**Tags**: #index #navigation

---

## Quick Navigation

| Section | Description | Pages |
|---------|-------------|-------|
| [[#Architecture]] | System design and isolation model | 10 |
| [[#Claws]] | Individual claw documentation | 6 |
| [[#Coordination]] | Message contracts and War Room | 5 |
| [[#Evolution]] | Self-evolution system | 8 |
| [[#Development]] | Conventions and testing | 3 |
| [[#Troubleshooting]] | Common issues and fixes | 4 |
| [[#Reference]] | Quick reference tables | 4 |
| [[#Configuration]] | Configuration files and schemas | 4 |
| [[#Solo]] | Solo system modules | 6 |
| [[#Templates]] | Squad templates | 8 |
| [[#Patterns]] | Cross-cutting implementation patterns | 1 |
| [[#Security]] | Provenance and attestation modules | 3 |
| [[#Operations]] | Health, metrics, and monitoring modules | 4 |
| [[#Scripts]] | Installation and service scripts | 3 |

---

## Architecture

System architecture and design documentation.

| Page | Description | Status |
|------|-------------|--------|
| [[system-overview]] | Eight-layer architecture overview | ✓ |
| [[sandbox-isolation]] | Landlock, seccomp, and filesystem isolation | ✓ |
| [[inter-claw-communication]] | Typed message contracts and routing | ✓ |
| [[mesh-coordinator]] | Inter-sandbox gateway and policies | ✓ |
| [[mesh-coordinator-modules]] | Mesh implementation details | ✓ |
| [[privacy-router]] | Inference routing and data sensitivity | ✓ |
| [[tool-generation]] | Core evolution system (tools, proposals, registry) | ✓ |
| [[claw-launcher]] | Claw startup and process supervision | ✓ |
| [[assistant-system]] | Conversational assistant configuration | ✓ |

---

## Claws

Documentation for each autonomous agent in the mesh.

| Claw | Role | Status |
|------|------|--------|
| [[content-claw]] | Creative department — posts, copy, campaigns | ✓ |
| [[ops-claw]] | Account manager — client lifecycle, delivery | ✓ |
| [[analytics-claw]] | Intelligence layer — reports, anomalies | ✓ |
| [[finance-claw]] | Financial system — invoicing, pricing | ✓ |
| [[build-claw]] | Engineering — code, PRs, deploys | ✓ |
| [[assistant-lucy]] | Conversational assistant — user interface | ✓ |

### Module Documentation

Detailed documentation for each code module:

**[[content-claw|Content]]**: content-init • content-generator • brief-manager • brand-voice • platform-publisher • content-scheduler • [[performance-monitor]] • [[publish-scheduler]]

**[[ops-claw|Ops]]**: ops-init • intake-manager • project-manager • health-scorer • ops-scheduler • [[comms-manager]] • [[scope-monitor]] • [[incident-analyzer]] • [[runbook-executor]] • [[webhook-server]]

**[[analytics-claw|Analytics]]**: analytics-init • signal-processor • anomaly-detector • opportunity-scorer • report-generator • [[baseline-manager]] • [[query-handler]] • [[forward-projector]] • [[collection-workers]] • [[data-collectors]]

**[[finance-claw|Finance]]**: finance-init • pricing-engine • invoice-manager • payment-monitor • revenue-tracker • [[payment-risk-scorer]] • [[expense-tracker]] • [[stripe-client]]

**[[build-claw|Build]]**: build-init • issue-manager • code-generator • pr-manager • deploy-manager • error-monitor

**[[assistant-lucy|Assistant]]**: lucy.py (TelegramBridge • PendingQuery • LucyAssistant)

---

## Coordination

Cross-claw coordination and messaging.

| Page | Description | Status |
|------|-------------|--------|
| [[message-contracts]] | All 24+ message type schemas | ✓ |
| [[contracts]] | Typed message contract definitions | ✓ |
| [[sequencing-rules]] | Non-negotiable ordering constraints | ✓ |
| [[approval-thresholds]] | REVIEW/HOLD/AUTO for each action | ✓ |
| [[war-room]] | TUI for pending action queue | ✓ |

---

## Evolution

Self-evolution and tool generation system.

| Page | Description | Status |
|------|-------------|--------|
| [[evolution-cycle]] | Sunday 5-stage evolution pipeline | ✓ |
| [[tool-generation]] | Inference-based tool creation | ✓ |
| [[pattern-detection]] | Identifying recurring patterns | ✓ |
| [[tool-generator]] | LLM-based tool code generation | ✓ |
| [[evolution-integration]] | Evolution cycle scheduler | ✓ |
| [[sandbox-runner]] | Isolated backtest execution | ✓ |
| [[marketplace-manager]] | Blueprint marketplace | ✓ |

---

## Development

Development conventions and guides.

| Page | Description | Status |
|------|-------------|--------|
| [[conventions]] | Code style and project conventions | ✓ |
| [[testing]] | Test structure and coverage | ✓ |
| [[debugging]] | Debugging guide and tools | ✓ |

---

## Troubleshooting

Common issues and fixes.

| Page | Description | Status |
|------|-------------|--------|
| [[common-issues]] | Frequently encountered problems | ✓ |
| [[issues-and-fixes]] | Comprehensive audit of past fixes | ✓ |
| [[sandbox-sync]] | Sandbox synchronization issues | ✓ |
| [[claw-silent-responses]] | Claws returning blank output | ✓ |
| [[sandbox-security-audit-2026-04-25]] | Critical: install.sh violates NemoClaw sandbox security model | ✓ |

---

## Reference

Quick reference tables and diagrams.

| Page | Description | Status |
|------|-------------|--------|
| [[ground-truth-hierarchy]] | Document authority order | ✓ |
| [[message-matrix]] | Visual message flow matrix | ✓ |
| [[file-structure]] | Complete project file map | ✓ |
| [[cli-reference]] | CLI command reference | ✓ |

---

## Templates

Squad templates and configuration.

| Page | Description | Status |
|------|-------------|--------|
| [[solo-founder]] | Solo operator template (all 6 claws) | ✓ |
| [[template-overview]] | All available squad templates | ✓ |
| [[ai-micro-saas]] | 4-claw AI SaaS squad (Build+Ops+Analytics+Finance) | ✓ |
| [[campus-ai-tool]] | 3-claw campus utilities squad | ✓ |
| [[content-agency]] | 3-claw content marketing agency | ✓ |
| [[design-studio]] | 3-claw design studio with financial ops | ✓ |
| [[event-promotion]] | 3-claw event marketing squad | ✓ |
| [[freelance-collective]] | 4-claw freelance collective | ✓ |

---

## Configuration

Configuration files and schemas.

| Page | Description | Status |
|------|-------------|--------|
| [[evolution-config]] | Evolution engine parameters | ✓ |
| [[claw-schema]] | Role blueprint structure | ✓ |
| [[mesh-config]] | Message routing matrix | ✓ |
| [[rate-limits]] | Tier-based limits | ✓ |

---

## Solo

Solo system modules for single-operator mode.

| Page | Description | Status |
|------|-------------|--------|
| [[solo-init]] | Template loader and validation | ✓ |
| [[solo-warroom]] | Single-operator action queue | ✓ |
| [[solo-privacy]] | Inference routing with cost guard | ✓ |
| [[solo-evolution]] | Weekly evolution scheduler | ✓ |
| [[solo-deep-work]] | Focused work mode | ✓ |
| [[solo-sandbox]] | Sandbox policy generation | ✓ |

---

## Policies

Sandbox policies and network egress.

| Page | Description | Status |
|------|-------------|--------|
| [[policy-overview]] | Policy structure and enforcement | ✓ |
| [[network-egress]] | Per-claw API allowlists | ✓ |

---

## Patterns

Cross-cutting implementation patterns used across claws.

| Page | Description | Status |
|------|-------------|--------|
| [[signal-dispatcher-pattern]] | Inter-claw communication pattern | ✓ |

---

## Security

Provenance, attestation, and cryptographic modules.

| Page | Description | Status |
|------|-------------|--------|
| [[provenance-signing]] | Ed25519 blueprint signing and verification | ✓ |
| [[chain-validator]] | Provenance chain validation | ✓ |
| [[attestation-generator]] | Performance attestation generation | ✓ |

---

## Operations

Health, metrics, and monitoring modules.

| Page | Description | Status |
|------|-------------|--------|
| [[operation-log]] | Structured action logging | ✓ |
| [[health-collector]] | Health metrics aggregation | ✓ |
| [[metrics-collector]] | Performance metrics collection | ✓ |
| [[latency-monitor]] | Inter-region latency tracking | ✓ |

---

## Scripts

Installation and service management scripts.

| Page | Description | Status |
|------|-------------|--------|
| [[installation-scripts]] | One-command installer | ✓ |
| [[service-scripts]] | Service management scripts | ✓ |
| [[development-scripts]] | Debug and coverage scripts | ✓ |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total pages | 150+ |
| Architecture pages | 10 |
| Claw pages | 6 |
| Module pages | 75+ |
| Coordination pages | 5 |
| Evolution pages | 8 |
| Development pages | 3 |
| Troubleshooting pages | 4 |
| Reference pages | 4 |
| Configuration pages | 4 |
| Solo pages | 6 |
| Template pages | 8 |
| Pattern pages | 1 |
| Security pages | 3 |
| Operations pages | 4 |
| Script pages | 3 |
| TUI pages | 1 |
| CLI pages | 1 |
| Lib pages | 1 |
| Mesh pages | 4 |
| Onboard pages | 1 |
| Infrastructure pages | 2 |

---

## Recent Changes

See [[log]] for complete operation history.

| Date | Change | Pages Affected |
|------|--------|----------------|
| 2026-04-17 | Evolution module pages (tool-generator, evolution-integration, sandbox-runner, marketplace-manager) | 4 new pages |
| 2026-04-15 | Wiki audit and broken link fixes | 10 new pages | |
| 2026-04-15 | Phase 4: Scripts section | 2 new pages |
| 2026-04-15 | Phase 4: Security and Operations modules | 7 new pages |
| 2026-04-15 | Phase 3: Configuration, Solo, Templates, Modules | 16 new pages |
| 2026-04-15 | Phase 2 module documentation | 12 new module pages |
| 2026-04-14 | Codebase audit & improvement plan | improvement-plan.md created |
| 2026-04-14 | Module documentation expansion | 19 new module pages |
| 2026-04-14 | Wiki initialization | All pages created |

---

## Wiki Maintenance

- [[improvement-plan]] — Prioritized roadmap for closing documentation gaps
- [[log]] — Append-only operation history

## Claw Reference

All 6 claws in the MilimoClaw mesh:

- [[content-claw]] — Creative content generation
- [[ops-claw]] — Client lifecycle and delivery
- [[analytics-claw]] — Intelligence and reports
- [[finance-claw]] — Invoicing and pricing
- [[build-claw]] — Engineering and deploys
- [[assistant-lucy]] — Conversational user interface

---

## External Sources

These documents are symlinked in `raw/` and serve as authoritative sources:

- `raw/AGENTS.md` → `.agents/AGENTS.md`
- `raw/ARCHITECTURE.md` → `milimo-claw-docs/ARCHITECTURE.md`
- `raw/SOLO_TEMPLATE_SPEC.md` → `milimo-claw-docs/reference/MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md`

See [[ground-truth-hierarchy]] for complete document authority.
