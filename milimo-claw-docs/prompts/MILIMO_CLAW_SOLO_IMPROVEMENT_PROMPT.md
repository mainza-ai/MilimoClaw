> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — SOLO TEMPLATE IMPROVEMENT PLAN IMPLEMENTATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
# Attach this prompt alongside:
#   1. SOLO_TEMPLATE_IMPROVEMENT_PLAN.md  (the gap analysis)
#   2. MILIMO_CLAW_SOLO_TEMPLATE_SPEC.md  (the ground truth spec)
#   3. solo-founder.yaml                  (the template config)
# Work through phases in strict order. Do not skip ahead.
# ─────────────────────────────────────────────────────────────────────────────

You are an expert TypeScript and Python engineer completing the Milimo Claw
solo founder template implementation. The improvement plan document is
attached and defines every gap. The spec document is the ground truth — if
code deviates from the spec, the code is wrong.

The platform is ~75% implemented. Your job is to close the remaining 25%,
working strictly in the phase order defined below.

---

## CONTEXT — WHAT YOU ARE WORKING WITH

**Product:** Milimo Claw — a multi-agent autonomous hustle platform built
as a plugin on NVIDIA NemoClaw. Six specialized AI agents (claws) run
24/7 inside isolated NemoClaw sandboxes, coordinating through the OpenShell
inter-sandbox gateway. A single operator manages all six from the War Room
dashboard.

**Plugin structure:**
  - TypeScript plugin:       milimo/src/
  - Python orchestrator:     milimo-blueprint/orchestrator/
  - Templates:               milimo-blueprint/templates/
  - Role blueprints:         milimo-blueprint/roles/
  - Sandbox policies:        milimo-blueprint/policies/
  - Operator config:         ~/.milimo/config.json (single source of truth)

**What already works (do not rewrite these):**
  - Blessed TUI split-pane layout with keyboard shortcuts
  - HOLD/REVIEW/AUTO/VETO approval engine with escalation
  - Evolution cycle 5-stage pipeline (observe/identify/propose/build/deploy)
  - Privacy router with locked routes and cost guard
  - All 15+ inter-claw message contracts in contracts.py
  - All 5 role blueprints and sandbox policies
  - Solo-founder.yaml template (complete)

**What is missing (your job):**
  - Revenue widget in War Room TUI
  - Morning brief / evening wrap automation
  - milimo squad finals-mode CLI command
  - Real health data collection
  - OpenShell gateway connection for inter-claw messaging
  - Message encryption
  - Inference-based tool generation in evolution cycle
  - Real backtesting in sandbox isolation
  - Production hardening items

**Operator:** Mainza Kangombe — senior systems architect and solo founder.
Experienced Python 3.11+ and TypeScript engineer. Write production-quality
code. No placeholder comments. No over-explanation of basics.

**Standards (non-negotiable):**
  - TypeScript: strict mode, full type annotations, no any
  - Python: 3.11+, full type hints, docstrings, pathlib.Path only
  - YAML: PyYAML safe_load only — never yaml.load()
  - Shell commands: child_process.spawn with array args only
  - Logging: structured, claw name as logger identifier
  - Error handling: never silently swallow exceptions — log and re-raise
    or return typed error results
  - Tests: pytest for Python, Jest for TypeScript

**Spec deviations to resolve before starting:**
  - Evolution time: use 02:00 Sunday (spec is ground truth)
  - Revenue Widget data source: add finance_summary to message contracts
  - Morning brief format: structured JSON digest rendered as a TUI panel
  - Cost guard token counting: use tiktoken; fall back to char/4 if unavailable
  - Health collection interval: 3-second polling (matches existing TUI)

---

## PHASE 1 — CRITICAL UX GAPS
## Complete all Phase 1 tasks before moving to Phase 2.

---

### TASK 1.1 — Revenue Widget in War Room TUI

**Files:** UPDATE warroom-tui.ts · UPDATE contracts.py · UPDATE solo_warroom.py

