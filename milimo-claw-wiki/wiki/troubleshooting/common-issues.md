# Common Issues

**Summary**: Frequently encountered problems and their solutions.

**Sources**:
- `milimo-claw-docs/troubleshooting/ISSUES_AND_FIXES_AUDIT.md`

**Last updated**: 2026-07-25

**Tags**: #troubleshooting #issues #fixes

---

## Cross-Claw Issues

### weekly-intelligence.json Unreadable

**Symptom**: Analytics report not accessible by other claws.

**Cause**: Missing shared mount in claw's sandbox policy.

**Fix**: Add entry to `policies/{role}-sandbox.yaml`:
```yaml
filesystem_policy:
  read_only:
    - /sandbox/.openclaw/milimo/claws/analytics/reports
```

Run: `pytest -m phase_a`

---

### project_brief Before pricing_response

**Symptom**: Brief sent without pricing.

**Cause**: Rule 1 violated — sequencing not enforced.

**Fix**: Check `intake_manager.py` — verify pricing awaited before brief.

---

### Invoice Sent at Stage 1 REVIEW

**Symptom**: Invoice transmitted on REVIEW approval.

**Cause**: Rule 2 violated — critical bug.

**Fix**: Check `finance/approval_handler.py` — ensure two-stage separation.

---

### PR Merged at REVIEW Approve

**Symptom**: PR merged without HOLD release.

**Cause**: Rule 3 violated — critical bug.

**Fix**: Check `build/approval_handler.py` — ensure two-stage separation.

---

## Content Claw Issues

### BrandVoiceManager Init Error

**Symptom**:
```
BrandVoiceManager.__init__() got an unexpected keyword argument 'voice_dir'
```

**Cause**: Wrong parameters passed to BrandVoiceManager.

**Fix**: Pass correct parameters:
```python
self._voice_manager = BrandVoiceManager(
    fs=self._fs,
    operational_log=self._operational_log,
    privacy_router=self._privacy_router,
)
```

---

### Draft Not in War Room

**Symptom**: Draft generated but not appearing in War Room.

**Cause**: `draft_ready` message not sent.

**Fix**: Verify Content Claw sends `draft_ready` after generation.

---

## Ops Claw Issues

### Welcome Sent Without Approval

**Symptom**: Client welcome sent automatically.

**Cause**: REVIEW mode misconfigured.

**Fix**: Check approval thresholds in `solo-founder.yaml`.

---

### Deadline Critical is REVIEW not HOLD

**Symptom**: 24-hour deadline shows as REVIEW.

**Cause**: `check_all_deadlines()` not setting HOLD at ≤1 day.

**Fix**: Update deadline checker to use HOLD for critical deadlines.

---

## Analytics Claw Issues

### Query Response > 2 Minutes

**Symptom**: Analytics response exceeds SLA.

**Cause**: SLA not measured in `query_handler.handle()`.

**Fix**: Add timing to query handler, log violations.

---

### No Mid-Week Opportunity Dispatch

**Symptom**: High-confidence opportunities not sent mid-week.

**Cause**: Confidence threshold check not in `opportunity_scorer`.

**Fix**: Verify opportunity scorer dispatches at >0.85 confidence.

---

## Finance Claw Issues

### revenue_summary Has Client Names

**Symptom**: Revenue summary contains identifying information.

**Cause**: Privacy leak — totals only allowed.

**Fix**: Ensure `revenue_summary` only includes aggregate totals.

---

### Overdue Not Firing

**Symptom**: Payment overdue alerts not triggering.

**Cause**: `payment_monitor` schedule not initialized.

**Fix**: Verify FinanceScheduler initializes payment monitor.

---

## Build Claw Issues

### Sprint Plan Blocked on Analytics

**Symptom**: Sprint planning waits indefinitely for Analytics.

**Cause**: 5-min timeout not implemented.

**Fix**: Add `ANALYTICS_WAIT_SECONDS` timeout in `issue_manager.py`.

---

### Deploy Auto-Triggers on PR Merge

**Symptom**: Deployment starts without HOLD release.

**Cause**: Deploy HOLD missing.

**Fix**: Ensure `deploy_manager.py` has separate HOLD queue.

---

## Assistant (Lucy) Issues

### Bridge CLI ImportError on send_to_claw (FIXED)

**Symptom**:
```
ModuleNotFoundError: No module named 'milimo_paths'
ImportError: attempted relative import with no known parent package
```

**Cause** (before 2026-05-06 fix): `bridge_cli.py` used bare `import milimo_paths` and relative `from .contracts import ...` imports. These fail when the script is executed directly (`python3 path/to/bridge_cli.py`) because Python cannot resolve relative imports without a package context, and bare imports only work if CWD happens to be `orchestrator/`.

**Fix** (2026-05-06):
- Converted all 22 relative imports to absolute: `from orchestrator.contracts import ...`
- Converted all 26 `milimo_paths.X` references to direct imports
- Added `PYTHONPATH: options.blueprintDir` to spawn env in `python-bridge.ts`

**See also**: [[bridge-cli]] — Import architecture documentation

---

### mesh_config.yaml message_matrix Parsed as None (FIXED)

**Symptom**:
```
AttributeError: 'NoneType' object has no attribute 'get'
```
at `contracts.py:669` in `ContractValidator.validate()`.

**Cause** (before 2026-05-06 fix): The `message_matrix` sub-keys (`content:`, `ops:`, etc.) were at YAML root level instead of indented under `message_matrix:`. PyYAML parsed the key as `message_matrix: null`, causing `self._matrix` to be `None` in `ContractValidator.__init__`.

**Fix** (2026-05-06): Indented all message_matrix sub-keys with 2 spaces under `message_matrix:`.

**Verification**: `python3 -c "import yaml; d=yaml.safe_load(open('mesh_config.yaml')); print(type(d.get('message_matrix')))"` should return `<class 'dict'>`, not `<class 'NoneType'>`.

**See also**: [[mesh-config]] — YAML indentation note

---

### Node.js Network Policy Blocked

