# MilimoClaw × NemoHermes: Integration Gap Analysis & Implementation Report

**Prepared for:** Milimo Quantum / MilimoClaw
**Date:** June 27, 2026
**Source:** Full audit against NemoClaw Hermes documentation (Quickstart, Architecture, Install Plugins, Network Policies, Inference Options, Credential Storage, Runtime Controls, Agent Skills)
**Scope:** Dual-track Hermes agent strategy — gap analysis, enhancement recommendations, phased implementation plan

---

## Executive Summary

The proposed dual-track architecture is strategically sound. Running OpenClaw and NemoHermes as parallel profiles under a shared `milimo-core` orchestrator is the right structural decision — it preserves the existing OpenClaw investment completely while unlocking Hermes' web dashboard, OpenAI-compatible API endpoint, and managed tool gateway ecosystem.

This updated report supersedes the earlier draft. After auditing the full Hermes documentation, **four items in the original report were materially wrong or incomplete**, and **five additional gaps were found** that were not in the first version. All have been corrected and incorporated. The original seven gaps are retained and sharpened with doc-grounded specifics. The nine enhancements stand with updates.

---

## Corrections to the Original Report

These are not stylistic updates — they are factual corrections based on the actual Hermes architecture documentation.

### Correction 1 — Plugin Installation Path Is Not `hermes plugin install`

**The original plan stated:** "Loadable Hermes plugin + 6 skills, installable via `hermes plugin install`."
**This is wrong.** Hermes plugins are not installed via a CLI command on a running sandbox. They must be baked into the sandbox image at build time using a custom `--from` Dockerfile.

The correct flow per the docs:
```
# Correct Hermes plugin installation
COPY milimo-hermes-plugin/ /opt/milimo-hermes-plugin/
RUN mkdir -p /sandbox/.hermes/plugins/milimo-hermes \
  && cp -a /opt/milimo-hermes-plugin/. /sandbox/.hermes/plugins/milimo-hermes/ \
  && /opt/hermes/.venv/bin/python -m pip install --no-cache-dir -r /opt/milimo-hermes-plugin/requirements.txt \
  && chown -R sandbox:sandbox /sandbox/.hermes/plugins/milimo-hermes \
  && chmod -R a+rX /sandbox/.hermes/plugins/milimo-hermes

# Then onboard with:
nemohermes onboard --name my-milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile
```

The plan's Phase 3 Dockerfile task (`agents/hermes/Dockerfile — COPY milimo-hermes-plugin`) was directionally correct but the deliverable statement was wrong. Correct it explicitly: **the plugin is image-resident, not hot-loadable**.

**Critical constraint also surfaced:** The NemoClaw Hermes image contract must be preserved. The custom Dockerfile must still include the generated Hermes config, NemoClaw Hermes plugin at `/sandbox/.hermes/plugins/nemoclaw` (do not remove this), blueprint files, and the `nemoclaw-start` entrypoint. Starting from `ghcr.io/nvidia/nemoclaw/hermes-sandbox-base:latest` alone is not sufficient — the NemoClaw Hermes layers from `agents/hermes/Dockerfile` must also be present.

---

### Correction 2 — Python Runtime Requirement for Plugin Network Egress

**The original report discussed network policy** in terms of `phone_home_hosts` in `manifest.yaml`.
**The docs add a constraint the original report missed entirely:** when a Hermes plugin calls an external API, policy entries must allow the **Hermes Python runtime binary** (`/opt/hermes/.venv/bin/python`) in addition to the target hostname and port. The policy is binary-scoped — it's not enough to allowlist `api.stripe.com:443`; you must also allowlist the binary that opens the connection.

This affects every claw's policy definition. The `milimo-mcp.yaml` preset spec needs a `binaries` field, not just a hostnames list.

---

### Correction 3 — Hermes Onboarding Does Not Include Brave Search

**The original report said nothing about web search.** The docs explicitly state:

> "The Hermes wizard does not ask for Brave Web Search because Hermes does not use NemoClaw's OpenClaw web-search configuration."

However, Nous Portal OAuth onboarding (as opposed to API-key mode) **does** unlock managed Nous tool gateways: web search, image generation, audio, browser automation, and managed code execution. These are distinct from Brave and add additional policy presets automatically.

This has a direct implication: if MilimoClaw's Hermes profile users authenticate via Nous Portal OAuth, the managed tool gateways available to the Hermes agent are fundamentally different from what API-key users get. This affects the feature matrix, onboarding decision tree, and documentation.

---

### Correction 4 — `nemohermes` Is an Alias, Not a Separate Binary

**The original plan repeatedly uses `nemoclaw onboard --agent hermes`** as the onboarding command.
**The correct command is `nemohermes onboard`** — `nemohermes` is an alias for `nemoclaw` with the Hermes agent pre-selected. The non-interactive equivalent requires `NEMOCLAW_AGENT=hermes` set before running the installer. Non-interactive onboarding uses:

```bash
export NEMOCLAW_AGENT=hermes
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export NEMOCLAW_SANDBOX_NAME=my-milimo-hermes
export NVIDIA_API_KEY=<your-key>
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

All install scripts, CI configurations, and README commands in the plan must use `nemohermes` and the environment variable pattern, not `--agent hermes` flags.

---

## Part 1: Gap Analysis (Updated — 12 Gaps Total)

### Gap 1 — Hermes Credential Model vs. `service_factory` (Critical)

The credential architecture is confirmed correct in the original report — NemoClaw never gives the sandbox a raw provider key; the OpenShell L7 proxy substitutes at egress. However, the doc surfaces two additional specifics:

**GitHub tokens are handled differently from all other credentials.** NemoClaw never persists `GITHUB_TOKEN` itself. Instead it calls `gh auth token` which reads from whatever the GitHub CLI has stored — macOS Keychain, Windows Credential Manager, Linux Secret Service, or `~/.config/gh/` on headless hosts. MilimoClaw's Build Claw, which makes GitHub API calls, must account for this. The `hermes_credential_adapter` in `milimo-core` needs a GitHub-specific path that calls through `gh auth token` rather than reading from the OpenShell gateway store.

**Credential migration matters.** If any Milimo operator has an older NemoClaw release with a `~/.nemoclaw/credentials.json`, Hermes onboarding will auto-migrate on first run — but only `nemohermes onboard` completes the verified migration and cleans up the plaintext file. `nemohermes rebuild` stages credentials but does not delete the legacy file. This is a security detail that the install script and documentation should surface explicitly.

**Resolution:** The `hermes_credential_adapter` in `milimo-core` needs a GitHub-specific code path. Add a credential migration note to the Hermes onboarding documentation.

---

### Gap 2 — Lucy / War Room Has No Hermes Continuity Plan (Critical)

Unchanged from the original report — this remains the highest user-impact gap. The docs confirm that Hermes' primary interfaces are the dashboard on port `18789` and the OpenAI-compatible API on port `8642`.

**Additional doc-grounded detail:** The Hermes dashboard on port `18789` is built into the sandbox image at build time (assets at `/opt/hermes/ui-tui`). Recovery is via `hermes dashboard --tui --skip-build`. `NEMOCLAW_HERMES_DASHBOARD_TUI=1` must be set before onboarding to enable the optional in-browser TUI tab — this is a build-time flag, not a runtime toggle.

If MilimoClaw wants a War Room TUI tab inside the Hermes dashboard (Option B from the original report), the `NEMOCLAW_HERMES_DASHBOARD_TUI=1` flag must be part of the onboarding configuration and the `milimo-warroom` widget must be built against the `/opt/hermes/ui-tui` bundle format.

**Resolution remains:** Lock to Option B. Add `NEMOCLAW_HERMES_DASHBOARD_TUI=1` as a Milimo-specific onboarding default in the install script.

---

### Gap 3 — `milimo-core` Extraction Sequencing Risk (Critical)

Unchanged from the original report. The dependency graph step before Phase 1 is mandatory.

**Additional specificity:** The Hermes Python runtime runs in `/opt/hermes/.venv/`, not the system Python. When `milimo-hermes-plugin` declares its `requirements.txt`, pip installs into that venv at image build time. If `milimo-core` is published to PyPI, the plugin `requirements.txt` can declare `milimo-core>=0.1.0`. If it stays as a local editable install, the Dockerfile must `COPY milimo-core/ /opt/milimo-core/` and `pip install /opt/milimo-core/` into the Hermes venv explicitly. This decision (PyPI vs. local) affects the Dockerfile and CI pipeline design — it must be made before Phase 1 concludes.

---

### Gap 4 — Network Policy: `phone_home_hosts` Is Incomplete and Binary-Scoped (Updated)

The original report identified the incomplete hostname inventory. The docs add the binary-scoping requirement (see Correction 2 above). Updated resolution:

The `milimo-mcp.yaml` preset must specify both hostnames **and** the `/opt/hermes/.venv/bin/python` binary for each rule. Example structure:

```yaml
# milimo-mcp.yaml — correct policy structure
endpoints:
  - host: api.stripe.com
    port: 443
    methods: [POST, GET]
    binaries:
      - /opt/hermes/.venv/bin/python
  - host: api.github.com
    port: 443
    methods: [GET, POST]
    binaries:
      - /opt/hermes/.venv/bin/python
