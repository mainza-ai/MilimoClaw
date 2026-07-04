# MilimoClaw Production-Readiness Audit — Code-Verified Against Current HEAD
**Date:** 2026-07-04
**Method:** Line-by-line comparison against actual source files at HEAD (`0c86b7b`)
**Verdict:** NOT PRODUCTION-READY

---

## Summary of Today's Remediation Commits (8394148 → 0c86b7b)

Commits `455de10`, `6024ca9`, `cc5d523`, `9c68aec`, `fa48ed4`, `3d670e8`, `0c86b7b` closed **9 previously-open findings**:

| Finding | Severity | Fix Location | Commit |
|---|---|---|---|
| SA3-1 | CRITICAL | `spend_handler.py:352-389` — `O_CREAT|O_EXCL` + PID + stale cleanup | `455de10` |
| SA3-2 | CRITICAL | `spend_handler.py:188-189` — rolling 24h aggregate with `LOCK_SH` | `fa48ed4` |
| SA3-3 | MEDIUM | `spend_handler.py:670-682` — `fcntl.flock` + `f.flush()` + `os.fsync()` | `fa48ed4` |
| F5-1 | CRITICAL | `stripe_client.py:87` — `env={"STRIPE_API_KEY": ...}`, no `--api-key` | `455de10` |
| SA-7.1 | HIGH | `webhook_server.py:47-99,174` — HMAC verify + HTTP 500 on failure | `cc5d523` |
| SA-7.2 | MEDIUM | `bridge_server.py:355-472` — `/metrics` with Prometheus text format | `cc5d523` |
| SA-4.3 | CRITICAL | `containment.py` + `sandbox_runner.py:190-201` — bwrap/docker wrapping | `cc5d523`, `9c68aec` |
| SA-1.4 | MEDIUM | `finance_claw.py:190-199` (both copies) — env-driven `test_mode` | `fa48ed4` |
| SA-1.3 | HIGH | `bridge_cli.py:2039-2082` — `handle_approve_action` + `handle_veto_action` | `cc5d523` |
| M-1 | MEDIUM | `bridge_server.py:344-348` — `GET /health` on RPC server (port 19999) | `cc5d523` |

---

## Findings Still Open After Today's Commits

| ID | Sev | File:Line | Gap |
|---|---|---|---|
| C-1 | CRITICAL | `spend_handler.py:93` | `test_mode=True` default — any caller without explicit `test_mode=False` runs in test mode |
| C-2 | CRITICAL | `server.py:47-228` | Zero auth on all War Room endpoints |
| C-3 | CRITICAL | `server.py:205,212-221` | Path traversal via POST filename from URL path |
| C-4 | CRITICAL | `server.py:11-14,79` | Hardcoded sys.path version-pinned to 0.1.0 |
| C-5 | CRITICAL | `server.py:106,173,196,228` | 500 htmx swap injects raw `str(e)` — blank page + XSS |
| H-1 | HIGH | `server.py:59-60` | `SimpleHTTPRequestHandler` allows arbitrary local file read |
| H-2 | HIGH | `server.py:62-75` | No CSRF token on state-mutating POST |
| H-3 | HIGH | `server.py:236-239` | No SIGTERM handler — in-flight approvals can be lost |
| H-4 | HIGH | `server.py:230-234` | No CORS headers |
| H-5 | HIGH | `server.py:106,173,196,228` | Error responses leak absolute filesystem paths |
| H-6 | HIGH | `spend_handler.py:497` | Bare `except Exception` silently drops JSON parse failures |
| H-7 | HIGH | `stripe-link.yaml:20,24`, `milimo-mcp.yaml:92,104` | `tls: skip` nuance — see below |
| M-1 | MEDIUM | `server.py` (absent) | War Room HTMX server still has no `/health` endpoint (RPC server fixed) |
| M-2 | MEDIUM | `server.py:17-18,43-45` | No structured JSON logging; HTTP access logs silently dropped |
| M-4 | MEDIUM | `server.py:80-84` | `bridge_cli` import failure → silent empty health dict |
| M-5 | MEDIUM | `warroom.html:64-91` | No htmx error backoff on failed polls |
| L-1 | LOW | `__init__.py:85,100,355` | `print()` instead of `logger` |
| L-2 | LOW | `server.py:87` | Hardcoded role list diverges from `contracts.VALID_ROLES` |
| L-3 | LOW | `server.py:230-234` | No `Cache-Control: no-store` |
| L-4 | LOW | `warroom.html` | No error-state CSS class |
| I-1 | INFO | `milimo_hermes_plugin/` | `warroom_bridge.py` missing |
| I-2 | INFO | `spend_handler.py:742` | Daemon thread abandons Link session on process exit |
| I-3 | INFO | `milimo-audit-report.md:10` | Executive summary still reads "PRODUCTION-READY" — stale |
| I-4 | INFO | `milimo-mcp.yaml` | Python binary path hardcoded 13x |
| SA2-1 | CRITICAL | `bridge_cli.py` / `issue_manager.py` | Sprint pipeline stall — `handle_sprint_plan_approved` unwired in production path |
| SA-4.1 | MEDIUM | `mesh.py:L128-138` | Plaintext fallback when `mesh_secret` empty |
| SA-4.2 | HIGH | `mesh.py:L404-409` | No persistent outbox for outbound mesh messages |
| SA-6.1 | HIGH | `region_detector.py:L108-442` | `RegionDetector` is dead/orphaned code |
| SA-6.2 | HIGH | `privacy_router.py:L50-100` | Tenant isolation header-only, no schema partitioning |

