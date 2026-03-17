#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Inter-Claw Message Contracts

Typed message contract definitions for squad mesh communication.
Each message is validated against the sender's outbound policy and
the recipient's inbound policy before delivery. Invalid messages
are dropped and logged.

Usage:
    from contracts import ContractValidator, ClawMessage

    validator = ContractValidator.from_config_file("mesh_config.yaml")
    msg = ClawMessage(
        sender_role="ops",
        recipient_role="content",
        message_type="brief",
        payload={"project_id": "abc", "scope": "Social campaign"},
        squad_id="my-squad",
    )
    result = validator.validate(msg)
    # result.valid == True
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("milimo.contracts")

# Valid claw roles
VALID_ROLES = {"content", "ops", "analytics", "finance", "build"}
# War room is a valid recipient but not a sender role
VALID_RECIPIENTS = VALID_ROLES | {"war_room"}

# Valid message types
VALID_MESSAGE_TYPES = {"brief", "query", "response", "signal", "deliverable", "summary"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ClawMessage:
    """A typed message between claws in the squad mesh."""

    sender_role: str
    recipient_role: str
    message_type: str
    payload: dict[str, Any]
    squad_id: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class ValidationResult:
    """Result of a message contract validation."""

    valid: bool
    reason: str
    message_id: str = ""


@dataclass(frozen=True)
class MessageTypeConfig:
    """Configuration for a message type from mesh_config."""

    description: str
    requires_approval: bool = False


# ---------------------------------------------------------------------------
# Contract Validator
# ---------------------------------------------------------------------------


class ContractValidator:
    """
    Validates inter-claw messages against the squad's mesh configuration.

    Checks:
    1. Sender and recipient roles are valid
    2. Message type is valid
    3. The sender→recipient→message_type route is allowed by the matrix
    """

    def __init__(
        self,
        message_matrix: dict[str, dict[str, list[str]]],
        message_types: dict[str, MessageTypeConfig],
    ) -> None:
        self._matrix = message_matrix
        self._types = message_types

    @classmethod
    def from_config_file(cls, path: str | Path) -> ContractValidator:
        """Load a contract validator from a mesh config YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Mesh config not found: {config_path}")

        with config_path.open() as f:
            raw: dict[str, Any] = yaml.safe_load(f)

        return cls._from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ContractValidator:
        """Create a contract validator from a parsed config dictionary."""
        return cls._from_dict(raw)

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> ContractValidator:
        matrix = raw.get("message_matrix", {})

        types_raw = raw.get("message_types", {})
        types: dict[str, MessageTypeConfig] = {}
        for name, config in types_raw.items():
            types[name] = MessageTypeConfig(
                description=config.get("description", ""),
                requires_approval=config.get("requires_approval", False),
            )

        return cls(message_matrix=matrix, message_types=types)

    def validate(self, message: ClawMessage) -> ValidationResult:
        """
        Validate a message against the contract rules.

        Returns ValidationResult with valid=True if the message passes
        all checks, or valid=False with a reason explaining the rejection.
        """
        # 1. Validate sender role
        if message.sender_role not in VALID_ROLES:
            return ValidationResult(
                valid=False,
                reason=f"Invalid sender role: '{message.sender_role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}",
                message_id=message.message_id,
            )

        # 2. Validate recipient role
        if message.recipient_role not in VALID_RECIPIENTS:
            return ValidationResult(
                valid=False,
                reason=f"Invalid recipient role: '{message.recipient_role}'. Must be one of: {', '.join(sorted(VALID_RECIPIENTS))}",
                message_id=message.message_id,
            )

        # 3. Validate message type
        if message.message_type not in VALID_MESSAGE_TYPES:
            return ValidationResult(
                valid=False,
                reason=f"Invalid message type: '{message.message_type}'. Must be one of: {', '.join(sorted(VALID_MESSAGE_TYPES))}",
                message_id=message.message_id,
            )

        # 4. Check message matrix authorization
        sender_routes = self._matrix.get(message.sender_role, {})
        allowed_types = sender_routes.get(message.recipient_role, [])

        if message.message_type not in allowed_types:
            return ValidationResult(
                valid=False,
                reason=(
                    f"Unauthorized: {message.sender_role} cannot send "
                    f"'{message.message_type}' to {message.recipient_role}. "
                    f"Allowed types: {allowed_types or 'none'}"
                ),
                message_id=message.message_id,
            )

        return ValidationResult(
            valid=True,
            reason="Message passes all contract checks",
            message_id=message.message_id,
        )

    def requires_approval(self, message_type: str) -> bool:
        """Check if a message type requires War Room approval."""
        type_config = self._types.get(message_type)
        return type_config.requires_approval if type_config else False

    def get_allowed_types(self, sender: str, recipient: str) -> list[str]:
        """Get the list of message types allowed from sender to recipient."""
        return self._matrix.get(sender, {}).get(recipient, [])

    def get_all_senders_for(self, recipient: str) -> dict[str, list[str]]:
        """Get all roles that can send messages to a given recipient."""
        result: dict[str, list[str]] = {}
        for sender, routes in self._matrix.items():
            types = routes.get(recipient, [])
            if types:
                result[sender] = types
        return result
