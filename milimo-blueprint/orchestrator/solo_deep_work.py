#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Deep Work Mode

Activates focused work mode for solo founders.
Hot-reloads claw policies to reduce interruptions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger("milimo.solo_deep_work")


# ---------------------------------------------------------------------------

DEEP_WORK_POLICIES = {
    "pause_drafts": {
        "description": "Queue only, no publishing",
        "actions_blocked": ["publish", "send"],
        "actions_queued": ["draft", "create", "schedule"],
    },
    "maintenance": {
        "description": "Auto-responses to active clients",
        "actions_blocked": ["new_outreach", "follow_up"],
        "actions_queued": ["maintenance", "status_update"],
    },
    "passive": {
        "description": "Collect data, no new experiments",
        "actions_blocked": ["experiment", "test"],
        "actions_queued": ["collect", "analyze"],
    },
    "invoices_only": {
        "description": "Sends continue, no new intake",
        "actions_blocked": ["new_invoice", "new_client"],
        "actions_queued": ["send_reminder", "process"],
    },
    "issues_only": {
        "description": "Triage only, no new PRs opened",
        "actions_blocked": ["open_pr", "merge"],
        "actions_queued": ["triage", "label", "comment"],
    },
}

CLAW_ON_ACTIVATE_MAP = {
    "content": "pause_drafts",
    "ops": "maintenance",
    "analytics": "passive",
    "finance": "invoices_only",
    "build": "issues_only",
}


# ---------------------------------------------------------------------------

@dataclass
class DeepWorkState:
    """State of deep work mode."""
    active: bool = False
    activated_at: Optional[datetime] = None
    resume_date: Optional[datetime] = None
    auto_response_template: str = ""
    claw_policies: dict[str, str] = field(default_factory=dict)


@dataclass
class ClawPolicyUpdate:
    """Policy update for a claw."""
    claw: str
    previous_policy: str
    new_policy: str
    blocked_actions: list[str] = field(default_factory=list)
    queued_actions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------