---

## Verified Against Actual Code

### spend_handler.py (840 lines)

| Line | What's There | Status |
|---|---|---|
| 93 | `test_mode: bool = True,` | **STILL OPEN** — C-1 |
| 188-189 | `daily_spent = self._get_daily_spend_aggregate()` + `if daily_spent + request.amount_cents > self.daily_spend_cap_cents:` | **FIXED** — SA3-2 |
| 352-389 | `os.open(lock_path, os.O_CREAT \| os.O_EXCL \| os.O_WRONLY)` + PID check + stale cleanup | **FIXED** — SA3-1 |
| 497 | `except (ValueError, AttributeError, IndexError, Exception): pass` | **STILL OPEN** — H-6 |
| 613-641 | `_get_daily_spend_aggregate()` with `fcntl.LOCK_SH` | **FIXED** — part of SA3-2 |
| 670-682 | `_log_decision()` with `fcntl.LOCK_EX` + `f.flush()` + `os.fsync()` | **FIXED** — SA3-3 |
| 742 | `threading.Thread(..., daemon=True)` | **STILL OPEN** — I-2 |

### server.py (243 lines, UNCHANGED)

| Line | What's There | Status |
|---|---|---|
| 11-14 | 3x hardcoded `sys.path.insert(0, "/sandbox/.nemoclaw/blueprints/0.1.0")` etc. | **STILL OPEN** — C-4 |
| 47-60 | `do_GET` with no auth check | **STILL OPEN** — C-2 |
| 62-75 | `do_POST` with filename from URL path, no sanitization | **STILL OPEN** — C-3 |
| 106,173,196,228 | `self._send_html(500, f"<div class='empty'>Error: {e}</div>")` | **STILL OPEN** — C-5 + H-5 |
| 230-234 | `_send_html` with no security headers, no CORS | **STILL OPEN** — H-4 + L-3 |
| 236-239 | `serve_forever()` with no signal handler | **STILL OPEN** — H-3 |

### warroom.html (98 lines, UNCHANGED)

| Line | What's There | Status |
|---|---|---|
| 7 | `<script src="https://unpkg.com/htmx.org@2.x"></script>` — CDN, no local fallback | **STILL OPEN** |
| 64-91 | `hx-trigger="every 5s"` with no `hx-retry`, no error backoff | **STILL OPEN** — M-5 |

### __init__.py (382 lines, UNCHANGED)

| Line | What's There | Status |
|---|---|---|
| 85 | `print(f"[milimo-hermes] Plugin loaded")` | **STILL OPEN** — L-1 |
| 100 | `print("[milimo-hermes] Plugin unloaded")` | **STILL OPEN** — L-1 |
| 355 | `print("[milimo-hermes] All 6 claw skills...")` | **STILL OPEN** — L-1 |

---

## H-7 Nuance: `tls: skip` on Stripe Link Policy Endpoints

**Status: Requires architectural confirmation, not a blind revert.**

`api.link.com` and `login.link.com` have:
```yaml
access: full
tls: skip
binaries: ["/usr/local/bin/node", "/usr/local/bin/link-cli", "/opt/hermes/.venv/bin/python"]
```

`portal.nousresearch.com` and `inference-api.nousresearch.com` have the SAME pattern with an explicit comment: `tls: skip is required so the proxy passes encrypted bytes through unmodified — OAuth redirects and inference API calls require E2E TLS.`

If Stripe Link's `api.link.com` and `login.link.com` also require L4 raw-TLS tunneling (the `access: full` + `node`/`link-cli` binaries strongly suggest this), then `tls: skip` is **intentionally required** for the same reason as the Nous endpoints. Removing it without confirming the tunnel architecture would break the payment flow.

**Action**: Confirm with infra whether `api.link.com` and `login.link.com` are L4-tunneled. If yes, add the same explanatory comment as the Nous endpoints. If no (L7 HTTP is sufficient), remove `tls: skip` and switch to `protocol: rest` with standard TLS termination.

---

## Implementation Priority (Post-Today's-Commits)

### Must-fix before production (CRITICAL still open)
1. **C-1** `test_mode=True` default → change to `False`. One-line change. Highest priority because it directly controls whether real money moves.
2. **C-2/C-3** War Room server auth + path traversal → add bearer token + filename regex. Security blocking.
3. **C-4/C-5** hardcoded sys.path + 500 htmx → CLI args + safe error fragments. Unblocks blank page root cause.

### Should-fix before first operator use (HIGH still open)
4. **H-1** LFD via SimpleHTTPRequestHandler → override do_GET path check
5. **H-2** CSRF on POST → add `X-Warroom-Token` header check
6. **H-3** SIGTERM drain → add signal handler + `fcntl.flock` on rename
7. **H-6** bare except in JSON parse at `spend_handler.py:497` → narrow except clause

### Nice-to-fix before scale (MEDIUM/LOW/INFO)
8. **M-1** `/health` on War Room server (RPC server already has it)
9. **M-2** Structured logging
10. **I-2** Non-daemon polling thread + atexit cleanup
11. **L-1/L-2/L-3/L-4** Low-priority cleanliness
12. **I-3** Update audit report executive summary to reflect what was actually fixed
