# Milimo Claw — Comprehensive Implementation Plan

## Objective

Address all critical and high-severity gaps identified in the full codebase audit, ensuring seamless connectivity across all 5 claws, proper dependency injection, working deployment infrastructure, and robust error handling.

## Priority Classification

- **P0 (Critical)**: System-breaking bugs that prevent core functionality
- **P1 (High)**: Significant functional gaps that degrade system reliability
- **P2 (Medium)**: Operational issues that affect production readiness
- **P3 (Low)**: Code quality and consistency improvements

---

## Phase 1: P0 — Critical System Bugs

### Step 1: Fix FailoverManager Constructor Signature Mismatch

- [ ] **Issue**: `claw_launcher.py:395-399` passes `heartbeat_dir`, `check_interval`, `unhealthy_threshold` but `FailoverManager.__init__` expects `mesh_coordinator`, `heartbeat_timeout_ms`, `max_recovery_attempts` — silently fails due to exception catch
- [ ] **Fix**: Create a `HeartbeatMonitor` wrapper class that accepts filesystem-based configuration and implements the monitoring interface, OR adapt the launcher to create a minimal `MeshCoordinator` and pass it to `FailoverManager`
- [ ] **Location**: `milimo-blueprint/orchestrator/claw_launcher.py:391-404`
- [ ] **Verification**: FailoverManager starts without errors and monitors claw heartbeats

### Step 2: Fix Code Generator Per-File Content Bug

- [ ] **Issue**: `code_generator.py:186-191` writes the entire `implementation` string to every file in `files_changed` instead of parsing and writing per-file content
- [ ] **Fix**: Build a `file_contents` dict during the parsing loop (lines 160-178) that maps filenames to their extracted content, then iterate `file_contents.items()` when committing
- [ ] **Location**: `milimo-blueprint/orchestrator/build/code_generator.py:160-191`
- [ ] **Verification**: Each file in a multi-file change receives only its own content

### Step 3: Fix Content Generator Inference Client Architecture

- [ ] **Issue**: `content_generator.py:380-381` creates a fresh `NvidiaInferenceClient()` on every call instead of using the injected dependency — no shared state, no usage tracking
- [ ] **Fix**: Add `inference_client` parameter to `ContentGenerator.__init__()`, wire it in `ContentClaw.startup()`, and use `self._inference_client.complete()` in `_call_inference()`
- [ ] **Location**: `milimo-blueprint/orchestrator/content/content_generator.py:365-390`, `milimo-blueprint/orchestrator/content/content_claw.py:120-146`
- [ ] **Verification**: Content generation uses the same inference client instance passed from the launcher

### Step 4: Fix Platform Publisher Retry Sleep Bug

- [ ] **Issue**: `platform_publisher.py:470-472` computes `wait_seconds` but never calls `time.sleep(wait_seconds)` — 8 retries fire instantly instead of every 15 minutes
- [ ] **Fix**: Add `time.sleep(wait_seconds)` after the log statement in the retry loop
- [ ] **Location**: `milimo-blueprint/orchestrator/content/platform_publisher.py:468-475`
- [ ] **Verification**: Retries are spaced 15 minutes apart

### Step 5: Fix Dockerfile HEALTHCHECK Path

- [ ] **Issue**: Dockerfile checks `~/.milimo/heartbeats/claw_build.json` but actual path is `~/.milimo/mesh/heartbeats/{role}.json` — HEALTHCHECK always fails
- [ ] **Fix**: Update Dockerfile HEALTHCHECK to use correct path pattern with role parameter
- [ ] **Location**: `Dockerfile:185-197`
- [ ] **Verification**: HEALTHCHECK passes when claws are running

---

## Phase 2: P1 — High-Severity Functional Gaps

### Step 6: Register Claw Instances for Graceful Shutdown

- [ ] **Issue**: `claw_launcher.py:432-445` only registers heartbeat/poller to `components` list — claw instances (with their schedulers, webhook servers, collection workers) are never stopped
- [ ] **Fix**: Add claw objects to the `components` list so `claw.shutdown()` is called during signal handler shutdown
- [ ] **Location**: `milimo-blueprint/orchestrator/claw_launcher.py:376-386`, `432-445`
- [ ] **Verification**: All claw schedulers and background threads stop cleanly on SIGTERM

