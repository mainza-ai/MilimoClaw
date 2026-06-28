# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Project Manager

Manages the full project lifecycle from brief to delivery.

Tracks: project status, deadline risk, deliverable receipt,
client confirmation, and project completion.
Coordinates: with Content/Build on brief sending, with Finance
on project_complete, with Analytics on client health.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


from .ops_init import OpsFilesystemInit, OpsOperationalLog, OpsLogEntry
from .signal_dispatcher import OpsSignalDispatcher
from .approval_handler import OpsApprovalHandler

logger = logging.getLogger("milimo.ops")


@dataclass
class ProjectStatus:
    """Status of a project in the Ops Claw."""

    project_id: str
    client_id: str
    status: Literal[
        "briefing",
        "pricing_pending",
        "proposal_sent",
        "active",
        "review",
        "delivered",
        "completed",
    ]
    deadline: str
    deliverable_received: bool = False
    client_confirmed: bool = False
    risk_level: str = "normal"  # "normal" | "elevated" | "critical"
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "status": self.status,
            "deadline": self.deadline,
            "deliverable_received": self.deliverable_received,
            "client_confirmed": self.client_confirmed,
            "risk_level": self.risk_level,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectStatus:
        return cls(
            project_id=data["project_id"],
            client_id=data["client_id"],
            status=data.get("status", "briefing"),
            deadline=data.get("deadline", ""),
            deliverable_received=data.get("deliverable_received", False),
            client_confirmed=data.get("client_confirmed", False),
            risk_level=data.get("risk_level", "normal"),
            last_updated=data.get("last_updated", ""),
        )


@dataclass
class DeadlineRisk:
    """Risk assessment for project deadline."""

    project_id: str
    client_id: str
    deadline: str
    days_remaining: int
    risk_level: str  # "elevated" | "critical"
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "deadline": self.deadline,
            "days_remaining": self.days_remaining,
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
        }


