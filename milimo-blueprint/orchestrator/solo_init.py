#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Solo Founder Template Loader

Loads and validates the solo-founder.yaml template configuration.
"""

from __future__ import annotations

import logging
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

    Args:
        config: Parsed configuration dictionary

    Raises:
        TemplateValidationError: If locked routes are not properly configured
    """
    routing_overrides = config.get("inference", {}).get("routing_overrides", {})

    for route in LOCKED_ROUTES:
        if route in routing_overrides:
            if routing_overrides[route] != "local":
                raise TemplateValidationError(
                    f"Locked route '{route}' must be 'local', got '{routing_overrides[route]}'"
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
