#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Main Entry Point

Initializes all components, wires them together, starts the scheduler.
Called by the NemoClaw blueprint orchestrator on sandbox startup.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .approval_handler import BuildApprovalHandler, DeployActivityLog, PRActivityLog
from .build_init import BuildFilesystemInit, BuildOperationalLog
from .build_scheduler import BuildScheduler
from .code_generator import CodeGenerator
from .cost_monitor import CostMonitor
from .dependency_auditor import DependencyAuditor
from .deploy_manager import DeployManager
from .doc_maintainer import DocMaintainer
from .error_monitor import ErrorMonitor
from .issue_manager import IssueManager
from .pr_manager import PRManager
from .signal_dispatcher import BuildSignalDispatcher

logger = logging.getLogger("milimo.build")


class BuildClaw:
    """
    Main entry point for the Build Claw.
    Initializes all components, wires them together, starts the scheduler.
    Called by the NemoClaw blueprint orchestrator on sandbox startup.
    """

    def __init__(
        self,
        squad_id: str,
        inference_client: Any,
        github_client: Any,
        sentry_client: Any | None = None,
        vercel_client: Any | None = None,
        railway_client: Any | None = None,
        base_path: Path | None = None,
    ):
        self._squad_id = squad_id
        self._inference = inference_client
        self._github = github_client
        self._sentry = sentry_client
        self._vercel = vercel_client
        self._railway = railway_client
        self._base_path = base_path or Path("/sandbox/build")

        self._fs: BuildFilesystemInit | None = None
        self._log: BuildOperationalLog | None = None
        self._pr_log: PRActivityLog | None = None
        self._deploy_log: DeployActivityLog | None = None
        self._dispatcher: BuildSignalDispatcher | None = None
        self._approval: BuildApprovalHandler | None = None
        self._issue_manager: IssueManager | None = None
        self._code_generator: CodeGenerator | None = None
        self._pr_manager: PRManager | None = None
        self._deploy_manager: DeployManager | None = None
        self._error_monitor: ErrorMonitor | None = None
        self._cost_monitor: CostMonitor | None = None
        self._dependency_auditor: DependencyAuditor | None = None
        self._doc_maintainer: DocMaintainer | None = None
        self._scheduler: BuildScheduler | None = None

        self._inbound_handlers: dict[str, Callable[[dict], None]] = {}
        self._approval_handlers: dict[str, Callable] = {}

    def startup(self) -> None:
        logger.info("Build Claw starting for squad: %s", self._squad_id)

        self._fs = BuildFilesystemInit(base_path=self._base_path)
        init_result = self._fs.initialize()
        if not init_result.success:
            logger.error("Filesystem init failed: %s", init_result.failed)
            raise RuntimeError("Failed to initialize Build Claw filesystem")

        self._log = BuildOperationalLog(self._fs.get_operational_log_path())
        self._pr_log = PRActivityLog(self._fs.get_pr_activity_log_path())
        self._deploy_log = DeployActivityLog(self._fs.get_deploy_activity_log_path())

        self._dispatcher = BuildSignalDispatcher(
            fs=self._fs,
            operational_log=self._log,
            squad_id=self._squad_id,
        )

        self._approval = BuildApprovalHandler(
            fs=self._fs,
            operational_log=self._log,
            pr_log=self._pr_log,
            deploy_log=self._deploy_log,
        )

        self._issue_manager = IssueManager(
            fs=self._fs,
            inference_client=self._inference,
            github_client=self._github,
            dispatcher=self._dispatcher,
            approval_handler=self._approval,
            operational_log=self._log,
        )

        self._code_generator = CodeGenerator(
            fs=self._fs,
            inference_client=self._inference,
            github_client=self._github,
            approval_handler=self._approval,
            operational_log=self._log,
        )

        self._pr_manager = PRManager(
            fs=self._fs,
            inference_client=self._inference,
            github_client=self._github,
            approval_handler=self._approval,
            operational_log=self._log,
            pr_log=self._pr_log,
        )

        self._deploy_manager = DeployManager(
            fs=self._fs,
            dispatcher=self._dispatcher,
            approval_handler=self._approval,
            operational_log=self._log,
            deploy_log=self._deploy_log,
            vercel_client=self._vercel,
            railway_client=self._railway,
        )

        self._error_monitor = ErrorMonitor(
            fs=self._fs,
            sentry_client=self._sentry,
            code_generator=self._code_generator,
            approval_handler=self._approval,
            operational_log=self._log,
        )

        self._cost_monitor = CostMonitor(
            fs=self._fs,
            dispatcher=self._dispatcher,
            approval_handler=self._approval,
            operational_log=self._log,
            inference_client=self._inference,
        )

        self._dependency_auditor = DependencyAuditor(
            fs=self._fs,
            approval_handler=self._approval,
            operational_log=self._log,
            github_client=self._github,
        )

        self._doc_maintainer = DocMaintainer(
            fs=self._fs,
            inference_client=self._inference,
            dispatcher=self._dispatcher,
            approval_handler=self._approval,
            operational_log=self._log,
        )

        self._scheduler = BuildScheduler(
            error_monitor=self._error_monitor,
            cost_monitor=self._cost_monitor,
            dependency_auditor=self._dependency_auditor,
            doc_maintainer=self._doc_maintainer,
            operational_log=self._log,
        )

        self._wire_message_handlers()
        self._wire_approval_handlers()

        self._scheduler.start()

        self._log.append(self._create_log_entry(
            "claw_started",
            self._squad_id,
            "success",
            {},
        ))

        logger.info("Build Claw started successfully")

    def shutdown(self) -> None:
        logger.info("Build Claw shutting down")

        if self._scheduler:
            self._scheduler.stop()

        if self._log:
            self._log.append(self._create_log_entry(
                "claw_stopped",
                self._squad_id,
                "success",
                {},
            ))

        logger.info("Build Claw stopped")

    def handle_inbound(self, raw_message: dict) -> None:
        message_type = raw_message.get("message_type", "")
        handler = self._inbound_handlers.get(message_type)

        if not handler:
            logger.warning("No handler for message type: %s", message_type)
            return

        try:
            handler(raw_message)
        except Exception as e:
            logger.error("Inbound message handler failed: %s", e)

    def handle_approval_decision(
        self,
        action_id: str,
        decision: str,
        reason: str | None = None,
    ) -> bool:
        if not self._approval:
            logger.error("Approval handler not initialized")
            return False

        action = self._approval.get_pending_action(action_id)
        if not action:
            logger.warning("Action not found: %s", action_id)
            return False

        handler = self._approval_handlers.get(action.action_type)
        if not handler:
            logger.warning("No handler for action type: %s", action.action_type)
            return False

        try:
            if decision == "approve":
                if action.mode == "REVIEW":
                    self._approval.handle_approve(action_id, next_step_fn=handler.get("approve"))
                elif action.mode == "HOLD":
                    self._approval.handle_hold_release(action_id, execute_fn=handler.get("release"))
            elif decision == "block":
                self._approval.handle_block(action_id, reason)
            elif decision == "cancel":
                self._approval.handle_hold_cancel(action_id)
            else:
                logger.warning("Unknown decision: %s", decision)
                return False

            return True
        except Exception as e:
            logger.error("Approval decision failed: %s", e)
            return False

    def _wire_message_handlers(self) -> None:
        if not self._dispatcher or not self._issue_manager:
            return

        self._dispatcher.register_feature_brief_handler(self._issue_manager.handle_feature_brief)
        self._dispatcher.register_retention_signal_handler(self._dispatcher.handle_retention_signals)

        self._inbound_handlers["feature_brief"] = lambda m: (
            self._issue_manager.handle_feature_brief(
                client_id=m.get("payload", {}).get("client_id", ""),
                project_id=m.get("payload", {}).get("project_id", ""),
                feature_description=m.get("payload", {}).get("feature_name", ""),
                deadline=m.get("payload", {}).get("deadline"),
                acceptance_criteria=m.get("payload", {}).get("description"),
            ) if self._issue_manager else None
        )

        self._inbound_handlers["retention_signals"] = lambda m: (
            self._dispatcher.handle_retention_signals(m)
        )

        self._inbound_handlers["behavior_query_response"] = lambda m: (
            self._issue_manager.receive_analytics_response(m)
        )

    def _wire_approval_handlers(self) -> None:
        self._approval_handlers["sprint_plan"] = {
            "approve": lambda: (
                self._issue_manager.handle_sprint_plan_approved(
                    self._approval.get_pending_action("sprint_plan").entity_id
                ) if self._approval and self._issue_manager else None
            ),
        }

        self._approval_handlers["pr_review"] = {
            "approve": lambda: (
                self._pr_manager.handle_review_approved(
                    self._approval.get_pending_action("pr_review").entity_id
                ) if self._approval and self._pr_manager else None
            ),
        }

        self._approval_handlers["pr_merge_hold"] = {
            "release": lambda: (
                self._pr_manager.handle_merge_hold_released(
                    self._approval.get_pending_action("pr_merge_hold").entity_id
                ) if self._approval and self._pr_manager else None
            ),
        }

        self._approval_handlers["deploy_hold"] = {
            "release": lambda: (
                self._deploy_manager.handle_deploy_hold_released(
                    self._approval.get_pending_action("deploy_hold").entity_id
                ) if self._approval and self._deploy_manager else None
            ),
        }

    @property
    def issue_manager(self) -> IssueManager | None:
        return self._issue_manager

    @property
    def pr_manager(self) -> PRManager | None:
        return self._pr_manager

    @property
    def deploy_manager(self) -> DeployManager | None:
        return self._deploy_manager

    @property
    def approval_handler(self) -> BuildApprovalHandler | None:
        return self._approval

    @property
    def dispatcher(self) -> BuildSignalDispatcher | None:
        return self._dispatcher

    @property
    def scheduler(self) -> BuildScheduler | None:
        return self._scheduler

    def _create_log_entry(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        details: dict[str, Any],
    ):
        from .build_init import BuildLogEntry

        return BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )
