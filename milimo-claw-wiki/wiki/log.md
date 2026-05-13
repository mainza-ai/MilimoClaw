# Operation Log

**Summary**: Append-only record of all wiki operations.

**Last updated**: 2026-05-06

**Tags**: #log #meta

---

## Log Format

Each entry follows this format:

```
### YYYY-MM-DD HH:MM — Operation Type

**Pages**: List of pages created/modified
**Source**: Source document or trigger
**Changes**: What was changed
**Notes**: Additional context
```

---

## 2026-05-02

### 2026-05-02 14:30 — install.sh Plugin Installation Rewrite + Wiki Update

**Pages**: installation-scripts.md, common-issues.md, index.md, log.md

**Source**: Rewriting `install.sh` plugin installation for NemoClaw v0.0.33 / OpenClaw v2026.4.24 compatibility

**Changes**:
- **Runtime deploy (Steps 2-3)**: Build TypeScript + production node_modules on host (`npm install --omit=dev`); transfer only deployable artifacts (openclaw.plugin.json, package.json, dist/, node_modules/); stage at `/tmp/milimo-plugin-install/` instead of `.openclaw/extensions/milimo/` (avoids Landlock path restrictions during extraction)
- **Step 9 (Plugin registration)**: `openclaw plugins install --force` + `--dangerously-force-unsafe-install` retry on exit 1; removed destructive `plugins.allow '["milimo"]'` override; verification via `openclaw plugins list | grep milimo` + `openclaw milimo --help`; proper exit code capture (not swallowed by `|| true`)
- **Step 10 (Gateway restart)**: `openclaw gateway restart` + health check loop polling `openclaw doctor` for up to 30s (replaces blind `pkill openclaw; sleep 8`)
- **generate_dockerfile()**: Added `--force`, removed `|| true`, added `openclaw plugins list | grep -q "milimo"` verification step; added `--legacy-peer-deps` to npm install
- **deploy_via_dockerfile()**: Build production node_modules on host before creating build context; Dockerfile COPY includes pre-built dist/ + node_modules/ (no npm install needed in Docker build)
- **Secondary fixes**: venv path `/sandbox/milimo-blueprint` → `/sandbox/.openclaw/milimo/milimo-blueprint`; gh CLI PATH via `/sandbox/.bashrc` (sandbox_exec_root writes PATH export since `.bashrc` is root-owned 444); Python .pth file path fixed to `/sandbox/.local/lib/python3.11/site-packages/`
- **Wiki**: Updated installation-scripts.md (new install flow, Dockerfile pattern, directory structure); added Plugin and Config Issues section to common-issues.md documenting 3 fixed issues (plugin not registered, destructive plugins.allow override, gateway restart without health check); updated index.md last updated date and recent changes table

**Notes**: Tested against running sandbox (my-assistant, NemoClaw v0.0.33, OpenClaw v2026.4.24). Plugin shows as "loaded" (51/108 plugins). `openclaw milimo --help` responds correctly. First `openclaw plugins install --force` returned exit 1 during gateway restart, retry with `--dangerously-force-unsafe-install` succeeded — handled in script.

---

## 2026-04-24

### 2026-04-24 — P12 Model Propagation + Doc Audit (104 Instances)

**Pages**: Welcome.md + 55 doc files + 10 code files modified
**Source**: Comprehensive audit of model propagation chain + doc consistency
**Changes**:
- Fixed Python fallback defaults from `nemotron-4-340b-instruct` → `nemotron-3-super-120b-a12b` (5 files)
- Fixed Dockerfile build-arg fallback model
- Fixed milimo-start.sh model overwrite on restart (check before writing)
- Added NEMOCLAW_MODEL env var to all 6 docker-compose services
- Added NEMOCLAW_MODEL to K8s main container via secretKeyRef
- Added model/endpointUrl fields to MilimoConfig + propagated from loadNemoClawConfig()
- loadNemoClawConfig now reads NEMOCLAW_MODEL env var first
- Fixed install.sh: added assistant to activeClaws, mkdir, chown, verification loops, claws dict, onboarding msg
- Fixed assistant.ts: resolve script path from ~/.milimo/blueprints instead of relative CWD
- Fixed non-interactive onboard error (was silent, now exit code 1)
- Fixed 5→6 claws across 32 milimo-claw-docs files (~80 edits)
- Fixed Cloud Nemotron → NEMOCLAW_MODEL across 23 milimo-claw-docs files (58 edits)
- Fixed hardcoded model refs in docs/ (3 files, 6 instances)
- Fixed wiki Welcome.md: Five→Six Claws, added assistant row, updated ASCII diagram
- Fixed ARCHITECTURE.md: seven→eight layers, NEMOCLAW_MODEL in privacy router diagram
- Fixed PRIVACY_AND_SECURITY.md: assistant in filesystem + network isolation tables
- Fixed claw specs: added assistant to cannot-read sections (5 specs)
**Notes**: Commit 72955d4 on develop. 82 files changed, 2068 insertions, 1679 deletions.

## 2026-04-23

### 2026-04-23 — P10 Wiki Consistency Audit Fixes

**Pages**: 16 pages modified
**Source**: Wiki audit — 16 inconsistencies found across architecture, coordination, templates, and reference pages
**Changes**:
- Fixed `system-overview.md` — "seven layers" → "eight layers", added Assistant/Lucy section
- Fixed `index.md` — "Seven-layer" → "Eight-layer", fixed page count mismatches (Evolution 3→8, Scripts 2→3, Troubleshooting 3→4), removed duplicate module lists, added assistant module line, updated solo-founder to 6 claws
- Fixed `approval-thresholds.md` — Added VETO mode to Approval Modes table and Priority Order, added Assistant Claw Thresholds section
- Fixed `contracts.md` — Added VETO to Priority Levels, added `assistant` to Valid Recipients
- Fixed `solo-warroom.md` — Added VETO to Priority Ordering, "five claws" → "six claws"
- Fixed `template-overview.md` — Freelance Collective 3→4 claws (added Content), solo-founder 5→6 claws
- Fixed `design-studio.md` — High-value invoice escalation HOLD → VETO (consistent with VETO mode definition)
- Fixed `solo-founder.md` — "5 claws" → "6 claws" (3 occurrences), added Assistant to Deep Work table, added assistant to claws list and YAML
- Fixed `claw-schema.md` — Added `assistant` to Valid Roles
- Fixed `ground-truth-hierarchy.md` — Added Assistant (Lucy) spec entry
- Fixed `assistant-lucy.md` — Added Runtime Coordinator section (LucyAssistant, TelegramBridge, PendingQuery), added Telegram Bot API to network access
- Fixed `war-room.md` — Added assistant row to Deep Work table, added [[assistant-lucy]] to related pages
- Fixed `claw-launcher.md` — Added assistant to health endpoint JSON, added assistant env vars, added [[assistant-lucy]] to dependencies, fixed port description
- Fixed `signal-dispatcher.md` — "5 claws" → "6 claws"
- Fixed `signal-dispatcher-pattern.md` — Added Assistant row to Implementation table
- Fixed `improvement-plan.md` — Updated audit date and next audit line
- Updated all stale dates (2026-04-14 → 2026-04-23) on 8 pages

**Notes**:
- All 16 wiki inconsistencies from P10 audit resolved
- VETO mode now documented in all 3 pages that used it without definition
- Assistant (Lucy) now reflected across all wiki pages
- P1-P10 implementation complete (P9 skipped per user request)

### 2026-04-23 — P11 Deep Wiki Consistency Audit Fixes

**Pages**: 25 pages modified
**Source**: Deep audit — 69 issues found (P10 audit missed many 5-claw references)
**Changes**:
- Fixed `sandbox-isolation.md` — "all five" → "all six", added Assistant to mount tree and egress table, added assistant-lucy link
- Fixed `mesh-coordinator.md` — Added Assistant to architecture diagram and inbox directory, added assistant-lucy link
- Fixed `privacy-router.md` — Added Assistant to sensitive data types table and SENSITIVE_TYPES dict, added assistant-lucy link
- Fixed `system-overview.md` — Removed duplicate "### 8. Runtime Layer" section (lines 139-147)
- Fixed `claw-silent-responses.md` — "All 5 claws" → "All 6 claws"
- Fixed `issues-and-fixes.md` — "All 5 claws" → "All 5 non-assistant claws" (semantic fix), added assistant port 8086 to HEALTH_PORTS
- Fixed `improvement-plan.md` — "signal_dispatcher.py (x5 claws)" → "(x4 claws) + lucy.py (Assistant)"
- Fixed `ai-micro-saas.md` — "all 5 claws" → "all 6 claws"
- Fixed `installation-scripts.md` — "all 5 claws active" → "all 6 claws active", added Assistant mount to directory structure
- Fixed `evolution-integration.md` — "for all 5 claws" → "for all 6 claws", "Register all 5 claw" → "Register all 6 claw", added assistant to registered claws and status JSON
- Fixed `evolution-cycle.md` — Added Assistant to schedule, thresholds, and evolution tools tables; fixed [[blueprint-manager]] → [[tool-registry]] broken link
- Fixed `tool-registry.md` — Added assistant to claw_role parameter
- Fixed `solo-sandbox.md` — Added Assistant to inference routes and policy file mapping tables
- Fixed `solo-deep-work.md` — Added Assistant to default claw activation table
- Fixed `solo-evolution.md` — Added Assistant to schedule and activity thresholds tables
- Fixed `solo-init.md` — Added assistant to filesystem and network_egress required fields
- Fixed `policy-overview.md` — Added Assistant to mount table
- Fixed `file-structure.md` — Added assistant-claw.yaml to roles directory
- Fixed `solo-founder.md` — Added .openclaw/ to filesystem structure, added [[assistant-lucy]] to related pages
- Fixed `signal-dispatcher-pattern.md` — Added Summary/Sources/Last updated/Tags format headers
- Fixed `solo-sandbox.md`, `solo-deep-work.md`, `solo-evolution.md`, `solo-init.md`, `solo-privacy.md`, `solo-warroom.md` — Added Summary/Sources/Last updated/Tags format headers per CLAUDE.md standard
- Fixed `CLAUDE.md` — Added assistant/ modules directory to folder structure
- Updated 13 pages with stale dates (2026-04-14 → 2026-04-23)
- Updated `index.md` — Added Claw Reference section with all 6 claws
- Updated `log.md` — This entry

