# ADR 001: Subagent Isolation Model

**Status**: Accepted
**Date**: 2026-06-27
**Deciders**: Mainza Kangombe

## Context

MilimoClaw runs six autonomous claws (Build, Content, Ops, Analytics, Finance, Assistant) that need parallel execution with isolation. The dual-track architecture supports two NemoClaw profiles:

- **OpenClaw profile**: Original TUI + bridge server architecture
- **Hermes profile**: Web dashboard + OpenAI-compatible API + native tool gateway

Each profile has a fundamentally different parallelism primitive:

### OpenClaw: `sessions_spawn`
- Creates child agent sessions within a parent session
- Non-deterministic flow control — LLM decides when to spawn children
- Fire-and-forget: results announce back to parent asynchronously
- **Depth constraint**: `maxSpawnDepth` defaults to 1, maximum 2
  - Depth 0: parent agent (mesh coordinator)
  - Depth 1: claw agents
  - Depth 2: sub-agents of claws (cannot spawn further children)

### Hermes: `delegate_task`
- Structured, deterministic tool call
- Returns `list[Result]` directly — clean async/await contract
- Controlled by `DELEGATION_MAX_CONCURRENT_CHILDREN` (set to 6 for 6 claws)
- No depth restriction — sub-agents can delegate further if needed
- Each subagent gets isolated context, restricted toolsets, separate terminal session

## Decision

**Use native primitives for each profile. Do not build a custom isolation layer.**

- OpenClaw profile: Continue using existing `mesh.py` with `sessions_spawn`
- Hermes profile: Use native `delegate_task` via `HermesDelegateAdapter`

## Consequences

### Positive
- Zero custom isolation code to maintain
- Each profile uses its platform's intended parallelism model
- Hermes profile gains architectural advantage for deep orchestration (no depth ceiling)
- Clean separation: `DelegationAdapter` ABC in milimo-core defines Hermes contract; OpenClaw mesh is equivalent but different execution model

### Negative
- No single unified `DelegationAdapter` implementation across profiles
- Cross-profile test harness requires adapter-specific mocks
- OpenClaw depth limit blocks future meta-orchestration (Planning Claw, recursive evolution)

## OpenClaw Depth Constraint — Documented Proactively

OpenClaw's `sessions_spawn` is limited to `maxSpawnDepth: 2` (default: 1).
Current MilimoClaw architecture uses depth 1 (mesh coordinator → claws).
Depth 2 would be required for: nested claw delegation, planning agents, or recursive evolution cycles.

**If depth >1 is needed on OpenClaw in the future:**
- Set `maxSpawnDepth: 2` in agents.yaml
- Note: depth-2 sub-agents cannot spawn further children — hard ceiling
- Consider migrating to the Hermes profile where `delegate_task` has no equivalent depth restriction (controlled by `max_concurrent_children` only)

**This constraint is one architectural advantage of the Hermes profile** over OpenClaw for complex, deeply-nested multi-claw workflows.

## Related ADRs
- ADR 005: Delegation Adapter Intentional Asymmetry
