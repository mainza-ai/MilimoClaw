# Production Spend Flow Fix Plan — 2026-07-06

**Pages**: [[spend-handler]], [[finance-claw]], [[hermes-profile]], [[link-cli-setup]], [[war-room]], [[troubleshooting/spend-flow-auth-failures]]

**Last updated**: 2026-07-06

**Tags**: #development #finance #spend #production #plan #link-cli #hermes #prompt-engineering

---

## 1. What Triggered This Plan

### 1.1 Live Session Reproduction

Operator triggered the Finance Claw spend-flow demo in a rebuilt sandbox (post-`main` merge `7b9fb90`). Agent exhibited the following behavior instead of completing the flow:

- Spent 60+ tool calls on filesystem exploration: reading `finance_claw.py` source, grepping for `spend|finance|link-cli`, walking `~/.linkcli`, `~/.config/linkcli`, `/sandbox/.linkcli`, searching for `*.token` and `*.key`
- Made 60-second blocking calls (`link-cli auth status --interval 5 --max-attempts 60`) that timed out and were killed by process guard
- Eventually received the `approval_url` from `_check_link_cli_auth`, but did **not** surface it verbatim — instead emitted a generic paraphrase requiring the operator to request the URL explicitly
- Only reached the auth check after exhausting filesystem exploration, adding 5+ minutes of latency before any progress

### 1.2 What Changed Since `e5a1da8` (Last Known Working)

The working `e5a1da8` commit had the Finance Claw spend-flow instructions baked directly into `SOUL.md` via Dockerfile heredoc. Between then and `HEAD`, three things changed:

| What changed | Working (`e5a1da8`) | Broken (`HEAD`) |
|---|---|---|
| `SOUL.md` location | Dockerfile heredoc with full "Finance Claw Spend Flow" section (5 steps + HARD RULE + payment-method discovery) | Tracked `agent_config/SOUL.md` with no spend-flow instructions |
| `HERMES_ENVIRONMENT_HINT` phrasing | `CRITICAL: When milimo_spend returns approval_url, always output the full URL verbatim...` | `Global rule: surf ace approval requirements verbatim...` (note typo `surf ace`) |
| `_validate_justification` | Always validates ≥100 chars | Skips validation when `test_mode=True` |

This plan addresses the **root cause class** (prompt/context starvation of the main Hermes agent), not just the symptom. The agent has no operational context for spend flow regardless of which prompt layer it reads from.

---

## 2. Root Cause Analysis

All six root causes are prompt/context-layer issues, not code bugs in the spend handler itself.

### R-1 · `SOUL.md` Contains No Spend-Flow Instructions

The main Hermes agent reads `SOUL.md` as its system prompt. In the working commit, `SOUL.md` had:

```
## Registered Tools
- milimo_spend: Finance Claw agent-initiated spend flow ... Always use --test flag in test mode.

## Finance Claw Spend Flow
1. Call milimo_spend with action=queue_review ...
2. HARD RULE: If _check_link_cli_auth returns an approval_url, you MUST include
   the full URL verbatim ... STOP and WAIT for operator confirmation.
3. After operator confirms approval, rerun the auth check ...
4. The spend flow runs in test mode by default ...
5. Payment method ID is obtained via: link-cli payment-methods list --format json
```

The current `agent_config/SOUL.md` has none of this. The agent sees `milimo_spend` as a tool name but has no guidance on:
- What parameters are required
- That `payment_method_id` must be discovered via `link-cli payment-methods list --format json`
- The two-stage gate sequence (`queue_review → approve_review → release_hold`)
- How to handle the `approval_url` response (surf verbatim + halt)
- Test-mode semantics (`--test` flag presence)
- Expected output format

**Without these instructions, the agent has no way to synthesize the flow from bare tool definitions.** It falls back to filesystem exploration because it has nothing else to act on.

### R-2 · Finance Domain Context Is Scoped Only to `delegate_task` Paths

`milimo-hermes-plugin/delegation.py` `CLAW_CONTEXTS["finance"]` contains the strict 8-rule Finance Claw protocol. But `CLAW_CONTEXTS` is only injected when the agent calls `delegate_task`.

For spend-flow demos and direct operator requests, the main Hermes agent calls `milimo_spend` directly (or shells out to `link-cli`). It never enters `delegate_task`. Therefore, it never sees `CLAW_CONTEXTS["finance"]`.

