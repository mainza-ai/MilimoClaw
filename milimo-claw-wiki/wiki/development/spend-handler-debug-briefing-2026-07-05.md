# Spend Handler Debug Briefing — 2026-07-05
## Root Cause Found: proxy env vars absent in `execute_code`

**Pages**: [[spend-handler]], [[link-cli-setup]], [[sandbox-isolation]]
**Last updated**: 2026-07-05
**Tags**: #development #finance #spend #link-cli #proxy #execute_code #debug

---

## 1. What the test showed

### 1.1 Working end-to-end (terminal shell path)

User ran this sequence in the terminal shell (after device approval):

```bash
link-cli spend-request create \
  --test --no-request-approval \
  --payment-method-id csmrpd_61UxbV8TRIawugVAW41K2MJSohSIrJlY \
  --amount 2000 --merchant-name Vercel \
  --merchant-url https://vercel.com \
  --context "<300-char justification>" \
  --total "type:total,display_text:Total,amount:2000" \
  --format json
  → rc=0, lsrq_1TpecbK2MJSohSIrltx7e2UM

link-cli spend-request request-approval lsrq_1TpecbK2MJSohSIrltx7e2UM
  → rc=0

link-cli spend-request retrieve lsrq_1TpecbK2MJSohSIrltx7e2UM --format json
  → status=approved
```

### 1.2 Handler path — partial success, `UNKNOWN` at release

```
queue_spend_review(request)    → logged review/queued, spend_id=spend-f147f611
handle_review_approve(...)     → moved to HOLD
handle_hold_release(...)       → FAILED
  → proc_create.stdout = {"code":"UNKNOWN","message":"Request failed: POST https://api.link.com/spend_requests"}
  → proc_create.stderr = ""   (empty)
  → returncode != 0
```

Raw-shell equivalent immediately after: rc=0, valid `lsrq_*`.

---

## 2. Root Cause (confirmed by Hermes agent)

**`link-cli` is a Node.js binary. Node's HTTP client reads proxy settings from env vars.**

The terminal shell exports these vars (from OpenShell profile or `.bashrc`):
```
HTTP_PROXY=http://10.200.0.1:3128
HTTPS_PROXY=http://10.200.0.1:3128
NO_PROXY=localhost,127.0.0.1,::1,10.200.0.1
NODE_USE_ENV_PROXY=1
```

Hermes `execute_code` runtime does **not** include these vars in `os.environ`. So when `SpendApprovalHandler` builds `env = {**os.environ}` and passes it to `subprocess.run`, the resulting `link-cli` subprocess cannot route to `api.link.com` and returns the opaque UNKNOWN error.

**Confirmed repro** inside `execute_code`:
- Without proxy vars → rc=1, `UNKNOWN`
- With proxy vars injected into env → rc=0, valid `lsrq_*`

---

## 3. Additional bugs found (pre-existing, not proxy-related)

### Bug A — `_get_request` drops fields on `hold/queued` reconstruction

`spend_handler.py` line 172-174 hardcodes `payment_method_id=None`, `justification=""`, `credential_type="card"`. The `review/queued` branch (line 158-160) correctly reads them from `details`. After `handle_review_approve`, the next log entry is `hold/queued`, so reconstruction loses these fields.

### Bug B — `_log_decision` writes `spend_id=None`

No guard at line 791. First bad test attempt wrote `{"action_id":"spend-review-None","spend_id":null,...}` to `decisions.log`. `_recover_and_resume_polling` guards on read but write side is unguarded.

### Bug C — `_validate_justification` ValueError not caught

Line 430 calls `_validate_justification(request)` outside the `try` block. Bug A's blank justification would cause an unhandled `ValueError` here before reaching the subprocess.

---

## 4. Fixes (all in `milimo-core/src/milimo_core/finance/spend_handler.py`)

### Fix 1 (P0) — `_build_link_cli_env` proxy propagation + `_discover_proxy_env` fallback

New/updated methods to replace the inline env-building in `handle_hold_release` (lines 509–524) and `_poll_spend_request` (lines 912–924):

