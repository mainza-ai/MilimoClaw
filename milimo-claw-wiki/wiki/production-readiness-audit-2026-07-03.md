# Production-Readiness Audit — 2026-07-03

**Summary**: Line-level code audit verified against HEAD, cross-referenced against WARROOM_PRODUCTION_READINESS.md. Documents all open findings and the two-phase implementation plan.

**Sources**: `WARROOM_PRODUCTION_READINESS.md`, `milimo-core/`, `milimo-hermes-plugin/warroom/`, `milimo-blueprint/`

**Last updated**: 2026-07-03

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

## Discrepancies Between Audit Doc and Code

| ID | Audit Doc Claim | Actual Code Status |
|----|-----------------|-------------------|
| C-1 | Test mode default=True | Partially mitigated: `finance_claw.py:197-198` overrides to False at call site; class default in `spend_handler.py:93` remains True |
| M-1 location | N/A | RPC /health lives in `milimo-blueprint/orchestrator/bridge_server.py`, not `milimo-core` |
| SA-4.3 | milimo-core | Containment (`bwrap`/`docker`) is in `milimo-core/src/milimo_core/evolution/sandbox_runner.py` and `containment.py` |

---

## Open Findings — milimo-core

### C-1: `test_mode` Default Is `True` (Confidentiality)
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:93`
- **Severity**: Medium
- **Detail**: `__init__` parameter `test_mode: bool = True`. Any direct instantiation without explicitly passing `False` runs in test mode — real charges are never executed, but the gap between test and production behavior can mask integration bugs.
- **Mitigation in place**: `finance_claw.py:197-198` explicitly passes `test_mode=False` in production.
- **Recommended fix**: Change class default to `False` so that explicit opt-in to test mode is required.

### H-6: Bare `Exception` in Error Handler (Correctness)
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:497`
- **Severity**: Medium
- **Detail**: `except (ValueError, AttributeError, IndexError, Exception):` — `Exception` in the tuple swallows everything including `KeyboardInterrupt`, `SystemExit`, and unexpected bugs silently.
- **Recommended fix**: Restrict to `(ValueError, AttributeError, IndexError)`; log unexpected exceptions explicitly.

### I-2: Daemon Thread (Reliability)
- **File**: `milimo-core/src/milimo_core/finance/spend_handler.py:742`
- **Severity**: Medium
- **Detail**: Background polling thread is started with `daemon=True`. Daemon threads are killed abruptly on process exit — any in-flight Link CLI request is abandoned, and in-progress spend approval state may be silently dropped.
- **Recommended fix**: Remove `daemon=True`; thread will complete or time out naturally.

---

## Open Findings — milimo-hermes-plugin/warroom

All 15 findings below are in `milimo-hermes-plugin/warroom/server.py` (243 lines total) or `warroom.html`.

### C-2: No Authentication (Confidentiality)
- **File**: `server.py:42-243`
- **Severity**: Critical
- **Detail**: Zero authentication. Any local process or network peer can approve or veto actions. No API key, no session, no origin check.

### C-3: Path Traversal via `action_id` (Confidentiality)
- **File**: `server.py:68-71`
- **Severity**: High
- **Detail**: `action_id = parts[3]` is passed directly into `Path` construction at line 205: `warroom_inbox / filename`. A crafted `action_id` like `../../etc/passwd` accesses arbitrary filesystem paths.

### C-4: Hardcoded `sys.path` Injection (Integrity)
- **File**: `server.py:11-14`
- **Severity**: High
- **Detail**: Four `sys.path.insert(0, ...)` calls with absolute paths hardcoded for a specific NemoClaw sandbox layout. Breaks outside that environment and is a supply-chain risk if sandbox is compromised.

### C-5: XSS via `str(e)` (Confidentiality)
- **File**: `server.py:106, 173, 196, 228`
- **Severity**: High
- **Detail**: All five error responses interpolate raw exception strings into HTML: `f"<div class='empty'>Error: {e}</div>"`. An attacker who controls an error message (e.g., via path traversal payload in C-3) achieves stored/reflected XSS.

