#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Sandbox Initializer

Creates filesystem mounts and generates NemoClaw-compatible sandbox policies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from orchestrator.solo_init import (
    CLAWS,
    get_claw_paths,
    get_claw_network_policy,
    get_approval_modes,
)

logger = logging.getLogger("milimo.solo_sandbox")


# ---------------------------------------------------------------------------


@dataclass
class SandboxPolicy:
    """NemoClaw sandbox policy configuration."""

    claw: str
    mount: str
    network_egress: list[str] = field(default_factory=list)
    inference_routes: dict[str, str] = field(default_factory=dict)
    approval_mode: str = "REVIEW"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: str = "1.0.0"


# ---------------------------------------------------------------------------


def init_solo_sandbox(
    config: dict[str, Any], base_dir: Path | None = None
) -> dict[str, Any]:
    """
    Initialize solo founder sandbox environment.

    Creates all six filesystem mount directories and generates
    NemoClaw-compatible sandbox policy YAML files.

    Args:
        config: Validated solo-founder configuration
        base_dir: Base directory for policy output (defaults to milimo-blueprint/policies/)

    Returns:
        Summary of what was created
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent / "policies"

    base_dir.mkdir(parents=True, exist_ok=True)

    claw_paths = get_claw_paths(config)
    approval_modes = get_approval_modes(config)
    inference_config = config.get("inference", {})
    routing_overrides = inference_config.get("routing_overrides", {})

    created: dict[str, Any] = {
        "directories": [],
        "policies": [],
        "summary": {},
    }

    for claw in CLAWS:
        mount_path = claw_paths.get(claw)
        if mount_path is None:
            logger.warning(f"No mount path for {claw}, skipping")
            continue

        mount_str = str(mount_path)

        network_policy = get_claw_network_policy(config, claw)
        approved_domains = network_policy.get("approved", [])

        claw_approval_modes = approval_modes.get(claw, {})
        default_approval = _determine_default_approval(claw_approval_modes)

        policy = SandboxPolicy(
            claw=claw,
            mount=mount_str,
            network_egress=approved_domains,
            inference_routes=_get_inference_routes(claw, routing_overrides),
            approval_mode=default_approval,
        )

        policy_file = base_dir / f"{claw}-claw.yaml"
        _write_sandbox_policy(policy, policy_file)

        created["directories"].append(mount_str)
        created["policies"].append(str(policy_file))

        logger.info(f"Created policy for {claw}: {policy_file}")

    created["summary"] = {
        "claws_initialized": len(created["policies"]),
        "base_directory": str(base_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _print_summary(created)

    return created


def _determine_default_approval(claw_modes: dict[str, str]) -> str:
    """
    Determine the default approval mode for a claw.

    Args:
        claw_modes: Approval modes for action types

    Returns:
        Default approval mode (HOLD, REVIEW, or AUTO)
    """
    if not claw_modes:
        return "REVIEW"

    hold_count = sum(1 for m in claw_modes.values() if m == "HOLD")
    review_count = sum(1 for m in claw_modes.values() if m == "REVIEW")
    auto_count = sum(1 for m in claw_modes.values() if m == "AUTO")

    if hold_count > 0:
        return "HOLD"
    elif review_count > auto_count:
        return "REVIEW"
    else:
        return "AUTO"


def _get_inference_routes(
    claw: str, routing_overrides: dict[str, str]
) -> dict[str, str]:
    """
    Get inference routing configuration for a claw.

    Args:
        claw: Claw name
        routing_overrides: Global routing overrides

    Returns:
        Routing configuration for the claw
    """
    claw_specific: dict[str, str] = {}

    claw_data_types = {
        "content": ["client_facing_drafts", "public_docs_changelogs"],
        "ops": ["client_records", "internal_ideation"],
        "analytics": ["analytics_synthesis"],
        "finance": ["financial_data"],
        "build": ["source_code"],
    }

    for data_type in claw_data_types.get(claw, []):
        if data_type in routing_overrides:
            if data_type in ("financial_data", "source_code"):
                claw_specific[data_type] = "local"
            else:
                claw_specific[data_type] = routing_overrides[data_type]

    if "financial_data" not in claw_specific:
        claw_specific["financial_data"] = "local"
    if "source_code" not in claw_specific:
        claw_specific["source_code"] = "local"

    return claw_specific


def _write_sandbox_policy(policy: SandboxPolicy, output_path: Path) -> None:
    """
    Write sandbox policy to YAML file.

    Args:
        policy: SandboxPolicy object
        output_path: Path to write the policy file
    """
    policy_dict = {
        "metadata": {
            "claw": policy.claw,
            "version": policy.version,
            "created_at": policy.created_at,
            "schema": "nemoClaw-sandbox-policy-v1",
        },
        "filesystem": {
            "mount": policy.mount,
            "permissions": "rw",
            "isolation": "landlock",
        },
        "network": {
            "egress_policy": "allowlist",
            "approved_domains": policy.network_egress,
            "default_action": "deny",
        },
        "inference": {
            "routing": policy.inference_routes,
            "default_route": "local",
        },
        "operator_policy": {
            "approval_mode": policy.approval_mode,
            "war_room_access": True,
        },
        "security": {
            "seccomp": "strict",
            "capabilities": ["CAP_NET_BIND_SERVICE"],
        },
    }

    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(policy_dict, f, default_flow_style=False, sort_keys=False)


def _print_summary(created: dict[str, Any]) -> None:
    """Print initialization summary."""
    print("\n" + "=" * 60)
    print("MIIMO CLAW — SOLO FOUNDER SANDBOX INITIALIZATION")
    print("=" * 60)
    print()

    print("Directories to create:")
    for directory in created["directories"]:
        print(f"  • {directory}")
    print()

    print("Policies generated:")
    for policy_file in created["policies"]:
        print(f"  • {policy_file}")
    print()

    print("Summary:")
    summary = created["summary"]
    print(f"  Claws initialized: {summary['claws_initialized']}")
    print(f"  Base directory: {summary['base_directory']}")
    print(f"  Timestamp: {summary['timestamp']}")
    print()

    print("=" * 60)
    print("Next steps:")
    print("  1. Create the mount directories (requires sudo for /sandbox/)")
    print("  2. Run: openclaw milimo init --squad solo --role content")
    print("  3. Launch War Room: openclaw milimo warroom")
    print("=" * 60 + "\n")


def create_mount_directories(config: dict[str, Any], dry_run: bool = True) -> list[str]:
    """
    Create filesystem mount directories.

    Args:
        config: Validated solo-founder configuration
        dry_run: If True, only print what would be done

    Returns:
        List of commands that would create the directories
    """
    claw_paths = get_claw_paths(config)
    commands: list[str] = []

    for claw, path in claw_paths.items():
        if path.exists():
            logger.info(f"Directory already exists: {path}")
            continue

        cmd = f"sudo mkdir -p {path} && sudo chown $USER:$USER {path}"
        commands.append(cmd)

        if dry_run:
            logger.info(f"Would create: {path}")
        else:
            import subprocess

            subprocess.run(cmd, shell=True, check=True)
            logger.info(f"Created: {path}")

    return commands


POLICY_DIR = Path(__file__).parent.parent / "policies"


def load_sandbox_policy(claw_role: str) -> dict[str, Any]:
    """
    Load and return the parsed sandbox policy YAML for a given claw role.

    Reads from milimo-blueprint/policies/{role}-sandbox.yaml.
    Maps role names: "ops" → "ops-sandbox.yaml", "clients" → "ops-sandbox.yaml"

    Args:
    claw_role: The claw role name (content, ops, analytics, finance, build, assistant)

    Returns:
    Parsed sandbox policy as dict

    Raises:
    FileNotFoundError: If the policy file doesn't exist
    """
    role_to_file = {
        "content": "content-sandbox.yaml",
        "ops": "ops-sandbox.yaml",
        "clients": "ops-sandbox.yaml",
        "analytics": "analytics-sandbox.yaml",
        "finance": "finance-sandbox.yaml",
        "build": "build-sandbox.yaml",
        "assistant": "assistant-sandbox.yaml",
    }

    filename = role_to_file.get(claw_role, f"{claw_role}-sandbox.yaml")
    policy_path = POLICY_DIR / filename

    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    with policy_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_read_only_mounts(policy: dict[str, Any]) -> list[Path]:
    """
    Extract all read_only mount paths from a parsed sandbox policy dict.

    Args:
        policy: Parsed sandbox policy dict

    Returns:
        List of Path objects for read-only mounts
    """
    fs_policy = policy.get("filesystem_policy", {})
    read_only = fs_policy.get("read_only", [])

    if isinstance(read_only, list):
        return [Path(p) if isinstance(p, str) else Path(str(p)) for p in read_only]
    return []


def get_all_accessible_mounts(policy: dict[str, Any]) -> list[Path]:
    """
    Extract ALL accessible paths (read_only + read_write) from policy.

    Args:
        policy: Parsed sandbox policy dict

    Returns:
        List of Path objects for all accessible mounts
    """
    fs_policy = policy.get("filesystem_policy", {})
    all_mounts: list[Path] = []

    read_only = fs_policy.get("read_only", [])
    if isinstance(read_only, list):
        all_mounts.extend([Path(p) for p in read_only if isinstance(p, str)])

    read_write = fs_policy.get("read_write", [])
    if isinstance(read_write, list):
        all_mounts.extend([Path(p) for p in read_write if isinstance(p, str)])

    return all_mounts
