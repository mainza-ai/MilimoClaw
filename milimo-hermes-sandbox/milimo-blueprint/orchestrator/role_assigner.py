# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Role Assigner

Assigns claw roles to members based on cohort configuration.
Supports automatic balancing and skill-based assignment.

Usage:
    from orchestrator.role_assigner import RoleAssigner

    assigner = RoleAssigner()
    assignments = assigner.assign_roles(members, template='campus-ai-tool')
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("milimo.role_assigner")


# ---------------------------------------------------------------------------

# Role templates define which roles are needed for each template
TEMPLATE_ROLES = {
    "content-agency": {
        "required": ["content", "ops"],
        "optional": ["analytics"],
        "max_members": 3,
    },
    "design-studio": {
        "required": ["content", "ops", "finance"],
        "optional": [],
        "max_members": 3,
    },
    "ai-micro-saas": {
        "required": ["build", "ops", "analytics"],
        "optional": ["finance"],
        "max_members": 4,
    },
    "campus-ai-tool": {
        "required": ["build", "content", "ops"],
        "optional": ["analytics"],
        "max_members": 4,
    },
    "full-squad": {
        "required": ["content", "ops", "analytics", "finance", "build", "assistant"],
        "optional": [],
        "max_members": 6,
    },
}

# Role descriptions for display
ROLE_DESCRIPTIONS = {
    "content": "Creative output — posts, copy, campaigns",
    "ops": "Client lifecycle — intake, delivery, follow-up",
    "analytics": "Intelligence — performance, trends, signals",
    "finance": "Financial ops — invoicing, pricing, margins",
    "build": "Engineering — code, PRs, deploys, monitoring",
    "assistant": "AI helper — scheduling, research, cross-claw coordination, operator support",
}

# Role prerequisites (skills that help)
ROLE_PREREQUISITES = {
    "content": ["writing", "design", "marketing"],
    "ops": ["communication", "organization", "project-management"],
    "analytics": ["data-analysis", "statistics", "visualization"],
    "finance": ["accounting", "budgeting", "spreadsheet"],
    "build": ["programming", "devops", "testing"],
    "assistant": ["communication", "scheduling", "research"],
}


# ---------------------------------------------------------------------------


@dataclass
class Member:
    """Member to be assigned a role."""

    email: str
    name: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    experience: dict[str, int] = field(default_factory=dict)  # role -> years


@dataclass
class RoleAssignment:
    """Result of role assignment."""

    member: Member
    role: str
    confidence: float = 1.0
    is_admin: bool = False
    reason: str = ""


@dataclass
class SquadAssignments:
    """Complete role assignments for a squad."""

    squad_name: str
    assignments: list[RoleAssignment]
    template: str
    missing_roles: list[str] = field(default_factory=list)
    excess_members: list[Member] = field(default_factory=list)


# ---------------------------------------------------------------------------