**Symptom**:
```
NET:OPEN DENIED /usr/local/bin/node -> api.github.com:443
```

**Cause**: Node.js not in allowed binaries.

**Fix**: Add to `assistant-sandbox.yaml` (with `protocol: rest` on the endpoint):
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

### Assistant Handlers Missing in Claws

**Symptom**: Messages to claws ignored.

**Cause**: `_handle_assistant_query` and `_handle_assistant_task` not implemented.

**Fix**: Add handlers to all claws.

---

## Plugin and Config Issues

### Plugin Not Registered After Install (FIXED)

**Symptom**: `openclaw plugins list` shows no `milimo` entry; `openclaw milimo --help` returns "unknown command".

**Cause** (before 2026-05-02 fix): Install flow transferred full plugin source to `.openclaw/extensions/milimo/` and attempted `npm install` + `npx tsc` inside the sandbox. This failed silently because: (1) sandbox network restrictions blocked npm package downloads, (2) build errors were swallowed by `|| true`, (3) staging directory was cleaned before verification could confirm install.

**Fix** (2026-05-02):
- Build TypeScript + production `node_modules` on host (`npm install --omit=dev` on host)
- Transfer only deployable artifacts: `openclaw.plugin.json`, `package.json`, `dist/`, `node_modules/`
- Stage at `/tmp/milimo-plugin-install/` (not `.openclaw/extensions/`) to avoid Landlock path restrictions
- Use `openclaw plugins install --force /tmp/milimo-plugin-install/`
- Retry with `--dangerously-force-unsafe-install` on exit code 1
- Verify: `openclaw plugins list | grep milimo` must show `loaded` before continuing
- Clean up staging dir only after successful verification

**See also**: [[installation-scripts]] — Full install flow documentation

---

### Destructive `plugins.allow` Override (FIXED)

**Symptom**: After install, all other OpenClaw plugins (telegram, github-copilot, etc.) disappear from `openclaw plugins list` or appear disabled.

**Cause**: Previous install script ran `openclaw config set plugins.allow '["milimo"]'` which sets a flat whitelist — only the listed plugins are enabled, all others are disabled.

**Fix** (2026-05-02): Removed entirely. `openclaw plugins install` already registers the plugin correctly without needing a plugins.allow override. The proper way to register a plugin is `openclaw plugins install --force <path>` — this adds the plugin to `plugins.entries` with default enabled state.

**See also**: [[openclaw-controls]] — Plugin system security controls

---

### Gateway Restart Without Health Check (FIXED)

**Symptom**: `openclaw plugins install` returns success but plugin not loaded; `openclaw milimo --help` still returns "unknown command".

**Cause**: Gateway restart (`pkill openclaw; sleep 8`) was unreliable — `sleep 8` was a blind wait that didn't confirm the gateway actually restarted. If the gateway took longer than 8s, subsequent commands ran against a gateway that hadn't fully reloaded plugins.

**Fix** (2026-05-02): `openclaw gateway restart` (graceful) followed by health check loop polling `openclaw doctor` for up to 30s until gateway is confirmed ready.

---

### acpx Plugin Config Warning (BENIGN)

**Symptom**:
```
plugins.entries.acpx: plugin disabled (bundled (disabled by default)) but config is present
```

**Cause**: `acpx` is a bundled OpenClaw plugin providing the Agent Client Protocol (ACP) runtime — used to launch external coding harnesses (Claude Code, Codex, Gemini CLI) through ACP sessions. It is disabled by default in NemoClaw sandboxes because ACP sessions run on the **host runtime, not inside the sandbox**, bypassing sandbox policy. The warning simply notes that `openclaw.json` contains an `acpx` config entry while the plugin itself is disabled.

**Impact**: None. The config is inert. ACP sessions cannot run inside NemoClaw sandboxes (`Sandboxed sessions cannot spawn ACP sessions`), so the disabled state is correct and expected.

**Fix**: No action needed. The warning is purely informational. If you want to suppress it, remove the `plugins.entries.acpx` config block from `openclaw.json` (or run `openclaw doctor --fix` which can quarantine unused plugin config). Do **not** enable `acpx` in a NemoClaw sandbox — it would not function and is flagged by `openclaw security audit` as a dangerous flag when `permissionMode=approve-all`.

**See also**: [[openclaw-controls]] — Plugin system security controls

---

### `kubectl not found in $PATH` during `--solo` deploy

**Symptom**: Running `./install.sh --solo` produces:
```
OCI runtime exec failed: exec failed: unable to start container process: exec: "kubectl": executable file not found in $PATH
```

**Cause**: `install.sh` helper functions (`sandbox_exec`, `sandbox_exec_root`, `sandbox_cp`) and direct `docker exec "$gateway" kubectl exec` calls assumed a K8s-in-Docker architecture where `kubectl` exists inside the gateway container. In `--solo` local deploy mode, the sandbox is a plain Docker container with no kubectl.

**Fix** (2026-05-15, BUG 16): Helpers now auto-detect whether `kubectl` exists inside the gateway container. If not found, they fall back to direct `docker exec "$SANDBOX_NAME"` — the correct path for `--solo` local deploy. All raw kubectl invocations replaced with helper calls.

---

### `requests` Module Not Found (Deprecated Dependency)

**Symptom**: Python import errors for `requests` module inside the sandbox.

**Cause**: The `requests` library was removed as a dependency (commit `b2741c5`). All HTTP calls now route through NemoClaw's L7 inference proxy via `httpx`.

**Fix**: Ensure no code imports `requests` directly. Use `httpx` for any HTTP calls that bypass the proxy. The `install.sh` venv setup (`pip install ... httpx ...`) includes `httpx` as a replacement.

---

## Hermes Profile Issues

### `nemohermes <name> connect` Hangs / `relay open timed out`

**Symptom**:
```
Hermes Agent gateway is not running inside the sandbox (sandbox likely restarted).
  Recovering...
  Confirming the gateway stays responsive (~25s)...
  ✓ Hermes Agent gateway restarted inside sandbox.

$ nemohermes milimo-hermes exec -- echo ok
Error: code: 'Deadline expired before operation could complete', message: "relay open timed out"
```

**Cause**: The sandbox's static auth token (baked into the Docker image at build time) has expired. Logs show:
```
RefreshSandboxToken returned Unauthenticated; static token sources cannot rebootstrap automatically source=File
```

The token is served from a static file source (`source=File`). Unlike dynamic tokens, it cannot be rotated or refreshed by the running sandbox. All SSH relay operations (`exec`, `connect`, `sessions`, `logs`) fail with `relay open timed out` because the relay rejects the expired credential before any command executes.

**Not this bug**: NemoClaw #3986 (`openshell-docker-gateway` idle-daemon death). That bug shows a stale PID file and dead `openshell-gateway` daemon. Here, PID 82731 is alive and listening on `127.0.0.1:8080`.

**Fix** (reliable): Destroy and re-onboard to bake a fresh token:
```bash
nemohermes milimo-hermes destroy --cleanup-gateway --yes
nemohermes onboard \
  --name milimo-hermes \
  --from ./milimo-hermes-sandbox/Dockerfile \
  --non-interactive \
  --yes \
  --yes-i-accept-third-party-software \
  --fresh \
  --recreate-sandbox
```

**First move when `connect` hangs**: Run `nemohermes milimo-hermes recover` first. If `recover` succeeds but `exec`/`connect` still fail with `relay open timed out`, it's token expiry — proceed to destroy + re-onboard.

**Preventive workaround** (upstream bug in NemoClaw): Expect this to recur after some idle period. The only permanent fix is NemoClaw support for automatic static-token rotation. Until then, re-onboarding replaces the expired token.

**See also**: [[hermes-profile]] — Sandbox token lifecycle

---

### Hermes Chat Asks for `sudo` Password During Spend Flow

**Symptom**: In a Hermes chat session, the agent ends blocked and shows:
```
Warning: tirith security scanner enabled but not available
Timeout — continuing without sudo
```
or prompts for a hidden sudo password before timing out.

**Root cause**: The Finance Claw spend tool wiring was missing. `register_core_tools()` only registered `milimo_status`, `milimo_warroom`, `milimo_approve`, `milimo_veto`, `delegate_task`. The capability `request_agent_spend` was declared in `finance_claw`, but no tool schema/handler was implemented. Because tool discovery failed, the agent fell back to shell filesystem inspection, hit root-owned paths under `/opt/milimo-core/src/`, and Hermes auto-escalated to `sudo`. In a non-interactive chat that prompt cannot be answered, so it timed out.

**Fix** (implemented in `tools.py`):
- Added `MILIMO_SPEND_SCHEMA` with actions: `queue_review`, `approve_review`, `block_review`, `release_hold`, `cancel_hold`, `status`
- Added `handle_milimo_spend()` wiring to `SpendApprovalHandler`
- Registered `milimo_spend` in `register_core_tools()`

After this fix, the agent can invoke the spend flow through the tool registry instead of shelling out, avoiding the sudo/filesystem-fallback path entirely.

**Verified live**: `tools.py` import resolves `MILIMO_SPEND_SCHEMA['name'] == 'milimo_spend'` inside the sandbox.

**See also**: [[hermes-skill-factory-remediation-2026-07-04]] — systemic factory/capability gap analysis affecting all 6 claws

---

### `link-cli auth login` Blocks Hermes TTY for Full Timeout

**Symptom**:
```
npx @stripe/link-cli auth login --client-name "Hermes" --interval 5 --timeout 300
# blocks for 300s; approval URL only appears after timeout or SIGINT
```

**Cause**: `auth login` is a polling command — it loops every `--interval` seconds for the full `--timeout` duration. The device-code URL is printed only on exit (timeout or SIGINT). Hermes invoked this as a subprocess in the agent TTY, stalling all subsequent steps for 300 seconds.

**Fix**:
1. Pre-flight check: run `link-cli auth status` before any spend-request subprocess.
2. If unauthenticated, return structured Hermes message with the device URL. Do NOT call `auth login` in the Hermes TTY.
3. Operator completes auth externally; agent retries `auth status` on next invocation.

**Preventive**: Add `link-cli auth login` to `install-hermes.sh` as a post-onboarding step that writes the device URL to onboarding logs. Operator auths once during setup.

---

### All 6 Claw Skill Factories Crash on Instantiation

**Symptom**: Each Hermes skill reports "mesh is not installed" when `delegate_task` tries to activate it. Hermes falls back to shell commands for every capability.

**Cause**: Every `create_*_claw` factory in `milimo-hermes-plugin/__init__.py` either omits required positional args (`squad_id`), or passes kwargs not accepted by the target `__init__` (`config`, `privacy_router`). All 6 factories raise `TypeError`.

```python
# Example — broken factory
def create_finance_claw(config=None):
    return FinanceClaw(
        inference_client=get_inference_client(),   # accepted
        privacy_router=get_privacy_router(),        # TypeError: unexpected kwarg
        config=config or {},                        # TypeError: unexpected kwarg
    )
    # squad_id missing — TypeError: missing required positional arg
```

**Fix**: Rewrite all 6 factories to pass only kwargs accepted by each `*Claw.__init__`, with explicit `squad_id` from env and protocol-shim fallbacks for `mesh_gateway`.

**See also**: [[hermes-skill-factory-remediation-2026-07-04]] — full gap analysis, sub-component map, and phased implementation plan covering all 6 claws and 45 capabilities

---

### 0 of 45 Declared Capabilities Implemented as Methods on `*Claw` Classes

**Symptom**: Even after fixing factories, `delegate_task` would fail because Hermes calls capabilities as methods on the instantiated skill object, and none of the 45 declared capabilities exist as methods on any `*Claw` class.

**Cause**: All capabilities are implemented inside sub-components (e.g., `PRManager`, `ContentGenerator`, `SpendApprovalHandler`) accessed only via properties. The `*Claw` classes have no top-level method for any declared capability.

**Fix**: Add one-line delegation methods to each `*Claw` class that forward to the corresponding sub-component property. See [[hermes-skill-factory-remediation-2026-07-04]] for exact method signatures per claw.

---

### `MILIMO_SPEND_TEST_MODE` Default Drift

**Symptom**: Test-mode behavior is unpredictable — `tools.py` defaults to `"true"`, `finance_claw.py` defaults to `"false"`.

**Fix**: Unify to `"true"` in `finance_claw.py:197` to match `tools.py:83`. Add CI test asserting both call sites read the same value.

---

### Multiple Hermes Gateway Processes / Port 18642 Conflict (FIXED 2026-07-09)

**Symptom** (inside sandbox):
```bash
# ps aux shows many hermes gateway processes
sandbox  488  ... /opt/hermes/.venv/bin/python /usr/local/bin/hermes.real gateway run
sandbox  5510 ... /opt/hermes/.venv/bin/python /usr/local/bin/hermes.real gateway run --replace
sandbox  5592 ... /opt/hermes/.venv/bin/python /usr/local/bin/hermes.real gateway run --replace
# ... tens of processes, growing every 25 s
```

Also appears as:
- `ERROR gateway.platforms.api_server: [Api_Server] Port 18642 already in use`
- `telegram.error.Conflict: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`
- Dashboard forwarding unreachable; `nemohermes ... connect --probe-only` returns `SUPERVISOR_UNAVAILABLE`

**Root cause**: Two independent supervisors raced to launch `hermes gateway run`:

1. `gateway-daemon.sh` was auto-started from `/etc/init.d/hermes-gateway` at boot AND from `~/.bashrc`/`~/.profile` on every shell login.
2. `start.sh` (`nemoclaw-start`) launched its own gateway when responding to OpenShell supervision signals.
3. Hermes v0.17's `--replace` flag only interacts with Hermes's own PID record — it cannot stop processes launched by a different supervisor.

Each pair of simultaneous gateways collided on port 18642. Telegram saw two `getUpdates` sessions. The daemon's monitor loop kept re-launching, and `start.sh`'s supervisor treated each new PID as a fresh crash, multiplying the count over time.

**Fix** (committed 2026-07-09):
- `scripts/start.sh` — `cleanup_stale_hermes_gateway_runtime` now force-kills every live `hermes gateway` PID before relaunching.
- `scripts/gateway-daemon.sh` — daemon enters monitor-only mode when port 18642 is already bound; monitor loop checks port state before re-launching.
- `Dockerfile` — removed `.bashrc`/`.profile` auto-start hooks and boot-time `update-rc.d` registration for `gateway-daemon.sh`. `start.sh` is the **sole** gateway manager.

**Verify**:
```bash
# Inside sandbox — must show exactly 1 gateway + 1 dashboard
openshell sandbox exec -n milimo-hermes -- ps aux | grep -E '[h]ermes.real'
# Expected:
# sandbox  <pid>  ... hermes.real gateway run
# sandbox  <pid>  ... hermes.real dashboard ...

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

**See also**: [[sandbox-isolation]] — cgroup `pids_limit` and `PYTHONTHREADSTACKSIZE`; [[hermes-profile]] — Hermes dashboard and API ports

---

### `nemohermes <name> recover` Fails: Stale Shields Transition Lock

**Symptom**:
```
Error: Timed out after 30000ms waiting for shields transition lock
'.../shields-transition-lock-milimo-hermes.json':
recorded owner PID 10743 is not running (gateway process recovery)
```

**Cause**: A previous `recover` or gateway-process operation crashed while holding the shields transition lock, leaving a stale JSON lock file whose recorded owner PID no longer exists.

**Fix**: Remove the stale lock file and retry:
```bash
rm ~/.nemoclaw/state/shields-transition-lock-<sandbox-name>.json
nemohermes <name> recover
```

---

## Related Pages

- [[issues-and-fixes]] — Complete audit
- [[sandbox-sync]] — Sandbox synchronization
- [[sequencing-rules]] — Rule violations

---

### Agent Explores Filesystem Instead of Calling `milimo_spend`

**Symptom**: When the operator requests a Finance Claw spend flow (e.g., "Pay Stripe invoice $49 for API credits"), the Hermes agent spends dozens of tool calls reading source files (`finance_claw.py`, `spend_handler.py`), grepping for `spend|finance|link-cli`, walking `~/.linkcli`, `~/.config/linkcli`, `/sandbox/.linkcli`, and searching for `*.token`/`*.key` files — instead of calling the registered `milimo_spend` tool directly.

**Root Cause** (fixed 2026-07-11, commit `02ff7d7`):

The Finance Claw HARD RULES (tool-first, mock-forbidding, approval_url verbatim surfacing, STOP AND WAIT, auth-check protocol, test-mode default) existed in exactly two places:

1. `CLAW_CONTEXTS["finance"]` in `milimo-hermes-plugin/delegation.py` — injected **only** when `delegate_task` is called with `claw=finance`. The agent in the failed demo invoked `milimo_spend` directly and shelled out to `link-cli`, never entering the `delegate_task` path, so these rules were never loaded.
2. `milimo_spend` tool responses — the `_finance_context` field is attached to tool responses. Same problem: the agent never called the tool.

The same gap existed for all 6 claws — their operational rules were scoped only to `CLAW_CONTEXTS` and unreachable from the agent's base system prompt at turn 1.

**Fix** (committed `02ff7d7`):

1. **`agent_config/SOUL.md`** — rewritten from 58-line generic to full 6-claw rules inline (243 lines). All HARD RULES for Build, Content, Ops, Analytics, Finance, and Lucy (Assistant) are now active from turn 1 regardless of which tool the agent calls. SOUL.md is baked into the Docker image via `COPY agent_config/SOUL.md /sandbox/.hermes/SOUL.md` and is read every turn by the Hermes runtime.
2. **`Dockerfile` `HERMES_ENVIRONMENT_HINT`** — expanded from a single compressed paragraph with only the approval_url fragment (and a `surf ace` typo) to include all 6 claw rule summaries and the full Finance Claw protocol. This is the highest-priority context at session start and now mirrors SOUL.md content.
3. **`milimo-hermes-plugin/tools.py`** — added `_link_cli_resolved_path()` (Fix 2) to detect PATH-hijack by runtime mocks/wrappers and fall back to the baked-in `/usr/local/bin/link-cli`; added forbidden-mock-creation rule to `delegation.py` system prompt (Fix 3); improved unauthenticated fallback message in `_check_link_cli_auth()` (Fix 4).

**Verify**:
```bash
# SOUL.md must contain all 6 claw rule sections
grep -c "You are the" milimo-hermes-sandbox/agent_config/SOUL.md
# Expected: 6 (Build, Content, Ops, Analytics, Finance, Lucy/Assistant)