Add finance_summary message type to contracts.py:
  sender: finance, recipients: [war_room]
  payload: week_revenue (float), week_over_week_pct (float),
           invoices_paid (int), invoices_pending (int), last_updated (str)
  frequency: on_change, priority: AUTO

Add get_revenue_summary() to SoloWarRoom in solo_warroom.py:
  - Reads from /sandbox/finance/revenue/weekly_summary.json
  - Returns typed RevenueSummary dataclass
  - Returns zeroed summary if file does not exist
  - Calculates week-over-week % from current vs previous week total

Add revenue widget to right panel in warroom-tui.ts:
  - Calls Python bridge: callPythonBridge("revenue_summary", {})
  - Renders: week revenue amount, week-over-week % (teal=up, coral=down),
    invoices paid count, invoices pending count
  - Refreshes every 30 seconds independently of 3-second health poll
  - Shows "No revenue data yet" for new installs

Write Jest tests: widget rendering, bridge call, color coding logic.
Write pytest tests: normal data, missing file, zero values, week boundary.

---

### TASK 1.2 & 1.3 — Morning Brief and Evening Wrap Automation

**Files:** NEW milimo/src/warroom/digest.ts · UPDATE warroom-tui.ts
          UPDATE milimo-blueprint/orchestrator/solo_warroom.py

Python generate_morning_brief() and generate_evening_wrap() already exist.
Wire them to TypeScript via the Python bridge.

Implement DigestScheduler class in digest.ts:
  - start(config): schedules 07:00 and 20:00 daily using setTimeout
    with recalculated delay to next occurrence — no cron, no new deps
  - stop(): clears both timers
  - getMorningBrief(): calls callPythonBridge("morning_brief", {})
    returns DigestBrief with: overnight_actions, queue_summary,
    evolution_updates (Sundays only), alerts
  - getEveningWrap(): calls callPythonBridge("evening_wrap", {})
    returns DigestBrief with: today_completed, queued_for_tomorrow,
    claw_health_summary
  - renderBrief(brief, panel): renders into blessed box element

Update warroom-tui.ts:
  - Initialize DigestScheduler on startup
  - Add D keyboard shortcut to toggle digest panel
  - Show notification indicator dot when new brief is available
  - Add D to help overlay

Write Jest tests: scheduler timing, brief rendering, panel toggle.
Write pytest tests: morning_brief bridge command, evening_wrap bridge command,
empty log handling, Sunday evolution inclusion.

---

### TASK 1.4 — Deep Work Mode CLI Command

**Files:** NEW milimo/src/commands/finals-mode.ts · UPDATE milimo/src/cli.ts
          UPDATE milimo-blueprint/orchestrator/solo_deep_work.py
          UPDATE milimo/src/onboard/config.ts

Python activate_deep_work and resume_deep_work already exist in
solo_deep_work.py. Wire them to CLI commands.

Register two commands under squad namespace:

  milimo squad finals-mode [--duration <2weeks|3days>] [--resume-date YYYY-MM-DD]
    - Validate: at least one option required
    - Calculate resume date from duration if not provided directly
    - Call bridge: activate_deep_work with resume_date ISO string
    - Print per-claw policy change summary (Content/Ops/Analytics/Finance/Build/Assistant)
    - Print: "Deep Work Mode active. Resume scheduled: {date}"
    - Write deep_work state to config: { active, activated_at, resume_date }

  milimo squad finals-resume
    - Error if deep_work not active in config
    - Call bridge: resume_deep_work
    - Print per-claw policy restoration summary
    - Print: "Deep Work Mode deactivated. All claws resuming."
    - Clear deep_work from config

Add deep_work field to MilimoConfig:
  deep_work?: { active: boolean; activated_at: string; resume_date: string }

Write Jest tests: duration parsing, resume date calc, config state,
already-active error, not-active error on resume.
Write pytest tests: activate, resume, auto-response substitution, rollback.

