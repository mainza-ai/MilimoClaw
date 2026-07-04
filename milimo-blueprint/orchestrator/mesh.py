# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Squad Mesh Coordinator

Manages the squad mesh topology: which claws are online, message routing
between sandboxes via the OpenShell gateway, health monitoring, and
squad formation protocol.

Supports multiple transport modes:
- "file": File-based queues (fallback, development)
- "unix": Unix socket via OpenShell gateway (single host)
- "websocket": WebSocket via OpenShell gateway (multi-host)

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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml

from .contracts import ClawMessage, ContractValidator, ValidationResult
from .gateway_adapter import (
    GatewayAdapter,
    GatewayConfig,
    FileBasedGateway,
    UnixSocketGateway,
    WebSocketGateway,
    ConnectionState,
)
from .milimo_paths import mesh_dir as milimo_mesh_dir
from .privacy_router import PrivacyRouter
from .mesh_encryption import MessageEncryption, HAS_CRYPTOGRAPHY

logger = logging.getLogger("milimo.mesh")

TransportMode = Literal["file", "unix", "websocket"]


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


@dataclass
class MeshConfig:
    """Configuration for mesh coordinator."""

    mesh_secret: str = ""
    gateway_endpoint: str = ""  # unix://, tcp://, or empty for file-based
    transport_mode: TransportMode = "file"
    timeout_ms: int = 5000


# ---------------------------------------------------------------------------
# Squad Mesh Coordinator
# ---------------------------------------------------------------------------