def activate_deep_work_mode(
    config: dict[str, Any],
    resume_date: str,
    policy_dir: Optional[Path] = None,
    state_file: Optional[Path] = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Activate deep work mode for solo founder.

    Hot-reloads each claw's policy to its on_activate setting.
    Sets auto-response template with the provided resume_date.
    Schedules automatic resume on resume_date.

    Args:
        config: Validated solo-founder configuration
        resume_date: Date to resume normal operations (YYYY-MM-DD)
        policy_dir: Directory containing claw policies
        state_file: Path to store deep work state
        quiet: If True, suppress console output

    Returns:
        Summary of what was changed per claw
    """
    deep_work_config = config.get("deep_work_mode", {})

    on_activate = deep_work_config.get("on_activate", CLAW_ON_ACTIVATE_MAP)
    auto_response_template = deep_work_config.get(
        "auto_response_template",
        "Hey [name], I'm heads-down until [resume_date]."
    )

    try:
        resume_dt = datetime.strptime(resume_date, "%Y-%m-%d")
        resume_dt = resume_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError(f"Invalid resume_date format: {resume_date}. Use YYYY-MM-DD.")

    if policy_dir is None:
        policy_dir = Path(__file__).parent.parent / "policies"

    if state_file is None:
        state_dir = Path.home() / ".milimo" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "deep_work.json"

    policy_updates: list[ClawPolicyUpdate] = []
    updated_policies: list[str] = []

    for claw, policy_name in on_activate.items():
        policy_data = DEEP_WORK_POLICIES.get(policy_name, {})

        previous_policy = _get_current_policy(claw, policy_dir)

        update = ClawPolicyUpdate(
            claw=claw,
            previous_policy=previous_policy,
            new_policy=policy_name,
            blocked_actions=policy_data.get("actions_blocked", []),
            queued_actions=policy_data.get("actions_queued", []),
        )
        policy_updates.append(update)

        if policy_dir.exists():
            _update_claw_policy(claw, policy_name, policy_dir)
            updated_policies.append(claw)

        logger.info(
            f"Deep work mode: {claw} -> {policy_name} "
            f"(blocked: {update.blocked_actions}, queued: {update.queued_actions})"
        )

    state = DeepWorkState(
        active=True,
        activated_at=datetime.now(timezone.utc),
        resume_date=resume_dt,
        auto_response_template=auto_response_template,
        claw_policies=on_activate,
    )

    _save_state(state, state_file)

    formatted_response = auto_response_template.replace("[resume_date]", resume_date)

    result: dict[str, Any] = {
        "active": True,
        "activated_at": state.activated_at.isoformat() if state.activated_at else None,
        "resume_date": resume_date,
        "auto_response": formatted_response,
        "policies_updated": updated_policies,
        "policy_changes": [
            {
                "claw": u.claw,
                "previous": u.previous_policy,
                "new": u.new_policy,
                "blocked_actions": u.blocked_actions,
                "queued_actions": u.queued_actions,
            }
            for u in policy_updates
        ],
    }

    if not quiet:
        _print_confirmation_summary(result)

    return result


def deactivate_deep_work_mode(
    config: dict[str, Any],
    policy_dir: Optional[Path] = None,
    state_file: Optional[Path] = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Deactivate deep work mode and restore normal operations.

    Args:
        config: Validated solo-founder configuration
        policy_dir: Directory containing claw policies
        state_file: Path where deep work state is stored
        quiet: If True, suppress console output

    Returns:
        Summary of what was restored
    """
    if state_file is None:
        state_dir = Path.home() / ".milimo" / "state"
        state_file = state_dir / "deep_work.json"

    if policy_dir is None:
        policy_dir = Path(__file__).parent.parent / "policies"

    state = _load_state(state_file)

    if not state or not state.active:
        logger.info("Deep work mode is not active")
        return {"active": False, "message": "Deep work mode is not active"}

    restored_policies: list[str] = []

    for claw in state.claw_policies.keys():
        if policy_dir.exists():
            _restore_claw_policy(claw, policy_dir)
            restored_policies.append(claw)

    _clear_state(state_file)

    logger.info("Deep work mode deactivated, normal operations resumed")

    result: dict[str, Any] = {
        "active": False,
        "deactivated_at": datetime.now(timezone.utc).isoformat(),
        "policies_restored": restored_policies,
        "message": "Normal operations resumed",
    }

    if not quiet:
        _print_deactivation_summary(result)

    return result


def _get_current_policy(claw: str, policy_dir: Path) -> str:
    """Get current policy for a claw."""
    policy_file = policy_dir / f"{claw}-claw.yaml"

    if not policy_file.exists():
        return "normal"

    try:
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)
            return policy.get("deep_work_policy", "normal")
    except Exception:
        return "normal"


def _update_claw_policy(claw: str, policy_name: str, policy_dir: Path) -> None:
    """Update claw policy file with deep work settings."""
    policy_file = policy_dir / f"{claw}-claw.yaml"

    if not policy_file.exists():
        return

    with policy_file.open("r") as f:
        policy = yaml.safe_load(f) or {}

    policy["deep_work_policy"] = policy_name
    policy["deep_work_active"] = True
    policy["deep_work_activated_at"] = datetime.now(timezone.utc).isoformat()

    policy_data = DEEP_WORK_POLICIES.get(policy_name, {})
    policy["deep_work_blocked_actions"] = policy_data.get("actions_blocked", [])
    policy["deep_work_queued_actions"] = policy_data.get("actions_queued", [])

    with policy_file.open("w") as f:
        yaml.dump(policy, f, default_flow_style=False)


def _restore_claw_policy(claw: str, policy_dir: Path) -> None:
    """Restore claw policy to normal operation."""
    policy_file = policy_dir / f"{claw}-claw.yaml"

    if not policy_file.exists():
        return

    with policy_file.open("r") as f:
        policy = yaml.safe_load(f) or {}

    policy.pop("deep_work_policy", None)
    policy.pop("deep_work_active", None)
    policy.pop("deep_work_activated_at", None)
    policy.pop("deep_work_blocked_actions", None)
    policy.pop("deep_work_queued_actions", None)

    with policy_file.open("w") as f:
        yaml.dump(policy, f, default_flow_style=False)


