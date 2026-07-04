# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Gateway Adapter

Abstracts inter-sandbox communication through a unified interface.
Supports multiple transport strategies:
- Unix socket (single host)
- WebSocket (multi-host)
- File-based (fallback when gateway unavailable)

Usage:
    from gateway_adapter import GatewayAdapter, UnixSocketGateway

    config = GatewayConfig(
        endpoint="unix:///var/run/openshell/gateway.sock",
        mesh_secret="squad-secret",
        squad_id="my-squad",
        role="content",
    )
    gateway = UnixSocketGateway(config)
    gateway.connect()
    gateway.send(message)
"""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from .milimo_paths import mesh_dir
from typing import Any, Callable, Optional

logger = logging.getLogger("milimo.gateway_adapter")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ConnectionState(str, Enum):
    """Gateway connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class GatewayConfig:
    """Configuration for gateway connection."""

    endpoint: str  # unix:///path, tcp://host:port, or file://
    mesh_secret: str
    squad_id: str
    role: str
    timeout_ms: int = 5000
    reconnect_attempts: int = 3
    reconnect_delay_ms: int = 1000
    validator: Any = None


@dataclass
class SendResult:
    """Result of sending a message through the gateway."""

    success: bool
    message_id: str = ""
    requires_approval: bool = False
    error_code: str = ""
    error_message: str = ""


@dataclass
class GatewayMessage:
    """Message envelope for gateway communication."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: str = ""


@dataclass
class GatewayResponse:
    """Response from gateway."""

    status: str
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Base Adapter
# ---------------------------------------------------------------------------


class GatewayAdapter(ABC):
    """
    Abstract base class for gateway adapters.

    Implementations must provide:
    - connect(): Establish connection to gateway
    - send(): Send message to recipient
    - receive(): Poll for pending messages
    - close(): Clean up connection
    """

    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self._last_message_time: Optional[datetime] = None
        self._error_count = 0

    def _validate_message(self, message: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate outbound/inbound message against contracts.py rules."""
        try:
            from orchestrator.contracts import ContractValidator, ClawMessage

            validator = getattr(self.config, "validator", None)
            if not validator:
                config_paths = [
                    Path(__file__).parent.parent / "mesh_config.yaml",
                    Path("/sandbox/.openclaw/milimo/milimo-blueprint/mesh_config.yaml"),
                    Path.home() / ".openclaw/milimo/milimo-blueprint/mesh_config.yaml",
                    Path("./milimo-blueprint/mesh_config.yaml"),
                ]
                config_path = next((p for p in config_paths if p.exists()), None)
                if config_path:
                    validator = ContractValidator.from_config_file(config_path)
                else:
                    sender = message.get("sender_role", self.config.role)
                    recipient = message.get("recipient_role", "unknown")
                    msg_type = message.get("message_type", "unknown")
                    basic_raw = {
                        "message_matrix": {sender: {recipient: [msg_type]}},
                        "message_types": {},
                    }
                    validator = ContractValidator.from_dict(basic_raw)

            claw_msg = ClawMessage(
                sender_role=message.get("sender_role", self.config.role),
                recipient_role=message.get("recipient_role", "unknown"),
                message_type=message.get("message_type", "unknown"),
                payload=message.get("payload", {}),
                message_id=message.get("message_id", ""),
                timestamp=message.get("timestamp", ""),
                squad_id=getattr(self.config, "squad_id", ""),
            )
            result = validator.validate(claw_msg)
            return result.valid, result.reason
        except Exception as e:
            logger.error("Transport contract validation error: %s", e)
            return True, None

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the gateway."""
        pass

    @abstractmethod
    def send(self, message: dict[str, Any]) -> SendResult:
        """
        Send a message through the gateway.

        Args:
            message: ClawMessage as dictionary

        Returns:
            SendResult indicating success/failure
        """
        pass

    @abstractmethod
    def receive(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Poll for pending messages.

        Args:
            limit: Maximum messages to retrieve

        Returns:
            List of ClawMessage dictionaries
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the gateway connection."""
        pass

    def health_check(self) -> dict[str, Any]:
        """Return health status of the gateway connection."""
        return {
            "state": self.state.value,
            "endpoint": self.config.endpoint,
            "role": self.config.role,
            "squad_id": self.config.squad_id,
            "last_message_at": (
                self._last_message_time.isoformat() if self._last_message_time else None
            ),
            "error_count": self._error_count,
        }

    def _authenticate(self) -> bool:
        """
        Authenticate with the gateway using mesh secret.

        Returns True if authentication successful.
        """
        auth_message = GatewayMessage(
            method="AUTH",
            params={
                "squad_id": self.config.squad_id,
                "role": self.config.role,
                "secret": self.config.mesh_secret,
            },
        )
        response = self._send_request(auth_message)
        return response is not None and response.status == "authenticated"

    @abstractmethod
    def _send_request(self, message: GatewayMessage) -> Optional[GatewayResponse]:
        """Send a request and receive response."""
        pass


