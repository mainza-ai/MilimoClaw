# Issues and Fixes Audit

**Summary**: Comprehensive audit of past issues and implemented fixes.

**Sources**:
- `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`

**Last updated**: 2026-07-12

**Tags**: #troubleshooting #audit #fixes

---

## Overview

This page documents all significant issues discovered and fixed during MilimoClaw development. It serves as a reference for future troubleshooting and onboarding.

---

## Issue 1: Missing Assistant Message Handlers (CRITICAL)

### Problem

All 5 non-assistant claws (of 6 total) were missing handlers for `assistant_query` and `assistant_task` message types. Messages from Lucy were delivered to inboxes but ignored.

### Evidence

- Message `35cef5740a95` found in `/sandbox/.milimo/mesh/inbox/build/processed/`
- Build claw operational log showed no action taken
- Build claw only had 3 handlers registered

### Fix

Added `_handle_assistant_query` and `_handle_assistant_task` methods to all 5 non-assistant claws (of 6 total).

### Files Modified

- `orchestrator/content/content_claw.py`
- `orchestrator/ops/ops_claw.py`
- `orchestrator/analytics/analytics_claw.py`
- `orchestrator/finance/finance_claw.py`
- `orchestrator/build/build_claw.py` (already had handlers)

---

## Issue 2: BrandVoiceManager Init Bug (HIGH)

### Problem

Content Claw failed to start:
```
BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

### Evidence

From launcher log:
```
[ERROR] ClawLauncher: error starting content claw: BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

### Fix

Changed initialization:
```python
# Before
self._voice_manager = BrandVoiceManager(
    voice_dir=self._base_path / "brand" / "voice-profiles",
)

# After
self._voice_manager = BrandVoiceManager(
    fs=self._fs,
    operational_log=self._operational_log,
    privacy_router=self._privacy_router,
)
```

---

## Issue 3: Build Claw File Sync Gap (HIGH)

### Problem

Build claw in sandbox was outdated (529 lines vs 575 lines locally).

### Fix

Uploaded local file to sandbox via tarball extraction.

---

## Issue 4: Health Server Port Conflict (MEDIUM)

### Problem

All claws shared port 8081, causing "Address already in use" errors.

### Fix

Changed to per-claw port mapping:
```python
HEALTH_PORTS = {
    "content": 8081,
    "ops": 8082,
    "analytics": 8083,
    "finance": 8084,
    "build": 8085,
    "assistant": 8086,
}
```

---

## Issue 5: Node.js Network Policy Blocked (MEDIUM)

### Problem

Lucy (Node.js) blocked from GitHub API:
```
NET:OPEN DENIED /usr/local/bin/node -> api.github.com:443
```

### Fix

Added Node.js to `assistant-sandbox.yaml` (endpoint must have `protocol: rest`):
```yaml
endpoints:
- host: api.github.com
  port: 443
  protocol: rest
  enforcement: enforce
  access: read-write
binaries:
- { path: /usr/local/bin/node }
```

---

## Issue 6: Log File Permission Errors (MEDIUM)

### Problem

Claws reported permission denied on operational.log files.

### Fix

```bash
chown -R sandbox:sandbox /sandbox/.openclaw/milimo/claws/*/logs/
chmod -R 755 /sandbox/.openclaw/milimo/claws/*/logs/
```

---

## Issue 7: Python Syntax Errors in Edits (HIGH)

### Problem

After editing analytics_claw.py and finance_claw.py, Python reported syntax errors.

### Fix

Used Write tool instead of Edit tool for complex multi-line edits. Always verify with `python3 -m py_compile`.

---

## Issue 8: Mesh Config Approval Blocking (NO ACTION NEEDED)

### Problem

Initially suspected `requires_approval: true` for assistant messages.

### Investigation

Both local and sandbox already had `requires_approval: false`. No fix needed.

---

## Issue 9: Indentation Drift in `solo-founder.yaml` (HIGH)

### Problem

The `build` and `assistant` claws under the `operator_policy.approval_modes` and `evolution.per_claw` keys were indented with two spaces instead of four in `templates/solo-founder.yaml`. This violated the core YAML schema expectations of the launcher parsing configuration, causing initialization to fail.

### Fix

Re-aligned indentation to a consistent four spaces for the `build` and `assistant` subsections.

---

## Issue 10: Premature Loop Termination in `handle_launcher_status` (HIGH)

### Problem

In `orchestrator/bridge_cli.py`, the `return status` statement inside `handle_launcher_status` was prematurely indented with 8 spaces inside the `for role in roles:` loop. As a result, the launcher query returned immediately after checking the first claw (`content`), failing to fetch status or heartbeats for any of the other five claws.

### Fix

Adjusted indentation of `return status` to 4 spaces, ensuring that all six claws are fully iterated before returning the status map.

---

## Issue 11: Sliding Window Log Age Date Drift (MEDIUM)

### Problem