# HERMES_ENVIRONMENT_HINT must contain mock-forbidding rule
grep "FORBIDDEN.*mock" milimo-hermes-sandbox/Dockerfile
# Expected: match

# After rebuild, agent must call milimo_spend within 2 tool calls
# Run the spend-flow demo (see README "Demo / Test Mode Spend Flow")
```

**Prevention**: After any SOUL.md or HERMES_ENVIRONMENT_HINT change, run the spend-flow blackbox scenario (see [[test-spend-flow]]). Confirm the agent calls `milimo_spend` within 2 tool calls and never reads source files.

---

### Agent Paraphrases `approval_url` Instead of Surfacing It Verbatim

**Symptom**: `_check_link_cli_auth` returns `{"error": "link_cli_not_authenticated", "approval_url": "https://app.link.com/device/setup?code=..."}`. Agent emits `"Open this URL and approve the device code in your Link app: [URL]"` — the URL is present but wrapped in prose, or the agent says "I have started a background poll" without showing the URL.

**Root Cause** (fixed 2026-07-11):

The approval-url rule was present as a HARD RULE in `CLAW_CONTEXTS["finance"]` but was never loaded into the agent's base system prompt. The agent only saw it if `delegate_task` was called with `claw=finance` — which it never was for direct spend requests. Without the rule in context, the agent treated the URL as advisory rather than a hard verbatim-surfacing requirement.

**Fix** (committed `02ff7d7`):
- `agent_config/SOUL.md` — approval_url rule is now a numbered HARD RULE in the Finance Claw section of the base system prompt (active from turn 1).
- `Dockerfile` `HERMES_ENVIRONMENT_HINT` — includes the full approval_url surfacing protocol with `CRITICAL:` emphasis.

**Verify**:
```bash
# SOUL.md must have the approval_url HARD RULE
grep -A3 "APPROVAL URL" milimo-hermes-sandbox/agent_config/SOUL.md
# Expected: "emit the EXACT URL as a plain string ... Do NOT paraphrase"

# HERMES_ENVIRONMENT_HINT must repeat it
grep "approval_url" milimo-hermes-sandbox/Dockerfile
# Expected: CRITICAL block with verbatim surfacing instructions
```

**Prevention**: The approval_url rule is now in both SOUL.md and HERMES_ENVIRONMENT_HINT — it cannot be accidentally stripped from one without also being visible in the other. CI check: grep both files for `APPROVAL URL` + `VERBATIM` wording after any prompt change.

---

### `_validate_justification` Silently Passes Short Justifications in Test Mode

**Symptom**: Operator requests a purchase with a 20-character justification (not a demo). `SpendApprovalHandler` logs it to `decisions.log` without raising `ValueError`. The spend request reaches the War Room with a malformed justification.

**Root Cause**:
```python
def _validate_justification(request: SpendRequest, test_mode: bool = False) -> None:
    if test_mode:
        return          # ← BUG: skips ≥100-char check