---

### TASK 1.5 — Real Health Data Collection

**Files:** NEW milimo/src/warroom/health-collector.ts
          UPDATE milimo-blueprint/orchestrator/health_collector.py

Current health panel reads from static file. Replace with live data.

Implement HealthCollector class in health-collector.ts:
  - collectAll(): calls callPythonBridge("collect_health", {})
    returns ClawHealthMap keyed by role
  - startPolling(onUpdate, onError): polls at 3000ms interval
    calls onUpdate with fresh ClawHealthMap each cycle
    calls onError on bridge failure — does NOT stop polling
    returns cleanup function that stops the interval
  - deriveStatus(health): active if last_action within 60s,
    processing if pending HOLD/REVIEW action, idle otherwise

ClawHealth interface:
  role, status, tool_count, last_evolution (ISO|null),
  last_action (ISO|null), actions_this_week, sparkline (7 ints)

Update health_collector.py to implement collect_health bridge command:
  - Read action timestamps from ~/.milimo/logs/warroom.log
  - Read tool counts and evolution timestamps from tool registry files
  - Calculate 7-day sparkline from operational log files
  - Handle missing files gracefully — return zeros not errors

Write Jest tests: status derivation, polling lifecycle, error resilience.
Write pytest tests: output structure, sparkline calculation, missing logs.

---

## PHASE 2 — GATEWAY INTEGRATION
## Complete all Phase 1 tasks before starting Phase 2.

---

### TASK 2.1 — OpenShell Gateway Connection

**Files:** NEW milimo/src/mesh/gateway-client.ts · UPDATE mesh.py

Implement GatewayClient class in gateway-client.ts:
  - connect(): Unix socket to /var/run/openshell/gateway.sock (Linux)
    or /tmp/openshell-gateway.sock (macOS fallback)
    retry with exponential backoff: 1s, 2s, 4s, max 30s
  - send(message): encrypt, send, await ack — 5s timeout
    throws GatewayDeliveryError on timeout
  - onMessage(handler): register handler for incoming messages
  - disconnect(): clean shutdown
  - isConnected(): boolean
  - getFallbackMode(): boolean — true when using file queues

Update mesh.py:
  - Check for gateway socket at startup
  - Use GatewayAdapter if socket exists
  - Log warning and use file-based fallback if not
  - Never crash — always deliver via best available transport

Write Jest tests: connect/disconnect, message send with ack, fallback
activation, retry backoff behavior.
Write pytest tests: gateway routing, fallback detection, pre-send validation.

---

### TASK 2.2 — Message Encryption

**Files:** NEW milimo/src/mesh/message-encryption.ts
          NEW milimo-blueprint/orchestrator/mesh_encryption.py

Algorithm: AES-256-GCM using Node.js built-in crypto / Python cryptography lib.
Key source: meshSecret from config. Key derivation: PBKDF2 with claw-pair salt.
Each message gets a unique IV — never reuse.
Include message timestamp in AAD to prevent replay attacks.

TypeScript MessageEncryption class: encrypt(message) / decrypt(encrypted)
Python MessageEncryption class: encrypt(message) / decrypt(encrypted)
Must be interoperable: TS-encrypted messages decryptable in Python.

Write cross-language test with known plaintext, key, IV, and expected
ciphertext. Both directions must pass.

---

### TASK 2.3 — WebSocket Adapter for Real-Time War Room Updates

**Files:** NEW milimo/src/warroom/realtime-bridge.ts
          UPDATE warroom-tui.ts · UPDATE solo_warroom.py

Implement RealtimeBridge WebSocket server on localhost:9876:
  - start() / stop()
  - onAction(handler): fires when any claw queues new action
  - onHealthUpdate(handler): fires on claw status change
  - onEvolutionEvent(handler): fires on evolution stage completion

Update solo_warroom.py to connect to WebSocket and emit events for:
  - New action queued (any mode)
  - Claw status change (active/idle/processing)
  - Evolution cycle stage completion

