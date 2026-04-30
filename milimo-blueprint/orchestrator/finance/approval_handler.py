# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Approval Handler.

Handles all War Room approval interactions for Finance Claw actions.
Enforces two-stage invoice approval.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import json

from milimo_paths import claw_base

from .finance_init import FinanceOperationalLog, FinanceLogEntry
from .invoice_manager import Invoice, InvoiceManager


@dataclass
class ApprovalAction:
    """Approval action for War Room."""

    action_id: str
    invoice_id: str
    stage: Literal["review", "hold"]
    action_type: Literal["approve", "edit", "block", "release", "cancel"]
    timestamp: str
    operator: str
    details: dict


class FinanceApprovalHandler:
    """
    Handles all War Room approval interactions for Finance Claw actions.

    Enforces two-stage invoice approval.
    Stage 1 (REVIEW): content review — approve moves to HOLD, never sends
    Stage 2 (HOLD): transmission gate — release triggers Stripe send

    Every decision logged to decisions.log.
    """

    def __init__(
        self,
        invoice_manager: InvoiceManager,
        operational_log: FinanceOperationalLog,
        decisions_path: Path | None = None,
    ):
        self.invoice_manager = invoice_manager
        self.operational_log = operational_log
        self.decisions_path = (
            decisions_path or claw_base("finance") / "logs/decisions.log"
        )

    def queue_invoice_review(self, invoice: Invoice) -> str:
        """
        Add invoice to War Room REVIEW queue.

        Returns action_id.
        War Room card shows:
        Client, project description, line items, total,
        due date, payment risk score and level.
        Available actions: APPROVE, EDIT, BLOCK
        """
        action_id = f"review-{invoice.invoice_id}"

        review_entry = {
            "action_id": action_id,
            "invoice_id": invoice.invoice_id,
            "stage": "review",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "client_id": invoice.client_id,
                "project_id": invoice.project_id,
                "total": invoice.total,
                "risk_level": invoice.payment_risk_level,
            },
        }
        self._log_decision(review_entry)

        return action_id

    def queue_invoice_hold(self, invoice: Invoice) -> str:
        """
        Add approved invoice to War Room HOLD queue.

        Returns action_id.
        War Room card shows:
        "Invoice approved — ready to send to {client_id}"
        Amount and due date.
        Warning: "This will transmit the invoice via Stripe"
        Available actions: RELEASE HOLD (sends), CANCEL
        """
        action_id = f"hold-{invoice.invoice_id}"

        hold_entry = {
            "action_id": action_id,
            "invoice_id": invoice.invoice_id,
            "stage": "hold",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "client_id": invoice.client_id,
                "total": invoice.total,
                "due_date": invoice.due_date,
                "warning": "This will transmit the invoice via Stripe",
            },
        }
        self._log_decision(hold_entry)

        return action_id

    def handle_review_approve(self, action_id: str) -> None:
        """
        Handle REVIEW approve.

        Called on REVIEW approve.
        Delegates to invoice_manager.handle_stage1_approve().
        Queues HOLD action (Stage 2).
        Logs to decisions.log: REVIEW_APPROVED
        """
        invoice_id = action_id.replace("review-", "")

        invoice = self.invoice_manager.handle_stage1_approve(invoice_id)

        self.queue_invoice_hold(invoice)

        decision = {
            "action_id": action_id,
            "invoice_id": invoice_id,
            "stage": "review",
            "action_type": "approve",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "operator",
            "details": {"outcome": "moved_to_hold"},
        }
        self._log_decision(decision)

    def handle_review_edit(
        self,
        action_id: str,
        edited_line_items: list[dict],
        edited_total: float,
    ) -> None:
        """
        Handle REVIEW edit.

        Delegates to invoice_manager.handle_stage1_edit().
        Re-queues REVIEW with edited invoice.
        Logs to decisions.log: REVIEW_EDITED
        """
        invoice_id = action_id.replace("review-", "")

        self.invoice_manager.handle_stage1_edit(
            invoice_id, edited_line_items, edited_total
        )

        decision = {
            "action_id": action_id,
            "invoice_id": invoice_id,
            "stage": "review",
            "action_type": "edit",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "operator",
            "details": {
                "edited_total": edited_total,
                "line_items_count": len(edited_line_items),
            },
        }
        self._log_decision(decision)

    def handle_review_block(self, action_id: str, reason: str) -> None:
        """
        Handle REVIEW block.

        Delegates to invoice_manager.handle_stage1_block().
        Logs to decisions.log: REVIEW_BLOCKED
        """
        invoice_id = action_id.replace("review-", "")

        self.invoice_manager.handle_stage1_block(invoice_id, reason)

        decision = {
            "action_id": action_id,
            "invoice_id": invoice_id,
            "stage": "review",
            "action_type": "block",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "operator",
            "details": {"reason": reason},
        }
        self._log_decision(decision)

    def handle_hold_release(self, action_id: str, stripe_client) -> None:
        """
        Handle HOLD release.

        Called on HOLD release — THIS SENDS THE INVOICE.
        Delegates to invoice_manager.handle_stage2_hold_release().
        Logs to decisions.log: HOLD_RELEASED
        """
        invoice_id = action_id.replace("hold-", "")

        self.invoice_manager.handle_stage2_hold_release(invoice_id, stripe_client)

        decision = {
            "action_id": action_id,
            "invoice_id": invoice_id,
            "stage": "hold",
            "action_type": "release",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "operator",
            "details": {"outcome": "invoice_sent"},
        }
        self._log_decision(decision)

    def handle_hold_cancel(self, action_id: str) -> None:
        """
        Handle HOLD cancel.

        Cancel the HOLD — invoice stays in approved/ for future send.
        Does NOT delete — just removes from HOLD queue.
        Logs to decisions.log: HOLD_CANCELLED
        """
        invoice_id = action_id.replace("hold-", "")

        decision = {
            "action_id": action_id,
            "invoice_id": invoice_id,
            "stage": "hold",
            "action_type": "cancel",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "operator",
            "details": {"outcome": "invoice_stays_approved"},
        }
        self._log_decision(decision)

    def queue_overdue_review(self, invoice: Invoice, days_overdue: int) -> str:
        """
        Queue REVIEW action for first overdue.

        Shows: client, invoice amount, days overdue, risk level.
        Suggested actions: send reminder, escalate, write off.
        """
        action_id = f"overdue-review-{invoice.invoice_id}"

        decision = {
            "action_id": action_id,
            "invoice_id": invoice.invoice_id,
            "stage": "review",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "type": "overdue",
                "client_id": invoice.client_id,
                "amount": invoice.total,
                "days_overdue": days_overdue,
                "risk_level": invoice.payment_risk_level,
            },
        }
        self._log_decision(decision)

        return action_id

    def queue_overdue_hold(
        self, invoice: Invoice, days_overdue: int, overdue_count: int
    ) -> str:
        """
        Queue HOLD action for repeat overdue (2+ invoices).

        Requires explicit operator action — cannot be auto-dismissed.
        Shows: client, total outstanding amount, overdue history.
        """
        action_id = f"overdue-hold-{invoice.invoice_id}"

        decision = {
            "action_id": action_id,
            "invoice_id": invoice.invoice_id,
            "stage": "hold",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "type": "repeat_overdue",
                "client_id": invoice.client_id,
                "amount": invoice.total,
                "days_overdue": days_overdue,
                "overdue_count": overdue_count,
            },
        }
        self._log_decision(decision)

        return action_id

    def queue_margin_alert(
        self,
        project_id: str,
        expected_margin_pct: float,
        actual_margin_pct: float,
    ) -> str:
        """
        Queue REVIEW action for margin compression.

        Shows margin gap, no immediate action required.
        """
        action_id = f"margin-alert-{project_id}"

        decision = {
            "action_id": action_id,
            "invoice_id": "",
            "stage": "review",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "type": "margin_alert",
                "project_id": project_id,
                "expected_margin_pct": expected_margin_pct,
                "actual_margin_pct": actual_margin_pct,
                "gap": expected_margin_pct - actual_margin_pct,
            },
        }
        self._log_decision(decision)

        return action_id

    def queue_rate_recommendation(
        self, recommendation: str, suggested_rate: float, current_rate: float
    ) -> str:
        """
        Queue REVIEW action for rate optimization.

        Recommendation only — operator decides.
        """
        action_id = f"rate-rec-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        decision = {
            "action_id": action_id,
            "invoice_id": "",
            "stage": "review",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "type": "rate_recommendation",
                "recommendation": recommendation,
                "suggested_rate": suggested_rate,
                "current_rate": current_rate,
            },
        }
        self._log_decision(decision)

        return action_id

    def _log_decision(self, decision: dict) -> None:
        """Log decision to decisions.log with file locking."""
        import fcntl

        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.decisions_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(decision) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        entry = FinanceLogEntry(
            timestamp=decision["timestamp"],
            action_type=f"approval_{decision['stage']}_{decision['action_type']}",
            entity_id=decision.get("invoice_id", ""),
            amount=decision.get("details", {}).get("total", 0),
            outcome="logged",
            details=decision,
        )
        self.operational_log.append(entry)
