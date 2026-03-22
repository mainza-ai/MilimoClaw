#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Deploy Manager

Manages the deployment pipeline after PR merge.

SEPARATE TWO-STAGE FLOW (independent of PR approval):
1. PR merged → deployment staged automatically
2. Deploy queued as its own HOLD
3. HOLD released → deployment triggered via Vercel/Railway API
4. On success: send deploy_complete to Ops, accumulate for shipping_summary
5. On failure: queue REVIEW — do NOT retry automatically

A merged PR that has not been deployed remains in deployments/pending/
indefinitely until operator acts on the deploy HOLD.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler, DeployActivityLog
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .pr_manager import PRRecord
    from .signal_dispatcher import BuildSignalDispatcher

logger = logging.getLogger("milimo.build")

DEPLOY_TIMEOUT_SECONDS = 300  # 5 minutes


@dataclass
class DeployRecord:
    """Record of a deployment."""

    deploy_id: str
    pr_id: str
    version: str
    deploy_target: str
    changes_summary: list[str]
    status: str
    hold_action_id: str | None
    staged_at: str
    deployed_at: str | None
    deploy_url: str | None
    failure_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "deploy_id": self.deploy_id,
            "pr_id": self.pr_id,
            "version": self.version,
            "deploy_target": self.deploy_target,
            "changes_summary": self.changes_summary,
            "status": self.status,
            "hold_action_id": self.hold_action_id,
            "staged_at": self.staged_at,
            "deployed_at": self.deployed_at,
            "deploy_url": self.deploy_url,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeployRecord:
        return cls(
            deploy_id=data["deploy_id"],
            pr_id=data["pr_id"],
            version=data["version"],
            deploy_target=data["deploy_target"],
            changes_summary=data.get("changes_summary", []),
            status=data["status"],
            hold_action_id=data.get("hold_action_id"),
            staged_at=data["staged_at"],
            deployed_at=data.get("deployed_at"),
            deploy_url=data.get("deploy_url"),
            failure_reason=data.get("failure_reason"),
        )


