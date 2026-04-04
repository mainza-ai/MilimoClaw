# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Invoice Manager.

Manages the full invoice lifecycle.
CRITICAL: Two-stage approval is non-negotiable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol
import json
import uuid
import re

from .finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    FinanceLogEntry,
    PaymentEventsLog,
    PaymentEvent,
)
from .signal_dispatcher import FinanceSignalDispatcher


class InferenceClient(Protocol):
    """Protocol for inference client."""

    def complete(
        self,
        prompt: str,
        data_type: str,
        max_tokens: int = 800,
    ) -> str:
        """Complete a prompt with the model."""
        ...


class StripeClient(Protocol):
    """Protocol for Stripe client."""

    def create_invoice(
        self,
        customer_id: str,
        amount: float,
        currency: str,
        description: str,
        due_date: str,
    ) -> dict:
        """Create a Stripe invoice."""
        ...

    def send_invoice(self, invoice_id: str) -> dict:
        """Send a Stripe invoice."""
        ...


@dataclass
class InvoiceLineItem:
    """Line item in an invoice."""

    description: str
    quantity: float
    unit_price: float
    total: float


@dataclass
class Invoice:
    """Invoice data structure."""

    invoice_id: str
    project_id: str
    client_id: str
    line_items: list[InvoiceLineItem]
    subtotal: float
    total: float
    currency: str = "USD"
    payment_terms: str = "Net 14"
    due_date: str = ""
    payment_risk_score: float = 0.0
    payment_risk_level: str = "unknown"
    status: str = "pending"
    stripe_invoice_id: str | None = None
    generated_at: str = ""
    approved_at: str | None = None
    sent_at: str | None = None
    paid_at: str | None = None

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "invoice_id": self.invoice_id,
            "project_id": self.project_id,
            "client_id": self.client_id,
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": item.total,
                }
                for item in self.line_items
            ],
            "subtotal": self.subtotal,
            "total": self.total,
            "currency": self.currency,
            "payment_terms": self.payment_terms,
            "due_date": self.due_date,
            "payment_risk_score": self.payment_risk_score,
            "payment_risk_level": self.payment_risk_level,
            "status": self.status,
            "stripe_invoice_id": self.stripe_invoice_id,
            "generated_at": self.generated_at,
            "approved_at": self.approved_at,
            "sent_at": self.sent_at,
            "paid_at": self.paid_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Invoice":
        """Create from dict."""
        return cls(
            invoice_id=data["invoice_id"],
            project_id=data["project_id"],
            client_id=data["client_id"],
            line_items=[
                InvoiceLineItem(
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    total=item["total"],
                )
                for item in data.get("line_items", [])
            ],
            subtotal=data.get("subtotal", 0),
            total=data["total"],
            currency=data.get("currency", "USD"),
            payment_terms=data.get("payment_terms", "Net 14"),
            due_date=data.get("due_date", ""),
            payment_risk_score=data.get("payment_risk_score", 0.0),
            payment_risk_level=data.get("payment_risk_level", "unknown"),
            status=data.get("status", "pending"),
            stripe_invoice_id=data.get("stripe_invoice_id"),
            generated_at=data.get("generated_at", ""),
            approved_at=data.get("approved_at"),
            sent_at=data.get("sent_at"),
            paid_at=data.get("paid_at"),
        )


DEFAULT_PAYMENT_TERMS_DAYS = 14


