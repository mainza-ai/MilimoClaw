# Milimo Claw System Audit Report

## Objective

Comprehensive audit of the Milimo Claw codebase cross-referenced against Lucy's interaction log (`lucy_question.md`) to identify gaps, missing functionalities, and systemic issues.

---

## Executive Summary

The Milimo Claw system is architecturally ambitious — a multi-agent autonomous platform with 5 specialized AI "claws" (Content, Ops, Analytics, Finance, Build) communicating through a typed contract mesh, coordinated via a War Room approval system, and exposed through a TypeScript CLI + Python orchestrator bridge. The **architecture is well-designed on paper** but **functionally incomplete in practice**. Six critical gaps prevent the system from operating as intended, with the root cause being a chain of unimplemented dependencies that cascade from the inference layer up through the execution pipeline.

---

## Issue 1: OpenCode / Inference Integration — **CRITICAL**

### Lucy's Complaint
Lucy attempted to install OpenCode and oh-my-openagent to give the Build Claw coding capability. She installed the oh-my-opencode CLI plugin but could not install the OpenCode binary due to sandbox network restrictions. The Build Claw has no actual AI inference backend.

### Code Analysis
- `claw_launcher.py:182-194` — The launcher creates **Mock** clients (`MockGitHubClient`, `MockInferenceClient`, `MockVercelClient`, `MockSentryClient`) that are empty shells with only attribute storage and zero methods
- `build_init.py:77-81` — Defines `INFERENCE_FALLBACK_CHAIN = ["nemotron-120b", "claude-sonnet-4-6", "gemini-3.1-pro"]` but no code ever implements the fallback retry logic
- `build_init.py:84-125` — Defines `BUILD_CATEGORIES` mapping task types to models and temperatures, but no inference routing code uses this
- `code_generator.py:129-133` — Calls `self._inference.complete(prompt=..., data_type=..., temperature=...)` but this method does not exist on any real class
- **No inference client implementation exists anywhere in the codebase** — no `NvidiaInferenceClient`, no `PrivacyRouter`-backed client, no OpenCode integration

### Impact
The Build Claw cannot generate code, score issues, write PR descriptions, create changelogs, or perform any AI-dependent task. The entire coding pipeline is inert.

### Severity: Critical

---

## Issue 2: GitHub Client — **CRITICAL**

### Lucy's Complaint
Lucy noted that `gh` CLI is available in the MilimoClaw container but not wired into the Build Claw. The launcher uses a mock client.

### Code Analysis
- `claw_launcher.py:182-184` — `MockGitHubClient` has only `self.token = os.environ.get("GITHUB_TOKEN", "")` — no methods
- `issue_manager.py:89` — Calls `self._github.get_open_issues()` — method does not exist
- `code_generator.py:185-191` — Calls `self._github.create_branch()` and `self._github.commit_file()` — methods do not exist
- `pr_manager.py:89-93` — Calls `self._github.create_pull_request()` and `self._github.merge_pull_request()` — methods do not exist
- `dependency_auditor.py` — Calls `self._github` for vulnerability scanning — methods do not exist
- `bridge_cli.py:944-977` — `handle_build_open_prs` correctly uses `subprocess.run(["gh", "pr", "list", ...])` — this is the **only** place in the codebase where `gh` CLI is actually invoked

### Impact
The Build Claw cannot fetch issues, create branches, commit files, create PRs, merge PRs, or scan dependencies. The entire GitHub workflow is inert.

### Severity: Critical

---

## Issue 3: Message Handling → Execution Pipeline Gap — **CRITICAL**

### Lucy's Complaint
Lucy sent a `feature_brief` message to the Build Claw requesting OpenCode installation. The message was received, logged, and moved to `processed/` — but zero execution occurred.

### Code Analysis
- `build_claw.py:214-218` — Inbound handler for `feature_brief` routes to `self._dispatcher.handle_feature_brief`
- `signal_dispatcher.py:200-233` — `handle_feature_brief()` does exactly three things:
  1. Validates the message type
  2. Starts a 10-minute SLA timer (which fires an overdue warning if not acknowledged)
  3. Logs the receipt
- **There is no code path from `handle_feature_brief` to `issue_manager.plan_sprint()` or `code_generator.resolve_issue()`**
- The expected pipeline should be: `feature_brief` → fetch GitHub issues → score complexity → generate sprint plan → queue for approval → (human approves) → resolve issues → generate code → create PR → queue for review → (human approves) → queue for merge hold → (human releases) → merge → deploy
- The actual pipeline is: `feature_brief` → log → start SLA timer → done

### Impact
Even if inference and GitHub clients were fully implemented, the Build Claw would still not execute any work from inbound messages. The message handler is a dead end.

### Severity: Critical

---

## Issue 4: Process Supervision / Heartbeat Monitoring — **MODERATE**

### Lucy's Complaint
Lucy discovered the Build Claw had been dead for 5+ hours (heartbeat stale since 08:08 UTC). The launcher process died and nothing restarted it.

