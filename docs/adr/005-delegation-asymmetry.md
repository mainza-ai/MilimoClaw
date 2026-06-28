# ADR 005: Delegation Adapter Intentional Asymmetry

**Status**: Accepted
**Date**: 2026-06-27
**Deciders**: Mainza Kangombe

## Context

MilimoClaw defines a `DelegationAdapter` abstract base class in `milimo-core/protocols/delegation.py`:

```python
class DelegationAdapter(ABC):
    @abstractmethod
    async def delegate(self, tasks: list[ClawTask]) -> list[ClawResult]: ...
    @abstractmethod
    async def delegate_single(self, task: ClawTask) -> ClawResult: ...
```

This interface is clean, typed, and awaitable — perfect for the Hermes profile's native `delegate_task` tool which returns `list[Result]` directly.

However, the OpenClaw profile's parallelism primitive (`sessions_spawn`) operates on a fundamentally different execution model:
- Non-blocking fire-and-forget
- Results announce back to parent session asynchronously
- No direct return value — parent must listen for announcements
- LLM controls when/whether to spawn children (non-deterministic)

## Decision

**Do not force OpenClaw's `sessions_spawn` into the `DelegationAdapter` ABC.**

The `DelegationAdapter` ABC defines the **Hermes-profile contract**. The OpenClaw `mesh.py` implements equivalent parallelism via `sessions_spawn` under a different execution model. Formal unification is deferred until a third profile or cross-profile test harness requires it.

## Rationale

Forcing `sessions_spawn` into `async def delegate(...) -> list[ClawResult]` would require:
1. A polling wrapper that waits for child announcements
2. Correlation logic to match announcements to original tasks
3. Timeout handling for children that never complete
4. Error propagation from non-deterministic flow

This adds significant complexity with **no current payoff** because:
- No code currently needs to call `delegate()` on both profiles interchangeably
- The War Room tools only run on Hermes profile
- Unit tests use `MockDelegationAdapter` which is profile-agnostic
- OpenClaw's existing `mesh.py` works correctly for its use cases

## When to Revisit

Formalize a unified `DelegationAdapter` implementation when:
1. A third profile (e.g., bare Python runner, Claude Code integration) needs the same interface
2. A cross-profile test harness needs to run identical tests against both profiles
3. A meta-orchestration layer (Planning Claw) needs to delegate on both profiles

Until then, document the asymmetry explicitly and keep `mesh.py` as-is.

## Related ADRs
- ADR 001: Subagent Isolation Model