### Step 7: Fix KeyboardInterrupt Bypassing Shutdown

- [ ] **Issue**: `claw_launcher.py:475-476` catches `KeyboardInterrupt` but only logs — doesn't call the shutdown handler
- [ ] **Fix**: Call the shutdown logic explicitly from the `KeyboardInterrupt` handler or remove the try/except block
- [ ] **Location**: `milimo-blueprint/orchestrator/claw_launcher.py:472-476`
- [ ] **Verification**: Ctrl+C triggers full graceful shutdown

### Step 8: Wire Mesh Communication for Content/Ops/Analytics Claws

- [ ] **Issue**: Content, Ops, and Analytics claws receive `None` or `MockMeshGateway` for mesh communication — inter-claw signaling is disabled
- [ ] **Fix**: Create a shared `MeshCoordinator` instance in the launcher and pass it (or a sender adapter) to each claw that needs mesh communication
- [ ] **Location**: `milimo-blueprint/orchestrator/claw_launcher.py:240-281`
- [ ] **Verification**: Content, Ops, and Analytics claws can send messages to other claws via the mesh

### Step 9: Implement DependencyAuditor.run_full_audit()

- [ ] **Issue**: `build_scheduler.py:164` and `build_scheduler.py:248` call `self._dependency_auditor.run_full_audit()` but this method doesn't exist — scheduler crashes on weekly audit
- [ ] **Fix**: Add `run_full_audit()` method to `DependencyAuditor` that fetches Dependabot alerts, assesses each, and auto-drafts or queues reviews
- [ ] **Location**: `milimo-blueprint/orchestrator/build/dependency_auditor.py`
- [ ] **Verification**: Weekly dependency audit runs without AttributeError

### Step 10: Fix Analytics Generic Collector Dispatch Bug

- [ ] **Issue**: `collection_workers.py:185-187` checks `elif name == "generic"` but generic collectors are registered with custom names (e.g., "stripe") — they never execute
- [ ] **Fix**: Change `elif name == "generic":` to `else:` so all non-YouTube, non-GA4 collectors execute
- [ ] **Location**: `milimo-blueprint/orchestrator/analytics/collection_workers.py:185-187`
- [ ] **Verification**: Generic API collectors execute on schedule

### Step 11: Fix MetricsCollector Cross-Process Readability

- [ ] **Issue**: `MetricsCollector.get_summary()` reads only from in-memory `_counters` and `_timings` — when `EvolutionIntegration` creates fresh instances, they see empty data
- [ ] **Fix**: Add `_read_from_file()` method that parses `metrics.jsonl` and reconstructs counters/timings; call it in `get_summary()` when in-memory data is empty
- [ ] **Location**: `milimo-blueprint/orchestrator/metrics_collector.py:153-175`
- [ ] **Verification**: Evolution cycle receives actual metrics from all claws

### Step 12: Wire NvidiaInferenceClient to Evolution Cycle

- [ ] **Issue**: `EvolutionIntegration` creates an `NvidiaInferenceClient` but never passes it to `EvolutionCycle` or `ToolBuilder` — tool generation uses templates, not real inference
- [ ] **Fix**: Pass `self.inference_client` from `EvolutionIntegration` through `EvolutionCycle` to `ToolBuilder`, and update `ToolGenerator._call_llm()` to use it
- [ ] **Location**: `milimo-blueprint/orchestrator/evolution_integration.py`, `milimo-blueprint/orchestrator/evolution_cycle.py`, `milimo-blueprint/orchestrator/tool_builder.py`
- [ ] **Verification**: Evolution cycle generates tools using real inference, not templates

---

## Phase 3: P2 — Medium-Severity Operational Issues

### Step 13: Fix Content Generator Privacy Router Data Type Mapping