def _save_state(state: DeepWorkState, state_file: Path) -> None:
    """Save deep work state to file."""
    state_file.parent.mkdir(parents=True, exist_ok=True)

    state_dict = {
        "active": state.active,
        "activated_at": state.activated_at.isoformat() if state.activated_at else None,
        "resume_date": state.resume_date.isoformat() if state.resume_date else None,
        "auto_response_template": state.auto_response_template,
        "claw_policies": state.claw_policies,
    }

    with state_file.open("w") as f:
        json.dump(state_dict, f, indent=2)


def _load_state(state_file: Path) -> Optional[DeepWorkState]:
    """Load deep work state from file."""
    if not state_file.exists():
        return None

    try:
        with state_file.open("r") as f:
            data = json.load(f)

        return DeepWorkState(
            active=data.get("active", False),
            activated_at=datetime.fromisoformat(data["activated_at"]) if data.get("activated_at") else None,
            resume_date=datetime.fromisoformat(data["resume_date"]) if data.get("resume_date") else None,
            auto_response_template=data.get("auto_response_template", ""),
            claw_policies=data.get("claw_policies", {}),
        )
    except Exception:
        return None


def _clear_state(state_file: Path) -> None:
    """Clear deep work state file."""
    if state_file.exists():
        state_file.unlink()


def _print_confirmation_summary(result: dict[str, Any]) -> None:
    """Print confirmation summary."""
    print("\n" + "=" * 60)
    print("🎯  DEEP WORK MODE ACTIVATED")
    print("=" * 60)
    print()

    print(f"Activated: {result['activated_at']}")
    print(f"Resume Date: {result['resume_date']}")
    print()

    print("Policy Changes:")
    for change in result["policy_changes"]:
        print(f"   • {change['claw'].capitalize()}: {change['previous']} → {change['new']}")
        if change["blocked_actions"]:
            print(f"     Blocked: {', '.join(change['blocked_actions'])}")
        if change["queued_actions"]:
            print(f"     Queued: {', '.join(change['queued_actions'])}")
    print()

    print("Auto-Response Template:")
    print(f"   \"{result['auto_response']}\"")
    print()

    print("To resume normal operations:")
    print("   milimo squad finals-mode --resume")
    print()

    print("=" * 60 + "\n")


def _print_deactivation_summary(result: dict[str, Any]) -> None:
    """Print deactivation summary."""
    print("\n" + "=" * 60)
    print("✅  NORMAL OPERATIONS RESUMED")
    print("=" * 60)
    print()

    print(f"Deactivated: {result['deactivated_at']}")
    print()

    print("Policies Restored:")
    for claw in result["policies_restored"]:
        print(f"   • {claw.capitalize()}")
    print()

    print("=" * 60 + "\n")


def get_deep_work_status(state_file: Optional[Path] = None) -> dict[str, Any]:
    """
    Get current deep work mode status.

    Args:
        state_file: Path where deep work state is stored

    Returns:
        Status information
    """
    if state_file is None:
        state_dir = Path.home() / ".milimo" / "state"
        state_file = state_dir / "deep_work.json"

    state = _load_state(state_file)

    if not state or not state.active:
        return {"active": False}

    return {
        "active": True,
        "activated_at": state.activated_at.isoformat() if state.activated_at else None,
        "resume_date": state.resume_date.isoformat() if state.resume_date else None,
        "auto_response_template": state.auto_response_template,
        "claw_policies": state.claw_policies,
    }


def is_deep_work_active(state_file: Optional[Path] = None) -> bool:
    """
    Check if deep work mode is active.

    Args:
        state_file: Path where deep work state is stored

    Returns:
        True if deep work mode is active
    """
    status = get_deep_work_status(state_file)
    return status.get("active", False)
