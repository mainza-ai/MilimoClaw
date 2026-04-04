# MilimoClaw Complete Gap Remediation Plan

## Objective

Address all identified gaps across the 5 claws, orchestrator core, and TypeScript plugin — derived from cross-referencing every spec document in `milimo-claw-docs/` against the actual implementation. This plan covers 50+ gaps organized by severity and dependency order.

---

## Current State Summary

| Claw | Modules | Functional Gaps | Critical | High | Medium | Low |
|---|---|---|---|---|---|---|
| **Content** | 11/11 | Constructor mismatch, stub publishers, broken revision flow | 2 | 3 | 2 | 3 |
| **Ops** | 11/11 | 5 stubs in ops_claw.py (proposal send, change order execute, archive) | 0 | 2 | 2 | 1 |
| **Analytics** | 12/12 | Report generator uses simplified projections, mock trend data, empty fields | 0 | 0 | 2 | 3 |
| **Finance** | 12/11+1 empty | Pricing SLA not enforced, weekly summary missing steps, empty __init__.py | 0 | 1 | 1 | 1 |
| **Build** | 0/13 | Entire Python implementation missing (13 modules, ~5000 lines) | 1 | 0 | 0 | 0 |
| **Core Orchestrator** | 38 modules | overdue_alert missing from contracts, tool sandbox unused, LLM placeholder | 1 | 2 | 2 | 2 |
| **TypeScript Plugin** | 55 TS + 3 JS | Stale .js files actively used, HOLD mode never returned, unencrypted fallback | 1 | 2 | 0 | 3 |

---

## Implementation Plan

### Phase 1: Critical Fixes — Blockers and Security Risks

- [ ] **1.1 Fix ContentClaw → ContentGenerator constructor mismatch** — `content_claw.py:132-137` passes `inference_client` and `voice_manager` but `ContentGenerator.__init__()` expects `privacy_router` and `tool_registry`. Rewire constructor to pass correct parameters and wire up privacy_router + tool_registry in ContentClaw.