```
`test_mode` was conflated with "skip all validation." Test mode should only skip the real charge (the `--test` flag in `link-cli spend-request create`). The justification QA gate must always run.

**Fix**: Remove `test_mode` parameter from `_validate_justification` entirely. Always validate.

**Verify**:
```bash
grep "_validate_justification" milimo-hermes-sandbox/milimo-core/src/milimo_core/finance/spend_handler.py
```
Confirm signature is `def _validate_justification(request: SpendRequest) -> None:` with no `test_mode` branch.

---

### Agent Returns Error Instead of Auto-Discovering `payment_method_id`

**Symptom**: Operator says "Pay Stripe $49 for API credits." Agent calls `milimo_spend action=queue_review` without `payment_method_id`. Tool returns `{"error": "Missing required fields for queue_review: payment_method_id"}`. Agent has no guidance on how to discover it.

**Root Cause**: `handle_milimo_spend` has a hard error for missing fields. The Finance Claw context does not specify that `payment_method_id` must be discovered via `link-cli payment-methods list --format json` before calling `queue_review`.

**Fix** (in `tools.py`): When action is `queue_review` and `payment_method_id` is missing, run `link-cli payment-methods list --format json` and select the default. Return structured error only if no methods exist.

**Prevention**: Add `payment_method_id` discovery as an explicit Step A in `CLAW_CONTEXTS["finance"]`.

---

### Sandbox Blocks External URLs / Policy Presets Not Applied

**Symptom**: Features that depend on external services fail silently or with connection errors:
- `hermes setup --portal` → HTTP 403 from `portal.nousresearch.com`
- `link-cli auth login` → cannot reach `api.link.com` / `app.link.com`
- `SpendApprovalHandler` → Stripe API calls fail with connection refused
- `gh` CLI → GitHub API requests blocked
- `pip install` / `npm install` → registry downloads fail

**Cause**: The sandbox network policy is deny-by-default. External hosts must be explicitly whitelisted via policy presets. If `install-hermes.sh` fails to apply presets (collision, network issue, or the batch `if/then/else` swallowing individual failures), the corresponding URLs are blocked by the OpenShell proxy at `10.200.0.1:3128`.

**Fix**: Verify all presets applied:
```bash
nemohermes milimo-hermes policy-list
# Must include: npm, pypi, huggingface, brew, nous-portal, stripe-link, stripe, sentry, vercel
```

Apply individually if any are missing:
```bash
for f in milimo-hermes-sandbox/milimo-blueprint/policies/presets/*.yaml; do
  nemohermes milimo-hermes policy-add --from-file "$f" --yes 2>&1 || true
done
```

**Critical presets for production**:
| Preset | Blocked if missing |
|--------|-------------------|
| `nous-portal` | `portal.nousresearch.com:443`, `inference-api.nousresearch.com:443` — OAuth login + managed tool gateways |
| `stripe-link` | `api.link.com`, `login.link.com`, `app.link.com` — spend approval flow |
| `stripe` | `api.stripe.com` — invoice + payment monitoring |
| `npm` / `pypi` / `huggingface` | Package/model downloads blocked |

**Prevention**: After every `install-hermes.sh` or `nemohermes onboard`, run `nemohermes milimo-hermes policy-list` and grep for the preset names above. If any are missing, re-apply from `milimo-blueprint/policies/presets/`.

**See also**: [[hermes-profile]] — policy preset architecture; [[common-issues]] — preset collision bug (npm preset name)

---

### War Room Page Returns 404 / Connection Refused (FIXED 2026-07-09)

**Symptom**: Visiting `http://127.0.0.1:9090/warroom.html` returns connection refused, or the page loads but shows no approve/release/veto buttons.

```bash
# War room health check fails
curl -s http://127.0.0.1:9090/health
# curl: (7) Failed to connect

# Inside sandbox — no warroom process
ps aux | grep server.py
# (no output)
```

**Root cause**: Two bugs in `start.sh`'s war room launch sequence:

1. **Wrong Python binary** (`start.sh:1419`, `start.sh:1439`): Both the current-user and sandbox-user launch paths used `/usr/bin/python3` to run `warroom/server.py`. The system Python has no `milimo_core` in `sys.path`, causing:
   ```
   ModuleNotFoundError: No module named 'milimo_core'
   ```
   The venv interpreter `/opt/hermes/.venv/bin/python3` (resolved as `$_HERMES_PYTHON` at `start.sh:293`) has `milimo_core` installed and is the correct binary.

2. **Missing `typing.Any` import** (`warroom/server.py:204`): Type annotations `dict[str, Any] | None` reference `Any` without importing it from `typing`. Under Python 3.13 (used in the container), annotations are evaluated eagerly, raising:
   ```
   NameError: name 'Any' is not defined. Did you mean: 'any'?
   ```
   Even with the correct Python binary, this crashed the server before it could bind to port 9090.

**Fix** (committed 2026-07-09 as `be62e42`):
- `scripts/start.sh` — replaced both `/usr/bin/python3` with `"$_HERMES_PYTHON"` at lines 1419 and 1439
- `milimo-hermes-plugin/warroom/server.py` — added `from typing import Any`

**Rebuild required**: The running sandbox's `/opt/hermes/warroom/server.py` is baked into the image and owned by `root:root`. The non-root `sandbox` user cannot patch it at runtime. Rebuild the image:
```bash
NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 \
NEMOCLAW_NON_INTERACTIVE=1 \
NEMOCLAW_ACCEPT_THIRD_PARTY=1 \
  ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

After rebuild, the war room auto-starts on port 9090. If port 9090 is not forwarded, add it:
```bash
openshell forward start --background 9090 milimo-hermes
```

**Verify**:
```bash
curl -s http://127.0.0.1:9090/health
# Expected: {"status":"ok"}
open http://127.0.0.1:9090/warroom.html
# Expected: War Room UI with Claw Status, HOLD Queue (Approve/Veto buttons), Cost Guard
```

**Important**: The war room is a **standalone HTMX server on port 9090** — it is not embedded in the Hermes dashboard at port 18790/19119. The dashboard URL (`http://127.0.0.1:18790/sessions?profile=default`) is the chat UI and has no war room buttons.

**See also**: [[issues-and-fixes]] — Issue 18 (full audit); [[hermes-profile]] — war room architecture

---

### Agent Never Calls `milimo_spend` + Device Approval URL Surfacing Failure (FIXED 2026-07-12)

**Symptom**: When the operator requests a spend flow (e.g., "Pay Stripe $49 for API credits"), the Hermes agent:
1. Never calls `milimo_spend` — instead runs `which`, `ls`, `find`, `cat`, `grep`, and reads source files (`finance_claw.py`, `spend_handler.py`, `tools.py`)
2. Writes a Python script importing `SpendApprovalHandler` directly (bypassing tool-layer parameter validation, auth prechecks, and `_finance_context` injection)
3. Fails to surface the device approval URL — even when it appears in tool output

**Root Cause** (3 layers, fixed in commits `a481e32`, `02ff7d7`, `4e62fef`):

1. **Structural contradiction**: `SOUL.md` Rule 3 told the agent to run `link-cli auth login` directly; `delegation.py` `CLAW_CONTEXTS["finance"]` Rule 5 forbade it. The agent could not satisfy both simultaneously.

2. **`environment_probe: true`** in `agent.environment_probe` pushed the agent to shell-first behavior (`which`, `ls`, `cat`) instead of calling registered tools. Fixed: `generate-config.ts` now sets `environment_probe: false`.

3. **Auth rules scoped only to `CLAW_CONTEXTS["finance"]`**: Rules were injected only during `delegate_task` calls. The agent invoked `milimo_spend` directly — never entering the `delegate_task` path — so finance rules were never loaded into its base context.

4. **No forbid-direct-handler-imports rule**: Neither `SOUL.md` nor `delegation.py` named `SpendApprovalHandler` / `SpendWarRoomBridge` / `milimo_core.finance.*` as forbidden import targets.

**Fix** (commits `a481e32`, `02ff7d7`, `4e62fef`, `ce0b677`):

> **Critical (2026-07-12, commit `ce0b677`)**: The `02ff7d7` SOUL.md rewrite introduced trigger patterns (`MUST be`, `FORBIDDEN`, `NON-NEGOTIABLE`, `NEVER`, `HARD RULES`) that OpenClaw's `forced_action` scanner blocks entirely. The agent saw zero MilimoClaw context and responded generically. The fix rewrote SOUL.md, `delegation.py` finance context, and `HERMES_ENVIRONMENT_HINT` using **advisory/guidance language** — all operational content preserved, only the framing changed from imperative to descriptive.

- `agent_config/SOUL.md` — advisory language: `BEHAVIORAL GUIDANCE` replaces `HARD RULES — NON-NEGOTIABLE`; `the recommended starting point is milimo_spend` replaces `your FIRST action MUST be`; `Avoid creating mocks` replaces `FORBIDDEN — DO NOT create`; `Avoid` replaces `You MUST NOT`; `Avoid running` replaces `NEVER run`. All 6-claw rules, sequences, error recovery, and output formats preserved verbatim.
- `Dockerfile` `HERMES_ENVIRONMENT_HINT` — advisory language; uppercase `NEVER` tokens changed to lowercase `is never` / `never touches`.
- `delegation.py` — finance `CLAW_CONTEXTS["finance"]` uses same advisory language as SOUL.md. Root and sandbox copies byte-identical.

**Why `_run_link_cli_auth_login()` instead of direct `link-cli auth login`**:
- Each direct invocation generates a NEW device code and invalidates any pending approval URL. The wrapper enforces "call exactly once" at the tool layer — the agent cannot accidentally call it twice.
- Eliminates the structural contradiction: the agent never needs to decide whether to run the forbidden command; it calls the allowed helper tool instead.

**Verify**:
```bash
# SOUL.md must reference _run_link_cli_auth_login in Rule 3, Registered Tools, and Step B
grep -c "_run_link_cli_auth_login" milimo-hermes-sandbox/agent_config/SOUL.md
# Expected: >= 3

# delegation.py finance context has Rule 0 (mandatory first action)
grep "MANDATORY FIRST ACTION" milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py
# Expected: match

# delegation.py forbids SpendApprovalHandler direct import
grep "SpendApprovalHandler" milimo-hermes-sandbox/milimo-hermes-plugin/milimo_hermes_plugin/delegation.py
# Expected: match (forbid rule)

# environment_probe is false
grep "environment_probe" milimo-hermes-sandbox/generate-config.ts
# Expected: environment_probe: false

# Plugin sync passes
bash scripts/check-plugin-sync.sh
# Expected: [OK] plugin, [OK] core
```

**Rebuild required**:
```bash
NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 \
NVIDIA_API_KEY="$(grep NVIDIA_API_KEY .env | cut -d= -f2)" \
NEMOCLAW_NON_INTERACTIVE=1 \
NEMOCLAW_ACCEPT_THIRD_PARTY=1 \
NEMOCLAW_AUTH_MODE=api_key \
  ./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

**See also**: [[issues-and-fixes]] — Issue 19 (demo mock creation + tool-path bypass); Issue 20 (auth rule contradiction + mandatory-first-action + handler import forbidding); [[hermes-profile]] — SOUL.md architecture; [[link-cli-setup]] — device approval flow

---

### Milimo Tools Not Visible in Hermes Agent Toolset (FIXED 2026-07-12)

**Symptom**: The Hermes agent bootstrap shows `31 tools · toolsets: browser, clarify, code_execution, computer_use, cronjob, delegation, file, image_gen, kanban, memory, session_search, skills, terminal, todo, tts, vision, web`. None of the Milimo core tools (`milimo_status`, `milimo_warroom`, `milimo_approve`, `milimo_veto`, `milimo_spend`, `delegate_task`) are visible. The agent cannot call `milimo_spend` and falls back to shelling out to `link-cli` directly or importing `SpendApprovalHandler` through Python `exec`.

**Root Cause**: Hermes Agent v0.17+ uses a different plugin tool-registration API than the legacy OpenClaw shim. The plugin was calling `skill_registry.register_tool(name, description, parameters, handler)` — which is a vestigial no-op in Hermes. The correct Hermes API is `ctx.register_tool(name, toolset, schema, handler, description)` with a required `toolset` parameter.

**Fix** (commit `be62e42` + new):
- `milimo_hermes_plugin/tools.py` — `register_core_tools(ctx)` now uses `ctx.register_tool()` with `toolset="milimo"` instead of `skill_registry.register_tool()`
- `milimo_hermes_plugin/__init__.py` — passes `ctx` to `register_core_tools()`

**Verify**:
```bash
python3 -c "
import milimo_hermes_plugin.tools as tools
print('MILIMO_SPEND_SCHEMA:', tools.MILIMO_SPEND_SCHEMA['name'])
print('Tool registration signature:', tools.register_core_tools.__doc__)
print('Expected: ctx.register_tool with toolset param')
"
```

---

### Sandbox Creation Hangs at [6/8] — NVIDIA_INFERENCE_API_KEY Missing (FIXED 2026-07-25)

**Symptom**: `nemohermes onboard --non-interactive` hangs at step [3/8] or [6/8] with:
```
NVIDIA_INFERENCE_API_KEY (or NEMOCLAW_PROVIDER_KEY) is required for NVIDIA Endpoints in non-interactive mode.
```

**Root Cause**: The `nemohermes onboard --non-interactive` CLI expects `NVIDIA_INFERENCE_API_KEY` (or `NEMOCLAW_PROVIDER_KEY`) to configure the inference provider. The `.env` file and `install-hermes.sh` use `NVIDIA_API_KEY` — a different env var. Without the correct var exported, non-interactive onboarding cannot proceed past provider configuration.

**Fix** (commit `51f9cc8`):
- `install-hermes.sh` now exports `export NVIDIA_INFERENCE_API_KEY="${NVIDIA_API_KEY}"` at both the prerequisite check and the env-var dump section
- Users continue to use `NVIDIA_API_KEY` in `.env` (backward compatible)

**Workaround**: Export manually before running install:
```bash
export NVIDIA_INFERENCE_API_KEY="$NVIDIA_API_KEY"
```

---

### Onboarding Hangs at [6/8] "Creating Sandbox" — Stale Sandbox State (FIXED 2026-07-25)

**Symptom**: `nemohermes onboard --recreate-sandbox` hangs indefinitely at step [6/8]:
```
[6/8] Creating sandbox
──────────────────────────────────────────────────


```
No error message, no timeout — just blank space after the header.

**Root Cause**: The `--recreate-sandbox` flag tries to gracefully tear down the existing sandbox workspace state before creating a new sandbox. If the old sandbox has accumulated state files or the gateway has a stale lock, this teardown can stall indefinitely.

**Fix** (commit `83bf1ea`):
1. **Preemptive destroy**: `install-hermes.sh` now forcefully destroys any existing "Ready" sandbox before running `nemohermes onboard`. The sandbox is already gone, so the recreate step is instant.
2. **Timeout (900s)**: The onboarding command is wrapped in `timeout 900`. If it ever hangs, the script exits with a clear error.
3. **Alias→function**: `alias nemohermes=...` replaced with a bash function + `export -f` (aliases don't expand in non-interactive scripts).

---

### Milimo Tools Not Accessible in Hermes Session — Toolset Name Mismatch (FIXED 2026-07-25)

**Symptom**: The Hermes agent session starts, the plugin is loaded (`plugins.enabled: ['nemoclaw', 'milimo-hermes']`), but the 6 core Milimo tools never appear. The agent falls back to probing the filesystem with `find`/`grep`/`read`.

**Root Cause**: `register_core_tools()` in `tools.py` used `toolset="milimo"` but the Hermes config (`generate-config.ts`) declared `"milimo-hermes"` in `API_SERVER_TOOLSETS`. The API server only surfaces tools whose toolset name matches an entry in `platform_toolsets.api_server`. Since `"milimo" ≠ "milimo-hermes"`, the tools were registered in the runtime but invisible to every session.

**Fix** (commit `8b6c9ce`):
- Changed `toolset="milimo"` to `toolset="milimo-hermes"` in `register_core_tools()` (line 1327 of `tools.py`)
- Added 9 registration tests that verify the toolset name matches between `tools.py` and `generate-config.ts`, preventing recurrence

---

### Milimo Tools Blocked in Chat Session — Missing Terminal Platform Toolset (FIXED 2026-07-25)

**Symptom**: `milimo_spend`, `milimo_approve`, `milimo_veto`, `milimo_warroom` are registered (importable, visible in `_CORE_TOOLS`), but the agent says "The registered tools are not loaded in this session." API server calls work but terminal/chat sessions fail.

**Root Cause**: `generate-config.ts` only configured `platform_toolsets.api_server` with `milimo-hermes`. The interactive chat session (`nemohermes connect` → `hermes`) uses the `terminal` platform, which had no toolset configuration. Session info logs showed no `milimo-hermes` entries in the loaded tools list.

**Fix** (commit `7642a41`):
- Added `TERMINAL_TOOLSETS` array in `generate-config.ts` including `milimo-hermes`
- Added `platform_toolsets.terminal` to the generated Hermes config
- After rebuild, terminal sessions include `milimo-hermes` tools alongside built-in tools

---

### Claw Status Stuck on "Loading..." in War Room — .pth Path Blocked by Landlock (FIXED 2026-07-25)

**Symptom**: The War Room page loads, but the "Claw Status" card stays on "Loading..." indefinitely. The `/v1/warroom/claw-status` endpoint returns 500 with `ModuleNotFoundError: No module named 'orchestrator'`.

**Root Cause**: The `nemoclaw_blueprint.pth` file pointed to `/opt/nemoclaw-blueprint/`, which is not readable by the `sandbox` user. OpenShell's Landlock security policy blocks `/opt/` for unprivileged users. The `orchestrator` package could not be imported from `milimo_core.bridge_cli`.

**Fix** (commit `8b6c9ce`):
- Changed `.pth` path to `/sandbox/.nemoclaw/blueprints/0.1.0/` (owned by `sandbox:sandbox`)
- Added `/sandbox/.nemoclaw/blueprints/0.1.0` to the `_BLUEPRINTS` search list in `server.py`

---

### "Port Forward on 18789 is Not Working" Warning During Onboard — NEMOCLAW_DASHBOARD_PORT Override (FIXED 2026-07-25)

**Symptom**: `nemohermes onboard` succeeds but prints:
```
⚠ Deployment verification found issues:
  ✗ dashboard: port forward not working (connection refused)
    Port forward on 18789 is not working.
```

**Root Cause**: `install-hermes.sh` exported `NEMOCLAW_DASHBOARD_PORT=18790`. The sandbox's `start.sh` reads this env var and sets the dashboard socat port to 18790 instead of the default 18789. The upstream Hermes agent manifest (`agents/hermes/manifest.yaml`) declares `forward_ports: [18789, 8642]`. The nemohermes CLI reads the manifest and verifies port 18789 — nothing is listening there because our env var moved it to 18790.

**The warning was caused by our own code.** Every previous fix treated the symptom:
1. Removing 18789 from blueprint `forward_ports` (CLI uses agent manifest, not blueprint)
2. Setting `CHAT_UI_URL=http://127.0.0.1:18790` (start.sh already derives from NEMOCLAW_DASHBOARD_PORT)
3. Exporting `NEMOCLAW_DASHBOARD_PORT=18790` (THIS was the actual cause)

**Fix** (commit `f25e860`):
- Reverted `NEMOCLAW_DASHBOARD_PORT` export from `install-hermes.sh`
- Reverted `CHAT_UI_URL` in blueprint back to empty string
- The sandbox now uses default port 18789, matching the upstream agent manifest

**Do NOT set `NEMOCLAW_DASHBOARD_PORT`** in environment or build args. Let the upstream default (18789) propagate through start.sh automatically.

---

## Related Pages

- [[production-spend-flow-fix-plan-2026-07-06]] — Full production fix plan
- [[spend-handler]] — Handler architecture
- [[test-spend-flow]] — Test scenarios
- [[link-cli-setup]] — Link CLI installation and auth
- [[hermes-profile]] — Hermes prompt layers