# ---------------------------------------------------------------------------
# Unix Socket Adapter
# ---------------------------------------------------------------------------


class UnixSocketGateway(GatewayAdapter):
    """
    Gateway adapter for local communication via Unix socket.

    Used when all squad members run on the same host (development/testing).
    """

    def __init__(self, config: GatewayConfig) -> None:
        super().__init__(config)
        self._socket: Optional[socket.socket] = None
        self._request_id = 0

    def connect(self) -> bool:
        """Connect to Unix socket gateway."""
        if not self.config.endpoint.startswith("unix://"):
            logger.error("Invalid endpoint for Unix socket: %s", self.config.endpoint)
            return False

        self.state = ConnectionState.CONNECTING
        sock_path = self.config.endpoint.replace("unix://", "")

        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.settimeout(self.config.timeout_ms / 1000)
            self._socket.connect(sock_path)
            self.state = ConnectionState.CONNECTED

            # Authenticate
            if not self._authenticate():
                logger.error("Authentication failed")
                self.close()
                return False

            logger.info("Connected to gateway at %s", sock_path)
            return True

        except socket.error as e:
            logger.error("Failed to connect to gateway: %s", e)
            self.state = ConnectionState.ERROR
            self._error_count += 1
            return False

    def send(self, message: dict[str, Any]) -> SendResult:
        """Send message through Unix socket."""
        if self.state != ConnectionState.CONNECTED:
            return SendResult(
                success=False,
                error_code="E001",
                error_message="Gateway not connected",
            )

        valid, reason = self._validate_message(message)
        if not valid:
            logger.error("Transport send validation failed: %s", reason)
            return SendResult(
                success=False,
                error_code="CONTRACT_VIOLATION",
                error_message=f"Contract validation failed: {reason}",
            )

        gateway_msg = GatewayMessage(
            method="SEND",
            params={"recipient": message.get("recipient_role"), "message": message},
        )

        response = self._send_request(gateway_msg)

        if response is None:
            return SendResult(
                success=False,
                error_code="E001",
                error_message="No response from gateway",
            )

        if response.error:
            return SendResult(
                success=False,
                message_id=message.get("message_id", ""),
                error_code=response.error.get("code", "E999"),
                error_message=response.error.get("message", "Unknown error"),
            )

        self._last_message_time = datetime.now(timezone.utc)
        return SendResult(
            success=response.status in ("queued", "delivered"),
            message_id=response.data.get("message_id", ""),
            requires_approval=response.data.get("requires_approval", False),
        )

    def receive(self, limit: int = 10) -> list[dict[str, Any]]:
        """Poll for pending messages."""
        if self.state != ConnectionState.CONNECTED:
            return []

        gateway_msg = GatewayMessage(
            method="RECEIVE", params={"role": self.config.role, "limit": limit}
        )

        response = self._send_request(gateway_msg)

        if response is None or response.error:
            return []

        messages = response.data.get("messages", [])
        valid_messages = []
        for msg in messages:
            valid, reason = self._validate_message(msg)
            if valid:
                valid_messages.append(msg)
            else:
                logger.error(
                    "Transport receive validation failed: %s. Dropping message.", reason
                )

        if valid_messages:
            self._last_message_time = datetime.now(timezone.utc)
        return valid_messages

    def close(self) -> None:
        """Close Unix socket connection."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self.state = ConnectionState.DISCONNECTED
        logger.info("Gateway connection closed")

    def _send_request(self, message: GatewayMessage) -> Optional[GatewayResponse]:
        """Send request and parse response."""
        if not self._socket:
            return None

        self._request_id += 1
        message.id = f"req-{self._request_id}"

        try:
            payload = json.dumps(
                {"method": message.method, "params": message.params, "id": message.id}
            )
            self._socket.sendall(payload.encode() + b"\n")

            # Read response
            response_data = b""
            while True:
                chunk = self._socket.recv(65536)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in response_data:
                    break

            response_json = json.loads(response_data.strip())
            return GatewayResponse(
                status=response_json.get("status", "error"),
                data=response_json.get("data", response_json.get("params", {})),
                error=response_json.get("error"),
            )

        except (socket.error, json.JSONDecodeError) as e:
            logger.error("Request failed: %s", e)
            self._error_count += 1
            return None


# ---------------------------------------------------------------------------
# WebSocket Adapter (for multi-host)
# ---------------------------------------------------------------------------


class WebSocketGateway(GatewayAdapter):
    """
    Gateway adapter for remote communication via WebSocket.

    Used for distributed squads across machines.
    Requires websocket-client library: pip install websocket-client
    """

    def __init__(self, config: GatewayConfig) -> None:
        super().__init__(config)
        self._ws: Any = None
        self._message_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._response_events: dict[str, threading.Event] = {}
        self._responses: dict[str, GatewayResponse] = {}
        self._thread: Optional[threading.Thread] = None
        self._request_id = 0
        self._subscriptions: dict[str, Callable[[dict[str, Any]], None]] = {}

    def connect(self) -> bool:
        """Connect to WebSocket gateway."""
        try:
            import websocket
        except ImportError:
            logger.error(
                "websocket-client not installed. Run: pip install websocket-client"
            )
            return False

        self.state = ConnectionState.CONNECTING

        # Convert endpoint URL
        ws_url = self.config.endpoint
        if ws_url.startswith("tcp://"):
            ws_url = ws_url.replace("tcp://", "ws://")
        elif ws_url.startswith("unix://"):
            logger.error("WebSocket adapter does not support Unix sockets")
            return False

        try:
            self._ws = websocket.WebSocketApp(  # type: ignore
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            self._thread = threading.Thread(target=self._ws.run_forever, daemon=True)
            self._thread.start()

            # Wait for connection
            time.sleep(0.5)

            if self.state == ConnectionState.CONNECTED:
                if not self._authenticate():
                    logger.error("Authentication failed")
                    self.close()
                    return False
                return True
            return False

        except Exception as e:
            logger.error("Failed to connect to WebSocket gateway: %s", e)
            self.state = ConnectionState.ERROR
            self._error_count += 1
            return False

    def _on_open(self, ws: Any) -> None:
        """WebSocket open callback."""
        self.state = ConnectionState.CONNECTED
        logger.info("WebSocket connected to %s", self.config.endpoint)

    def _on_message(self, ws: Any, message: str) -> None:
        """WebSocket message callback."""
        try:
            data = json.loads(message)

            # Check if this is a response to a request
            request_id = data.get("id", "")
            if request_id in self._response_events:
                self._responses[request_id] = GatewayResponse(
                    status=data.get("status", "error"),
                    data=data.get("data", data.get("params", {})),
                    error=data.get("error"),
                )
                self._response_events[request_id].set()
            # Check if this is a subscription event
            elif "event" in data:
                event_type = data["event"]
                if event_type in self._subscriptions:
                    self._subscriptions[event_type](data.get("message", {}))
            else:
                # Queue as incoming message
                self._message_queue.put(data)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse WebSocket message: %s", e)

    def _on_error(self, ws: Any, error: Any) -> None:
        """WebSocket error callback."""
        logger.error("WebSocket error: %s", error)
        self.state = ConnectionState.ERROR
        self._error_count += 1

    def _on_close(self, ws: Any, close_status_code: int, close_msg: str) -> None:
        """WebSocket close callback."""
        self.state = ConnectionState.DISCONNECTED
        logger.info("WebSocket closed: %s", close_msg)

    def send(self, message: dict[str, Any]) -> SendResult:
        """Send message through WebSocket."""
        if self.state != ConnectionState.CONNECTED:
            return SendResult(
                success=False,
                error_code="E001",
                error_message="Gateway not connected",
            )

        valid, reason = self._validate_message(message)
        if not valid:
            logger.error("Transport send validation failed: %s", reason)
            return SendResult(
                success=False,
                error_code="CONTRACT_VIOLATION",
                error_message=f"Contract validation failed: {reason}",
            )

        self._request_id += 1
        request_id = f"req-{self._request_id}"

        payload = {
            "id": request_id,
            "method": "SEND",
            "params": {"recipient": message.get("recipient_role"), "message": message},
        }

        event = threading.Event()
        self._response_events[request_id] = event

        try:
            self._ws.send(json.dumps(payload))

            # Wait for response
            if event.wait(timeout=self.config.timeout_ms / 1000):
                response: Optional[GatewayResponse] = self._responses.pop(
                    request_id, None
                )
                self._response_events.pop(request_id, None)

                if response is None or response.error:
                    err = response.error if response else None
                    return SendResult(
                        success=False,
                        message_id=message.get("message_id", ""),
                        error_code=err.get("code", "E999") if err else "E001",
                        error_message=err.get("message", "Unknown error")
                        if err
                        else "No response",
                    )

                self._last_message_time = datetime.now(timezone.utc)
                return SendResult(
                    success=response.status in ("queued", "delivered"),
                    message_id=response.data.get("message_id", ""),
                    requires_approval=response.data.get("requires_approval", False),
                )
            else:
                self._response_events.pop(request_id, None)
                return SendResult(
                    success=False,
                    error_code="E001",
                    error_message="Request timeout",
                )

        except Exception as e:
            self._response_events.pop(request_id, None)
            logger.error("Send failed: %s", e)
            self._error_count += 1
            return SendResult(success=False, error_code="E001", error_message=str(e))

    def receive(self, limit: int = 10) -> list[dict[str, Any]]:
        """Poll for pending messages."""
        messages = []
        for _ in range(limit):
            try:
                msg = self._message_queue.get_nowait()
                valid, reason = self._validate_message(msg)
                if valid:
                    messages.append(msg)
                else:
                    logger.error(
                        "Transport receive validation failed: %s. Dropping message.",
                        reason,
                    )
            except queue.Empty:
                break

        if messages:
            self._last_message_time = datetime.now(timezone.utc)
        return messages

    def subscribe(self, event: str, handler: Callable[[dict[str, Any]], None]) -> str:
        """Subscribe to real-time events."""
        if self.state != ConnectionState.CONNECTED:
            return ""

        subscription_id = f"sub-{event}-{self._request_id}"
        self._request_id += 1
        self._subscriptions[event] = handler

        payload = {
            "id": subscription_id,
            "method": "SUBSCRIBE",
            "params": {"role": self.config.role, "events": [event]},
        }

        self._ws.send(json.dumps(payload))
        return subscription_id

    def unsubscribe(self, event: str) -> bool:
        """Unsubscribe from events."""
        if event in self._subscriptions:
            del self._subscriptions[event]
            return True
        return False

    def close(self) -> None:
        """Close WebSocket connection."""
        if self._ws:
            self._ws.close()
            self._ws = None
        self.state = ConnectionState.DISCONNECTED

    def _send_request(self, message: GatewayMessage) -> Optional[GatewayResponse]:
        """Not used for WebSocket - use send() instead."""
        return None


# ---------------------------------------------------------------------------
# File-Based Adapter (Fallback)
# ---------------------------------------------------------------------------


class FileBasedGateway(GatewayAdapter):
    """
    Gateway adapter using file-based message queues.

    Fallback when OpenShell gateway is not available.
    Uses the ~/.milimo/mesh directory structure.
    """

    def __init__(self, config: GatewayConfig) -> None:
        super().__init__(config)
        self._base_dir: Optional[Path] = None
        self._inbox: Optional[Path] = None

    def connect(self) -> bool:
        """Initialize file-based message directories."""
        self._base_dir = mesh_dir()
        self._inbox = self._base_dir / "inbox" / self.config.role

        try:
            self._inbox.mkdir(parents=True, exist_ok=True)
            (self._base_dir / "outbox" / self.config.role).mkdir(
                parents=True, exist_ok=True
            )
            (self._base_dir / "delivered").mkdir(parents=True, exist_ok=True)
            (self._base_dir / "rejected").mkdir(parents=True, exist_ok=True)
            (self._base_dir / "inbox" / "war_room").mkdir(parents=True, exist_ok=True)

            self.state = ConnectionState.CONNECTED
            logger.info("File-based gateway initialized at %s", self._base_dir)
            return True

        except OSError as e:
            logger.error("Failed to initialize file-based gateway: %s", e)
            self.state = ConnectionState.ERROR
            return False

    def send(self, message: dict[str, Any]) -> SendResult:
        """Write message to recipient's inbox."""
        if self.state != ConnectionState.CONNECTED or not self._base_dir:
            return SendResult(
                success=False,
                error_code="E001",
                error_message="Gateway not connected",
            )

        valid, reason = self._validate_message(message)
        if not valid:
            logger.error("Transport send validation failed: %s", reason)
            return SendResult(
                success=False,
                error_code="CONTRACT_VIOLATION",
                error_message=f"Contract validation failed: {reason}",
            )

        recipient = message.get("recipient_role", "")
        if not recipient:
            return SendResult(
                success=False,
                error_code="E003",
                error_message="Missing recipient_role in message",
            )

        recipient_inbox = self._base_dir / "inbox" / recipient
        recipient_inbox.mkdir(parents=True, exist_ok=True)

        timestamp = message.get("timestamp", datetime.now(timezone.utc).isoformat())
        message_id = message.get("message_id", "")

        filename = f"{timestamp.replace(':', '-').replace('.', '-')}_{message_id}.json"
        filepath = recipient_inbox / filename

        try:
            filepath.write_text(json.dumps(message, indent=2, default=str))
            self._last_message_time = datetime.now(timezone.utc)
            logger.debug("Message written to %s", filepath)

            # Check if recipient is war_room (needs approval)
            requires_approval = recipient == "war_room"

            return SendResult(
                success=True,
                message_id=message_id,
                requires_approval=requires_approval,
            )

        except OSError as e:
            logger.error("Failed to write message: %s", e)
            self._error_count += 1
            return SendResult(
                success=False,
                message_id=message_id,
                error_code="E001",
                error_message=str(e),
            )

    def receive(self, limit: int = 10) -> list[dict[str, Any]]:
        """Read messages from inbox."""
        if self.state != ConnectionState.CONNECTED or not self._inbox:
            return []

        messages = []
        try:
            for msg_file in sorted(self._inbox.glob("*.json"))[:limit]:
                try:
                    content = msg_file.read_text()
                    msg = json.loads(content)
                    valid, reason = self._validate_message(msg)
                    if valid:
                        messages.append(msg)
                    else:
                        logger.error(
                            "Transport receive validation failed: %s. Dropping message.",
                            reason,
                        )
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to read message %s: %s", msg_file, e)

            if messages:
                self._last_message_time = datetime.now(timezone.utc)

        except OSError as e:
            logger.error("Failed to read inbox: %s", e)

        return messages

    def ack(self, message_id: str) -> bool:
        """Acknowledge and remove a message from inbox."""
        if not self._inbox or not self._base_dir:
            return False

        for msg_file in self._inbox.glob(f"*{message_id}*.json"):
            try:
                # Move to delivered
                delivered_dir = self._base_dir / "delivered"
                msg_file.rename(delivered_dir / msg_file.name)
                return True
            except OSError:
                pass
        return False

    def reject(self, message_id: str, reason: str = "") -> bool:
        """Reject and move message to rejected queue."""
        if not self._inbox or not self._base_dir:
            return False

        for msg_file in self._inbox.glob(f"*{message_id}*.json"):
            try:
                rejected_dir = self._base_dir / "rejected"
                target = rejected_dir / msg_file.name
                msg_file.rename(target)

                # Write rejection reason
                (target.with_suffix(".rejected.json")).write_text(
                    json.dumps(
                        {
                            "reason": reason,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )
                return True
            except OSError:
                pass
        return False

    def close(self) -> None:
        """No persistent connection to close."""
        self.state = ConnectionState.DISCONNECTED

    def _send_request(self, message: GatewayMessage) -> Optional[GatewayResponse]:
        """Not applicable for file-based gateway."""
        return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_gateway(config: GatewayConfig) -> GatewayAdapter:
    """
    Create appropriate gateway adapter based on endpoint.

    Args:
        config: Gateway configuration

    Returns:
        GatewayAdapter instance
    """
    endpoint = config.endpoint

    if endpoint.startswith("unix://"):
        return UnixSocketGateway(config)
    elif endpoint.startswith("tcp://") or endpoint.startswith("ws://"):
        return WebSocketGateway(config)
    elif endpoint.startswith("file://") or endpoint == "":
        return FileBasedGateway(config)
    else:
        logger.warning("Unknown endpoint scheme, using file-based gateway")
        return FileBasedGateway(config)
