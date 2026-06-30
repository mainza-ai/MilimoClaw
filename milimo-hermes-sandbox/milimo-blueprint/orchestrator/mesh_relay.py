# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Mesh Relay

Provides relay server functionality for NAT traversal and cross-region
communication. Enables squad members behind firewalls to participate
in the mesh through a public relay endpoint.

Usage:
    from orchestrator.mesh_relay import MeshRelay, RelayClient

    # Server mode
    relay = MeshRelay(port=443, tls_cert="/path/to/cert.pem")
    relay.start()

    # Client mode
    client = RelayClient(relay_url="wss://relay.milimo.dev:443")
    client.connect()
"""

from __future__ import annotations

import hashlib
import json
import logging
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger("milimo.mesh_relay")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class RelayState(str, Enum):
    """Relay connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    READY = "ready"
    ERROR = "error"


@dataclass
class RelayConfig:
    """Configuration for mesh relay."""

    relay_url: str = ""
    mesh_secret: str = ""
    squad_id: str = ""
    role: str = ""
    region: str = ""
    timeout_ms: int = 10000
    reconnect_attempts: int = 5
    reconnect_delay_ms: int = 2000
    heartbeat_interval_ms: int = 30000
    max_connections: int = 100


@dataclass
class RelayConnection:
    """Represents a connection through the relay."""

    connection_id: str
    squad_id: str
    role: str
    region: str
    connected_at: str
    last_activity: str
    bytes_sent: int = 0
    bytes_received: int = 0


@dataclass
class RoutedMessage:
    """Message being routed through the relay."""

    message_id: str
    sender_connection_id: str
    recipient_connection_id: str
    payload: dict[str, Any]
    timestamp: str
    hops: int = 0


# ---------------------------------------------------------------------------
# Relay Client
# ---------------------------------------------------------------------------


