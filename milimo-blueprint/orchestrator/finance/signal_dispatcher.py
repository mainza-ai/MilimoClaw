# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Signal Dispatcher.

Sends all outbound messages from the Finance Claw to other claws.
All sends go through the inter-claw mesh gateway.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from finance.finance_init import FinanceOperationalLog, FinanceLogEntry


class MeshGateway(Protocol):
    """Protocol for the inter-claw mesh gateway."""

    def send(
        self,
        message_type: str,
        recipient_role: str,
        sender_role: str,
        payload: dict,
        message_id: str,
        timestamp: str,
    ) -> bool:
        """Send a message through the mesh gateway."""
        ...


class FinanceSignalDispatcher:
    """
    Sends all outbound messages from the Finance Claw to other claws.

    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to operational.log.
    Never raises on dispatch failure — logs error and continues.
    """

    def __init__(
        self,
        gateway: MeshGateway,
        operational_log: FinanceOperationalLog,
        mesh_path: Path | None = None,
    ):
        self.gateway = gateway
        self.operational_log = operational_log
        self.mesh_path = mesh_path or Path("/sandbox/mesh/outbox")

    def send_pricing_response(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float,
        scope_notes: str,
        data_quality: str = "complete",
    ) -> None:
        """
        Send pricing_response to Ops Claw.

        Args:
            project_id: Project identifier
            floor_price: Minimum acceptable price
            ceiling_price: Maximum price
            scope_notes: Notes about scope and assumptions
            data_quality: "complete" or "estimated" when no historical data exists
        """
        payload = {
            "project_id": project_id,
            "floor_price": floor_price,
            "ceiling_price": ceiling_price,
            "scope_notes": scope_notes,
            "data_quality": data_quality,
        }

        self._send("pricing_response", "ops", payload)

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pricing_response_sent",
            entity_id=project_id,
            amount=floor_price,
            outcome="success",
            details={"data_quality": data_quality, "ceiling": ceiling_price},
        )
        self.operational_log.append(entry)

    def send_invoice_ready(
        self,
        project_id: str,
        client_id: str,
        amount: float,
        invoice_id: str,
        due_date: str,
    ) -> None:
        """
        Send invoice_ready to Ops Claw.

        Fired AFTER Stage 1 REVIEW approval — before Stage 2 HOLD.
        Ops Claw uses this to update client record.

        Args:
            project_id: Project identifier
            client_id: Client identifier
            amount: Invoice total amount
            invoice_id: Invoice identifier
            due_date: ISO date string for payment due date
        """
        payload = {
            "project_id": project_id,
            "client_id": client_id,
            "amount": amount,
            "invoice_id": invoice_id,
            "due_date": due_date,
        }

        self._send("invoice_ready", "ops", payload)

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="invoice_ready_sent",
            entity_id=invoice_id,
            amount=amount,
            outcome="success",
            details={"project_id": project_id, "client_id": client_id},
        )
        self.operational_log.append(entry)

    def send_payment_overdue(
        self,
        client_id: str,
        invoice_id: str,
        days_overdue: int,
        amount: float,
        risk_level: str,
    ) -> None:
        """
        Send payment_overdue to Ops Claw.

        Fired IMMEDIATELY when due date passes — no weekly wait.

        Args:
            client_id: Client identifier
            invoice_id: Invoice identifier
            days_overdue: Number of days past due
            amount: Invoice amount
            risk_level: "low", "medium", or "high"
        """
        payload = {
            "client_id": client_id,
            "invoice_id": invoice_id,
            "days_overdue": days_overdue,
            "amount": amount,
            "risk_level": risk_level,
        }

        self._send("payment_overdue", "ops", payload)

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="payment_overdue_sent",
            entity_id=invoice_id,
            amount=amount,
            outcome="success",
            details={
                "client_id": client_id,
                "days_overdue": days_overdue,
                "risk_level": risk_level,
            },
        )
        self.operational_log.append(entry)

    def send_revenue_summary(
        self,
        week_total: float,
        week_over_week_pct: float,
        invoices_paid: int,
        invoices_pending: int,
    ) -> None:
        """
        Send revenue_summary to Analytics Claw.

        TOTALS ONLY — never include line items, client names, invoice IDs.

        Args:
            week_total: Total revenue for the week
            week_over_week_pct: Percentage change from previous week
            invoices_paid: Number of invoices paid this week
            invoices_pending: Number of invoices pending
        """
        payload = {
            "week_total": week_total,
            "week_over_week_pct": week_over_week_pct,
            "invoices_paid": invoices_paid,
            "invoices_pending": invoices_pending,
        }

        self._send("revenue_summary", "analytics", payload)

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="revenue_summary_sent",
            entity_id="weekly",
            amount=week_total,
            outcome="success",
            details={
                "week_over_week_pct": week_over_week_pct,
                "invoices_paid": invoices_paid,
                "invoices_pending": invoices_pending,
            },
        )
        self.operational_log.append(entry)

    def _send(
        self,
        message_type: str,
        recipient_role: str,
        payload: dict,
    ) -> None:
        """
        Core send via mesh gateway.

        Includes message_id (UUID), timestamp, sender_role="finance".
        On exception: log error, do not raise.
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            self.gateway.send(
                message_type=message_type,
                recipient_role=recipient_role,
                sender_role="finance",
                payload=payload,
                message_id=message_id,
                timestamp=timestamp,
            )
        except Exception as e:
            error_entry = FinanceLogEntry(
                timestamp=timestamp,
                action_type=f"{message_type}_send_failed",
                entity_id=message_id,
                amount=None,
                outcome="failed",
                details={
                    "error": str(e),
                    "recipient": recipient_role,
                    "message_type": message_type,
                },
            )
            self.operational_log.append(error_entry)
