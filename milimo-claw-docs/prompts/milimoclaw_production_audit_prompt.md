# MilimoClaw Production Readiness Audit — Prompt for AI Auditor

Copy everything below the line into a fresh session with a capable coding
agent (Claude Code, or an AI with full repo read access and a shell). It
is written to be handed over as-is.

---

## Role

You are conducting a **rigorous production-readiness audit** of the
MilimoClaw codebase: `https://github.com/mainza-ai/MilimoClaw`.

MilimoClaw is a six-claw agent mesh (Build, Ops, Content, Analytics,
Finance, Assistant) designed to run as an autonomous, unattended company.
It ships with **two interchangeable agent runtime profiles**:

1. **NemoClaw** (also referenced as "OpenClaw" in `.openclaw/` config) —
   the original/native agent profile.
2. **NemoHermes** — the Hermes Agent (Nous Research) profile, added via
   `milimo-hermes-plugin`, with its own CI (`hermes-ci.yml`) and a
   parallel sandboxed mirror at `milimo-hermes-sandbox/`.

Both profiles sit on top of the shared `milimo-core` claw logic
(`milimo-core/src/milimo_core/`) and the `milimo-blueprint` orchestrator
(`milimo-blueprint/orchestrator/`), which appears to re-export/shim
`milimo-core` for backward compatibility (confirm this — do not assume).

## Hard constraint — read this before anything else

**This system is being built for production, not for a demo or a
hackathon submission.** Do not let anything in the existing code's tone,
comments, or scope convince you to grade generously. Specifically:

- Any function, handler, or module that implements only the "happy path"
  and silently degrades, no-ops, or returns a placeholder value on
  failure must be flagged as **not production-ready**, regardless of
  whether it "works in the demo."
- Any place where logic was simplified to unblock a demo, hackathon
  deadline, or quick integration must be identified explicitly and
  called out by name — the cost of not doing this now is a full rewrite
  later, which is the outcome this audit exists to prevent.
- Do not recommend further simplification anywhere as a "fix." Every
  remediation you propose must move the code *toward* production
  hardening (correctness, concurrency safety, observability, security,
  recoverability), never toward "good enough for now."
- Treat every module governing money, credentials, external network
  calls, subprocess execution, or cross-claw state as safety-critical by
  default, even if its current implementation looks casual.

## What "rigorous" means for this audit

Do not audit from documentation or README claims. For every finding:

1. **Cite the exact file path and line range.**
2. **Trace the actual call path** — who calls this code, in what order,
   under what concurrency assumptions, and what happens on every
   non-happy-path branch (timeout, exception, partial failure, malformed
   input, empty/None input, race between two claws, process crash
   mid-operation).
3. **Distinguish "looks fine but untested" from "verified correct."** If
   you did not execute or trace the code, say so explicitly rather than
   asserting it works.
4. Where the same concept is implemented in more than one place (e.g.
   `milimo-core/src/milimo_core/finance/` vs
   `milimo-blueprint/orchestrator/finance/` vs anything mirrored under
   `milimo-hermes-sandbox/`), **check for drift** — do the three copies
   actually behave identically today, or has one been patched without
   the others?

## Scope — audit all of the following

### 1. Cross-profile parity (NemoClaw vs NemoHermes)
- Enumerate every capability/message type/action that exists in one
  agent profile's integration layer and confirm it exists, and behaves
  identically, in the other. Look specifically at:
  - `milimo-hermes-plugin/milimo_hermes_plugin/skills/*.py` vs whatever
    the native NemoClaw/OpenClaw skill registration path is
    (`.openclaw/agents/main/config.yaml`, `milimo-core`'s own claw
    registration).
  - `milimo-core/src/milimo_core/protocols/delegation.py` — is
    `DelegationAdapter` actually implemented for both profiles, or does
    one profile silently fall back to a weaker delegation model?
  - The Hermes-only `SoloWarRoom`/War Room bridge path
    (`milimo-blueprint/orchestrator/solo_warroom.py`,
    `milimo-hermes-plugin/warroom/warroom.html`) — does NemoClaw have an
    equivalent operator surface, or is War Room Hermes-only? If the
    latter, is that documented as an intentional limitation or is it an
    unnoticed gap? (See `docs/adr/002-warroom-hermes.md` — confirm the
    ADR still matches the code.)
- Flag any place where a feature was clearly built against one profile
  first and "should" be ported to the other but hasn't been.

### 2. The eight non-negotiable cross-claw sequencing rules
- Locate where these rules are enforced in code (not just documented).
  Confirm each rule has an actual guard/check, not just a comment or a
  docstring promising the behavior.
