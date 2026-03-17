#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Proposal Pipeline

Defines the schema for evolved tool proposals, validates that proposed
tools stay within the claw's existing policy boundaries, and generates
proposals from detected patterns.

Usage:
    from tool_proposal import ToolProposal, validate_permissions, generate_proposal

    proposal = generate_proposal(pattern, claw_role="content")
    if validate_permissions(proposal, sandbox_policy):
        # proceed to build & test
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .pattern_detector import EvolutionPattern

logger = logging.getLogger("milimo.tool_proposal")


# Valid tool types (must match pattern_types in evolution_config.yaml)
VALID_TOOL_TYPES = frozenset({
    "classifier",
    "optimizer",
    "predictor",
    "generator_variant",
    "anomaly_detector",
})

# Valid proposal statuses
VALID_STATUSES = frozenset({
    "proposed",
    "approved",
    "building",
    "testing",
    "deployed",
    "rejected",
    "disabled",
    "failed",
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ToolProposal:
    """A proposal for a new evolved tool."""

    tool_name: str
    tool_type: str  # classifier | optimizer | predictor | generator_variant | anomaly_detector
    trigger_pattern: EvolutionPattern
    metric_target: str
    data_sources_required: list[str] = field(default_factory=list)
    estimated_improvement: float = 0.0  # predicted % uplift
    status: str = "proposed"
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    claw_role: str = ""
    squad_id: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    rejection_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolProposal:
        # Handle nested EvolutionPattern
        trigger = data.get("trigger_pattern", {})
        if isinstance(trigger, dict):
            data["trigger_pattern"] = EvolutionPattern(**{
                k: v for k, v in trigger.items()
                if k in EvolutionPattern.__dataclass_fields__
            })
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_permissions(
    proposal: ToolProposal,
    sandbox_policy: dict[str, Any],
) -> tuple[bool, str]:
    """
    Validate that a proposed tool only needs resources within the
    claw's existing sandbox policy.

    Critical constraint: Evolution cannot expand a claw's permissions.
    A tool that requires access to mounts or endpoints not in the
    policy is rejected.

    Returns (is_valid, reason).
    """
    # Validate tool type
    if proposal.tool_type not in VALID_TOOL_TYPES:
        return False, f"Invalid tool type: '{proposal.tool_type}'"

    # Validate status
    if proposal.status not in VALID_STATUSES:
        return False, f"Invalid status: '{proposal.status}'"

    # Check data sources against policy
    allowed_mounts = set()
    fs_policy = sandbox_policy.get("filesystem_policy", {})
    for mount in fs_policy.get("read_write", []):
        allowed_mounts.add(mount)
    for mount in fs_policy.get("read_only", []):
        allowed_mounts.add(mount)

    allowed_endpoints = set()
    net_policies = sandbox_policy.get("network_policies", {})
    for policy_name, policy_config in net_policies.items():
        allowed_endpoints.add(policy_name)
        for endpoint in policy_config.get("endpoints", []):
            allowed_endpoints.add(endpoint.get("host", ""))

    for source in proposal.data_sources_required:
        # Check filesystem sources
        if source.startswith("/sandbox/") or source.startswith("/tmp"):
            # Verify this path is within an allowed mount
            source_allowed = any(source.startswith(m) for m in allowed_mounts)
            if not source_allowed:
                return False, (
                    f"Tool requires filesystem access to '{source}' which is "
                    f"not in the claw's sandbox policy"
                )

        # Check network sources
        if source.startswith("https://") or source.startswith("http://"):
            host = source.split("//")[1].split("/")[0]
            if host not in allowed_endpoints:
                return False, (
                    f"Tool requires network access to '{host}' which is "
                    f"not in the claw's egress policy"
                )

    return True, "Proposal passes all permission checks"


# ---------------------------------------------------------------------------
# Proposal Generation
# ---------------------------------------------------------------------------


def generate_proposal(
    pattern: EvolutionPattern,
    claw_role: str,
    squad_id: str = "",
) -> ToolProposal:
    """
    Generate a tool proposal from a detected pattern.

    This creates the proposal metadata. The actual tool code is
    generated in the build stage (tool_builder.py).
    """
    tool_name = _derive_tool_name(pattern, claw_role)

    proposal = ToolProposal(
        tool_name=tool_name,
        tool_type=pattern.pattern_type,
        trigger_pattern=pattern,
        metric_target=pattern.metric_target,
        data_sources_required=pattern.data_sources,
        estimated_improvement=_estimate_improvement(pattern),
        claw_role=claw_role,
        squad_id=squad_id,
    )

    logger.info(
        "Generated proposal '%s' (%s) for %s — estimated +%.1f%% on %s",
        proposal.tool_name,
        proposal.tool_type,
        claw_role,
        proposal.estimated_improvement,
        proposal.metric_target,
    )

    return proposal


def load_sandbox_policy(policy_path: str | Path) -> dict[str, Any]:
    """Load a sandbox policy YAML file for permission validation."""
    path = Path(policy_path)
    if not path.exists():
        raise FileNotFoundError(f"Sandbox policy not found: {path}")
    with path.open() as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive_tool_name(pattern: EvolutionPattern, claw_role: str) -> str:
    """
    Derive a human-readable tool name from the pattern.

    Examples:
    - edit pattern on "tone" → "tone_classifier"
    - low approval on "social_post_draft" → "draft_quality_predictor"
    - timing pattern → "timing_optimizer"
    - metric drift on "engagement_rate" → "engagement_anomaly_detector"
    - cross-signal from analytics → "analytics_cross_predictor"
    """
    details = pattern.details

    if pattern.pattern_type == "classifier" and "edit_field" in details:
        return f"{details['edit_field']}_{pattern.pattern_type}"

    if pattern.pattern_type == "predictor" and "action_type" in details:
        action = details["action_type"].replace("_", " ").split()
        short = "_".join(action[:2]) if len(action) > 1 else action[0]
        return f"{short}_quality_predictor"

    if pattern.pattern_type == "optimizer":
        return "timing_optimizer"

    if pattern.pattern_type == "anomaly_detector" and "metric_name" in details:
        metric = details["metric_name"].replace("_", " ").split()[0]
        return f"{metric}_anomaly_detector"

    if pattern.pattern_type == "predictor" and "sender_role" in details:
        return f"{details['sender_role']}_cross_predictor"

    return f"{claw_role}_{pattern.pattern_type}_{pattern.confidence:.0f}"


def _estimate_improvement(pattern: EvolutionPattern) -> float:
    """
    Estimate the percentage improvement a tool might achieve.

    This is a rough heuristic based on the pattern's confidence and type.
    The actual improvement is measured during backtesting.
    """
    base = pattern.confidence * 15.0  # Higher confidence → higher estimate

    # Type multiplier
    multipliers = {
        "classifier": 1.2,
        "optimizer": 1.1,
        "predictor": 1.0,
        "generator_variant": 0.8,
        "anomaly_detector": 0.9,
    }
    multiplier = multipliers.get(pattern.pattern_type, 1.0)

    return round(base * multiplier, 1)