This is structural: the domain rules (no self-navigation, tool-first, test-mode default, justification length) exist in a context that is unreachable from the primary invocation path.

### R-3 · `HERMES_ENVIRONMENT_HINT` Is Malformed and Underweighted

The environment hint is the highest-priority context the Hermes agent receives at session start. The current value:

```
...Global rule: surf ace approval requirements verbatim and wait for operator
confirmation. Do not navigate to private/internal addresses...
```

Two problems:
- **Typo**: `surf ace` (should be `surface`). LLMs weight malformed text lower.
- **Phrasing**: "Global rule: surface approval requirements verbatim" is generic. The working version said: `CRITICAL: When milimo_spend or _check_link_cli_auth returns an approval_url, always output the full URL verbatim to the operator. Do not paraphrase, omit, or replace it with a generic statement. The operator cannot approve without the exact URL. Wait for operator confirmation before proceeding.`

The working version repeated the rule with `CRITICAL:` emphasis and tied it to the specific tool names (`milimo_spend`, `_check_link_cli_auth`). The current version omits the tool names entirely.

### R-4 · Agent Output Was Paraphrased, Not Verbatim

When `_check_link_cli_auth` returns:
```json
{"error": "link_cli_not_authenticated", "approval_url": "https://app.link.com/device/setup?code=..."}
```

The working behavior: agent emitted `https://app.link.com/device/setup?code=...` verbatim as plain text and halted.

The broken behavior: agent emitted `"Open this URL and approve the device code in your Link app: [URL]"` — the URL was present but wrapped, and the agent did not halt cleanly because it was already deep in filesystem exploration. The operator had to explicitly request the raw URL.

### R-5 · `_validate_justification` Silently Bypasses QA in Test Mode

```python
def _validate_justification(request: SpendRequest, test_mode: bool = False) -> None:
    if test_mode:
        return                      # ← bypasses ≥100-char check
    if len(request.justification) < _LINK_CLI_MIN_CONTEXT_LENGTH:
        raise ValueError(...)
```

`MILIMO_SPEND_TEST_MODE=true` is the default. An operator providing a 20-character justification in a real purchase request (not a demo) silently passes validation. Test mode should skip the real charge (`link-cli spend-request create --test` already handles that). It must NOT skip the QA gate.

This is a production-correctness regression: test-mode semantics were conflated with "skip validation."

### R-6 · Agent Has No Guidance on Parameter Discovery or Mid-Flow Gaps

In production, an operator might say:
- "Pay Stripe $49" — `merchant_name`, `merchant_url`, `amount_cents` inferable; `payment_method_id` not present
- "Use my usual card" — requires `link-cli payment-methods list --format json` first
- "Buy it" — short justification, needs to be rejected or expanded

The agent has no instructions for:
- How to discover `payment_method_id` (which command, what JSON path)
- When to ask the operator vs. derive from context
- How to handle missing `merchant_url` (derive from name, or ask)

---

## 3. Production Scenario Inventory

A production-grade system must handle all of these without filesystem exploration:

| Scenario | Input | Expected agent behavior |
|---|---|---|
| A | "Pay Stripe invoice $49 for API credits" (no auth) | discover payment methods → hit auth check → surface approval_url verbatim → halt |
| B | "Pay Stripe invoice $49 for API credits" (authenticated, no payment method specified) | auto-discover `payment_method_id` → call `queue_review` with `--test` → return structured JSON |
| C | "Use my regular card" | call `link-cli payment-methods list --format json`, select default, populate `payment_method_id` |
| D | "Just buy it, I don't care" | refuse to queue; return structured error requiring ≥100 chars justification |
| E | Auth expires mid-flow | re-check auth → surface new URL → halt |
| F | `link-cli auth status` timeout | surface structured error; do not retry in background |
| G | No payment methods in Link app | tell operator to add one; do not silently fail |
| H | Operator says "approve it" after seeing approval_url | re-check auth → proceed to `approve_review` → `release_hold` → return `lsrq_id` |

---

## 4. Fix Plan

### Fix 1 · Expand `CLAW_CONTEXTS["finance"]` Into Complete Production Playbook

**File**: `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py`

**Current content** (~50 lines): 8 strict rules + 5-line tool inventory + truncated flow sequence. Does not cover parameter discovery, error recovery, or output format.