### Code Analysis
- `claw_launcher.py:57-99` — `HeartbeatEmitter` writes heartbeat files every 30 seconds — **this works**
- `mesh.py:434-444` — `MeshCoordinator.heartbeat()` records heartbeats into topology — **this works**
- `mesh_failover.py:261-305` — `FailoverManager._check_node_health()` monitors heartbeats and marks nodes unhealthy/offline — **this exists but is never instantiated**
- `claw_launcher.py:274-276` — The shutdown handler calls `sys.exit(0)` but does **not** call `heartbeat.stop()`, `poller.stop()`, or `claw.shutdown()` before exiting
- **No process supervisor** — no systemd unit, no supervisord, no Docker restart policy, no watchdog

### Impact
When the launcher process dies (which it did), claws are permanently offline until manually restarted. The failover monitoring system exists but is never wired into the startup process.

### Severity: Moderate

---

## Issue 5: Generic Claws Are Inert — **MODERATE**

### Lucy's Complaint
Lucy sent introduction messages to all 5 claws. Only the Build Claw processed its message. The other 4 claws (Content, Ops, Analytics, Finance) received messages but did nothing.

### Code Analysis
- `claw_launcher.py:233-244` — `start_generic_claw()` starts heartbeat + inbox poller but passes **no message handler**: `InboxPoller(role, poll_interval)` — the `message_handler` parameter defaults to `None`
- `InboxPoller._check_inbox()` at `claw_launcher.py:155-156` — checks `if self._message_handler:` before calling it. With no handler, messages are parsed and archived but never processed
- The full claw implementations exist (`content_claw.py`, `ops_claw.py`, `analytics_claw.py`, `finance_claw.py`) but they are never instantiated by the launcher
- Only `BuildClaw` is wired up with actual component initialization

### Impact
4 out of 5 claws are functionally inert. The squad mesh operates as a single-claw system. Inter-claw communication is broken for all non-build roles.

### Severity: Moderate

---

## Issue 6: Fallback Message Delivery Writes to Dead-Letter Directory — **MODERATE**

### Lucy's Complaint
Lucy had to write messages directly to each claw's inbox because the mesh validator blocked certain routes and messages were not delivered.

### Code Analysis
- `signal_dispatcher.py:313-321` — `_send_message()` tries gateway first, falls back to `_write_fallback_message()`
- `signal_dispatcher.py:323-327` — `_write_fallback_message()` writes to `self._fs.base / "messages"` (e.g., `/sandbox/build/messages/`) — this is a **local directory**, NOT the mesh inbox at `~/.milimo/mesh/inbox/{recipient}/`
- The `MeshCoordinator._send_via_file()` at `mesh.py:370-379` correctly writes to `~/.milimo/mesh/inbox/{recipient}/` — but the SignalDispatcher doesn't use MeshCoordinator for fallback
- Messages written to the fallback directory are effectively lost — no other process reads from them

### Impact
When the gateway is unavailable (which is the default since no gateway is configured), inter-claw messages are silently dropped into a dead-letter directory.

### Severity: Moderate

---

## Issue 7: War Room Routing — **RESOLVED (was previously broken)**

### Analysis
- `mesh.py:336-337` — `send_message()` now correctly routes approval-required messages to the War Room: `if needs_approval and message.recipient_role != "war_room": return self._route_to_warroom(message)`
- `mesh.py:465-501` — `_route_to_warroom()` writes messages to `~/.milimo/mesh/inbox/war_room/` with original routing metadata preserved
- `mesh_config.yaml:32-38` — Assistant message types are now in the message matrix
- `bridge_cli.py:770-776` — `send_to_claw` loads from the real `mesh_config.yaml` instead of an empty dict

### Status: Fixed

---

## Issue 8: Sandbox vs Container Environmental Separation — **ARCHITECTURAL CONSTRAINT**

### Lucy's Complaint
Lucy operates in the NemoClaw sandbox (restricted network, limited CLI) while the Build Claw runs in the MilimoClaw container (full network, authenticated `gh` CLI). Lucy attempted installations in the sandbox that should have been delegated to the Build Claw.

### Analysis
- This is not a code bug but an **architectural design constraint**
- The correct pattern is: Lucy sends tasks via `send_to_claw` → claws execute in the container
- However, because of Issues 1-3 above, even this correct pattern fails — the Build Claw receives the task but cannot execute it
- The `assistant_setup.py:195` bridge timeout of 3 seconds may be too short for filesystem-scanning commands

### Severity: Architectural (compounded by Issues 1-3)

---

## Root Cause Chain

The gaps form a dependency cascade:

```
No inference client (Issue 1)
  → Code generator cannot generate code
  → No GitHub client (Issue 2)
    → Issue manager cannot fetch issues, PR manager cannot create PRs
    → No execution path from messages (Issue 3)
      → Even with real clients, feature briefs only get logged
      → No process supervision (Issue 4)
        → When launcher dies, nothing restarts it
        → 4/5 claws are inert (Issue 5)
          → The squad mesh is functionally a single-claw system
          → Fallback messages go to dead-letter dir (Issue 6)
            → Inter-claw communication is silently broken
```

---

## What Actually Works

| Component | Status | Evidence |
|-----------|--------|----------|
| `MeshCoordinator` routing | Working | `mesh.py:290-343` — validates, routes, War Room integration |
| `GatewayAdapter` pattern | Working | `gateway_adapter.py` — 3 transport modes |
| `FailoverManager` logic | Exists but unused | `mesh_failover.py` — heartbeat monitoring code is correct |
| `ContractValidator` | Working | `contracts.py:593-648` — validates 47 message types |
| `BuildClaw` startup wiring | Working | `build_claw.py:100-227` — all 13 components wired |
| `Bridge CLI` (34 commands) | Working | `bridge_cli.py` — read-only commands functional |
| `War Room TUI` | Working | `warroom-tui.ts` — Blessed-based split-pane UI |
| `Approval Engine` | Working | `approval.ts` — 4-mode approval with escalation |
| Test infrastructure | Working | 318 tests, MVR test suite |
| Heartbeat writing | Working | `claw_launcher.py:57-99` — writes every 30s |

---

## What Is Missing or Broken

| Component | Status | Details |
|-----------|--------|---------|
| Inference client implementation | Missing | No class implements `.complete()` or `.get_usage()` |
| GitHub client implementation | Missing | No class wraps `gh` CLI or GitHub API |
| Message → execution pipeline | Broken | `handle_feature_brief` only logs + starts SLA timer |
| Process supervision | Missing | No watchdog, restart policy, or health check daemon |
| Generic claw handlers | Missing | Content, Ops, Analytics, Finance have no inbound handlers |
| Fallback message delivery | Broken | `signal_dispatcher._write_fallback_message` writes to wrong directory |
| Inference fallback chain | Defined but unused | `INFERENCE_FALLBACK_CHAIN` never wired into retry logic |
| Category-based model routing | Defined but unused | `BUILD_CATEGORIES` never consulted during inference calls |
| Test execution in code generator | Placeholder | `run_tests()` returns `("passing", 0, 0)` |
| Sentry/Vercel client implementations | Missing | Only mock stubs exist |
| FailoverManager startup | Missing | Never instantiated in `claw_launcher.py` |
| Graceful shutdown | Broken | `sys.exit(0)` without stopping threads or components |

---

## Gap Severity Summary

| # | Area | Severity | Root Cause |
|---|------|----------|------------|
| 1 | OpenCode / Inference | Critical | No inference client implementation |
| 2 | GitHub Client | Critical | Mock client lacks all required methods |
| 3 | Message → Execution | Critical | Handler only logs, no execution path |
| 4 | Process Supervision | Moderate | No watchdog or restart policy |
| 5 | Generic Claws Inert | Moderate | No message handlers wired |
| 6 | Fallback Dead-Letter | Moderate | Writes to wrong directory |
| 7 | War Room Routing | Resolved | Previously broken, now fixed |
| 8 | Sandbox/Container | Architectural | Design constraint, compounded by 1-3 |

---

## Recommendations (Priority Order)

### P0 — Build Claw Execution Pipeline
1. Implement `NvidiaInferenceClient` (or `PrivacyRouter`-backed client) that wraps the NVIDIA API with the fallback chain from `build_init.py:77-81`
2. Implement `GitHubClient` that wraps the `gh` CLI (following the pattern in `bridge_cli.py:944-977`)
3. Wire real clients into `claw_launcher.py` instead of mock stubs
4. Extend `handle_feature_brief` in `signal_dispatcher.py` to trigger the execution pipeline: fetch issues → score → plan sprint → queue for approval

### P1 — Process Supervision
5. Add a `FailoverManager` startup in `claw_launcher.py` that monitors heartbeats and can restart dead claws
6. Add graceful shutdown that calls `heartbeat.stop()`, `poller.stop()`, and `claw.shutdown()` before exit
7. Consider Docker restart policy or systemd unit for production deployment

### P2 — Generic Claw Activation
8. Wire up Content, Ops, Analytics, and Finance claw classes in `claw_launcher.py` (same pattern as Build Claw)
9. Add message handlers to `InboxPoller` for each generic claw role

### P3 — Message Delivery Reliability
10. Fix `signal_dispatcher._write_fallback_message` to write to `~/.milimo/mesh/inbox/{recipient}/` instead of the local `messages/` directory
11. Or better: have SignalDispatcher use `MeshCoordinator` for all message sending

### P4 — Bridge and Integration
12. Increase bridge timeout from 3 seconds to 10+ seconds for filesystem-scanning commands
13. Register bridge commands as proper OpenClaw tools instead of `spawnSync` subprocess calls