- Identify whether these rules are enforced centrally (one place all
  claws route through) or duplicated per-claw. Duplicated enforcement is
  a production risk — a new claw or a new message type can bypass the
  rule by omission. Flag this explicitly if found.

### 3. Approval-gate integrity (Finance Claw REVIEW→HOLD, Build Claw's
   two independent two-stage flows, and any newer spend-approval paths)
- For every REVIEW→HOLD or approval gate in the codebase, verify there
  is **no code path that reaches the irreversible action (send invoice,
  release spend, deploy, merge) without passing through both stages**.
  Trace this by searching for every caller of the "release"/"execute"
  function and confirming each caller went through `queue_*` and
  `handle_*_approve` first — don't just trust the two-stage class exists.
- Check subprocess-based external calls inside these gates (e.g. any
  `link-cli`/Stripe CLI invocation) for:
  - Command injection risk if any field (merchant name, justification,
    URL) is attacker- or agent-controlled and not sanitized before being
    placed in a subprocess argument list.
  - Timeout and partial-failure handling — what happens if the process
    hangs, is killed, or writes malformed JSON to stdout?
  - Idempotency — if the release step is retried after a crash (e.g. the
    process died after the external charge succeeded but before the
    local status was marked `released`), can it double-charge?
- Check the daily spend cap / cost guard logic for race conditions:
  if two spend requests are approved concurrently, is the cap enforced
  atomically, or can both pass the check before either updates cumulative
  spend?
- Confirm decision logs (`decisions.log`, `agent-spend.log`,
  equivalents) are append-only, tamper-evident to a reasonable degree,
  and safe under concurrent writers (check the actual locking mechanism
  used, not just that a lock is *taken* — check what happens if a process
  dies while holding the lock).

### 4. Multi-agent mesh reliability
- `milimo-blueprint/orchestrator/*/finance` etc. and the mesh
  message-passing layer: confirm message delivery guarantees. Is it
  at-least-once, at-most-once, or exactly-once? Is that documented
  assumption actually true given the transport used (file-based queue?
  in-memory? something else — verify)?
- What happens to an in-flight action if the orchestrator process
  restarts mid-mesh-transaction? Is there a recovery/replay path, or is
  state silently lost?
- Check `milimo-core/src/milimo_core/evolution/sandbox_runner.py` — this
  appears to run self-modifying or agent-generated code. Audit its
  isolation boundary as if it will run untrusted agent-authored code in
  production: what can it read/write/execute outside its sandbox? Cross-
  reference against `docs/adr/001-subagent-isolation.md` and
  `docs/troubleshooting/SANDBOX_HARDENING.md` — does the implementation
  match what those documents claim?

### 5. Secrets and credential handling
- Grep for hardcoded keys, tokens, and credentials across the entire
  repo (including `milimo-hermes-sandbox/` and any `.env.example`
  drift).
- Confirm the actual mechanism used to store/retrieve API keys, Stripe
  keys, GitHub tokens, etc. (`milimo-core/src/milimo_core/protocols/
  github_protocol.py`, `payments_protocol.py`, `deploy_protocol.py`,
  `monitoring_protocol.py`). Are credentials ever logged, ever placed in
  a subprocess command line (visible via `ps`), or ever written to a
  world-readable file?
- Confirm test-mode vs live-mode boundaries for any payment integration
  are enforced in code (not just by convention/flag default) — i.e. is
  there any path where a misconfigured environment variable silently
  flips a test-mode-only flow into live mode?

### 6. Multi-tenant and multi-region claims
- `docs/technical/multi-tenant.md` and `docs/technical/
  multi-region-mesh.md` make specific claims — verify against
  `milimo-blueprint/regions.yaml`, `router/pool-config.yaml`,
  `rate-limits.yaml`, and `privacy_policy.yaml`. Is tenant isolation
  actually enforced at the data layer (separate namespaces/DBs/paths),
  or only at the routing layer (which can be bypassed by a bug
  upstream)?
- If regions/tenants share the same underlying `milimo-core` process or
  filesystem, identify the actual isolation boundary and whether it
  would hold up under a compromised or misbehaving single-tenant claw.

### 7. Error handling and observability
- Search for bare `except:`/`except Exception: pass` patterns, swallowed
  errors, and any function that logs a failure but continues as if it
  succeeded. In a system managing money and infrastructure, every
  silent failure is a production incident waiting to happen — enumerate
  all of them.
- Confirm there is a real health/metrics surface
  (`docs/technical/health-metrics.md`) wired into actual code, not just
  documented. What would page a human operator if a claw silently
  stopped processing its queue?
