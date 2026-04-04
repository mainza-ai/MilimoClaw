"""
Build Claw main entry point.

Wires together all Build Claw components:
- Filesystem initialization
- Signal dispatcher (inter-claw communication)
- Issue manager (sprint planning, velocity, backlog)
- Code generator (implementation, branch management)
- PR manager (two-stage REVIEW → HOLD → merge)
- Deploy manager (separate HOLD → deploy)
- Error monitor, cost monitor, dependency auditor
- Doc maintainer (changelog, devlog, API docs)
- Build scheduler (periodic tasks)

Enhancement: Inference fallback chain, category-based model selection,
session recovery from oh-my-openagent patterns.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .build_init import (
    BASE,
    BuildFilesystemInit,
    BuildOperationalLog,
    INFERENCE_FALLBACK_CHAIN,
    BUILD_CATEGORIES,
)
from .build_scheduler import BuildScheduler
from .signal_dispatcher import BuildSignalDispatcher
from .approval_handler import (
    BuildApprovalHandler,
    PRActivityLog,
    DeployActivityLog,
)
from .issue_manager import IssueManager
from .code_generator import CodeGenerator
from .pr_manager import PRManager
from .deploy_manager import DeployManager
from .error_monitor import ErrorMonitor
from .cost_monitor import CostMonitor
from .dependency_auditor import DependencyAuditor
from .doc_maintainer import DocMaintainer

logger = logging.getLogger(__name__)


class BuildClaw:
    """Main entry point for the Build Claw."""

    def __init__(
        self,
        squad_id: str,
        inference_client: Any,
        github_client: Any,
        sentry_client: Any | None = None,
        vercel_client: Any | None = None,
        base_path: Path | None = None,
    ) -> None:
        self._squad_id = squad_id
        self._inference = inference_client
        self._github_client = github_client
        self._sentry_client = sentry_client
        self._vercel_client = vercel_client
        self._base_path = base_path

        # Components (initialized in startup)
        self._fs: BuildFilesystemInit | None = None
        self._log: BuildOperationalLog | None = None
        self._pr_log: PRActivityLog | None = None
        self._deploy_log: DeployActivityLog | None = None
        self._dispatcher: BuildSignalDispatcher | None = None
        self._approval_handler: BuildApprovalHandler | None = None
        self._issue_manager: IssueManager | None = None
        self._code_gen: CodeGenerator | None = None
        self._pr_manager: PRManager | None = None
        self._deploy_manager: DeployManager | None = None
        self._error_monitor: ErrorMonitor | None = None
        self._cost_monitor: CostMonitor | None = None
        self._dependency_auditor: DependencyAuditor | None = None
        self._doc_maintainer: DocMaintainer | None = None
        self._scheduler: BuildScheduler | None = None

        # Inbound message routing
        self._inbound_handlers: dict[str, Any] = {}

        # MVR test aliases (so tests can access via expected names)
        self._github = self._github_client
        self._inference_client = self._inference
        self._vercel = self._vercel_client
        self._code_generator = self._code_gen

    # ------------------------------------------------------------------
    # Startup / Shutdown
    # ------------------------------------------------------------------

    def startup(self) -> None:
        """Initialize all Build Claw components."""
        base_path = self._base_path or BASE

        # 1. Filesystem init
        self._fs = BuildFilesystemInit(base_path=base_path)
        self._fs.initialize()

        # 2. Operational logs
        self._log = BuildOperationalLog(base_path / "logs" / "operational.log")
        self._pr_log = PRActivityLog(base_path / "logs" / "pr-activity.log")
        self._deploy_log = DeployActivityLog(base_path / "logs" / "deploy-activity.log")

        # 3. Signal dispatcher
        self._dispatcher = BuildSignalDispatcher(
            fs=self._fs,
            operational_log=self._log,
            squad_id=self._squad_id,
        )

        # 4. Approval handler
        self._approval_handler = BuildApprovalHandler(
            fs=self._fs,
            operational_log=self._log,
            pr_log=self._pr_log,
            deploy_log=self._deploy_log,
        )

        # 5. Issue manager
        self._issue_manager = IssueManager(
            fs=self._fs,
            github_client=self._github_client,
            inference_client=self._inference,
            approval_handler=self._approval_handler,
            dispatcher=self._dispatcher,
            operational_log=self._log,
        )

        # 6. Code generator
        self._code_gen = CodeGenerator(
            fs=self._fs,
            inference_client=self._inference,
            github_client=self._github_client,
            approval_handler=self._approval_handler,
            operational_log=self._log,
            repo_path=base_path / "repo",
        )

        # 7. PR manager
        self._pr_manager = PRManager(
            fs=self._fs,
            inference_client=self._inference,
            github_client=self._github_client,
            approval_handler=self._approval_handler,
            operational_log=self._log,
            pr_log=self._pr_log,
        )

        # 8. Deploy manager
        self._deploy_manager = DeployManager(
            fs=self._fs,
            dispatcher=self._dispatcher,
            approval_handler=self._approval_handler,
            operational_log=self._log,
            deploy_log=self._deploy_log,
            vercel_client=self._vercel_client,
        )

        # 9. Error monitor
        self._error_monitor = ErrorMonitor(
            fs=self._fs,
            sentry_client=self._sentry_client,
            code_generator=self._code_gen,
            approval_handler=self._approval_handler,
            operational_log=self._log,
        )

        # 10. Cost monitor
        self._cost_monitor = CostMonitor(
            fs=self._fs,
            dispatcher=self._dispatcher,
            approval_handler=self._approval_handler,
            operational_log=self._log,
            inference_client=self._inference,
        )

        # 11. Dependency auditor
        self._dependency_auditor = DependencyAuditor(
            fs=self._fs,
            approval_handler=self._approval_handler,
            operational_log=self._log,
            github_client=self._github_client,
            repo_path=base_path / "repo",
        )

        # 12. Doc maintainer
        self._doc_maintainer = DocMaintainer(
            fs=self._fs,
            inference_client=self._inference,
            dispatcher=self._dispatcher,
            approval_handler=self._approval_handler,
            operational_log=self._log,
        )

        # 13. Scheduler
        self._scheduler = BuildScheduler(
            error_monitor=self._error_monitor,
            cost_monitor=self._cost_monitor,
            dependency_auditor=self._dependency_auditor,
            doc_maintainer=self._doc_maintainer,
            operational_log=self._log,
        )

        # Wire inbound handlers
        self._inbound_handlers = {
            "feature_brief": self._dispatcher.handle_feature_brief,
            "retention_signals": self._dispatcher.handle_retention_signals,
            "behavior_query_response": self._dispatcher.handle_behavior_query_response,
        }

        # Update MVR test aliases after component initialization
        self._github = self._github_client
        self._code_generator = self._code_gen

        # Start scheduler
        self._scheduler.start()

        logger.info("BuildClaw started successfully")

    def shutdown(self) -> None:
        """Stop all Build Claw components cleanly."""
        if self._scheduler:
            self._scheduler.stop()
        logger.info("BuildClaw shutdown complete")

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    def handle_inbound(self, message: dict[str, Any]) -> None:
        """Route inbound message to the correct handler."""
        msg_type = message.get("message_type", "unknown")
        handler = self._inbound_handlers.get(msg_type)
        if handler:
            handler(message)
        else:
            logger.warning("No handler for message type: %s", msg_type)

    def handle_approval_decision(
        self,
        action_id: str,
        decision: str,
        reason: str = "",
    ) -> Any:
        """Handle operator approval/block decision."""
        if decision == "approve":
            return self._approval_handler.handle_approve(action_id)
        elif decision == "block":
            return self._approval_handler.handle_block(action_id, reason)
        elif decision == "cancel":
            return self._approval_handler.handle_hold_cancel(action_id)
        else:
            raise ValueError(f"Unknown decision: {decision}")

    # ------------------------------------------------------------------
    # Properties (for test access)
    # ------------------------------------------------------------------

    @property
    def approval_handler(self) -> BuildApprovalHandler:
        # Support both _approval_handler (startup) and _approval (MVR fixture)
        handler = getattr(self, "_approval_handler", None) or getattr(self, "_approval", None)
        if handler is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return handler

    @property
    def fs(self) -> BuildFilesystemInit:
        if self._fs is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._fs

    @property
    def dispatcher(self) -> BuildSignalDispatcher:
        if self._dispatcher is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._dispatcher

    @property
    def issue_manager(self) -> IssueManager:
        if self._issue_manager is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._issue_manager

    @property
    def code_generator(self) -> CodeGenerator:
        if self._code_gen is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._code_gen

    @property
    def pr_manager(self) -> PRManager:
        if self._pr_manager is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._pr_manager

    @property
    def deploy_manager(self) -> DeployManager:
        if self._deploy_manager is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._deploy_manager

    @property
    def error_monitor(self) -> ErrorMonitor:
        if self._error_monitor is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._error_monitor

    @property
    def cost_monitor(self) -> CostMonitor:
        if self._cost_monitor is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._cost_monitor

    @property
    def dependency_auditor(self) -> DependencyAuditor:
        if self._dependency_auditor is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._dependency_auditor

    @property
    def doc_maintainer(self) -> DocMaintainer:
        if self._doc_maintainer is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._doc_maintainer

    @property
    def scheduler(self) -> BuildScheduler:
        if self._scheduler is None:
            raise RuntimeError("BuildClaw not started — call startup() first")
        return self._scheduler