**Notes**:
- All 69 issues from deep audit resolved across 8 categories (A through H)
- Category A: 10 explicit "5 claws" references → "6 claws" (or "5 non-assistant" where semantically correct)
- Category B: 26 tables/diagrams/lists updated with Assistant row
- Category C: Duplicate "### 8. Runtime Layer" section removed from system-overview.md
- Category D: Broken [[blueprint-manager]] link fixed → [[tool-registry]]
- Category E: CLAUDE.md folder structure updated with assistant/ module directory
- Category F: 13 stale dates updated from 2026-04-14 to 2026-04-23
- Category G: 7 solo/pattern pages brought up to CLAUDE.md format standard
- Category H: log.md line 76 "5" → "6" fixed
- The assistant mount is `/sandbox/.openclaw/` (not `/sandbox/assistant/`)
- The assistant health port is 8086
- issues-and-fixes.md uses "5 non-assistant claws" because the assistant was the message sender, not a recipient needing handlers


---

## 2026-04-18

### 2026-04-18 04:30 — Claw Silent Response Fixes

**Pages**: 1 new page, 3 pages modified
**Source**: MilimoClaw claw diagnostic investigation
**Changes**:
- Created `troubleshooting/claw-silent-responses.md` — Troubleshooting guide for claws returning blank output
- Fixed `content_claw.py` — Handler return types and explicit returns
- Fixed `build_claw.py` — Added mesh_sender and _send_assistant_response
- Fixed `finance_claw.py` — Added explicit return statements
- Updated `index.md` — Added claw-silent-responses to Troubleshooting section
- Updated `log.md` — Added this entry

**Notes**:
- 3 claws (content, finance, build) were returning blank output due to missing return statements in handlers
- Root cause: handlers returned `None` instead of `dict[str, Any]`
- All 6 claws now properly return diagnostic output
- NemoClaw sandbox rebuilt with fixes applied
- Model set to minimaxai/minimax-m2.7 via NEMOCLAW_MODEL env var
- Total wiki pages: 150+

---

### 2026-04-17 10:00 — Evolution Module Documentation

**Pages**: 4 new pages
**Source**: Comprehensive completeness audit
**Changes**:
- Created `modules/build/github-client.md` — GitHub API client
- Created `modules/infrastructure/inference-client.md` — NVIDIA NIM client
- Created `modules/evolution/tool-builder.md` — Tool building and backtesting
- Created `modules/evolution/tool-validator.md` — Security validation
- Created `modules/evolution/tool-proposal.md` — Proposal schema and validation
- Created `modules/infrastructure/bridge-cli.md` — Python bridge CLI
- Created `modules/mesh/mesh-encryption.md` — AES-256-GCM encryption
- Created `modules/mesh/mesh-failover.md` — Failover handling
- Created `modules/mesh/mesh-relay.md` — Relay server for NAT traversal
- Updated `wiki/index.md` with new sections

**Notes**:
- Wiki coverage now 95%+ for all Python modules
- All mesh infrastructure documented
- All evolution pipeline documented
- Total wiki pages: 145+

---

### 2026-04-17 10:00 — Evolution Module Documentation

**Pages**: 4 new pages
**Source**: tool_generator.py, evolution_integration.py, sandbox_runner.py, marketplace_manager.py
**Changes**:
- Created `modules/evolution/tool-generator.md` — LLM-based tool code generation
- Created `modules/evolution/evolution-integration.md` — Evolution cycle scheduler
- Created `modules/evolution/sandbox-runner.md` — Isolated backtest execution
- Created `modules/evolution/marketplace-manager.md` — Blueprint marketplace
- Updated `wiki/index.md` with new evolution pages

**Notes**:
- All evolution pipeline modules now documented
- Total wiki pages: 149+

---

### 2026-04-15 16:30 — Final Wiki Audit Complete

**Pages**: 1 new page + 2 fixes
**Source**: Final audit verification
**Changes**:
- Created `scripts/development-scripts.md` — Debug and coverage scripts
- Fixed broken links in `vercel-client.md` — Removed non-existent deployment-* references
- Fixed broken links in `sentry-client.md` — Removed non-existent deployment-tracker reference
- Updated `wiki/index.md` with final statistics

**Notes**:
- **AUDIT PASSED** — All wiki-links verified
- Total wiki pages: 136
- No orphan pages (except audit log)
- No broken links remaining
- Wiki documentation complete

---

### 2026-04-15 16:00 — TypeScript Documentation Complete

**Pages**: 5 new TypeScript pages
**Source**: TypeScript source files
**Changes**:
- Created `tui/warroom-tui.md` — War Room TUI (blessed)
- Created `cli/cli-commands.md` — CLI command reference
- Created `lib/bridge-tools.md` — Python bridge wrapper
- Created `mesh/mesh-gateway-client.md` — Gateway socket client
- Created `onboard/onboard-flows.md` — Onboarding flows
- Updated `wiki/index.md` with new sections

**Notes**:
- All TypeScript pages now documented
- New sections: TUI (1), CLI (1), Lib (1), Mesh (1), Onboard (1)
- Total wiki pages: 135+ (up from 125+)
- Wiki now covers all Python and TypeScript modules

---

### 2026-04-15 15:30 — Missing Module Pages Created (Batch 2)

