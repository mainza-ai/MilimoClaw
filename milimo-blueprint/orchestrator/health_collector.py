# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Health Collector

Collects and aggregates health metrics from all squad claws for
real-time health monitoring and alerting.

Usage:
    from orchestrator.health_collector import HealthCollector

    collector = HealthCollector(mesh_coordinator)
    collector.start()

    health = collector.get_claw_health("content")
    print(f"Content claw health: {health.score}")
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum

from .milimo_paths import health_dir

logger = logging.getLogger("milimo.health_collector")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    GOOD = "good"
    FAIR = "fair"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class MetricSample:
    """A single metric sample."""

    metric_type: str
    value: float
    timestamp: str
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


@dataclass
class ClawHealthMetrics:
    """All metrics for a single claw."""

    claw_role: str
    heartbeat_latency_ms: float = 0.0
    message_throughput_per_min: float = 0.0
    evolution_status: str = "never_run"
    approval_backlog: int = 0
    error_rate_per_hour: float = 0.0
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claw_role": self.claw_role,
            "heartbeat_latency_ms": self.heartbeat_latency_ms,
            "message_throughput_per_min": self.message_throughput_per_min,
            "evolution_status": self.evolution_status,
            "approval_backlog": self.approval_backlog,
            "error_rate_per_hour": self.error_rate_per_hour,
            "last_updated": self.last_updated,
        }


@dataclass
class ClawHealth:
    """Health status for a single claw."""

    role: str
    status: HealthStatus
    score: float
    metrics: ClawHealthMetrics
    region: str = ""
    squad_id: str = ""
    last_heartbeat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "status": self.status.value,
            "score": self.score,
            "metrics": self.metrics.to_dict(),
            "region": self.region,
            "squad_id": self.squad_id,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class SquadHealth:
    """Health status for the entire squad."""

    squad_id: str
    overall_score: float
    overall_status: HealthStatus
    claws: list[ClawHealth]
    alerts: list[dict[str, Any]]
    last_updated: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "squad_id": self.squad_id,
            "overall_score": self.overall_score,
            "overall_status": self.overall_status.value,
            "claws": [c.to_dict() for c in self.claws],
            "alerts": self.alerts,
            "last_updated": self.last_updated,
        }


# ---------------------------------------------------------------------------
# Health Scorer
# ---------------------------------------------------------------------------


class HealthScorer:
    """Calculates health scores from metrics."""

    WEIGHTS = {
        "heartbeat_latency": 0.30,
        "message_throughput": 0.25,
        "evolution_status": 0.20,
        "approval_backlog": 0.15,
        "error_rate": 0.10,
    }

    @classmethod
    def calculate_score(cls, metrics: ClawHealthMetrics) -> float:
        """Calculate overall health score from metrics."""
        heartbeat_score = cls.score_heartbeat_latency(metrics.heartbeat_latency_ms)
        throughput_score = cls.score_throughput(metrics.message_throughput_per_min)
        evolution_score = cls.score_evolution_status(metrics.evolution_status)
        backlog_score = cls.score_backlog(metrics.approval_backlog)
        error_score = cls.score_error_rate(metrics.error_rate_per_hour)

        weighted = (
            heartbeat_score * cls.WEIGHTS["heartbeat_latency"]
            + throughput_score * cls.WEIGHTS["message_throughput"]
            + evolution_score * cls.WEIGHTS["evolution_status"]
            + backlog_score * cls.WEIGHTS["approval_backlog"]
            + error_score * cls.WEIGHTS["error_rate"]
        )

        return round(weighted, 1)

    @classmethod
    def score_heartbeat_latency(cls, latency_ms: float) -> float:
        if latency_ms < 100:
            return 100.0
        elif latency_ms < 500:
            return 90.0
        elif latency_ms < 1000:
            return 70.0
        elif latency_ms < 5000:
            return 40.0
        else:
            return 0.0

    @classmethod
    def score_throughput(cls, throughput: float) -> float:
        capacity = 20.0
        ratio = throughput / capacity if capacity > 0 else 0
        if ratio > 1.0:
            return 100.0
        elif ratio > 0.8:
            return 90.0
        elif ratio > 0.5:
            return 70.0
        elif ratio > 0.2:
            return 40.0
        else:
            return 20.0

    @classmethod
    def score_evolution_status(cls, status: str) -> float:
        scores = {
            "success": 100.0,
            "success_24h": 100.0,
            "success_48h": 80.0,
            "success_7d": 60.0,
            "skipped": 50.0,
            "failed_recoverable": 30.0,
            "failed_critical": 0.0,
            "never_run": 40.0,
        }
        return scores.get(status, 50.0)

    @classmethod
    def score_backlog(cls, count: int) -> float:
        if count == 0:
            return 100.0
        elif count <= 5:
            return 90.0
        elif count <= 10:
            return 70.0
        elif count <= 20:
            return 50.0
        else:
            return 20.0

    @classmethod
    def score_error_rate(cls, rate: float) -> float:
        if rate == 0:
            return 100.0
        elif rate <= 5:
            return 80.0
        elif rate <= 10:
            return 60.0
        elif rate <= 20:
            return 30.0
        else:
            return 0.0

    @classmethod
    def score_to_status(cls, score: float, offline: bool = False) -> HealthStatus:
        if offline:
            return HealthStatus.OFFLINE
        if score >= 90:
            return HealthStatus.HEALTHY
        elif score >= 70:
            return HealthStatus.GOOD
        elif score >= 50:
            return HealthStatus.FAIR
        elif score >= 30:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.CRITICAL