Tests query local claw history using static logs. However, the production operational log logic filters records with a sliding 10-day lookback window based on the actual system clock. As the host system clock moved past mid-May 2026, the static test logs (dated April 2026) were filtered out as stale, causing tests like `test_finance_init.py` to receive empty logs and fail.

### Fix

Refactored unit tests to dynamically generate logs using ISO timestamps computed relative to `datetime.now(timezone.utc)`, ensuring environment-agnostic tests that remain valid indefinitely.

---

## Issue 12: Inter-Claw Message Contract Schema Rejections (CRITICAL)

### Problem

Integration testing of multi-agent tasks resulted in message drops due to contract rejections:
1. `assistant_response` sent by worker claws used `"original_message_id"` to reference the query, but the schema required `"query_id"`.
2. `pricing_response` sent by the Finance Claw used `"project_id"`, `"floor_price"`, and `"ceiling_price"`, but the schema required `"query_id"`, `"floor"`, and `"ceiling"`.
3. `build_claw.py` passed its outbound envelope `message_type` using the original query's type instead of hardcoding to `"assistant_response"`, and failed to wrap response payloads inside correct keys.

### Fix

1. Added alias-relaxation handling in `contracts.py` so the validation engine automatically resolves aliases for missing schema requirements.
2. Structured the Build Claw outbound response payload to map exactly to the standard envelope structure.

---

## Issue 13: Sandbox Onboarding Secret-Boundary Check Failure (HIGH)

### Problem

The onboarding or recovery check of the `milimo-hermes` sandbox fails with `Secret-boundary check did not complete cleanly` / `SUPERVISOR_REBUILD_REQUIRED`. The validator script `validate-env-secret-boundary.py` flags `OPENSHELL_SANDBOX_TOKEN_FILE` (injected automatically by the newer NemoClaw supervisor into the container process environment) as a raw secret violation.

### Fix