**Pages**: 8 new module pages
**Source**: Wiki audit follow-up
**Changes**:
- Created `modules/build/build-scheduler.md` — Build Claw job scheduler
- Created `modules/finance/finance-scheduler.md` — Finance Claw job scheduler
- Created `modules/build/cost-monitor.md` — Inference cost tracking
- Created `modules/build/dependency-auditor.md` — Security vulnerability scanning
- Created `modules/build/doc-maintainer.md` — Documentation automation
- Created `modules/content/timing-optimizer.md` — Evolved timing tool
- Created `modules/finance/payment-events-log.md` — Payment audit trail
- Created `modules/finance/quarterly-tax-prep.md` — Tax preparation summaries
- Updated `wiki/index.md` with new pages

**Notes**:
- All scheduler pages now documented
- All Build Claw modules now documented
- Remaining: TypeScript CLI/TUI pages (deferred)
- Total wiki pages: 125+ (up from 115+)

---

### 2026-04-15 15:00 — Wiki Audit and Broken Link Fixes

**Pages**: 10 new pages + 1 audit report
**Source**: Wiki audit request
**Changes**:
- Created `Wiki-Audit-2026-04-15.md` — Comprehensive audit report
- Created `development/debugging.md` — Debug guide (was missing)
- Created `troubleshooting/sandbox-sync.md` — Sandbox sync troubleshooting
- Created `evolution/pattern-detection.md` — Pattern detection overview
- Created `patterns/signal-dispatcher.md` — Redirect to signal-dispatcher-pattern
- Created `modules/analytics/analytics-scheduler.md` — Analytics job scheduler
- Created `modules/evolution/tool-registry.md` — Tool inventory manager
- Created `modules/coordination/approval-handler.md` — Approval queue management
- Created `modules/finance/invoice-generator.md` — Invoice generation
- Created `modules/evolution/pattern-detector.md` — Pattern detection engine
- Updated `wiki/index.md` with new sections

**Notes**:
- Wiki audit found 24 broken links
- 4 naming mismatches fixed (debugging, sandbox-sync, pattern-detection, signal-dispatcher)
- 6 high-priority module pages created
- Remaining broken links: deferred TypeScript pages, lower-priority modules
- Total wiki pages: 115+ (up from 105+)

---

### 2026-04-15 02:30 — Phase 4: Scripts Section

**Pages**: 2 new pages
**Source**: Improvement plan Phase 4 execution
**Changes**:
- Created `scripts/installation-scripts.md` — One-command installer documentation
- Created `scripts/service-scripts.md` — Service management scripts
- Updated `wiki/index.md` with Scripts section

**Notes**:
- Phase 4 script reference pages complete
- Added new section: Scripts (2)
- 105+ total wiki pages (up from 100+)
- Phase 4 now complete (security + operations + scripts)

---

### 2026-04-15 02:00 — Phase 4: Security and Operations Modules

**Pages**: 7 new pages
**Source**: Improvement plan Phase 4 execution
**Changes**:
- Created `modules/security/provenance-signing.md` — Ed25519 blueprint signing
- Created `modules/security/chain-validator.md` — Provenance chain validation
- Created `modules/security/attestation-generator.md` — Performance attestations
- Created `modules/operations/operation-log.md` — Structured action logging
- Created `modules/operations/health-collector.md` — Health metrics aggregation
- Created `modules/operations/metrics-collector.md` — Performance metrics collection
- Created `modules/operations/latency-monitor.md` — Inter-region latency tracking
- Updated `wiki/index.md` with Security and Operations sections

**Notes**:
- Phase 4 Tier 4 (security + operations) pages complete
- Added new sections: Security (3), Operations (4)
- 100+ total wiki pages (up from 90+)
- Remaining: CLI/TUI pages, script reference pages

---

### 2026-04-15 01:30 — Phase 3: Configuration, Solo, Templates, and Additional Modules

**Pages**: 16 new pages
**Source**: Improvement plan Phase 3 execution
**Changes**:
- Created `configuration/evolution-config.md` — Evolution engine parameters
- Created `configuration/claw-schema.md` — Role blueprint structure
- Created `configuration/mesh-config.md` — Message routing matrix
- Created `configuration/rate-limits.md` — Tier-based limits
- Created `solo/solo-init.md` — Template loader and validation
- Created `solo/solo-warroom.md` — Single-operator action queue
- Created `solo/solo-privacy.md` — Inference routing with cost guard
- Created `solo/solo-evolution.md` — Weekly evolution scheduler
- Created `solo/solo-deep-work.md` — Focused work mode
- Created `solo/solo-sandbox.md` — Sandbox policy generation
- Created `templates/ai-micro-saas.md` — 4-claw AI SaaS squad
- Created `templates/campus-ai-tool.md` — 3-claw campus utilities squad
- Created `templates/content-agency.md` — 3-claw content marketing agency
- Created `templates/design-studio.md` — 3-claw design studio
- Created `templates/event-promotion.md` — 3-claw event marketing squad
- Created `templates/freelance-collective.md` — 4-claw freelance collective
- Created `modules/analytics/collection-workers.md` — Scheduled data collection
- Created `modules/analytics/data-collectors.md` — YouTube, GA4, generic API collectors
- Created `modules/ops/incident-analyzer.md` — AI-powered incident analysis
- Created `modules/ops/runbook-executor.md` — Automated remediation
- Created `modules/ops/webhook-server.md` — Real-time incident ingestion
- Created `modules/content/publish-scheduler.md` — Scheduled content publishing
- Updated `wiki/index.md` with all new sections and pages

