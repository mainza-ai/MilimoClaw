# Milimo Claw — Production Readiness Plan

> **Date:** 2026-04-05
> **Status:** Audited — Gaps Identified
> **Next:** Implementation

---

## Audit Summary

The `claw_launcher.py` is a **functional prototype** with a solid foundation. The threading model, inbox polling, heartbeat emission, and graceful shutdown are all production-quality. However, the critical missing pieces are:

1. **Auto-restart** — HeartbeatMonitor only logs warnings; dead claws stay dead
2. **No result/outbox** — Messages go to `processed/` (dead end); claw results never return
3. **Mock clients** — `MockVercelClient`, `MockSentryClient`, `MockMeshGateway` are empty stubs
4. **No daemonization** — Launcher dies with the terminal session
5. **No crash recovery** — Thread dies silently with no supervisor

---

## Current Message Flow (Broken)

```
Bridge command → writes JSON to ~/.milimo/mesh/inbox/{role}/ →
InboxPoller picks it up → handle_inbound() →
ARCHIVED TO processed/ (dead end — no result returned)
```

---

## Phase 1: Process Supervision & Lifecycle
**Goal:** Claws that crash get restarted automatically. Launcher survives terminal closure.

| # | Change | File | Description |
|---|--------|------|-------------|
| 1.1 | Add `restart_claw()` to `HeartbeatMonitor` | `claw_launcher.py` | `_check_heartbeats()` restarts when heartbeat > 2× threshold (180s) |
| 1.2 | Add `--daemon` flag | `claw_launcher.py` | Background mode with PID file at `~/.milimo/launcher.pid` |
| 1.3 | Add `shutdown()` to all claw classes | `ops_claw.py`, `build_claw.py`, `content_claw.py`, `analytics_claw.py`, `finance_claw.py` | Stop schedulers, flush logs, close connections |
| 1.4 | Add restart tracking | `claw_launcher.py` | Track restarts per claw; log and alert on >3 restarts/hour |
| 1.5 | Add crash recovery loop | `claw_launcher.py` | If claw thread dies, restart with exponential backoff (1s, 2s, 4s, max 60s) |
| 1.6 | Add PID file management | `claw_launcher.py` | Prevent multiple launchers; support `--stop` and `--status` |
| 1.7 | Add `--supervise` flag | `claw_launcher.py` | Auto-restart launcher if it dies |

---

## Phase 2: Message Outbox
**Goal:** When a claw processes a message, the result flows back to the bridge.

| # | Change | File | Description |
|---|--------|------|-------------|
| 2.1 | Add `OutboxPoller` to launcher | `claw_launcher.py` | Watches `~/.milimo/mesh/outbox/{role}/` for result JSON |
| 2.2 | Add `_write_result()` to each claw | `ops_claw.py`, `build_claw.py`, etc. | Write result JSON to outbox after processing |
| 2.3 | Add `get_result(message_id)` to bridge | `bridge_cli.py` | Read from outbox, return to Lucy |
| 2.4 | Wire outbox to `send_to_claw` | `bridge_cli.py` | `send_to_claw` waits for result with 60s timeout |
| 2.5 | Add result TTL + cleanup | `claw_launcher.py` | Outbox messages expire after 1 hour |

---

## Phase 3: Real Client Integrations
**Goal:** Replace all mock clients with real implementations.

| # | Change | File | Description |
|---|--------|------|-------------|
| 3.1 | Implement `VercelClient` | `build/vercel_client.py` | Real Vercel API — deploy, rollback, status, deployment URLs |
| 3.2 | Implement `SentryClient` | `build/sentry_client.py` | Real Sentry API — error events, releases, sourcemaps |
| 3.3 | Wire real clients in launcher | `claw_launcher.py` | Use real clients when `VERCEL_API_TOKEN` / `SENTRY_AUTH_TOKEN` env vars present |
| 3.4 | Implement real `MeshGateway` for finance | `finance/finance_claw.py` | Replace `MockMeshGateway` — send/receive mesh messages |
| 3.5 | Add client health checks at startup | `claw_launcher.py` | Validate API credentials before declaring claw "running" |
| 3.6 | Add `gh CLI` availability check | `claw_launcher.py` | Verify `gh auth status` before starting Build claw |

---

## Phase 4: Bridge Lifecycle Commands
**Goal:** Lucy can manage claws from chat.

| # | Command | File | Description |
|---|---------|------|-------------|
| 4.1 | `bridge: start_claw(role)` | `bridge_cli.py` | Spawn `claw_launcher.py --role {role}` as subprocess |
| 4.2 | `bridge: stop_claw(role)` | `bridge_cli.py` | Send SIGTERM to launcher PID, clear heartbeat |
| 4.3 | `bridge: restart_claw(role)` | `bridge_cli.py` | Stop + start with 2s gap |
| 4.4 | `bridge: restart_all_claws()` | `bridge_cli.py` | Stop all, then start all |
| 4.5 | `bridge: claw_logs(role, lines)` | `bridge_cli.py` | `tail -n {lines} ~/.milimo/mesh/logs/{role}.log` |
| 4.6 | `bridge: launcher_status()` | `bridge_cli.py` | Check if launcher running, PID, uptime, restart count |
| 4.7 | `bridge: get_result(message_id)` | `bridge_cli.py` | Poll outbox for result with 30s timeout |