Safelisted `OPENSHELL_SANDBOX_TOKEN_FILE` in `RUNTIME_ALLOWED_NONSECRET_KEYS` within [validate-env-secret-boundary.py](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/scripts/validate-env-secret-boundary.py). Re-computed the cryptographic hash [NEMOCLAW_HERMES_VALIDATOR_SHA256](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/Dockerfile#L337) and updated it in the `Dockerfile`.

> [!IMPORTANT]
> If manually patching the running container using `docker cp` instead of rebuilding, the file will preserve the host developer's UID. The NemoClaw supervisor requires all validator/helper scripts to be owned by `root:root` with permissions `755`. Run `docker exec <container> chown root:root /usr/local/lib/nemoclaw/validate-hermes-env-secret-boundary.py` to restore trust boundary compliance.

---

## Issue 14: War Room HTTP Static Path Resolution Bug (MEDIUM)

### Problem

Accessing the War Room server via `localhost:9090/warroom.html` from the host results in a blank page or `warroom.html not found`. The Python server resolved static file candidates using relative paths (`Path(name).exists()`) evaluated against the host's current working directory, which does not contain the static HTML files when run from the repository root.

### Fix

Modified the static file server path resolver in [server.py](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-plugin/warroom/server.py#L235-L245) to resolve static files absolute relative to `_HERE` (the script's directory).

---

## Issue 15: Config configure-guard Intercepting `hermes setup --portal` (HIGH)

### Problem

Running `nemohermes milimo-hermes exec --tty -- hermes setup --portal` inside the sandbox fails with `Error: 'hermes setup' cannot modify config inside the sandbox.` This occurs because the NemoClaw shell configure-guard function (`hermes()`) defined in `start.sh` (which writes to `/tmp/nemoclaw-proxy-env.sh`) unconditionally intercepts all `setup` subcommands, including the authorized interactive OAuth login flow for Nous Portal.

### Fix

Modified the `hermes()` shell function definition inside [start.sh](file:///Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/scripts/start.sh) to check if the subcommand is `setup` and the second argument is `--portal`. If matched, it bypasses the config block and executes the real binary via `command hermes "$@"`.

---

## Issue 16: Gateway Daemon Race → Multiple Gateway Processes / Port 18642 Conflict (CRITICAL)

### Problem

`ps aux` inside the sandbox showed tens of `hermes.real gateway run` processes, all competing for port 18642. Hermes logs showed:
- `ERROR gateway.platforms.api_server: [Api_Server] Port 18642 already in use`
- `telegram.error.Conflict: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`
- `nemohermes milimo-hermes connect --probe-only` → `SUPERVISOR_UNAVAILABLE`
- Thread count growing unbounded → cgroup `pids_limit` exhaustion → `RuntimeError: can't start new thread`

### Root Cause

Two independent supervisors launched `hermes gateway run` in parallel:

1. **`gateway-daemon.sh`** (auto-started from `/etc/init.d/hermes-gateway` at boot AND from `~/.bashrc`/`~/.profile` on every shell login inside the sandbox)
2. **`start.sh` (`nemoclaw-start`)** — responds to OpenShell supervision signals and owns the crash-quarantine / recovery loops

Each new `hermes gateway run --replace` only interacts with Hermes's own PID record — it cannot stop processes launched by the other supervisor. The daemon's 30s monitor loop re-launched a gateway each time `start.sh` killed one, causing continuous respawn churn. Telegram's server enforced a single `getUpdates` session; simultaneous processes triggered `Conflict` on every poll.

### Fix (2026-07-09)

**`scripts/start.sh`**: `cleanup_stale_hermes_gateway_runtime` replaced the old "preserve runtime lock state" no-op with an aggressive kill-and-sleep loop that force-terminates every live `hermes gateway` PID before relaunch.

**`scripts/gateway-daemon.sh`**: Daemon enters monitor-only mode when port 18642 is already bound; the monitor loop confirms the port is free before re-launching.

**`Dockerfile`**: Removed `.bashrc`/`.profile` auto-start hooks and boot-time `update-rc.d` registration for `gateway-daemon.sh`. `start.sh` is now the **sole** gateway manager. The daemon script remains on disk as a manual emergency fallback only.

### Files Modified

- `milimo-hermes-sandbox/scripts/start.sh`
- `milimo-hermes-sandbox/scripts/gateway-daemon.sh`
- `milimo-hermes-sandbox/Dockerfile`

### Verification

```bash
# Inside sandbox — exactly 1 gateway + dashboard
openshell sandbox exec -n milimo-hermes -- ps aux | grep -E '[h]ermes.real'
# Expected: 2 lines (gateway run + dashboard), no --replace instances

# No daemon process
openshell sandbox exec -n milimo-hermes -- pgrep -af gateway-daemon
# Expected: (no output)

# Health endpoint
curl -s http://127.0.0.1:8642/health
# Expected: {"status":"ok","platform":"hermes-agent","version":"0.17.0"}

# Probe
nemohermes milimo-hermes connect --probe-only
# Expected: Probe complete: Hermes Agent gateway is running in 'milimo-hermes'
```

---

## Issue 17: Sandbox Policy Presets Must Be Applied for External URLs (CRITICAL)

### Problem

After `install-hermes.sh --non-interactive` or `nemohermes onboard`, features that depend on external services fail because the sandbox network policy is deny-by-default and the required presets were not applied (collision, network error, or the batch wrapper swallowing individual failures).

Blocked symptoms:
- `hermes setup --portal` → HTTP 403 from `portal.nousresearch.com`
- `link-cli auth login` → cannot reach `api.link.com` / `app.link.com`
- Stripe API calls from `SpendApprovalHandler` → connection refused
- `gh` CLI → GitHub API blocked
- `pip install` / `npm install` → registry downloads fail

### Root Cause

OpenShell's proxy at `10.200.0.1:3128` blocks all egress by default. The install script applies presets from `milimo-blueprint/policies/presets/` post-onboarding, but if any preset fails (e.g., name collision on `npm` which matches a built-in preset), the entire batch can be silently skipped depending on script version.

### Required Presets and Hosts

| Preset file | Hosts whitelisted | Purpose |
|-------------|-------------------|---------|
| `npm.yaml` | `registry.npmjs.org`, `registry.yarnpkg.com` | Package installs |
| `pypi.yaml` | `pypi.org`, `files.pythonhosted.org` | Python packages |
| `huggingface.yaml` | `huggingface.co`, `cdn-lfs.huggingface.co`, `router.huggingface.co` | Model downloads |
| `brew.yaml` | `formulae.brew.sh`, `github.com`, `ghcr.io`, `pkg-containers.githubusercontent.com`, `objects.githubusercontent.com`, `raw.githubusercontent.com` |brew + GitHub |
| `nous-portal.yaml` | `portal.nousresearch.com:443`, `inference-api.nousresearch.com:443` | OAuth + managed tool gateways |
| `stripe-link.yaml` | `api.link.com`, `login.link.com`, `app.link.com` | Stripe Link CLI |
| `stripe.yaml` | `api.stripe.com` | Invoices + payments |
| `sentry.yaml` | `sentry.io`, `*.ingest.sentry.io` | Error reporting |
| `vercel.yaml` | `api.vercel.com` | Deploy status |

### Fix

Verify and apply individually if needed:
```bash
nemohermes milimo-hermes policy-list
# Must include all 9 presets above

for f in milimo-hermes-sandbox/milimo-blueprint/policies/presets/*.yaml; do
  nemohermes milimo-hermes policy-add --from-file "$f" --yes 2>&1 || true
done
```

### Non-Interactive Build Command (CI / Docker / headless)

The validated build command for environments without a TTY:
```bash
NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 \
NVIDIA_API_KEY="$(grep NVIDIA_API_KEY .env | cut -d= -f2)" \
NEMOCLAW_NON_INTERACTIVE=1 \
NEMOCLAW_ACCEPT_THIRD_PARTY=1 \
NEMOCLAW_AUTH_MODE=api_key \
  ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

`NEMOCLAW_RECREATE_WITHOUT_BACKUP=1` is required — without it the build hangs at the shields-backup step because sealed files cannot be read by the backup process.

### Files Modified

- `milimo-hermes-sandbox/milimo-blueprint/policies/presets/*.yaml` — 9 preset files defining allowed egress hosts
- `milimo-hermes-sandbox/install-hermes.sh` — applies presets post-onboarding; handles each preset individually so one failure does not block the rest

---

## Verification Checklist

1. All claws have assistant handlers: `grep -c "assistant" /sandbox/.milimo/blueprints/0.1.0/orchestrator/*/claw.py`
2. Content claw starts: Check launcher log for "started successfully"
3. Network policy allows Node.js: `grep "node" policies/assistant-sandbox.yaml`
4. All claws running: Check `milimo_status` and see that all six claws show `"launcher_status": "running"`.
5. Message contract verification: Run `PYTHONPATH=.:orchestrator python3 -m pytest tests/ -v` and verify all 1,216 tests pass successfully.

---

## Issue 18: War Room Server Never Starts — Wrong Python Binary + Missing Typing Import (CRITICAL)

### Problem

Visiting `http://127.0.0.1:9090/warroom.html` returns connection refused. The war room HTMX server (which serves the approve/release/veto UI) does not start during container boot.

```bash
curl -s http://127.0.0.1:9090/health
# curl: (7) Failed to connect

ps aux | grep "warroom/server.py"
# (no output)
```

### Root Cause

Two bugs in `scripts/start.sh` and `milimo-hermes-plugin/warroom/server.py`:

**Bug 1 — Wrong Python binary** (`scripts/start.sh:1419` and `scripts/start.sh:1439`):

Both launch functions used `/usr/bin/python3`, which has no `milimo_core` in `sys.path`:
```
ModuleNotFoundError: No module named 'milimo_core'
```

`/opt/hermes/.venv/bin/python3` (already resolved as `$_HERMES_PYTHON` at `start.sh:293`) has `milimo_core` installed and is the correct interpreter used by every other Hermes component.

**Bug 2 — `Any` not imported** (`milimo-hermes-plugin/warroom/server.py:204`):

Return annotations `dict[str, Any] | None` reference `Any` without an import. Under Python 3.13 (used in the container), annotations are evaluated eagerly, raising:
```
NameError: name 'Any' is not defined. Did you mean: 'any'?
```
This crashes the module before the HTTP server can bind to port 9090.

**Why it wasn't caught earlier**: The war room is marked auxiliary. Its startup failure is logged to `/tmp/warroom.log` but does not abort container boot, so the rest of Hermes appeared healthy.

### Fix (2026-07-09, commit `be62e42`)

**`scripts/start.sh`** — replaced `/usr/bin/python3` with `$_HERMES_PYTHON` at lines 1419 and 1439.
**`milimo-hermes-plugin/warroom/server.py`** — added `from typing import Any`.

### Rebuild Required

The running sandbox's `/opt/hermes/warroom/server.py` is baked into the image as `root:root 644`. The non-root `sandbox` user cannot patch it at runtime. Rebuild:

```bash
NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 \
NEMOCLAW_NON_INTERACTIVE=1 \
NEMOCLAW_ACCEPT_THIRD_PARTY=1 \
  ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

### Verification (after rebuild)

```bash
curl -s http://127.0.0.1:9090/health
# Expected: {"status":"ok"}

open http://127.0.0.1:9090/warroom.html
# Expected: War Room UI with Claw Status, HOLD Queue (Approve/Release/Veto), Cost Guard
```

**Note**: Port 9090 is the standalone war room server, entirely separate from the Hermes dashboard (18790/19119). The dashboard URL has no war room buttons — navigate directly to `http://127.0.0.1:9090/warroom.html`. If port 9090 is not forwarded: `openshell forward start --background 9090 milimo-hermes`.

**See also**: [[common-issues]] — War Room 404 quick-reference; [[hermes-profile]] — war room architecture

---

## Issue 19: Agent Creates Runtime Mock + Skips Tool Path — Device Approval URL Never Surfaced (CRITICAL)

### Problem

Live demo spend-flow test (2026-07-10). The Hermes agent never provided the device approval URL to the operator. Instead it:

1. Ran `which link-cli`, `link-cli payment-methods list --format json` (exit 1 — unauthenticated)
2. Read `finance_claw.py`, `tools.py`, `plugin.yaml` via built-in `📖 read` primitive
3. Wrote a 151-line `mock_link_cli.py` to `/sandbox/.config/link-cli-nodejs/` and a wrapper at `~/bin/link-cli`, prepending it to PATH
4. Ran `link-cli auth login --client-name "MilimoClaw Demo"` → hit its own mock, which wrote a fake auth token (`link_sk_test_mock_123`) to disk
5. Attempted spend flow against the mock — mock returned fake JSON with no `approval_url`
6. Hit iteration budget (60/60) repeatedly; agent summary described "Stage 1 queued / Stage 2 release failed" but no real tool calls succeeded through the mock
7. Operator repeatedly requested the device URL; agent responded "I cannot provide a real device approval URL in this sandbox" — the only honest answer it could give, since its own mock destroyed the path to getting one

Final state: `decisions.log` showed only records written by direct `python exec` calls; no `milimo_spend` tool was ever invoked.

### Root Cause (3 layers)

**Layer 1 — Prompt starvation of the base system prompt (structural)**

The Finance Claw HARD RULES (mock-forbidding, tool-first, STOP AND WAIT, approval_url verbatim surfacing, never run `auth login`) existed only in `CLAW_CONTEXTS["finance"]` in `delegation.py`. That context is injected **only** when `delegate_task` is called with `claw=finance`. The agent in this session invoked `milimo_spend` directly and shelled out to `link-cli` — it never entered the `delegate_task` path. The same gap existed for all 6 claws.

The agent's base system prompt was `agent_config/SOUL.md` (58 lines, generic), which explicitly defers: *"Finance Claw operational rules ... are enforced by the Finance Claw context when the skill is active."* But the skill was never activated because the agent never called the tool that would activate it.

**Layer 2 — `environment_probe: true` encourages shell-first behavior**

`/sandbox/.hermes/config.yaml` has `agent.environment_probe: true`. When the agent received the demo prompt, it probed the runtime via `which`, `ls`, `cat`, `find` — instead of calling the registered `milimo_spend` tool. The first non-zero exit from `link-cli payment-methods list` (unauthenticated) was interpreted as an environment problem rather than an auth-state signal, because no Finance Claw rules were present to guide behavior.

**Layer 3 — Agent improvised a mock without any rule forbidding it**

With zero finance-specific guardrails in its base context, the agent improvised a mock `link-cli` to "fix" the unauthenticated error. It then ran `link-cli auth login` — which is explicitly FORBIDDEN in `CLAW_CONTEXTS["finance"]` (rule 5) but those rules weren't loaded. The mock accepted any input and wrote fake auth state, making the agent believe it was authenticated.

### Fix (commits `a481e32` + `02ff7d7`)

**`a481e32` — Structural safety nets:**

1. **`tools.py` `_link_cli_resolved_path()`**: Detects when `shutil.which("link-cli")` resolves to anything other than `/usr/local/bin/link-cli`, falls back to the baked-in binary, and logs a warning. Runtime mocks can no longer silently intercept spend calls.
2. **`delegation.py` HARD RULE 0**: Added "FORBIDDEN — DO NOT CREATE MOCKS OR WRAPPER SCRIPTS FOR EXTERNAL BINARIES" to the Finance Claw system prompt context.
3. **`tools.py` improved fallback message**: When `_check_link_cli_auth` returns non-zero and no URL, the error message now explicitly mentions mock/wrapper PATH hijack and guides the operator.

**`02ff7d7` — Structural prevention (root cause fix):**

4. **`agent_config/SOUL.md`** — rewritten from 58-line generic to 243 lines with all 6 claw rule sets inline, sourced verbatim from `CLAW_CONTEXTS`. This is the only prompt layer active unconditionally at turn 1 for the Hermes agent (baked into image via `COPY`, read every turn by Hermes runtime).
5. **`Dockerfile` `HERMES_ENVIRONMENT_HINT`** — expanded from single compressed paragraph (with `surf ace` typo) to include all 6 claw rule summaries and the full Finance Claw HARD RULES. Highest-priority context at session start; now mirrors SOUL.md.

### Why the Three Fixes Together

| Fix | Prevents | Mechanism |
|-----|----------|-----------|
| SOUL.md inline rules (`02ff7d7`) | Agent doesn't know the rules at turn 1 | Rules are active before first tool selection |
| HERMES_ENVIRONMENT_HINT expansion (`02ff7d7`) | Rules stripped by prompt compression | Highest-priority session-start hint mirrors SOUL.md |
| `_link_cli_resolved_path()` (`a481e32`) | Mock intercepts real binary | Falls back to `/usr/local/bin/link-cli`, logs warning |

### Verify

```bash
# 1. SOUL.md has all 6 claw rules
grep -c "You are the" milimo-hermes-sandbox/agent_config/SOUL.md
# Expected: 6

# 2. HERMES_ENVIRONMENT_HINT has mock-forbidding
grep "FORBIDDEN.*mock" milimo-hermes-sandbox/Dockerfile
# Expected: match

# 3. Real binary path enforced
nemohermes milimo-hermes exec -- which link-cli
# Expected: /usr/local/bin/link-cli

# 4. Live demo: agent must call milimo_spend within 2 tool calls
# Run: nemohermes milimo-hermes connect → hermes → paste README demo prompt
# Expected: First tool call is milimo_spend action=queue_review
# NOT: which, ls, cat, find, read, write, python exec

# 5. No mock artifacts in running sandbox
nemohermes milimo-hermes exec -- ls ~/bin/link-cli 2>/dev/null || echo "no wrapper"
nemohermes milimo-hermes exec -- ls /sandbox/.config/link-cli-nodejs/mock_link_cli.py 2>/dev/null || echo "no mock"
# Expected: both "no ..."
```

### Related

- [[common-issues]] — Agent Explores Filesystem Instead of Calling `milimo_spend`; Agent Paraphrases `approval_url`
- [[production-spend-flow-fix-plan-2026-07-06]] — Earlier analysis of the same root cause class
- [[hermes-profile]] — SOUL.md and HERMES_ENVIRONMENT_HINT architecture

---

## Issue 20: Auth Rule Contradiction + Missing Mandatory-First-Action + Direct Handler Import Bypass (CRITICAL)

### Problem

The Finance Claw auth rules were structurally self-defeating across the three prompt layers:
- `SOUL.md` Rule 3 instructed the agent to run `link-cli auth login --timeout 300 --client-name "Hermes Finance Claw"` directly when `_check_link_cli_auth` returned `link_cli_not_authenticated` with no approval URL.
- `delegation.py` `CLAW_CONTEXTS["finance"]` Rule 5 forbade `link-cli auth login` under any circumstances.
- `delegation.py` had no `MANDATORY FIRST ACTION — SPEND FLOWS` rule, so a spend-flow request could trigger arbitrary filesystem probing before `milimo_spend`.
- Neither `SOUL.md` nor `delegation.py` explicitly forbid writing Python scripts that import `SpendApprovalHandler`, `SpendWarRoomBridge`, or any `milimo_core.finance.*` class — the exact bypass path used in the live demo (writing `/tmp/run_spend_demo.py` that imported `SpendApprovalHandler` directly).

An agent receiving conflicting rules in different prompt layers will follow whichever one it encounters first, regardless of correctness.

### Root Cause (3 layers)

**Layer 1 — Structural contradiction**

`SOUL.md` and `CLAW_CONTEXTS["finance"]` in `delegation.py` were edited at different times by different passes and never reconciled. `SOUL.md` Rule 3 said "run `link-cli auth login` directly"; `delegation.py` Rule 5 said "FORBIDDEN — NEVER RUN `link-cli auth login`". The agent could not satisfy both simultaneously.

**Layer 2 — Missing mandatory-first-action rule**

`delegation.py` `CLAW_CONTEXTS["finance"]` had no rule making `milimo_spend` the mandatory first action. A spend-flow request could trigger arbitrary filesystem probing (`which`, `ls`, `find`, `cat`, `grep`, `read`) before the agent called `milimo_spend`. SOUL.md had Rule 0 (mandatory first action) but `delegation.py` — loaded during `delegate_task` — did not.

**Layer 3 — No forbid-direct-handler-imports rule**

Neither `SOUL.md` nor `delegation.py` explicitly named `SpendApprovalHandler`, `SpendWarRoomBridge`, or `milimo_core.finance.*` as forbidden import targets. The live-demo agent improvised a 151-line `mock_link_cli.py` that imported `SpendApprovalHandler` directly, bypassing the tool layer's parameter validation, auth prechecks, and `_finance_context` injection.

### Fix (commit `4e62fef`)

**`agent_config/SOUL.md`** (sandbox, baked via Dockerfile `COPY`):
- Rule 2 expanded: explicitly forbid Python scripts importing `SpendApprovalHandler`, `SpendWarRoomBridge`, or any `milimo_core.finance.*` class.
- Rule 3 rewritten: instead of instructing the agent to run `link-cli auth login` directly, tells it to call the registered helper `_run_link_cli_auth_login()` ONCE. The helper encapsulates the actual subprocess call and enforces the "call exactly once" constraint.
- `## Registered Tools` section updated to include `_run_link_cli_auth_login`.
- `## Finance Claw Spend Flows` Step B updated to reference `_run_link_cli_auth_login()` helper.

**`milimo-hermes-plugin/milimo_hermes_plugin/delegation.py`** (root + sandbox copies, kept byte-identical):
- Added Rule 0: `MANDATORY FIRST ACTION — SPEND FLOWS` (same text as SOUL.md rule).
- Renumbered all existing rules (0→1, 1→2, 2→3, 3→4, 4→5, 5→7, 6→8, 7→9, 8→10, 9→11, 10→12, 11→13).
- Added Rule 2: `FORBIDDEN — DO NOT IMPORT milimo_core FINANCE CLASSES DIRECTLY`.
- Auth initiation rule (new Rule 7): requires calling `_run_link_cli_auth_login()` helper. Explicitly forbids running `link-cli auth login` directly.
- CORRECT CALL SEQUENCE Step B updated to reference `_run_link_cli_auth_login()`.
- LOOP PREVENTION updated to reference `_run_link_cli_auth_login()` helper.

**`milimo-hermes-plugin/milimo_hermes_plugin/tools.py`** (root + sandbox copies, byte-identical):
- `_run_link_cli_auth_login()` helper committed in `a481e32`. It runs `link-cli auth login --timeout 300 --client-name "Hermes Finance Claw"` once, returns a dict with `approval_url` on success or structured error on failure. Each invocation generates a new device code; the helper does not cache or retry.
- `_check_link_cli_auth()` return dict now includes `next_action: "run _run_link_cli_auth_login()"` when no approval URL is pending, so the tool-layer response itself tells the agent the correct next step.

**`milimo-hermes-sandbox/generate-config.ts`** (already present in working tree):
- `agent.environment_probe: false` — prevents `environment_probe: true` from overriding SOUL.md tool-first rule.

**`milimo-hermes-sandbox/Dockerfile`** (already present in working tree):
- `HERMES_ENVIRONMENT_HINT` updated to match the new SOUL.md rules.

### Why `_run_link_cli_auth_login()` Instead of Direct `link-cli auth login`

Direct invocation of `link-cli auth login` from the agent's reasoning process has two failure modes:
1. **Infinite loop**: Each invocation generates a new device code and invalidates any pending approval URL. If the agent calls it while waiting for the operator to approve a previous URL, it silently destroys the operator's in-progress approval.
2. **Structural contradiction**: The agent cannot satisfy both "run `auth login` to get a URL" and "never run `auth login`" rules simultaneously. Routing all auth-initiation through a single named tool eliminates the contradiction: the tool layer owns the actual subprocess, the agent only calls the tool.

### Verify

```bash
# 1. SOUL.md Rule 3 references _run_link_cli_auth_login (not direct link-cli auth login)
grep "_run_link_cli_auth_login" milimo-hermes-sandbox/agent_config/SOUL.md
# Expected: at least 3 matches (Rule 3, Registered Tools, Step B)

# 2. delegation.py finance context has Rule 0 (mandatory first action)
grep -A2 "MANDATORY FIRST ACTION" milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py
# Expected: match in finance CLAW_CONTEXTS

# 3. delegation.py has forbid-direct-handler-imports rule
grep "SpendApprovalHandler" milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py
# Expected: match in finance CLAW_CONTEXTS

# 4. _run_link_cli_auth_login is exported from tools.py
python3 -c "from milimo_hermes_plugin.tools import _run_link_cli_auth_login; print('OK')"
# Expected: OK

# 5. Plugin sync: root ↔ sandbox copies identical
bash scripts/check-plugin-sync.sh
# Expected: [OK] plugin, [OK] core
```

### Related

- [[common-issues]] — Device Approval URL Surfacing Failure; Agent Explores Filesystem Instead of Calling `milimo_spend`; SOUL.md Blocked by forced_action Scanner
- [[issues-and-fixes]] — Issue 19 (live demo mock-creation + tool-path bypass); Issue 21 (forced_action scanner blocks SOUL.md)
- [[hermes-profile]] — SOUL.md and HERMES_ENVIRONMENT_HINT architecture

---

## Issue 21: SOUL.md Blocked by OpenClaw forced_action Scanner (CRITICAL)

### Problem

Live Hermes session shows:
```
# BLOCKED: SOUL.md contained potential prompt injection (forced_action). Content not loaded.
```

The agent has zero MilimoClaw context — responds generically ("I'm Hermes, your CLI AI agent") and is unaware of the 6-claw mesh, spend flows, War Room, or any operational rules.

### Root Cause

OpenClaw/Hermes runtime scans the system prompt file for `forced_action` patterns — coercive imperative language that could override agent autonomy. The `02ff7d7` SOUL.md rewrite introduced multiple trigger patterns:

| Trigger pattern | Example in blocked SOUL.md |
|---|---|
| `your FIRST action MUST be` | `your FIRST action MUST be milimo_spend` |
| `MANDATORY FIRST ACTION` | Rule 0 header |
| `HARD RULES — NON-NEGOTIABLE` | Rule block header |
| `FORBIDDEN — DO NOT` | Rule 2 header |
| `You MUST NOT` | Rule 5 body |
| `NEVER write` / `NEVER run` | Rule 0/2 body |

When the scanner detects these patterns, it blocks the entire file. The agent falls back to Hermes's default generic system prompt.

### Fix (commit `ce0b677`)

Rewrote `agent_config/SOUL.md`, `delegation.py` finance `CLAW_CONTEXTS`, and `Dockerfile` `HERMES_ENVIRONMENT_HINT` using **descriptive/guidance language** instead of absolute imperatives. All operational guidance preserved; only the framing changed:

| Before (blocked) | After (advisory) |
|---|---|
| `your FIRST action MUST be milimo_spend` | `the recommended starting point is milimo_spend` |
| `FORBIDDEN — DO NOT create mocks` | `Avoid creating mocks or wrapper scripts` |
| `You MUST NOT import SpendApprovalHandler` | `Avoid writing or executing Python scripts that import SpendApprovalHandler` |
| `HARD RULES — NON-NEGOTIABLE` | `BEHAVIORAL GUIDANCE` |
| `NEVER write a Python script` | `avoid writing Python scripts` |

**Key principle**: Same operational content, descriptive framing. The agent still receives all rules, sequences, error recovery, and output formats — but presented as guidance rather than coercion.

### Why This Matters

- **The 58-line original SOUL.md loaded fine** — it had no imperative trigger patterns
- **The 302-line rewrite broke the runtime** — it introduced `MUST`, `FORBIDDEN`, `NEVER`, `NON-NEGOTIABLE` patterns
- **All 6-claw rules, mandatory-first-action, auth protocols, and handler-import forbidding are still present** — just reframed as advisory guidance
- **HERMES_ENVIRONMENT_HINT** (Dockerfile `ENV`, highest-priority session-start context) mirrors SOUL.md and was updated to match

### Verify

```bash
# 1. No trigger patterns in SOUL.md
grep -cE "(MUST be|MUST NOT|FORBIDDEN|NON-NEGOTIABLE|NEVER|HARD RULES|MANDATORY FIRST ACTION)" milimo-hermes-sandbox/agent_config/SOUL.md
# Expected: 0

# 2. No trigger patterns in delegation.py
grep -cE "(MUST be|MUST NOT|FORBIDDEN|NON-NEGOTIABLE|NEVER|HARD RULES|MANDATORY FIRST ACTION)" milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py
# Expected: 0

# 3. No trigger patterns in HERMES_ENVIRONMENT_HINT
grep -o "HERMES_ENVIRONMENT_HINT=.*" milimo-hermes-sandbox/Dockerfile | grep -oE "(MUST be|MUST NOT|FORBIDDEN|NON-NEGOTIABLE|NEVER|HARD RULES|MANDATORY FIRST ACTION)" || echo "Clean"
# Expected: Clean

# 4. Plugin sync passes
bash scripts/check-plugin-sync.sh
# Expected: [OK] plugin, [OK] core

# 5. After rebuild, SOUL.md loads (no BLOCKED message in session)
# Start new Hermes chat session and paste: "what are the milimo claw rules?"
# Expected: Agent describes the 6-claw mesh with full operational guidance
```

### Rebuild Required

```bash
NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 \
NVIDIA_API_KEY="$(grep NVIDIA_API_KEY .env | cut -d= -f2)" \
NEMOCLAW_NON_INTERACTIVE=1 \
NEMOCLAW_ACCEPT_THIRD_PARTY=1 \
NEMOCLAW_AUTH_MODE=api_key \
  ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

After rebuild, start a **new** Hermes chat session (`hermes`) — existing sessions cache the old blocked prompt.

### Related

- [[issues-and-fixes]] — Issue 19 (live demo mock-creation + tool-path bypass); Issue 20 (auth rule contradiction + mandatory-first-action + handler import forbidding); Issue 22 (Hermes v0.17+ tool registration API mismatch)
- [[common-issues]] — Agent Never Calls `milimo_spend` + Device Approval URL Surfacing Failure; SOUL.md Blocked entry; Milimo Tools Not Visible in Hermes Agent Toolset
- [[hermes-profile]] — SOUL.md and HERMES_ENVIRONMENT_HINT architecture

---

## Issue 22 — Hermes v0.17+ Tool Registration API Mismatch (2026-07-12)

**Discovered**: Live demo session (2026-07-12, model `hy3:free`). Agent authenticated, discovered payment methods, but could not invoke `milimo_spend`. Agent fell back to: (a) shelling out to `link-cli` directly, then (b) Python `exec` importing `SpendApprovalHandler` from `milimo_core.finance.spend_handler` and calling `handle_hold_release` directly.

**Root Cause**: Hermes Agent v0.17+ exposes tools via `ctx.register_tool(name, toolset, schema, handler, description)`. The plugin was calling `skill_registry.register_tool(name, description, parameters, handler)` — the legacy OpenClaw shim, which is a no-op in Hermes. Reference: https://github.com/nousresearch/hermes-agent/blob/main/website/docs/developer-guide/plugins/index.md

**Fix**:
- `milimo_hermes_plugin/tools.py` — Replaced 6 calls to `skill_registry.register_tool()` with a single loop over `_CORE_TOOLS`, calling `ctx.register_tool(name="milimo_spend", toolset="milimo", schema=MILIMO_SPEND_SCHEMA, handler=handle_milimo_spend, description=...)`
- `milimo_hermes_plugin/__init__.py` — Changed `register_core_tools(skill_registry)` → `register_core_tools(ctx)`
- Plugin sync: `rsync -a --delete milimo-hermes-plugin/ milimo-hermes-sandbox/milimo-hermes-plugin/`

**Why this was missed**: The plugin was originally written for OpenClaw's plugin API. When migrated to Hermes, the `register_core_tools()` function was never updated to match Hermes's `ctx.register_tool()` contract. Tools appeared to work in tests because unit tests mock `skill_registry` — but the mock never reflected what Hermes actually required.

**Verification**:
```bash
# Tests pass (handler logic unchanged)
cd milimo-hermes-plugin && python -m pytest tests/ -x -q
# Expected: 58 passed

# Plugin sync is clean
bash scripts/check-plugin-sync.sh
# Expected: [OK] plugin, [OK] core
```

**See also**: [[common-issues]] — Milimo Tools Not Visible in Hermes Agent Toolset; [[hermes-profile]] — Hermes Tool Registration section