- [ ] **Issue**: `content_generator.py:370-377` maps `routing.backend.value` (e.g., "cloud", "local-nim") to data types, but keys are content categories — always falls through to "general"
- [ ] **Fix**: Use the `data_type` from `_determine_data_type()` instead of `routing.backend.value` for the lookup
- [ ] **Location**: `milimo-blueprint/orchestrator/content/content_generator.py:370-377`
- [ ] **Verification**: Correct inference category is selected based on content type

### Step 14: Fix Content Scheduler Async Fire-and-Forget

- [ ] **Issue**: `content_scheduler.py:179` uses `asyncio.ensure_future()` without awaiting — `generate_daily_plan()` may not complete and errors are silently swallowed
- [ ] **Fix**: Use `asyncio.run()` in the sync context path, or convert the scheduler to use a persistent event loop
- [ ] **Location**: `milimo-blueprint/orchestrator/content/content_scheduler.py:174-189`
- [ ] **Verification**: Daily plan generation completes reliably

### Step 15: Add Finance Claw Approval Message Handlers

- [ ] **Issue**: `FinanceClaw.handle_inbound()` only routes `pricing_query` and `project_complete` — no handlers for `hold_release`, `review_approve`, `review_edit`, `review_block` — War Room approval flow has no integration point
- [ ] **Fix**: Add message type handlers for approval actions that call the appropriate `FinanceApprovalHandler` methods
- [ ] **Location**: `milimo-blueprint/orchestrator/finance/finance_claw.py:261-332`
- [ ] **Verification**: War Room can approve/reject/release finance actions via mesh messages

### Step 16: Add Stripe Configuration Validation at Finance Startup

- [ ] **Issue**: `FinanceClaw.startup()` doesn't check `stripe_client.is_configured()` — system initializes silently with no Stripe credentials
- [ ] **Fix**: Add a configuration check in `startup()` that logs a warning if Stripe is not configured
- [ ] **Location**: `milimo-blueprint/orchestrator/finance/finance_claw.py:110-231`
- [ ] **Verification**: Warning logged when Stripe credentials are missing

### Step 17: Fix MeshCoordinator Factory Methods for Privacy Router

- [ ] **Issue**: `MeshCoordinator.from_config_file()` and `from_dict()` don't load or instantiate a `PrivacyRouter` — privacy classification is silently skipped in production
- [ ] **Fix**: Add optional `privacy_policy_path` parameter to factory methods and instantiate `PrivacyRouter` when provided
- [ ] **Location**: `milimo-blueprint/orchestrator/mesh.py:139-190`
- [ ] **Verification**: Privacy router is loaded when config file includes policy path

### Step 18: Fix Docker Compose Environment Variables

- [ ] **Issue**: `analytics-claw` and `finance-claw` services are missing `NVIDIA_API_KEY`; finance service missing `STRIPE_API_KEY` and `STRIPE_WEBHOOK_SECRET`; env var name mismatch (`STRIPE_SECRET_KEY` vs `STRIPE_API_KEY`)
- [ ] **Fix**: Add missing env vars to docker-compose.yml; standardize on `STRIPE_API_KEY` in `.env.example`
- [ ] **Location**: `docker-compose.yml:124-181`, `.env.example:14-16`
- [ ] **Verification**: All claws receive required API keys via docker-compose

### Step 19: Fix milimo-mesh Volume Mount Path

- [ ] **Issue**: `docker-compose.yml` mounts `milimo-mesh` at `/root/.milimo/mesh` but code uses `/sandbox/.milimo/mesh` (HOME=/sandbox) — volume is effectively unused
- [ ] **Fix**: Change mount point to `/sandbox/.milimo/mesh` for all services
- [ ] **Location**: `docker-compose.yml:35,68,101,134,165`
- [ ] **Verification**: Mesh data persists correctly across container restarts

### Step 20: Clear Alert Buffer on Webhook Server Restart

- [ ] **Issue**: `_WebhookHandler.alert_buffer` is class-level and never cleared on restart — stale alerts persist across lifecycles
- [ ] **Fix**: Add `alert_buffer.clear()` in `OpsWebhookServer.start()`
- [ ] **Location**: `milimo-blueprint/orchestrator/ops/webhook_server.py:200-215`
- [ ] **Verification**: Alert buffer is empty after server restart

---

## Phase 4: P3 — Code Quality and Consistency

