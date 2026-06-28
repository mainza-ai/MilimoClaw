# Changelog

All notable changes to `milimo-core` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-06-27

### Added

#### Protocols (Extension Points for Third Profiles)
- **`protocols/delegation.py`** — `DelegationAdapter` ABC with `ClawTask`, `ClawResult` types. Defines the Hermes-profile contract for parallel claw execution via native `delegate_task`. OpenClaw profile uses equivalent `sessions_spawn` under a different execution model (documented in ADR 005).
- **`protocols/scheduling.py`** — `SchedulerInterface` ABC with `ScheduledJob` type. OpenClaw implements via `threading.Timer`; Hermes implements via native `cronjob`.

#### Credential Model
- **`hermes_credential_adapter.py`** — `HermesCredentialAdapter` class resolving credentials per NemoClaw Hermes model:
  - GitHub: calls `gh auth token` (not OpenShell gateway)
  - Stripe/Vercel/Sentry/NVIDIA: use OpenShell L7 proxy placeholders (`STRIPE_API_KEY`, `VERCEL_TOKEN`, `SENTRY_AUTH_TOKEN`, `NVIDIA_API_KEY`)

#### Shared Business Logic (Profile-Agnostic)
- **`DelegationAdapter.CLAW_TOOLSETS`** — Per-claw toolset mappings (`build: ["file","shell"]`, `content: ["web","file"]`, etc.)
- **`DelegationAdapter.CLAW_CONTEXTS`** — Per-claw system prompt context strings

#### Core Modules (Extracted from `milimo-blueprint/orchestrator/`)
All six claws + shared infrastructure with backward-compat shims in `milimo-blueprint/orchestrator/`:
- **Claws**: `build`, `content`, `ops`, `analytics`, `finance`, `assistant`
- **Contracts**: `ClawMessage`, `ContractValidator`, `ValidationResult`
- **Privacy Router**: `PrivacyRouter`, `InferenceBackend`, `RoutingDecision`
- **Inference Client**: `NvidiaInferenceClient`
- **Service Factory**: `create_github_client`, `create_vercel_client`, `create_sentry_client`, `create_stripe_client`
- **Provenance Signing**: `ProvenanceSigner`, `Attestation`, `generate_key_pair`
- **Tooling**: `ToolGenerator`, `ToolValidator`, `ToolSandbox`
- **Protocols**: GitHub, Deploy, Monitoring, Payments client protocols
- **Evolution**: `SandboxRunner`, `BacktestResult`, evolution cycle components

#### Test Infrastructure
- **`tests/mocks/mock_delegation.py`** — `MockDelegationAdapter` for unit testing `DelegationAdapter` consumers without Hermes runtime. Configurable preset results, injected failures, call recording.

### Deferred (Explicitly Not in 0.1.0)

- **OpenClaw `DelegationAdapter` implementation** — `milimo-blueprint/orchestrator/mesh.py` uses `sessions_spawn` (fire-and-forget, depth-limited). Formal unification deferred until third profile or cross-profile test harness requires it. Documented in ADR 005.
- **Model Router integration** — Hermes `delegation.model` overrides cover per-claw cost optimization. NemoClaw Model Router (prefill router checkpoint, Python 3.10–13 prerequisite) is opt-in for future phases.
- **War Room dashboard widget** — Hermes `/opt/hermes/ui-tui` internal bundle format not a public API. Standalone `/warroom` HTML endpoint provided instead.
- **PyPI publishing** — Local editable install (`pip install -e milimo-core/`) for development. PyPI release when API stable post-v0.2.0.

### Known Constraints

- **OpenClaw `maxSpawnDepth`** — Defaults to 1, maximum 2. Depth 2 sub-agents cannot spawn further children. Blocks future meta-orchestration (Planning Claw, recursive evolution) on OpenClaw. Hermes `delegate_task` has no equivalent depth restriction. See ADR 001.

---

## [Unreleased]

### Planned for 0.2.0 (Phase B)
- `EvolutionScheduler` using `SchedulerInterface` abstraction
- Hermes `HermesCronScheduler` with native `cronjob`
- SSRF validation for all egress hosts
- Slack/Telegram push in `milimo_warroom` tool
- CI/CD test pyramid (unit/integration/smoke)

---

## Migration Notes

### From `milimo-blueprint/orchestrator/` to `milimo-core`

All imports should migrate from:
```python
from orchestrator.contracts import ClawMessage
from orchestrator.build import BuildClaw
# etc.
```

To:
```python
from milimo_core import ClawMessage, BuildClaw
# or
from milimo_core.contracts import ClawMessage
from milimo_core.build import BuildClaw
```

**Backward compatibility**: `milimo-blueprint/orchestrator/` contains DeprecationWarning shims re-exporting from `milimo_core`. Zero test regressions (1,217 tests pass).

### Version Tagging Policy

- `v0.1.0` — First version with all extension point protocols (`DelegationAdapter`, `SchedulerInterface`) and credential adapter. Suitable for building third profiles.
- `v0.2.0` — Evolution scheduler abstraction + Hermes cron implementation.
- `v1.0.0` — API stable, PyPI publish, external adoption ready.

---

## Links

- [ADR 001: Subagent Isolation Model](docs/adr/001-subagent-isolation.md)
- [ADR 005: Delegation Adapter Asymmetry](docs/adr/005-delegation-asymmetry.md)
- [MilimoClaw Hermes Integration Report](milimo-claw-docs/reports/milimoclaw-hermes-integration-report.md)