```python
def _build_link_cli_env(self, operator_id: str | None = None) -> dict[str, str]:
    env: dict[str, str] = {
        **os.environ,
        "NODE_USE_ENV_PROXY": os.environ.get("NODE_USE_ENV_PROXY", "1"),
    }

    proxy_vars = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
                  "http_proxy", "https_proxy", "no_proxy")
    for var in proxy_vars:
        value = env.get(var) or os.environ.get(var)
        if value:
            env[var] = value

    if not any(env.get(v) for v in proxy_vars):
        fallback = self._discover_proxy_env()
        env.update(fallback)
        if fallback:
            env["NODE_USE_ENV_PROXY"] = "1"

    if operator_id:
        safe_op_id = "".join(c for c in operator_id if c.isalnum() or c in ("-", "_")).strip()
        if safe_op_id and safe_op_id not in ("system", "operator", "sandbox"):
            base = "/sandbox/.config" if os.path.exists("/sandbox") else os.path.expanduser("~/.config")
            env["XDG_CONFIG_HOME"] = f"{base}/users/{safe_op_id}"
        else:
            if os.path.exists("/sandbox/.config"):
                env["XDG_CONFIG_HOME"] = "/sandbox/.config"
    else:
        if os.path.exists("/sandbox/.config"):
            env["XDG_CONFIG_HOME"] = "/sandbox/.config"
    return env

def _discover_proxy_env(self) -> dict[str, str]:
    result: dict[str, str] = {}
    PROXY_KEYS = frozenset({
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "no_proxy",
        "NODE_USE_ENV_PROXY",
    })

    # 1. /etc/environment
    env_file = Path("/etc/environment")
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            key, _, val = line.strip().partition("=")
            if key.strip() in PROXY_KEYS:
                result[key.strip()] = val.strip().strip("\"'")

    # 2. /etc/environment.d/*.conf
    for conf in Path("/etc/environment.d").glob("*.conf"):
        for line in conf.read_text().splitlines():
            key, _, val = line.strip().partition("=")
            if key.strip() in PROXY_KEYS:
                result[key.strip()] = val.strip().strip("\"'")

    # 3. ~/.config/environment.d/*.conf
    for conf in (Path.home() / ".config" / "environment.d").glob("*.conf"):
        for line in conf.read_text().splitlines():
            key, _, val = line.strip().partition("=")
            if key.strip() in PROXY_KEYS:
                result[key.strip()] = val.strip().strip("\"'")

    # 4. /sandbox/.config/milimo/proxy.env
    milimo_proxy = Path("/sandbox/.config/milimo/proxy.env")
    if milimo_proxy.is_file():
        for line in milimo_proxy.read_text().splitlines():
            key, _, val = line.strip().partition("=")
            if key.strip() in PROXY_KEYS:
                result[key.strip()] = val.strip().strip("\"'")

    # 5. /proc/<pid>/environ
    for entry in Path("/proc").iterdir():
        if not entry.is_dir() or not entry.name.isdigit():
            continue
        environ_file = entry / "environ"
        if not environ_file.is_file():
            continue
        for token in environ_file.read_bytes().decode("utf-8", errors="replace").split("\x00"):
            if "=" not in token:
                continue
            key, _, val = token.partition("=")
            if key in result:
                continue
            if key in PROXY_KEYS and val:
                result[key] = val
        if all(k in result for k in ("HTTP_PROXY", "HTTPS_PROXY")) or \
           ("http_proxy" in result and "https_proxy" in result):
            break
    return result
```

Then:
```python
# handle_hold_release line 522:
env = self._build_link_cli_env(operator_id)

# _poll_spend_request line 1111:
env = self._build_link_cli_env(operator_id)
```

### Fix 2 (P1) — `_get_request` hold/queued reconstruction (line 172-174)

```python
# OLD:
justification="",
payment_method_id=None,
credential_type="card",

# NEW:
justification=details.get("justification", ""),
payment_method_id=details.get("payment_method_id"),
credential_type=details.get("credential_type", "card"),
```

### Fix 3 (P1) — `_log_decision` guard (line 791)

```python
def _log_decision(self, decision: dict) -> None:
    import fcntl
    import os

    spend_id = decision.get("spend_id")
    if not spend_id:
        logger.warning(
            "_log_decision: refusing to write entry without spend_id; "
            "action_id=%s stage=%s action_type=%s",
            decision.get("action_id"),
            decision.get("stage"),
            decision.get("action_type"),
        )
        return
    ...
```

### Fix 4 (P1) — ValueError catch in `handle_hold_release` (line 430)

```python
try:
    _validate_justification(request)
except ValueError as ve:
    request.status = "blocked"
    self._log_decision({...details: {"outcome": "invalid_justification", "error": str(ve)}})
    return request
```

---

## 5. Repro steps for developers

```python
python3 -c "
from milimo_core.finance.spend_handler import SpendApprovalHandler, SpendRequest
from milimo_core.finance.finance_init import FinanceOperationalLog
from pathlib import Path

handler = SpendApprovalHandler(
    operational_log=FinanceOperationalLog(Path('/tmp/ops.log')),
    decisions_path=Path('/tmp/dec.log'),
    spend_log_path=Path('/tmp/spend.log'),
    test_mode=True,
)
req = SpendRequest(
    spend_id='test-001', claw='finance',
    merchant_name='Vercel', merchant_url='https://vercel.com',
    amount_cents=2000, currency='USD',
    justification='x' * 300,
    payment_method_id='csmrpd_...',
    credential_type='card',
)
handler.queue_spend_review(req)
handler.handle_review_approve('spend-review-test-001')
result = handler.handle_hold_release('spend-hold-test-001', operator_id='system')
print('status:', result.status, 'lsrq:', result.link_spend_request_id)
"
```

Before Fix 1 (`3f9ea89`): `status: blocked`, `lsrq: None`
After Fix 1 (`3f9ea89` + `91388df`): `status: released`, `lsrq: lsrq_*` even when `os.environ` lacks proxy vars, because `_discover_proxy_env()` recovers them from system config and `/proc`

---

## 6. Related

- [[spend-handler]] — main handler documentation
- [[link-cli-setup]] — link-cli config, `UNKNOWN` error section
- [[test-spend-flow]] — automated tests for handler paths
- [[sandbox-isolation]] — why proxy vars are absent in execute_code
- [[network-egress]] — proxy and policy configuration