```

GitHub access is explicitly not in the Hermes baseline — the `github` preset must be applied at onboarding. Finance Claw (Stripe), Build Claw (GitHub, npm, PyPI), and Vercel deployment all need explicit preset additions. The `npm_registry` and `pypi` presets are included in the Balanced tier by default — Build Claw benefits from selecting Balanced or Open tier. Finance Claw (Stripe) and Vercel require custom presets regardless of tier.

---

### Gap 5 — Subagent Isolation Model Is Unresolved but Blocks Phase 2 Design

Unchanged from original report. **Decision: multi-sandbox per claw subagent.**

---

### Gap 6 — Solo Mode Is Not Addressed for Hermes Profile

Unchanged from original report.

**Additional detail from docs:** The default Hermes sandbox name is `hermes`. The docs recommend using a distinct name (e.g., `my-hermes`) so Hermes and OpenClaw sandboxes can run side by side. `nemoclaw list` shows the agent type for each sandbox. The install script must generate a Milimo-specific sandbox name (e.g., `milimo-hermes`) to avoid collision with a default `hermes` sandbox an operator may have created independently.

---

### Gap 7 — CI/CD Test Coverage for Hermes Is Superficial

Unchanged from original report.

**Additional specificity from docs:** Non-interactive Hermes onboarding in CI requires `NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1` in addition to `NEMOCLAW_NON_INTERACTIVE=1`. The policy tier can be set with `NEMOCLAW_POLICY_TIER=restricted` for CI to minimize network surface. These env vars must be in the CI matrix.

---

### Gap 8 — NEW: Sandbox Name Collision Risk in Multi-User Environments

**Not in the original report.** The docs state:

> "NemoClaw prevents same-name reuse when an existing sandbox uses a different agent."

This means if an operator already has a sandbox named `hermes` running OpenClaw, `nemohermes onboard` with the default name will fail. MilimoClaw's install script must either generate a unique sandbox name (e.g., `milimo-hermes`) or prompt the operator for one. This is a first-run UX failure case that is easy to hit if the operator has previously run any NemoClaw quickstart.

**Resolution:** The install script must default to `NEMOCLAW_SANDBOX_NAME=milimo-hermes` and document that this can be customized.

---

### Gap 9 — NEW: Model Router Requires Host Python — Not Addressed for Hermes Path

**Not in the original report.** If MilimoClaw recommends or defaults to the Model Router provider for the Hermes profile (as suggested in Enhancement 9 / the `milimo-compatibility.json` model routing plan), the host must have Python 3.10–3.13 with `ensurepip`, `pyexpat`, `ssl`, and `venv` all available. This is a non-obvious prerequisite.

On macOS with Homebrew Python 3.14 (which has a known `pyexpat`/`libexpat` dlopen issue), the Model Router onboarding will abort. The operator must pin via `NEMOCLAW_MODEL_ROUTER_PYTHON`.

**Resolution:** The Milimo install script, when selecting Model Router as the default routing strategy, must probe for a qualifying Python before invoking `nemohermes onboard`. If the probe fails, it should fall back to a single-model provider with a clear message, not silently fail mid-onboard.

---

### Gap 10 — NEW: `CHAT_UI_URL` / Remote Dashboard Not Addressed

**Not in the original report.** If MilimoClaw is deployed on a headless remote GPU instance (a common pattern for solo founders on cloud VMs), the Hermes dashboard on port `18789` is not reachable by default. The docs specify:

> "If a headless host needs to expose the Hermes dashboard through a remote URL or tunnel, set `CHAT_UI_URL` before onboarding."

This must be set before the sandbox image is built — it cannot be changed at runtime without a rebuild. MilimoClaw's install script must detect headless environments and either prompt for `CHAT_UI_URL` or document SSH local port forwarding (`ssh -L 18789:127.0.0.1:18789 user@host`) as the default remote access pattern.

---

### Gap 11 — NEW: Hermes Baseline Policy Does Not Include GitHub — Breaks Build Claw

**Not in the original report — confirmed from the network policy docs:**

> "GitHub access (`github.com`, `api.github.com`) is not included in the baseline policy. Apply the `github` preset during onboarding if your agent needs GitHub access."

Build Claw makes GitHub API calls for repo operations. Without the `github` preset explicitly applied at onboarding, Build Claw will hit a network block on its first GitHub operation. The install script must apply the `github` preset as part of Milimo's Hermes onboarding defaults. This is not automatic under any policy tier.

**Resolution:** Add `--policy-preset github` to the non-interactive install defaults. Document this in the install script and README.

---

### Gap 12 — NEW: `NemoClaw Agent Skills` Are Irrelevant to Milimo's Own Plugin Skills — Naming Confusion Risk

**Not in the original report.** The NemoClaw docs describe "Agent Skills" as `.agents/skills/` files for AI coding assistants (Cursor, Claude Code) to answer NemoClaw operational questions — not what MilimoClaw's plan calls "skills" (the six claw-wrapping Hermes skill packages). These are different concepts with the same name.

MilimoClaw's internal documentation and code must use a distinct term — recommend **"claw plugins"** or **"claw handlers"** for the six Hermes skill packages — to avoid confusion with NemoClaw's own agent-skill system. This naming conflict would confuse contributors and LLM-assisted debugging tools that ingest both NemoClaw docs and MilimoClaw's own `CLAUDE.md`.

---

## Part 2: Enhancement Opportunities (9 Enhancements, Updated)

### Enhancement 1 — `milimo-core` as a Versioned Package (Updated)

The correct answer is local editable install (`pip install -e`) for development; PyPI release for distribution. If PyPI, the Hermes Dockerfile uses `pip install milimo-core` into `/opt/hermes/.venv`. If local, `COPY milimo-core/ /opt/milimo-core/` and `pip install /opt/milimo-core/` into the venv. **Make this decision before Phase 1 ends** — it determines the Dockerfile and CI pipeline shape.

---

### Enhancement 2 — Hermes Dashboard as the Primary Operator UX Upgrade

The Hermes dashboard at port `18789` is the flagship UI for the Hermes profile. The `NEMOCLAW_HERMES_DASHBOARD_TUI=1` flag (set before onboarding) enables the in-browser TUI tab. MilimoClaw should enable this by default for the Hermes profile and build the War Room widget into it. The dashboard handles sessions itself — no `#token=` fragment, no auth friction for operators.