### Step 21: Fix PR Manager Line Count Metadata Bug

- [ ] **Issue**: `pr_manager.py:104-105` uses `resolution.tests_passing` as `lines_added` and `resolution.tests_failing` as `lines_removed` — incorrect metadata
- [ ] **Fix**: Track actual lines added/removed during code generation and pass them to the PR record
- [ ] **Location**: `milimo-blueprint/orchestrator/build/pr_manager.py:100-110`
- [ ] **Verification**: PR records show accurate line counts

### Step 22: Fix HeartbeatEmitter Uptime Calculation

- [ ] **Issue**: `claw_launcher.py:96` uses `time.monotonic()` which returns process uptime, not emitter uptime — meaningless values
- [ ] **Fix**: Track emitter start time and compute uptime relative to that
- [ ] **Location**: `milimo-blueprint/orchestrator/claw_launcher.py:57-99`
- [ ] **Verification**: Heartbeat uptime reflects actual emitter uptime

### Step 23: Standardize NVIDIA API Key Configuration

- [ ] **Issue**: Build claw uses `BUILD_CLAW_NVIDIA_API_KEY` fallback but other claws only use `NVIDIA_API_KEY` — inconsistent
- [ ] **Fix**: Standardize on `NVIDIA_API_KEY` for all claws, or document per-claw override pattern consistently
- [ ] **Location**: `milimo-blueprint/orchestrator/claw_launcher.py:185,244,258,272,287`
- [ ] **Verification**: All claws use consistent API key configuration

### Step 24: Remove Dead Code in Doc Maintainer

- [ ] **Issue**: `doc_maintainer.py:181` references `self._fs.base_path` which doesn't exist (should be `self._fs.base`) — `check_doc_drift()` is never called
- [ ] **Fix**: Either fix the attribute reference or remove the dead method
- [ ] **Location**: `milimo-blueprint/orchestrator/build/doc_maintainer.py:175-185`
- [ ] **Verification**: No AttributeError if `check_doc_drift()` is ever called

### Step 25: Add Analytics Collector Environment Variables to .env.example

- [ ] **Issue**: `.env.example` doesn't document `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID`, `GA4_PROPERTY_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `COLLECTOR_*` variables
- [ ] **Fix**: Add all Analytics Claw collector environment variables to `.env.example`
- [ ] **Location**: `.env.example`
- [ ] **Verification**: Operators can configure real data collection from env documentation

---

## Verification Criteria

| Phase | Success Metric |
|-------|---------------|
| Phase 1 (P0) | All 5 critical bugs fixed: FailoverManager starts, code generator writes per-file content, content generator uses injected inference client, publisher retries sleep, Dockerfile HEALTHCHECK passes |
| Phase 2 (P1) | All 7 high-severity gaps closed: graceful shutdown works, KeyboardInterrupt handled, mesh communication wired, dependency audit runs, generic collectors execute, metrics readable cross-process, evolution uses real inference |
| Phase 3 (P2) | All 8 operational issues resolved: privacy routing correct, async handling reliable, finance approval handlers wired, Stripe validation present, privacy router loaded in factories, docker-compose env vars complete, volume mounts correct, alert buffer cleared |
| Phase 4 (P3) | All 5 code quality issues fixed: PR metadata accurate, heartbeat uptime correct, API key config consistent, dead code removed, env vars documented |

## Execution Order

Execute phases in order: P0 → P1 → P2 → P3. Each phase unblocks the next. Phase 1 fixes are critical for system stability. Phase 2 fixes enable full multi-claw functionality. Phase 3 fixes improve production readiness. Phase 4 fixes improve code quality and maintainability.

## Risk Assessment

1. **Mesh communication wiring (Step 8)**: May require changes to multiple claw constructors. Mitigation: Use adapter pattern to avoid breaking existing interfaces.
2. **Evolution cycle inference wiring (Step 12)**: ToolBuilder architecture may need refactoring. Mitigation: Add inference client as optional parameter with template fallback.
3. **MetricsCollector cross-process read (Step 11)**: JSONL parsing may be slow for large files. Mitigation: Add configurable lookback window and streaming parser.
