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
import threading
import time
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
            "feature_brief": self._handle_feature_brief_with_execution,
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

    def handle_inbound(self, message: dict[str, Any]) -> dict[str, Any]:
        """Route inbound message to the correct handler.

        Returns:
            Dict with handler result including status and any relevant data.
            This is written to the outbox for async result polling.
        """
        msg_type = message.get("message_type", "unknown")
        handler = self._inbound_handlers.get(msg_type)
        if handler:
            result = handler(message)
            if result is None:
                result = {
                    "status": "processed",
                    "message_type": msg_type,
                    "role": "build",
                }
            return result
        else:
            logger.warning("No handler for message type: %s", msg_type)
            return {
                "status": "no_handler",
                "message_type": msg_type,
                "role": "build",
                "error": f"No handler for message type: {msg_type}",
            }

    # ------------------------------------------------------------------
    # Execution Pipeline: feature_brief → sprint plan → approval → code → PR
    # ------------------------------------------------------------------

    def _handle_feature_brief_with_execution(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle feature_brief and trigger the full execution pipeline.

        Pipeline:
        1. Log receipt and start SLA timer (via dispatcher)
        2. Generate sprint plan from open GitHub issues
        3. Queue sprint plan for War Room approval
        4. Start a background watcher that polls for approval decisions
        and triggers code generation when approved

        Returns:
            Dict with pipeline started status
        """
        # Step 1: Log and start SLA timer
        self._dispatcher.handle_feature_brief(message)

        # Step 2 & 3: Generate sprint plan and queue for approval
        # Run in background thread to not block message processing
        thread = threading.Thread(
            target=self._execute_sprint_pipeline,
            daemon=True,
            name="build-execution-pipeline",
        )
        thread.start()

        return {
            "status": "pipeline_started",
            "message_type": "feature_brief",
            "role": "build",
            "message": "Sprint planning pipeline started. Use launcher_status() to monitor progress.",
        }

    def _execute_sprint_pipeline(self) -> None:
        """
        Execute the full sprint pipeline: plan → approve → code → PR.

        This runs in a background thread after a feature_brief is received.
        """
        try:
            # Step 2: Generate sprint plan (fetches issues, scores complexity, queues for approval)
            logger.info("Starting sprint planning pipeline")
            plan = self._issue_manager.generate_sprint_plan()
            logger.info(
                "Sprint plan generated: %s with %d issues",
                plan.plan_id,
                len(plan.issues),
            )

            if not plan.issues:
                logger.info("No issues in sprint plan — pipeline complete")
                return

            # Step 4: Start background approval watcher
            self._watch_for_approval(plan.plan_id)

        except Exception as e:
            logger.error("Sprint pipeline failed: %s", e)

    def _watch_for_approval(self, plan_id: str) -> None:
        """
        Poll for sprint plan approval and execute issues when approved.

        Checks every 30 seconds for up to 24 hours.
        """
        max_wait_seconds = 86400  # 24 hours
        poll_interval = 30
        waited = 0

        while waited < max_wait_seconds:
            try:
                plan_path = self._fs.base / "context" / "sprint" / "current-plan.json"
                if plan_path.exists():
                    import json

                    plan_data = json.loads(plan_path.read_text())
                    if plan_data.get("status") == "approved":
                        logger.info(
                            "Sprint plan %s approved — executing issues", plan_id
                        )
                        self._execute_approved_plan(plan_data)
                        return
                    elif plan_data.get("status") == "rejected":
                        logger.warning(
                            "Sprint plan %s rejected — pipeline aborted", plan_id
                        )
                        return

                time.sleep(poll_interval)
                waited += poll_interval
            except Exception as e:
                logger.error("Error polling for approval: %s", e)
                time.sleep(poll_interval)
                waited += poll_interval

        logger.warning(
            "Sprint plan %s approval timed out after %d seconds",
            plan_id,
            max_wait_seconds,
        )

    def _execute_approved_plan(self, plan_data: dict) -> None:
        """
        Execute all issues in an approved sprint plan.

        For each issue:
        1. Resolve it (read context → generate code → test → fix)
        2. Create a PR
        3. Queue for merge hold
        """
        issues = plan_data.get("issues", [])
        plan_id = plan_data.get("plan_id", "unknown")

        for idx, issue in enumerate(issues):
            try:
                issue_number = issue.get("issue_number", 0)
                logger.info(
                    "Executing issue %d/%d: #%d — %s",
                    idx + 1,
                    len(issues),
                    issue_number,
                    issue.get("title", ""),
                )

                # Import ComplexityScore for the code generator
                from .issue_manager import ComplexityScore

                score = ComplexityScore(
                    issue_number=issue_number,
                    issue_title=issue.get("title", ""),
                    complexity_tier=issue.get("complexity_tier", "M"),
                    estimated_hours=issue.get("estimated_hours", 8.0),
                    clarity_score=issue.get("clarity_score", "clear"),
                )

                # Resolve the issue (code generation + testing)
                result = self._code_gen.resolve_issue(score)
                logger.info(
                    "Issue #%d resolved: %s (tests: %d passing, %d failing, %d attempts)",
                    issue_number,
                    result.status,
                    result.tests_passing,
                    result.tests_failing,
                    result.attempts,
                )

                if result.status == "ready_for_pr":
                    # Create PR
                    pr = self._pr_manager.open_pr(result)
                    logger.info(
                        "PR created for issue #%d: %s (review_action: %s)",
                        issue_number,
                        pr.pr_id,
                        pr.review_action_id,
                    )

            except Exception as e:
                logger.error(
                    "Failed to execute issue %s: %s", issue.get("issue_number"), e
                )

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
        handler = getattr(self, "_approval_handler", None) or getattr(
            self, "_approval", None
        )
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