Update warroom-tui.ts to use event-driven updates from RealtimeBridge
instead of polling for queue and health. Keep 30-second polling for
revenue widget only.

---

### TASK 2.4 — Operator Notification Delivery

**Files:** NEW milimo/src/warroom/notifier.ts · UPDATE approval.ts
          NEW milimo/src/commands/action.ts · UPDATE cli.ts

OperatorNotifier class — system notification when TUI is closed:
  - macOS: osascript (no new deps)
  - Linux: notify-send (no new deps)
  - Fallback: write to ~/.milimo/notifications/pending.json
  - notify(action): HOLD items only
    Format: "🦀 WAR ROOM — {CLAW} | {action summary}"
  - notifyHoldRelease(actionId): confirmation after HOLD released

Register two CLI commands:
  milimo action approve <action_id>
  milimo action block <action_id>
Both work without opening TUI. Read pending queue from file,
update decision, trigger downstream execution.

---

## PHASE 3 — EVOLUTION ENHANCEMENT
## Complete all Phase 2 tasks before starting Phase 3.

---

### TASK 3.1 — Inference-Based Tool Generation

**Update:** milimo-blueprint/orchestrator/tool_builder.py

Replace skeleton code generation with inference-based generation.
All tool generation routes to local/cloud NIM via privacy router
(data_type="source_code" — local/cloud).

_generate_tool_code(proposal, operational_data) -> str:
  - Build structured prompt from: tool purpose, target metric,
    data sources available, permission constraints,
    expected input/output interface, sample operational data
  - Call privacy_router.route_inference(data_type="source_code", ...)
  - Extract code block from response
  - Validate Python syntax before returning

Generated tool requirements:
  - Accepts standard ToolInput interface
  - Returns standard ToolOutput interface
  - Includes error handling
  - Is importable as Python module
  - Passes syntax validation before backtesting

Write pytest tests: prompt construction, code extraction, syntax
validation, privacy enforcement (source_code must use local NIM).

---

### TASK 3.2 — Real Backtesting in Sandbox Isolation

**Files:** NEW milimo-blueprint/orchestrator/evolution/sandbox_runner.py
          UPDATE tool_builder.py

SandboxRunner class:
  backtest(tool_code, historical_data, target_metric, baseline_value)
    -> BacktestResult (improvement_pct, sample_outputs, error_rate, runtime_ms)

Isolation requirements:
  - Runs in subprocess with restricted builtins
  - No network access during backtest
  - Read-only access to historical data snapshot
  - 30-second timeout — kill if exceeded
  - 256MB memory limit via resource module
  - Allowed imports only: json, datetime, statistics, math, re
  - Blocked: requests, subprocess, os.system, eval, exec

_meets_threshold(result, threshold_pct=5.0) -> bool:
  Returns True if improvement_pct >= threshold_pct

Update tool_builder.py: use SandboxRunner.backtest() instead of
simulated backtest. Only deploy tools that pass _meets_threshold.

Write pytest tests: successful validation, threshold failure discard,
timeout enforcement, blocked import rejection, memory limit, 4-week window.

---

### TASK 3.3 — Tool Provenance Signing

**Update:** milimo-blueprint/orchestrator/tool_registry.py

ToolProvenance dataclass fields:
  tool_id, claw_role, generated_at, generation_model, trigger_pattern,
  backtest_result, deployed_at, signature (Ed25519), signer_key_id

Sign on deploy using squad private key from provenance-keygen.
Verify signature on every tool load at startup.
Refuse to load tools with invalid signatures — log and skip (do not crash).

---

### TASK 3.4 — Automatic Rollback on Regression

**Update:** milimo-blueprint/orchestrator/tool_registry.py

check_for_regression(tool_id, current_metric_value) -> RollbackDecision:
  - Monitor target metric for 7 days post-deploy
  - If metric < baseline * 0.95: deactivate tool
  - Restore previous behavior
  - Log rollback event to War Room evolution log
  - Never auto-remove — keep in registry with 'rolled_back' status