Recommended additions: `milimo-warroom` status widget (HOLD queue, claw status, cost guard remaining budget), Stripe invoice preview, Analytics Claw timeline view.

---

### Enhancement 3 — Skill Granularity: Hybrid Approach

One primary claw plugin per claw (6) + one shared `milimo-core-primitives` handler. Rename internally to "claw plugins" or "claw handlers" to avoid collision with NemoClaw's own `agent-skills` system (see Gap 12).

---

### Enhancement 4 — Hermes Cron as the Evolution Cycle Driver

The Hermes cron path is cleaner and more restartable than the current `evolution_cycle.py` + Build Claw scheduler. Make the Hermes cron path the reference implementation and backport a `SchedulerInterface` abstract base into `milimo-core` for shared evolution cycle logic with profile-specific trigger adapters.

---

### Enhancement 5 — Lucy Persona System Should Be Profile-Aware

The `on_session_start` hook in the Hermes plugin is the right place to inject the operator-configured persona name into the Hermes session context. Persona coherence between OpenClaw TUI and Hermes dashboard matters for operators who switch profiles.

---

### Enhancement 6 — Hermes Messaging Channel Integration (Updated with Env Var Specifics)

Telegram, Slack (Bot Token + Socket Mode), and other channels are supported. The docs specify the exact environment variables:

- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_ALLOWED_IDS` for Telegram
- `SLACK_BOT_TOKEN` + `SLACK_APP_TOKEN` (Socket Mode) + `SLACK_ALLOWED_USERS` + `SLACK_ALLOWED_CHANNELS` for Slack

`SLACK_ALLOWED_CHANNELS` is **baked into the sandbox image at build time** — it cannot be changed without a rebuild. MilimoClaw's install wizard must prompt for this before building the image, not after. HOLD alerts and Analytics Claw weekly summaries pushed to Slack are a first-class operator workflow, not a future enhancement.

---

### Enhancement 7 — Obsidian Vault Hermes Topology Section

The vault needs a `hermes-profile/` section covering: sandbox layout, claw plugin-to-claw mapping, `milimo-core` dependency graph, updated sequencing rules under the Hermes subagent model, and the corrected onboarding command (`nemohermes onboard`). Stale topology docs degrade LLM-assisted debugging.

---

### Enhancement 8 — Dual-Profile Onboarding Decision Tree (Updated)

The decision tree should now also surface the Nous Portal OAuth vs. API-key distinction, since OAuth enables managed tool gateways (web search, browser automation, image generation) that API-key mode does not:

```
Do you want web search / browser automation inside the Hermes agent?
  → Yes: Use Nous Portal OAuth authentication at onboarding
  → No: API-key mode is sufficient

Are you on a headless remote host?
  → Yes: Set CHAT_UI_URL before onboarding, or use SSH port forwarding
  → No (local machine): Dashboard accessible at http://127.0.0.1:18789/ after onboard

Do you want a web dashboard UI?
  → Yes: nemohermes (Hermes profile)
  → No: nemoclaw (OpenClaw profile, default)
