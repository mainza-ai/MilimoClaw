#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Performance Metrics Collector

Shared module for all claws to write performance metrics.
These metrics are read by the Evolution Cycle for analysis
and continuous improvement.

Each claw writes metrics to:
    ~/.milimo/metrics/{claw_role}/metrics.jsonl

Metrics tracked:
- Messages processed (count, avg processing time)
- Errors (count, types)
- Inference calls (count, tokens, latency)
- SLA compliance (on-time vs late)
- Resource usage (memory, CPU — if available)
"""

from __future__ import annotations

import json
import logging
import os
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("milimo.metrics")


@dataclass
class MetricEntry:
    """A single performance metric entry."""
    timestamp: str
    claw_role: str
    metric_type: str
    value: float | int
    unit: str = ""
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "timestamp": self.timestamp,
            "claw_role": self.claw_role,
            "metric_type": self.metric_type,
            "value": self.value,
        }
        if self.unit:
            result["unit"] = self.unit
        if self.tags:
            result["tags"] = self.tags
        return result


class MetricsCollector:
    """
    Thread-safe performance metrics collector.

    Each claw should have its own instance, writing to its own
    metrics directory.
    """

    def __init__(self, claw_role: str, metrics_dir: Path | None = None) -> None:
        self.claw_role = claw_role
        self.metrics_dir = metrics_dir or Path.home() / ".milimo" / "metrics" / claw_role
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._timings: dict[str, list[float]] = {}
        self._errors: dict[str, int] = {}

    def record_message_processed(self, message_type: str, processing_time_ms: float) -> None:
        """Record a successfully processed message."""
        self._increment_counter("messages_processed")
        self._increment_counter(f"messages.{message_type}")
        self._record_timing(f"latency.{message_type}", processing_time_ms)

        self._write(MetricEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            claw_role=self.claw_role,
            metric_type="message_processed",
            value=processing_time_ms,
            unit="ms",
            tags={"message_type": message_type},
        ))

    def record_error(self, error_type: str, message: str = "") -> None:
        """Record an error occurrence."""
        self._increment_counter("errors")
        self._increment_counter(f"errors.{error_type}")

        self._write(MetricEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            claw_role=self.claw_role,
            metric_type="error",
            value=1,
            tags={"error_type": error_type, "message": message[:200]},
        ))

    def record_inference_call(self, data_type: str, tokens: int, latency_ms: float) -> None:
        """Record an inference API call."""
        self._increment_counter("inference_calls")
        self._increment_counter(f"inference.{data_type}")
        self._increment_counter("inference_tokens", tokens)
        self._record_timing(f"inference_latency.{data_type}", latency_ms)

        self._write(MetricEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            claw_role=self.claw_role,
            metric_type="inference_call",
            value=latency_ms,
            unit="ms",
            tags={"data_type": data_type, "tokens": str(tokens)},
        ))

    def record_sla_compliance(self, message_type: str, sla_ms: float, actual_ms: float) -> None:
        """Record SLA compliance for a message."""
        compliant = actual_ms <= sla_ms
        counter = "sla_compliant" if compliant else "sla_violation"
        self._increment_counter(counter)
        self._increment_counter(f"sla.{message_type}.{counter}")

        self._write(MetricEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            claw_role=self.claw_role,
            metric_type="sla_compliance",
            value=1 if compliant else 0,
            tags={
                "message_type": message_type,
                "sla_ms": str(sla_ms),
                "actual_ms": str(actual_ms),
            },
        ))

    def record_custom(self, metric_type: str, value: float | int, unit: str = "", tags: dict | None = None) -> None:
        """Record a custom metric."""
        self._write(MetricEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            claw_role=self.claw_role,
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags or {},
        ))

    def get_summary(self, lookback_hours: int = 24) -> dict[str, Any]:
        """Get a summary of metrics over the lookback period.

        Reads from persisted JSONL files for cross-process readability.
        Falls back to in-memory counters if no file data exists.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (lookback_hours * 3600)

        # Try to read from persisted JSONL file first (cross-process)
        filepath = self.metrics_dir / "metrics.jsonl"
        persisted_counters: dict[str, int] = {}
        persisted_timings: dict[str, list[float]] = {}

        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            metric_type = record.get("metric_type", "")
                            value = record.get("value", 0)
                            tags = record.get("tags", {})

                            # Reconstruct counters from persisted data
                            if metric_type == "message_processed":
                                persisted_counters["messages_processed"] = persisted_counters.get("messages_processed", 0) + 1
                                msg_type = tags.get("message_type", "unknown")
                                key = f"messages.{msg_type}"
                                persisted_counters[key] = persisted_counters.get(key, 0) + 1
                                timing_key = f"latency.{msg_type}"
                                if timing_key not in persisted_timings:
                                    persisted_timings[timing_key] = []
                                persisted_timings[timing_key].append(float(value))
                            elif metric_type == "error":
                                persisted_counters["errors"] = persisted_counters.get("errors", 0) + 1
                                error_type = tags.get("error_type", "unknown")
                                key = f"errors.{error_type}"
                                persisted_counters[key] = persisted_counters.get(key, 0) + 1
                            elif metric_type == "inference_call":
                                persisted_counters["inference_calls"] = persisted_counters.get("inference_calls", 0) + 1
                                data_type = tags.get("data_type", "unknown")
                                persisted_counters[f"inference.{data_type}"] = persisted_counters.get(f"inference.{data_type}", 0) + 1
                                tokens = int(tags.get("tokens", "0"))
                                persisted_counters["inference_tokens"] = persisted_counters.get("inference_tokens", 0) + tokens
                                timing_key = f"inference_latency.{data_type}"
                                if timing_key not in persisted_timings:
                                    persisted_timings[timing_key] = []
                                persisted_timings[timing_key].append(float(value))
                            elif metric_type == "sla_compliance":
                                compliant = bool(value)
                                counter = "sla_compliant" if compliant else "sla_violation"
                                persisted_counters[counter] = persisted_counters.get(counter, 0) + 1
                                msg_type = tags.get("message_type", "unknown")
                                persisted_counters[f"sla.{msg_type}.{counter}"] = persisted_counters.get(f"sla.{msg_type}.{counter}", 0) + 1
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
            except Exception as e:
                logger.warning("Failed to read persisted metrics: %s", e)

        # Merge in-memory counters with persisted (in-memory takes precedence for current process)
        merged_counters = {**persisted_counters, **self._counters}

        # Merge timings
        merged_timings = {}
        for key in set(list(persisted_timings.keys()) + list(self._timings.keys())):
            persisted = persisted_timings.get(key, [])
            in_memory = self._timings.get(key, [])
            combined = persisted + in_memory
            if combined:
                merged_timings[key] = {
                    "count": len(combined),
                    "avg_ms": round(sum(combined) / len(combined), 2),
                    "min_ms": round(min(combined), 2),
                    "max_ms": round(max(combined), 2),
                    "p95_ms": round(sorted(combined)[int(len(combined) * 0.95)], 2) if len(combined) >= 20 else round(max(combined), 2),
                }

        return {
            "claw_role": self.claw_role,
            "lookback_hours": lookback_hours,
            "counters": merged_counters,
            "timings": merged_timings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _increment_counter(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def _record_timing(self, name: str, value_ms: float) -> None:
        with self._lock:
            if name not in self._timings:
                self._timings[name] = []
            self._timings[name].append(value_ms)

    def _write(self, entry: MetricEntry) -> None:
        """Write a metric entry to the JSONL file."""
        filepath = self.metrics_dir / "metrics.jsonl"
        try:
            with open(filepath, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.warning("Failed to write metric: %s", e)
