# MilimoClaw Wiki — Index

**Summary**: Master table of contents for the MilimoClaw knowledge base.

**Last updated**: 2026-06-30

> Note: After onboarding, the sandbox is already running. Use `nemohermes milimo-hermes connect` to start a chat session, not `nemoclaw start`.

**Tags**: #index #navigation

---

## Quick Navigation

| Section | Description | Pages |
|---------|-------------|-------|
| [[#Architecture]] | System design and isolation model | 14 |
| [[#Claws]] | Individual claw documentation | 6 |
| [[#Coordination]] | Message contracts and War Room | 5 |
| [[#Evolution]] | Self-evolution system | 8 |
| [[#Development]] | Conventions and testing | 4 |
| [[#Troubleshooting]] | Common issues and fixes | 4 |
| [[#Reference]] | Quick reference tables | 4 |
| [[#Configuration]] | Configuration files and schemas | 4 |
| [[#Solo]] | Solo system modules | 6 |
| [[#Templates]] | Squad templates | 8 |
| [[#Patterns]] | Cross-cutting implementation patterns | 1 |
| [[#Security]] | Sandbox security, credentials, hardening, OpenClaw controls | 7 |
| [[#Operations]] | Health, metrics, and monitoring modules | 4 |
| [[#Scripts]] | Installation and service scripts | 3 |

---

## Architecture

System architecture and design documentation.

| Page | Description | Status |
|------|-------------|--------|
| [[hermes-integration-report]] | Full gap analysis & corrected integration plan | ✓ |
| [[implementation-plan]] | Complete Phase A–E implementation plan | ✓ |
| [[hermes-profile]] | Hermes profile architecture & components | ✓ |
| [[system-overview]] | Nine-layer architecture overview | ✓ |
| [[sandbox-isolation]] | Landlock, process limits, capability drop, and filesystem isolation | ✓ |
| [[inter-claw-communication]] | Typed message contracts and routing | ✓ |
| [[mesh-coordinator]] | Inter-sandbox gateway and policies | ✓ |
| [[mesh-coordinator-modules]] | Mesh implementation details | ✓ |
| [[privacy-router]] | Inference routing and data sensitivity | ✓ |
| [[workspace-files]] | Workspace file persistence and rebuild behavior | ✓ |
| [[tool-generation]] | Core evolution system (tools, proposals, registry) | ✓ |
| [[claw-launcher]] | Claw startup, process supervision, bootstrapper | ✓ |
| [[inference-client]] | Model-agnostic inference client, fallback chain, category routing | ✓ |
| [[assistant-system]] | Conversational assistant configuration | ✓ |
| [[workspace-files]] | Agent workspace persistence and semantics | ✓ |

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

**[[build-claw|Build]]**: build-init • issue-manager • code-generator • pr-manager • deploy-manager • error-monitor • github-client

**[[assistant-lucy|Assistant]]**: [[lucy]] (PendingQuery • LucyAssistant)

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
| [[sandbox-file-sharing]] | Accessing and extracting claw-generated files | ✓ |

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
| [[NemoClaw-Reference]] | NemoClaw core CLI & API reference | ✓ |
| [[NemoClaw-x-Milimo-Integration-Map]] | Cross-reference of NemoClaw & Milimo integration points | ✓ |
| [[NemoClaw-Blueprint-Implementation]] | Technical specification for NemoClaw blueprints & L7 network policies | ✓ |
| [[implementation-plan]] | Dual-track Hermes integration plan | ✓ |

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

Sandbox security controls, credential management, image hardening, and OpenClaw application-layer security.

| Page | Description | Status |
|------|-------------|--------|
| [[provenance-signing]] | Ed25519 blueprint signing and verification | ✓ |
| [[chain-validator]] | Provenance chain validation | ✓ |
| [[attestation-generator]] | Performance attestation generation | ✓ |
| [[best-practices]] | Four protection layers, network/filesystem/process/inference controls | ✓ |
| [[credential-storage]] | OpenShell gateway credential storage, no-disk-persistence | ✓ |
| [[openclaw-controls]] | OpenClaw application-layer security beyond NemoClaw's scope | ✓ |
| [[sandbox-hardening]] | Sandbox image hardening, capability drops, filesystem policy | ✓ |

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
| [[installation-scripts]] | One-command installer (Dockerfile mode + runtime-deploy mode) | ✓ |
| [[service-scripts]] | Service management scripts | ✓ |
| [[development-scripts]] | Debug and coverage scripts | ✓ |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total pages | 153+ |
| Architecture pages | 12 |
| Claw pages | 6 |
| Module pages | 76+ |
| Coordination pages | 5 |
| Evolution pages | 8 |
| Development pages | 3 |
| Troubleshooting pages | 4 |
| Reference pages | 4 |
| Configuration pages | 4 |
| Solo pages | 6 |
| Template pages | 8 |
| Pattern pages | 1 |
| Security pages | 7 |
| Operations pages | 4 |
| Script pages | 3 |
| TUI pages | 1 |
| CLI pages | 1 |
| Lib pages | 1 |
| Mesh pages | 4 |
| Onboard pages | 1 |
| Infrastructure pages | 2 |
| File Sync pages | 1 |

---

## Recent Changes

See [[log]] for complete operation history.

| Date | Change | Pages Affected |
|------|--------|----------------|
| 2026-06-30 | Phase E7: Gateway daemon sandbox resilience (socat forwarder, .bashrc/.profile hooks), CI build context fixes, gh CLI, milimo_core.build git fix | hermes-profile.md, implementation-plan.md, log.md, index.md |
| 2026-06-30 | Nous Portal login fix, policy preset format, `inference-api.nousresearch.com` added to nous-portal preset | hermes-profile.md, README.md, network-egress.md, log.md, index.md |
| 2026-06-30 | Hermes file sync: `claw_layouts.py` centralized layouts, `milimo_paths.py` Hermes-native paths, `hermes-sync.sh` CLI, `hermes-inventory.py`, Dockerfile claw dirs at build time | sandbox-file-sharing.md, development-scripts.md, log.md, index.md |
| 2026-06-30 | Stripe Link spend integration: SpendApprovalHandler (mirror of FinanceApprovalHandler), spend_warroom_bridge, 3 message handlers, solo-founder.yaml spend_review/spend_hold modes | finance-claw.md, spend-handler.md, approval-thresholds.md, message-contracts.md, AGENTS.md, log.md, index.md |
| 2026-06-30 | Nous Portal 403 fix (tls: skip L4 tunnel), inference-api.nousresearch.com added, install-hermes.sh sandbox_dir scope bug fix | hermes-profile.md, network-egress.md, index.md, log.md |
| 2026-05-28 | Dynamic delay optimization inside sandbox/tests, offline inference fallback mocks, E2E background execution pipeline integration, and robust host file synchronization scripting. | index.md, log.md, sandbox-sync.md |
| 2026-05-24 | Operational stabilization audit, YAML indentation fixes for solo-founder, loop correction in launcher status, dual-namespace mock test containment, sliding window log aging timestamp correction, contract alias relaxation for assistant_response/pricing_response, and Build Claw response envelope mapping | index.md, log.md, contracts.md, message-contracts.md, issues-and-fixes.md |
| 2026-05-12 | Full code audit fixes: Path resolution false positive `_is_sandbox`, ToolRegistry `mkdir` fallback, ContentClaw assert crash, InboxPoller race condition, Evolution minimum actions, Build Claw auth fallback | index.md, log.md, milimo_paths.py, tool_registry.py, content_claw.py, claw_launcher.py, evolution.ts |
| 2026-05-02 | install.sh rewrite: host-based build + pre-built artifacts, --force plugin install, remove destructive plugins.allow override, gateway restart with health check loop, Dockerfile plugin verification step, venv path fix (was /sandbox/milimo-blueprint → correct /sandbox/.openclaw/milimo/milimo-blueprint), gh CLI PATH via /sandbox/.bashrc | installation-scripts.md, common-issues.md, index.md, log.md |
| 2026-04-29 | Sixth wiki correction pass: Nine-layer fix, acpx/ACP plugin docs, plugin system security, assistant module page | index.md, common-issues.md, openclaw-controls.md, modules/assistant/lucy.md |
| 2026-04-29 | Fifth wiki correction pass: Dockerfile install mode, filesystem two-level model, posture profiles vs policy tiers, Common Mistakes, Known Limitations, Gateway Auth Controls | installation-scripts.md, best-practices.md, policy-overview.md, index.md |
| 2026-04-29 | Fourth wiki correction pass: Node.js >=22.16, posture profile naming, seccomp conflation, inference-client default model | install.sh, installation-scripts.md, best-practices.md, policy-overview.md, inference-client.md |
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