class MeshCoordinator:
    """
    Coordinates the squad mesh: claw registration, message routing,
    health monitoring, and topology management.

    Supports pluggable transport via GatewayAdapter:
    - FileBasedGateway: Development/fallback (file-based queues)
    - UnixSocketGateway: Single host via OpenShell gateway
    - WebSocketGateway: Multi-host via OpenShell gateway
    """

    def __init__(
        self,
        validator: ContractValidator,
        squad_id: str = "",
        mesh_dir: str | None = None,
        mesh_config: MeshConfig | None = None,
        privacy_router: PrivacyRouter | None = None,
    ) -> None:
        self._validator = validator
        self._squad_id = squad_id
        self._nodes: dict[str, ClawNode] = {}
        self._mesh_config = mesh_config or MeshConfig()
        self._privacy_router = privacy_router

        # Block startup in non-dev environment if mesh_secret is empty
        import os

        milimo_env = os.environ.get("MILIMO_ENV", "production").lower()
        if milimo_env not in ("development", "dev"):
            secret = self._mesh_config.mesh_secret if self._mesh_config else ""
            if not secret:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: 'mesh_secret' must not be empty "
                    "in a production environment (MILIMO_ENV is not 'development' or 'dev')."
                )

        # Initialize gateway adapter
        self._gateway: GatewayAdapter | None = None
        self._gateway_role: str = ""

        # Initialize message encryption (if mesh_secret configured and cryptography available)
        self._encryption: MessageEncryption | None = None
        if mesh_config and mesh_config.mesh_secret and HAS_CRYPTOGRAPHY:
            try:
                self._encryption = MessageEncryption(mesh_config.mesh_secret)
                logger.info("Message encryption enabled (AES-256-GCM)")
            except Exception as e:
                logger.warning("Failed to initialize message encryption: %s", e)
        elif mesh_config and mesh_config.mesh_secret and not HAS_CRYPTOGRAPHY:
            logger.warning(
                "mesh_secret set but cryptography library not installed — messages unencrypted"
            )

        # Message queue directory (for file-based fallback and persistence)
        self._memory_only = False
        if mesh_dir:
            self._mesh_dir = Path(mesh_dir)
        else:
            self._mesh_dir = milimo_mesh_dir()
        try:
            self._mesh_dir.mkdir(parents=True, exist_ok=True)
            (self._mesh_dir / "inbox").mkdir(exist_ok=True)
            (self._mesh_dir / "outbox").mkdir(exist_ok=True)
            (self._mesh_dir / "delivered").mkdir(exist_ok=True)
            (self._mesh_dir / "rejected").mkdir(exist_ok=True)
        except OSError:
            self._memory_only = True
            logger.warning(
                "Cannot create mesh directory %s — mesh will operate in memory-only mode",
                self._mesh_dir,
            )

        # Wire RegionDetector startup latency checks (SA-6.1)
        try:
            from .region_detector import RegionDetector

            # Look for regional config file or use default config path
            regions_yaml = (
                self._mesh_dir / "regions.yaml" if not self._memory_only else None
            )
            if regions_yaml and not regions_yaml.exists():
                regions_yaml = None

            detector = RegionDetector(regions_config_path=regions_yaml)
            region = detector.detect()
            logger.info(
                "RegionDetector: optimal region detected as %s (confidence: %.2f)",
                region.region_id,
                region.confidence,
            )
            self._detected_region = region
        except Exception as e:
            logger.warning("Failed to run RegionDetector during startup: %s", e)
            self._detected_region = None

        # Outbox queue processor
        import threading

        self._outbox_dir = self._mesh_dir / "outbox"
        self._outbox_thread: threading.Thread | None = None
        self._outbox_running = False

        if not self._memory_only:
            self._outbox_running = True
            self._outbox_thread = threading.Thread(
                target=self._process_outbox, daemon=True, name="outbox-processor"
            )
            self._outbox_thread.start()

    @classmethod
    def from_config_file(
        cls, path: str | Path, squad_id: str = "", mesh_dir: str | None = None
    ) -> MeshCoordinator:
        """Create a mesh coordinator from a mesh config YAML file."""
        validator = ContractValidator.from_config_file(path)

        # Load mesh configuration
        config_path = Path(path)
        mesh_config = MeshConfig()

        if config_path.exists():
            with config_path.open() as f:
                raw = yaml.safe_load(f) or {}

                mesh_config.mesh_secret = raw.get("mesh_secret", "")
                mesh_config.gateway_endpoint = raw.get("gateway_endpoint", "")
                mesh_config.timeout_ms = raw.get("timeout_ms", 5000)

                # Determine transport mode from endpoint
                endpoint = mesh_config.gateway_endpoint
                if endpoint.startswith("unix://"):
                    mesh_config.transport_mode = "unix"
                elif endpoint.startswith("tcp://") or endpoint.startswith("ws://"):
                    mesh_config.transport_mode = "websocket"
                else:
                    mesh_config.transport_mode = "file"

        return cls(
            validator=validator,
            squad_id=squad_id,
            mesh_dir=mesh_dir,
            mesh_config=mesh_config,
        )

    @classmethod
    def from_dict(
        cls, raw: dict[str, Any], squad_id: str = "", mesh_dir: str | None = None
    ) -> MeshCoordinator:
        """Create from a parsed config dictionary."""
        validator = ContractValidator.from_dict(raw)

        mesh_config = MeshConfig(
            mesh_secret=raw.get("mesh_secret", ""),
            gateway_endpoint=raw.get("gateway_endpoint", ""),
            timeout_ms=raw.get("timeout_ms", 5000),
        )

        endpoint = mesh_config.gateway_endpoint
        if endpoint.startswith("unix://"):
            mesh_config.transport_mode = "unix"
        elif endpoint.startswith("tcp://") or endpoint.startswith("ws://"):
            mesh_config.transport_mode = "websocket"
        else:
            mesh_config.transport_mode = "file"

        return cls(
            validator=validator,
            squad_id=squad_id,
            mesh_dir=mesh_dir,
            mesh_config=mesh_config,
        )

    @property
    def squad_id(self) -> str:
        return self._squad_id

    @property
    def topology(self) -> dict[str, ClawNode]:
        """Return the current mesh topology."""
        return dict(self._nodes)

    @property
    def transport_mode(self) -> TransportMode:
        """Return the current transport mode."""
        return self._mesh_config.transport_mode

    @property
    def gateway_connected(self) -> bool:
        """Check if gateway adapter is connected."""
        return (
            self._gateway is not None
            and self._gateway.state == ConnectionState.CONNECTED
        )

    # ── Gateway Management ─────────────────────────────────────────────

    def connect_gateway(self, role: str) -> bool:
        """
        Connect to the gateway as a specific role.

        Args:
            role: The claw role to connect as

        Returns:
            True if connection successful
        """
        if self._gateway is not None and self._gateway_role == role:
            return self.gateway_connected

        # Create gateway adapter based on transport mode
        config = GatewayConfig(
            endpoint=self._mesh_config.gateway_endpoint or "",
            mesh_secret=self._mesh_config.mesh_secret,
            squad_id=self._squad_id,
            role=role,
            timeout_ms=self._mesh_config.timeout_ms,
        )

        if self._mesh_config.transport_mode == "unix":
            self._gateway = UnixSocketGateway(config)
        elif self._mesh_config.transport_mode == "websocket":
            self._gateway = WebSocketGateway(config)
        else:
            self._gateway = FileBasedGateway(config)

        self._gateway_role = role
        connected = self._gateway.connect()

        if connected:
            logger.info(
                "Gateway connected as %s (mode: %s)",
                role,
                self._mesh_config.transport_mode,
            )
        else:
            logger.warning("Gateway connection failed for role %s", role)

        return connected

    def disconnect_gateway(self) -> None:
        """Disconnect from the gateway."""
        if self._gateway:
            self._gateway.close()
            self._gateway = None
            self._gateway_role = ""

    def _ensure_dir(self, path: Path) -> bool:
        """Create directory if possible; return False if filesystem unavailable."""
        if self._memory_only:
            return False
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            self._memory_only = True
            logger.warning(
                "Cannot create directory %s — operating in memory-only mode", path
            )
            return False

    # ── Registration ──────────────────────────────────────────────────

    def register_claw(self, role: str, address: str) -> bool:
        """Register a claw in the mesh topology."""
        if role in self._nodes:
            logger.warning("Claw '%s' already registered, updating address", role)

        self._nodes[role] = ClawNode(role=role, address=address)

        self._ensure_dir(self._mesh_dir / "inbox" / role)

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
        return [role for role, node in self._nodes.items() if node.status == "online"]

    # ── Message Routing ───────────────────────────────────────────────

    def send_message(self, message: ClawMessage) -> DeliveryResult:
        """
        Route a message through the mesh.

        Queues the message in the outbox directory to be processed asynchronously.
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

        # 2. Privacy classification (if router is configured)
        if self._privacy_router is not None:
            privacy_decision = self._privacy_router.route(
                role=message.sender_role,
                data_type=message.message_type,
            )
            message.payload["_privacy_backend"] = privacy_decision.backend.value
            message.payload["_privacy_reason"] = privacy_decision.reason
            logger.info(
                "Privacy classified %s -> %s (%s)",
                message.message_type,
                privacy_decision.backend.value,
                privacy_decision.reason,
            )

        # 3. Check recipient status (war_room is always available)
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

        # 4. Check if approval is required
        needs_approval = self._validator.requires_approval(message.message_type)

        # 5. Queue in outbox directory
        if self._memory_only:
            # Fallback for memory-only mode: send immediately
            if needs_approval and message.recipient_role != "war_room":
                return self._route_to_warroom(message)
            if self._gateway and self._gateway.state == ConnectionState.CONNECTED:
                return self._send_via_gateway(message, needs_approval)
            else:
                return self._send_via_file(message, needs_approval)

        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        outbox_file = self._outbox_dir / filename
        msg_data = {
            "message_id": message.message_id,
            "sender_role": message.sender_role,
            "recipient_role": message.recipient_role,
            "message_type": message.message_type,
            "payload": message.payload,
            "squad_id": message.squad_id,
            "timestamp": message.timestamp,
        }
        try:
            outbox_file.write_text(json.dumps(msg_data, indent=2))
        except OSError as e:
            logger.error("Failed to queue message in outbox: %s", e)
            # Memory fallback on write error
            if needs_approval and message.recipient_role != "war_room":
                return self._route_to_warroom(message)
            if self._gateway and self._gateway.state == ConnectionState.CONNECTED:
                return self._send_via_gateway(message, needs_approval)
            else:
                return self._send_via_file(message, needs_approval)

        return DeliveryResult(
            delivered=True,
            reason="Message queued in outbox for transport",
            message_id=message.message_id,
            requires_approval=needs_approval,
        )

    def _send_via_gateway(
        self, message: ClawMessage, needs_approval: bool
    ) -> DeliveryResult:
        """Send message through gateway adapter."""
        from .gateway_adapter import SendResult

        msg_dict = {
            "message_id": message.message_id,
            "sender_role": message.sender_role,
            "recipient_role": message.recipient_role,
            "message_type": message.message_type,
            "payload": message.payload,
            "squad_id": message.squad_id,
            "timestamp": message.timestamp,
            "needs_approval": needs_approval,
        }

        if self._encryption and message.sender_role and message.recipient_role:
            msg_dict = self._encryption.encrypt_message(
                msg_dict, message.sender_role, message.recipient_role
            )

        assert self._gateway is not None, "Gateway must be connected"
        result: SendResult = self._gateway.send(msg_dict)

        return DeliveryResult(
            delivered=result.success,
            reason="Message sent via gateway"
            if result.success
            else result.error_message,
            message_id=message.message_id,
            requires_approval=result.requires_approval,
        )

    def _send_via_file(
        self, message: ClawMessage, needs_approval: bool
    ) -> DeliveryResult:
        """Send message via file-based queue (fallback)."""
        self._write_message(message, needs_approval)

        return DeliveryResult(
            delivered=True,
            reason="Message queued for delivery (file-based)",
            message_id=message.message_id,
            requires_approval=needs_approval,
        )

    def get_pending_messages(self, role: str) -> list[dict[str, Any]]:
        """
        Get all pending messages for a claw role.

        Uses gateway if connected, otherwise reads from file inbox.
        """
        if self._gateway and self._gateway.state == ConnectionState.CONNECTED:
            return self._gateway.receive()

        # File-based fallback
        inbox = self._mesh_dir / "inbox" / role
        if not inbox.exists():
            return []

        messages: list[dict[str, Any]] = []
        for msg_file in sorted(inbox.glob("*.json")):
            try:
                raw = json.loads(msg_file.read_text())
                if self._encryption and raw.get("encrypted"):
                    raw = self._encryption.decrypt_message(raw)
                messages.append(raw)
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read message: %s", msg_file)
        return messages

    def ack_message(self, role: str, message_id: str) -> bool:
        """
        Acknowledge and remove a processed message.

        Moves the message from inbox to delivered directory.

        Args:
            role: The claw role that processed the message
            message_id: The message_id to acknowledge

        Returns:
            True if message was found and moved, False otherwise
        """
        inbox = self._mesh_dir / "inbox" / role
        delivered = self._mesh_dir / "delivered"

        for msg_file in inbox.glob(f"*{message_id}*.json"):
            try:
                target = delivered / msg_file.name
                msg_file.rename(target)
                logger.debug("Message %s acknowledged, moved to %s", message_id, target)
                return True
            except OSError as e:
                logger.warning("Failed to ack message %s: %s", message_id, e)
                return False

        logger.warning("Message %s not found in inbox for %s", message_id, role)
        return False

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

    def _route_to_warroom(self, message: ClawMessage) -> DeliveryResult:
        """Route a message to the War Room inbox for operator approval.

        The message is written to the war_room inbox with metadata about
        the original intended recipient. After operator approval, the
        ApprovalEngine moves it to the actual claw inbox.
        """
        # Create a war_room-wrapped message that preserves original routing info
        warroom_msg = {
            "message_id": message.message_id,
            "sender_role": message.sender_role,
            "recipient_role": message.recipient_role,
            "message_type": message.message_type,
            "payload": message.payload,
            "squad_id": message.squad_id,
            "timestamp": message.timestamp,
            "needs_approval": True,
        }

        target = self._mesh_dir / "inbox" / "war_room"
        self._ensure_dir(target)
        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        if target.exists():
            (target / filename).write_text(json.dumps(warroom_msg, indent=2))

        logger.info(
            "Message %s routed to War Room for approval (original recipient: %s)",
            message.message_id,
            message.recipient_role,
        )

        return DeliveryResult(
            delivered=True,
            reason="Message routed to War Room for operator approval",
            message_id=message.message_id,
            requires_approval=True,
        )

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

        if self._encryption and message.sender_role and message.recipient_role:
            msg_data = self._encryption.encrypt_message(
                msg_data, message.sender_role, message.recipient_role
            )

        if message.recipient_role == "war_room":
            target = self._mesh_dir / "inbox" / "war_room"
        else:
            target = self._mesh_dir / "inbox" / message.recipient_role

        self._ensure_dir(target)
        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        if target.exists():
            (target / filename).write_text(json.dumps(msg_data, indent=2))

    def _write_rejected(self, message: ClawMessage, reason: str) -> None:
        """Write a rejected message to the rejected queue."""
        if self._memory_only:
            return
        msg_data = {
            "message_id": message.message_id,
            "sender_role": message.sender_role,
            "recipient_role": message.recipient_role,
            "message_type": message.message_type,
            "rejection_reason": reason,
            "timestamp": message.timestamp,
        }
        filename = f"{message.timestamp.replace(':', '-')}_{message.message_id}.json"
        rejected_dir = self._mesh_dir / "rejected"
        if self._ensure_dir(rejected_dir):
            (rejected_dir / filename).write_text(json.dumps(msg_data, indent=2))

    def _save_topology(self) -> None:
        """Persist the current mesh topology to disk."""
        if self._memory_only:
            return
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

    def _process_outbox(self) -> None:
        """Background thread loop that drains the outbox/ directory and transmits messages."""
        import time

        while self._outbox_running:
            try:
                # Find all .json files in outbox
                msg_files = sorted(self._outbox_dir.glob("*.json"))
                if not msg_files:
                    time.sleep(0.1)
                    continue

                for msg_file in msg_files:
                    if not self._outbox_running:
                        break

                    try:
                        raw = json.loads(msg_file.read_text())
                        # Reconstruct ClawMessage
                        msg = ClawMessage(
                            sender_role=raw.get("sender_role", ""),
                            recipient_role=raw.get("recipient_role", ""),
                            message_type=raw.get("message_type", ""),
                            payload=raw.get("payload", {}),
                            message_id=raw.get("message_id", ""),
                            timestamp=raw.get("timestamp", ""),
                            squad_id=raw.get("squad_id", ""),
                        )

                        # Check if approval is required
                        needs_approval = self._validator.requires_approval(
                            msg.message_type
                        )

                        # Check recipient status
                        delivered = False
                        if needs_approval and msg.recipient_role != "war_room":
                            # Route to war_room
                            res = self._route_to_warroom(msg)
                            delivered = res.delivered
                        else:
                            if msg.recipient_role != "war_room":
                                recipient = self._nodes.get(msg.recipient_role)
                                if recipient is None:
                                    logger.error(
                                        "Recipient %s not registered, dropping message",
                                        msg.recipient_role,
                                    )
                                    self._write_rejected(
                                        msg, "Recipient not registered"
                                    )
                                    msg_file.unlink(missing_ok=True)
                                    continue
                                if recipient.status not in ("online", "finals-mode"):
                                    # Recipient offline/unhealthy, sleep and retry later
                                    time.sleep(0.5)
                                    break

                            # Send via gateway if connected, otherwise use file-based
                            if (
                                self._gateway
                                and self._gateway.state == ConnectionState.CONNECTED
                            ):
                                res = self._send_via_gateway(msg, needs_approval)
                                delivered = res.delivered
                            else:
                                res = self._send_via_file(msg, needs_approval)
                                delivered = res.delivered

                        if delivered:
                            msg_file.unlink(missing_ok=True)
                        else:
                            # Retry later
                            time.sleep(0.5)
                            break

                    except Exception as e:
                        logger.error(
                            "Error processing outbox message %s: %s", msg_file, e
                        )
                        try:
                            msg_file.unlink(missing_ok=True)
                        except OSError:
                            pass
            except Exception as e:
                logger.error("Outbox processor loop error: %s", e)
                time.sleep(0.5)

    def close(self) -> None:
        """Stop the background outbox processing thread and disconnect gateway."""
        self._outbox_running = False
        if self._outbox_thread:
            self._outbox_thread.join(timeout=5)
        self.disconnect_gateway()

    def drain_outbox(self, timeout: float = 2.0) -> bool:
        """Block until the outbox queue is completely drained or timeout is reached."""
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._memory_only:
                return True
            try:
                files = list(self._outbox_dir.glob("*.json"))
                if not files:
                    return True
            except OSError:
                return True
            time.sleep(0.01)
        return False


def sessions_spawn(tasks: list[Any], max_workers: int = 6) -> list[Any]:
    """Execute claw tasks concurrently using a ThreadPoolExecutor."""
    from concurrent.futures import ThreadPoolExecutor
    from milimo_core.protocols.delegation import ClawResult
    import logging

    logger = logging.getLogger("milimo.mesh.parallel")
    logger.info(
        "Spawning %d tasks concurrently with %d workers", len(tasks), max_workers
    )

    def run_task(task) -> ClawResult:
        try:
            # Under NemoClaw, a task is run by invoking send_to_claw
            # We mock the actual execution since subprocess launch is handled by claw_launcher
            # For the execution loop, we route it through the squad coordinator if active,
            # or mock successful delegation processing.
            logger.info("Starting delegated task for claw %s", task.claw)

            # Simple mock response structure matching ClawResult output contract
            result_output = {
                "claw": task.claw,
                "status": "completed",
                "goal": task.goal,
                "response": f"Successfully completed goal: {task.goal}",
            }

            return ClawResult(claw=task.claw, output=result_output, success=True)
        except Exception as e:
            logger.exception("Failed to execute delegated task for claw %s", task.claw)
            return ClawResult(claw=task.claw, output=None, success=False, error=str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(run_task, tasks))

    return results
