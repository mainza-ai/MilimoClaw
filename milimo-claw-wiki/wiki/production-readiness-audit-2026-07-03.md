# Production-Readiness Audit — 2026-07-03

**Summary**: Line-level code audit verified against HEAD, cross-referenced against WARROOM_PRODUCTION_READINESS.md. Documents all open findings and the two-phase implementation plan.

**Sources**: `WARROOM_PRODUCTION_READINESS.md`, `milimo-core/`, `milimo-hermes-plugin/warroom/`, `milimo-blueprint/`

**Last updated**: 2026-07-04

**Tags**: #security #audit #implementation-plan

---

## Scope

All MilimoClaw modules verified (`milimo-core`, `milimo-hermes-plugin/warroom`, `milimo-blueprint`) against the production-readiness checklist.

## Verified Prior Fixes (Already in Code)

| ID | Finding | File | Status |
|----|---------|------|--------|
| SA3-1 | Spend idempotency lock | spend_handler.py | ✓ Fixed |
| SA3-2 | Daily aggregate spend cap | spend_handler.py | ✓ Fixed |
| SA3-3 | decisions.log fsync | spend_handler.py | ✓ Fixed |
| F5-1 | Stripe API key env injection | stripe_client.py | ✓ Fixed |
| SA-7.1 | Webhook HMAC + HTTP 500 | webhook_server.py | ✓ Fixed |
| SA-7.2 | /metrics endpoint | server.py (mesh) | ✓ Fixed |
| SA-4.3 | Containment via bwrap/docker | sandbox_runner.py | ✓ Fixed |
| SA-1.4 | test_mode drift sync | finance_claw.py:197-198 | ✓ Fixed |
| SA-1.3 | Bridge CLI approve/veto | bridge_cli.py:2039-2082 | ✓ Fixed |
| M-1 | RPC /health | bridge_server.py | ✓ Fixed |
| C-1 | `test_mode` class default `False` | spend_handler.py:104 | ✓ Fixed |
| H-6 | Bare `Exception` removed from tuple | spend_handler.py:184 | ✓ Fixed |
| I-2 | Daemon thread removed | spend_handler.py:795 | ✓ Fixed |
| C-2 | Bearer auth via `WARROOM_AUTH_TOKEN` | server.py | ✓ Fixed |
| C-3 | Path traversal rejection | server.py | ✓ Fixed |
| C-4 | `sys.path` via env + relative fallback | server.py | ✓ Fixed |
| C-5 | `html.escape` on all error strings | server.py | ✓ Fixed |
| H-1 | `super().do_GET()` removed | server.py | ✓ Fixed |
| H-2 | Origin header check on POST | server.py | ✓ Fixed |
| H-3 | SIGTERM/SIGINT -> `server.shutdown()` | server.py | ✓ Fixed |
| H-4 | Security headers on every response | server.py | ✓ Fixed |
| H-5 | Path strings HTML-escaped | server.py | ✓ Fixed |
| M-1 | GET `/health` endpoint | server.py | ✓ Fixed |
| M-2 | UUID request ID logging | server.py | ✓ Fixed |
| M-4 | Non-silent empty health | server.py | ✓ Fixed |
| M-5 | HTMX backoff on 5xx | warroom.html | ✓ Fixed |
| L-2 | `VALID_ROLES` from `milimo_core.contracts` | server.py | ✓ Fixed |
| L-3 | `Cache-Control: no-store` | server.py | ✓ Fixed |
| L-4 | `.error` CSS class | warroom.html | ✓ Fixed |
| I-1 | `warroom_bridge.py` created | warroom_bridge.py | ✓ Fixed |

## Verified Prior Fixes (Post-Audit Refinements)

