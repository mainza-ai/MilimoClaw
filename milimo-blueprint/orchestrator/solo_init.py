#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Founder Template Loader

Loads and validates the solo-founder.yaml template configuration.
Handles filesystem mount automation based on available permissions.
"""

from __future__ import annotations

import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("milimo.solo_init")


# ---------------------------------------------------------------------------

class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


class MissingFieldError(TemplateValidationError):
    """Raised when a required field is missing."""
    pass


class InvalidFieldTypeError(TemplateValidationError):
    """Raised when a field has an invalid type."""
    pass


# ---------------------------------------------------------------------------

@dataclass
class FilesystemConfig:
    """Resolved filesystem configuration for a squad."""

    sandbox_base: Path
    claw_paths: dict[str, Path]
    using_system_sandbox: bool
    reason: str


# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "template": ["name", "display_name", "category", "description", "squad_size", "claws_active"],
    "operator_policy": ["squad_lead", "approval_modes"],
    "filesystem": ["content", "ops", "analytics", "finance", "build"],
    "inference": ["routing_overrides", "cost_guard"],
    "war_room": ["operator", "mode", "queue_priority", "digest_schedule"],
    "evolution": ["cycle", "day", "time", "per_claw"],
    "network_egress": ["content", "ops", "analytics", "finance", "build"],
    "deep_work_mode": ["alias", "on_activate", "auto_response_template"],
}

CLAWS = ["content", "ops", "analytics", "finance", "build"]

LOCKED_ROUTES = ["financial_data", "source_code"]

SYSTEM_SANDBOX_BASE = Path("/sandbox")
USER_SANDBOX_BASE = Path.home() / ".milimo" / "sandboxes"


# ---------------------------------------------------------------------------
# Filesystem Mount Automation
# ---------------------------------------------------------------------------


def detect_filesystem_config(
    squad_id: str,
    config: dict[str, Any] | None = None,
    claws_to_init: list[str] | None = None,
) -> FilesystemConfig:
    """
    Auto-detect and configure sandbox filesystem paths.

    If running with sufficient permissions: uses /sandbox/{role}
    If not: creates under ~/.milimo/sandboxes/{role}/

    Args:
        squad_id: Squad identifier
        config: Optional template config (for custom paths)
        claws_to_init: Optional list of claws to create paths for.
                       If not provided, uses all CLAWS.

    Returns:
        FilesystemConfig with resolved paths and reason
    """
    # Determine which claws to create paths for
    target_claws = claws_to_init if claws_to_init is not None else CLAWS

    # Check if we can use system sandbox
    can_use_system = _can_write_to_system_sandbox()

    if can_use_system:
        sandbox_base = SYSTEM_SANDBOX_BASE
        using_system = True
        reason = "Sufficient permissions for /sandbox"
    else:
        sandbox_base = USER_SANDBOX_BASE / squad_id
        using_system = False
        reason = f"Insufficient permissions for /sandbox, using {sandbox_base}"

    # Build claw paths only for requested claws
    claw_paths: dict[str, Path] = {}
    for claw in target_claws:
        if using_system:
            claw_paths[claw] = sandbox_base / claw
        else:
            claw_paths[claw] = sandbox_base / claw

    return FilesystemConfig(
        sandbox_base=sandbox_base,
        claw_paths=claw_paths,
        using_system_sandbox=using_system,
        reason=reason,
    )


def _can_write_to_system_sandbox() -> bool:
    """
    Check if we have permission to write to /sandbox.

    Returns:
        True if we can create directories in /sandbox
    """
    # Check if /sandbox exists and is writable
    if SYSTEM_SANDBOX_BASE.exists():
        return _is_writable(SYSTEM_SANDBOX_BASE)

    # Check if we can create /sandbox (requires root)
    try:
        # Check parent directory permissions
        parent = SYSTEM_SANDBOX_BASE.parent
        if parent.exists():
            return _is_writable(parent)
    except (OSError, PermissionError):
        pass

    return False


def _is_writable(path: Path) -> bool:
    """Check if a path is writable."""
    try:
        # Check write permission
        if os.access(path, os.W_OK):
            return True
    except (OSError, PermissionError):
        pass
    return False


def setup_sandbox_directories(fs_config: FilesystemConfig) -> dict[str, Path]:
    """
    Create sandbox directories for all claws.

    Args:
        fs_config: FilesystemConfig from detect_filesystem_config()

    Returns:
        Dictionary of created paths

    Raises:
        PermissionError: If directories cannot be created
    """
    created: dict[str, Path] = {}

    for claw, path in fs_config.claw_paths.items():
        try:
            path.mkdir(parents=True, exist_ok=True)

            # Create standard subdirectories
            (path / "tools").mkdir(exist_ok=True)
            (path / "data").mkdir(exist_ok=True)
            (path / "logs").mkdir(exist_ok=True)

            created[claw] = path
            logger.info("Created sandbox directory: %s", path)

        except PermissionError as e:
            logger.error("Failed to create sandbox directory %s: %s", path, e)
            raise

    return created


def get_effective_paths(
    squad_id: str,
    config: dict[str, Any] | None = None,
    claws_to_init: list[str] | None = None,
) -> dict[str, Path]:
    """
    Get effective filesystem paths for all claws.

    This is the main entry point for path resolution:
    1. Check for custom paths in config
    2. Fall back to auto-detected paths
    3. Create directories if needed

    Args:
        squad_id: Squad identifier
        config: Optional template config
        claws_to_init: Optional list of claws to initialize.
                       If not provided, uses all CLAWS.

    Returns:
        Dictionary mapping claw names to their paths
    """
    # Determine which claws to initialize
    target_claws = claws_to_init if claws_to_init is not None else CLAWS

    # Check if config has custom paths
    if config and "filesystem" in config:
        custom_paths = _extract_custom_paths(config, target_claws)
        if custom_paths:
            logger.info("Using custom filesystem paths from config")
            return custom_paths

    # Auto-detect paths
    fs_config = detect_filesystem_config(squad_id, config, target_claws)

    # Setup directories
    setup_sandbox_directories(fs_config)

    # Print summary
    _print_path_summary(fs_config)

    return fs_config.claw_paths


def _extract_custom_paths(
    config: dict[str, Any],
    target_claws: list[str] | None = None,
) -> dict[str, Path] | None:
    """Extract custom paths from config if they exist and are accessible."""
    filesystem = config.get("filesystem", {})
    paths: dict[str, Path] = {}
    claws_to_check = target_claws if target_claws is not None else CLAWS

    for claw in claws_to_check:
        if claw in filesystem:
            path = Path(filesystem[claw])
            # Check if path is accessible
            if path.exists() or _can_create_path(path):
                paths[claw] = path
            else:
                logger.warning(
                    "Custom path %s for %s not accessible, using auto-detection",
                    path,
                    claw,
                )
                return None

    return paths if paths else None


def _can_create_path(path: Path) -> bool:
    """Check if we can create a path."""
    try:
        # Check if parent is writable
        parent = path.parent
        while not parent.exists():
            parent = parent.parent
        return _is_writable(parent)
    except (OSError, PermissionError):
        return False


def _print_path_summary(fs_config: FilesystemConfig) -> None:
    """Print a summary of filesystem configuration."""
    print("\n" + "=" * 60)
    print("FILESYSTEM CONFIGURATION")
    print("=" * 60)
    print()
    print(f"  Sandbox base: {fs_config.sandbox_base}")
    print(f"  Mode: {'System' if fs_config.using_system_sandbox else 'User'} sandbox")
    print(f"  Reason: {fs_config.reason}")
    print()
    print("  Claw paths:")
    for claw, path in fs_config.claw_paths.items():
        print(f"    {claw.upper().ljust(10)} {path}")
    print()
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------

def load_solo_founder_template(path: str) -> dict[str, Any]:
    """
    Load and validate a solo-founder.yaml template.

    Args:
        path: Path to the solo-founder.yaml file

    Returns:
        Parsed and validated configuration dictionary

    Raises:
        FileNotFoundError: If the file does not exist
        TemplateValidationError: If validation fails
        MissingFieldError: If a required field is missing
        InvalidFieldTypeError: If a field has an invalid type
    """
    template_path = Path(path)

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    if not template_path.is_file():
        raise TemplateValidationError(f"Path is not a file: {path}")

    try:
        with template_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise TemplateValidationError(f"Invalid YAML in template: {e}")

    if config is None:
        raise TemplateValidationError("Empty template file")

    _validate_required_fields(config)
    _validate_field_types(config)
    _validate_locked_routes(config)

    logger.info(f"Successfully loaded template: {config.get('template', {}).get('name', 'unknown')}")

    return config


def _validate_required_fields(config: dict[str, Any]) -> None:
    """
    Validate that all required fields are present.

    Args:
        config: Parsed configuration dictionary

    Raises:
        MissingFieldError: If a required field is missing
    """
    missing: list[str] = []

    for section, fields in REQUIRED_FIELDS.items():
        if section not in config:
            missing.append(section)
            continue

        section_data = config[section]
        if not isinstance(section_data, dict):
            missing.append(f"{section} (not a dict)")
            continue

        for field in fields:
            if field not in section_data:
                missing.append(f"{section}.{field}")

    # Check that all claws are defined in filesystem
    for claw in CLAWS:
        if "filesystem" in config and claw not in config.get("filesystem", {}):
            missing.append(f"filesystem.{claw}")

    # Check that all claws have network egress config
    for claw in CLAWS:
        if "network_egress" in config and claw not in config.get("network_egress", {}):
            missing.append(f"network_egress.{claw}")

    # Check that all claws have evolution config
    for claw in CLAWS:
        if "evolution" in config and "per_claw" in config["evolution"]:
            if claw not in config["evolution"]["per_claw"]:
                missing.append(f"evolution.per_claw.{claw}")

    # Check approval modes for all claws
    if "operator_policy" in config and "approval_modes" in config["operator_policy"]:
        for claw in CLAWS:
            if claw not in config["operator_policy"]["approval_modes"]:
                missing.append(f"operator_policy.approval_modes.{claw}")

    if missing:
        raise MissingFieldError(f"Missing required fields: {', '.join(missing)}")


def _validate_field_types(config: dict[str, Any]) -> None:
    """
    Validate that fields have correct types.

    Args:
        config: Parsed configuration dictionary

    Raises:
        InvalidFieldTypeError: If a field has an invalid type
    """
    errors: list[str] = []

    # template section
    template = config.get("template", {})
    if not isinstance(template.get("name"), str):
        errors.append("template.name must be a string")
    if not isinstance(template.get("display_name"), str):
        errors.append("template.display_name must be a string")
    if not isinstance(template.get("category"), str):
        errors.append("template.category must be a string")
    if not isinstance(template.get("description"), str):
        errors.append("template.description must be a string")
    if not isinstance(template.get("squad_size"), int):
        errors.append("template.squad_size must be an integer")
    if not isinstance(template.get("claws_active"), list):
        errors.append("template.claws_active must be a list")

    # Validate claws_active contains valid claw names
    claws_active = template.get("claws_active", [])
    for claw in claws_active:
        if claw not in CLAWS:
            errors.append(f"template.claws_active contains invalid claw: {claw}")

    # filesystem section - all paths must be strings
    filesystem = config.get("filesystem", {})
    for claw in CLAWS:
        if claw in filesystem:
            if not isinstance(filesystem[claw], str):
                errors.append(f"filesystem.{claw} must be a string")

    # inference section
    inference = config.get("inference", {})
    if "routing_overrides" in inference:
        if not isinstance(inference["routing_overrides"], dict):
            errors.append("inference.routing_overrides must be a dict")
    if "cost_guard" in inference:
        cost_guard = inference["cost_guard"]
        if not isinstance(cost_guard, dict):
            errors.append("inference.cost_guard must be a dict")
        else:
            if not isinstance(cost_guard.get("daily_cloud_token_budget"), int):
                errors.append("inference.cost_guard.daily_cloud_token_budget must be an int")
            if not isinstance(cost_guard.get("alert_at_percent"), (int, float)):
                errors.append("inference.cost_guard.alert_at_percent must be a number")
            if not isinstance(cost_guard.get("fallback_on_exceed"), str):
                errors.append("inference.cost_guard.fallback_on_exceed must be a string")

    # war_room section
    war_room = config.get("war_room", {})
    if not isinstance(war_room.get("operator"), str):
        errors.append("war_room.operator must be a string")
    if not isinstance(war_room.get("mode"), str):
        errors.append("war_room.mode must be a string")
    if not isinstance(war_room.get("queue_priority"), dict):
        errors.append("war_room.queue_priority must be a dict")

    # evolution section
    evolution = config.get("evolution", {})
    if not isinstance(evolution.get("cycle"), str):
        errors.append("evolution.cycle must be a string")
    if not isinstance(evolution.get("day"), str):
        errors.append("evolution.day must be a string")
    if not isinstance(evolution.get("time"), str):
        errors.append("evolution.time must be a string")

    # deep_work_mode section
    deep_work = config.get("deep_work_mode", {})
    if not isinstance(deep_work.get("alias"), str):
        errors.append("deep_work_mode.alias must be a string")
    if not isinstance(deep_work.get("on_activate"), dict):
        errors.append("deep_work_mode.on_activate must be a dict")
    if not isinstance(deep_work.get("auto_response_template"), str):
        errors.append("deep_work_mode.auto_response_template must be a string")

    if errors:
        raise InvalidFieldTypeError("; ".join(errors))


def _validate_locked_routes(config: dict[str, Any]) -> None:
    """
    Validate that locked routes are set to 'local'.

    In Docker testing mode, locked routes can be set to 'cloud' for testing.

    Args:
        config: Parsed configuration dictionary

    Raises:
        TemplateValidationError: If locked routes are not properly configured
    """
    inference_config = config.get("inference", {})
    docker_testing = inference_config.get("docker_testing", False)
    routing_overrides = inference_config.get("routing_overrides", {})

    for route in LOCKED_ROUTES:
        if route in routing_overrides:
            route_value = routing_overrides[route]
            if docker_testing and route_value == "cloud":
                continue
            if route_value != "local":
                raise TemplateValidationError(
                    f"Locked route '{route}' must be 'local', got '{route_value}'. "
                    f"Set 'docker_testing: true' in inference config to allow cloud for testing."
                )


def get_claw_paths(config: dict[str, Any]) -> dict[str, Path]:
    """
    Extract filesystem paths for each claw from config.

    Args:
        config: Validated configuration dictionary

    Returns:
        Dictionary mapping claw names to Path objects
    """
    filesystem = config.get("filesystem", {})
    paths: dict[str, Path] = {}

    for claw in CLAWS:
        if claw in filesystem:
            paths[claw] = Path(filesystem[claw])

    return paths


def get_claws_to_initialize(config: dict[str, Any]) -> list[str]:
    """
    Returns the list of claw roles whose sandboxes should be initialized.

    Solo mode (clawRole == "solo"):
        Returns all active claws from the template.
        All five sandboxes are created on this machine.

    Mesh mode (clawRole is a specific claw name):
        Returns only the one claw this operator runs.
        Other sandboxes are on other machines.

    Args:
        config: Configuration dictionary with clawRole and activeClaws keys

    Returns:
        List of claw role names to initialize

    Raises:
        ValueError: If clawRole is not in activeClaws (mesh mode mismatch)
    """
    claw_role: str = config.get("clawRole", "solo")
    active_claws: list[str] = config.get(
        "activeClaws", ["content", "ops", "analytics", "finance", "build"]
    )

    if claw_role == "solo":
        return active_claws
    else:
        # Mesh mode — verify the role is actually in the active claws list
        if claw_role not in active_claws:
            raise ValueError(
                f"clawRole '{claw_role}' is not in activeClaws {active_claws}. "
                f"Check config.json."
            )
        return [claw_role]


def get_claw_network_policy(config: dict[str, Any], claw: str) -> dict[str, Any]:
    """
    Extract network egress policy for a specific claw.

    Args:
        config: Validated configuration dictionary
        claw: Claw name

    Returns:
        Network policy dictionary for the claw
    """
    if claw not in CLAWS:
        raise ValueError(f"Invalid claw: {claw}")

    network_egress = config.get("network_egress", {})
    return network_egress.get(claw, {"approved": []})


def get_approval_modes(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """
    Extract approval modes for all claws.

    Args:
        config: Validated configuration dictionary

    Returns:
        Dictionary mapping claw names to their approval modes
    """
    return config.get("operator_policy", {}).get("approval_modes", {})


def get_evolution_config(config: dict[str, Any], claw: str) -> dict[str, Any]:
    """
    Extract evolution configuration for a specific claw.

    Args:
        config: Validated configuration dictionary
        claw: Claw name

    Returns:
        Evolution configuration for the claw
    """
    if claw not in CLAWS:
        raise ValueError(f"Invalid claw: {claw}")

    return config.get("evolution", {}).get("per_claw", {}).get(claw, {})