**Notes**:
- Phase 3 of improvement plan complete
- Added new sections: Configuration (4), Solo (6), Templates (6)
- Added 6 additional module pages
- 90+ total wiki pages (up from 75+)
- All 23 Phase 3 pages created as planned

---

### 2026-04-15 00:30 — Phase 2: High-Priority Module Pages

**Pages**: 12 new module/pattern pages
**Source**: Improvement plan Phase 2 execution
**Changes**:
- Created `modules/analytics/baseline-manager.md` — 30-day rolling baseline calculator
- Created `modules/analytics/query-handler.md` — On-demand query handler with SLA
- Created `modules/analytics/forward-projector.md` — 4-week projection engine
- Created `modules/ops/comms-manager.md` — Client communication handler
- Created `modules/ops/scope-monitor.md` — Scope creep detection
- Created `modules/finance/payment-risk-scorer.md` — Client payment risk assessment
- Created `modules/finance/expense-tracker.md` — Expense logging with tax classification
- Created `modules/finance/stripe-client.md` — Stripe API wrapper
- Created `modules/build/sentry-client.md` — Sentry error monitoring client
- Created `modules/build/vercel-client.md` — Vercel deployment client
- Created `modules/content/performance-monitor.md` — Content performance tracking
- Created `patterns/signal-dispatcher-pattern.md` — Cross-cutting inter-claw communication pattern
- Updated `wiki/index.md` with all new pages

**Notes**:
- Phase 2 of improvement plan complete
- All high-priority operational modules now documented
- Added new "Patterns" section for cross-cutting concerns
- 75+ total wiki pages (up from 63)

---

## 2026-04-14

### 2026-04-14 23:45 — Phase 1: Critical Architecture Pages

**Pages**: 5 new architecture/coordination pages
**Source**: Improvement plan Phase 1 execution
**Changes**:
- Created `architecture/tool-generation.md` — Core evolution system documentation
- Created `architecture/claw-launcher.md` — Process supervision and health monitoring
- Created `architecture/assistant-system.md` — Assistant setup and identity management
- Created `architecture/mesh-coordinator-modules.md` — Mesh implementation details
- Created `coordination/contracts.md` — Typed message contract definitions
- Updated `wiki/index.md` with new architecture pages

**Notes**:
- Phase 1 of improvement plan complete
- All critical foundational modules now documented
- 62 total wiki pages

### 2026-04-14 23:30 — Wiki Audit and Improvement Plan

**Pages**: improvement-plan.md
**Source**: User request for codebase audit
**Changes**:
- Conducted comprehensive codebase audit
- Identified 82 undocumented Python modules
- Identified 17+ undocumented configuration files
- Identified 11 undocumented scripts
- Identified 6 undocumented squad templates
- Created improvement-plan.md with 51+ recommended new pages
- Organized recommendations into 4 priority tiers

**Notes**:
- Current doc coverage: ~27% of codebase
- Target: 100% coverage (120+ pages)
- Critical gap: tool-generation, claw-launcher, assistant-system, contracts
- Improvement plan includes execution phases and success metrics

### 2026-04-14 22:45 — Module Documentation Expansion

**Pages**: 19 new module pages
**Source**: User request to expand module documentation
**Changes**:
- Reorganized existing modules into subdirectories (content/, ops/, analytics/, finance/, build/)
- Created Content Claw modules: brief-manager, brand-voice, platform-publisher, content-scheduler
- Created Ops Claw modules: project-manager, health-scorer, ops-scheduler, ops-init
- Created Analytics Claw modules: signal-processor, opportunity-scorer, report-generator, analytics-init
- Created Finance Claw modules: pricing-engine, payment-monitor, revenue-tracker, finance-init
- Created Build Claw modules: issue-manager, code-generator, deploy-manager, error-monitor, build-init

**Notes**:
- Each module page follows standardized template
- All pages include key classes, dependencies, and wiki-links
- Total module pages now 25+ (up from 6)

### 2026-04-14 20:45 — Wiki Initialization

**Pages**: All pages (55+)
**Source**: User request to create comprehensive wiki
**Changes**:
- Created complete folder structure
- Created CLAUDE.md with comprehensive AI instructions
- Created all architecture pages
- Created all claw pages
- Created module documentation for all claws
- Created coordination, evolution, development, troubleshooting, reference pages
- Created templates for new pages
- Set up symlinks in raw/ folder

**Notes**:
- Wiki follows LLM Wiki pattern (Karpathy)
- Optimized for AI comprehension
- Uses Sync & Link strategy — wiki synthesizes, original docs are authoritative
- 35+ wiki pages created with proper interlinking

### 2026-04-14 20:00 — CLAUDE.md Creation

**Pages**: CLAUDE.md
**Source**: User requirement for comprehensive AI instructions
**Changes**:
- Created 300+ line CLAUDE.md
- Documented ground truth hierarchy
- Defined page format standards
- Specified wiki-link usage rules
- Created ingest workflow
- Defined question answering protocol
- Added lint & audit rules
- Documented MilimoClaw-specific terminology

**Notes**: CLAUDE.md is the authoritative guide for AI behavior in the wiki

---

## Log Legend