---

## Phase 5: Startup Validation & Health
**Goal:** Claws fail fast and loudly when misconfigured.

| # | Change | File | Description |
|---|--------|------|-------------|
| 5.1 | Add env var validation at startup | `claw_launcher.py` | Check required vars before starting; exit 1 with clear error if missing |
| 5.2 | Add startup health verification | `claw_launcher.py` | After 10s, verify heartbeat file exists; restart if not |
| 5.3 | Add HTTP `/health` endpoint | `claw_launcher.py` | `python3 -m http.server 8081` with JSON status for external monitoring |
| 5.4 | Add `--validate-only` flag | `claw_launcher.py` | Check all env vars and connections, report status, exit |
| 5.5 | Alert on silent degradation | `claw_launcher.py` | When falling back to heartbeat-only mode, write alert to `~/.milimo/mesh/alerts/` |
| 5.6 | Add startup summary to stdout | `claw_launcher.py` | Print all claws started, their PIDs, and health check URL |

---

## Phase 6: Execution Engine
**Goal:** Claws process tasks and return results, not just route files.

| # | Change | File | Description |
|---|--------|------|-------------|
| 6.1 | Add `OutboxWriter` to `BuildClaw` | `build_claw.py` | After code generation, write result with generated code diff and file paths |
| 6.2 | Add `OutboxWriter` to `OpsClaw` | `ops_claw.py` | After project setup or deadline escalation, write result with project ID |
| 6.3 | Add `OutboxWriter` to `FinanceClaw` | `finance_claw.py` | After invoice creation, write result with invoice ID and Stripe URL |
| 6.4 | Add `OutboxWriter` to `ContentClaw` | `content_claw.py` | After draft generation, write result with draft content and review URL |
| 6.5 | Add `OutboxWriter` to `AnalyticsClaw` | `analytics_claw.py` | After report generation, write result with report summary |
| 6.6 | Add result timeout to bridge | `bridge_cli.py` | `send_to_claw` waits up to 60s for result; returns "pending" if timeout |
| 6.7 | Add async result polling to Lucy docs | `LUCY_INSTRUCTIONS` | Lucy can poll `get_result()` for async task completion |

---

## Implementation Order

```
Phase 1 (Process Supervision) → Phase 2 (Outbox) → Phase 3 (Real Clients)
                                                              ↓
Phase 4 (Bridge Lifecycle) ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
                                                              ↓
Phase 5 (Validation & Health) → Phase 6 (Execution Engine)
```

**Rationale:** Phase 1 is the foundation — everything else depends on claws running and staying running. Phase 2 enables result flow. Phase 3 unblocks real work. Phase 4 gives Lucy control. Phase 5 prevents silent failures. Phase 6 enables autonomous operation.

---

## Files to Modify

### High Priority
- `milimo-blueprint/orchestrator/claw_launcher.py` — Process supervision, daemonization, PID management
- `milimo-blueprint/orchestrator/bridge_cli.py` — Lifecycle commands, outbox reading
- `milimo-blueprint/orchestrator/ops/ops_claw.py` — `shutdown()`, outbox writing
- `milimo-blueprint/orchestrator/build/build_claw.py` — `shutdown()`, outbox writing
- `milimo-blueprint/orchestrator/content/content_claw.py` — `shutdown()`, outbox writing
- `milimo-blueprint/orchestrator/analytics/analytics_claw.py` — `shutdown()`, outbox writing
- `milimo-blueprint/orchestrator/finance/finance_claw.py` — `shutdown()`, outbox writing, real MeshGateway

### Medium Priority
- `milimo-blueprint/orchestrator/build/vercel_client.py` — Implement real Vercel client
- `milimo-blueprint/orchestrator/build/sentry_client.py` — Implement real Sentry client
- `milimo-claw-docs/guides/LUCY_INSTRUCTIONS_NEW_CAPABILITIES.md` — Add lifecycle commands, async result polling

### Low Priority (Once all above are done)
- `milimo-claw-docs/guides/PRODUCTION_DEPLOYMENT.md` — Deployment guide for production setup
- `milimo-blueprint/orchestrator/health_collector.py` — External health endpoint wiring

---

## Success Criteria

- [ ] `claw_launcher.py --daemon` runs in background and survives terminal close
- [ ] Claw with stale heartbeat (>180s) is automatically restarted
- [ ] `bridge: start_claw(ops)` starts the Ops claw and Lucy can verify via `claw_status`
- [ ] `bridge: stop_claw(ops)` stops the Ops claw and its heartbeat file is removed
- [ ] `bridge: restart_claw(build)` restarts the Build claw
- [ ] After sending a task via `send_to_claw`, the result appears in the outbox within 60s
- [ ] `bridge: get_result(message_id)` returns the claw's result JSON
- [ ] Real `VercelClient` deploys to Vercel when `VERCEL_API_TOKEN` is set
- [ ] Real `SentryClient` reports errors when `SENTRY_AUTH_TOKEN` is set
- [ ] Missing env vars cause clear error at startup, not silent degradation
- [ ] HTTP `/health` on port 8081 returns JSON with all claw statuses
- [ ] All 5 claws can be started via bridge commands and process real work