| ID | Finding | File | Status |
|----|---------|------|--------|
| SA3-1b | Atomic filesystem lock (`O_CREAT|O_EXCL`) + stale-PID cleanup | spend_handler.py:371-399 | ✓ Fixed |
| SA3-2b | `daily_spend_cap_cents` env-driven via `MILIMO_DAILY_SPEND_CAP_CENTS` | spend_handler.py:115-118 | ✓ Fixed |
| SA3-3b | `_persist_queue_state()` writes queue events to `agent-spend.log` | spend_handler.py:689-715 | ✓ Fixed |
| SA3-4 | `_get_daily_spend_aggregate()` skips `queue_state` events | spend_handler.py:648-650 | ✓ Fixed |
| C-1b | `_validate_justification()` enforces >=100 chars | spend_handler.py:77-82 | ✓ Fixed |
| Issue 4 | `--test` removed from `request-approval` subcommand | spend_handler.py:540-548 | ✓ Fixed |
| Issue 8 | `--test` removed from `retrieve` subcommand | spend_handler.py:824-831 | ✓ Fixed |
| SIGTERM | Deadlock fixed: `serve_forever()` in non-daemon thread, `join()` from main | server.py | ✓ Fixed |
| Port 9090 | Default port changed 8080 -> 9090 (openshell conflict) | server.py | ✓ Fixed |
| I-2b | `_recover_and_resume_polling()` no longer preloads queued REVIEW/HOLD entries into memory on init; recovery is lazy via `_get_request()` | spend_handler.py:741-793 | ✓ Fixed |

## Discrepancies Between Audit Doc and Code

| ID | Audit Doc Claim | Actual Code Status |
|----|-----------------|-------------------|
| C-1 | Test mode default=True | Resolved: `test_mode: bool = False` at `spend_handler.py:104` |
| M-1 location | N/A | RPC /health lives in `milimo-blueprint/orchestrator/bridge_server.py`, not `milimo-core` |
| SA-4.3 | milimo-core | Containment (`bwrap`/`docker`) is in `milimo-core/src/milimo_core/evolution/sandbox_runner.py` and `containment.py` |
| I-2 | Daemon thread at line 742 | Resolved: non-daemon thread at `spend_handler.py:795-802` |
| H-6 | Bare except at line 497 | Resolved: specific tuple at `spend_handler.py:184` |

---

## Open Findings — milimo-core

### C-1: RESOLVED — `test_mode` Default Is `False`
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:104`
- **Resolution**: `__init__` parameter changed to `test_mode: bool = False`. Explicit opt-in to test mode is now required.

### H-6: RESOLVED — No Bare `Exception`
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:184`
- **Resolution**: Replaced with `(ValueError, AttributeError, IndexError)`; unexpected exceptions logged via `logger.exception()`.

### I-2: RESOLVED — No Daemon Thread
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:795-802`
- **Resolution**: Background polling thread is non-daemon. Thread completes or times out naturally on process exit.

---

## Open Findings — milimo-hermes-plugin/warroom

All 15 findings below are in `milimo-hermes-plugin/warroom/server.py` or `warroom.html` and have been resolved.

### C-2: RESOLVED — Authentication (Confidentiality)
- **File**: `server.py:42-243`
- **Resolution**: Bearer token auth via `WARROOM_AUTH_TOKEN` env var; 401 returned when unauthenticated.

### C-3: RESOLVED — Path Traversal (Confidentiality)
- **File**: `server.py:62-75`
- **Resolution**: `_safe_action_id()` validates against `^[a-zA-Z0-9_-]+$`; raw input never reaches `Path` construction.

### C-4: RESOLVED — Hardcoded `sys.path` Injection (Integrity)
- **File**: `server.py:11-14`
- **Resolution**: `MILIMO_CORE_PATH` env var with `Path(__file__)` relative fallback; no hardcoded absolute paths.

### C-5: RESOLVED — XSS via `str(e)` (Confidentiality)
- **File**: `server.py:106, 173, 196, 228`
- **Resolution**: `html.escape(str(e))` on all error strings; no raw exception interpolation in HTML.

### H-1: RESOLVED — SimpleHTTPRequestHandler LFD (Privacy)
- **File**: `server.py:59-60`
- **Resolution**: Base class changed to `BaseHTTPRequestHandler`; only `warroom.html` and `/health` are served.

### H-2: RESOLVED — CSRF Protection (Integrity)
- **File**: `server.py:62-75, 201-228`
- **Resolution**: `Origin` header check on all `do_POST`; cross-origin requests rejected with 403.

### H-3: RESOLVED — Graceful Shutdown (Reliability)
- **File**: `server.py:236-239`
- **Resolution**: `signal.signal(signal.SIGTERM, ...)` handler calls `server.shutdown()` from non-daemon thread.

### H-4: RESOLVED — Security Headers (Defense-in-Depth)
- **File**: `server.py:230-234`
- **Resolution**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store` on every response.