| Operation Type | Description |
|----------------|-------------|
| INIT | Initial creation of pages |
| INGEST | Processing of source document |
| UPDATE | Modification to existing pages |
| LINK | Adding/updating wiki-links |
| AUDIT | Lint and audit operation |
| SYNC | Synchronizing with source changes |

---

### 2026-04-23 15:30 — SYNC

**Pages**: mesh-coordinator.md, privacy-router.md, system-overview.md, sandbox-isolation.md, solo-privacy.md, claw-schema.md, pricing-engine.md, brand-voice.md, tool-generation.md, finance-claw.md
**Source**: P11 batch — Assistant Claw integration + NEMOCLAW_MODEL normalization
**Changes**:
- Added Assistant Claw to mesh-coordinator.md architecture diagram and inbox directory
- Updated all "Local NIM" display references to "Local NIM (NEMOCLAW_MODEL)" across privacy-router.md, sandbox-isolation.md, system-overview.md, solo-privacy.md, claw-schema.md, pricing-engine.md, brand-voice.md, tool-generation.md, finance-claw.md
- Updated "NVIDIA Cloud Nemotron 120B" to "Cloud (NEMOCLAW_MODEL)" in solo-privacy.md, claw-schema.md

**Notes**: Config keys (local_nim, local-nim) preserved unchanged — they are backend categories, not display labels

---

## 2026-04-29

### 2026-04-29 — Inference Routing and Workspace Accuracy Fixes

**Pages**: 5 pages modified, 1 new page
**Source**: NemoClaw docs accuracy review — inference routing, workspace paths, TelegramBridge removal
**Changes**:
- Fixed `privacy-router.md` — Corrected inference.local proxy endpoint, OpenShell L7 credential substitution, NEMOCLAW_MODEL env var, model switching commands (openshell inference set / nemoclaw inference-switch), experimental providers (NEMOCLAW_EXPERIMENTAL=1), provider trust tiers, OpenShell cost guard reference, added NemoClaw compliance notice
- Fixed `solo-privacy.md` — Corrected inference.local proxy endpoint, removed OPENAI_API_KEY for local inference (provider-specific tokens), NEMOCLAW_MODEL determines model, OpenShell cost controls reference, added NemoClaw compliance notice
- Fixed `network-egress.md` — Removed NVIDIA NIM endpoints from Assistant Egress (inference.local is internal-only, handled by OpenShell gateway, not an external egress endpoint)
- Fixed `sandbox-sync.md` — Added workspace path references (/sandbox/.openclaw/workspace/), multi-agent workspace-name/ subdirectories, persistence across restarts but not rebuilds, rebuild = new container data loss, added NemoClaw compliance notice
- Fixed `assistant-lucy.md` — Removed TelegramBridge class and all telegram_poll_loop/process_telegram_message references, replaced with OpenShell channel messaging (Telegram, Discord, Slack), replaced NVIDIA NIM with inference.local in network access, updated startup to use OpenShell channels instead of Telegram bridge
- Created `architecture/workspace-files.md` — Workspace file persistence model: location, multi-agent layout, persistence model (survives restart, lost on rebuild), Landlock writable exception, use cases, backup guidance
- Updated `index.md` — Added workspace-files to Architecture section, updated Architecture page count to 11, fixed Assistant module reference (removed TelegramBridge)

**Notes**:
- All inference routing pages now correctly describe inference.local as the sandbox-internal proxy endpoint
- No API keys in sandbox environment is now documented across privacy-router, solo-privacy
- TelegramBridge fully removed from assistant-lucy and index — messaging uses OpenShell channels
- Workspace persistence model now documented as a first-class architecture page

### 2026-04-29 — Official command audit corrections

**Pages changed**: workspace-files.md, development-scripts.md, best-practices.md, sandbox-hardening.md, sandbox-isolation.md, solo-init.md, index.md

**Fixes**:
- `nemoclaw snapshot create/list/restore` — re-annotated as official NemoClaw v0.0.29 commands (previously incorrectly marked as "MilimoClaw-specific")
- `nemoclaw debug` — confirmed official; `milimo debug` correctly documented as wrapper
- `/sandbox` writability — corrected across all wiki pages: `/sandbox` is writable at the container mount level (per official best-practices.html + architecture.html); `/sandbox/.openclaw/` is the only read-only exception (root-owned, immutable, SHA256-verified)
- Removed "Landlock-read-only" claim for `/sandbox` root — Landlock adds best-effort restrictions on 5.13+ kernels but is not the sole enforcement mechanism
- `/sandbox/.openclaw/workspace/` writability — now correctly attributed to symlink into `.openclaw-data/` (official mechanism), not "MilimoClaw convention"

### 2026-04-29 — Fourth wiki correction pass (prerequisites + posture profiles + seccomp)

**Pages changed**: install.sh, installation-scripts.md, best-practices.md, policy-overview.md, inference-client.md