```

---

### Enhancement 9 — Model Router for Per-Claw Cost Optimization (Updated)

The Model Router uses a PrefillRouter (`llm-router/checkpoints/prefill_router_qwen08b.pt`) to select models based on a cost/quality tolerance. The pool is defined in `nemoclaw-blueprint/router/pool-config.yaml`. For MilimoClaw:

- Finance/Ops approval flows: `tolerance: 0.0` (always highest accuracy)
- Content generation: `tolerance: 0.20–0.40` (cost-optimized)
- Analytics summarization: `tolerance: 0.15`

This directly implements the 50K daily token cost guard in a more intelligent way than simple token counting — the router picks cheaper models when query complexity allows. Add this to `milimo-compatibility.json` in the blueprint. Note the host Python prerequisite (Gap 9).

---

## Part 3: Revised Implementation Plan

### Pre-Phase: Locks and Dependency Audit (3 days, before Week 1)

| Task | Output |
|------|--------|
| Run full import graph across `milimo-blueprint/orchestrator/` | Ordered extraction sequence for Phase 1 |
| Document every external hostname + binary reached by each claw | Egress inventory with binary-scoped policy spec |
| Decide: `milimo-core` on PyPI vs. local editable | Determines Dockerfile and CI shape |
| Lock: multi-sandbox subagent isolation, Option B War Room, `NEMOCLAW_HERMES_DASHBOARD_TUI=1` default | ADR in `docs/adr/` |
| Confirm build-time flags: `NEMOCLAW_HERMES_DASHBOARD_TUI`, `SLACK_ALLOWED_CHANNELS`, `CHAT_UI_URL` | Install wizard prompt spec |
| Probe for qualifying Python 3.10–3.13 if Model Router will be recommended | Fallback logic for install script |

---

### Phase 1: Shared Foundation (Week 1–2)

Original tasks 1.1–1.5 stand. Add:

| Added Task | Description |
|------------|-------------|
| 1.6 | Backward-compat shim: `milimo-blueprint/orchestrator/contracts.py` re-exports from `milimo_core.contracts` with deprecation warning. No bridge server breakage. |
| 1.7 | Run existing test suite against shim imports to confirm zero regression before cutting over |
| 1.8 | Add `milimo-core/CHANGELOG.md` and tag `v0.1.0` on Phase 1 completion |
| 1.9 | Add `milimo-core-primitives` shared handler spec (privacy_router, provenance_signer, cost_guard) |
| 1.10 | Decide and document PyPI vs. local install for `milimo-core`; update Dockerfile template accordingly |

---

### Phase 2: Hermes Plugin Development (Week 2–4)

**Critical correction:** The deliverable is an image-resident plugin baked via `--from` Dockerfile, not a `hermes plugin install` command.

Original tasks 2.1–2.8 with corrections:

| Task | Description (Corrected) |
|------|------------------------|
| 2.1 | Create `milimo-hermes-plugin/` with `plugin.yaml` manifest — **image-resident, installed via Dockerfile COPY** |
| 2.2 | Implement `register(ctx)` with `on_session_start`, `pre_llm_call` hooks. Inject persona in `on_session_start`. |
| 2.3 | Register core tools: `milimo_status`, `milimo_warroom`, `milimo_approve`, `milimo_veto` |
| 2.4 | Create 6 claw handler packages (rename from "skills" to avoid NemoClaw naming conflict): `milimo-content`, `milimo-ops`, `milimo-analytics`, `milimo-finance`, `milimo-build`, `milimo-assistant` |
| 2.5 | Each handler wraps `milimo-core` modules. No business logic duplication. |
| 2.6 | Add subagent spawning for parallel claw execution — **multi-sandbox isolation model** |
| 2.7 | Integrate Hermes cron for evolution cycle (Sunday 2AM) with `SchedulerInterface` abstraction in `milimo-core` |
| 2.8 | Map network policies → binary-scoped `milimo-mcp.yaml` preset (hostname + `/opt/hermes/.venv/bin/python`) |

Added tasks:

| Added Task | Description |
|------------|-------------|
| 2.9 | Implement `hermes_credential_adapter` in `milimo-core`: wraps service clients to use OpenShell provider placeholders; GitHub path calls `gh auth token` not gateway store |
| 2.10 | Add Slack/Telegram push integration to `milimo_warroom` tool; prompt for `SLACK_ALLOWED_CHANNELS` before image build |
| 2.11 | Define `milimo-warroom` dashboard widget spec for `/opt/hermes/ui-tui` bundle format |
| 2.12 | Build `milimo-hermes-sandbox/Dockerfile` that: (a) preserves NemoClaw Hermes image contract, (b) COPYs and installs `milimo-hermes-plugin` into `/opt/hermes/.venv`, (c) does NOT remove `/sandbox/.hermes/plugins/nemoclaw` |

---

### Phase 3: Blueprint Updates (Week 3–4)

Original tasks stand. Add:

| Added Task | Description |
|------------|-------------|
| 3.1a | Produce complete egress inventory with binary-scoped policy for each claw before writing any YAML |
| 3.1b | Add Model Router profile to `milimo-compatibility.json` with per-claw tolerance settings |
| 3.1c | Validate all Milimo custom hosts against NemoClaw's SSRF endpoint validation (`ssrf.ts`) |
| 3.1d | Add `github` preset to Milimo's Hermes onboarding defaults (not in any baseline tier automatically) |
| 3.1e | Default `NEMOCLAW_SANDBOX_NAME=milimo-hermes` to avoid collision with default `hermes` sandbox |

**Corrected onboarding command throughout all Phase 3 artifacts:** use `nemohermes onboard --name milimo-hermes --from ./milimo-hermes-sandbox/Dockerfile`, not `nemoclaw onboard --profile hermes-milimo`.

---

### Phase 4: OpenClaw Preservation (Week 1, ongoing)

No changes. All components remain ✅ Unchanged.

Add: Backport `SchedulerInterface` abstract base to `evolution_cycle.py` in `milimo-core` for shared evolution logic.

---

### Phase 5: CI/CD & Shared Tooling (Week 4–5)

Original tasks 5.1–5.5 stand. Add:

| Added Task | Description |
|------------|-------------|
| 5.6 | Define Hermes test pyramid: unit (plugin registration, handler tool schema), integration (mock Hermes gateway), smoke (`NEMOCLAW_POLICY_TIER=restricted nemohermes onboard --non-interactive`) |
| 5.7 | Add `milimo-core` coverage gate before extraction cutover |
| 5.8 | Resolve `uv.lock` / root `pyproject.toml` vs. `milimo-core/pyproject.toml` workspace layout |
| 5.9 | CI env vars for Hermes non-interactive: `NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1`, `NEMOCLAW_POLICY_TIER=restricted`, `NEMOCLAW_SANDBOX_NAME=milimo-hermes-ci` |
| 5.10 | Add egress host + binary allowlist validation test using the inventory from Pre-Phase |

---

### Phase 6: Documentation & UX (Week 5, new)

| Task | Description |
|------|-------------|
| 6.1 | Add `hermes-profile/` section to Obsidian vault: sandbox layout, claw handler mapping, `milimo-core` dep graph, updated sequencing rules, corrected CLI commands |
| 6.2 | Update `README.md`: dual-profile decision tree, `nemohermes onboard` command (not `--agent hermes`), Nous Portal OAuth vs. API-key feature matrix, `CHAT_UI_URL` for headless deployments |
| 6.3 | Update `CLAUDE.md` in vault: Hermes profile ground truth, naming conventions (`claw handlers` not `skills`) |
| 6.4 | `docs/adr/` with Architecture Decision Records for the four locked decisions (subagent isolation, War Room, packaging, sandbox naming) |
| 6.5 | Install wizard: prompt for `CHAT_UI_URL` on headless hosts, `SLACK_ALLOWED_CHANNELS` before image build, `NEMOCLAW_MODEL_ROUTER_PYTHON` if Model Router selected |

---

## Part 4: Answers to Open Questions (Updated)

| Question | Recommended Answer | Rationale |
|----------|-------------------|-----------|
| `milimo-core` packaging | Local editable (`pip install -e`) for dev; PyPI for distribution. Decide before Phase 1 ends — it determines Dockerfile. | Enables community adoption; PyPI means Dockerfile uses `pip install milimo-core` into `/opt/hermes/.venv` |
| Skill/claw handler granularity | One per claw (6) + `milimo-core-primitives` shared handler. Rename to "claw handlers" to avoid NemoClaw naming conflict. | Clean separation; naming hygiene critical for LLM-assisted debugging |
| Subagent isolation | Multi-sandbox per claw subagent | Preserves zero-trust file isolation |
| War Room for Hermes | Option B: `milimo_warroom` CLI + Hermes dashboard widget. Set `NEMOCLAW_HERMES_DASHBOARD_TUI=1` before onboarding. | Prebuilt TUI tab at `/opt/hermes/ui-tui`; build-time flag required |
| Migration path | OpenClaw stays, Hermes is additive | Correct — no forced migration |
| CI/CD dual-profile | Yes; use `NEMOCLAW_POLICY_TIER=restricted` and `NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1` for CI | Non-negotiable for release confidence |

---

## Risk Register (Updated)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Plugin installed as hot-loadable instead of image-resident | **Critical** | Correct in Phase 2.1 deliverable; use `--from` Dockerfile pattern |
| NemoClaw Hermes image contract broken (nemoclaw plugin removed, layers missing) | **Critical** | Dockerfile review gate; never remove `/sandbox/.hermes/plugins/nemoclaw` |
| Phase 1 extraction breaks `bridge_server.py` at import time | High | Shim re-export period + regression test gate (1.6–1.7) |
| Hermes credential model incompatibility with `service_factory` | High | `hermes_credential_adapter` with GitHub-specific `gh auth token` path (2.9) |
| `SLACK_ALLOWED_CHANNELS` not captured before image build | High | Install wizard prompts before `nemohermes onboard` fires (6.5) |
| `github` preset not applied → Build Claw network block | High | Add `github` to Milimo's Hermes onboarding defaults (3.1d) |
| Subagent stall detection fails under Hermes (Lucy gap) | High | `milimo_warroom` tool schema + polling design before Phase 2 |
| Sandbox name collision with existing `hermes` sandbox | Medium | Default `NEMOCLAW_SANDBOX_NAME=milimo-hermes` (3.1e) |
| Model Router fails on macOS Homebrew Python 3.14 | Medium | Pre-onboard Python probe in install script; fallback to single provider (Gap 9) |
| `CHAT_UI_URL` not set on headless host → dashboard unreachable | Medium | Install wizard detects headless environment and prompts (6.5) |
| Naming conflict: "skills" used for both NemoClaw agent skills and Milimo claw handlers | Medium | Rename Milimo's packages to "claw handlers" throughout codebase (Gap 12) |
| `phone_home_hosts` missing binary scope → policy silently blocks claw network calls | Medium | Binary-scoped policy spec in `milimo-mcp.yaml` (Gap 4, 3.1a) |
| Obsidian vault stale → LLM-assisted debugging gives wrong answers | Medium | Phase 6.1 vault update before any Hermes release |
| Nous Portal OAuth vs. API-key feature matrix not communicated | Low–Medium | Decision tree in README and onboarding wizard (Enhancement 8) |
| `uv.lock` conflict between root and `milimo-core` packages | Low–Medium | Explicit workspace layout doc (5.8) |

---

## Summary

The dual-track strategy is correct. Four items in the original plan were factually wrong based on the actual Hermes documentation — plugin installation method, binary-scoped network policy, Brave Search absence, and the `nemohermes` alias — and five additional gaps were found: sandbox name collision risk, Model Router Python requirement, headless `CHAT_UI_URL` handling, GitHub preset not in baseline, and the NemoClaw/Milimo "skills" naming conflict. All are now incorporated.

The three things that must be locked before writing Phase 2 code are: the `milimo-core` packaging decision (it determines the Dockerfile), the `hermes_credential_adapter` GitHub code path, and the `SLACK_ALLOWED_CHANNELS` capture in the install wizard (it's baked at image build time and can't be changed without a rebuild).

The strategic observation from the original report stands and is now better grounded: the OpenAI-compatible API endpoint on port `8642` is a distribution channel, not just an architecture detail. Any OpenAI-compatible client can point at a Milimo Hermes instance. That belongs in the README and positioning docs, not the quickstart footnotes.

*The milimo never stops. Work. Without working.*