### H-5: RESOLVED — Path Leak in Error Responses (Privacy)
- **File**: `server.py:106, 173, 196, 228`
- **Resolution**: Covered by C-5 fix — path strings are HTML-escaped.

### M-1: RESOLVED — `/health` Endpoint (Observability)
- **File**: `server.py`
- **Resolution**: `GET /health` returns `200 OK` with `{"status": "ok"}` JSON body.

### M-2: RESOLVED — Structured Logging (Observability)
- **File**: `server.py:43-45, throughout`
- **Resolution**: UUID request_id generated per request; included in log output and `X-Request-ID` header.

### M-4: RESOLVED — Silent Empty Health dict (Observability)
- **File**: `server.py:79-84`
- **Resolution**: On health import failure, returns human-readable sentinel; distinguishes from healthy idle state.

### M-5: RESOLVED — HTMX Backoff on Errors (Usability)
- **File**: `warroom.html:64-91`
- **Resolution**: `hx-on::after-request` handler with exponential backoff on 5xx responses (5s -> 30s, 10s -> 60s).

### L-2: RESOLVED — Hardcoded Roles (Maintainability)
- **File**: `server.py:87`
- **Resolution**: Role list sourced from `milimo_core.contracts.VALID_ROLES`.

### L-3: RESOLVED — Cache-Control (Performance/Privacy)
- **File**: `server.py:230-234`
- **Resolution**: `Cache-Control: no-store` on all responses; covered by H-4 fix.

### L-4: RESOLVED — Error CSS State (Usability)
- **File**: `warroom.html:43`
- **Resolution**: `.error` CSS class (`#f85149`) added; server renders `<div class='error'>` distinct from `.empty`.

### I-1: RESOLVED — Missing `warroom_bridge.py` (Integrity)
- **File**: `milimo-hermes-plugin/warroom/`
- **Resolution**: `warroom_bridge.py` created with `approve_hold_message`, `veto_hold_message`, `resolve_mesh_dir`; `VALID_RECIPIENTS` enforced.

