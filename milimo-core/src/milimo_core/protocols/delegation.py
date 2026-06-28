# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Delegation Protocol — Profile-agnostic interface for claw parallelism.

This module defines the abstract interface for executing claw tasks in parallel.
Concrete implementations are profile-specific:

- OpenClaw profile: uses `sessions_spawn` (implemented in milimo-blueprint/orchestrator/mesh.py)
- Hermes profile: uses native `delegate_task` (implemented in milimo-hermes-plugin/delegation.py)

The interface is defined here in milimo-core so that:
1. Tool schemas (milimo_warroom, milimo_approve, milimo_veto) can use shared types
2. Unit tests can inject MockDelegationAdapter without Hermes runtime
3. Future profiles can implement without touching existing code
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ClawTask:
    """Profile-agnostic claw task descriptor."""
    claw: str          # "build", "content", "ops", "analytics", "finance", "assistant"
    goal: str
    context: str = ""
    priority: int = 0  # 0 = normal, 1 = urgent (Finance/Ops approval flows)


@dataclass
class ClawResult:
    """Profile-agnostic claw task result."""
    claw: str
    output: Any
    success: bool
    error: str | None = None


class DelegationAdapter(ABC):
    """
    Profile-agnostic interface for claw parallelism.

    OpenClaw profile implements via sessions_spawn.
    Hermes profile implements via delegate_task.
    Neither implementation leaks into milimo-core.
    """

    # Toolset mappings per claw — profile-agnostic business logic
    CLAW_TOOLSETS: dict[str, list[str]] = {
        "build":     ["file", "shell"],
        "content":   ["web", "file"],
        "ops":       ["file", "shell"],
        "analytics": ["file"],
        "finance":   ["file"],
        "assistant": ["file", "web"],
    }

    # Context strings per claw — profile-agnostic business logic
    CLAW_CONTEXTS: dict[str, str] = {
        "build":     "You are the Build Claw. Handle CI/CD, deployments, dependency auditing.",
        "content":   "You are the Content Claw. Generate and schedule content.",
        "ops":       "You are the Ops Claw. Manage incidents, projects, client health.",
        "analytics": "You are the Analytics Claw. Process signals, detect anomalies, report.",
        "finance":   "You are the Finance Claw. Handle invoicing, payments, pricing.",
        "assistant": "You are Lucy, the conversational interface for all claws.",
    }

    @abstractmethod
    async def delegate(self, tasks: list[ClawTask]) -> list[ClawResult]:
        """
        Execute claw tasks in parallel.

        Profile-specific implementation:
        - Hermes: calls native delegate_task tool
        - OpenClaw: uses sessions_spawn
        """
        ...

    @abstractmethod
    async def delegate_single(self, task: ClawTask) -> ClawResult:
        """Execute a single claw task. Used for HOLD/REVIEW flows."""
        ...

    def build_context(self, task: ClawTask) -> str:
        """Build full context string for a claw task."""
        base = self.CLAW_CONTEXTS.get(task.claw, "")
        return f"{base}\n{task.context}".strip() if task.context else base


__all__ = [
    "ClawTask",
    "ClawResult",
    "DelegationAdapter",
]