class DeployManager:
    """
    Manages the deployment pipeline after PR merge.

    SEPARATE TWO-STAGE FLOW (independent of PR approval):
    1. PR merged → deployment staged automatically
    2. Deploy queued as its own HOLD
    3. HOLD released → deployment triggered via Vercel/Railway API
    4. On success: send deploy_complete to Ops, accumulate for shipping_summary
    5. On failure: queue REVIEW — do NOT retry automatically

    A merged PR that has not been deployed remains in deployments/pending/
    indefinitely until operator acts on the deploy HOLD.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
        deploy_log: DeployActivityLog,
        vercel_client: Any | None = None,
        railway_client: Any | None = None,
    ):
        self._fs = fs
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log
        self._deploy_log = deploy_log
        self._vercel = vercel_client
        self._railway = railway_client

    def stage_deployment(self, merged_pr: PRRecord) -> DeployRecord:
        deploy_id = f"deploy-{uuid.uuid4().hex[:8]}"

        version = self._derive_version(merged_pr)
        deploy_target = self._detect_deploy_target()

        changes_summary = self._extract_changes_summary(merged_pr)

        deploy = DeployRecord(
            deploy_id=deploy_id,
            pr_id=merged_pr.pr_id,
            version=version,
            deploy_target=deploy_target,
            changes_summary=changes_summary,
            status="staged",
            hold_action_id=None,
            staged_at=datetime.now(timezone.utc).isoformat(),
            deployed_at=None,
            deploy_url=None,
            failure_reason=None,
        )

        deploy_path = self._fs.get_deploy_path("pending", deploy_id)
        self._fs.atomic_write_json(deploy_path, deploy.to_dict())

        hold_action_id = self._approval.queue_deploy_hold(
            deploy_id=deploy_id,
            version=version,
            deploy_target=deploy_target,
            changes_summary=changes_summary,
        )

        deploy.hold_action_id = hold_action_id
        self._fs.atomic_write_json(deploy_path, deploy.to_dict())

        self._deploy_log.append("deploy_staged", deploy_id, {
            "version": version,
            "deploy_target": deploy_target,
            "pr_id": merged_pr.pr_id,
            "hold_action_id": hold_action_id,
        })

        self._log.append(self._create_log_entry(
            "deployment_staged",
            deploy_id,
            "pending_hold",
            {
                "version": version,
                "pr_id": merged_pr.pr_id,
                "hold_action_id": hold_action_id,
            },
        ))

        return deploy

    def handle_deploy_hold_released(self, deploy_id: str) -> DeployRecord:
        deploy = self.load_deploy(deploy_id, "pending")
        if not deploy:
            logger.error("Deploy not found in pending: %s", deploy_id)
            raise ValueError(f"Deploy not found in pending: {deploy_id}")

        if deploy.status != "staged":
            raise ValueError(f"Deploy status is '{deploy.status}', expected 'staged'")

        self._deploy_log.append("hold_released", deploy_id, {
            "version": deploy.version,
            "deploy_target": deploy.deploy_target,
        })

        try:
            if deploy.deploy_target == "vercel":
                success, deploy_url = self._trigger_vercel_deploy(deploy_id)
            elif deploy.deploy_target == "railway":
                success, deploy_url = self._trigger_railway_deploy(deploy_id)
            else:
                success, deploy_url = self._trigger_generic_deploy(deploy_id)

            if success:
                deploy.status = "deployed"
                deploy.deployed_at = datetime.now(timezone.utc).isoformat()
                deploy.deploy_url = deploy_url

                old_path = self._fs.get_deploy_path("pending", deploy_id)
                new_path = self._fs.get_deploy_path("history", deploy_id)

                self._fs.atomic_write_json(new_path, deploy.to_dict())
                if old_path.exists():
                    old_path.unlink()

                self._dispatcher.send_deploy_complete(
                    project_id=deploy.pr_id,
                    deploy_url=deploy_url or "",
                    version=deploy.version,
                    deployed_at=deploy.deployed_at,
                )

                self._dispatcher.accumulate_shipping_data(
                    pr_id=deploy.pr_id,
                    issue_number=0,
                    feature_name=f"Deploy {deploy.version}",
                    changes=deploy.changes_summary,
                )

                self._deploy_log.append("deploy_success", deploy_id, {
                    "version": deploy.version,
                    "deploy_url": deploy_url,
                })

                self._log.append(self._create_log_entry(
                    "deployed_to_production",
                    deploy_id,
                    "success",
                    {
                        "version": deploy.version,
                        "deploy_url": deploy_url,
                    },
                ))

                return deploy

            else:
                deploy.status = "failed"
                deploy.failure_reason = "Deployment returned failure status"

                deploy_path = self._fs.get_deploy_path("pending", deploy_id)
                self._fs.atomic_write_json(deploy_path, deploy.to_dict())

                self._queue_deploy_failure_review(deploy)

                self._deploy_log.append("deploy_failed", deploy_id, {
                    "version": deploy.version,
                    "failure_reason": deploy.failure_reason,
                })

                self._log.append(self._create_log_entry(
                    "deploy_failed",
                    deploy_id,
                    "failed",
                    {"failure_reason": deploy.failure_reason},
                ))

                return deploy

        except Exception as e:
            deploy.status = "failed"
            deploy.failure_reason = str(e)

            deploy_path = self._fs.get_deploy_path("pending", deploy_id)
            self._fs.atomic_write_json(deploy_path, deploy.to_dict())

            self._queue_deploy_failure_review(deploy)

            self._deploy_log.append("deploy_failed", deploy_id, {
                "version": deploy.version,
                "failure_reason": str(e),
            })

            self._log.append(self._create_log_entry(
                "deploy_failed",
                deploy_id,
                "failed",
                {"failure_reason": str(e)},
            ))

            return deploy

    def handle_deploy_hold_cancelled(self, deploy_id: str) -> None:
        deploy = self.load_deploy(deploy_id, "pending")
        if not deploy:
            logger.error("Deploy not found in pending: %s", deploy_id)
            raise ValueError(f"Deploy not found: {deploy_id}")

        deploy.status = "cancelled"

        deploy_path = self._fs.get_deploy_path("pending", deploy_id)
        self._fs.atomic_write_json(deploy_path, deploy.to_dict())

        self._deploy_log.append("deploy_cancelled", deploy_id, {
            "version": deploy.version,
        })

        self._log.append(self._create_log_entry(
            "deploy_cancelled",
            deploy_id,
            "cancelled",
            {"version": deploy.version},
        ))

    def _trigger_vercel_deploy(self, deploy_id: str) -> tuple[bool, str | None]:
        if not self._vercel:
            logger.warning("Vercel client not configured")
            return (False, None)

        try:
            result = self._vercel.trigger_deployment()

            import time
            start = time.time()
            while time.time() - start < DEPLOY_TIMEOUT_SECONDS:
                status = self._vercel.get_deployment_status(result.get("id"))
                if status == "ready":
                    return (True, result.get("url"))
                elif status == "error":
                    return (False, None)
                time.sleep(5)

            return (False, None)

        except Exception as e:
            logger.error("Vercel deployment failed: %s", e)
            return (False, None)

    def _trigger_railway_deploy(self, deploy_id: str) -> tuple[bool, str | None]:
        if not self._railway:
            logger.warning("Railway client not configured")
            return (False, None)

        try:
            result = self._railway.trigger_deployment()

            import time
            start = time.time()
            while time.time() - start < DEPLOY_TIMEOUT_SECONDS:
                status = self._railway.get_deployment_status(result.get("id"))
                if status == "success":
                    return (True, result.get("url"))
                elif status == "failed":
                    return (False, None)
                time.sleep(5)

            return (False, None)

        except Exception as e:
            logger.error("Railway deployment failed: %s", e)
            return (False, None)

    def _trigger_generic_deploy(self, deploy_id: str) -> tuple[bool, str | None]:
        logger.info("No deployment target configured, treating as success")
        return (True, f"https://staging.example.com/{deploy_id}")

    def _derive_version(self, pr: PRRecord) -> str:
        return f"v1.0.{pr.github_pr_number or 0}"

    def _detect_deploy_target(self) -> str:
        return "vercel"

    def _extract_changes_summary(self, pr: PRRecord) -> list[str]:
        summary = [pr.title]
        if pr.description:
            lines = pr.description.split("\n")[:3]
            summary.extend(lines)
        return summary

    def _queue_deploy_failure_review(self, deploy: DeployRecord) -> None:
        self._approval.queue_error_pattern_review(
            error_id=deploy.deploy_id,
            error_summary=f"Deployment failed for {deploy.version}",
            occurrence_count=1,
            is_known_pattern=False,
            auto_patch_available=False,
        )

    def get_pending_deployments(self) -> list[DeployRecord]:
        pending_dir = self._fs._base / "deployments" / "pending"
        if not pending_dir.exists():
            return []

        deploys = []
        for deploy_file in pending_dir.glob("*.json"):
            data = self._fs.read_json(deploy_file)
            if data:
                deploys.append(DeployRecord.from_dict(data))

        return deploys

    def load_deploy(self, deploy_id: str, status: str) -> DeployRecord | None:
        deploy_path = self._fs.get_deploy_path(status, deploy_id)
        data = self._fs.read_json(deploy_path)
        if data:
            return DeployRecord.from_dict(data)
        return None

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
