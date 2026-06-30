# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Hermes Delegate Adapter — Hermes-specific implementation of DelegationAdapter.

Uses native `delegate_task` tool for parallel claw execution.
DELEGATION_MAX_CONCURRENT_CHILDREN=6 should be set in Hermes config.
"""

from typing import Any

from milimo_core.protocols.delegation import DelegationAdapter, ClawTask, ClawResult


class HermesDelegateAdapter(DelegationAdapter):
    """
    Hermes-specific implementation using native delegate_task.

    The `delegate_task` tool is a native Hermes capability — called as a tool
    invocation, not imported. This keeps the adapter thin and profile-specific.

    Configuration (in Hermes config.yaml or milimo-compatibility.json):
    - delegation.max_concurrent_children: 6 (for 6 claws)
    - delegation.model: per-claw model overrides (cheaper for Content/Analytics)
    """

    def __init__(self, ctx: Any = None):
        self._ctx = ctx

    async def delegate(self, tasks: list[ClawTask]) -> list[ClawResult]:
        """
        Execute claw tasks in parallel via native delegate_task.

        Args:
            tasks: List of ClawTask objects with claw name, goal, context, priority

        Returns:
            List of ClawResult objects matching input order
        """
        if not tasks:
            return []

        # Build delegation task format for native delegate_task tool
        delegation_tasks = [
            {
                "goal": task.goal,
                "toolsets": self.CLAW_TOOLSETS.get(task.claw, ["file"]),
                "context": self.build_context(task),
            }
            for task in tasks
        ]

        # Invoke native Hermes delegate_task tool
        # This is called via the Hermes tool invocation layer
        results = await self._invoke_delegate_task(delegation_tasks)

        # Map results back to ClawResult objects
        return [
            ClawResult(
                claw=task.claw,
                output=result,
                success=result is not None and not (isinstance(result, dict) and result.get("error")),
                error=result.get("error") if isinstance(result, dict) else None,
            )
            for task, result in zip(tasks, results)
        ]

    async def delegate_single(self, task: ClawTask) -> ClawResult:
        """Execute a single claw task. Used for HOLD/REVIEW flows."""
        return (await self.delegate([task]))[0]

    async def _invoke_delegate_task(self, tasks: list[dict[str, Any]]) -> list[Any]:
        """
        Invoke native Hermes delegate_task tool.

        This method is called by the Hermes tool invocation layer when the
        `delegate_task` tool is invoked.
        """
        if not self._ctx:
            raise NotImplementedError(
                "HermesDelegateAdapter._invoke_delegate_task requires context (ctx) to execute."
            )

        try:
            from tools.registry import registry
            original_delegate_task = registry._tools.get("delegate_task") if registry else None
            original_handler = original_delegate_task.handler if original_delegate_task else None
        except ImportError:
            original_handler = None

        if original_handler:
            import inspect
            sig = inspect.signature(original_handler)
            kwargs = {}
            if "context" in sig.parameters:
                kwargs["context"] = self._ctx
            elif "ctx" in sig.parameters:
                kwargs["ctx"] = self._ctx

            args = {"tasks": tasks}
            if inspect.iscoroutinefunction(original_handler):
                result_str = await original_handler(args, **kwargs)
            else:
                result_str = original_handler(args, **kwargs)
        else:
            result_str = await self._ctx.dispatch_tool("delegate_task", {"tasks": tasks})

        import json
        if isinstance(result_str, str):
            try:
                return json.loads(result_str)
            except json.JSONDecodeError:
                return [result_str]
        return result_str


__all__ = ["HermesDelegateAdapter"]