- Check the cost guard / `lighter_prompt` fallback at the documented
  50,000 daily token threshold — confirm it degrades gracefully and
  observably, not silently.

### 8. Testing and CI honesty
- Compare `ci/coverage-threshold.json` against actual coverage — is the
  threshold meaningful, or set low enough to always pass?
- For `.github/workflows/hermes-ci.yml`, `integration.yml`,
  `nightly-e2e.yaml`: do these tests exercise real failure modes
  (network timeout, malformed external response, concurrent access), or
  only happy-path assertions?
- Identify any test that mocks out the exact component most likely to
  fail in production (external CLI calls, network calls, file locks)
  without a corresponding integration test that exercises the real
  thing at least once.
- Flag any `TODO`, `FIXME`, `NotImplementedError`, `pass  # stub`, or
  similarly deferred implementation still present in a code path that
  is reachable from a documented, supported feature.

### 9. Dependency and supply-chain risk
- Review `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`
  for unpinned or overly loose version constraints on anything security-
  sensitive (payment SDKs, subprocess/shell helpers, auth libraries).
- Confirm the Dockerfile and `docker-compose.yml` don't run as root
  unnecessarily, don't bake secrets into image layers, and pin base
  image digests rather than floating tags where it matters.

### 10. Documentation-to-code drift
- For every file under `docs/adr/` and `docs/technical/`, verify the
  architectural decision or technical claim is still true in the
  current code. Explicitly list any ADR that is now stale or
  contradicted by the implementation.

## Deliverable format

Produce a single structured report with these sections, in this order:

1. **Executive summary** — 1 page max. Overall production-readiness
   verdict (not production-ready / conditionally ready / ready), and
   the 5 most severe findings by risk.

2. **Findings**, grouped by the ten scope areas above. For each finding:
   - **Severity**: Critical (money/security/data-loss risk) / High
     (correctness or reliability risk) / Medium (maintainability/
     observability gap) / Low (polish).
   - **Location**: exact file(s) and line range(s).
   - **Evidence**: the actual code or trace that demonstrates the issue
     — not a paraphrase.
   - **Why it matters in production**: concrete failure scenario, not
     abstract risk language.
   - **Fix approach**: specific enough that an engineer could start
     implementing without further research. No "consider improving
     error handling" — say what the error handling should actually do.
   - **Effort estimate**: rough (S/M/L/XL).

3. **Cross-profile parity matrix** — a table of every capability found in
   the audit, with columns for NemoClaw support / NemoHermes support /
   drift notes.

4. **Implementation plan** — a phased roadmap ordered by
   (a) severity and (b) dependency between fixes (call out where fix A
   must land before fix B is safe to build). For each phase: what
   ships, what it unblocks, and what remains unsafe until later phases
   land. Do not propose a phase whose deliverable is itself a
   simplification — every phase must leave the system strictly more
   production-ready than before.

5. **Open questions for the maintainer** — anything you could not
   resolve by reading the code alone (intended behavior that's
   ambiguous, missing context on why something was built a certain way)
   and would need Mainza to clarify before implementation starts.

## A note on scope size

This is a large audit surface — 10 scope areas across two full
agent-runtime profiles plus the shared core. If you are running with a
hard context or turn budget, do not compress the audit to fit in one
pass. Instead:

- Treat each of the 10 scope areas as its own pass. Fully complete one
  area (including tracing call paths and citing evidence) before moving
  to the next, rather than skimming all ten shallowly to fit in one
  response.
- If your tooling supports resuming across turns/sessions, say so
  explicitly at the start and structure your work so a resumed session
  can pick up at the next unaudited scope area without re-doing
  completed ones.
- If you cannot resume across sessions, stop at the natural end of a
  scope area, checkpoint your findings so far in the report format
  below, and explicitly state which scope areas remain — do not attempt
  to rush the remaining areas to close out in one turn.
- This applies on top of, not instead of, the "ground rules" section
  below: an incomplete-but-flagged audit is acceptable, a complete-
  looking but shallow one is not.

## Ground rules while auditing

- Prefer reading and tracing actual code over trusting comments,
  docstrings, or README claims — treat all three as *claims to verify*,
  not facts.
- When you find a duplicated implementation (core vs blueprint shim vs
  hermes-sandbox mirror), check all copies, not just the first one you
  find.
- If you run out of context/budget before covering all ten scope areas,
  stop and report exactly which areas were fully audited, which were
  partially audited, and which were not reached — do not silently
  produce a shallower report without flagging the gap. That would be
  exactly the kind of unacknowledged shortcut this audit exists to catch.