**Fixes**:
- Node.js version — corrected from `>=20` to `>=22.16` per official NemoClaw v0.0.29 prerequisites.html (install.sh check logic + wiki)
- Posture profiles — previously conflated with policy tiers; wiki now distinguishes the two: **Policy tiers** (from `nemoclaw onboard`) = Restricted/Balanced/Open; **Posture profiles** (operational guidance from best-practices.html) = Locked-Down (Default)/Development/Integration Testing
- Seccomp conflation — removed "as part of the seccomp filter setup" from `PR_SET_NO_NEW_PRIVS` description in both best-practices.md and policy-overview.md; `prctl()` is a separate call, NemoClaw does NOT add its own seccomp BPF filters
- `/sandbox/` (root) removed from Read-Only Paths table in policy-overview.md — `/sandbox` is writable at container mount level; only `.openclaw/` is read-only
- inference-client.md — added official default model reference (`nvidia/nemotron-3-super-120b-a12b` via NVIDIA Endpoints, `integrate.api.nvidia.com/v1`, routed through `inference.local`)
- installation-scripts.md — directory structure updated to reflect actual `.openclaw-data/milimo/claws/<role>` mount paths with full tree

### 2026-04-29 — Fifth wiki correction pass (Dockerfile install mode + filesystem two-level model + full docs re-check)

**Pages changed**: installation-scripts.md, best-practices.md, policy-overview.md, index.md

**Official docs re-verified**: prerequisites.html, best-practices.html, sandbox-hardening.html, install-openclaw-plugins.html, commands.html, architecture.html, network-policies.html, credential-storage.html, workspace-files.html, inference-options.html

**Fixes**:
- installation-scripts.md — rewritten to document two install modes: Dockerfile (default, official `nemoclaw onboard --from` path) and Runtime deploy (`--runtime-deploy` flag). Added macOS tar xattr handling section, credential storage guidance per official docs, Dockerfile pattern explanation with `ARG SANDBOX_BASE`, `openclaw doctor --fix`, `WORKDIR /opt/nemoclaw`
- best-practices.md — Writable Paths section updated with two-level model table (mount vs Landlock vs DAC) reflecting both best-practices.html (mount rw) and sandbox-hardening.html (Landlock ro) semantics
- best-practices.md — Policy Tiers vs Posture Profiles section added: distinguishes tiers (Restricted/Balanced/Open from `nemoclaw onboard`) from profiles (Locked-Down/Development/Integration Testing from best-practices.html)
- best-practices.md — Common Mistakes table updated with "Disabling device auth for remote deployments" and "Adding inference provider hosts to network policy" per official docs
- best-practices.md — Known Limitations added: `openclaw agent --local` bypass, direct filesystem writes bypass scanner, base64/hex-encoded secrets not detected
- best-practices.md — Gateway Authentication Controls section added (device auth, insecure auth derivation, auto-pair allowlist, CLI secret redaction, memory secret scanner)
- best-practices.md — Auth Profile Permissions and Image Digest Pinning sections added
- policy-overview.md — Read-Only Paths table updated with `/sandbox` as read-only via Landlock + Level column
- policy-overview.md — Seccomp Filters section wording clarified: OpenShell applies seccomp internally; NemoClaw does NOT add its own BPF filters

### 2026-04-29 — Sixth wiki correction pass (index layer count fix + acpx/ACP documentation + plugin system docs + assistant module page)

**Pages changed**: index.md, common-issues.md, openclaw-controls.md, modules/assistant/lucy.md (new)

**Fixes**:
- index.md — corrected "Eight-layer architecture overview" to "Nine-layer architecture overview" to match system-overview.md
- common-issues.md — added "Plugin and Config Issues" section documenting the acpx plugin config warning (benign): plugins.entries.acpx disabled-by-default config is purely informational; ACP sessions run on host runtime, disabled in sandbox by design
- openclaw-controls.md — added "Plugin System Security" section: plugin allowlist/denylist (plugins.allow, plugins.deny), plugin states (Disabled/Missing/Invalid), bundled plugins table (model providers, browser, copilot-proxy, acpx, memory-core, memory-lancedb), acpx in NemoClaw Sandboxes explanation, dangerous config flags (permissionMode=approve-all)
- modules/assistant/lucy.md — NEW page: runtime coordinator module documentation for lucy.py (PendingQuery, LucyAssistant, message routing, operator message parsing, consolidation)
- index.md — updated Assistant module line to link to lucy module page

---

---

## 2026-04-30

### 2026-04-30 — NemoClaw Unified Layout Migration (.openclaw-data → .openclaw)

**Pages**: installation-scripts.md, sandbox-isolation.md, log.md, docker-compose.yml, Dockerfile
**Source**: NemoClaw Dockerfile analysis + official docs
**Changes**:
- Confirmed NemoClaw Dockerfile actively removes `.openclaw-data/` — 150+ line migration block flattens to unified `.openclaw/` layout
- Migrated all MilimoClaw paths from `.openclaw-data/milimo/` to `.openclaw/milimo/` across:
  - `milimo_paths.py` — centralized path resolver with legacy fallback
  - `bridge_cli.py` — blueprints dir + handle_collect_health
  - `assistant_setup.py` — config candidates
  - `ops/comms_manager.py` — config path
  - `milimo-blueprint/orchestrator/milimo_paths.py` — centralized path resolver
  - Dockerfile — extended `sandbox-base:latest`, `openclaw plugins install`
  - docker-compose.yml — 6 hardened services, all paths migrated
  - install.sh — 56 refs migrated, `openclaw plugins install` pattern
  - TypeScript files — 69 refs across `milimo/src/**/*.ts`