class InvoiceManager:
    """
    Manages the full invoice lifecycle.

    CRITICAL: Two-stage approval is non-negotiable.
    Stage 1 (REVIEW approve) → moves to approved/ — does NOT send
    Stage 2 (HOLD release) → transmits via Stripe — only send trigger

    Any code path that sends an invoice without HOLD release is a bug.
    """

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        inference_client: InferenceClient,
        dispatcher: FinanceSignalDispatcher,
        payment_risk_scorer: Any,
        operational_log: FinanceOperationalLog,
        payment_events_log: PaymentEventsLog,
    ):
        self.fs = fs
        self.inference_client = inference_client
        self.dispatcher = dispatcher
        self.payment_risk_scorer = payment_risk_scorer
        self.operational_log = operational_log
        self.payment_events_log = payment_events_log

    def generate_invoice(
        self,
        project_id: str,
        client_id: str,
        delivered_at: str,
    ) -> Invoice:
        """
        Generate an invoice for a completed project.

        1. Load pricing estimate from pricing/estimates/{project_id}.json
        2. Load any scope notes from the estimate
        3. Generate invoice line items via inference (data_type="invoice_generation")
        4. Calculate: subtotal, total, due_date (today + 14 days)
        5. Score payment risk for this client
        6. Assign invoice_id (UUID)
        7. Write to invoices/pending/{invoice_id}.json
        8. Queue War Room REVIEW action via approval_handler
        9. Log: action_type="invoice_generated"
        10. Return Invoice
        """
        estimate_path = self.fs.get_pricing_estimate_path(project_id)
        estimate = {}
        if estimate_path.exists():
            estimate = json.loads(estimate_path.read_text())

        scope_description = estimate.get("scope_description", "Services rendered")
        estimated_total = estimate.get("ceiling_price", 0)
        if estimated_total == 0:
            estimated_total = estimate.get("floor_price", 1000)

        prompt = self._build_invoice_prompt(
            project_id, scope_description, estimated_total, delivered_at
        )

        line_items: list[InvoiceLineItem]
        try:
            output = self.inference_client.complete(
                prompt=prompt,
                data_type="invoice_generation",
                max_tokens=800,
            )
            line_items = self._parse_invoice_line_items(output)
        except Exception:
            line_items = [
                InvoiceLineItem(
                    description=f"Services rendered: {scope_description}",
                    quantity=1.0,
                    unit_price=estimated_total,
                    total=estimated_total,
                )
            ]

        subtotal = sum(item.total for item in line_items)
        invoice_id = f"inv-{uuid.uuid4().hex[:8]}"
        due_date = (datetime.now(timezone.utc) + timedelta(days=DEFAULT_PAYMENT_TERMS_DAYS)).strftime("%Y-%m-%d")

        risk_score = self.payment_risk_scorer.score(client_id)

        invoice = Invoice(
            invoice_id=invoice_id,
            project_id=project_id,
            client_id=client_id,
            line_items=line_items,
            subtotal=subtotal,
            total=subtotal,
            due_date=due_date,
            payment_risk_score=risk_score.score,
            payment_risk_level=risk_score.risk_level,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        invoice_path = self.fs.get_invoice_path("pending", invoice_id)
        invoice_path.parent.mkdir(parents=True, exist_ok=True)
        invoice_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="invoice_generated",
            entity_id=invoice_id,
            amount=invoice.total,
            outcome="success",
            details={
                "project_id": project_id,
                "client_id": client_id,
                "status": "pending",
            },
        )
        self.operational_log.append(entry)

        return invoice

    def handle_stage1_approve(self, invoice_id: str) -> Invoice:
        """
        Handle Stage 1 REVIEW approval.

        Called when operator approves Stage 1 REVIEW.
        1. Load invoice from invoices/pending/{invoice_id}.json
        2. Update status to "approved", approved_at = now
        3. Move file: pending/ → approved/{invoice_id}.json
        4. Remove from pending/
        5. Queue War Room HOLD action (Stage 2)
        6. Send invoice_ready to Ops Claw via dispatcher
        7. Log: action_type="invoice_stage1_approved"

        DO NOT SEND INVOICE HERE. HOLD QUEUE ONLY.
        """
        invoice = self.load_invoice(invoice_id, "pending")

        invoice.status = "approved"
        invoice.approved_at = datetime.now(timezone.utc).isoformat()

        approved_path = self.fs.get_invoice_path("approved", invoice_id)
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        pending_path = self.fs.get_invoice_path("pending", invoice_id)
        if pending_path.exists():
            pending_path.unlink()

        self.dispatcher.send_invoice_ready(
            project_id=invoice.project_id,
            client_id=invoice.client_id,
            amount=invoice.total,
            invoice_id=invoice.invoice_id,
            due_date=invoice.due_date,
        )

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="invoice_stage1_approved",
            entity_id=invoice_id,
            amount=invoice.total,
            outcome="success",
            details={"client_id": invoice.client_id},
        )
        self.operational_log.append(entry)

        return invoice

    def handle_stage1_edit(
        self,
        invoice_id: str,
        edited_line_items: list[dict],
        edited_total: float,
    ) -> Invoice:
        """
        Handle Stage 1 REVIEW edit.

        Load from pending/, apply edits, recalculate total.
        Save edited version back to pending/ (re-queue REVIEW).
        Log: action_type="invoice_edited"
        """
        invoice = self.load_invoice(invoice_id, "pending")

        invoice.line_items = [
            InvoiceLineItem(
                description=item["description"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total=item["quantity"] * item["unit_price"],
            )
            for item in edited_line_items
        ]
        invoice.subtotal = edited_total
        invoice.total = edited_total

        pending_path = self.fs.get_invoice_path("pending", invoice_id)
        pending_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="invoice_edited",
            entity_id=invoice_id,
            amount=edited_total,
            outcome="success",
            details={"line_items_count": len(edited_line_items)},
        )
        self.operational_log.append(entry)

        return invoice

    def handle_stage1_block(self, invoice_id: str, reason: str) -> None:
        """
        Handle Stage 1 REVIEW block.

        Move invoice from pending/ to a discarded state.
        Do not delete — archive with blocked status.
        Log: action_type="invoice_blocked", details={reason}
        """
        invoice = self.load_invoice(invoice_id, "pending")
        invoice.status = "blocked"

        pending_path = self.fs.get_invoice_path("pending", invoice_id)

        blocked_dir = self.fs.base / "invoices" / "blocked"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        blocked_path = blocked_dir / f"{invoice_id}.json"
        blocked_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        if pending_path.exists():
            pending_path.unlink()

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="invoice_blocked",
            entity_id=invoice_id,
            amount=invoice.total,
            outcome="blocked",
            details={"reason": reason, "client_id": invoice.client_id},
        )
        self.operational_log.append(entry)

    def handle_stage2_hold_release(
        self,
        invoice_id: str,
        stripe_client: StripeClient,
    ) -> Invoice:
        """
        Handle Stage 2 HOLD release.

        THIS IS THE ONLY PLACE AN INVOICE IS TRANSMITTED.

        1. Load invoice from invoices/approved/{invoice_id}.json
        2. Verify status == "approved" — raise if not
        3. Create Stripe invoice via Stripe API
        4. Send Stripe invoice to client
        5. Update invoice: status="sent", sent_at=now, stripe_invoice_id
        6. Move file: approved/ → sent/{invoice_id}.json
        7. Log to payment-events.log: invoice_sent
        8. Log: action_type="invoice_sent"

        On Stripe API failure: keep in approved/, retry logic in payment_monitor.
        """
        invoice = self.load_invoice(invoice_id, "approved")

        if invoice.status != "approved":
            raise ValueError(
                f"Invoice {invoice_id} is not in approved status (status: {invoice.status})"
            )

        try:
            stripe_result = stripe_client.create_invoice(
                customer_id=invoice.client_id,
                amount=invoice.total,
                currency=invoice.currency,
                description=f"Invoice {invoice_id} - {invoice.project_id}",
                due_date=invoice.due_date,
            )
            stripe_invoice_id = stripe_result.get("id", "")

            stripe_client.send_invoice(stripe_invoice_id)

            invoice.status = "sent"
            invoice.sent_at = datetime.now(timezone.utc).isoformat()
            invoice.stripe_invoice_id = stripe_invoice_id

            sent_path = self.fs.get_invoice_path("sent", invoice_id)
            sent_path.parent.mkdir(parents=True, exist_ok=True)
            sent_path.write_text(json.dumps(invoice.to_dict(), indent=2))

            approved_path = self.fs.get_invoice_path("approved", invoice_id)
            if approved_path.exists():
                approved_path.unlink()

            payment_event = PaymentEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="invoice_sent",
                invoice_id=invoice_id,
                client_id=invoice.client_id,
                amount=invoice.total,
                details={"stripe_invoice_id": stripe_invoice_id},
            )
            self.payment_events_log.append(payment_event)

            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="invoice_sent",
                entity_id=invoice_id,
                amount=invoice.total,
                outcome="success",
                details={"stripe_invoice_id": stripe_invoice_id},
            )
            self.operational_log.append(entry)

        except Exception as e:
            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="invoice_send_failed",
                entity_id=invoice_id,
                amount=invoice.total,
                outcome="failed",
                details={"error": str(e)},
            )
            self.operational_log.append(entry)
            raise

        return invoice

    def _build_invoice_prompt(
        self,
        project_id: str,
        scope_description: str,
        total_amount: float,
        delivered_at: str,
    ) -> str:
        """Build prompt for invoice line item generation."""
        return f"""Generate invoice line items for this completed project.

Project: {project_id}
Scope: {scope_description}
Total Amount: ${total_amount:.2f}
Delivered: {delivered_at}

Create line items that fairly represent the work done. Return JSON array:
[
  {{"description": "...", "quantity": 1.0, "unit_price": ..., "total": ...}},
  ...
]"""

    def _parse_invoice_line_items(self, inference_output: str) -> list[InvoiceLineItem]:
        """
        Parse inference output into InvoiceLineItem list.

        Fallback: single line item "Services rendered" if parse fails.
        Never return empty line items — always at least one item.
        """
        try:
            json_match = re.search(r"\[[\s\S]*\]", inference_output)
            if json_match:
                items_data = json.loads(json_match.group())
                return [
                    InvoiceLineItem(
                        description=item.get("description", "Services"),
                        quantity=float(item.get("quantity", 1)),
                        unit_price=float(item.get("unit_price", 0)),
                        total=float(item.get("total", 0)),
                    )
                    for item in items_data
                    if item.get("description")
                ]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        return [
            InvoiceLineItem(
                description="Services rendered",
                quantity=1.0,
                unit_price=0,
                total=0,
            )
        ]

    def get_pending_invoices(self) -> list[Invoice]:
        """Get all pending invoices."""
        return self._load_invoices_by_status("pending")

    def get_approved_invoices(self) -> list[Invoice]:
        """Get all approved invoices."""
        return self._load_invoices_by_status("approved")

    def get_sent_invoices(self) -> list[Invoice]:
        """Get all sent invoices."""
        return self._load_invoices_by_status("sent")

    def _load_invoices_by_status(self, status: Literal["pending", "approved", "sent", "paid", "overdue", "blocked"]) -> list[Invoice]:
        """Load all invoices with a given status."""
        invoices: list[Invoice] = []
        status_dir = self.fs.base / "invoices" / status
        if not status_dir.exists():
            return invoices

        for path in status_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                invoices.append(Invoice.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue

        return invoices

    def load_invoice(self, invoice_id: str, status: Literal["pending", "approved", "sent", "paid", "overdue", "blocked"]) -> Invoice:
        """Load an invoice by ID and status."""
        path = self.fs.get_invoice_path(status, invoice_id)
        if not path.exists():
            raise FileNotFoundError(f"Invoice {invoice_id} not found in {status}")

        data = json.loads(path.read_text())
        return Invoice.from_dict(data)
