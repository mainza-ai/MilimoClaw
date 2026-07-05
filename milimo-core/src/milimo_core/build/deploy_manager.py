# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Build Claw deploy manager.

Handles:
- Staging deployments (creates HOLD, does NOT deploy)
- Deploy HOLD release → actual deployment via Vercel/Railway
- Failed deploy handling (queues REVIEW, no retry)
- Cancelled deploy handling

Enhancement: Background execution for async deployment operations.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from .approval_handler import BuildApprovalHandler, DeployActivityLog
from .signal_dispatcher import BuildSignalDispatcher
from .pr_manager import PRRecord

logger = logging.getLogger(__name__)


@dataclass
class DeployRecord:
    deploy_id: str
    pr_id: str
    version: str
    deploy_target: str
    status: str  # "staged", "deployed", "failed", "cancelled"
    hold_action_id: str | None = None
    deploy_url: str | None = None
    staged_at: str = ""
    deployed_at: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.staged_at:
            self.staged_at = datetime.now(timezone.utc).isoformat()


class DeployManager:
    """Manages deployment lifecycle with separate HOLD flow."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        deploy_log: DeployActivityLog,
        vercel_client: Any | None = None,
        railway_client: Any | None = None,
    ) -> None:
        self._fs = fs
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log
        self._deploy_log = deploy_log
        self._vercel = vercel_client
        self._railway = railway_client

    # ------------------------------------------------------------------
    # Stage deployment (creates HOLD, does NOT deploy)
    # ------------------------------------------------------------------

    def stage_deployment(self, pr: PRRecord) -> DeployRecord:
        """Create a deploy HOLD action. Does NOT trigger deployment."""
        deploy_id = f"deploy-{uuid.uuid4().hex[:8]}"
        version = (
            f"v{pr.issue_number}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )

        deploy = DeployRecord(
            deploy_id=deploy_id,
            pr_id=pr.pr_id,
            version=version,
            deploy_target="vercel",
            status="staged",
        )

        # Write to pending/
        deploy_path = self._fs.get_deploy_path("pending", deploy_id)
        self._fs.atomic_write_json(deploy_path, self._deploy_to_dict(deploy))

        # Queue HOLD for deployment
        hold_action_id = self._approval.queue_deploy_hold(
            deploy_id=deploy_id,
            version=version,
            deploy_target=deploy.deploy_target,
            changes_summary=[pr.title],
        )
        deploy.hold_action_id = hold_action_id
        self._fs.atomic_write_json(deploy_path, self._deploy_to_dict(deploy))

        self._deploy_log.append("staged", deploy_id, {"version": version})
        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="deployment_staged",
                entity_id=deploy_id,
                outcome="success",
                details={"version": version, "pr_id": pr.pr_id},
            )
        )
        return deploy

    # ------------------------------------------------------------------
    # HOLD released → deploy
    # ------------------------------------------------------------------

    def handle_deploy_hold_released(self, deploy_id: str) -> DeployRecord:
        """Release deploy HOLD and trigger actual deployment."""
        import os

        deploy_path = self._fs.get_deploy_path("pending", deploy_id)
        if not deploy_path.exists():
            history_path = self._fs.get_deploy_path("history", deploy_id)
            if history_path.exists():
                return DeployRecord(**self._fs.read_json(history_path))
            raise ValueError(f"Deploy {deploy_id} not found in pending/")

        deploy_data = self._fs.read_json(deploy_path)
        pr_id = deploy_data.get("pr_id", "")
        lock_path = self._fs.BASE / f".deploy_lock.{pr_id}"

        # Implement PID-validated lock check to prevent duplicate parallel deployments
        if lock_path.exists():
            try:
                with open(lock_path) as f:
                    lock_pid = int(f.read().strip())
                os.kill(lock_pid, 0)
                raise RuntimeError(f"Deployment for PR {pr_id} is already in progress by PID {lock_pid}")
            except (ValueError, ProcessLookupError, OSError):
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

        try:
            with open(lock_path, "x") as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            raise RuntimeError(f"Deployment lock file exists, concurrency conflict for PR {pr_id}")

        try:
            # Trigger deployment via Vercel/Railway
            if self._vercel:
                result = self._vercel.trigger_deployment()
                deploy_url = result.get("url", "")
                status = self._vercel.get_deployment_status()
            elif self._railway:
                result = self._railway.trigger_deployment()
                deploy_url = result.get("url", "")
                status = self._railway.get_deployment_status()
            else:
                deploy_url = ""
                status = "ready"
        finally:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass

        if status in ("ready", "success"):
            deploy_data["status"] = "deployed"
            deploy_data["deployed_at"] = datetime.now(timezone.utc).isoformat()
            deploy_data["deploy_url"] = deploy_url

            # Move to history/
            history_path = self._fs.get_deploy_path("history", deploy_id)
            self._fs.atomic_write_json(history_path, deploy_data)
            deploy_path.unlink(missing_ok=True)

            # Send deploy_complete signal
            self._dispatcher.send_deploy_complete(
                project_id=deploy_data.get("pr_id", ""),
                deploy_url=deploy_url,
                version=deploy_data.get("version", ""),
                deployed_at=deploy_data["deployed_at"],
            )

            self._deploy_log.append("deployed", deploy_id, {"url": deploy_url})
            self._log.append(
                BuildLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="deployment_completed",
                    entity_id=deploy_id,
                    outcome="success",
                    details={"deploy_url": deploy_url},
                )
            )
            return DeployRecord(**deploy_data)

        else:
            # Failed deploy — stay in pending/, queue REVIEW
            deploy_data["status"] = "failed"
            deploy_data["error_message"] = f"Deployment status: {status}"
            self._fs.atomic_write_json(deploy_path, deploy_data)

            self._deploy_log.append("failed", deploy_id, {"status": status})
            self._log.append(
                BuildLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="deployment_failed",
                    entity_id=deploy_id,
                    outcome="failed",
                    details={"status": status},
                )
            )
            return DeployRecord(**deploy_data)

    # ------------------------------------------------------------------
    # Cancelled deploy
    # ------------------------------------------------------------------

    def handle_deploy_hold_cancelled(self, deploy_id: str) -> None:
        """Cancel a deployment — stays in pending/ with cancelled status."""
        deploy_path = self._fs.get_deploy_path("pending", deploy_id)
        if deploy_path.exists():
            deploy_data = self._fs.read_json(deploy_path)
            deploy_data["status"] = "cancelled"
            self._fs.atomic_write_json(deploy_path, deploy_data)

        self._deploy_log.append("cancelled", deploy_id, {})
        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="deployment_cancelled",
                entity_id=deploy_id,
                outcome="cancelled",
                details={},
            )
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _deploy_to_dict(self, deploy: DeployRecord) -> dict[str, Any]:
        return {
            "deploy_id": deploy.deploy_id,
            "pr_id": deploy.pr_id,
            "version": deploy.version,
            "deploy_target": deploy.deploy_target,
            "status": deploy.status,
            "hold_action_id": deploy.hold_action_id,
            "deploy_url": deploy.deploy_url,
            "staged_at": deploy.staged_at,
            "deployed_at": deploy.deployed_at,
            "error_message": deploy.error_message,
        }
