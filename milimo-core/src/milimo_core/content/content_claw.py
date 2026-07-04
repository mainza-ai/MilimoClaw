# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Content Claw — Main Entry Point

Initializes all components, wires them together, starts the scheduler.
Called by the NemoClaw blueprint orchestrator on sandbox startup.

Inbound messages handled:
  - project_brief        (from Ops)
  - performance_intel     (from Analytics)
  - client_health_signal  (from Analytics)
  - revision_request      (from Ops)
  - content_performance_response (from Analytics)

Outbound messages dispatched:
  - draft_ready           → War Room
  - content_performance_query → Analytics
  - performance_signal    → Analytics
  - brief_acknowledged    → Ops
  - deliverable_complete  → Ops
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from ..milimo_paths import claw_base
from ..privacy_router import PrivacyRouter
from ..tool_registry import ToolRegistry
from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from .content_generator import ContentGenerator
from .brief_manager import BriefManager
from .approval_handler import ContentApprovalHandler
from .platform_publisher import PlatformPublisher
from .performance_monitor import PerformanceMonitor
from .publish_scheduler import PublishScheduler
from .brand_voice import BrandVoiceManager
from .content_scheduler import ContentScheduler

logger = logging.getLogger("milimo.content")


class ContentClaw:
    """
    Main entry point for the Content Claw.

    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(
        self,
        squad_id: str,
        inference_client: Any,
        mesh_sender: Callable[[dict[str, Any]], None] | None = None,
        base_path: Path | None = None,
        privacy_router: PrivacyRouter | None = None,
        tool_registry: ToolRegistry | None = None,
        war_room: Any | None = None,
    ) -> None:
        self._squad_id = squad_id
        self._inference_client = inference_client
        self._mesh_sender = mesh_sender
        self._base_path = base_path or claw_base("content")
        self._privacy_router = privacy_router
        self._tool_registry = tool_registry
        self._war_room = war_room

        # Component references — initialized in startup()
        self._fs: ContentFilesystemInit | None = None
        self._operational_log: ContentOperationalLog | None = None
        self._generator: ContentGenerator | None = None
        self._brief_manager: BriefManager | None = None
        self._approval_handler: ContentApprovalHandler | None = None
        self._publisher: PlatformPublisher | None = None
        self._performance_monitor: PerformanceMonitor | None = None
        self._publish_scheduler: PublishScheduler | None = None
        self._voice_manager: BrandVoiceManager | None = None
        self._scheduler: ContentScheduler | None = None

        # Handler registries
        self._inbound_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def startup(self) -> None:
        """Initialize all components and start the scheduler."""
        if self._started:
            logger.warning("ContentClaw already started")
            return

        logger.info("Starting Content Claw for squad: %s", self._squad_id)

        # 1. Filesystem
        self._fs = ContentFilesystemInit(self._base_path)
        init_result = self._fs.initialize()
        if not init_result.success:
            logger.error("Filesystem initialization failed: %s", init_result.failed)
            raise RuntimeError("Failed to initialize Content Claw filesystem")

        validation = self._fs.validate()
        if not validation.valid:
            logger.warning(
                "Filesystem validation issues: %s",
                validation.missing_paths,
            )

        # 2. Operational log
        log_path = self._base_path / "logs" / "operational.log"
        self._operational_log = ContentOperationalLog(log_path)

        self._operational_log.append(
            LogEntry(
                action_type="claw_startup",
                entity_id=self._squad_id,
                outcome="started",
                details={},
            )
        )

        # 3. Brand voice
        self._voice_manager = BrandVoiceManager(
            fs=self._fs,
            operational_log=self._operational_log,
            privacy_router=self._privacy_router,
        )

        # 4. Content generator
        # Create default dependencies if not injected (graceful degradation)
        if self._privacy_router is None:
            self._privacy_router = PrivacyRouter.from_dict({})
            logger.info("ContentClaw: using default PrivacyRouter")
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry(
                squad_id=self._squad_id, claw_role="content"
            )
            logger.info("ContentClaw: using default ToolRegistry")

        self._generator = ContentGenerator(
            privacy_router=self._privacy_router,
            tool_registry=self._tool_registry,
            operational_log=self._operational_log,
            fs=self._fs,
            war_room=self._war_room,
        )

        # 5. Brief manager
        self._brief_manager = BriefManager(
            fs=self._fs,
            operational_log=self._operational_log,
            mesh_client=self._mesh_sender,
        )

        # 6. Approval handler
        self._approval_handler = ContentApprovalHandler(
            fs=self._fs,
            operational_log=self._operational_log,
            war_room=self._war_room,
        )

        # 7. Platform publisher
        self._publisher = PlatformPublisher(
            fs=self._fs,
            operational_log=self._operational_log,
            war_room=self._war_room,
        )

        # 8. Performance monitor
        self._performance_monitor = PerformanceMonitor(
            fs=self._fs,
            operational_log=self._operational_log,
            mesh_client=self._mesh_sender,
            war_room=self._war_room,
        )

        # 9. Publish scheduler
        self._publish_scheduler = PublishScheduler(
            fs=self._fs,
            publisher=self._publisher,
            operational_log=self._operational_log,
        )

        # 10. Content scheduler (morning planning, weekly query)
        self._scheduler = ContentScheduler(
            fs=self._fs,
            operational_log=self._operational_log,
            generator=self._generator,
            brief_manager=self._brief_manager,
            performance_monitor=self._performance_monitor,
            mesh_client=self._mesh_sender,
        )

        # Register message handlers
        self._register_inbound_handlers()

        # Start scheduler
        self._scheduler.start()

        self._started = True

        self._operational_log.append(
            LogEntry(
                action_type="claw_started",
                entity_id=self._squad_id,
                outcome="success",
                details={"base_path": str(self._base_path)},
            )
        )

        logger.info("Content Claw started successfully")

    def shutdown(self) -> None:
        """Stop scheduler and log shutdown."""
        if not self._started:
            return

        logger.info("Shutting down Content Claw")

        if self._scheduler:
            self._scheduler.stop()

        if self._operational_log:
            self._operational_log.append(
                LogEntry(
                    action_type="claw_stopped",
                    entity_id=self._squad_id,
                    outcome="success",
                    details={},
                )
            )

        self._started = False
        logger.info("Content Claw shutdown complete")

    # ------------------------------------------------------------------
    # Inbound message routing
    # ------------------------------------------------------------------

    def handle_inbound(self, raw_message: dict[str, Any]) -> dict[str, Any]:
        """Route inbound message to correct handler.

        Returns:
            Dict with handler result including status and any relevant data.
        """
        if not self._started:
            logger.warning("ContentClaw not started, cannot handle message")
            return {"status": "error", "error": "claw_not_started", "role": "content"}

        message_type = raw_message.get("message_type", "")
        sender = raw_message.get("sender_role", "unknown")

        logger.debug("Received %s from %s", message_type, sender)

        result = {
            "status": "processed",
            "message_type": message_type,
            "role": "content",
        }

        handler = self._inbound_handlers.get(message_type)
        if not handler:
            logger.warning("No handler for message type: %s", message_type)
            return {
                "status": "no_handler",
                "message_type": message_type,
                "role": "content",
            }

        try:
            handler_result = handler(raw_message)
            if handler_result:
                result.update(handler_result)

            if self._operational_log:
                self._operational_log.append(
                    LogEntry(
                        action_type="message_handled",
                        entity_id=raw_message.get("message_id", ""),
                        outcome="success",
                        details={
                            "message_type": message_type,
                            "sender": sender,
                        },
                    )
                )

        except Exception as e:
            logger.error("Error handling message %s: %s", message_type, e)
            result["status"] = "error"
            result["error"] = str(e)

            if self._operational_log:
                self._operational_log.append(
                    LogEntry(
                        action_type="message_handler_error",
                        entity_id=raw_message.get("message_id", ""),
                        outcome="failed",
                        details={
                            "error": str(e),
                            "message_type": message_type,
                        },
                    )
                )

        return result

    def _register_inbound_handlers(self) -> None:
        """Register all inbound message type handlers."""
        self._inbound_handlers["project_brief"] = self._handle_project_brief
        self._inbound_handlers["performance_intel"] = self._handle_performance_intel
        self._inbound_handlers["client_health_signal"] = (
            self._handle_client_health_signal
        )
        self._inbound_handlers["revision_request"] = self._handle_revision_request
        self._inbound_handlers["content_performance_response"] = (
            self._handle_content_performance_response
        )
        self._inbound_handlers["assistant_query"] = self._handle_assistant_query
        self._inbound_handlers["assistant_task"] = self._handle_assistant_task

        # ------------------------------------------------------------------
        # Inbound handlers
        # ------------------------------------------------------------------

    def _handle_project_brief(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._brief_manager:
            brief = self._brief_manager.receive_brief(message)
            self._brief_manager.acknowledge_brief(brief.brief_id)

            logger.info(
                "Brief received and acknowledged: %s (project=%s, client=%s)",
                brief.brief_id,
                brief.project_id,
                brief.client_id,
            )
            return {
                "status": "processed",
                "role": "content",
                "message_type": "project_brief",
                "brief_id": brief.brief_id,
                "project_id": brief.project_id,
            }
        return {
            "status": "skipped",
            "role": "content",
            "message_type": "project_brief",
            "reason": "no_brief_manager",
        }

    def _handle_performance_intel(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._scheduler:
            self._scheduler.handle_analytics_intel(message)
            return {
                "status": "processed",
                "role": "content",
                "message_type": "performance_intel",
            }
        return {
            "status": "skipped",
            "role": "content",
            "message_type": "performance_intel",
            "reason": "no_scheduler",
        }

    def _handle_client_health_signal(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._scheduler:
            self._scheduler.handle_client_health_signal(message)
            return {
                "status": "processed",
                "role": "content",
                "message_type": "client_health_signal",
            }
        return {
            "status": "skipped",
            "role": "content",
            "message_type": "client_health_signal",
            "reason": "no_scheduler",
        }

    def _handle_revision_request(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._brief_manager:
            self._brief_manager.handle_revision_request(message)
            return {
                "status": "processed",
                "role": "content",
                "message_type": "revision_request",
            }
        return {
            "status": "skipped",
            "role": "content",
            "message_type": "revision_request",
            "reason": "no_brief_manager",
        }

    def _handle_content_performance_response(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        if self._scheduler:
            self._scheduler.handle_analytics_intel(message)
            return {
                "status": "processed",
                "role": "content",
                "message_type": "content_performance_response",
            }
        return {
            "status": "skipped",
            "role": "content",
            "message_type": "content_performance_response",
            "reason": "no_scheduler",
        }

    # ------------------------------------------------------------------
    # Approval decisions (called by War Room)
    # ------------------------------------------------------------------

    def handle_approval_decision(
        self,
        action_id: str,
        decision: str,
        edited_content: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """
        Handle operator approval decision from War Room.

        Args:
            action_id: War Room action ID
            decision: "approved", "edited", or "blocked"
            edited_content: New content if decision is "edited"
            reason: Rejection reason if decision is "blocked"

        Returns:
            True if the decision was processed successfully
        """
        if not self._approval_handler:
            logger.warning("Approval handler not initialized")
            return False

        try:
            if decision == "approved":
                result = self._approval_handler.handle_approve(
                    draft_id=action_id,
                    action_id=action_id,
                )
                return result is not None

            elif decision == "edited" and edited_content is not None:
                result = self._approval_handler.handle_edit(
                    draft_id=action_id,
                    edited_content=edited_content,
                    action_id=action_id,
                )
                return result is not None

            elif decision == "blocked":
                result = self._approval_handler.handle_block(
                    draft_id=action_id,
                    reason=reason,
                    action_id=action_id,
                )
                return result is not None

            else:
                logger.warning("Unknown approval decision: %s", decision)
                return False

        except Exception as e:
            logger.error("Approval decision failed for %s: %s", action_id, e)
            return False

    # ------------------------------------------------------------------
    # Outbound dispatch helpers
    # ------------------------------------------------------------------

    def _send_message(self, message: dict[str, Any]) -> None:
        """Send an outbound message via mesh gateway."""
        if self._mesh_sender:
            self._mesh_sender(message)
        else:
            logger.warning(
                "No mesh sender configured, message dropped: %s",
                message.get("message_type"),
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Whether the claw is currently running."""
        return self._started

    @property
    def generator(self) -> ContentGenerator | None:
        """Content generator instance."""
        return self._generator

    @property
    def brief_manager(self) -> BriefManager | None:
        """Brief manager instance."""
        return self._brief_manager

    @property
    def approval_handler(self) -> ContentApprovalHandler | None:
        """Approval handler instance."""
        return self._approval_handler

    def _handle_assistant_query(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle assistant_query from Lucy.
        Returns current status and state of the Content Claw.
        """
        sender = message.get("sender_role", "unknown")
        logger.info("Assistant query from %s", sender)

        result = {
            "claw": "content",
            "status": "online" if self._started else "offline",
            "components": {
                "filesystem": self._fs is not None,
                "generator": self._generator is not None,
                "voice_manager": self._voice_manager is not None,
                "scheduler": self._scheduler is not None,
                "publisher": self._publisher is not None,
            },
            "pending_work": {
                "drafts": len(list((self._base_path / "drafts").glob("*.json")))
                if self._base_path
                else 0,
            },
        }
        self._log_and_respond(message, result)
        return result

    def _handle_assistant_task(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        Handle assistant_task from Lucy.
        Executes content-related tasks requested by the assistant.
        """
        payload = message.get("payload", {})
        task_type = payload.get("task_type", "unknown")
        logger.info("Assistant task '%s' received", task_type)

        result = {
            "claw": "content",
            "task_type": task_type,
            "status": "accepted",
            "message": f"Task '{task_type}' queued for processing",
        }

        if task_type == "generate_draft":
            brief_data = payload.get("brief", {})
            if self._generator and self._brief_manager:
                try:
                    # Attempt to create a brief from the task payload
                    if hasattr(self._brief_manager, "create_brief_from_task"):
                        brief = getattr(self._brief_manager, "create_brief_from_task")(
                            brief_data
                        )
                        result["status"] = "queued"
                        result["brief_id"] = getattr(brief, "brief_id", "pending")
                        result["message"] = "Draft generation queued from task"
                    else:
                        # Fallback: synthesize a project_brief message and route it
                        synth_message = {
                            "message_type": "project_brief",
                            "sender_role": "assistant",
                            "payload": brief_data,
                        }
                        brief = self._brief_manager.receive_brief(synth_message)
                        self._brief_manager.acknowledge_brief(brief.brief_id)
                        result["status"] = "queued"
                        result["brief_id"] = brief.brief_id
                        result["message"] = "Draft generation queued via brief pipeline"
                except Exception as e:
                    logger.error("generate_draft task failed: %s", e)
                    result["status"] = "error"
                    result["message"] = f"Draft generation failed: {e}"
            else:
                result["status"] = "error"
                result["message"] = "Content generator not initialized"

        self._log_and_respond(message, result)
        return result

    def _log_and_respond(self, message: dict[str, Any], result: dict[str, Any]) -> None:
        """Log action and send response via mesh."""
        if self._operational_log is not None:
            self._operational_log.append(
                LogEntry(
                    action_type="assistant_message",
                    entity_id=message.get("message_type", "unknown"),
                    outcome="success",
                    details=result,
                )
            )
        if self._mesh_sender:
            self._mesh_sender(
                {
                    "sender_role": "content",
                    "recipient_role": "assistant",
                    "message_type": "assistant_response",
                    "payload": {
                        "original_message_id": message.get("message_id"),
                        "response": result,
                    },
                }
            )

    @property
    def publisher(self) -> PlatformPublisher | None:
        """Platform publisher instance."""
        return self._publisher

    @property
    def performance_monitor(self) -> PerformanceMonitor | None:
        """Performance monitor instance."""
        return self._performance_monitor

    @property
    def scheduler(self) -> ContentScheduler | None:
        """Content scheduler instance."""
        return self._scheduler

    @property
    def voice_manager(self) -> BrandVoiceManager | None:
        """Brand voice manager instance."""
        return self._voice_manager

    def _publish(self, platform: str, content: str) -> dict:
        if not self._publisher:
            raise RuntimeError("ContentClaw not started — call startup() first")
        self._publisher.publish(content, platform)
        return {"status": "published", "platform": platform}

    def generate_content(self, brief: dict) -> dict:
        if not self._generator:
            raise RuntimeError("ContentClaw not started — call startup() first")
        return self._generator._build_prompt(brief)

    def schedule_content(self, item: dict) -> dict:
        if not self._scheduler:
            raise RuntimeError("ContentClaw not started — call startup() first")
        self._scheduler.trigger_morning_planning()
        return {"status": "scheduled"}

    def publish_to_twitter(self, content: str) -> dict:
        return self._publish("twitter", content)

    def publish_to_linkedin(self, content: str) -> dict:
        return self._publish("linkedin", content)

    def publish_to_tiktok(self, content: str) -> dict:
        return self._publish("tiktok", content)

    def manage_brand_voice(self, client_id: str, content: str) -> dict:
        if not self._voice_manager:
            raise RuntimeError("ContentClaw not started — call startup() first")
        profile = self._voice_manager.load_profile(client_id)
        if not profile:
            return {"status": "no_profile", "client_id": client_id}
        return self._voice_manager.apply_voice(content, profile)

    def track_performance(self, post_id: str) -> dict:
        if not self._performance_monitor:
            raise RuntimeError("ContentClaw not started — call startup() first")
        return self._performance_monitor.collect_performance(post_id).to_dict()
