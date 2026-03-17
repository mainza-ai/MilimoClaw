#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Squad Mesh Coordinator

Manages the squad mesh topology: which claws are online, message routing
between sandboxes via the OpenShell gateway, health monitoring, and
squad formation protocol.

In Phase 0, the mesh runs within a single Docker container where all
claws share the same host. Messages are routed through a local message
bus (file-based queue). In later phases, OpenShell gateway will provide
true inter-sandbox IPC.

Usage:
    from mesh import MeshCoordinator

    mesh = MeshCoordinator.from_config_file("mesh_config.yaml")
    mesh.register_claw("content", address="local://content")
    mesh.register_claw("ops", address="local://ops")
    mesh.send_message(message)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .contracts import ClawMessage, ContractValidator, ValidationResult

logger = logging.getLogger("milimo.mesh")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class ClawNode:
    """A registered claw in the mesh topology."""

    role: str
    address: str
    status: str = "online"  # online, offline, unhealthy, finals-mode
    registered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_heartbeat: str = ""
    consecutive_failures: int = 0


@dataclass
class DeliveryResult:
    """Result of attempting to deliver a message."""

    delivered: bool
    reason: str
    message_id: str = ""
    requires_approval: bool = False


# ---------------------------------------------------------------------------
# Squad Mesh Coordinator
# ---------------------------------------------------------------------------


