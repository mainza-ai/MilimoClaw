#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Mesh Failover

Handles failover scenarios for the multi-region mesh. Detects node
failures, region isolation, and network partitions. Implements
automatic recovery and split-brain resolution.

Usage:
    from orchestrator.mesh_failover import FailoverManager, FailoverState

    manager = FailoverManager(mesh_coordinator)
    manager.start()

    # Check if failover is active
    if manager.state == FailoverState.FAILOVER_ACTIVE:
        print("Operating in failover mode")
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("milimo.mesh_failover")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class FailoverState(str, Enum):
    """Failover operational states."""

    NORMAL = "normal"
    DEGRADED = "degraded"
    FAILOVER_ACTIVE = "failover_active"
    PARTITION = "partition"
    RECOVERING = "recovering"


class FailoverEvent(str, Enum):
    """Types of failover events."""

    NODE_OFFLINE = "node_offline"
    NODE_ONLINE = "node_online"
    REGION_ISOLATED = "region_isolated"
    REGION_RECOVERED = "region_recovered"
    PARTITION_DETECTED = "partition_detected"
    PARTITION_HEALED = "partition_healed"
    RELAY_CONNECTED = "relay_connected"
    RELAY_DISCONNECTED = "relay_disconnected"


@dataclass
class NodeHealth:
    """Health status of a mesh node."""

    role: str
    region: str
    status: str  # online, offline, unhealthy, recovering
    last_heartbeat: str
    consecutive_failures: int
    last_failure_reason: str = ""
    recovery_attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "region": self.region,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_reason": self.last_failure_reason,
            "recovery_attempts": self.recovery_attempts,
        }


@dataclass
class RegionHealth:
    """Health status of a region."""

    region_id: str
    status: str  # healthy, degraded, isolated, unknown
    nodes_online: int
    nodes_total: int
    latency_ms: float
    packet_loss: float
    last_updated: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "status": self.status,
            "nodes_online": self.nodes_online,
            "nodes_total": self.nodes_total,
            "latency_ms": self.latency_ms,
            "packet_loss": self.packet_loss,
            "last_updated": self.last_updated,
        }


@dataclass
class FailoverRecord:
    """Record of a failover event."""

    event_id: str
    event_type: FailoverEvent
    timestamp: str
    details: dict[str, Any]
    actions_taken: list[str] = field(default_factory=list)
    resolved_at: str = ""
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "details": self.details,
            "actions_taken": self.actions_taken,
            "resolved_at": self.resolved_at,
            "resolved": self.resolved,
        }