# ---------------------------------------------------------------------------
# Health Collector
# ---------------------------------------------------------------------------


class HealthCollector:
    """
    Collects health metrics from all squad claws.

    Features:
    - Periodic metric collection
    - Rolling window aggregation
    - Alert generation
    - Historical data storage
    """

    def __init__(
        self,
        mesh_coordinator: Any,
        collection_interval_ms: int = 10000,
        storage_dir: Optional[str] = None,
    ) -> None:
        self.mesh = mesh_coordinator
        self.collection_interval_ms = collection_interval_ms

        self._metrics: dict[str, ClawHealthMetrics] = {}
        self._health: dict[str, ClawHealth] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._alerts: list[dict[str, Any]] = []

        if storage_dir:
            self._storage_dir = Path(storage_dir)
        else:
            self._storage_dir = health_dir()

        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Start health collection."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        logger.info("Health collector started")

    def stop(self) -> None:
        """Stop health collection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health collector stopped")

    def _collection_loop(self) -> None:
        """Background collection loop."""
        while self._running:
            self._collect_all_metrics()
            self._calculate_health_scores()
            self._check_alerts()
            self._save_health_data()

            interval_seconds = self.collection_interval_ms / 1000
            time.sleep(interval_seconds)

    def _collect_all_metrics(self) -> None:
        """Collect metrics from all registered claws."""
        topology = self.mesh.topology

        for role, node in topology.items():
            metrics = self._collect_claw_metrics(role, node)
            with self._lock:
                self._metrics[role] = metrics

    def _collect_claw_metrics(self, role: str, node: Any) -> ClawHealthMetrics:
        """Collect metrics for a single claw."""
        now = datetime.now(timezone.utc).isoformat()

        metrics = ClawHealthMetrics(
            claw_role=role,
            last_updated=now,
        )

        # Heartbeat latency
        if hasattr(node, "last_heartbeat") and node.last_heartbeat:
            try:
                last_hb = datetime.fromisoformat(
                    node.last_heartbeat.replace("Z", "+00:00")
                )
                metrics.heartbeat_latency_ms = (
                    datetime.now(timezone.utc) - last_hb
                ).total_seconds() * 1000
            except Exception:
                metrics.heartbeat_latency_ms = float("inf")

        # Status from node
        if hasattr(node, "status"):
            if node.status == "offline":
                metrics.heartbeat_latency_ms = float("inf")

        # Message throughput (simulated - would read from actual metrics)
        metrics.message_throughput_per_min = 12.0

        # Evolution status — read from persisted summary.json
        _evolution_status = "unknown"
        _summary_path = Path("/sandbox/.openclaw/milimo/state/evolution/summary.json")
        if _summary_path.exists():
            try:
                _summary = json.loads(_summary_path.read_text())
                _role_data = _summary.get("by_role", {}).get(role, {})
                _last_stage = _role_data.get("last_stage")
                if _last_stage == "deploy":
                    _evolution_status = "success"
                elif _last_stage == "error":
                    _evolution_status = "error"
                elif _last_stage is not None:
                    _evolution_status = "incomplete"
                elif role in _summary.get("by_role", {}):
                    _evolution_status = "unknown"
                else:
                    _evolution_status = "never_run"
            except (json.JSONDecodeError, OSError):
                pass
        else:
            _evolution_status = "never_run"
        metrics.evolution_status = _evolution_status

        # Approval backlog (would read from War Room)
        metrics.approval_backlog = 3

        # Error rate (would read from error log)
        metrics.error_rate_per_hour = 1.0

        return metrics

    def _calculate_health_scores(self) -> None:
        """Calculate health scores for all claws."""
        topology = self.mesh.topology

        with self._lock:
            for role, metrics in self._metrics.items():
                score = HealthScorer.calculate_score(metrics)
                node = topology.get(role)

                offline = False
                region = ""
                last_heartbeat = ""

                if node:
                    if hasattr(node, "status"):
                        offline = node.status == "offline"
                    if hasattr(node, "address"):
                        region = self._extract_region(node.address)
                    if hasattr(node, "last_heartbeat"):
                        last_heartbeat = node.last_heartbeat

                status = HealthScorer.score_to_status(score, offline)

                self._health[role] = ClawHealth(
                    role=role,
                    status=status,
                    score=score,
                    metrics=metrics,
                    region=region,
                    squad_id=self.mesh.squad_id,
                    last_heartbeat=last_heartbeat,
                )

    def _extract_region(self, address: str) -> str:
        """Extract region from address."""
        if "us-east" in address:
            return "us-east-1"
        elif "eu-west" in address:
            return "eu-west-1"
        elif "ap-southeast" in address:
            return "ap-southeast-1"
        elif "us-west" in address:
            return "us-west-2"
        return "unknown"

    def _check_alerts(self) -> None:
        """Check for health alerts."""
        new_alerts = []

        with self._lock:
            for role, health in self._health.items():
                if health.status == HealthStatus.CRITICAL:
                    new_alerts.append(
                        {
                            "role": role,
                            "level": "critical",
                            "message": f"{role} is in critical condition (score: {health.score})",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                elif health.status == HealthStatus.DEGRADED:
                    new_alerts.append(
                        {
                            "role": role,
                            "level": "warning",
                            "message": f"{role} is degraded (score: {health.score})",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                elif health.status == HealthStatus.OFFLINE:
                    new_alerts.append(
                        {
                            "role": role,
                            "level": "critical",
                            "message": f"{role} is offline",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        self._alerts = new_alerts

    def _save_health_data(self) -> None:
        """Save health data to disk."""
        health_file = self._storage_dir / "health.json"

        with self._lock:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "squad_id": self.mesh.squad_id,
                "claws": {
                    role: health.to_dict() for role, health in self._health.items()
                },
                "alerts": self._alerts,
            }

        try:
            health_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save health data: %s", e)

    def get_claw_health(self, role: str) -> Optional[ClawHealth]:
        """Get health for a specific claw."""
        with self._lock:
            return self._health.get(role)

    def get_squad_health(self) -> SquadHealth:
        """Get health for the entire squad."""
        with self._lock:
            claws = list(self._health.values())
            scores = [h.score for h in claws if h.status != HealthStatus.OFFLINE]

            overall_score = sum(scores) / len(scores) if scores else 0.0
            overall_status = HealthScorer.score_to_status(overall_score)

            return SquadHealth(
                squad_id=self.mesh.squad_id,
                overall_score=round(overall_score, 1),
                overall_status=overall_status,
                claws=claws,
                alerts=self._alerts.copy(),
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

    def get_metrics(self, role: str) -> Optional[ClawHealthMetrics]:
        """Get metrics for a specific claw."""
        with self._lock:
            return self._metrics.get(role)

    def get_alerts(self) -> list[dict[str, Any]]:
        """Get current alerts."""
        with self._lock:
            return self._alerts.copy()

    def collect_once(self, role: str) -> Optional[ClawHealthMetrics]:
        """Perform a single collection for a claw."""
        topology = self.mesh.topology
        node = topology.get(role)
        if node:
            return self._collect_claw_metrics(role, node)
        return None


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "HealthStatus",
    "MetricSample",
    "ClawHealthMetrics",
    "ClawHealth",
    "SquadHealth",
    "HealthScorer",
    "HealthCollector",
]