class MeshCoordinator:
    """
    Coordinates the squad mesh: claw registration, message routing,
    health monitoring, and topology management.
    """

    def __init__(
        self,
        validator: ContractValidator,
        squad_id: str = "",
        mesh_dir: str | None = None,
    ) -> None:
        self._validator = validator
        self._squad_id = squad_id
        self._nodes: dict[str, ClawNode] = {}

        # Message queue directory (file-based for Phase 0)
        if mesh_dir:
            self._mesh_dir = Path(mesh_dir)
        else:
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            self._mesh_dir = Path(home) / ".milimo" / "mesh"
        self._mesh_dir.mkdir(parents=True, exist_ok=True)
        (self._mesh_dir / "inbox").mkdir(exist_ok=True)
        (self._mesh_dir / "outbox").mkdir(exist_ok=True)
        (self._mesh_dir / "delivered").mkdir(exist_ok=True)
        (self._mesh_dir / "rejected").mkdir(exist_ok=True)

    @classmethod
    def from_config_file(
        cls, path: str | Path, squad_id: str = "", mesh_dir: str | None = None
    ) -> MeshCoordinator:
        """Create a mesh coordinator from a mesh config YAML file."""
        validator = ContractValidator.from_config_file(path)
        return cls(validator=validator, squad_id=squad_id, mesh_dir=mesh_dir)

    @classmethod
    def from_dict(
        cls, raw: dict[str, Any], squad_id: str = "", mesh_dir: str | None = None
    ) -> MeshCoordinator:
        """Create from a parsed config dictionary."""
        validator = ContractValidator.from_dict(raw)
        return cls(validator=validator, squad_id=squad_id, mesh_dir=mesh_dir)

    @property
    def squad_id(self) -> str:
        return self._squad_id

    @property
    def topology(self) -> dict[str, ClawNode]:
        """Return the current mesh topology."""
        return dict(self._nodes)

    # ── Registration ──────────────────────────────────────────────────

    def register_claw(self, role: str, address: str) -> bool:
        """Register a claw in the mesh topology."""
        if role in self._nodes:
            logger.warning("Claw '%s' already registered, updating address", role)

        self._nodes[role] = ClawNode(role=role, address=address)

        # Create per-claw inbox directory
        (self._mesh_dir / "inbox" / role).mkdir(exist_ok=True)

        logger.info("Registered claw: %s @ %s", role, address)
        self._save_topology()
        return True

    def unregister_claw(self, role: str) -> bool:
        """Remove a claw from the mesh topology."""
        if role not in self._nodes:
            return False
        del self._nodes[role]
        self._save_topology()
        return True

    def get_online_claws(self) -> list[str]:
        """Return list of claw roles that are currently online."""
        return [
            role
            for role, node in self._nodes.items()
            if node.status == "online"
        ]

    # ── Message Routing ───────────────────────────────────────────────

    def send_message(self, message: ClawMessage) -> DeliveryResult:
        """
        Route a message through the mesh.

        Steps:
        1. Validate the message against contracts
        2. Check recipient is registered and online
        3. Queue the message for delivery
        4. Flag if approval is required
        """
        # 1. Validate contract
        validation: ValidationResult = self._validator.validate(message)
        if not validation.valid:
            self._write_rejected(message, validation.reason)
            return DeliveryResult(
                delivered=False,
                reason=validation.reason,
                message_id=message.message_id,
            )

        # 2. Check recipient status (war_room is always available)
        if message.recipient_role != "war_room":
            recipient = self._nodes.get(message.recipient_role)
            if recipient is None:
                reason = f"Recipient '{message.recipient_role}' not registered in mesh"
                self._write_rejected(message, reason)
                return DeliveryResult(
                    delivered=False,
                    reason=reason,
                    message_id=message.message_id,
                )
            if recipient.status not in ("online", "finals-mode"):
                reason = f"Recipient '{message.recipient_role}' is {recipient.status}"
                self._write_rejected(message, reason)
                return DeliveryResult(
                    delivered=False,
                    reason=reason,
                    message_id=message.message_id,
                )

        # 3. Check if approval is required
        needs_approval = self._validator.requires_approval(message.message_type)

        # 4. Queue for delivery
        self._write_message(message, needs_approval)

        return DeliveryResult(
            delivered=True,
            reason="Message queued for delivery",
            message_id=message.message_id,
            requires_approval=needs_approval,
        )

    def get_pending_messages(self, role: str) -> list[dict[str, Any]]:
        """Get all pending messages for a claw role."""
        inbox = self._mesh_dir / "inbox" / role
        if not inbox.exists():
            return []

        messages: list[dict[str, Any]] = []
        for msg_file in sorted(inbox.glob("*.json")):
            try:
                messages.append(json.loads(msg_file.read_text()))
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read message: %s", msg_file)
        return messages

    # ── Health Monitoring ─────────────────────────────────────────────

    def heartbeat(self, role: str) -> bool:
        """Record a heartbeat from a claw."""
        node = self._nodes.get(role)
        if not node:
            return False
        node.last_heartbeat = datetime.now(timezone.utc).isoformat()
        node.consecutive_failures = 0
        if node.status == "unhealthy":
            node.status = "online"
        self._save_topology()
        return True

    def mark_unhealthy(self, role: str) -> None:
        """Mark a claw as unhealthy after failed health checks."""
        node = self._nodes.get(role)
        if node:
            node.consecutive_failures += 1
            node.status = "unhealthy"
            self._save_topology()

    def set_status(self, role: str, status: str) -> bool:
        """Set a claw's status (online, offline, finals-mode)."""
        node = self._nodes.get(role)
        if not node:
            return False
        node.status = status
        self._save_topology()
        return True

    # ── Internals ─────────────────────────────────────────────────────

    def _write_message(self, message: ClawMessage, needs_approval: bool) -> None:
        """Write a message to the recipient's inbox."""
        msg_data = {
            "message_id": message.message_id,
            "sender_role": message.sender_role,
            "recipient_role": message.recipient_role,
            "message_type": message.message_type,
            "payload": message.payload,
            "squad_id": message.squad_id,
            "timestamp": message.timestamp,
            "needs_approval": needs_approval,
        }

        if message.recipient_role == "war_room":
            target = self._mesh_dir / "inbox" / "war_room"
        else:
            target = self._mesh_dir / "inbox" / message.recipient_role

        target.mkdir(exist_ok=True)
        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        (target / filename).write_text(json.dumps(msg_data, indent=2))

    def _write_rejected(self, message: ClawMessage, reason: str) -> None:
        """Write a rejected message to the rejected queue."""
        msg_data = {
            "message_id": message.message_id,
            "sender_role": message.sender_role,
            "recipient_role": message.recipient_role,
            "message_type": message.message_type,
            "rejection_reason": reason,
            "timestamp": message.timestamp,
        }
        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        (self._mesh_dir / "rejected" / filename).write_text(
            json.dumps(msg_data, indent=2)
        )

    def _save_topology(self) -> None:
        """Persist the current mesh topology to disk."""
        topo = {
            "squad_id": self._squad_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "nodes": {
                role: {
                    "role": node.role,
                    "address": node.address,
                    "status": node.status,
                    "registered_at": node.registered_at,
                    "last_heartbeat": node.last_heartbeat,
                }
                for role, node in self._nodes.items()
            },
        }
        (self._mesh_dir / "topology.json").write_text(json.dumps(topo, indent=2))