### H-1: SimpleHTTPRequestHandler LFD (Privacy)
- **File**: `server.py:59-60`
- **Severity**: High
- **Detail**: `super().do_GET()` falls through to Python's `SimpleHTTPRequestHandler`, which serves any file in `os.getcwd()` — arbitrary file disclosure for any file in the working directory.

### H-2: No CSRF Protection (Integrity)
- **File**: `server.py:62-75, 201-228`
- **Severity**: High
- **Detail**: All `do_POST` endpoints (approve, veto) accept any cross-origin POST. No `Origin` header check, no CSRF token, no `SameSite` cookie.

### H-3: No Graceful Shutdown (Reliability)
- **File**: `server.py:236-239`
- **Severity**: Medium
- **Detail**: `server.serve_forever()` — no signal handler for `SIGTERM`/`SIGINT`. Process receives ungraceful termination, potentially corrupting in-flight decisions.

### H-4: No Security Headers (Defense-in-Depth)
- **File**: `server.py:230-234`
- **Severity**: Medium
- **Detail**: `_send_html` only sets `Content-Type`. Missing: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`.

### H-5: Path Leak in Error Responses (Privacy)
- **File**: `server.py:106, 173, 196, 228` (same as C-5)
- **Severity**: Medium
- **Detail**: Exception tracebacks include full Python file paths (`/sandbox/...`), exposing sandbox internals.

### M-1: No `/health` Endpoint (Observability)
- **File**: `server.py:42-243`
- **Severity**: Low
- **Detail**: No liveness/readiness endpoint. Container orchestrators and load balancers cannot verify server health.

### M-2: No Structured Logging (Observability)
- **File**: `server.py:43-45, throughout`
- **Severity**: Low
- **Detail**: Logs are unstructured text. No request ID, no action ID correlation, making incident investigation difficult.

### M-4: Silent Empty Health dict (Observability)
- **File**: `server.py:79-84`
- **Severity**: Medium
- **Detail**: When `bridge_cli` health import fails, the handler returns `health = {}`, which renders as six `"idle"` claw status entries — silent masking of infrastructure failures.

### M-5: No HTMX Backoff on Errors (Usability)
- **File**: `warroom.html:64-91`
- **Severity**: Low
- **Detail**: HTMX polling intervals are fixed (5s, 10s, 30s). On a 500 error, the browser continues polling at full rate, hammering a degraded server.

### L-2: Hardcoded Roles (Maintainability)
- **File**: `server.py:87`
- **Severity**: Low
- **Detail**: Role list `["content", "ops", "analytics", "finance", "build", "assistant"]` is hardcoded rather than sourced from `milimo_core.contracts.VALID_ROLES`.

### L-3: No Cache-Control (Performance/Privacy)
- **File**: `server.py:230-234`
- **Severity**: Low
- **Detail**: All responses are cacheable by default (browsers/CDNs).

### L-4: No Error CSS State (Usability)
- **File**: `warroom.html:43`
- **Severity**: Low
- **Detail**: `.empty` class is shared between "loading..." and "Error: ..." states — operator cannot distinguish a healthy empty queue from a server error.

### I-1: Missing `warroom_bridge.py` (Integrity)
- **File**: `milimo-hermes-plugin/warroom/`
- **Severity**: High
- **Detail**: The wiki references `spend-warroom-bridge` as a module but `warroom_bridge.py` does not exist in the plugin directory. Spend approval decisions are handled entirely inside `server.py` with no bridge abstraction.

---

## Implementation Plan

### Phase 1: milimo-core (Low Coupling — No Plugin Interface Changes)

| ID | Action | File | Line |
|----|--------|------|------|
| C-1 | Change `test_mode: bool = True` → `test_mode: bool = False` | spend_handler.py | 93 |
| H-6 | Replace `(ValueError, AttributeError, IndexError, Exception)` → `(ValueError, AttributeError, IndexError)`; add `else: logger.exception(...)` after the try block | spend_handler.py | 497-498 |
| I-2 | Remove `daemon=True` from `threading.Thread(...)` call | spend_handler.py | 739-743 |

### Phase 2: milimo-hermes-plugin/warroom/server.py (Single Hardening PR)

| ID | Action | File |
|----|--------|------|
| C-2 | Add simple token auth: check `Authorization: Bearer <token>` header; configurable via `WARROOM_AUTH_TOKEN` env var | server.py |
| C-3 | Validate `action_id` against `warpath.is_relative_to(warroom_inbox)` after construction; reject with 400 if traversal detected | server.py:205 |
| C-4 | Replace hardcoded `sys.path` inserts with dynamic resolution: check `MILIMO_CORE_PATH` env var, fall back to relative `Path(__file__)` parent traversal | server.py:11-14 |
| C-5 | Sanitize error strings before interpolation: `html.escape(str(e))`; add `import html` | server.py:106,173,196,228 |
| H-1 | Restrict `do_GET` fallback: remove `super().do_GET()`, serve only `warroom.html` for `/`; reject everything else with 404 | server.py:59-60 |
| H-2 | Add CSRF-style `Origin` header check on `do_POST`; reject cross-origin requests with 403 | server.py:62-75 |
| H-3 | Add `signal.signal(signal.SIGTERM, ...)` handler; call `server.shutdown()` in signal handler | server.py:236-239 |
| H-4 | Add security headers in `_send_html`: `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control` | server.py:230-234 |
| H-5 | Sanitize error path strings: strip absolute path prefix from `str(e)`; also covered by C-5 fix | server.py:106,173,196,228 |
| M-1 | Add `/health` endpoint returning `200 OK` with `{"status": "ok"}` JSON | server.py |
| M-2 | Add request ID to each request; include in log output via `extra={"request_id": ...}` | server.py |
| M-4 | Log warning and return empty HTML fragment instead of silent `{}` when health import fails; distinguish from healthy idle state | server.py:79-84 |
| M-5 | Add `hx-on::after-request` handler with exponential backoff on 5xx responses | warroom.html:64-91 |
| L-2 | Import `VALID_ROLES` from `milimo_core.contracts` and use it for role loop | server.py:87 |
| L-3 | Add `Cache-Control: no-store` header | server.py:230-234 |
| L-4 | Add `.error` CSS class distinct from `.empty`; use it in all 500 responses | warroom.html, server.py |
| I-1 | Create `warroom_bridge.py` abstraction layer between `server.py` and mesh filesystem operations | milimo-hermes-plugin/warroom/ |

---

## Verification Checklist

### Phase 1 Checks
- [ ] `spend_handler.py` passes `python -m py_compile`
- [ ] `test_mode` default confirmed `False` in class signature
- [ ] `except (ValueError, AttributeError, IndexError)` confirmed at H-6 location (no bare `Exception`)
- [ ] `daemon=True` absent from `_start_polling_thread`
- [ ] `finance_claw.py` production caller still passes `test_mode=False` explicitly
- [ ] All existing tests pass

### Phase 2 Checks
- [ ] `server.py` passes `python -m py_compile`
- [ ] `/health` returns `200` with JSON body
- [ ] `GET /v1/warroom/unknown-path` returns `404` (not a file listing)
- [ ] `POST /v1/warroom/hold-queue/x/approve` without `Authorization` header returns `401`
- [ ] `POST` with path-traversal `action_id` (`../../etc/passwd`) returns `400`
- [ ] `Authorization` header with `Bearer <token>` where `WARROOM_AUTH_TOKEN` is unset returns `500` (fail-closed)
- [ ] `SIGTERM` to process exits cleanly (no traceback, no zombie threads)
- [ ] Error response HTML contains no raw exception strings (confirmed escaped)
- [ ] `warroom.html` htmx backoff shows reduced poll rate on 500 errors
- [ ] `Cache-Control: no-store` present in all responses
- [ ] `.error` CSS class renders distinctly from `.empty` in browser

---

## Related Pages

- [[sandbox-hardening]] — NemoClaw sandbox image hardening
- [[openclaw-controls]] — OpenClaw application-layer security
- [[best-practices]] — Four protection layers
- [[war-room]] — War Room TUI overview
- [[approval-thresholds]] — REVIEW/HOLD/AUTO approval matrix
- [[spend-warroom-bridge]] — Spend approval flow documentation