- [ ] **1.2 Delete stale .js files in milimo/src/warroom/** — Remove `approval.js`, `audit.js`, `warroom.js`. These are compiled artifacts that are actively imported by `slash.ts:21` and contain outdated code (no rate limiting, no tier support, old CLI patterns).

- [ ] **1.3 Add `overdue_alert` to contracts.py VALID_MESSAGE_TYPES** — `mesh_config.yaml:82-84` defines `overdue_alert` as a Finance → War Room message type, but `contracts.py:47-90` does not include it. Add it to `VALID_MESSAGE_TYPES` and create a schema entry in `MESSAGE_TYPE_SCHEMAS`.

- [ ] **1.4 Implement Build Claw Python modules (13 files)** — The `orchestrator/build/` directory does not exist. Create all 13 modules following the Build Claw spec (`MILIMO_CLAW_BUILD_CLAW_SPEC.md`): `__init__.py`, `build_init.py`, `issue_manager.py`, `code_generator.py`, `pr_manager.py`, `deploy_manager.py`, `error_monitor.py`, `cost_monitor.py`, `dependency_auditor.py`, `doc_maintainer.py`, `approval_handler.py`, `signal_dispatcher.py`, `build_claw.py`, `build_scheduler.py`. The existing 2,836 lines of tests in `test_build_unit.py` and `test_build_mvr_integration.py` define the exact API contracts.

- [ ] **1.5 Populate Finance Claw `__init__.py`** — Currently 0 bytes. Export all public classes matching the pattern used by other claws: `FinanceClaw`, `PricingEngine`, `InvoiceManager`, `PaymentMonitor`, `ApprovalHandler`, `RevenueTracker`, `ExpenseTracker`, `FinanceScheduler`, `SignalDispatcher`.

### Phase 2: High Priority — Broken Functionality

- [ ] **2.1 Implement per-claw/per-action-type approval mode evaluation** — `approval.ts:103-139` never returns `HOLD` mode and doesn't load the Python blueprint's `approval_modes` structure. Add logic to load approval mode config and return `HOLD` for `finance:invoice_send` and `build:pr_merge` actions.

- [ ] **2.2 Wire revision_request regeneration in Content Claw** — `brief_manager.py:302-359` returns `revision_context` with `regeneration_required: True` but `content_claw.py:333-334` discards it. Wire the returned context to trigger `ContentGenerator.generate_draft()` with revision notes.

- [ ] **2.3 Connect publish → performance_signal pipeline** — `platform_publisher.py:_handle_publish_success()` does not call `PerformanceMonitor.monitor_post()`. Add the call so that `performance_signal` is automatically sent to Analytics Claw after each publish.

- [ ] **2.4 Auto-trigger `deliverable_complete` in Content Claw** — `brief_manager.py:375-425` (`complete_brief`) exists but nothing calls it. Add logic to detect when all deliverables for a project are approved and published, then auto-trigger `complete_brief()`.

- [ ] **2.5 Fix Ops Claw stubs — proposal send and change order execute** — `ops_claw.py:386` (proposal send) and `ops_claw.py:393` (scope change order execute) are empty `pass` statements. Implement the actual send/execute logic using the signal dispatcher and comms manager.

- [ ] **2.6 Wire War Room references to Content Claw components** — `content_claw.py` does not pass `war_room` to `ContentApprovalHandler`, `PlatformPublisher`, or `PerformanceMonitor`. Pass the war_room reference so rejection alerts, publish failures, and anomaly flags are surfaced.

- [ ] **2.7 Encrypt fallback file messages** — `gateway-client.ts:250-256` writes plaintext JSON to disk when gateway is unavailable. Use the existing `MessageEncryption` class or add AES-256-GCM encryption to `sendFileMessage()`.

- [ ] **2.8 Enforce pricing SLA timeout** — `pricing_engine.py:63` defines `RESPONSE_TIMEOUT_SECONDS = 540` but never uses it. Wrap the inference call with `asyncio.wait_for()` or a threading timer to enforce the 10-minute SLA and return a fallback response on timeout.

### Phase 3: Medium Priority — Incomplete Implementations

- [ ] **3.1 Wire ForwardProjector into ReportGenerator** — `analytics_claw.py:137` instantiates `ForwardProjector` but `report_generator.py:612-631` uses a simplified inline projection. Replace `_generate_forward_projections()` with a call to `ForwardProjector.project_all()`.

- [ ] **3.2 Replace mock trend data in OpportunityScorer** — `opportunity_scorer.py:431-439` returns hardcoded trend data. Replace with actual API calls to approved external endpoints (Google Trends, etc.) per the spec's egress policy.

- [ ] **3.3 Implement computed fields in ReportGenerator** — Populate `worst_performing` (`report_generator.py:328`), `platform_algorithm_notes` (`report_generator.py:329`), `new_signals` (`report_generator.py:401`), and `velocity_vs_baseline` (`report_generator.py:491`) with actual computed values instead of empty/hardcoded defaults.

- [ ] **3.4 Add missing steps to Finance weekly summary** — `revenue_tracker.generate_weekly_summary()` does not call `margin_analysis()` or `rate_optimization_check()`. Add these calls to the weekly Sunday 03:00 cycle as required by the spec.

- [ ] **3.5 Implement `_archive_project()` in Ops Claw** — `project_manager.py:470` is an empty `pass`. Add logic to move project files from `active/` to `completed/` directory after delivery confirmation.

- [ ] **3.6 Fix Ops Claw `_register_approval_handlers()`** — `ops_claw.py:265` is empty. Wire up post-approval callback handlers for proposal approval, change order release, and deadline critical release.

- [ ] **3.7 Fix Content Generator data_type logging** — `content_generator.py:195-206` logs `content_type`, `tools_applied`, and `routing_backend` but not `data_type`. Add `data_type` to the `LogEntry` details dict.

- [ ] **3.8 Wire evolution cycle into Content Scheduler** — `content_scheduler.py` does not schedule or trigger the Sunday 02:00 evolution cycle. Add scheduling for `EvolutionCycle.run_cycle()`.

- [ ] **3.9 Add retry logic to mesh gateway connection** — `mesh.py:233-237` returns `False` on connection failure with no retry. Add exponential backoff retry loop.

- [ ] **3.10 Implement automated health check loop in MeshCoordinator** — `mesh_config.yaml:145-149` defines `health_check` settings but `mesh.py` only has manual `heartbeat()` methods. Add an automated periodic health check loop.

- [ ] **3.11 Fix strict inequality thresholds** — Change `>=` to `>` for anomaly thresholds (`anomaly_detector.py:110, 120`) and opportunity dispatch threshold (`opportunity_scorer.py:96`) to match spec's strict inequalities.

### Phase 4: Low Priority — Cleanup and Polish

- [ ] **4.1 Remove unused `message-encryption.ts`** — The entire `MessageEncryption` class in `mesh/message-encryption.ts` is not imported anywhere. Delete it to reduce confusion.

- [ ] **4.2 Add error logging for non-interactive NemoClaw missing case** — `onboard.ts:118` silently returns when NemoClaw is not onboarded in non-interactive mode. Add error logging and a non-zero exit code.

- [ ] **4.3 Remove dead `config-legacy.ts`** — `onboard/config-legacy.ts` is a 14-line re-export that is superseded by `ConfigManager`. Remove it and update the re-export in `config.ts:255`.

- [ ] **4.4 Add specialized TUI card rendering for more message types** — `warroom-tui.ts:368-394` only renders `tool_proposal` and `deliverable` specially. Add rendering for `invoice`, `alert`, `status_update`, and other common message types.

- [ ] **4.5 Replace evolution log placeholder in TUI** — `warroom-tui.ts:445` shows a hardcoded placeholder string. Wire it to actual evolution log data.

- [ ] **4.6 Fix Content Claw morning planning to send daily analytics query** — `content_scheduler.py:_morning_planning()` does not send `content_performance_query` daily as the spec requires. Add the daily query in addition to the weekly Monday query.

- [ ] **4.7 Implement `_call_inference()` stub in ContentGenerator** — `content_generator.py:365-368` returns a fabricated string. Integrate with the privacy router's inference backend.

- [ ] **4.8 Implement platform publisher HTTP calls** — `platform_publisher.py` stub publishers return fake post IDs. Implement actual HTTP calls to platform APIs with proper credential validation, retry with `time.sleep()`, and egress allowlist checking.

- [ ] **4.9 Remove unused imports in tool_builder.py** — `ToolSandbox`, `SandboxRunner`, `SandboxBacktestResult`, and `_meets_threshold` are imported but never used. Either wire them into the tool builder or remove the imports.

- [ ] **4.10 Fix template validation in assistant_setup.py** — `assistant_setup.py:152-156` only checks known placeholders. Add detection for unknown template variables that pass silently.

- [ ] **4.11 Add `weekly-intelligence.json` mount check in content_init.py** — `content_init.py:256` creates a stub `{}` file where a read-only mount from Analytics Claw should exist. Check for the mount point before creating the file.

- [ ] **4.12 Fix ContentClaw approval handler ID mismatch** — `content_claw.py:374-377` passes `action_id` as `draft_id` to approval handlers. Extract the actual `draft_id` from the action's payload.

- [ ] **4.13 Add payload schemas for untyped message types** — `query`, `response`, `signal`, `deliverable`, `summary`, `payment_overdue` have no schema in `MESSAGE_TYPE_SCHEMAS`. Add schemas for payload validation.

---

## Verification Criteria

1. **All 5 claws pass spec compliance** — Every checkpoint from the spec documents is implemented and tested
2. **Build Claw tests pass** — All 2,836 lines of existing tests in `test_build_unit.py` and `test_build_mvr_integration.py` pass
3. **No stale .js files** — `milimo/src/warroom/` contains only `.ts` files
4. **No constructor mismatches** — All claw constructors match their component signatures
5. **All message types validated** — Every message type in `mesh_config.yaml` is in `contracts.py` VALID_MESSAGE_TYPES with a schema
6. **HOLD mode functional** — `approval.ts` returns HOLD for applicable actions (finance:invoice_send, build:pr_merge)
7. **Fallback messages encrypted** — File-based queue messages are encrypted at rest
8. **SLA timeouts enforced** — Pricing engine and query handler enforce their timeouts
9. **Full test suite passes** — `npm test` for TypeScript, `pytest` for Python, with no `continue-on-error`

---

## Potential Risks and Mitigations

1. **Build Claw scope is large (13 modules, ~5000 lines)** — This is the biggest single task. Mitigation: Build modules in dependency order (init → signal_dispatcher → approval_handler → core managers → monitors → scheduler → build_claw) and run tests incrementally.

2. **Platform publisher HTTP calls require external API credentials** — The stub publishers don't need credentials, but real API calls do. Mitigation: Implement the HTTP call structure with credential injection points; use mock credentials for testing.

3. **Constructor mismatch fix may cascade** — Rewiring ContentClaw's constructor may require changes to how it's instantiated in solo_init.py. Mitigation: Check all instantiation points before changing the constructor.

4. **Approval mode evaluation requires loading Python blueprint config** — The TypeScript plugin needs access to the YAML approval_modes structure. Mitigation: Read the YAML at plugin startup or pass it via the onboard config.

---

## Alternative Approaches

1. **Phase-by-phase vs. claw-by-claw**: Instead of organizing by severity, organize by claw (fix all Content gaps, then all Ops gaps, etc.). This is cleaner for testing but delays critical fixes in later claws. The severity-based approach is preferred for risk reduction.

2. **Build Claw: skeleton-first vs. test-first**: Write all 13 module skeletons first, then fill in implementations. vs. Write one module at a time and run its tests immediately. The test-first approach is preferred because the existing tests define the exact API contracts.

3. **Platform publishers: keep stubs vs. implement real APIs**: Keep the stub publishers and add a "publish mode" config (stub vs. real). This allows testing without API credentials. Preferred: implement real API structure with a configurable publish mode flag.