**New content** (~180 lines): Structured production playbook.

```
[IDENTITY]
You are the Finance Claw — treasury function of the squad.

[INTENT RECOGNITION]
Treat ANY operator request involving payment, purchase, invoice payment,
SaaS provisioning, API credit purchase, subscription, or "charge my card"
as a spend flow. Route to milimo_spend. Do NOT explore the filesystem,
walk directories, or open source files to understand how tools work.
Filesystem exploration wastes turns and produces no progress.

[REQUIRED PARAMETERS — derive or ask, do not fabricate]
  merchant_name   : always required — derive from operator's request or ask
  merchant_url    : if operator provides only a name, derive from name
                    (e.g., "Vercel" → "https://vercel.com") or ask
  amount_cents    : always required (integer cents, not dollars)
  justification   : >= 100 characters — generate one coherent sentence
                    if the operator does not provide sufficient detail;
                    ask for more detail before calling milimo_spend
  payment_method_id: REQUIRED — never call queue_review without this.
                     Obtain via: link-cli payment-methods list --format json
                     Select the most recently used default, or ask operator
                     if multiple methods exist and the request is ambiguous
  credential_type : "card" (default) or "shared_payment_token"
  claw            : "finance"

[CORRECT CALL SEQUENCE — DO NOT SKIP STEPS]
  Step A (if payment_method_id missing):
    Call: link-cli payment-methods list --format json
    Read payment_methods[0].id (or ask operator if ambiguous)
  Step B (if link-cli auth unknown):
    Call: link-cli auth status
    If not authenticated:
      • Surface exact approval_url verbatim to operator
      • STOP. WAIT for operator confirmation.
  Step C:
    Call: milimo_spend action=queue_review --test
          claw=finance merchant_name=... merchant_url=...
          amount_cents=... justification="..." payment_method_id=...
          credential_type=card
  Step D (after operator approves in War Room or via explicit message):
    Call: milimo_spend action=approve_review spend_id=...
  Step E:
    Call: milimo_spend action=release_hold spend_id=...
         (handler appends --test automatically in test mode)

[MANDATORY OUTPUT FORMAT — include ALL applicable fields]
  {
    "stage": "review" | "hold" | "released" | "blocked",
    "spend_id": "...",
    "action_id": "...",
    "status": "...",
    "hold_action_id": "...",       // present after approve_review
    "lsrq_id": "...",               // present after release_hold
    "approval_url": "https://...",  // present only if auth required
    "test_mode": true,
    "full_payload": { ... },
    "next_step": "Surface approval_url to operator" | "Awaiting War Room approval" | ...
  }

[ERROR RECOVERY]
  Auth timeout (60s)         → surface URL, halt; do not retry link-cli auth automatically
  No payment method          → call payment-methods list; if empty, tell operator to add one in Link app
  Short justification        → refuse to queue; ask operator for >= 100 chars
  approval_url returned      → NEVER paraphrase, NEVER self-navigate, STOP and WAIT
  link-cli returns UNKNOWN   → check proxy env vars (NODE_USE_ENV_PROXY=1); surface error to operator
  Daily spend cap exceeded   → auto-blocked; surface cap and remaining budget
  Duplicate release_hold     → idempotent — returns existing lsrq_id

[HARD RULES]
  1. TOOL-FIRST — call registered tools (milimo_spend), do not explore filesystem
  2. APPROVAL URL — emit exact URL as plain string, no wrapping, no markdown, no paraphrasing
  3. NO SELF-NAVIGATION — must not open, visit, navigate, click, or "go to" approval_url
  4. STOP AND WAIT — after surfacing URL, halt all tool calls; wait for operator confirmation
  5. TEST MODE DEFAULT — --test always present in test mode (MILIMO_SPEND_TEST_MODE=true)
  6. LINK-CLI PATH — /usr/local/bin/link-cli (pinned @ 0.8.2 in Dockerfile)
  7. NO CLOUD FOR FINANCE — financial inference routes to local NIM only
  8. PARAMETER COMPLETENESS — never call queue_review without payment_method_id
```

**Approval required**: yes — this changes the authoritative Finance Claw operational context. Confirm length and wording before implementation.

---

### Fix 2 · Make `CLAW_CONTEXTS["finance"]` Reachable from Main Agent (Structural)

**Problem**: `CLAW_CONTEXTS` is only injected during `delegate_task`. The main agent never sees it.

**Option A (preferred — low-friction)**: When the main agent invokes `milimo_spend`, prepend `CLAW_CONTEXTS["finance"]` to the tool's return context so the agent sees the rules alongside the result.

**Option B (strict separation)**: The main agent uses `delegate_task[claw=finance]` for all spend work. This automatically injects `CLAW_CONTEXTS["finance"]` but adds delegation overhead.

**Recommendation**: Option A. The user's constraint is "Finance domain logic lives in Finance Claw's context, not in SOUL.md" — Option A satisfies this while keeping the direct-invocation model.

---

### Fix 3 · Replace `agent_config/SOUL.md` With Generic Pointer (Remove Script)

**Problem**: If Fix 1 is approved, SOUL.md must not duplicate or contradict the Money Claw's authoritative context.

**Action**: Rewrite `agent_config/SOUL.md` to contain only:
- Generic Hermes identity
- Tool inventory (names + one-line purpose)
- Pointer: "Finance Claw operational rules (parameter requirements, sequence, error handling, output format) are enforced by `CLAW_CONTEXTS['finance']` when the Finance Claw skill is active. Do not inline spend instructions here."

---

### Fix 4 · Fix `HERMES_ENVIRONMENT_HINT` Typo + Strengthen Finance Routing

**File**: `milimo-hermes-sandbox/Dockerfile`

**Current**:
```
...Global rule: surf ace approval requirements verbatim and wait for operator
confirmation. Do not navigate to private/internal addresses...
```

**New**:
```
...CRITICAL: When milimo_spend or _check_link_cli_auth returns an approval_url,
always output the full URL verbatim to the operator. Do not paraphrase, omit,
or replace it with a generic statement. The operator cannot approve without the
exact URL. Wait for operator confirmation before proceeding. Finance spend
flows are governed by the Finance Claw operational context (CLAW_CONTEXTS).
Work within sandbox boundary.
```

---

### Fix 5 · Remove Silent Bypass in `_validate_justification`

**File**: `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/spend_handler.py`

**Current**:
```python
def _validate_justification(request: SpendRequest, test_mode: bool = False) -> None:
    if test_mode:
        return
    if len(request.justification) < _LINK_CLI_MIN_CONTEXT_LENGTH:
        raise ValueError(...)
```

**New**:
```python
def _validate_justification(request: SpendRequest) -> None:
    if len(request.justification) < _LINK_CLI_MIN_CONTEXT_LENGTH:
        raise ValueError(...)
```

`test_mode` controls `--test` flag injection in `cmd_create` (already correct). It must NOT bypass QA.

---

### Fix 6 · Add Parameter-Gap Auto-Discovery in `handle_milimo_spend`

**File**: `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py`

**Current**: Returns hard error when `payment_method_id` is missing.

**New behavior**: If action is `queue_review` and `payment_method_id` is missing:
1. Run `link-cli payment-methods list --format json` via subprocess
2. Parse JSON array, select first/default method
3. If empty, return `{"error": "no_payment_method", "action_required": "Add a payment method in your Link app"}`
4. Never proceed to `handler.queue_spend_review` without `payment_method_id`

---

### Fix 7 · Enforce Structured Output Schema in `handle_milimo_spend`

**File**: `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py`

Every action branch must return a dict with at minimum:
```python
{"action", "spend_id", "status", "stage", "test_mode"}
```
When `approval_url` is present, it must be a top-level key. This gives the agent a consistent response schema for formatting operator-facing output.

---

### Fix 8 · Inject Finance Claw Context at Plugin Registration

**File**: `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/__init__.py`

When `register_finance_claw` is called, inject `CLAW_CONTEXTS["finance"]` into the Finance Claw's startup system prompt so the operational context is loaded at init, not only during delegation.

This ensures Finance Claw has its full playbook even when running standalone (not via `delegate_task`).

---

## 5. Files to Modify

| File | Fixes |
|---|---|
| `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py` | Fix 1 (expand `CLAW_CONTEXTS["finance"]`), Fix 2 (context injection path) |
| `milimo-hermes-sandbox/agent_config/SOUL.md` | Fix 3 (generic pointer only) |
| `milimo-hermes-sandbox/Dockerfile` | Fix 4 (HERMES_ENVIRONMENT_HINT) |
| `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/spend_handler.py` | Fix 5 (remove test_mode bypass) |
| `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py` | Fix 6 (parameter gap handling), Fix 7 (structured output) |
| `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/__init__.py` | Fix 8 (context injection hook) |

