# War Room Security

**Summary**: Security posture, open findings, and hardening status for both War Room interfaces — the terminal TUI and the HTMX plugin server.

**Sources**:
- `milimo-hermes-plugin/warroom/server.py`
- `milimo/src/warroom/warroom.ts`
- `milimo-hermes-plugin/warroom/warroom.html`
- `milimo-claw-docs/reference/WARROOM_PRODUCTION_READINESS.md`

**Last updated**: 2026-07-04

**Tags**: #coordination #warroom #security #audit

---

## Security Audit Status

This page tracks the current state of the production-readiness audit findings as they relate to the War Room interface. The authoritative source is `WARROOM_PRODUCTION_READINESS.md`.

## War Room Interfaces

| Interface | Location | Layer | Status |
|-----------|----------|-------|--------|
| Terminal TUI | `milimo/src/warroom/warroom.ts` | TypeScript CLI | Production-ready |
| HTMX Server | `milimo-hermes-plugin/warroom/server.py` | Python HTTP plugin | **Under hardening — 12 findings open** |

## Phase 1 — milimo-core fixes (complete or in progress)

| ID | Sev | File | Fix | Status |
|----|-----|------|-----|--------|
| C-1 | CRITICAL | `milimo-core/.../finance/spend_handler.py:93` | `test_mode` default changed from `True` to `False`; production caller in `finance_claw.py` already passes env-driven value | In progress |
| H-6 | HIGH | `milimo-core/.../finance/spend_handler.py:497` | Narrow bare `except Exception: pass` to specific parse errors; log and block request on failure | In progress |
| I-2 | INFO | `milimo-core/.../finance/spend_handler.py:742` | Change daemon polling thread to non-daemon so Link approval session survives process exit | In progress |

## Phase 2 — HTMX plugin server hardening

| ID | Sev | File | Finding | Fix |
|----|-----|------|---------|-----|
| C-2 | CRITICAL | `server.py:47-60` | Zero auth on all War Room endpoints | Add `X-Warroom-Token` bearer check |
| C-3 | CRITICAL | `server.py:62-75` | Path traversal via POST filename from URL path | Validate `action_id` with regex `^[a-zA-Z0-9_-]+$` |
| C-4 | CRITICAL | `server.py:11-14` | Hardcoded `sys.path.insert` × 3, version-pinned to `0.1.0` | Remove all `sys.path.insert`; rely on plugin loader `PYTHONPATH` |
| C-5 | CRITICAL | `server.py:106,173,196,228` | 500 htmx swap injects raw `str(e)` — blank page + XSS | Use `_send_error_html` with `html.escape()` |
| H-1 | HIGH | `server.py:59-60` | `SimpleHTTPRequestHandler` allows arbitrary local file read | Switch base class to `BaseHTTPRequestHandler` |
| H-2 | HIGH | `server.py:62-75` | No CSRF token on state-mutating POST | `X-Warroom-Token` header check covers this |
| H-3 | HIGH | `server.py:236-239` | No SIGTERM handler — in-flight approvals lost on restart | Add `signal.signal(SIGTERM, ...)` + `server.shutdown()` |
| H-4 | HIGH | `server.py:230-234` | No CORS headers, no `Cache-Control`, no `X-Content-Type-Options` | Add all three in `_send_html` |
| H-5 | HIGH | `server.py:106,173,196,228` | Error responses leak absolute filesystem paths via `str(e)` | Covered by C-5 fix |
| M-1 | MEDIUM | `server.py` (absent) | HTMX server has no `/health` endpoint | Add `/health` handler |
| M-2 | MEDIUM | `server.py:17-18,43-45` | No structured JSON logging; access logs suppressed | Replace `log_message` with JSON-formatted access log |
| M-4 | MEDIUM | `server.py:79-84` | `bridge_cli` import failure → silent empty health dict | Return sentinel dict with per-claw `"unknown"` status |
| M-5 | MEDIUM | `warroom.html:64-91` | No htmx error backoff on failed polls | Add `hx-retry="every 30s"` + `hx-swap-error` |
| L-2 | LOW | `server.py:87` | Hardcoded role list diverges from `contracts.VALID_ROLES` | Import from `milimo_core.contracts` |
| L-3 | LOW | `server.py:230-234` | No `Cache-Control: no-store` | Covered by H-4 fix |
| L-4 | LOW | `warroom.html` | No error-state CSS class | Add `.error-state` class |
| I-1 | INFO | `milimo-hermes-plugin/warroom/` | `warroom_bridge.py` missing | Create bridge module watching mesh inbox |
| I-2 | INFO | `milimo-core/.../spend_handler.py:742` | Daemon thread abandons Link session | Covered by Phase 1 fix above |
| I-3 | INFO | `milimo-audit-report.md:10` | Executive summary still reads "PRODUCTION-READY" — stale | Update once all Phase 2 changes land |
| I-4 | INFO | `milimo-mcp.yaml` | Python binary path hardcoded 13× | Env-var refactor — post-security hardening |

## Implementation Phases

```
Phase 1 (milimo-core)          Phase 2 (HTMX plugin)
─────────────────────────       ─────────────────────────
C-1  test_mode default      →    C-2  auth header
H-6  bare except            →    C-3  action_id regex
I-2  daemon thread          →    C-4  remove sys.path.insert
                             →    C-5  safe error fragments
                             →    H-1  BaseHTTPRequestHandler
                             →    H-2  CSRF via auth header
                             →    H-3  SIGTERM handler
                             →    H-4/H-5  security headers + html.escape
                             →    M-1  /health endpoint
                             →    M-2  structured logging
                             →    M-4  sentinel health dict
                             →    M-5  hx-retry on polls
                             →    L-2/L-3/L-4  minor polish
                             →    I-1  warroom_bridge.py new file
```

## Verification Checklist

- [ ] `SpendApprovalHandler().test_mode is False` confirmed in REPL
- [ ] `test_mode=False` in `spend_handler.py:93`
- [ ] No bare `except Exception: pass` in `spend_handler.py`
- [ ] `threading.Thread(..., daemon=False)` at `spend_handler.py:742`
- [ ] `server.py` base class is `BaseHTTPRequestHandler` (no `super().do_GET()`)
- [ ] All `sys.path.insert` calls removed from `server.py`
- [ ] `curl` without `X-Warroom-Token` returns HTTP 401
- [ ] `curl` with path-traversal filename returns HTTP 400
- [ ] `kill -TERM <server-pid>` results in clean shutdown within 5s
- [ ] `warroom.html` loads with no console errors
- [ ] All existing `test_spend_flow.py` tests pass with new defaults

## Related Pages

- [[war-room]] — War Room overview and TUI documentation
- [[approval-thresholds]] — REVIEW/HOLD/AUTO definitions
- [[spend-handler]] — Finance Claw spend approval details
- [[link-cli-setup]] — Stripe Link CLI configuration
