# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Main Entry Point.

Main entry point for the Finance Claw.
Initializes all components, wires them together, starts the scheduler.
Called by the NemoClaw blueprint orchestrator on sandbox startup.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Protocol

from ..milimo_paths import claw_base

logger = logging.getLogger("milimo.finance")

from .finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    PaymentEventsLog,
    FinanceLogEntry,
)
from .signal_dispatcher import FinanceSignalDispatcher
from .pricing_engine import PricingEngine
from .invoice_manager import InvoiceManager
from .approval_handler import FinanceApprovalHandler
from .spend_handler import SpendApprovalHandler, SpendRequest
from .payment_risk_scorer import PaymentRiskScorer
from .payment_monitor import PaymentMonitor
from .revenue_tracker import RevenueTracker
from .expense_tracker import ExpenseTracker
from .finance_scheduler import FinanceScheduler


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
        inference_client: Any,
        stripe_client: Any | None = None,
        gateway: MeshGateway | None = None,
        base_path: Path | None = None,
    ):
        self.squad_id = squad_id
        self.inference_client = inference_client
        self.stripe_client = stripe_client
        self.gateway = gateway
        self.base_path = base_path or claw_base("finance")

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

        # Validate Stripe configuration
        import os

        stripe_key = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get(
            "STRIPE_API_KEY"
        )
        if not stripe_key:
            import logging

            logging.getLogger("milimo.finance").warning(
                "STRIPE_SECRET_KEY or STRIPE_API_KEY not set — Finance Claw will use mock Stripe client"
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

        import os as _os

        spend_handler = SpendApprovalHandler(
            operational_log=operational_log,
            decisions_path=self.base_path / "logs" / "decisions.log",
            spend_log_path=self.base_path / "logs" / "agent-spend.log",
            daily_spend_cap_cents=int(
                _os.environ.get("MILIMO_DAILY_SPEND_CAP_CENTS", "10000")
            ),
            test_mode=_os.environ.get("MILIMO_SPEND_TEST_MODE", "false").lower()
            == "true",
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
            "spend_handler": spend_handler,
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

    def handle_inbound(self, raw_message: dict) -> dict:
        """
        Handle an inbound message.

        Route inbound message to correct handler.
        Log receipt to operational.log.
        Catch all exceptions — never crash on bad input.

        Returns:
            Dict with handler result including status and any relevant data.
        """
        message_type = raw_message.get("message_type", "")
        sender_role = raw_message.get("sender_role", "")
        payload = raw_message.get("payload", {})

        import uuid

        operational_log = self._components.get("operational_log")
        self._components.get("dispatcher")

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

        result = {
            "status": "processed",
            "message_type": message_type,
            "role": "finance",
        }

        try:
            if message_type == "pricing_query":
                pricing_engine = self._components.get("pricing_engine")
                if pricing_engine:
                    pricing_engine.handle_pricing_query(payload)
                result["action"] = "pricing_query_handled"

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

                    result["invoice_id"] = invoice.invoice_id
                    result["project_id"] = project_id
                    result["action"] = "invoice_generated"

                    approval_handler = self._components.get("approval_handler")
                    if approval_handler:
                        approval_handler.queue_invoice_review(invoice)

            elif message_type == "hold_release":
                # War Room released a held payment/invoice
                payment_monitor = self._components.get("payment_monitor")
                if payment_monitor:
                    payment_id = payload.get("payment_id", "")
                    payment_monitor.release_hold(payment_id, payload)
                    result["payment_id"] = payment_id
                    result["action"] = "hold_released"
                    if operational_log:
                        operational_log.append(
                            FinanceLogEntry(
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                action_type="hold_released",
                                entity_id=payment_id,
                                amount=None,
                                outcome="success",
                                details={"reason": payload.get("reason", "")},
                            )
                        )

            elif message_type == "review_approve":
                # War Room approved a financial action
                approval_handler = self._components.get("approval_handler")
                if approval_handler:
                    action_id = payload.get("action_id", "")
                    approval_handler.process_approval(action_id, payload)
                    result["action_id"] = action_id
                    result["action"] = "review_approved"
                    if operational_log:
                        operational_log.append(
                            FinanceLogEntry(
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                action_type="review_approved",
                                entity_id=action_id,
                                amount=None,
                                outcome="success",
                                details={
                                    "approver": payload.get("approver", "war_room")
                                },
                            )
                        )

            elif message_type == "review_reject":
                # War Room rejected a financial action
                approval_handler = self._components.get("approval_handler")
                if approval_handler:
                    action_id = payload.get("action_id", "")
                    approval_handler.process_rejection(action_id, payload)
                    result["action_id"] = action_id
                    result["action"] = "review_rejected"
                    if operational_log:
                        operational_log.append(
                            FinanceLogEntry(
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                action_type="review_rejected",
                                entity_id=action_id,
                                amount=None,
                                outcome="rejected",
                                details={"reason": payload.get("reason", "")},
                            )
                        )

            elif message_type == "spend_request":
                spend_handler = self._components.get("spend_handler")
                if spend_handler:
                    request = SpendRequest(
                        spend_id=payload.get("spend_id", uuid.uuid4().hex[:12]),
                        claw=sender_role,
                        merchant_name=payload.get("merchant_name", ""),
                        merchant_url=payload.get("merchant_url", ""),
                        amount_cents=int(payload.get("amount_cents", 0)),
                        currency=payload.get("currency", "usd"),
                        justification=payload.get("justification", ""),
                        payment_method_id=payload.get("payment_method_id"),
                        credential_type=payload.get("credential_type", "card"),
                    )
                    action_id = spend_handler.queue_spend_review(request)
                    result["action_id"] = action_id
                    result["spend_id"] = request.spend_id
                    result["action"] = (
                        "spend_blocked"
                        if request.status == "blocked"
                        else "spend_queued_review"
                    )

            elif message_type == "spend_review_decision":
                spend_handler = self._components.get("spend_handler")
                if spend_handler:
                    action_id = payload.get("action_id", "")
                    decision = payload.get("decision", "")
                    if decision == "approve":
                        hold_action_id = spend_handler.handle_review_approve(
                            action_id
                        )
                        result["hold_action_id"] = hold_action_id
                        result["action"] = "spend_moved_to_hold"
                    elif decision == "edit":
                        spend_handler.handle_review_edit(
                            action_id,
                            amount_cents=int(payload.get("amount_cents", 0)),
                            justification=payload.get("justification", ""),
                        )
                        result["action"] = "spend_review_edited"
                    elif decision == "block":
                        spend_handler.handle_review_block(
                            action_id, reason=payload.get("reason", "")
                        )
                        result["action"] = "spend_blocked"
                    result["action_id"] = action_id

            elif message_type == "spend_hold_decision":
                spend_handler = self._components.get("spend_handler")
                if spend_handler:
                    action_id = payload.get("action_id", "")
                    decision = payload.get("decision", "")
                    if decision == "release":
                        operator_id = payload.get("operator_id") or payload.get("approver")
                        request = spend_handler.handle_hold_release(action_id, operator_id=operator_id)
                        result["spend_status"] = request.status
                        result["action"] = (
                            "spend_completed"
                            if request.status == "released"
                            else "spend_release_failed"
                        )
                    elif decision == "cancel":
                        spend_handler.handle_hold_cancel(
                            action_id, reason=payload.get("reason", "")
                        )
                        result["action"] = "spend_hold_cancelled"
                    result["action_id"] = action_id

            elif message_type == "assistant_query":
                import json

                result["claw"] = "finance"
                query = payload.get("query", "")

                if query == "diagnostics":
                    review_count = 0
                    hold_count = 0
                    try:
                        decisions_path = self.base_path / "logs" / "decisions.log"
                        if decisions_path.exists():
                            actions = {}
                            for line in decisions_path.read_text().splitlines():
                                if line.strip():
                                    data = json.loads(line)
                                    aid = data.get("action_id")
                                    atype = data.get("action_type")
                                    stage = data.get("stage")
                                    if atype == "queued":
                                        actions[aid] = stage
                                    elif atype in (
                                        "approve",
                                        "edit",
                                        "block",
                                        "release",
                                        "cancel",
                                    ):
                                        if aid in actions:
                                            del actions[aid]
                            for stage in actions.values():
                                if stage == "review":
                                    review_count += 1
                                elif stage == "hold":
                                    hold_count += 1
                    except Exception:
                        pass

                    recent_logs = []
                    op_log = self._components.get("operational_log")
                    if op_log and hasattr(op_log, "log_path"):
                        log_path = op_log.log_path
                        if log_path.exists():
                            try:
                                lines = log_path.read_text().splitlines()
                                recent_logs = lines[-5:]
                            except Exception:
                                pass

                    result["status"] = "diagnostics"
                    result["queue_size"] = review_count + hold_count
                    result["review_queue_size"] = review_count
                    result["hold_queue_size"] = hold_count
                    result["recent_logs"] = recent_logs
                else:
                    result["components"] = {
                        "pricing_engine": self._components.get("pricing_engine")
                        is not None,
                        "invoice_manager": self._components.get("invoice_manager")
                        is not None,
                        "payment_monitor": self._components.get("payment_monitor")
                        is not None,
                        "revenue_tracker": self._components.get("revenue_tracker")
                        is not None,
                    }
                self._send_assistant_response(raw_message, result)
                return result

            elif message_type == "assistant_task":
                result["claw"] = "finance"
                result["task_type"] = payload.get("task_type", "unknown")
                result["status"] = "accepted"
                self._send_assistant_response(raw_message, result)
                return result

            else:
                result["status"] = "unknown_type"
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
            result["status"] = "error"
            result["error"] = str(e)
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

        return result

    def get_component(self, name: str) -> Any:
        """Get a component by name."""
        return self._components.get(name)

    @property
    def is_initialized(self) -> bool:
        """Check if the Finance Claw is initialized."""
        return self._initialized

    def _send_assistant_response(
        self, message: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Send response back to assistant via mesh gateway."""
        from datetime import datetime, timezone
        import uuid

        try:
            self.gateway.send(
                message_type="assistant_response",
                recipient_role="assistant",
                sender_role="finance",
                payload={
                    "original_message_id": message.get("message_id"),
                    "response": result,
                },
                message_id=uuid.uuid4().hex[:12],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.warning("Failed to send assistant response: %s", e)
