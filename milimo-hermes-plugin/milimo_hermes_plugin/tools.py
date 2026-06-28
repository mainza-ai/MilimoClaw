# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Core Tools for Milimo Hermes Plugin.

Registers the following tools:
- milimo_status: Get status of all 6 Milimo claws
- milimo_warroom: War Room dashboard - HOLD queue, claw status, cost guard
- milimo_approve: Approve a pending item in HOLD queue
- milimo_veto: Veto/reject a pending item in HOLD queue
- delegate_task: Native Hermes delegation (wraps native capability)
"""

from typing import Any

from milimo_core.protocols.delegation import ClawTask, ClawResult
from milimo_core.ops.approval_handler import OpsApprovalHandler, OpsApprovalAction
from milimo_core.cost_guard import get_cost_guard
from milimo_core.milimo_paths import CLAWS_DIR
from milimo_core import WarRoomNotifier, get_warroom_notifier, init_warroom_notifier, NotificationPayload


# Global references initialized by plugin
_claw_launcher = None
_approval_handler: OpsApprovalHandler | None = None
_cost_guard = None
_warroom_notifier = None


def set_claw_launcher(launcher: Any) -> None:
    """Set the claw launcher instance for status queries."""
    global _claw_launcher
    _claw_launcher = launcher


def set_approval_handler(handler: OpsApprovalHandler) -> None:
    """Set the approval handler for HOLD/REVIEW queue operations."""
    global _approval_handler
    _approval_handler = handler


def set_cost_guard(cg: Any) -> None:
    """Set the cost guard instance."""
    global _cost_guard
    _cost_guard = cg


def set_warroom_notifier(notifier: WarRoomNotifier | None = None) -> None:
    """Set or initialize the War Room notifier."""
    global _warroom_notifier
    if notifier:
        _warroom_notifier = notifier
    else:
        _warroom_notifier = init_warroom_notifier()


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
    """Get status of all 6 claws from the claw launcher."""
    if _claw_launcher is None:
        # Fallback to basic status
        claws = ["build", "content", "ops", "analytics", "finance", "assistant"]
        return {
            "status": "operational",
            "claws": {claw: {"status": "ready", "last_activity": None} for claw in claws},
            "detailed": detailed
        }

    try:
        status = _claw_launcher.status()
        if not detailed:
            # Simplified status
            return {
                "status": "operational" if status.get("running") else "stopped",
                "claws": status.get("claws", {}),
                "launcher_pid": status.get("launcher_pid"),
                "timestamp": status.get("timestamp"),
            }
        return status
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_milimo_warroom(ctx: Any, action: str, item_id: str = None,
                                reason: str = None, claw_task: dict = None) -> dict:
    """War Room operations."""
    if action == "status":
        return await handle_milimo_status(ctx, detailed=True)

    elif action == "hold_queue":
        if _approval_handler is None:
            return {"hold_queue": [], "review_queue": [], "message": "Approval handler not initialized"}

        hold_items = _approval_handler.get_hold_queue()
        review_items = _approval_handler.get_review_queue()

        # Check for urgency flags and notify
        if _warroom_notifier:
            for item in hold_items:
                if item.urgency_flag:
                    _warroom_notifier.notify_hold_alert(
                        action_id=item.action_id,
                        action_type=item.action_type,
                        entity_id=item.entity_id,
                        claw_role="ops",  # Ops handles approvals
                        urgency=item.urgency_flag,
                    )

        return {
            "hold_queue": [item.to_dict() for item in hold_items],
            "review_queue": [item.to_dict() for item in review_items],
            "total_hold": len(hold_items),
            "total_review": len(review_items),
        }

    elif action == "cost_guard":
        cg = _cost_guard or get_cost_guard()
        usage = cg.get_detailed_usage()

        # Check if we should notify
        if _warroom_notifier:
            summary = usage.get("summary", {})
            if summary.get("alert_triggered"):
                _warroom_notifier.notify_cost_guard(
                    tokens_used=summary.get("total_tokens", 0),
                    limit=summary.get("daily_limit", 50000),
                    percentage=summary.get("percent_used", 0),
                    status="alert",
                )
            elif summary.get("warning_triggered"):
                _warroom_notifier.notify_cost_guard(
                    tokens_used=summary.get("total_tokens", 0),
                    limit=summary.get("daily_limit", 50000),
                    percentage=summary.get("percent_used", 0),
                    status="warning",
                )

        return usage

    elif action in ("approve", "veto"):
        if not item_id:
            return {"error": f"item_id required for {action}"}

        if _approval_handler is None:
            return {"error": "Approval handler not initialized"}

        if action == "approve":
            result = _approval_handler.handle_approve(item_id, lambda: None)
            status = "approved" if result else "failed"

            # Notify on approve
            if _warroom_notifier and result:
                action_data = _approval_handler.get_action(item_id)
                if action_data:
                    _warroom_notifier.notify_hold_alert(
                        action_id=item_id,
                        action_type=action_data.action_type,
                        entity_id=action_data.entity_id,
                        claw_role="ops",
                        urgency=None,
                    )

            return {"action": "approve", "item_id": item_id, "status": status}

        else:  # veto
            result = _approval_handler.handle_block(item_id, reason or "No reason provided")
            status = "rejected" if result else "failed"

            # Notify on veto
            if _warroom_notifier and result:
                action_data = _approval_handler.get_action(item_id)
                if action_data:
                    _warroom_notifier.slack.send(NotificationPayload(
                        title="HOLD Item Vetoed",
                        message=f"Action `{item_id}` ({action_data.action_type}) was vetoed.",
                        level="warning",
                        metadata={"Action ID": item_id, "Reason": reason or "No reason provided"},
                    ))

            return {"action": "veto", "item_id": item_id, "status": status}

    return {"error": f"Unknown action: {action}"}


async def handle_milimo_approve(ctx: Any, item_id: str, reason: str = None,
                                delegate_to_claw: str = None, delegation_goal: str = None) -> dict:
    """Approve a pending item, optionally delegating to a claw."""
    if _approval_handler is None:
        return {"error": "Approval handler not initialized"}

    # Approve the item
    result = _approval_handler.handle_approve(item_id, lambda: None)
    if not result:
        return {"action": "approve", "item_id": item_id, "status": "failed", "error": "Item not found or approval failed"}

    response = {"action": "approve", "item_id": item_id, "status": "approved"}

    # Optionally delegate to a claw
    if delegate_to_claw and delegation_goal:
        from .delegation import HermesDelegateAdapter
        adapter = HermesDelegateAdapter()
        task = ClawTask(
            claw=delegate_to_claw,
            goal=delegation_goal,
            context=f"Approved from War Room: {reason or 'No reason provided'}",
            priority=1
        )
        try:
            results = await adapter.delegate([task])
            if results:
                response["delegated_to"] = delegate_to_claw
                response["delegation_goal"] = delegation_goal
                response["delegation_result"] = {
                    "claw": results[0].claw,
                    "output": results[0].output,
                    "success": results[0].success,
                    "error": results[0].error
                }
        except Exception as e:
            response["delegation_error"] = str(e)

    return response


async def handle_milimo_veto(ctx: Any, item_id: str, reason: str) -> dict:
    """Veto/reject a pending item."""
    if _approval_handler is None:
        return {"error": "Approval handler not initialized"}

    result = _approval_handler.handle_block(item_id, reason)
    return {
        "action": "veto",
        "item_id": item_id,
        "reason": reason,
        "status": "rejected" if result else "failed"
    }


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
    "set_claw_launcher",
    "set_approval_handler",
    "set_cost_guard",
    "MILIMO_STATUS_SCHEMA",
    "MILIMO_WARROOM_SCHEMA",
    "MILIMO_APPROVE_SCHEMA",
    "MILIMO_VETO_SCHEMA",
    "DELEGATE_TASK_SCHEMA",
]