class ProjectManager:
    """
    Manages the full project lifecycle from brief to delivery.

    Tracks: project status, deadline risk, deliverable receipt,
    client confirmation, and project completion.
    Coordinates: with Content/Build on brief sending, with Finance
    on project_complete, with Analytics on client health.
    """

    ELEVATED_RISK_DAYS = 5
    CRITICAL_RISK_DAYS = 1

    def __init__(
        self,
        fs: OpsFilesystemInit,
        dispatcher: OpsSignalDispatcher,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog,
        inference_client: Any | None = None,
    ):
        self._fs = fs
        self._dispatcher = dispatcher
        self._approval_handler = approval_handler
        self._operational_log = operational_log
        self._inference_client = inference_client

    def create_project(
        self,
        client_id: str,
        brief: Any,
        deadline: str,
    ) -> ProjectStatus:
        project_id = f"project-{uuid.uuid4().hex[:8]}"

        self._fs.create_project_dirs(client_id, project_id)

        brief_dict = brief.to_dict() if hasattr(brief, "to_dict") else brief.__dict__
        brief_dict["project_id"] = project_id
        brief_dict["client_id"] = client_id

        project_dir = self._fs.get_project_path(client_id, project_id)
        brief_file = project_dir / "brief.json"
        self._fs.write_json_atomic(brief_file, brief_dict)

        timeline = {
            "project_id": project_id,
            "client_id": client_id,
            "deadline": deadline,
            "milestones": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        timeline_file = project_dir / "timeline.json"
        self._fs.write_json_atomic(timeline_file, timeline)

        status = ProjectStatus(
            project_id=project_id,
            client_id=client_id,
            status="pricing_pending",
            deadline=deadline,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        status_file = project_dir / "status.json"
        self._fs.write_json_atomic(status_file, status.to_dict())

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="project_created",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id, "deadline": deadline},
            )
        )

        return status

    def handle_deliverable_complete(self, message: dict[str, Any]) -> None:
        payload = message.get("payload", message)
        project_id = payload.get("project_id")
        if not project_id:
            logger.warning("deliverable_complete missing project_id")
            return

        client_id = payload.get("client_id")
        if not client_id:
            client_id = self._find_client_for_project(project_id)

        if not client_id:
            logger.warning("No client_id for project %s", project_id)
            return

        status = self._load_project_status(client_id, project_id)
        if not status:
            logger.warning("Project %s not found for deliverable", project_id)
            return

        status.deliverable_received = True
        status.status = "delivered"
        status.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_project_status(client_id, project_id, status)

        deliverables_summary = self._format_deliverables_summary(payload)

        delivery_draft = self._draft_delivery_message(
            client_id=client_id,
            project_id=project_id,
            deliverables_summary=deliverables_summary,
        )

        self._approval_handler.queue_review(
            action_type="delivery_message",
            entity_id=project_id,
            content=delivery_draft,
            context={
                "client_id": client_id,
                "project_id": project_id,
                "deliverables_summary": deliverables_summary,
            },
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="deliverable_received",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id},
            )
        )

    def handle_deploy_complete(self, message: dict[str, Any]) -> None:
        payload = message.get("payload", message)
        project_id = payload.get("project_id")
        if not project_id:
            logger.warning("deploy_complete missing project_id")
            return

        client_id = payload.get("client_id") or self._find_client_for_project(
            project_id
        )
        if not client_id:
            logger.warning("No client_id for project %s", project_id)
            return

        status = self._load_project_status(client_id, project_id)
        if status:
            status.last_updated = datetime.now(timezone.utc).isoformat()
            self._save_project_status(client_id, project_id, status)

        deploy_url = payload.get("deploy_url") or payload.get("url", "")
        version = payload.get("version", "unknown")

        notification_draft = (
            f"Deployment complete for project {project_id}.\n\n"
            f"Version: {version}\n"
            f"URL: {deploy_url}\n\n"
            "Shall I notify the client?"
        )

        self._approval_handler.queue_review(
            action_type="deploy_notification",
            entity_id=project_id,
            content=notification_draft,
            context={
                "client_id": client_id,
                "deploy_url": deploy_url,
                "version": version,
            },
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="deploy_received",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id, "version": version},
            )
        )

    def confirm_client_receipt(self, project_id: str) -> None:
        client_id = self._find_client_for_project(project_id)
        if not client_id:
            logger.warning("No client found for project %s", project_id)
            return

        status = self._load_project_status(client_id, project_id)
        if not status:
            logger.warning("Project %s not found for confirmation", project_id)
            return

        status.client_confirmed = True
        status.status = "completed"
        status.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_project_status(client_id, project_id, status)

        self._dispatcher.send_project_complete(
            project_id=project_id,
            client_id=client_id,
            delivered_at=datetime.now(timezone.utc).isoformat(),
        )

        self._archive_project(client_id, project_id)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="project_completed",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id},
            )
        )

    def check_all_deadlines(self) -> list[DeadlineRisk]:
        active_projects = self.get_active_projects()
        risks: list[DeadlineRisk] = []

        for status in active_projects:
            risk = self._check_project_deadline(status)
            if risk:
                risks.append(risk)

        return risks

    def _check_project_deadline(self, status: ProjectStatus) -> DeadlineRisk | None:
        if status.status in ("completed", "delivered"):
            return None

        if not status.deadline:
            return None

        try:
            deadline_dt = datetime.fromisoformat(status.deadline.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_remaining = (deadline_dt - now).days
        except ValueError:
            return None

        if days_remaining <= self.CRITICAL_RISK_DAYS:
            risk_level = "critical"
            recommended_action = "Immediate attention required. Deadline imminent."
        elif days_remaining <= self.ELEVATED_RISK_DAYS:
            risk_level = "elevated"
            recommended_action = "Review progress and address blockers."
        else:
            status.risk_level = "normal"
            return None

        status.risk_level = risk_level
        self._save_project_status(status.client_id, status.project_id, status)

        risk = DeadlineRisk(
            project_id=status.project_id,
            client_id=status.client_id,
            deadline=status.deadline,
            days_remaining=days_remaining,
            risk_level=risk_level,
            recommended_action=recommended_action,
        )

        if risk_level == "critical":
            self._approval_handler.queue_hold(
                action_type="deadline_critical",
                entity_id=status.project_id,
                content=f"CRITICAL: Project {status.project_id} deadline in {days_remaining} day(s).\n\n"
                f"Deadline: {status.deadline}\n"
                f"Recommended: {recommended_action}",
                context={
                    "client_id": status.client_id,
                    "deadline": status.deadline,
                    "days_remaining": days_remaining,
                },
            )
        else:
            self._approval_handler.queue_review(
                action_type="deadline_risk",
                entity_id=status.project_id,
                content=f"Elevated risk: Project {status.project_id} deadline in {days_remaining} days.\n\n"
                f"Deadline: {status.deadline}\n"
                f"Recommended: {recommended_action}",
                context={
                    "client_id": status.client_id,
                    "deadline": status.deadline,
                    "days_remaining": days_remaining,
                },
            )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="deadline_risk_detected",
                entity_id=status.project_id,
                outcome="flagged",
                details={"risk_level": risk_level, "days_remaining": days_remaining},
            )
        )

        return risk

    def update_project_status(self, project_id: str, new_status: str) -> None:
        client_id = self._find_client_for_project(project_id)
        if not client_id:
            logger.warning("No client found for project %s", project_id)
            return

        status = self._load_project_status(client_id, project_id)
        if not status:
            logger.warning("Project %s not found for status update", project_id)
            return

        status.status = new_status  # type: ignore
        status.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_project_status(client_id, project_id, status)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="project_status_updated",
                entity_id=project_id,
                outcome="success",
                details={"new_status": new_status},
            )
        )

    def get_active_projects(self) -> list[ProjectStatus]:
        projects: list[ProjectStatus] = []
        active_projects = self._fs.get_active_projects()

        for client_id, project_id in active_projects:
            status = self._load_project_status(client_id, project_id)
            if status and status.status not in ("completed",):
                projects.append(status)

        return projects

    def handle_pricing_response(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float,
    ) -> None:
        client_id = self._find_client_for_project(project_id)
        if not client_id:
            return

        status = self._load_project_status(client_id, project_id)
        if not status:
            return

        status.status = "proposal_sent"
        status.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_project_status(client_id, project_id, status)

    def _load_project_status(
        self, client_id: str, project_id: str
    ) -> ProjectStatus | None:
        project_dir = self._fs.get_project_path(client_id, project_id)
        status_file = project_dir / "status.json"
        data = self._fs.read_json(status_file)
        if not data:
            return None
        return ProjectStatus.from_dict(data)

    def _save_project_status(
        self, client_id: str, project_id: str, status: ProjectStatus
    ) -> None:
        project_dir = self._fs.get_project_path(client_id, project_id)
        status_file = project_dir / "status.json"
        self._fs.write_json_atomic(status_file, status.to_dict())

    def _find_client_for_project(self, project_id: str) -> str | None:
        active_projects = self._fs.get_active_projects()
        for client_id, proj_id in active_projects:
            if proj_id == project_id:
                return client_id
        return None

    def _archive_project(self, client_id: str, project_id: str) -> None:
        """Move a completed project to the completed directory and log the action."""
        project_dir = self._fs.get_project_path(client_id, project_id)
        completed_dir = self._fs._base / "completed" / client_id / project_id
        completed_dir.parent.mkdir(parents=True, exist_ok=True)

        if project_dir.exists():
            try:
                import shutil

                shutil.move(str(project_dir), str(completed_dir))
                logger.info("Archived project %s for client %s", project_id, client_id)
            except OSError as e:
                logger.error("Failed to archive project %s: %s", project_id, e)
                return

        if self._operational_log:
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="project_archived",
                    entity_id=project_id,
                    outcome="success",
                    details={"client_id": client_id},
                )
            )

    def _format_deliverables_summary(self, message: dict[str, Any]) -> str:
        urls = message.get("published_urls", [])
        if urls:
            return "\n".join(f"- {url}" for url in urls)
        return "Deliverables have been sent."

    def _draft_delivery_message(
        self, client_id: str, project_id: str, deliverables_summary: str
    ) -> str:
        template = self._fs.get_template("delivery-message.md")

        message = template.replace("{{client_name}}", client_id)
        message = message.replace("{{deliverables_summary}}", deliverables_summary)
        message = message.replace("{{squad_name}}", "Milimo Claw")

        if self._inference_client:
            prompt = f"""Personalize this delivery message for the client.

TEMPLATE:
{message}

PROJECT: {project_id}
CLIENT: {client_id}

Keep it warm and professional. Output only the message."""

            try:
                response = self._inference_client.complete(
                    prompt=prompt,
                    data_type="delivery_message_drafting",
                    max_tokens=300,
                )
                return response.strip()
            except Exception as e:
                logger.warning("Delivery message drafting failed: %s", e)

        return message