All changes mirrored to root `milimo-hermes-plugin/` copy.

---

## 6. Verification — Production Scenarios

After rebuild, walk through all 8 scenarios from §3. Pass criteria for each:

| # | Scenario | Pass criterion |
|---|---|---|
| A | No auth | Agent surfaces `approval_url` verbatim, halts within 2 tool calls, no filesystem exploration |
| B | Authenticated, no payment method | Agent calls `link-cli payment-methods list --format json`, selects default, calls `queue_review` with `--test` |
| C | "Use my regular card" | Agent lists methods, asks if ambiguous |
| D | Short justification | Agent returns structured error; no silent bypass |
| E | Auth expires mid-flow | Agent re-checks auth, surfaces new URL |
| F | Auth timeout | Structured error returned, no background retry |
| G | No payment methods in app | Tells operator to add one |
| H | Operator confirms approval | Agent proceeds through `approve_review` → `release_hold` → returns `lsrq_id` |

**Negative test**: Agent must NOT read `spend_handler.py`, `finance_claw.py`, or any source file during any scenario.

---

## 7. Rollback Notes

If any fix causes regressions:

1. **Fix 1 (CLAW_CONTEXTS)**: Rollback to 50-line version. Production correctness is preserved by SOUL.md pointer + HERMES_ENVIRONMENT_HINT, but agent loses full production playbook.
2. **Fix 5 (test_mode bypass)**: If this breaks existing tests, check whether tests were relying on the bypass. Fix the tests; do not restore the bypass.
3. **Fix 6 (auto-discovery)**: If auto-selection is unsafe, add an explicit `ask_operator: true` branch instead of silent selection.

---

## 8. Open Questions (Awaiting Approval Before Implementation)

1. **`CLAW_CONTEXTS["finance"]` length**: Current ~50 lines → expanded ~180 lines. Acceptable?
2. **Auto-discovery of `payment_method_id`**: Fix 6 silently selects the first/primary method. Safe for production, or should the agent always ask "which card?"
3. **`assistant_system_prompt.md`**: It contains a Finance Claw section. Should it also be updated to point to the skill (not contain instructions), or is its current content acceptable?
4. **Fix 2 implementation path**: Option A (context injection in tool return) or Option B (force `delegate_task` for all spend work)?

---

## 9. Implementation Status — 2026-07-06

All fixes implemented and mirrored to root copies. Awaiting rebuild + live retest.

| Fix | File | Status |
|-----|------|--------|
| Fix 1: Expand `CLAW_CONTEXTS["finance"]` | `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py` | ✅ Implemented |
| Fix 2: `get_finance_context()` classmethod | same file | ✅ Implemented |
| Fix 3: Rewrite SOUL.md as generic pointer | `milimo-hermes-sandbox/agent_config/SOUL.md` | ✅ Implemented |
| Fix 4: HERMES_ENVIRONMENT_HINT typo + CRITICAL phrasing | `milimo-hermes-sandbox/Dockerfile`, root `Dockerfile` | ✅ Implemented |
| Fix 5: Remove `test_mode` bypass in `_validate_justification` | `milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/spend_handler.py`, root `milimo-core/...` | ✅ Implemented |
| Fix 6: Auto-discover `payment_method_id` | `milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/tools.py` | ✅ Implemented |
| Fix 7: Structured output schema | same file | ✅ Implemented |
| Fix 8: Context injection at registration | Satisfied by Fix 2 (`_FINANCE_CONTEXT` import in `tools.py`) | ✅ Implemented |

### Key implementation details

- `tools.py` adds `_FINANCE_CONTEXT = HermesDelegateAdapter.get_finance_context()` at module load
- `_discover_payment_method_id()` calls `link-cli payment-methods list --format json` and returns first/default ID or structured error
- `_format_spend_response()` normalizes all spend tool responses with consistent schema; injects `_finance_context` on first queue_review
- All return paths in `handle_milimo_spend` now use `_format_spend_response(...)`
- `queue_review` auto-discovers `payment_method_id` when missing; only errors if `link-cli` is unavailable or no methods exist