---

## PHASE 4 — PRODUCTION HARDENING
## Complete all Phase 3 tasks before starting Phase 4.

---

### TASK 4.1 — Audit Log Rotation and Search

**Update:** milimo/src/warroom/audit.ts

  - Rotate warroom.log daily at midnight
  - 90-day retention (configurable in solo-founder.yaml)
  - Compress rotated logs with gzip (Node.js built-in zlib — no deps)
  - NEW command: milimo logs search --query <text> --from <date> --to <date>
    searches across rotated and current logs

---

### TASK 4.2 — Filesystem Mount Automation

**Update:** milimo-blueprint/orchestrator/solo_init.py

  - If running with sufficient permissions: use /sandbox/{role}
  - If not: create under ~/.milimo/sandboxes/{role}/ and configure
    NemoClaw to use these as sandbox filesystem roots
  - Auto-detect during milimo init, use best available path
  - Print clear summary of which paths are in use and why

---

### TASK 4.3 — Stripe Integration for PRO Tier

**Update:** milimo/src/commands/payment.ts · UPDATE rate-limiter.ts

Replace localhost:3001 default:
  const API_BASE = process.env.MILIMO_SERVER_URL ?? config.serverUrl
    ?? "https://api.milimoclaw.com";

Add Stripe webhook handler:
  customer.subscription.created → upgrade to PRO in config
  customer.subscription.deleted → downgrade to FREE in config
  invoice.payment_failed → War Room alert notification

Update rate-limiter.ts:
  - Verify PRO tier from config before lifting limits
  - Cache tier status with 1-hour TTL — do not call Stripe on every action

---

## VERIFICATION CHECKLIST

After completing all phases, confirm every item passes:

□ Revenue widget shows week revenue, invoices paid/pending, WoW change
□ Morning brief appears at 07:00 without manual trigger
□ Evening wrap appears at 20:00 without manual trigger
□ milimo squad finals-mode --duration 2weeks activates Deep Work Mode
□ milimo squad finals-resume restores all policies correctly
□ Health panel updates every 3 seconds with real data
□ D keyboard shortcut toggles digest panel in War Room TUI
□ Inter-claw messages route through OpenShell gateway when available
□ File queue fallback activates with warning when gateway unavailable
□ AES-256-GCM messages interoperable between TypeScript and Python
□ War Room queue updates instantly on new claw action (event-driven)
□ HOLD items trigger system notification when TUI is closed
□ milimo action approve <id> and milimo action block <id> work from CLI
□ Evolution generates real tool code via local NIM — not skeletons
□ Generated tools backtested against 4 weeks of historical data
□ Blocked imports (requests, subprocess, os.system) rejected in backtest
□ Tools regressing below baseline are auto-deactivated within 7 days
□ Deployed tools have Ed25519 provenance signatures
□ Invalid signatures refuse to load at startup (log and skip)
□ Audit logs rotate daily, 90-day retention, gzip compressed
□ milimo logs search returns results across rotated and current logs
□ payment.ts uses production API URL from env or config
□ Rate limiter verifies PRO tier with 1-hour cache TTL
□ npm test passes in milimo/
□ pytest passes in milimo-blueprint/
□ openclaw milimo --help shows all commands including finals-mode,
  finals-resume, action approve, action block, logs search

---

## OUTPUT FORMAT

For each task:

  --- TASK N.N: [Title] ---
  Files: [exact paths — NEW or UPDATE]
  Summary: [one sentence]

  [complete implementation — no TODOs, no stubs, no placeholders]

  Tests: [complete test file immediately after implementation]
  -----------------------------------------

Begin with Task 1.1. Do not proceed to 1.2 until 1.1 is complete with tests.
The spec document is the ground truth. If this prompt conflicts with the
spec, the spec wins.
