# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Main Entry Point

Main entry point for the Ops Claw.
Initializes all components, wires them together, starts the scheduler.
Called by the NemoClaw blueprint orchestrator on sandbox startup.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .ops_init import (
    OpsFilesystemInit,
    OpsOperationalLog,
    OpsCommsLog,
    OpsLogEntry,
    BASE,
)
from .signal_dispatcher import OpsSignalDispatcher, MeshGateway
from .approval_handler import OpsApprovalHandler
from .intake_manager import IntakeManager
from .health_scorer import ClientHealthScorer
from .project_manager import ProjectManager
from .scope_monitor import ScopeMonitor
from .comms_manager import CommsManager
from .ops_scheduler import OpsScheduler
from .incident_analyzer import IncidentAnalyzer
from .runbook_executor import RunbookExecutor
from .webhook_server import OpsWebhookServer

logger = logging.getLogger("milimo.ops")


class MockMeshGateway:
    """Mock mesh gateway for testing."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send(self, message: dict[str, Any]) -> bool:
        self.calls.append(message)
        return True


class OpsClaw:
    """
    Main entry point for the Ops Claw.

    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(
        self,
        squad_id: str,
        inference_client: Any,
        mesh_gateway: MeshGateway,
        base_path: Path | None = None,
    ):
        self._squad_id = squad_id
        self._inference_client = inference_client
        self._base_path = base_path or BASE
        self._mesh_gateway = mesh_gateway

        self._fs: OpsFilesystemInit | None = None
        self._operational_log: OpsOperationalLog | None = None
        self._comms_log: OpsCommsLog | None = None
        self._dispatcher: OpsSignalDispatcher | None = None
        self._approval_handler: OpsApprovalHandler | None = None
        self._intake_manager: IntakeManager | None = None
        self._health_scorer: ClientHealthScorer | None = None
        self._project_manager: ProjectManager | None = None
        self._scope_monitor: ScopeMonitor | None = None
        self._comms_manager: CommsManager | None = None
        self._scheduler: OpsScheduler | None = None
        self._incident_analyzer: IncidentAnalyzer | None = None
        self._runbook_executor: RunbookExecutor | None = None
        self._webhook_server: OpsWebhookServer | None = None

        self._inbound_handlers: dict[
            str, Callable[[dict[str, Any]], dict[str, Any]]
        ] = {}
        self._approval_handlers: dict[str, Callable[[str, dict[str, Any]], None]] = {}

        self._running = False

    def startup(self) -> None:
        logger.info("Starting Ops Claw for squad: %s", self._squad_id)

        self._fs = OpsFilesystemInit(self._base_path)
        init_result = self._fs.initialize()

        if not init_result.success:
            logger.error("Filesystem initialization failed: %s", init_result.failed)
            for path, error in init_result.failed:
                logger.error("  - %s: %s", path, error)
        else:
            logger.info(
                "Filesystem initialized: %d dirs, %d files, %d already existed",
                len(init_result.created_dirs),
                len(init_result.created_files),
                len(init_result.already_existed),
            )

        validation = self._fs.validate()
        if not validation.valid:
            logger.warning(
                "Filesystem validation issues: %s",
                validation.missing_dirs + validation.missing_files,
            )

        log_path = self._base_path / "logs" / "operational.log"
        self._operational_log = OpsOperationalLog(log_path)

        comms_log_path = self._base_path / "logs" / "comms.log"
        self._comms_log = OpsCommsLog(comms_log_path)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="claw_startup",
                entity_id=self._squad_id,
                outcome="started",
                details={},
            )
        )

        self._dispatcher = OpsSignalDispatcher(
            gateway=self._mesh_gateway,
            operational_log=self._operational_log,
            squad_id=self._squad_id,
            pricing_confirmed_dir=self._base_path / "pricing_confirmed",
        )

        self._approval_handler = OpsApprovalHandler(
            fs_base=self._base_path,
            decisions_log_path=self._base_path / "logs" / "decisions.log",
        )

        self._intake_manager = IntakeManager(
            fs=self._fs,
            inference_client=self._inference_client,
            dispatcher=self._dispatcher,
            approval_handler=self._approval_handler,
            operational_log=self._operational_log,
        )

        self._project_manager = ProjectManager(
            fs=self._fs,
            dispatcher=self._dispatcher,
            approval_handler=self._approval_handler,
            operational_log=self._operational_log,
            inference_client=self._inference_client,
        )

        self._scope_monitor = ScopeMonitor(
            fs=self._fs,
            inference_client=self._inference_client,
            approval_handler=self._approval_handler,
            dispatcher=self._dispatcher,
            operational_log=self._operational_log,
        )

        self._comms_manager = CommsManager(
            fs=self._fs,
            inference_client=self._inference_client,
            approval_handler=self._approval_handler,
            operational_log=self._operational_log,
            comms_log=self._comms_log,
            dispatcher=self._dispatcher,
            scope_monitor=self._scope_monitor,
        )

        self._health_scorer = ClientHealthScorer(
            fs=self._fs,
            inference_client=self._inference_client,
            dispatcher=self._dispatcher,
            approval_handler=self._approval_handler,
            operational_log=self._operational_log,
            comms_log=self._comms_log,
        )

        self._register_inbound_handlers()
        self._register_approval_handlers()

        self._scheduler = OpsScheduler(
            project_manager=self._project_manager,
            intake_manager=self._intake_manager,
            health_scorer=self._health_scorer,
            comms_manager=self._comms_manager,
            operational_log=self._operational_log,
            fs=self._fs,
        )

        self._scheduler.start()

        # 14. Incident analyzer — AI-powered incident analysis
        self._incident_analyzer = IncidentAnalyzer(
            inference_client=self._inference_client,
            operational_log=self._operational_log,
            dispatcher=self._dispatcher,
        )

        # 15. Runbook executor — automated remediation
        self._runbook_executor = RunbookExecutor(
            operational_log=self._operational_log,
            dispatcher=self._dispatcher,
        )

        # 16. Webhook server — real-time alert ingestion
        webhook_port = int(os.environ.get("OPS_WEBHOOK_PORT", "8080"))
        self._webhook_server = OpsWebhookServer(
            port=webhook_port,
            dispatcher=self._dispatcher,
            ops_claw=self,
        )
        self._webhook_server.start()

        self._running = True

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="claw_started",
                entity_id=self._squad_id,
                outcome="success",
                details={},
            )
        )

        logger.info("Ops Claw started successfully")

    def shutdown(self) -> None:
        logger.info("Shutting down Ops Claw")

        if self._scheduler:
            self._scheduler.stop()

        if self._webhook_server:
            self._webhook_server.stop()

        if self._operational_log:
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="claw_stopped",
                    entity_id=self._squad_id,
                    outcome="success",
                    details={},
                )
            )

        self._running = False
        logger.info("Ops Claw shutdown complete")

    def handle_inbound(self, raw_message: dict[str, Any]) -> dict[str, Any]:
        """Route inbound message to the correct handler.

        Returns:
            Dict with handler result including status and any relevant data.
        """
        message_type = raw_message.get("message_type")
        if not message_type:
            logger.warning("Received message without message_type")
            return {"status": "error", "error": "No message_type", "role": "ops"}

        handler = self._inbound_handlers.get(message_type)
        if not handler:
            logger.warning("No handler for message type: %s", message_type)
            return {"status": "no_handler", "message_type": message_type, "role": "ops"}

        try:
            result = handler(raw_message)
            if result is None:
                result = {
                    "status": "processed",
                    "message_type": message_type,
                    "role": "ops",
                }
            return result
        except Exception as e:
            logger.error("Error handling message %s: %s", message_type, e)

            if self._operational_log:
                self._operational_log.append(
                    OpsLogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        action_type="message_handler_error",
                        entity_id=raw_message.get("project_id", "unknown"),
                        outcome="failed",
                        details={"error": str(e), "message_type": message_type},
                    )
                )

            return {
                "status": "error",
                "message_type": message_type,
                "role": "ops",
                "error": str(e),
            }

    def handle_incident(self, alert: dict[str, Any]) -> None:
        """Handle an incoming incident alert — full pipeline: analyze → remediate.

        This is the main entry point for webhook alerts. It chains:
        1. Log the alert (via dispatcher)
        2. AI-powered analysis (via IncidentAnalyzer)
        3. Automated remediation (via RunbookExecutor)
        """
        # Step 1: Log via dispatcher
        if self._dispatcher:
            self._dispatcher.handle_incident(alert)

        # Step 2: AI analysis
        if self._incident_analyzer:
            analysis = self._incident_analyzer.analyze_incident(alert)

            # Step 3: Automated remediation
            if self._runbook_executor:
                result = self._runbook_executor.handle_incident_with_remediation(
                    alert, analysis
                )

                if self._operational_log:
                    self._operational_log.append(
                        OpsLogEntry(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            action_type="incident_remediation_complete",
                            entity_id=alert.get("alert_id", "unknown"),
                            outcome="success" if result.success else "partial",
                            details={
                                "runbook": result.runbook_name,
                                "steps_executed": result.steps_executed,
                                "steps_failed": result.steps_failed,
                                "duration_seconds": result.duration_seconds,
                            },
                        )
                    )
        else:
            logger.warning(
                "Incident analyzer not initialized — alert logged but not analyzed"
            )

    def _register_inbound_handlers(self) -> None:
        self._inbound_handlers["deliverable_complete"] = (
            self._handle_deliverable_complete
        )
        self._inbound_handlers["deploy_complete"] = self._handle_deploy_complete
        self._inbound_handlers["pricing_response"] = self._handle_pricing_response
        self._inbound_handlers["invoice_ready"] = self._handle_invoice_ready
        self._inbound_handlers["payment_overdue"] = self._handle_payment_overdue
        self._inbound_handlers["brief_acknowledged"] = self._handle_brief_acknowledged
        self._inbound_handlers["assistant_query"] = self._handle_assistant_query
        self._inbound_handlers["assistant_task"] = self._handle_assistant_task
        self._inbound_handlers["feature_brief_acknowledged"] = (
            self._handle_feature_brief_acknowledged
        )

    def _register_approval_handlers(self) -> None:
        """Register default approval thresholds for ops actions.

        Ops Claw approval is handled through handle_approval_decision() which
        dispatches to the appropriate manager based on action type. This method
        ensures the approval handler is initialized with the correct queue paths.
        """
        if not self._approval_handler:
            logger.warning("Approval handler not initialized, skipping registration")
            return

        # Log that approval system is active
        logger.info("Ops Claw approval handlers registered")

    def _handle_deliverable_complete(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._project_manager:
            self._project_manager.handle_deliverable_complete(message)
            return {
                "status": "processed",
                "role": "ops",
                "message_type": "deliverable_complete",
            }
        return {
            "status": "skipped",
            "role": "ops",
            "message_type": "deliverable_complete",
            "reason": "no_project_manager",
        }

    def _handle_deploy_complete(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._project_manager:
            self._project_manager.handle_deploy_complete(message)
            return {
                "status": "processed",
                "role": "ops",
                "message_type": "deploy_complete",
            }
        return {
            "status": "skipped",
            "role": "ops",
            "message_type": "deploy_complete",
            "reason": "no_project_manager",
        }

    def _handle_pricing_response(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", message)
        project_id = payload.get("project_id") or payload.get("query_id", "").replace(
            "query_", "project_"
        )
        floor_val = payload.get("floor")
        if floor_val is None:
            floor_val = payload.get("floor_price", 0)
        floor_price = float(floor_val if floor_val is not None else 0)

        ceil_val = payload.get("ceiling")
        if ceil_val is None:
            ceil_val = payload.get("ceiling_price", 0)
        ceiling_price = float(ceil_val if ceil_val is not None else 0)

        scope_notes = str(payload.get("notes") or payload.get("scope_notes", ""))

        if self._intake_manager:
            self._intake_manager.handle_pricing_response(
                project_id=project_id,
                floor_price=floor_price,
                ceiling_price=ceiling_price,
                scope_notes=scope_notes,
            )

        if self._project_manager:
            self._project_manager.handle_pricing_response(
                project_id=project_id,
                floor_price=floor_price,
                ceiling_price=ceiling_price,
            )
        return {
            "status": "processed",
            "role": "ops",
            "message_type": "pricing_response",
            "project_id": project_id,
        }

    def _handle_invoice_ready(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", message)
        invoice_id = payload.get("invoice_id")
        client_id = payload.get("client_id")
        amount = payload.get("amount")

        if self._approval_handler:
            self._approval_handler.log_auto(
                action_type="invoice_received",
                entity_id=invoice_id or "unknown",
                content_preview=f"Invoice {invoice_id} for ${amount} ready for client {client_id}",
            )
        return {
            "status": "processed",
            "role": "ops",
            "message_type": "invoice_ready",
            "invoice_id": invoice_id,
        }

    def _handle_payment_overdue(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", message)
        invoice_id = payload.get("invoice_id")
        client_id = payload.get("client_id")
        days_overdue = payload.get("days_overdue", 0)
        amount = payload.get("amount", 0)

        if self._approval_handler:
            self._approval_handler.queue_review(
                action_type="payment_overdue",
                entity_id=invoice_id or client_id or "unknown",
                content=f"Payment overdue: Invoice {invoice_id} for client {client_id}\n\n"
                f"Days overdue: {days_overdue}\n"
                f"Amount: ${amount}\n\n"
                f"Recommended: Send follow-up message to client.",
                context={
                    "invoice_id": invoice_id,
                    "client_id": client_id,
                    "days_overdue": days_overdue,
                    "amount": amount,
                },
            )
        return {
            "status": "processed",
            "role": "ops",
            "message_type": "payment_overdue",
            "invoice_id": invoice_id,
        }

    def _handle_brief_acknowledged(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", message)
        project_id = payload.get("project_id")
        estimated_time = payload.get("estimated_first_draft_time")

        if self._operational_log:
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="brief_acknowledged",
                    entity_id=project_id or "unknown",
                    outcome="success",
                    details={"estimated_time": estimated_time},
                )
            )
        return {
            "status": "processed",
            "role": "ops",
            "message_type": "brief_acknowledged",
            "project_id": project_id,
        }

    def _handle_feature_brief_acknowledged(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        payload = message.get("payload", message)
        project_id = payload.get("project_id")
        estimated_time = payload.get("estimated_first_draft_time")

        if self._operational_log:
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="feature_brief_acknowledged",
                    entity_id=project_id or "unknown",
                    outcome="success",
                    details={"estimated_time": estimated_time},
                )
            )
        return {
            "status": "processed",
            "role": "ops",
            "message_type": "feature_brief_acknowledged",
            "project_id": project_id,
        }

    def handle_approval_decision(
        self, action_id: str, decision: str, edited_content: str | None = None
    ) -> bool:
        if not self._approval_handler:
            logger.warning("Approval handler not initialized")
            return False

        action = self._approval_handler.get_action(action_id)
        if not action:
            logger.warning("Action %s not found for approval decision", action_id)
            return False

        if decision == "approved":
            send_fn = self._create_send_fn(action)
            return self._approval_handler.handle_approve(action_id, send_fn)

        elif decision == "edited" and edited_content:
            send_fn = self._create_send_fn(action)
            return self._approval_handler.handle_edit(
                action_id, edited_content, send_fn
            )

        elif decision == "blocked":
            return self._approval_handler.handle_block(action_id, "operator_blocked")

        elif decision == "released":
            execute_fn = self._create_execute_fn(action)
            return self._approval_handler.handle_hold_release(action_id, execute_fn)

        else:
            logger.warning("Unknown approval decision: %s", decision)
            return False

    def _create_send_fn(self, action: Any) -> Callable[[], None]:
        def send() -> None:
            if action.action_type in (
                "welcome_message",
                "client_response",
                "delivery_message",
            ):
                if self._comms_manager:
                    self._comms_manager.send_auto_response(
                        client_id=action.context.get("client_id", "unknown"),
                        message_text=action.content,
                    )
            elif action.action_type == "proposal":
                project_id = action.context.get("project_id", "")
                if self._operational_log:
                    self._operational_log.append(
                        OpsLogEntry(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            action_type="proposal_sent",
                            entity_id=project_id,
                            outcome="success",
                            details={
                                "action_id": action.action_id,
                                "content_preview": action.content[:200],
                            },
                        )
                    )
                logger.info(
                    "Proposal sent for project %s (action: %s)",
                    project_id,
                    action.action_id,
                )

        return send

    def _create_execute_fn(self, action: Any) -> Callable[[], None]:
        def execute() -> None:
            if action.action_type == "scope_change_order":
                project_id = action.context.get("project_id", "")
                if self._project_manager:
                    self._project_manager.update_project_status(
                        project_id=project_id,
                        new_status="scope_changed",
                    )
                if self._operational_log:
                    self._operational_log.append(
                        OpsLogEntry(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            action_type="scope_change_executed",
                            entity_id=project_id,
                            outcome="success",
                            details={"action_id": action.action_id},
                        )
                    )
            elif action.action_type == "deadline_critical":
                project_id = action.context.get("project_id", "")
                if self._project_manager:
                    self._project_manager.update_project_status(
                        project_id=project_id,
                        new_status="deadline_at_risk",
                    )
                if self._operational_log:
                    self._operational_log.append(
                        OpsLogEntry(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            action_type="deadline_escalated",
                            entity_id=project_id,
                            outcome="success",
                            details={"action_id": action.action_id},
                        )
                    )

        return execute

    def _handle_assistant_query(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle assistant_query from Lucy."""
        payload = message.get("payload", {})
        query = payload.get("query", "")

        if query == "diagnostics":
            review_len = (
                len(self._approval_handler.get_review_queue())
                if self._approval_handler
                else 0
            )
            hold_len = (
                len(self._approval_handler.get_hold_queue())
                if self._approval_handler
                else 0
            )

            # Read recent log entries
            recent_logs = []
            if self._operational_log and hasattr(self._operational_log, "_log_path"):
                log_path = self._operational_log._log_path
                if log_path.exists():
                    try:
                        lines = log_path.read_text().splitlines()
                        recent_logs = lines[-5:]
                    except Exception:
                        pass

            result = {
                "claw": "ops",
                "status": "diagnostics",
                "queue_size": review_len + hold_len,
                "review_queue_size": review_len,
                "hold_queue_size": hold_len,
                "recent_logs": recent_logs,
            }
        else:
            result = {
                "claw": "ops",
                "status": "online" if self._running else "offline",
                "components": {
                    "intake_manager": self._intake_manager is not None,
                    "project_manager": self._project_manager is not None,
                    "scheduler": self._scheduler is not None,
                    "health_scorer": self._health_scorer is not None,
                },
                "clients": len(list((self._base_path / "clients").glob("*")))
                if self._base_path
                else 0,
            }
        self._send_assistant_response(message, result)
        return result

    def _handle_assistant_task(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle assistant_task from Lucy."""
        payload = message.get("payload", {})
        task_type = payload.get("task_type", "unknown")
        task_desc = payload.get("task_description", "")

        # If task description indicates onboarding or pricing scoping, trigger pricing query
        if (
            "onboard" in task_desc.lower()
            or "stripe billing" in task_desc.lower()
            or "pricing" in task_desc.lower()
        ):
            import re

            proj_match = re.search(
                r"project\s+([A-Za-z0-9_-]+)", task_desc, re.IGNORECASE
            )
            project_id = proj_match.group(1) if proj_match else "proj-1002"

            logger.info(
                "Ops Claw _handle_assistant_task: triggering pricing_query for %s",
                project_id,
            )
            self._dispatcher.send_pricing_query(
                project_id=project_id,
                scope_description=task_desc,
                complexity_estimate="medium",
                deadline=payload.get("deadline", "2026-05-30T00:00:00Z"),
                client_id="client-enterprise-999",
            )
            task_type = "onboarding"

        result = {
            "claw": "ops",
            "task_type": task_type,
            "status": "accepted",
        }
        self._send_assistant_response(message, result)
        return result

    def _send_assistant_response(
        self, message: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Send response back to assistant."""
        if self._mesh_gateway:
            self._mesh_gateway.send(
                {
                    "sender_role": "ops",
                    "recipient_role": "assistant",
                    "message_type": "assistant_response",
                    "payload": {
                        "original_message_id": message.get("message_id"),
                        "response": result,
                    },
                }
            )

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def intake_manager(self) -> IntakeManager | None:
        return self._intake_manager

    @property
    def project_manager(self) -> ProjectManager | None:
        return self._project_manager

    @property
    def health_scorer(self) -> ClientHealthScorer | None:
        return self._health_scorer

    @property
    def approval_handler(self) -> OpsApprovalHandler | None:
        return self._approval_handler

    @property
    def dispatcher(self) -> OpsSignalDispatcher | None:
        return self._dispatcher
