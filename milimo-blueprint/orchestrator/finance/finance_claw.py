# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Main Entry Point.

Main entry point for the Finance Claw.
Initializes all components, wires them together, starts the scheduler.
Called by the NemoClaw blueprint orchestrator on sandbox startup.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    PaymentEventsLog,
    FinanceLogEntry,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.pricing_engine import PricingEngine
from finance.invoice_manager import InvoiceManager
from finance.approval_handler import FinanceApprovalHandler
from finance.payment_risk_scorer import PaymentRiskScorer
from finance.payment_monitor import PaymentMonitor
from finance.revenue_tracker import RevenueTracker
from finance.expense_tracker import ExpenseTracker
from finance.finance_scheduler import FinanceScheduler


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


class MeshGateway(Protocol):
    """Protocol for mesh gateway."""

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


class FinanceClaw:
    """
    Main entry point for the Finance Claw.

    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(
        self,
        squad_id: str,
        inference_client: InferenceClient,
        stripe_client: StripeClient,
        gateway: MeshGateway,
        base_path: Path | None = None,
    ):
        self.squad_id = squad_id
        self.inference_client = inference_client
        self.stripe_client = stripe_client
        self.gateway = gateway
        self.base_path = base_path or Path("/sandbox/finance")

        self._initialized = False
        self._components: dict[str, Any] = {}

    def startup(self) -> None:
        """
        Initialize and start the Finance Claw.

        1. Run filesystem init — validate structure
        2. Log startup to operational.log
        3. Initialize all components with shared dependencies
        4. Register inbound message handlers with mesh router
        5. Register approval flow handlers with War Room
        6. Start finance_scheduler
        7. Log: action_type="claw_started"
        """
        fs = FinanceFilesystemInit(self.base_path)
        init_result = fs.initialize()

        if not init_result.success:
            raise RuntimeError(
                f"Failed to initialize Finance filesystem: {init_result.failed}"
            )

        operational_log = FinanceOperationalLog(
            self.base_path / "logs" / "operational.log"
        )
        payment_events_log = PaymentEventsLog(
            self.base_path / "logs" / "payment-events.log"
        )

        dispatcher = FinanceSignalDispatcher(
            gateway=self.gateway,
            operational_log=operational_log,
        )

        payment_risk_scorer = PaymentRiskScorer(
            payment_events_log=payment_events_log,
            inference_client=self.inference_client,
        )

        invoice_manager = InvoiceManager(
            fs=fs,
            inference_client=self.inference_client,
            dispatcher=dispatcher,
            payment_risk_scorer=payment_risk_scorer,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        pricing_engine = PricingEngine(
            fs=fs,
            inference_client=self.inference_client,
            dispatcher=dispatcher,
            operational_log=operational_log,
        )

        approval_handler = FinanceApprovalHandler(
            invoice_manager=invoice_manager,
            operational_log=operational_log,
            decisions_path=self.base_path / "logs" / "decisions.log",
        )

        revenue_tracker = RevenueTracker(
            fs=fs,
            inference_client=self.inference_client,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
            operational_log=operational_log,
        )

        expense_tracker = ExpenseTracker(
            fs_path=self.base_path,
            inference_client=self.inference_client,
            operational_log=operational_log,
        )

        payment_monitor = PaymentMonitor(
            fs=fs,
            stripe_client=self.stripe_client,
            dispatcher=dispatcher,
            revenue_tracker=revenue_tracker,
            approval_handler=approval_handler,
            operational_log=operational_log,
            payment_events_log=payment_events_log,
        )

        scheduler = FinanceScheduler(
            payment_monitor=payment_monitor,
            revenue_tracker=revenue_tracker,
            expense_tracker=expense_tracker,
            approval_handler=approval_handler,
            operational_log=operational_log,
            fs_path=self.base_path,
        )

        self._components = {
            "fs": fs,
            "operational_log": operational_log,
            "payment_events_log": payment_events_log,
            "dispatcher": dispatcher,
            "payment_risk_scorer": payment_risk_scorer,
            "invoice_manager": invoice_manager,
            "pricing_engine": pricing_engine,
            "revenue_tracker": revenue_tracker,
            "expense_tracker": expense_tracker,
            "approval_handler": approval_handler,
            "payment_monitor": payment_monitor,
            "scheduler": scheduler,
        }

        startup_entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="claw_started",
            entity_id=self.squad_id,
            amount=None,
            outcome="success",
            details={
                "dirs_created": len(init_result.created_dirs),
                "files_created": len(init_result.created_files),
            },
        )
        operational_log.append(startup_entry)

        scheduler.start()
        self._initialized = True

    def shutdown(self) -> None:
        """
        Shut down the Finance Claw.

        Stop scheduler cleanly.
        Log: action_type="claw_stopped"
        """
        if not self._initialized:
            return

        scheduler = self._components.get("scheduler")
        if scheduler:
            scheduler.stop()

        operational_log = self._components.get("operational_log")
        if operational_log:
            shutdown_entry = FinanceLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="claw_stopped",
                entity_id=self.squad_id,
                amount=None,
                outcome="success",
                details={},
            )
            operational_log.append(shutdown_entry)

        self._initialized = False

    def handle_inbound(self, raw_message: dict) -> None:
        """
        Handle an inbound message.

        Route inbound message to correct handler.
        Log receipt to operational.log.
        Catch all exceptions — never crash on bad input.
        """
        message_type = raw_message.get("message_type", "")
        sender_role = raw_message.get("sender_role", "")
        payload = raw_message.get("payload", {})

        operational_log = self._components.get("operational_log")
        dispatcher = self._components.get("dispatcher")

        receipt_entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="message_received",
            entity_id=message_type,
            amount=None,
            outcome="processing",
            details={"sender": sender_role},
        )
        if operational_log:
            operational_log.append(receipt_entry)

        try:
            if message_type == "pricing_query":
                pricing_engine = self._components.get("pricing_engine")
                if pricing_engine:
                    pricing_engine.handle_pricing_query(payload)

            elif message_type == "project_complete":
                invoice_manager = self._components.get("invoice_manager")
                if invoice_manager:
                    project_id = payload.get("project_id", "")
                    client_id = payload.get("client_id", "")
                    delivered_at = payload.get("delivered_at", "")

                    invoice = invoice_manager.generate_invoice(
                        project_id=project_id,
                        client_id=client_id,
                        delivered_at=delivered_at,
                    )

                    approval_handler = self._components.get("approval_handler")
                    if approval_handler:
                        approval_handler.queue_invoice_review(invoice)

            else:
                if operational_log:
                    unknown_entry = FinanceLogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        action_type="unknown_message_type",
                        entity_id=message_type,
                        amount=None,
                        outcome="ignored",
                        details={"sender": sender_role},
                    )
                    operational_log.append(unknown_entry)

        except Exception as e:
            if operational_log:
                error_entry = FinanceLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="message_handler_error",
                    entity_id=message_type,
                    amount=None,
                    outcome="failed",
                    details={"error": str(e), "sender": sender_role},
                )
                operational_log.append(error_entry)

    def get_component(self, name: str) -> Any:
        """Get a component by name."""
        return self._components.get(name)

    @property
    def is_initialized(self) -> bool:
        """Check if the Finance Claw is initialized."""
        return self._initialized
