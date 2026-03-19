#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Latency Monitor

Tracks inter-region latency for mesh routing decisions. Provides
continuous latency measurement, historical data aggregation, and
routing recommendations.

Usage:
    from orchestrator.latency_monitor import LatencyMonitor, LatencySample

    monitor = LatencyMonitor(region="us-east-1")
    monitor.start()

    latency = monitor.get_latency("eu-west-1")
    print(f"Latency to eu-west-1: {latency:.2f}ms")
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import urllib.request
import urllib.error

import yaml

logger = logging.getLogger("milimo.latency_monitor")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class LatencySample:
    """A single latency measurement."""

    source_region: str
    target_region: str
    latency_ms: float
    timestamp: str
    packet_loss: float = 0.0
    jitter_ms: float = 0.0
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_region": self.source_region,
            "target_region": self.target_region,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "packet_loss": self.packet_loss,
            "jitter_ms": self.jitter_ms,
            "success": self.success,
        }


@dataclass
class LatencyStats:
    """Aggregated latency statistics for a region pair."""

    source_region: str
    target_region: str
    min_ms: float = float("inf")
    max_ms: float = 0.0
    mean_ms: float = 0.0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    std_dev: float = 0.0
    packet_loss_rate: float = 0.0
    sample_count: int = 0
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_region": self.source_region,
            "target_region": self.target_region,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "std_dev": self.std_dev,
            "packet_loss_rate": self.packet_loss_rate,
            "sample_count": self.sample_count,
            "last_updated": self.last_updated,
        }


@dataclass
class LatencyMatrix:
    """Latency matrix between all regions."""

    timestamp: str
    regions: list[str]
    matrix: dict[str, dict[str, float]]

    def get(self, source: str, target: str) -> Optional[float]:
        """Get latency between two regions."""
        return self.matrix.get(source, {}).get(target)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "regions": self.regions,
            "matrix": self.matrix,
        }


# ---------------------------------------------------------------------------
# Latency Monitor
# ---------------------------------------------------------------------------

