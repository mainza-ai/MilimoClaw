# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Mock Delegation Adapter — Reusable mock for unit tests across all profiles.

The mock belongs in milimo-core/tests/ because it implements the
milimo_core.protocols.delegation.DelegationAdapter interface. Any profile
(milimo-hermes-plugin, future third profiles) can import this for unit tests
without requiring the Hermes runtime.
"""

from typing import Any
from dataclasses import dataclass, field

from milimo_core.protocols.delegation import DelegationAdapter, ClawTask, ClawResult


@dataclass
class MockDelegationConfig:
    """Configuration for MockDelegationAdapter behavior."""
    preset_results: dict[str, ClawResult] = field(default_factory=dict)
    fail_claws: set[str] = field(default_factory=set)
    delay_seconds: float = 0.0
    record_calls: bool = True


class MockDelegationAdapter(DelegationAdapter):
    """
    Reusable mock for DelegationAdapter unit tests.

    Configurable: inject expected results, simulate failures, record calls,
    add artificial delays for async testing.

    Usage:
        adapter = MockDelegationAdapter(
            preset_results={"finance": ClawResult(claw="finance", output="approved", success=True)},
            fail_claws={"analytics"},
            delay_seconds=0.1
        )
    """

    def __init__(self, config: MockDelegationConfig | None = None):
        self.config = config or MockDelegationConfig()
        self.calls: list[ClawTask] = []
        self.call_count = 0

    async def delegate(self, tasks: list[ClawTask]) -> list[ClawResult]:
        """Execute claw tasks with mock behavior."""
        if self.config.delay_seconds > 0:
            import asyncio
            await asyncio.sleep(self.config.delay_seconds)

        if self.config.record_calls:
            self.calls.extend(tasks)
            self.call_count += len(tasks)

        results = []
        for task in tasks:
            if task.claw in self.config.fail_claws:
                result = ClawResult(
                    claw=task.claw,
                    output=None,
                    success=False,
                    error=f"Injected failure for {task.claw}"
                )
            elif task.claw in self.config.preset_results:
                result = self.config.preset_results[task.claw]
            else:
                result = ClawResult(
                    claw=task.claw,
                    output={"status": "completed", "task": task.goal},
                    success=True
                )
            results.append(result)

        return results

    async def delegate_single(self, task: ClawTask) -> ClawResult:
        """Execute a single claw task."""
        return (await self.delegate([task]))[0]

    def reset(self) -> None:
        """Reset call history."""
        self.calls.clear()
        self.call_count = 0

    def get_calls_for_claw(self, claw: str) -> list[ClawTask]:
        """Get all calls made for a specific claw."""
        return [t for t in self.calls if t.claw == claw]

    def assert_called_with(self, claw: str, goal_contains: str | None = None) -> bool:
        """Assert that a call was made for a specific claw."""
        calls = self.get_calls_for_claw(claw)
        if not calls:
            return False
        if goal_contains:
            return any(goal_contains in c.goal for c in calls)
        return True


# Convenience factory functions for common test scenarios

def create_success_adapter() -> MockDelegationAdapter:
    """Create adapter that succeeds for all claws."""
    return MockDelegationAdapter()

def create_failing_adapter(*claws: str) -> MockDelegationAdapter:
    """Create adapter that fails for specified claws."""
    return MockDelegationAdapter(MockDelegationConfig(fail_claws=set(claws)))

def create_preset_adapter(**results: ClawResult) -> MockDelegationAdapter:
    """Create adapter with preset results for specific claws."""
    return MockDelegationAdapter(MockDelegationConfig(preset_results=results))

def create_delayed_adapter(delay: float) -> MockDelegationAdapter:
    """Create adapter with artificial delay for async timing tests."""
    return MockDelegationAdapter(MockDelegationConfig(delay_seconds=delay))


__all__ = [
    "MockDelegationAdapter",
    "MockDelegationConfig",
    "create_success_adapter",
    "create_failing_adapter",
    "create_preset_adapter",
    "create_delayed_adapter",
]