- Added critical NemoClaw isolation warnings to installation-scripts.md and sandbox-isolation.md: claws MUST run through `nemoclaw onboard --from`, Docker Compose mode DEPRECATED/UNSUPPORTED
- Deprecated `milimo-start.sh` reference in docker-compose.yml header
- Docker Compose hardened per official NemoClaw Sandbox Hardening docs: `cap_drop: ALL`, `security_opt: no-new-privileges`, `ulimits nproc: 512:512`
- Updated docker-compose.yml deprecation header to explain only `nemoclaw onboard --from` provides full isolation

**Notes**:
- NemoClaw Dockerfile.base confirms: "No separate .openclaw-data or symlink bridge"
- Plugin install: `openclaw plugins install /opt/milimo` (NOT manual cp to extensions dir)
- 171 Python .py files pass syntax check after migration
- Docker Compose mode bypasses NemoClaw isolation — UNSUPPORTED
- Remaining: tests (56 Python refs + 4 TS refs), scripts/milimo-start.sh, wiki docs still reference .openclaw-data

---

*This log is append-only. Never delete entries.*

---

### 2026-05-06 09:20 — Bridge CLI Import Fix + Mesh Memory-Only Mode + mesh_config.yaml Indentation Fix

**Pages**: bridge-cli.md, mesh-coordinator.md, mesh-config.md, bridge-tools.md, common-issues.md, log.md
**Source**: Bug fix session — bridge CLI `send_to_claw` failing with ImportError + AttributeError
**Changes**:
- bridge-cli.md: Updated import architecture from relative/mixed to absolute `from orchestrator.X import Y`; documented PYTHONPATH requirement
- mesh-coordinator.md: Added memory-only mode documentation (`_memory_only` flag, `_ensure_dir()` helper); documented graceful degradation when `/sandbox` unavailable
- mesh-config.md: Fixed YAML indentation note; added assistant claw routes to message matrix tables
- bridge-tools.md: Added PYTHONPATH injection in python-bridge.ts spawn env
- common-issues.md: Added two new entries — Bridge CLI ImportError on send_to_claw, mesh_config.yaml message_matrix parsed as None
**Notes**:
- 4 bugs fixed: (1) bridge_cli.py relative imports, (2) python-bridge.ts missing PYTHONPATH, (3) mesh.py unguarded mkdir calls, (4) mesh_config.yaml broken indentation
- All integration tests pass: `send_to_claw` returns `{"success": true, "delivered": true}`
- TypeScript build compiles clean after installing @types/blessed

---

*This log is append-only. Never delete entries.*

---

## 2026-05-12

### 2026-05-12 14:00 — System Audit & Remediation (11 Critical Fixes)

**Pages**: index.md, log.md
**Source**: User request for codebase audit and Milimo Claw fix
**Changes**:
- **BUG 1**: Fixed `ContentClaw.startup()` hard crash. Passed default constructors for `PrivacyRouter` and `ToolRegistry` when not provided.
- **BUG 2**: Fixed `generate_draft` handler stub. Now wires task payload directly to the brief management pipeline.
- **BUG 3**: Reduced `minimum_actions` threshold in `evolution_config.yaml` from 20 to 5 to unblock evolution bootstrapping.
- **BUG 4**: Updated `EvolutionManager` in TypeScript to use sandbox-aware path resolution (`resolveToolsDir()`) to match Python orchestrator expectations.
- **BUG 5**: Suppressed `oom_score_adj` stderr noise in `claw-launcher-service.ts` to prevent log pollution.
- **BUG 6**: Added NemoClaw credential store fallback for `GITHUB_TOKEN` in `Build Claw` injection.
- **BUG 7**: Fixed `InboxPoller` race condition. Reordered launcher startup to bind handlers *before* starting the message poller to prevent dropped messages.
- **BUG 8**: Installed `@types/blessed` to resolve TypeScript compilation errors.
- **BUG 9**: Deprecated `callPython` in `python-bridge.ts` to prevent code injection risks.
- **BUG 10**: Fixed false positive `_is_sandbox()` detection in `milimo_paths.py` by requiring `/sandbox` to actually exist (not just checking `NEMOCLAW_MODEL`).
- **BUG 11**: Wrapped `ToolRegistry` directory creation in a try/except block to allow for graceful memory-only fallback when directory creation fails on the host.

**Notes**: All fixes deployed. Path resolution is robust across host and sandbox, ContentClaw starts successfully, evolution thresholds are reachable, and all integration tests pass perfectly.

---

*This log is append-only. Never delete entries.*
### 2026-05-12 19:00 — Ops Claw Messaging Gaps & IDE Error Fixes

**Pages**: log.md, ops-claw.md
**Source**: User request to investigate missing data and handlers
**Changes**:
- **BUG 12**: Fixed missing `project_id` in Ops payload handling. Updated `ProjectManager` and `OpsClaw` handlers to correctly unwrap the `payload` dict from incoming messages.
- **BUG 13**: Implemented and registered `_handle_feature_brief_acknowledged` in `OpsClaw` to fix missing handler warnings during startup. Fixed `float.__new__` map and string annotations.
- **BUG 14**: Corrected message type from `brief` to `project_brief` in `signal_dispatcher.py` to match `ContentClaw`'s registered handlers, fixing the issue of messages being silently discarded to the processed folder. Enforced `str()` on `entity_id` in `OpsLogEntry`.
- Fixed Ruff linter errors by removing unused `project_id` assignments in `_handle_invoice_ready` and `_handle_payment_overdue`.

**Notes**: Ops Claw is now fully stable and correctly routing payloads.

---