class LatencyMonitor:
    """
    Monitors inter-region latency for mesh routing.

    Features:
    - Continuous background probing
    - Historical data aggregation
    - Latency matrix generation
    - Alert on degradation
    """

    DEFAULT_REGIONS = [
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "eu-central-1",
        "ap-southeast-1",
        "ap-northeast-1",
        "sa-east-1",
    ]

    def __init__(
        self,
        region: str,
        target_regions: Optional[list[str]] = None,
        probe_interval_ms: int = 30000,
        sample_window: int = 10,
        storage_dir: Optional[str] = None,
        probe_timeout_ms: int = 5000,
    ) -> None:
        self.region = region
        self.target_regions = target_regions or self.DEFAULT_REGIONS.copy()
        if region in self.target_regions:
            self.target_regions.remove(region)

        self.probe_interval_ms = probe_interval_ms
        self.sample_window = sample_window
        self.probe_timeout_ms = probe_timeout_ms

        self._samples: dict[str, list[LatencySample]] = {r: [] for r in self.target_regions}
        self._stats: dict[str, LatencyStats] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        if storage_dir:
            self._storage_dir = Path(storage_dir)
            self._storage_dir.mkdir(parents=True, exist_ok=True)
        else:
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            self._storage_dir = Path(home) / ".milimo" / "latency"
            self._storage_dir.mkdir(parents=True, exist_ok=True)

        self._load_historical_data()

    def start(self) -> None:
        """Start background latency monitoring."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Latency monitor started for region: %s", self.region)

    def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Latency monitor stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            self._probe_all_targets()
            self._save_historical_data()

            interval_seconds = self.probe_interval_ms / 1000
            for _ in range(int(interval_seconds)):
                if not self._running:
                    break
                time.sleep(1)

    def _probe_all_targets(self) -> None:
        """Probe latency to all target regions."""
        for target in self.target_regions:
            sample = self._probe_region(target)
            if sample:
                self._add_sample(target, sample)

    def _probe_region(self, target_region: str) -> Optional[LatencySample]:
        """Probe latency to a specific region."""
        endpoint = self._get_probe_endpoint(target_region)

        samples = []
        for _ in range(3):
            start_time = time.time()
            try:
                request = urllib.request.Request(endpoint, method="HEAD")
                request.add_header("User-Agent", "MilimoClaw-LatencyMonitor/1.0")

                response = urllib.request.urlopen(request, timeout=self.probe_timeout_ms / 1000)
                latency_ms = (time.time() - start_time) * 1000

                if response.status < 400:
                    samples.append(latency_ms)

            except (urllib.error.URLError, Exception) as e:
                logger.debug("Probe failed for %s: %s", target_region, e)

        if not samples:
            return LatencySample(
                source_region=self.region,
                target_region=target_region,
                latency_ms=float("inf"),
                timestamp=datetime.now(timezone.utc).isoformat(),
                packet_loss=1.0,
                success=False,
            )

        return LatencySample(
            source_region=self.region,
            target_region=target_region,
            latency_ms=statistics.mean(samples),
            timestamp=datetime.now(timezone.utc).isoformat(),
            jitter_ms=statistics.stdev(samples) if len(samples) > 1 else 0.0,
            packet_loss=1.0 - (len(samples) / 3),
            success=True,
        )

    def _get_probe_endpoint(self, region: str) -> str:
        """Get probe endpoint for a region."""
        endpoints = {
            "us-east-1": "https://us-east-1.endpoint.milimo.dev/health",
            "us-west-2": "https://us-west-2.endpoint.milimo.dev/health",
            "eu-west-1": "https://eu-west-1.endpoint.milimo.dev/health",
            "eu-central-1": "https://eu-central-1.endpoint.milimo.dev/health",
            "ap-southeast-1": "https://ap-southeast-1.endpoint.milimo.dev/health",
            "ap-northeast-1": "https://ap-northeast-1.endpoint.milimo.dev/health",
            "sa-east-1": "https://sa-east-1.endpoint.milimo.dev/health",
        }
        return endpoints.get(region, f"https://{region}.endpoint.milimo.dev/health")

    def _add_sample(self, target: str, sample: LatencySample) -> None:
        """Add a latency sample."""
        with self._lock:
            if target not in self._samples:
                self._samples[target] = []

            self._samples[target].append(sample)

            if len(self._samples[target]) > self.sample_window:
                self._samples[target] = self._samples[target][-self.sample_window:]

            self._update_stats(target)

    def _update_stats(self, target: str) -> None:
        """Update aggregated statistics for a target."""
        samples = self._samples.get(target, [])
        if not samples:
            return

        successful = [s for s in samples if s.success]
        if not successful:
            return

        latencies = [s.latency_ms for s in successful]
        latencies_sorted = sorted(latencies)

        packet_losses = [s.packet_loss for s in samples]

        stats = LatencyStats(
            source_region=self.region,
            target_region=target,
            min_ms=min(latencies),
            max_ms=max(latencies),
            mean_ms=statistics.mean(latencies),
            median_ms=statistics.median(latencies),
            p95_ms=self._percentile(latencies_sorted, 95),
            p99_ms=self._percentile(latencies_sorted, 99),
            std_dev=statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            packet_loss_rate=statistics.mean(packet_losses),
            sample_count=len(samples),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        self._stats[target] = stats

    def _percentile(self, sorted_data: list[float], percentile: float) -> float:
        """Calculate percentile of sorted data."""
        if not sorted_data:
            return 0.0

        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(math.floor(index))
        upper = int(math.ceil(index))

        if lower == upper:
            return sorted_data[lower]

        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def get_latency(self, target_region: str) -> float:
        """Get current latency to a region (median)."""
        with self._lock:
            stats = self._stats.get(target_region)
            if stats:
                return stats.median_ms

            samples = self._samples.get(target_region, [])
            successful = [s for s in samples if s.success]
            if successful:
                return statistics.mean([s.latency_ms for s in successful])

            return float("inf")

    def get_stats(self, target_region: str) -> Optional[LatencyStats]:
        """Get aggregated statistics for a region."""
        with self._lock:
            return self._stats.get(target_region)

    def get_matrix(self) -> LatencyMatrix:
        """Get latency matrix from this region to all targets."""
        matrix: dict[str, dict[str, float]] = {self.region: {}}

        for target in self.target_regions:
            matrix[self.region][target] = self.get_latency(target)

        return LatencyMatrix(
            timestamp=datetime.now(timezone.utc).isoformat(),
            regions=[self.region] + self.target_regions,
            matrix=matrix,
        )

    def get_optimal_route(self, final_target: str, intermediate_regions: Optional[list[str]] = None) -> list[str]:
        """
        Find optimal route to a target region.

        Args:
            final_target: Destination region
            intermediate_regions: Optional intermediate hops

        Returns:
            List of regions in routing order
        """
        candidates = intermediate_regions or self.target_regions.copy()
        if final_target not in candidates:
            candidates.append(final_target)

        if final_target == self.region:
            return [self.region]

        direct_latency = self.get_latency(final_target)
        if direct_latency < 500:
            return [self.region, final_target]

        best_intermediate = None
        best_total_latency = direct_latency

        for intermediate in candidates:
            if intermediate == final_target or intermediate == self.region:
                continue

            to_intermediate = self.get_latency(intermediate)
            if to_intermediate == float("inf"):
                continue

            from_intermediate_stats = self._stats.get(intermediate)
            if from_intermediate_stats:
                from_intermediate = self.get_latency(final_target) * 0.8
            else:
                from_intermediate = direct_latency * 0.9

            total = to_intermediate + from_intermediate
            if total < best_total_latency:
                best_total_latency = total
                best_intermediate = intermediate

        if best_intermediate:
            return [self.region, best_intermediate, final_target]

        return [self.region, final_target]

    def is_region_healthy(self, target_region: str, max_latency_ms: float = 500.0) -> bool:
        """Check if a region is healthy (acceptable latency)."""
        latency = self.get_latency(target_region)
        if latency == float("inf"):
            return False

        stats = self._stats.get(target_region)
        if stats and stats.packet_loss_rate > 0.1:
            return False

        return latency < max_latency_ms

    def _load_historical_data(self) -> None:
        """Load historical latency data from disk."""
        history_file = self._storage_dir / f"latency_{self.region}.json"
        if not history_file.exists():
            return

        try:
            data = json.loads(history_file.read_text())
            for target, samples_data in data.get("samples", {}).items():
                samples = [LatencySample(**s) for s in samples_data]
                self._samples[target] = samples[-self.sample_window:]

            logger.debug("Loaded historical latency data for %s", self.region)

        except Exception as e:
            logger.warning("Failed to load historical data: %s", e)

    def _save_historical_data(self) -> None:
        """Save latency data to disk."""
        history_file = self._storage_dir / f"latency_{self.region}.json"

        with self._lock:
            samples_data = {
                target: [s.to_dict() for s in samples]
                for target, samples in self._samples.items()
            }

        data = {
            "region": self.region,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "samples": samples_data,
        }

        try:
            history_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save historical data: %s", e)

    def probe_once(self, target_region: str) -> Optional[LatencySample]:
        """Perform a single probe to a region (non-background)."""
        return self._probe_region(target_region)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "LatencySample",
    "LatencyStats",
    "LatencyMatrix",
    "LatencyMonitor",
]