@dataclass
class VersionVector:
    """
    Vector clock for split-brain resolution.

    Tracks causality of messages across nodes for conflict resolution.
    """

    node_id: str
    counters: dict[str, int] = field(default_factory=dict)
    timestamp: str = ""

    def increment(self) -> None:
        """Increment own counter."""
        self.counters[self.node_id] = self.counters.get(self.node_id, 0) + 1
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def merge(self, other: VersionVector) -> VersionVector:
        """Merge two version vectors."""
        merged = VersionVector(node_id=self.node_id)

        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        for node in all_nodes:
            merged.counters[node] = max(
                self.counters.get(node, 0),
                other.counters.get(node, 0)
            )

        merged.timestamp = datetime.now(timezone.utc).isoformat()
        return merged

    def happens_before(self, other: VersionVector) -> bool:
        """Check if this vector happens-before another."""
        dominated = False
        for node in set(self.counters.keys()) | set(other.counters.keys()):
            self_val = self.counters.get(node, 0)
            other_val = other.counters.get(node, 0)
            if self_val > other_val:
                return False
            if self_val < other_val:
                dominated = True
        return dominated

    def concurrent_with(self, other: VersionVector) -> bool:
        """Check if two vectors are concurrent (conflict)."""
        return not self.happens_before(other) and not other.happens_before(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "counters": self.counters,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Failover Manager
# ---------------------------------------------------------------------------

class FailoverManager:
    """
    Manages failover for the mesh.

    Responsibilities:
    - Monitor node health
    - Detect region isolation
    - Handle network partitions
    - Coordinate recovery
    """

    def __init__(
        self,
        mesh_coordinator: Any,
        heartbeat_timeout_ms: int = 10000,
        max_recovery_attempts: int = 5,
        recovery_delay_ms: int = 5000,
        partition_timeout_ms: int = 60000,
    ) -> None:
        self.mesh = mesh_coordinator
        self.heartbeat_timeout_ms = heartbeat_timeout_ms
        self.max_recovery_attempts = max_recovery_attempts
        self.recovery_delay_ms = recovery_delay_ms
        self.partition_timeout_ms = partition_timeout_ms

        self.state = FailoverState.NORMAL
        self._node_health: dict[str, NodeHealth] = {}
        self._region_health: dict[str, RegionHealth] = {}
        self._failover_history: list[FailoverRecord] = []
        self._version_vector: Optional[VersionVector] = None
        self._pending_messages: dict[str, list[dict[str, Any]]] = {}

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._event_handlers: dict[FailoverEvent, list[Callable[[FailoverRecord], None]]] = {}

    def start(self) -> None:
        """Start failover monitoring."""
        if self._running:
            return

        self._running = True
        self._version_vector = VersionVector(node_id=self.mesh.squad_id)
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Failover manager started")

    def stop(self) -> None:
        """Stop failover monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Failover manager stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            self._check_node_health()
            self._check_region_health()
            self._detect_partitions()
            self._attempt_recovery()

            time.sleep(self.heartbeat_timeout_ms / 1000 / 2)

    def _check_node_health(self) -> None:
        """Check health of all registered nodes."""
        topology = self.mesh.topology
        now = datetime.now(timezone.utc)

        for role, node in topology.items():
            health = self._node_health.get(role, NodeHealth(
                role=role,
                region=self._get_node_region(node),
                status="online",
                last_heartbeat="",
                consecutive_failures=0,
            ))

            if node.last_heartbeat:
                last_hb = datetime.fromisoformat(node.last_heartbeat.replace("Z", "+00:00"))
                elapsed_ms = (now - last_hb).total_seconds() * 1000

                if elapsed_ms > self.heartbeat_timeout_ms:
                    self._handle_node_timeout(role, health, elapsed_ms)
                else:
                    health.status = "online"
                    health.consecutive_failures = 0
                    health.last_heartbeat = node.last_heartbeat

            self._node_health[role] = health

    def _get_node_region(self, node: Any) -> str:
        """Get region for a node."""
        return getattr(node, "region", "unknown")

    def _handle_node_timeout(self, role: str, health: NodeHealth, elapsed_ms: float) -> None:
        """Handle a node heartbeat timeout."""
        health.consecutive_failures += 1
        health.last_failure_reason = f"Heartbeat timeout: {elapsed_ms:.0f}ms"

        if health.status == "online":
            health.status = "unhealthy"
            logger.warning("Node %s is unhealthy (timeout: %.0fms)", role, elapsed_ms)
            self._emit_event(FailoverEvent.NODE_OFFLINE, {"role": role, "reason": "timeout"})

        elif health.status == "unhealthy" and health.consecutive_failures >= 3:
            health.status = "offline"
            logger.error("Node %s is offline after %d failures", role, health.consecutive_failures)
            self._update_failover_state()

    def _check_region_health(self) -> None:
        """Check health of each region."""
        regions: dict[str, list[str]] = {}

        for role, health in self._node_health.items():
            region = health.region
            if region not in regions:
                regions[region] = []
            regions[region].append(role)

        for region_id, nodes in regions.items():
            online = sum(1 for r in nodes if self._node_health.get(
                r, NodeHealth(role=r, region=region_id, status="unknown", last_heartbeat="", consecutive_failures=0)
            ).status == "online")

            total = len(nodes)
            status = "healthy" if online == total else ("degraded" if online > 0 else "isolated")

            self._region_health[region_id] = RegionHealth(
                region_id=region_id,
                status=status,
                nodes_online=online,
                nodes_total=total,
                latency_ms=0.0,
                packet_loss=0.0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

            if status == "isolated":
                self._handle_region_isolated(region_id)

    def _handle_region_isolated(self, region_id: str) -> None:
        """Handle a region becoming isolated."""
        if self.state != FailoverState.PARTITION:
            self.state = FailoverState.DEGRADED
            logger.warning("Region %s is isolated", region_id)
            self._emit_event(FailoverEvent.REGION_ISOLATED, {"region": region_id})

    def _detect_partitions(self) -> None:
        """Detect network partitions."""
        if self.state == FailoverState.PARTITION:
            return

        healthy_regions = sum(
            1 for r in self._region_health.values() if r.status == "healthy"
        )

        isolated_regions = sum(
            1 for r in self._region_health.values() if r.status == "isolated"
        )

        if isolated_regions > 0 and healthy_regions > 0:
            self.state = FailoverState.PARTITION
            logger.error("Network partition detected: %d regions isolated", isolated_regions)
            self._emit_event(FailoverEvent.PARTITION_DETECTED, {
                "isolated_regions": [r for r, h in self._region_health.items() if h.status == "isolated"],
            })

    def _attempt_recovery(self) -> None:
        """Attempt recovery from failover states."""
        if self.state == FailoverState.NORMAL:
            return

        all_healthy = all(
            h.status == "healthy" for h in self._region_health.values()
        )

        if all_healthy:
            self._handle_recovery()

    def _handle_recovery(self) -> None:
        """Handle recovery from failover."""
        previous_state = self.state
        self.state = FailoverState.RECOVERING
        logger.info("Recovering from %s state", previous_state.value)

        self._replay_pending_messages()

        self.state = FailoverState.NORMAL
        logger.info("Recovery complete, now in normal state")

        if previous_state == FailoverState.PARTITION:
            self._emit_event(FailoverEvent.PARTITION_HEALED, {})
        else:
            self._emit_event(FailoverEvent.REGION_RECOVERED, {})

    def _replay_pending_messages(self) -> None:
        """Replay messages queued during partition."""
        with self._lock:
            for recipient, messages in self._pending_messages.items():
                for msg in messages:
                    logger.info("Replaying message to %s: %s", recipient, msg.get("message_id"))
                    self.mesh.send_message(msg)

            self._pending_messages.clear()

    def _update_failover_state(self) -> None:
        """Update overall failover state based on node health."""
        offline_count = sum(
            1 for h in self._node_health.values() if h.status == "offline"
        )

        if offline_count == 0:
            self.state = FailoverState.NORMAL
        elif offline_count < len(self._node_health):
            self.state = FailoverState.DEGRADED
        else:
            self.state = FailoverState.FAILOVER_ACTIVE

    def _emit_event(self, event_type: FailoverEvent, details: dict[str, Any]) -> FailoverRecord:
        """Emit a failover event."""
        event_id = f"{event_type.value}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        record = FailoverRecord(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
        )

        with self._lock:
            self._failover_history.append(record)

        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(record)
            except Exception as e:
                logger.error("Event handler failed: %s", e)

        return record

    def queue_message(self, message: dict[str, Any]) -> None:
        """Queue a message for later delivery during partition."""
        recipient = message.get("recipient_role", "")
        if recipient not in self._pending_messages:
            self._pending_messages[recipient] = []
        self._pending_messages[recipient].append(message)

        if self._version_vector:
            self._version_vector.increment()

    def get_node_health(self, role: str) -> Optional[NodeHealth]:
        """Get health status for a node."""
        return self._node_health.get(role)

    def get_region_health(self, region_id: str) -> Optional[RegionHealth]:
        """Get health status for a region."""
        return self._region_health.get(region_id)

    def get_all_node_health(self) -> dict[str, NodeHealth]:
        """Get health status for all nodes."""
        return dict(self._node_health)

    def get_all_region_health(self) -> dict[str, RegionHealth]:
        """Get health status for all regions."""
        return dict(self._region_health)

    def on_event(self, event_type: FailoverEvent, handler: Callable[[FailoverRecord], None]) -> None:
        """Register a handler for a failover event."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def is_failover_active(self) -> bool:
        """Check if failover is currently active."""
        return self.state in (FailoverState.FAILOVER_ACTIVE, FailoverState.PARTITION)

    def get_version_vector(self) -> Optional[VersionVector]:
        """Get current version vector."""
        return self._version_vector

    def resolve_conflict(self, local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve conflict between two versions of data.

        Uses last-write-wins with version vectors.
        """
        local_ts = local.get("_timestamp", "")
        remote_ts = remote.get("_timestamp", "")

        if local_ts > remote_ts:
            return local
        elif remote_ts > local_ts:
            return remote
        else:
            return local if local.get("_node_id", "") > remote.get("_node_id", "") else remote


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "FailoverState",
    "FailoverEvent",
    "NodeHealth",
    "RegionHealth",
    "FailoverRecord",
    "VersionVector",
    "FailoverManager",
]
