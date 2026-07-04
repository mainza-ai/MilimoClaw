# War Room Security

**Summary**: Security posture, open findings, and hardening status for both War Room interfaces — the terminal TUI and the HTMX plugin server.

**Sources**:
- `milimo-hermes-plugin/warroom/server.py`
- `milimo-hermes-plugin/warroom/warroom.html`
- `milimo-hermes-plugin/warroom/warroom_bridge.py`
- `milimo-claw-docs/reference/WARROOM_PRODUCTION_READINESS.md`

**Last updated**: 2026-07-04

**Tags**: #coordination #warroom #security #audit

---

## Security Audit Status

This page tracks the current state of the production-readiness audit findings as they relate to the War Room interface. The authoritative source is `WARROOM_PRODUCTION_READINESS.md`.

## War Room Interfaces

| Interface | Location | Layer | Status |
|-----------|----------|-------|--------|
| Terminal TUI | [[solo-warroom]] | Solo action queue | Production-ready |
| HTMX Server | `milimo-hermes-plugin/warroom/server.py` | Python HTTP plugin | **Production-ready — all findings closed** |

## Phase 1 — milimo-core fixes (COMPLETE)

| ID | Sev | File | Fix | Status |
|----|-----|------|-----|--------|
| C-1 | CRITICAL | `milimo-core/.../finance/spend_handler.py:104` | `test_mode` default changed from `True` to `False`; production caller in `finance_claw.py` passes env-driven value | ✓ Fixed |
| H-6 | HIGH | `milimo-core/.../finance/spend_handler.py:184` | Narrow bare `except Exception: pass` to specific parse errors; log and block request on failure | ✓ Fixed |
| I-2 | INFO | `milimo-core/.../finance/spend_handler.py:795` | Non-daemon polling thread — Link approval session survives process exit | ✓ Fixed |

## Phase 2 — HTMX plugin server hardening (COMPLETE)

| ID | Sev | File | Finding | Fix |
|----|-----|------|---------|-----|
| C-2 | CRITICAL | `server.py` | Zero auth on all War Room endpoints | `WARROOM_AUTH_TOKEN` Bearer check; 401 when unauthenticated |
| C-3 | CRITICAL | `server.py` | Path traversal via `action_id` in URL path | `_safe_action_id()` validates `^[a-zA-Z0-9_-]+$`; rejects traversal |
| C-4 | CRITICAL | `server.py:11-14` | Hardcoded `sys.path.insert` calls | Replaced with `MILIMO_CORE_PATH` env + `Path(__file__)` relative fallback |
| C-5 | CRITICAL | `server.py` | Raw `str(e)` in HTML error responses | `html.escape(str(e))` on all error strings |
| H-1 | HIGH | `server.py` | `SimpleHTTPRequestHandler` allows arbitrary local file read | Base class changed to `BaseHTTPRequestHandler`; only `warroom.html` + `/health` served |
| H-2 | HIGH | `server.py` | No CSRF protection on POST | `Origin` header check; cross-origin POST rejected with 403 |
| H-3 | HIGH | `server.py` | No SIGTERM handler | `signal.signal(signal.SIGTERM, ...)` calls `server.shutdown()` from non-daemon thread |
| H-4 | HIGH | `server.py` | No security headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store` |
| H-5 | HIGH | `server.py` | Error responses leak absolute filesystem paths | Covered by C-5 fix |
| M-1 | MEDIUM | `server.py` | No `/health` endpoint | `GET /health` returns `{"status": "ok"}` |
| M-2 | MEDIUM | `server.py` | No structured logging | UUID request_id; logged + `X-Request-ID` response header |
| M-4 | MEDIUM | `server.py` | Silent empty health dict on import failure | Returns sentinel with "Health data unavailable" |
| M-5 | MEDIUM | `warroom.html:64-91` | No HTMX backoff on errors | `hx-on::after-request` exponential backoff on 5xx |
| L-2 | LOW | `server.py` | Hardcoded role list | `VALID_ROLES` imported from `milimo_core.contracts` |
| L-3 | LOW | `server.py` | No `Cache-Control` | Covered by H-4 fix |
| L-4 | LOW | `warroom.html` | No error-state CSS class | `.error` CSS class (`#f85149`) renders distinctly from `.empty` |
| I-1 | INFO | `warroom/` | `warroom_bridge.py` missing | Created — `approve_hold_message`, `veto_hold_message`, `resolve_mesh_dir` |

## Post-Audit Refinements

| ID | Finding | File | Status |
|----|---------|------|--------|
| SIGTERM-deadlock | `serve_forever()` + `shutdown()` in same thread caused deadlock | server.py | ✓ Fixed — `serve_forever()` runs in non-daemon thread; `join()` from main |
| Port 9090 | Default port 8080 conflicted with OpenShell gateway | server.py | ✓ Fixed — default changed to 9090 |
| Queue persistence | REVIEW/HOLD entries lost on daemon restart | spend_handler.py | ✓ Fixed — `_persist_queue_state()` + `_recover_and_resume_polling()` |
| Queue-state cap bug | `_get_daily_spend_aggregate()` summed `queue_state` entries as real spends | spend_handler.py | ✓ Fixed — skips `event == "queue_state"` entries |
| Recovery over-eager | `_recover_and_resume_polling()` inserted every queued spend_id into `_requests` on init | spend_handler.py | ✓ Fixed — only resumes polling threads; REVIEW/HOLD reconstructed lazily via `_get_request()` |
| Justification length | `link-cli --context` requires >=100 chars; handler passed verbatim | spend_handler.py | ✓ Fixed — `_validate_justification()` raises ValueError |
| `--test` restrictions | `--test` invalid on `request-approval` and `retrieve` subcommands | spend_handler.py | ✓ Fixed — only passed on `create` |

## Verification Checklist

- [x] `SpendApprovalHandler().test_mode is False` confirmed in REPL
- [x] `test_mode=False` in `spend_handler.py:104`
- [x] No bare `except Exception: pass` in `spend_handler.py`
- [x] Non-daemon polling thread at `spend_handler.py:795`
- [x] `server.py` base class is `BaseHTTPRequestHandler` (no `super().do_GET()`)
- [x] All `sys.path.insert` calls removed from `server.py`
- [x] `curl` without `X-Warroom-Token` returns HTTP 401
- [x] `curl` with path-traversal `action_id` returns HTTP 400
- [x] `kill -TERM <server-pid>` results in clean shutdown within 5s
- [x] `warroom.html` loads with no console errors
- [x] All `test_spend_flow.py` tests pass (1265 passed)
- [x] `_persist_queue_state()` writes to `agent-spend.log`; queue survives restart
- [x] `_get_daily_spend_aggregate()` excludes `queue_state` events
- [x] `--test` only on `create`; absent from `request-approval` and `retrieve`

## Related Pages

- [[war-room]] — War Room overview
- [[approval-thresholds]] — REVIEW/HOLD/AUTO definitions
- [[spend-handler]] — Finance Claw spend approval details
- [[link-cli-setup]] — Stripe Link CLI configuration
- [[production-readiness-audit-2026-07-03]] — Full finding register with implementation plan
