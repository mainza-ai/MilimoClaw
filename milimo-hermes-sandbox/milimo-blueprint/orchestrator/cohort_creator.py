# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Cohort Creator

Creates multiple squads in bulk for university/accelerator programs.
Supports templates, role assignment, and progress tracking.

Usage:
    from orchestrator.cohort_creator import CohortCreator

    creator = CohortCreator(tenant_id='stanford-ent')
    cohort = await creator.create_from_template(template_data)
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from .milimo_paths import cohorts_dir

logger = logging.getLogger("milimo.cohort_creator")

# ---------------------------------------------------------------------------


@dataclass
class CohortMember:
    """Member to add to a squad."""

    email: str
    role: str
    is_admin: bool = False
    name: Optional[str] = None


@dataclass
class CohortSquad:
    """Squad to create within a cohort."""

    name: str
    members: list[CohortMember]
    custom_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class CohortTemplate:
    """Template for cohort creation."""

    name: str
    squads: list[CohortSquad]
    template: str = "campus-ai-tool"
    tenant_id: str = ""
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CohortTemplate":
        """Create template from dictionary."""
        squads = []
        for squad_data in data.get("squads", []):
            members = [
                CohortMember(
                    email=m["email"],
                    role=m["role"],
                    is_admin=m.get("is_admin", False),
                    name=m.get("name"),
                )
                for m in squad_data.get("members", [])
            ]
            squads.append(
                CohortSquad(
                    name=squad_data["name"],
                    members=members,
                    custom_config=squad_data.get("custom_config", {}),
                )
            )

        return cls(
            name=data["name"],
            squads=squads,
            template=data.get("template", "campus-ai-tool"),
            tenant_id=data.get("tenant_id", ""),
            description=data.get("description", ""),
            settings=data.get("settings", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SquadCreationResult:
    """Result of creating a single squad."""

    squad_id: str
    squad_name: str
    status: Literal["success", "failed", "pending"]
    members_invited: int = 0
    error: Optional[str] = None


@dataclass
class CohortCreationProgress:
    """Progress tracking for cohort creation."""

    cohort_id: str
    cohort_name: str
    status: Literal["pending", "creating", "active", "completed", "failed"]
    total_squads: int = 0
    squads_created: int = 0
    squads_failed: int = 0
    members_invited: int = 0
    members_joined: int = 0
    results: list[SquadCreationResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    @property
    def progress_percent(self) -> float:
        """Get creation progress as percentage."""
        if self.total_squads == 0:
            return 0.0
        return (self.squads_created / self.total_squads) * 100


# ---------------------------------------------------------------------------


class CohortCreator:
    """
    Creates squads in bulk for cohort programs.

    Supports:
    - Template-based creation
    - Automatic role assignment
    - Progress tracking
    - Error recovery
    """

    def __init__(
        self,
        tenant_id: str,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize the cohort creator.

        Args:
            tenant_id: Tenant identifier
            storage_dir: Directory to store cohort data
        """
        self.tenant_id = tenant_id
        self.storage_dir = storage_dir or cohorts_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._cohorts: dict[str, CohortCreationProgress] = {}

    async def create_from_template(
        self,
        template_data: dict[str, Any],
        batch_size: int = 5,
    ) -> CohortCreationProgress:
        """
        Create a cohort from a template.

        Args:
            template_data: Template configuration
            batch_size: Number of squads to create concurrently

        Returns:
            CohortCreationProgress tracking object
        """
        template = CohortTemplate.from_dict(template_data)

        cohort_id = f"cohort_{secrets.token_hex(8)}"

        progress = CohortCreationProgress(
            cohort_id=cohort_id,
            cohort_name=template.name,
            status="creating",
            total_squads=len(template.squads),
        )

        self._cohorts[cohort_id] = progress

        logger.info(
            f"Creating cohort '{template.name}' with {len(template.squads)} squads"
        )

        # Create squads in batches
        for i in range(0, len(template.squads), batch_size):
            batch = template.squads[i : i + batch_size]
            tasks = [
                self._create_squad(squad, template.template, progress)
                for squad in batch
            ]
            await asyncio.gather(*tasks)

            logger.info(
                f"Cohort {cohort_id}: {progress.squads_created}/{progress.total_squads} squads created"
            )

        # Update final status
        if progress.squads_failed == 0:
            progress.status = "completed"
        elif progress.squads_created > 0:
            progress.status = "active"
        else:
            progress.status = "failed"

        progress.completed_at = datetime.now(timezone.utc)

        # Save cohort data
        self._save_cohort(cohort_id, template, progress)

        return progress

    async def _create_squad(
        self,
        squad: CohortSquad,
        template: str,
        progress: CohortCreationProgress,
    ) -> SquadCreationResult:
        """
        Create a single squad.

        Args:
            squad: Squad to create
            template: Blueprint template to use
            progress: Progress tracker

        Returns:
            SquadCreationResult
        """
        squad_id = f"squad_{secrets.token_hex(8)}"

        try:
            # Simulate squad creation (replace with actual implementation)
            await asyncio.sleep(0.1)  # Simulate API call

            # Invite members
            members_invited = len(squad.members)
            progress.members_invited += members_invited

            result = SquadCreationResult(
                squad_id=squad_id,
                squad_name=squad.name,
                status="success",
                members_invited=members_invited,
            )

            progress.squads_created += 1
            progress.results.append(result)

            logger.debug(f"Created squad: {squad.name} ({squad_id})")

        except Exception as e:
            logger.error(f"Failed to create squad {squad.name}: {e}")

            result = SquadCreationResult(
                squad_id="",
                squad_name=squad.name,
                status="failed",
                error=str(e),
            )

            progress.squads_failed += 1
            progress.results.append(result)

        return result

    def _save_cohort(
        self,
        cohort_id: str,
        template: CohortTemplate,
        progress: CohortCreationProgress,
    ) -> None:
        """Save cohort data to storage."""
        cohort_file = self.storage_dir / f"{cohort_id}.json"

        data = {
            "cohort_id": cohort_id,
            "template": {
                "name": template.name,
                "template": template.template,
                "tenant_id": template.tenant_id,
            },
            "progress": {
                "status": progress.status,
                "total_squads": progress.total_squads,
                "squads_created": progress.squads_created,
                "squads_failed": progress.squads_failed,
                "members_invited": progress.members_invited,
                "created_at": progress.created_at.isoformat(),
                "completed_at": progress.completed_at.isoformat()
                if progress.completed_at
                else None,
            },
            "squads": [
                {
                    "squad_id": r.squad_id,
                    "squad_name": r.squad_name,
                    "status": r.status,
                    "members_invited": r.members_invited,
                }
                for r in progress.results
            ],
        }

        cohort_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved cohort data to {cohort_file}")

    def get_progress(self, cohort_id: str) -> Optional[CohortCreationProgress]:
        """Get progress for a cohort."""
        return self._cohorts.get(cohort_id)

    def list_cohorts(self) -> list[dict[str, Any]]:
        """List all cohorts for the tenant."""
        cohorts = []

        for cohort_file in self.storage_dir.glob("cohort_*.json"):
            try:
                data = json.loads(cohort_file.read_text())
                cohorts.append(data)
            except Exception as e:
                logger.warning(f"Failed to load cohort {cohort_file}: {e}")

        return cohorts

    def delete_cohort(self, cohort_id: str) -> bool:
        """Delete a cohort and its data."""
        if cohort_id in self._cohorts:
            del self._cohorts[cohort_id]

        cohort_file = self.storage_dir / f"{cohort_id}.json"

        if cohort_file.exists():
            cohort_file.unlink()
            logger.info(f"Deleted cohort {cohort_id}")
            return True

        return False


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def generate_cohort_template(
    name: str,
    num_squads: int,
    members_per_squad: int = 4,
    template: str = "campus-ai-tool",
) -> dict[str, Any]:
    """
    Generate a cohort template with placeholder members.

    Args:
        name: Cohort name
        num_squads: Number of squads to create
        members_per_squad: Members per squad
        template: Blueprint template

    Returns:
        Template dictionary
    """
    roles = ["content", "ops", "analytics", "finance", "build", "assistant"]

    squads = []
    for i in range(num_squads):
        members = []
        for j in range(min(members_per_squad, len(roles))):
            members.append(
                {
                    "email": f"team{i + 1}_member{j + 1}@example.edu",
                    "role": roles[j],
                    "is_admin": j == 0,
                }
            )

        squads.append(
            {
                "name": f"{name} - Team {i + 1}",
                "members": members,
            }
        )

    return {
        "name": name,
        "template": template,
        "squads": squads,
    }