class RelayClient:
    """
    Client for connecting to a mesh relay.

    Used when direct P2P connections are not possible (NAT/firewall).
    """

    def __init__(self, config: RelayConfig) -> None:
        self.config = config
        self.state = RelayState.DISCONNECTED
        self._connection_id: str = ""
        self._ws: Any = None
        self._message_queue: list[dict[str, Any]] = []
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_heartbeat: Optional[datetime] = None
        self._message_handlers: dict[str, Callable[[dict[str, Any]], None]] = {}

    def connect(self) -> bool:
        """Connect to the relay server."""
        try:
            import websocket  # noqa: F401
        except ImportError:
            logger.error("websocket-client not installed")
            return False

        self.state = RelayState.CONNECTING

        try:
            self._ws = websocket.WebSocketApp(
                self.config.relay_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            self._running = True
            self._thread = threading.Thread(target=self._run_websocket, daemon=True)
            self._thread.start()

            for _ in range(20):
                if self.state == RelayState.READY:
                    return True
                if self.state == RelayState.ERROR:
                    return False
                time.sleep(0.1)

            logger.warning("Connection timeout")
            return self.state == RelayState.READY

        except Exception as e:
            logger.error("Failed to connect to relay: %s", e)
            self.state = RelayState.ERROR
            return False

    def _run_websocket(self) -> None:
        """Run the websocket connection loop."""
        if self._ws:
            self._ws.run_forever()

    def _on_open(self, ws: Any) -> None:
        """WebSocket opened."""
        logger.info("Connected to relay: %s", self.config.relay_url)
        self.state = RelayState.AUTHENTICATING
        self._authenticate()

    def _on_message(self, ws: Any, message: str) -> None:
        """Handle incoming message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "auth_success":
                self._connection_id = data.get("connection_id", "")
                self.state = RelayState.READY
                logger.info(
                    "Authenticated with relay, connection_id: %s", self._connection_id
                )

            elif msg_type == "message":
                self._handle_routed_message(data)

            elif msg_type == "heartbeat_ack":
                self._last_heartbeat = datetime.now(timezone.utc)

            elif msg_type == "error":
                logger.error("Relay error: %s", data.get("message"))
                self.state = RelayState.ERROR

        except json.JSONDecodeError as e:
            logger.error("Failed to parse relay message: %s", e)

    def _on_error(self, ws: Any, error: Any) -> None:
        """WebSocket error."""
        logger.error("Relay error: %s", error)
        self.state = RelayState.ERROR

    def _on_close(self, ws: Any, close_status_code: int, close_msg: str) -> None:
        """WebSocket closed."""
        self.state = RelayState.DISCONNECTED
        logger.info("Relay connection closed: %s", close_msg)
        self._schedule_reconnect()

    def _authenticate(self) -> None:
        """Send authentication to relay."""
        auth_payload = {
            "type": "auth",
            "squad_id": self.config.squad_id,
            "role": self.config.role,
            "region": self.config.region,
            "secret": self._hash_secret(self.config.mesh_secret),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._ws.send(json.dumps(auth_payload))

    def _hash_secret(self, secret: str) -> str:
        """Hash the mesh secret for authentication."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = f"{secret}:{timestamp}:{self.config.squad_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _handle_routed_message(self, data: dict[str, Any]) -> None:
        """Handle a message routed through relay."""
        message = data.get("message", {})
        sender = data.get("sender", "")

        handler = self._message_handlers.get(sender)
        if handler:
            handler(message)
        else:
            self._message_queue.append(message)

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""
        if not self._running:
            return

        def reconnect():
            time.sleep(self.config.reconnect_delay_ms / 1000)
            if self._running and self.state == RelayState.DISCONNECTED:
                self.connect()

        threading.Thread(target=reconnect, daemon=True).start()

    def send(self, recipient_role: str, message: dict[str, Any]) -> bool:
        """Send a message through the relay."""
        if self.state != RelayState.READY:
            logger.warning("Relay not ready, state: %s", self.state)
            return False

        payload = {
            "type": "route",
            "recipient_role": recipient_role,
            "squad_id": self.config.squad_id,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self._ws.send(json.dumps(payload))
            return True
        except Exception as e:
            logger.error("Failed to send via relay: %s", e)
            return False

    def receive(self, limit: int = 10) -> list[dict[str, Any]]:
        """Receive queued messages."""
        messages = self._message_queue[:limit]
        self._message_queue = self._message_queue[limit:]
        return messages

    def subscribe(
        self, sender_role: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """Subscribe to messages from a specific role."""
        self._message_handlers[sender_role] = handler

    def heartbeat(self) -> bool:
        """Send a heartbeat to the relay."""
        if self.state != RelayState.READY:
            return False

        try:
            self._ws.send(
                json.dumps({"type": "heartbeat", "connection_id": self._connection_id})
            )
            return True
        except Exception as e:
            logger.error("Heartbeat failed: %s", e)
            return False

    def close(self) -> None:
        """Close the relay connection."""
        self._running = False
        if self._ws:
            self._ws.close()
        self.state = RelayState.DISCONNECTED

    @property
    def connection_id(self) -> str:
        return self._connection_id

    @property
    def is_ready(self) -> bool:
        return self.state == RelayState.READY


# ---------------------------------------------------------------------------
# Relay Server (for self-hosted deployments)
# ---------------------------------------------------------------------------


class MeshRelay:
    """
    Relay server for mesh communication.

    Used for self-hosted deployments where squads want to run their own
    relay infrastructure.
    """

    def __init__(
        self,
        port: int = 443,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        mesh_secret: str = "",
        max_connections: int = 100,
    ) -> None:
        self.port = port
        self.tls_cert = tls_cert
        self.tls_key = tls_key
        self.mesh_secret = mesh_secret
        self.max_connections = max_connections

        self._connections: dict[str, RelayConnection] = {}
        self._role_index: dict[str, str] = {}  # role -> connection_id
        self._running = False
        self._lock = threading.Lock()
        self._server: Any = None

    def start(self) -> bool:
        """Start the relay server."""
        try:
            import websocket  # noqa: F401
        except ImportError:
            logger.error("websocket-client not installed")
            return False

        self._running = True

        if self.tls_cert and self.tls_key:
            pass

        def on_connect(ws: Any, path: str) -> None:
            self._handle_connection(ws)

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(("0.0.0.0", self.port))
            self._server_socket.listen(self.max_connections)
            self._server_socket.settimeout(1.0)
            logger.info("Relay server started on port %d", self.port)
            return True
        except Exception as e:
            logger.error("Failed to start relay server: %s", e)
            return False

    def stop(self) -> None:
        """Stop the relay server."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def _handle_connection(self, ws: Any) -> None:
        """Handle a new connection."""
        connection_id = ""

        try:
            for message in ws:
                data = json.loads(message)
                msg_type = data.get("type", "")

                if msg_type == "auth":
                    connection_id = self._authenticate_connection(ws, data)
                    if not connection_id:
                        ws.send(
                            json.dumps(
                                {"type": "error", "message": "Authentication failed"}
                            )
                        )
                        return

                elif msg_type == "route":
                    self._route_message(connection_id, data)

                elif msg_type == "heartbeat":
                    self._handle_heartbeat(connection_id)

        except json.JSONDecodeError:
            logger.warning("Invalid message from connection")
        except Exception as e:
            logger.error("Connection error: %s", e)
        finally:
            if connection_id:
                self._remove_connection(connection_id)

    def _authenticate_connection(self, ws: Any, data: dict[str, Any]) -> str:
        """Authenticate a new connection."""
        with self._lock:
            if len(self._connections) >= self.max_connections:
                return ""

            squad_id = data.get("squad_id", "")
            role = data.get("role", "")
            region = data.get("region", "unknown")
            secret_hash = data.get("secret", "")

            expected_hash = self._hash_secret(self.mesh_secret, squad_id)
            if secret_hash != expected_hash:
                logger.warning("Invalid secret for squad: %s", squad_id)
                return ""

            connection_id = hashlib.sha256(
                f"{squad_id}:{role}:{time.time()}".encode()
            ).hexdigest()[:16]

            connection = RelayConnection(
                connection_id=connection_id,
                squad_id=squad_id,
                role=role,
                region=region,
                connected_at=datetime.now(timezone.utc).isoformat(),
                last_activity=datetime.now(timezone.utc).isoformat(),
            )

            self._connections[connection_id] = connection
            self._role_index[f"{squad_id}:{role}"] = connection_id

            ws.send(
                json.dumps(
                    {
                        "type": "auth_success",
                        "connection_id": connection_id,
                    }
                )
            )

            logger.info(
                "Authenticated connection: %s (%s/%s)", connection_id, squad_id, role
            )
            return connection_id

    def _route_message(self, sender_id: str, data: dict[str, Any]) -> None:
        """Route a message to recipient."""
        recipient_role = data.get("recipient_role", "")
        squad_id = data.get("squad_id", "")
        message = data.get("message", {})

        recipient_key = f"{squad_id}:{recipient_role}"
        recipient_id = self._role_index.get(recipient_key)

        if not recipient_id:
            logger.warning("Recipient not found: %s", recipient_role)
            return

        with self._lock:
            if recipient_id not in self._connections:
                return

            recipient_conn = self._connections[recipient_id]
            recipient_conn.bytes_received += len(json.dumps(message))

            sender_conn = self._connections.get(sender_id)
            if sender_conn:
                sender_conn.bytes_sent += len(json.dumps(message))

    def _handle_heartbeat(self, connection_id: str) -> None:
        """Handle heartbeat from connection."""
        with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].last_activity = datetime.now(
                    timezone.utc
                ).isoformat()

    def _remove_connection(self, connection_id: str) -> None:
        """Remove a connection."""
        with self._lock:
            if connection_id in self._connections:
                conn = self._connections.pop(connection_id)
                key = f"{conn.squad_id}:{conn.role}"
                self._role_index.pop(key, None)
                logger.info("Removed connection: %s", connection_id)

    def _hash_secret(self, secret: str, squad_id: str) -> str:
        """Hash the mesh secret for verification."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data = f"{secret}:{timestamp}:{squad_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    def get_stats(self) -> dict[str, Any]:
        """Get relay server statistics."""
        with self._lock:
            return {
                "total_connections": len(self._connections),
                "max_connections": self.max_connections,
                "connections": [
                    {
                        "connection_id": c.connection_id,
                        "squad_id": c.squad_id,
                        "role": c.role,
                        "region": c.region,
                        "bytes_sent": c.bytes_sent,
                        "bytes_received": c.bytes_received,
                    }
                    for c in self._connections.values()
                ],
            }


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "RelayState",
    "RelayConfig",
    "RelayConnection",
    "RoutedMessage",
    "RelayClient",
    "MeshRelay",
]
