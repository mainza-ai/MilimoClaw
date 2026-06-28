# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Core Tools for Milimo Hermes Plugin.

Registers the following tools:
- milimo_status: Get status of all 6 claws
- milimo_warroom: War Room dashboard - HOLD queue, claw status, cost guard
- milimo_approve: Approve a pending item in HOLD queue
- milimo_veto: Veto/reject a pending item in HOLD queue
- delegate_task: Native Hermes delegation (wraps native capability)
"""

from typing import Any

from milimo_core.protocols.delegation import ClawTask, ClawResult


# Tool schemas using shared types from milimo-core

MILIMO_STATUS_SCHEMA = {
    "name": "milimo_status",
    "description": "Get status of all 6 Milimo claws (Build, Content, Ops, Analytics, Finance, Assistant)",
    "parameters": {
        "type": "object",
        "properties": {
            "detailed": {"type": "boolean", "default": False, "description": "Include detailed metrics"}
        },
        "required": []
    }
}

MILIMO_WARROOM_SCHEMA = {
    "name": "milimo_warroom",
    "description": "War Room operations - HOLD queue, claw status, cost guard, approve/veto",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "hold_queue", "approve", "veto", "cost_guard"],
                "description": "War Room action to perform"
            },
            "item_id": {"type": "string", "description": "ID of item to approve/veto (required for approve/veto)"},
            "reason": {"type": "string", "description": "Reason for approve/veto action"},
            "claw_task": {
                "type": "object",
                "description": "ClawTask for approve/veto with delegation",
                "properties": {
                    "claw": {"type": "string", "enum": ["build", "content", "ops", "analytics", "finance", "assistant"]},
                    "goal": {"type": "string"},
                    "context": {"type": "string", "default": ""},
                    "priority": {"type": "integer", "default": 0}
                }
            }
        },
        "required": ["action"]
    }
}

MILIMO_APPROVE_SCHEMA = {
    "name": "milimo_approve",
    "description": "Approve a pending item in HOLD queue. Optionally delegates to claw for execution.",
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string", "description": "ID of item to approve"},
            "reason": {"type": "string", "description": "Approval reason"},
            "delegate_to_claw": {
                "type": "string",
                "enum": ["build", "content", "ops", "analytics", "finance", "assistant"],
                "description": "Optionally delegate approved action to a claw"
            },
            "delegation_goal": {"type": "string", "description": "Goal for delegated claw execution"}
        },
        "required": ["item_id"]
    }
}

MILIMO_VETO_SCHEMA = {
    "name": "milimo_veto",
    "description": "Veto/reject a pending item in HOLD queue.",
    "parameters": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string", "description": "ID of item to veto"},
            "reason": {"type": "string", "description": "Veto reason"}
        },
        "required": ["item_id", "reason"]
    }
}

# Delegate task tool - wraps native Hermes delegate_task capability
DELEGATE_TASK_SCHEMA = {
    "name": "delegate_task",
    "description": "Execute multiple claw tasks in parallel using Hermes native delegation. Each subagent runs in isolated context with restricted toolsets.",
    "parameters": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claw": {"type": "string", "enum": ["build", "content", "ops", "analytics", "finance", "assistant"]},
                        "goal": {"type": "string"},
                        "context": {"type": "string", "default": ""},
                        "priority": {"type": "integer", "default": 0}
                    },
                    "required": ["claw", "goal"]
                },
                "minItems": 1,
                "maxItems": 6
            }
        },
        "required": ["tasks"]
    }
}


# Tool handlers

async def handle_milimo_status(ctx: Any, detailed: bool = False) -> dict:
    """Get status of all 6 claws."""
    # Query each claw for status
    # This would integrate with actual claw instances
    claws = ["build", "content", "ops", "analytics", "finance", "assistant"]
    return {
        "status": "operational",
        "claws": {claw: {"status": "ready", "last_activity": None} for claw in claws},
        "detailed": detailed
    }


async def handle_milimo_warroom(ctx: Any, action: str, item_id: str = None,
                                reason: str = None, claw_task: dict = None) -> dict:
    """War Room operations."""
    if action == "status":
        return await handle_milimo_status(ctx, detailed=True)
    elif action == "hold_queue":
        return {"hold_queue": [], "message": "HOLD queue empty"}
    elif action == "cost_guard":
        return {"daily_tokens_used": 0, "daily_limit": 50000, "remaining": 50000}
    elif action in ("approve", "veto"):
        if not item_id:
            return {"error": f"item_id required for {action}"}
        return {"action": action, "item_id": item_id, "status": "completed"}
    return {"error": f"Unknown action: {action}"}


async def handle_milimo_approve(ctx: Any, item_id: str, reason: str = None,
                                delegate_to_claw: str = None, delegation_goal: str = None) -> dict:
    """Approve a pending item, optionally delegating to a claw."""
    result = {"action": "approve", "item_id": item_id, "status": "approved"}

    if delegate_to_claw and delegation_goal:
        # This would use the delegation adapter
        result["delegated_to"] = delegate_to_claw
        result["delegation_goal"] = delegation_goal

    return result


async def handle_milimo_veto(ctx: Any, item_id: str, reason: str) -> dict:
    """Veto/reject a pending item."""
    return {"action": "veto", "item_id": item_id, "reason": reason, "status": "rejected"}


async def handle_delegate_task(ctx: Any, tasks: list[dict]) -> list[dict]:
    """
    Native Hermes delegate_task tool handler.

    This wraps Hermes' native delegate_task capability. Each task in the list
    specifies a claw, goal, toolsets, and context. Hermes executes them in
    parallel subagents with isolated contexts.

    Args:
        tasks: List of task dicts with {claw, goal, context, priority}

    Returns:
        List of results from each subagent
    """
    from .delegation import HermesDelegateAdapter

    adapter = HermesDelegateAdapter()
    claw_tasks = [ClawTask(**t) for t in tasks]
    results = await adapter.delegate(claw_tasks)

    return [
        {"claw": r.claw, "output": r.output, "success": r.success, "error": r.error}
        for r in results
    ]


# Tool registration function

def register_core_tools(skill_registry: Any) -> None:
    """Register all core Milimo tools with the skill registry."""

    skill_registry.register_tool(
        name="milimo_status",
        description=MILIMO_STATUS_SCHEMA["description"],
        parameters=MILIMO_STATUS_SCHEMA["parameters"],
        handler=handle_milimo_status
    )

    skill_registry.register_tool(
        name="milimo_warroom",
        description=MILIMO_WARROOM_SCHEMA["description"],
        parameters=MILIMO_WARROOM_SCHEMA["parameters"],
        handler=handle_milimo_warroom
    )

    skill_registry.register_tool(
        name="milimo_approve",
        description=MILIMO_APPROVE_SCHEMA["description"],
        parameters=MILIMO_APPROVE_SCHEMA["parameters"],
        handler=handle_milimo_approve
    )

    skill_registry.register_tool(
        name="milimo_veto",
        description=MILIMO_VETO_SCHEMA["description"],
        parameters=MILIMO_VETO_SCHEMA["parameters"],
        handler=handle_milimo_veto
    )

    skill_registry.register_tool(
        name="delegate_task",
        description=DELEGATE_TASK_SCHEMA["description"],
        parameters=DELEGATE_TASK_SCHEMA["parameters"],
        handler=handle_delegate_task
    )


__all__ = [
    "register_core_tools",
    "handle_milimo_status",
    "handle_milimo_warroom",
    "handle_milimo_approve",
    "handle_milimo_veto",
    "handle_delegate_task",
    "MILIMO_STATUS_SCHEMA",
    "MILIMO_WARROOM_SCHEMA",
    "MILIMO_APPROVE_SCHEMA",
    "MILIMO_VETO_SCHEMA",
    "DELEGATE_TASK_SCHEMA",
]