class RoleAssigner:
    """
    Assigns claw roles to members.

    Supports:
    - Template-based assignment
    - Skill matching
    - Preference consideration
    - Automatic balancing
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the role assigner.

        Args:
            seed: Random seed for reproducible assignments
        """
        self.random = random.Random(seed)

    def assign_roles(
        self,
        members: list[Member],
        template: str = "campus-ai-tool",
        assign_admin: bool = True,
    ) -> SquadAssignments:
        """
        Assign roles to members based on template.

        Args:
            members: Members to assign roles to
            template: Template to use for role requirements
            assign_admin: Whether to assign an admin role

        Returns:
            SquadAssignments with role assignments
        """
        template_config = TEMPLATE_ROLES.get(template, TEMPLATE_ROLES["campus-ai-tool"])

        required_roles = list(template_config["required"])
        optional_roles = list(template_config["optional"])
        max_members = template_config["max_members"]

        # Calculate needed roles
        num_members = len(members)
        all_roles = required_roles + optional_roles

        # Determine which roles to fill
        roles_to_fill = self._determine_roles(
            num_members, required_roles, optional_roles, max_members
        )

        # Score members for each role
        scores: dict[str, dict[str, float]] = {}
        for member in members:
            scores[member.email] = {}
            for role in all_roles:
                scores[member.email][role] = self._score_member_for_role(member, role)

        # Assign roles using greedy matching
        assignments: list[RoleAssignment] = []
        assigned_members: set[str] = set()

        # First pass: assign required roles based on best fit
        for role in roles_to_fill:
            best_member = None
            best_score = -1

            for member in members:
                if member.email in assigned_members:
                    continue

                score = scores[member.email].get(role, 0)
                if score > best_score:
                    best_score = score
                    best_member = member

            if best_member:
                assigned_members.add(best_member.email)
                reason = self._get_assignment_reason(best_member, role, best_score)

                assignments.append(
                    RoleAssignment(
                        member=best_member,
                        role=role,
                        confidence=min(best_score / 10, 1.0),
                        reason=reason,
                    )
                )

        # Assign admin role to first member (or best fit for ops/content)
        if assign_admin and assignments:
            # Prefer ops or content role for admin
            admin_candidates = [a for a in assignments if a.role in ["ops", "content"]]
            if admin_candidates:
                admin_candidates[0].is_admin = True
            else:
                assignments[0].is_admin = True

        # Identify missing roles and excess members
        assigned_roles = {a.role for a in assignments}
        missing_roles = [r for r in required_roles if r not in assigned_roles]

        excess_members = [m for m in members if m.email not in assigned_members]

        return SquadAssignments(
            squad_name="",
            assignments=assignments,
            template=template,
            missing_roles=missing_roles,
            excess_members=excess_members,
        )

    def _determine_roles(
        self,
        num_members: int,
        required_roles: list[str],
        optional_roles: list[str],
        max_members: int,
    ) -> list[str]:
        """Determine which roles to fill based on member count."""
        if num_members <= len(required_roles):
            return required_roles[:num_members]

        # Fill required roles first, then add optional roles
        roles = list(required_roles)

        # Add optional roles based on member count
        remaining_members = num_members - len(required_roles)
        for i, role in enumerate(optional_roles):
            if i >= remaining_members:
                break
            roles.append(role)

        return roles[:max_members]

    def _score_member_for_role(self, member: Member, role: str) -> float:
        """
        Score a member's fit for a role.

        Args:
            member: Member to score
            role: Role to score for

        Returns:
            Score (higher is better)
        """
        score = 5.0  # Base score

        # Add points for skills
        prerequisites = ROLE_PREREQUISITES.get(role, [])
        for skill in member.skills:
            if skill.lower() in [p.lower() for p in prerequisites]:
                score += 2.0

        # Add points for preferences
        if role in member.preferences:
            score += 3.0

        # Add points for experience
        if role in member.experience:
            score += min(member.experience[role], 5)  # Cap at 5 points

        return score

    def _get_assignment_reason(
        self,
        member: Member,
        role: str,
        score: float,
    ) -> str:
        """Get human-readable reason for assignment."""
        reasons = []

        if role in member.preferences:
            reasons.append("matched preference")

        matching_skills = [
            skill
            for skill in member.skills
            if skill.lower() in [p.lower() for p in ROLE_PREREQUISITES.get(role, [])]
        ]
        if matching_skills:
            reasons.append(f"relevant skills: {', '.join(matching_skills)}")

        if role in member.experience:
            reasons.append(f"{member.experience[role]} years experience")

        if not reasons:
            reasons.append("automatic assignment")

        return "; ".join(reasons)

    def balance_roles(
        self,
        squads: list[SquadAssignments],
    ) -> list[SquadAssignments]:
        """
        Balance roles across multiple squads.

        Ensures fair distribution of experience across squads.

        Args:
            squads: Squads to balance

        Returns:
            Balanced squads
        """
        # Calculate total experience per role
        role_totals: dict[str, float] = {}
        for squad in squads:
            for assignment in squad.assignments:
                role = assignment.role
                exp = assignment.member.experience.get(role, 0)
                role_totals[role] = role_totals.get(role, 0) + exp

        # This is a simplified balancing - in production, you would
        # swap members between squads to balance
        return squads


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def create_member_from_dict(data: dict[str, Any]) -> Member:
    """Create a Member from a dictionary."""
    return Member(
        email=data["email"],
        name=data.get("name"),
        skills=data.get("skills", []),
        preferences=data.get("preferences", []),
        experience=data.get("experience", {}),
    )


def get_role_description(role: str) -> str:
    """Get description for a role."""
    return ROLE_DESCRIPTIONS.get(role, "Unknown role")