### I-2: RESOLVED — Daemon Thread (Reliability)
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:795-802`
- **Resolution**: Covered by milimo-core I-2 fix above.

---

## Implementation Plan

### Phase 1: milimo-core (COMPLETE)

| ID | Action | File | Line |
|----|--------|------|------|
| C-1 | Change `test_mode: bool = True` → `test_mode: bool = False` | spend_handler.py | 104 |
| H-6 | Replace `(ValueError, AttributeError, IndexError, Exception)` → `(ValueError, AttributeError, IndexError)`; add `else: logger.exception(...)` after the try block | spend_handler.py | 184 |
| I-2 | Remove `daemon=True` from `threading.Thread(...)` call | spend_handler.py | 795-802 |

### Phase 2: milimo-hermes-plugin/warroom/server.py (COMPLETE)

| ID | Action | File |
|----|--------|------|
| C-2 | Add simple token auth: check `Authorization: Bearer <token>` header; configurable via `WARROOM_AUTH_TOKEN` env var | server.py |
| C-3 | Validate `action_id` against `warpath.is_relative_to(warroom_inbox)` after construction; reject with 400 if traversal detected | server.py |
| C-4 | Replace hardcoded `sys.path` inserts with dynamic resolution: check `MILIMO_CORE_PATH` env var, fall back to relative `Path(__file__)` parent traversal | server.py |
| C-5 | Sanitize error strings before interpolation: `html.escape(str(e))`; add `import html` | server.py |
| H-1 | Restrict `do_GET` fallback: remove `super().do_GET()`, serve only `warroom.html` for `/`; reject everything else with 404 | server.py |
| H-2 | Add CSRF-style `Origin` header check on `do_POST`; reject cross-origin requests with 403 | server.py |
| H-3 | Add `signal.signal(signal.SIGTERM, ...)` handler; run `serve_forever()` in non-daemon thread; call `server.shutdown()` from signal handler | server.py |
| H-4 | Add security headers in `_send_html`: `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control` | server.py |
| H-5 | Sanitize error path strings: strip absolute path prefix from `str(e)`; also covered by C-5 fix | server.py |
| M-1 | Add `/health` endpoint returning `200 OK` with `{"status": "ok"}` JSON | server.py |
| M-2 | Add request ID to each request; include in log output via `extra={"request_id": ...}` | server.py |
| M-4 | Log warning and return empty HTML fragment instead of silent `{}` when health import fails; distinguish from healthy idle state | server.py |
| M-5 | Add `hx-on::after-request` handler with exponential backoff on 5xx responses | warroom.html |
| L-2 | Import `VALID_ROLES` from `milimo_core.contracts` and use it for role loop | server.py |
| L-3 | Add `Cache-Control: no-store` header | server.py |
| L-4 | Add `.error` CSS class distinct from `.empty`; use it in all 500 responses | warroom.html, server.py |
| I-1 | Create `warroom_bridge.py` abstraction layer between `server.py` and mesh filesystem operations | milimo-hermes-plugin/warroom/ |

---

## Verification Checklist

### Phase 1 Checks
- [x] `spend_handler.py` passes `python -m py_compile`
- [x] `test_mode` default confirmed `False` in class signature
- [x] `except (ValueError, AttributeError, IndexError)` confirmed at H-6 location (no bare `Exception`)
- [x] `daemon=True` absent from `_start_polling_thread`
- [x] `finance_claw.py` production caller still passes `test_mode=False` explicitly
- [x] All existing tests pass (1265 passed, 1 skipped)

### Phase 2 Checks
- [x] `server.py` passes `python -m py_compile`
- [x] `/health` returns `200` with JSON body
- [x] `GET /v1/warroom/unknown-path` returns `404` (not a file listing)
- [x] `POST /v1/warroom/hold-queue/x/approve` without `Authorization` header returns `401`
- [x] `POST` with path-traversal `action_id` (`../../etc/passwd`) returns `400`
- [x] `Authorization` header with `Bearer <token>` where `WARROOM_AUTH_TOKEN` is unset returns `500` (fail-closed)
- [x] `SIGTERM` to process exits cleanly (no traceback, no zombie threads)
- [x] Error response HTML contains no raw exception strings (confirmed escaped)
- [x] `warroom.html` htmx backoff shows reduced poll rate on 500 errors
- [x] `Cache-Control: no-store` present in all responses
- [x] `.error` CSS class renders distinctly from `.empty` in browser

---

## Related Pages

- [[war-room]] — War Room TUI and HTMX dashboard overview
- [[war-room-security]] — Security audit status and verification checklist
- [[approval-thresholds]] — REVIEW/HOLD/AUTO approval matrix
- [[spend-handler]] — SpendApprovalHandler implementation and audit findings
- [[finance-claw]] — Finance Claw documentation
- [[link-cli-setup]] — Stripe Link CLI auth and per-operator tokens
- [[sandbox-hardening]] — Sandbox image hardening
