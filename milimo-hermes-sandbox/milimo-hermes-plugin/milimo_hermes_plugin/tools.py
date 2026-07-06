# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Core Tools for Milimo Hermes Plugin.

Registers the following tools:
- milimo_status: Get status of all 6 Milimo claws
- milimo_warroom: War Room dashboard - HOLD queue, claw status, cost guard
- milimo_approve: Approve a pending item in HOLD queue
- milimo_veto: Veto/reject a pending item in HOLD queue
- milimo_spend: Finance Claw agent-initiated spend flow (Stage 1 REVIEW + Stage 2 HOLD)
- delegate_task: Native Hermes delegation (wraps native capability)
"""

from typing import Any, Optional
import logging
import os
import shutil
import subprocess

logger = logging.getLogger("milimo.hermes.tools")

try:
    from milimo_core.protocols.delegation import ClawTask, ClawResult
    from milimo_core.ops.approval_handler import OpsApprovalHandler, OpsApprovalAction
    from milimo_core.cost_guard import get_cost_guard
    from milimo_core.milimo_paths import CLAWS_DIR
    from milimo_core import (
        WarRoomNotifier, get_warroom_notifier, init_warroom_notifier, NotificationPayload
    )
    from milimo_core.finance.spend_handler import SpendApprovalHandler, SpendRequest
    from milimo_core.finance.finance_init import FinanceOperationalLog
    _MILIMO_CORE_OK = True
except ImportError:
    _MILIMO_CORE_OK = False
    ClawTask = ClawResult = OpsApprovalHandler = OpsApprovalAction = None
    get_cost_guard = CLAWS_DIR = None
    WarRoomNotifier = get_warroom_notifier = init_warroom_notifier = NotificationPayload = None
    SpendApprovalHandler = SpendRequest = FinanceOperationalLog = None


# Global references initialized by plugin
_claw_launcher = None
_approval_handler: OpsApprovalHandler | None = None
_cost_guard = None
_warroom_notifier = None
_spend_handler: SpendApprovalHandler | None = None


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


def set_spend_handler(handler: SpendApprovalHandler | None = None) -> None:
    """Set or initialize the Finance Claw spend handler."""
    global _spend_handler
    _spend_handler = handler


def _get_spend_handler() -> SpendApprovalHandler:
    """Lazy-init the spend handler from env/defaults."""
    global _spend_handler
    if _spend_handler is None:
        if not _MILIMO_CORE_OK:
            raise RuntimeError(
                "milimo_core is not installed in this environment. "
                "Ensure the Dockerfile runs: uv pip install -e /opt/milimo-core/"
            )
        import os as _os
        operational_log = FinanceOperationalLog(
            CLAWS_DIR / "finance" / "logs" / "operational.log"
        )
        _spend_handler = SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=CLAWS_DIR / "finance" / "logs" / "decisions.log",
            spend_log_path=CLAWS_DIR / "finance" / "logs" / "agent-spend.log",
            daily_spend_cap_cents=int(
                _os.environ.get("MILIMO_DAILY_SPEND_CAP_CENTS", "10000")
            ),
            test_mode=_os.environ.get("MILIMO_SPEND_TEST_MODE", "true").lower()
            == "true",
        )
    return _spend_handler


_build_approval_handler: Any | None = None
_content_approval_handler: Any | None = None
_finance_invoice_handler: Any | None = None


def set_build_approval_handler(handler: Any | None = None) -> None:
    global _build_approval_handler
    _build_approval_handler = handler


def set_content_approval_handler(handler: Any | None = None) -> None:
    global _content_approval_handler
    _content_approval_handler = handler


def set_finance_invoice_handler(handler: Any | None = None) -> None:
    global _finance_invoice_handler
    _finance_invoice_handler = handler


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

MILIMO_SPEND_SCHEMA = {
    "name": "milimo_spend",
    "description": "Finance Claw agent-initiated spend flow via stripe-link-cli. Two-stage gate: Stage 1 REVIEW (is this purchase approved?), Stage 2 HOLD (ready to charge — creates Link spend request and pings user's phone).",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "queue_review",
                    "approve_review",
                    "block_review",
                    "release_hold",
                    "cancel_hold",
                    "status",
                ],
                "description": "Spend flow action to perform"
            },
            "spend_id": {"type": "string", "description": "Spend request ID to operate on (required for all actions except queue_review)"},
            "claw": {"type": "string", "enum": ["build", "content", "ops", "analytics", "finance", "assistant"], "description": "Requesting claw (required for queue_review)"},
            "merchant_name": {"type": "string", "description": "Merchant display name (required for queue_review)"},
            "merchant_url": {"type": "string", "description": "Merchant URL (required for queue_review)"},
            "amount_cents": {"type": "integer", "description": "Amount in cents (required for queue_review)"},
            "justification": {"type": "string", "description": "Justification text — must be at least 100 characters (required for queue_review)"},
            "payment_method_id": {"type": "string", "description": "Stripe Link payment method ID (required for queue_review)"},
            "credential_type": {"type": "string", "enum": ["card", "shared_payment_token"], "default": "card", "description": "Payment credential type (required for queue_review)"},
            "reason": {"type": "string", "description": "Reason for block/cancel actions"}
        },
        "required": ["action"]
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
        ops_hold: list[dict] = []
        ops_review: list[dict] = []
        if _approval_handler is not None:
            ops_hold = [item.to_dict() for item in _approval_handler.get_hold_queue()]
            ops_review = [item.to_dict() for item in _approval_handler.get_review_queue()]

        spend_review_queue: list[dict] = []
        spend_hold_queue: list[dict] = []
        if _spend_handler is not None:
            for spend_id, req in _spend_handler._requests.items():
                entry = {
                    "action_id": f"spend-review-{spend_id}",
                    "entity_id": spend_id,
                    "action_type": "spend_review" if req.status == "pending_review" else "spend_hold",
                    "status": req.status,
                    "summary": (
                        f"{req.claw} wants to buy from {req.merchant_name}: "
                        f"${req.amount_cents / 100:.2f} — "
                        f"{req.justification[:80]}..."
                        if len(req.justification) > 80 else req.justification
                    ),
                    "payload": {
                        "spend_id": spend_id,
                        "claw": req.claw,
                        "merchant_name": req.merchant_name,
                        "merchant_url": req.merchant_url,
                        "amount_cents": req.amount_cents,
                        "currency": req.currency,
                        "justification": req.justification,
                        "credential_type": req.credential_type,
                        "payment_method_id": req.payment_method_id,
                    },
                    "claw": "finance",
                }
                if req.status == "pending_review":
                    spend_review_queue.append(entry)
                elif req.status == "held":
                    spend_hold_queue.append(entry)

        build_review: list[dict] = []
        build_hold: list[dict] = []
        if _build_approval_handler is not None:
            for action in _build_approval_handler.get_all_pending_actions():
                entry = {
                    "action_id": action.action_id,
                    "entity_id": action.entity_id,
                    "action_type": action.action_type,
                    "status": action.mode.lower(),
                    "summary": action.summary,
                    "payload": action.metadata,
                    "claw": "build",
                }
                if action.mode == "REVIEW":
                    build_review.append(entry)
                elif action.mode == "HOLD":
                    build_hold.append(entry)

        finance_invoice_review: list[dict] = []
        finance_invoice_hold: list[dict] = []
        if _finance_invoice_handler is not None:
            for entry in _finance_invoice_handler.get_pending_reviews():
                finance_invoice_review.append(
                    {
                        "action_id": entry.get("action_id", ""),
                        "entity_id": entry.get("invoice_id", ""),
                        "action_type": entry.get("action_type", "invoice_review"),
                        "status": "pending_review",
                        "summary": (
                            f"Invoice {entry.get('invoice_id')}: "
                            f"${entry.get('details', {}).get('total', 0) / 100:.2f} "
                            f"(risk: {entry.get('details', {}).get('risk_level', 'unknown')})"
                        ),
                        "payload": entry.get("details", {}),
                        "claw": "finance",
                    }
                )
            for entry in _finance_invoice_handler.get_pending_holds():
                finance_invoice_hold.append(
                    {
                        "action_id": entry.get("action_id", ""),
                        "entity_id": entry.get("invoice_id", ""),
                        "action_type": entry.get("action_type", "invoice_hold"),
                        "status": "held",
                        "summary": (
                            f"Invoice {entry.get('invoice_id')} approved — "
                            f"${entry.get('details', {}).get('total', 0) / 100:.2f} "
                            f"(ready to send to {entry.get('details', {}).get('client_id', 'client')})"
                        ),
                        "payload": entry.get("details", {}),
                        "claw": "finance",
                    }
                )

        content_review: list[dict] = []
        if _content_approval_handler is not None:
            content_review = [
                {
                    "action_id": d.get("action_id", ""),
                    "entity_id": d.get("draft_id", ""),
                    "action_type": d.get("action_type", "draft_review"),
                    "status": "pending_review",
                    "summary": d.get("summary", ""),
                    "payload": d.get("payload", {}),
                    "claw": "content",
                }
                for d in _content_approval_handler.get_pending_drafts()
            ]

        # Check for urgency flags and notify
        if _warroom_notifier:
            for item in ops_hold + build_hold + finance_invoice_hold:
                if isinstance(item, dict) and item.get("urgency_flag"):
                    _warroom_notifier.notify_hold_alert(
                        action_id=item.get("action_id", ""),
                        action_type=item.get("action_type", ""),
                        entity_id=item.get("entity_id", ""),
                        claw_role=item.get("claw", "ops"),
                        urgency=item.get("urgency_flag"),
                    )
            for item in spend_hold_queue:
                _warroom_notifier.notify_hold_alert(
                    action_id=item["action_id"],
                    action_type=item["action_type"],
                    entity_id=item["entity_id"],
                    claw_role="finance",
                    urgency="spend_held",
                )

        hold_queue = (
            ops_hold + build_hold + finance_invoice_hold + spend_hold_queue
        )
        review_queue = (
            ops_review + build_review + finance_invoice_review + spend_review_queue + content_review
        )
        return {
            "hold_queue": hold_queue,
            "review_queue": review_queue,
            "total_hold": len(hold_queue),
            "total_review": len(review_queue),
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

        # Finance spend flow
        if isinstance(item_id, str) and item_id.startswith("spend-review-") and _spend_handler is not None:
            spend_id = item_id[len("spend-review-"):]
            req = _spend_handler._requests.get(spend_id)
            if not req:
                return {"action": action, "item_id": item_id, "status": "not_found", "error": f"Spend {spend_id} not found"}

            if action == "approve":
                if req.status != "pending_review":
                    return {"action": "approve", "item_id": item_id, "status": "invalid", "error": f"Cannot approve spend in status: {req.status}"}
                try:
                    hold_action_id = _spend_handler.handle_review_approve(item_id)
                    req.status = "held"
                    if _warroom_notifier:
                        _warroom_notifier.notify_hold_alert(
                            action_id=item_id,
                            action_type="spend_hold",
                            entity_id=spend_id,
                            claw_role="finance",
                            urgency="spend_review_approved",
                        )
                    return {"action": "approve", "item_id": item_id, "hold_action_id": hold_action_id, "spend_id": spend_id}
                except ValueError as ve:
                    return {"action": "approve", "item_id": item_id, "status": "failed", "error": str(ve)}

            else:  # veto
                if req.status != "pending_review":
                    return {"action": "veto", "item_id": item_id, "status": "invalid", "error": f"Cannot veto spend in status: {req.status}"}
                try:
                    _spend_handler.handle_review_block(item_id, reason or "vetoed from war room")
                    req.status = "blocked"
                    if _warroom_notifier:
                        _warroom_notifier.notify_hold_alert(
                            action_id=item_id,
                            action_type="spend_review_blocked",
                            entity_id=spend_id,
                            claw_role="finance",
                            urgency="spend_review_blocked",
                        )
                    return {"action": "veto", "item_id": item_id, "spend_id": spend_id}
                except ValueError as ve:
                    return {"action": "veto", "item_id": item_id, "status": "failed", "error": str(ve)}

        # Build approval flow (PR review/merge-hold, deploy hold)
        if _build_approval_handler is not None and isinstance(item_id, str) and (
            item_id.startswith("pr-review-")
            or item_id.startswith("pr-merge-hold-")
            or item_id.startswith("deploy-hold-")
        ):
            if action == "approve":
                result = _build_approval_handler.handle_approve(item_id)
                status = "approved" if result.executed else "failed"
                if _warroom_notifier and result.executed:
                    _warroom_notifier.notify_hold_alert(
                        action_id=item_id,
                        action_type=result.details.get("mode", "build"),
                        entity_id=item_id,
                        claw_role="build",
                        urgency=None,
                    )
                return {
                    "action": "approve",
                    "item_id": item_id,
                    "status": status,
                    "details": result.details,
                }
            else:  # veto
                result = _build_approval_handler.handle_block(item_id, reason or "vetoed from war room")
                status = "rejected" if result.executed else "failed"
                return {
                    "action": "veto",
                    "item_id": item_id,
                    "status": status,
                    "details": result.details,
                }

        # Finance invoice approval flow
        if _finance_invoice_handler is not None and isinstance(item_id, str):
            if item_id.startswith("review-"):
                if action == "approve":
                    try:
                        _finance_invoice_handler.handle_review_approve(item_id)
                        if _warroom_notifier:
                            _warroom_notifier.notify_hold_alert(
                                action_id=item_id,
                                action_type="invoice_hold",
                                entity_id=item_id.replace("review-", ""),
                                claw_role="finance",
                                urgency="invoice_review_approved",
                            )
                        return {"action": "approve", "item_id": item_id, "status": "moved_to_hold"}
                    except Exception as exc:
                        return {"action": "approve", "item_id": item_id, "status": "failed", "error": str(exc)}
                else:  # veto
                    try:
                        _finance_invoice_handler.handle_review_block(item_id, reason or "vetoed from war room")
                        return {"action": "veto", "item_id": item_id, "status": "blocked"}
                    except Exception as exc:
                        return {"action": "veto", "item_id": item_id, "status": "failed", "error": str(exc)}

            if item_id.startswith("hold-"):
                if action == "approve":
                    return {
                        "action": "approve",
                        "item_id": item_id,
                        "status": "requires_stripe_client",
                        "error": "Invoice HOLD release requires a Stripe client; use the MilimoClaw TUI to send.",
                    }
                else:  # veto/cancel hold
                    try:
                        _finance_invoice_handler.handle_hold_cancel(item_id)
                        return {"action": "veto", "item_id": item_id, "status": "hold_cancelled"}
                    except Exception as exc:
                        return {"action": "veto", "item_id": item_id, "status": "failed", "error": str(exc)}

        # Content draft approval flow
        if _content_approval_handler is not None and not item_id.startswith(("spend-review-", "pr-review-", "pr-merge-hold-", "deploy-hold-", "review-", "hold-")):
            pending = _content_approval_handler.get_pending_drafts()
            match = next((d for d in pending if d.get("draft_id") == item_id or d.get("action_id") == item_id), None)
            if match:
                if action == "approve":
                    try:
                        result = _content_approval_handler.handle_approve(
                            draft_id=item_id,
                            action_id=item_id,
                        )
                        status = "approved" if result.success else "failed"
                        if _warroom_notifier and result.success:
                            _warroom_notifier.notify_hold_alert(
                                action_id=item_id,
                                action_type="draft_approved",
                                entity_id=item_id,
                                claw_role="content",
                                urgency=None,
                            )
                        return {"action": "approve", "item_id": item_id, "status": status, "details": result.to_dict() if hasattr(result, "to_dict") else {}}
                    except Exception as exc:
                        return {"action": "approve", "item_id": item_id, "status": "failed", "error": str(exc)}
                else:  # veto
                    try:
                        result = _content_approval_handler.handle_block(
                            draft_id=item_id,
                            action_id=item_id,
                            reason=reason or "vetoed from war room",
                        )
                        status = "rejected" if result.success else "failed"
                        return {"action": "veto", "item_id": item_id, "status": status, "details": result.to_dict() if hasattr(result, "to_dict") else {}}
                    except Exception as exc:
                        return {"action": "veto", "item_id": item_id, "status": "failed", "error": str(exc)}

        # Fallback to Ops approval handler
        if _approval_handler is None:
            return {"error": "Approval handler not initialized"}

        if action == "approve":
            result = _approval_handler.handle_approve(item_id, lambda: None)
            status = "approved" if result else "failed"

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
        adapter = HermesDelegateAdapter(ctx)
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


def _extract_device_url(text: str) -> str | None:
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            return line
    return None


_LINK_CLI_PREFIX = "/sandbox/.npm-global"
_HAVE_LINK_CLI: bool | None = None


def _ensure_link_cli() -> dict | None:
    """Resolve the ``link-cli`` binary path.

    Checks the default ``shutil.which`` lookup first and returns ``None`` when
    the binary is available. Otherwise attempts a one-shot self-healing
    install into ``/sandbox/.npm-global`` — a sandbox-user-writable prefix
    that is unaffected by the root-owned npm global directory — prepends the
    resulting ``bin`` directory to PATH, and re-checks.  The result is cached
    in ``_HAVE_LINK_CLI`` so repeated spend calls do not retry the install.
    """
    global _HAVE_LINK_CLI
    if _HAVE_LINK_CLI is not None:
        return None if _HAVE_LINK_CLI else {
            "error": "link_cli_not_available",
            "action_required": "link-cli binary is not installed and runtime install failed.",
        }

    resolved = shutil.which("link-cli")
    if resolved:
        _HAVE_LINK_CLI = True
        return None

    try:
        prefix = _LINK_CLI_PREFIX
        os.makedirs(prefix, exist_ok=True)
        install_cmd = [
            "npm", "install", "-g",
            "@stripe/link-cli@0.8.2",
            "--prefix", prefix,
        ]
        result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(os.path.join(prefix, "bin", "link-cli")):
            bin_dir = os.path.join(prefix, "bin")
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            resolved = shutil.which("link-cli")
            if resolved:
                _HAVE_LINK_CLI = True
                return None
    except Exception as exc:
        logger.debug("link-cli self-healing install failed: %s", exc)

    _HAVE_LINK_CLI = False
    return {
        "error": "link_cli_not_available",
        "action_required": (
            "link-cli is not installed. "
            "Rebuild the sandbox image or run: "
            f"npm install -g @stripe/link-cli@0.8.2 --prefix {_LINK_CLI_PREFIX}"
        ),
    }


def _check_link_cli_auth() -> dict | None:
    missing = _ensure_link_cli()
    if missing:
        return missing

    HEADLESS_AUTH_MODES = ("headless_service_account", "ci")
    headless = os.environ.get("MILIMO_LINK_CLI_AUTH_MODE", "").lower()
    if headless in HEADLESS_AUTH_MODES:
        try:
            proc = subprocess.run(
                ["link-cli", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            return {
                "error": "link_cli_not_available",
                "action_required": "link-cli binary is not installed or not on PATH.",
            }
        except subprocess.TimeoutExpired:
            return {
                "error": "link_cli_auth_check_timeout",
                "action_required": "link-cli auth status timed out. Check network and retry.",
            }

        if proc.returncode != 0 or "authenticated" not in (proc.stdout or "").lower():
            label = {
                "ci": "CI environment",
                "headless_service_account": "headless service account",
            }.get(headless, headless)
            return {
                "error": "link_cli_not_authenticated",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "action_required": (
                    f"[{label}] link-cli is not authenticated. "
                    "Set up service-account credentials or set "
                    "MILIMO_LINK_CLI_AUTH_MODE=environment to skip."
                ),
            }
        return None

    try:
        proc = subprocess.run(
            ["link-cli", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return {
            "error": "link_cli_not_available",
            "action_required": "link-cli binary is not installed or not on PATH.",
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "link_cli_auth_check_timeout",
            "action_required": "link-cli auth status timed out. Check network and retry.",
        }

    if proc.returncode != 0 or "authenticated" not in (proc.stdout or "").lower():
        device_url = _extract_device_url(proc.stdout) or _extract_device_url(proc.stderr)
        return {
            "error": "link_cli_not_authenticated",
            "approval_url": device_url,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "action_required": (
                "Visit the URL above and approve in your Link app, then retry."
                if device_url
                else "Run 'link-cli auth login' in an interactive shell, then retry."
            ),
        }
    return None


def _auto_spend_id(prefix: str = "spend") -> str:
    """Generate a short unique spend request ID."""
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def handle_milimo_spend(ctx: Any, action: str, spend_id: Optional[str] = None,
                               claw: Optional[str] = None,
                               merchant_name: Optional[str] = None,
                               merchant_url: Optional[str] = None,
                               amount_cents: Optional[int] = None,
                               justification: Optional[str] = None,
                               payment_method_id: Optional[str] = None,
                               credential_type: str = "card",
                               reason: Optional[str] = None) -> dict:
    """
    Finance Claw spend flow via stripe-link-cli.

    Stage 1 — REVIEW:
      queue_review   → add spend request to REVIEW queue
      approve_review → move REVIEW → HOLD (does NOT spend yet)
      block_review   → block/deny in REVIEW (purchase never happens)

    Stage 2 — HOLD:
      release_hold   → create Link spend-request, fire phone notification,
                       start background polling for final app approval
      cancel_hold    → cancel/release HOLD without spending
      status         → query spend request state by spend_id
    """
    missing = _ensure_link_cli()
    if missing:
        return missing
    auth_error = _check_link_cli_auth()
    if auth_error:
        return auth_error

    handler = _get_spend_handler()

    if action == "queue_review":
        missing = [f for f in ("claw", "merchant_name", "merchant_url", "amount_cents",
                               "justification", "payment_method_id") if not locals().get(f)]
        if missing:
            return {"error": f"Missing required fields for queue_review: {', '.join(missing)}"}

        if len(justification or "") < 100:
            return {"error": "justification must be at least 100 characters"}

        request = SpendRequest(
            spend_id=_auto_spend_id(),
            claw=claw,
            merchant_name=merchant_name,
            merchant_url=merchant_url,
            amount_cents=amount_cents,
            currency="USD",
            justification=justification,
            payment_method_id=payment_method_id,
            credential_type=credential_type,
        )
        try:
            action_id = handler.queue_spend_review(request)
        except ValueError as ve:
            return {"error": str(ve)}
        return {
            "action": "queue_review",
            "spend_id": request.spend_id,
            "action_id": action_id,
            "status": "pending_review",
        }

    if action == "approve_review":
        if not spend_id:
            return {"error": "spend_id is required for approve_review"}
        try:
            spend = handler._get_request(spend_id)
        except KeyError:
            return {"error": f"Spend request {spend_id} not found"}
        if spend.status not in ("pending_review",):
            return {"error": f"Cannot approve spend in status: {spend.status}"}
        try:
            hold_action_id = handler.handle_review_approve(
                f"spend-review-{spend_id}",
            )
        except ValueError as ve:
            return {"error": str(ve)}
        spend.status = "held"
        return {
            "action": "approve_review",
            "spend_id": spend_id,
            "status": "held",
            "hold_action_id": hold_action_id,
            "outcome": "moved_to_hold",
        }

    if action == "block_review":
        if not spend_id:
            return {"error": "spend_id is required for block_review"}
        if not reason:
            return {"error": "reason is required for block_review"}
        try:
            spend = handler._get_request(spend_id)
        except KeyError:
            return {"error": f"Spend request {spend_id} not found"}
        spend.status = "blocked"
        handler.handle_review_block(
            f"spend-review-{spend_id}",
            reason,
        )
        return {
            "action": "block_review",
            "spend_id": spend_id,
            "status": "blocked",
            "reason": reason,
        }

    if action == "release_hold":
        if not spend_id:
            return {"error": "spend_id is required for release_hold"}
        try:
            spend = handler._get_request(spend_id)
        except KeyError:
            return {"error": f"Spend request {spend_id} not found"}
        try:
            released = handler.handle_hold_release(
                f"spend-hold-{spend_id}",
                operator_id="system",
            )
        except ValueError as ve:
            return {"error": str(ve)}
        return {
            "action": "release_hold",
            "spend_id": spend_id,
            "status": released.status,
            "link_spend_request_id": released.link_spend_request_id,
            "outcome": (
                "release_initiated"
                if released.status == "released"
                else (
                    "notify_failed"
                    if released.status == "approval_pending"
                    else "blocked"
                )
            ),
        }

    if action == "cancel_hold":
        if not spend_id:
            return {"error": "spend_id is required for cancel_hold"}
        if not reason:
            reason = "Cancelled by operator"
        try:
            spend = handler._get_request(spend_id)
        except KeyError:
            return {"error": f"Spend request {spend_id} not found"}
        spend.status = "cancelled"
        handler.handle_hold_cancel(
            f"spend-hold-{spend_id}",
            reason,
        )
        return {
            "action": "cancel_hold",
            "spend_id": spend_id,
            "status": "cancelled",
            "reason": reason,
        }

    if action == "status":
        if not spend_id:
            return {"error": "spend_id is required for status"}
        try:
            spend = handler._get_request(spend_id)
        except KeyError:
            return {"error": f"Spend request {spend_id} not found"}
        return {
            "action": "status",
            "spend_id": spend_id,
            "status": spend.status,
            "link_spend_request_id": spend.link_spend_request_id,
            "claw": spend.claw,
            "merchant_name": spend.merchant_name,
            "merchant_url": spend.merchant_url,
            "amount_cents": spend.amount_cents,
            "currency": spend.currency,
        }

    return {"error": f"Unknown spend action: {action}"}


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

    adapter = HermesDelegateAdapter(ctx)
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
        name="milimo_spend",
        description=MILIMO_SPEND_SCHEMA["description"],
        parameters=MILIMO_SPEND_SCHEMA["parameters"],
        handler=handle_milimo_spend
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
    "handle_milimo_spend",
    "handle_delegate_task",
    "set_claw_launcher",
    "set_approval_handler",
    "set_cost_guard",
    "set_spend_handler",
    "MILIMO_STATUS_SCHEMA",
    "MILIMO_WARROOM_SCHEMA",
    "MILIMO_APPROVE_SCHEMA",
    "MILIMO_VETO_SCHEMA",
    "MILIMO_SPEND_SCHEMA",
    "DELEGATE_TASK_SCHEMA",
]
