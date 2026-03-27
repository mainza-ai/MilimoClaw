# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Payment Monitor.

Monitors payment status for all sent invoices via Stripe API.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Any, Protocol
import json

from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    FinanceLogEntry,
    PaymentEventsLog,
    PaymentEvent,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.invoice_manager import Invoice


class StripeClient(Protocol):
    """Protocol for Stripe client."""

    def get_invoice(self, invoice_id: str) -> dict:
        """Get invoice status from Stripe."""
        ...

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
class PaymentStatus:
    """Payment status for an invoice."""

    invoice_id: str
    stripe_invoice_id: str
    status: str
    amount_paid: float
    amount_due: float
    due_date: str
    days_overdue: int


CHECK_INTERVAL_HOURS = 24
STRIPE_RETRY_INTERVAL_MINUTES = 30
STRIPE_MAX_RETRY_HOURS = 24


class PaymentMonitor:
    """
    Monitors payment status for all sent invoices via Stripe API.

    Checks every 24 hours for each sent invoice.
    On payment: moves to paid/, updates revenue summaries, sends signal.
    On overdue: moves to overdue/, escalates to War Room, notifies Ops Claw.
    On repeat overdue: escalates to HOLD.

    All Stripe calls use test credentials during development.
    All external API calls logged to payment-events.log.
    """

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        stripe_client: StripeClient,
        dispatcher: FinanceSignalDispatcher,
        revenue_tracker: Any,
        approval_handler: Any,
        operational_log: FinanceOperationalLog,
        payment_events_log: PaymentEventsLog,
    ):
        self.fs = fs
        self.stripe_client = stripe_client
        self.dispatcher = dispatcher
        self.revenue_tracker = revenue_tracker
        self.approval_handler = approval_handler
        self.operational_log = operational_log
        self.payment_events_log = payment_events_log

    def check_all_sent_invoices(self) -> list[PaymentStatus]:
        """
        Check payment status for all sent invoices.

        Load all invoices from invoices/sent/.
        Check payment status for each via Stripe API.
        Process status changes.
        Log all API calls to payment-events.log.
        Return list of current statuses.
        """
        statuses: list[PaymentStatus] = []
        sent_dir = self.fs.base / "invoices" / "sent"

        if not sent_dir.exists():
            return statuses

        for invoice_path in sent_dir.glob("*.json"):
            try:
                invoice_data = json.loads(invoice_path.read_text())
                invoice = Invoice.from_dict(invoice_data)
                status = self.check_invoice_status(invoice)
                statuses.append(status)

                if status.status == "paid":
                    self.process_payment_received(invoice)
                elif status.days_overdue > 0 and invoice.status == "sent":
                    self.process_payment_overdue(invoice)

            except (json.JSONDecodeError, KeyError, Exception):
                continue

        return statuses

    def check_invoice_status(self, invoice: Invoice) -> PaymentStatus:
        """
        Check invoice status via Stripe API.

        GET to Stripe API for stripe_invoice_id.
        Log API call to payment-events.log.
        Return PaymentStatus.
        """
        if not invoice.stripe_invoice_id:
            return PaymentStatus(
                invoice_id=invoice.invoice_id,
                stripe_invoice_id="",
                status="unknown",
                amount_paid=0,
                amount_due=invoice.total,
                due_date=invoice.due_date,
                days_overdue=0,
            )

        try:
            stripe_data = self.stripe_client.get_invoice(invoice.stripe_invoice_id)

            stripe_status = stripe_data.get("status", "open")
            amount_paid = stripe_data.get("amount_paid", 0) / 100
            amount_due = stripe_data.get("amount_due", invoice.total * 100) / 100

            due_date_str = invoice.due_date
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                due_date = datetime.now(timezone.utc).date()

            today = datetime.now(timezone.utc).date()
            days_overdue = max(0, (today - due_date).days) if stripe_status == "open" else 0

            payment_event = PaymentEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="status_check",
                invoice_id=invoice.invoice_id,
                client_id=invoice.client_id,
                amount=invoice.total,
                details={"stripe_status": stripe_status, "days_overdue": days_overdue},
            )
            self.payment_events_log.append(payment_event)

            return PaymentStatus(
                invoice_id=invoice.invoice_id,
                stripe_invoice_id=invoice.stripe_invoice_id,
                status=stripe_status,
                amount_paid=amount_paid,
                amount_due=amount_due,
                due_date=due_date_str,
                days_overdue=days_overdue,
            )

        except Exception as e:
            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="stripe_status_check_failed",
                entity_id=invoice.invoice_id,
                amount=invoice.total,
                outcome="failed",
                details={"error": str(e)},
            )
            self.operational_log.append(entry)

            return PaymentStatus(
                invoice_id=invoice.invoice_id,
                stripe_invoice_id=invoice.stripe_invoice_id or "",
                status="unknown",
                amount_paid=0,
                amount_due=invoice.total,
                due_date=invoice.due_date,
                days_overdue=0,
            )

    def process_payment_received(self, invoice: Invoice) -> None:
        """
        Process a received payment.

        1. Update invoice: status="paid", paid_at=now
        2. Move: sent/ → paid/{invoice_id}.json
        3. Log payment-events.log: payment_received
        4. Call revenue_tracker.record_payment(invoice)
        5. Log operational.log: action_type="payment_received"
        """
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc).isoformat()

        paid_path = self.fs.get_invoice_path("paid", invoice.invoice_id)
        paid_path.parent.mkdir(parents=True, exist_ok=True)
        paid_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        sent_path = self.fs.get_invoice_path("sent", invoice.invoice_id)
        if sent_path.exists():
            sent_path.unlink()

        payment_event = PaymentEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="payment_received",
            invoice_id=invoice.invoice_id,
            client_id=invoice.client_id,
            amount=invoice.total,
            details={"paid_at": invoice.paid_at},
        )
        self.payment_events_log.append(payment_event)

        self.revenue_tracker.record_payment(invoice)

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="payment_received",
            entity_id=invoice.invoice_id,
            amount=invoice.total,
            outcome="success",
            details={"client_id": invoice.client_id},
        )
        self.operational_log.append(entry)

    def process_payment_overdue(self, invoice: Invoice) -> None:
        """
        Process an overdue payment.

        1. Update invoice: status="overdue"
        2. Move: sent/ → overdue/{invoice_id}.json
        3. Log payment-events.log: payment_overdue
        4. Calculate days_overdue
        5. Calculate risk_level from overdue count for this client
        6. Send payment_overdue to Ops Claw via dispatcher
        7. Check overdue count for this client:
           - First overdue (count=1): queue REVIEW in War Room
           - Repeat overdue (count>=2): queue HOLD in War Room
        8. Log operational.log: action_type="payment_overdue"
        """
        invoice.status = "overdue"

        overdue_path = self.fs.get_invoice_path("overdue", invoice.invoice_id)
        overdue_path.parent.mkdir(parents=True, exist_ok=True)
        overdue_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        sent_path = self.fs.get_invoice_path("sent", invoice.invoice_id)
        if sent_path.exists():
            sent_path.unlink()

        today = datetime.now(timezone.utc).date()
        try:
            due_date = datetime.strptime(invoice.due_date, "%Y-%m-%d").date()
            days_overdue = (today - due_date).days
        except ValueError:
            days_overdue = 1

        overdue_count = self.payment_events_log.count_overdue_by_client(invoice.client_id)

        risk_level = "low"
        if overdue_count >= 2:
            risk_level = "high"
        elif overdue_count >= 1:
            risk_level = "medium"

        self.dispatcher.send_payment_overdue(
            client_id=invoice.client_id,
            invoice_id=invoice.invoice_id,
            days_overdue=days_overdue,
            amount=invoice.total,
            risk_level=risk_level,
        )

        payment_event = PaymentEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="payment_overdue",
            invoice_id=invoice.invoice_id,
            client_id=invoice.client_id,
            amount=invoice.total,
            details={
                "days_overdue": days_overdue,
                "overdue_count": overdue_count + 1,
                "risk_level": risk_level,
            },
        )
        self.payment_events_log.append(payment_event)

        if self.approval_handler:
            if overdue_count >= 1:
                self.approval_handler.queue_overdue_hold(
                    invoice=invoice,
                    days_overdue=days_overdue,
                    overdue_count=overdue_count + 1,
                )
            else:
                self.approval_handler.queue_overdue_review(
                    invoice=invoice,
                    days_overdue=days_overdue,
                )

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="payment_overdue",
            entity_id=invoice.invoice_id,
            amount=invoice.total,
            outcome="escalated",
            details={
                "client_id": invoice.client_id,
                "days_overdue": days_overdue,
                "overdue_count": overdue_count + 1,
            },
        )
        self.operational_log.append(entry)

    def check_and_flag_overdue(self) -> list[Invoice]:
        """
        Check all sent invoices for overdue status.

        Called daily — check all sent invoices for overdue.
        Invoice is overdue when: due_date < today AND status == "sent".
        Process each overdue invoice.
        """
        overdue_invoices: list[Invoice] = []
        sent_dir = self.fs.base / "invoices" / "sent"

        if not sent_dir.exists():
            return overdue_invoices

        today = datetime.now(timezone.utc).date()

        for invoice_path in sent_dir.glob("*.json"):
            try:
                invoice_data = json.loads(invoice_path.read_text())
                invoice = Invoice.from_dict(invoice_data)

                if self._is_overdue(invoice, today):
                    self.process_payment_overdue(invoice)
                    overdue_invoices.append(invoice)

            except (json.JSONDecodeError, KeyError, Exception):
                continue

        return overdue_invoices

    def retry_failed_stripe_send(self, invoice: Invoice) -> bool:
        """
        Retry a failed Stripe send.

        Called when initial Stripe send failed (invoice stuck in approved/).
        Retry every 30 minutes for up to 24 hours.
        After 24 hours: escalate to War Room REVIEW.
        Returns True if send succeeded, False if still failing.
        """
        if not invoice.approved_at:
            return False

        approved_time = datetime.fromisoformat(invoice.approved_at.replace("Z", "+00:00"))
        elapsed_hours = (datetime.now(timezone.utc) - approved_time).total_seconds() / 3600

        if elapsed_hours > STRIPE_MAX_RETRY_HOURS:
            entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="stripe_retry_exhausted",
                entity_id=invoice.invoice_id,
                amount=invoice.total,
                outcome="escalated",
                details={"elapsed_hours": elapsed_hours},
            )
            self.operational_log.append(entry)

            if self.approval_handler:
                self.approval_handler.queue_overdue_review(invoice, int(elapsed_hours))
            return False

        payment_event = PaymentEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="retry_attempted",
            invoice_id=invoice.invoice_id,
            client_id=invoice.client_id,
            amount=invoice.total,
            details={"attempt_hours": elapsed_hours},
        )
        self.payment_events_log.append(payment_event)

        try:
            from finance.invoice_manager import InvoiceManager

            sent_invoice = self._attempt_stripe_send(invoice)
            return True
        except Exception as e:
            retry_entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="stripe_retry_failed",
                entity_id=invoice.invoice_id,
                amount=invoice.total,
                outcome="failed",
                details={"error": str(e), "attempt_hours": elapsed_hours},
            )
            self.operational_log.append(retry_entry)
            return False

    def _attempt_stripe_send(self, invoice: Invoice) -> Invoice:
        """Attempt to send invoice via Stripe."""
        stripe_result = self.stripe_client.create_invoice(
            customer_id=invoice.client_id,
            amount=invoice.total,
            currency=invoice.currency,
            description=f"Invoice {invoice.invoice_id} - {invoice.project_id}",
            due_date=invoice.due_date,
        )
        stripe_invoice_id = stripe_result.get("id", "")

        self.stripe_client.send_invoice(stripe_invoice_id)

        invoice.status = "sent"
        invoice.sent_at = datetime.now(timezone.utc).isoformat()
        invoice.stripe_invoice_id = stripe_invoice_id

        sent_path = self.fs.get_invoice_path("sent", invoice.invoice_id)
        sent_path.parent.mkdir(parents=True, exist_ok=True)
        sent_path.write_text(json.dumps(invoice.to_dict(), indent=2))

        approved_path = self.fs.get_invoice_path("approved", invoice.invoice_id)
        if approved_path.exists():
            approved_path.unlink()

        return invoice

    def _is_overdue(self, invoice: Invoice, today: date) -> bool:
        """Check if invoice is overdue."""
        if invoice.status != "sent":
            return False

        try:
            due_date = datetime.strptime(invoice.due_date, "%Y-%m-%d").date()
            return today > due_date
        except ValueError:
            return False
