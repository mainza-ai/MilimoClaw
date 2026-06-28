# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Signal Processor

Processes and stores all inbound signals from other claws.
Validates message schema against contracts, routes to correct handlers,
and triggers anomaly detection on performance signals.
"""

from __future__ import annotations

import json
import logging
import uuid
import fcntl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
)

logger = logging.getLogger("milimo.signal_processor")


class SignalValidationError(Exception):
    """Raised when a signal fails schema validation."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


@dataclass
class InboundSignal:
    """Represents a processed inbound signal."""

    signal_id: str
    message_type: str
    source_claw: str
    received_at: str
    payload: dict[str, Any]
    stored_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "message_type": self.message_type,
            "source_claw": self.source_claw,
            "received_at": self.received_at,
            "payload": self.payload,
            "stored_path": str(self.stored_path) if self.stored_path else None,
        }


@dataclass
class SignalSchema:
    """Schema definition for validating inbound signals."""

    message_type: str
    allowed_senders: list[str]
    required_payload_fields: list[str]
    optional_payload_fields: list[str] = field(default_factory=list)


SIGNAL_SCHEMAS: dict[str, SignalSchema] = {
    "performance_signal": SignalSchema(
        message_type="performance_signal",
        allowed_senders=["content"],
        required_payload_fields=[
            "post_id",
            "platform",
            "engagement_data",
            "publish_time",
            "content_type",
        ],
        optional_payload_fields=["client_id"],
    ),
    "client_health_signal": SignalSchema(
        message_type="client_health_signal",
        allowed_senders=["ops"],
        required_payload_fields=["client_id", "health_score"],
        optional_payload_fields=["health_factors", "recommended_action"],
    ),
    "client_onboarded": SignalSchema(
        message_type="client_onboarded",
        allowed_senders=["ops"],
        required_payload_fields=[
            "client_id",
            "niche",
            "project_type",
            "estimated_value",
        ],
        optional_payload_fields=["onboarded_at"],
    ),
    "revenue_summary": SignalSchema(
        message_type="revenue_summary",
        allowed_senders=["finance"],
        required_payload_fields=["week_total", "week_over_week_pct"],
        optional_payload_fields=["invoices_paid", "invoices_pending", "pipeline_value"],
    ),
    "shipping_summary": SignalSchema(
        message_type="shipping_summary",
        allowed_senders=["build"],
        required_payload_fields=["prs_merged", "deploys"],
        optional_payload_fields=[
            "issues_closed",
            "velocity_delta",
            "avg_pr_cycle_hours",
        ],
    ),
    "content_performance_query": SignalSchema(
        message_type="content_performance_query",
        allowed_senders=["content"],
        required_payload_fields=["query"],
        optional_payload_fields=["lookback_days", "platform"],
    ),
    "behavior_query": SignalSchema(
        message_type="behavior_query",
        allowed_senders=["build"],
        required_payload_fields=["query"],
        optional_payload_fields=["feature_id", "lookback_days"],
    ),
}


class SignalProcessor:
    """
    Processes and stores all inbound signals from other claws.

    Validates message schema, routes to correct handlers, triggers
    anomaly detection on content performance signals, and dispatches
    client health alerts immediately when score < 6.0.
    """

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
        alert_dispatcher: Callable[[str, str, dict], None] | None = None,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log
        self.alert_dispatcher = alert_dispatcher

    def process(self, raw_message: dict[str, Any]) -> InboundSignal:
        """
        Process an inbound message.

        Validates schema, routes to correct handler, logs receipt.
        Raises SignalValidationError on schema violations.
        """
        message_type = raw_message.get("message_type")
        if not message_type:
            raise SignalValidationError("Missing message_type field", "message_type")

        schema = SIGNAL_SCHEMAS.get(message_type)
        if not schema:
            raise SignalValidationError(
                f"Unknown message_type: {message_type}", "message_type"
            )

        sender = raw_message.get("sender_role")
        if sender not in schema.allowed_senders:
            raise SignalValidationError(
                f"Sender '{sender}' not allowed for {message_type}. Allowed: {schema.allowed_senders}",
                "sender_role",
            )

        payload = raw_message.get("payload", {})
        for required_field in schema.required_payload_fields:
            if required_field not in payload:
                raise SignalValidationError(
                    f"Missing required payload field: {required_field}",
                    f"payload.{required_field}",
                )

        signal_id = raw_message.get("message_id") or str(uuid.uuid4())[:12]
        received_at = (
            raw_message.get("timestamp") or datetime.now(timezone.utc).isoformat()
        )

        signal = InboundSignal(
            signal_id=signal_id,
            message_type=message_type,
            source_claw=sender,
            received_at=received_at,
            payload=payload,
        )

        handler_map: dict[str, Callable[[InboundSignal], None]] = {
            "performance_signal": self.handle_performance_signal,
            "client_health_signal": self.handle_client_health_signal,
            "client_onboarded": self.handle_client_onboarded,
            "revenue_summary": self.handle_revenue_summary,
            "shipping_summary": self.handle_shipping_summary,
        }

        handler = handler_map.get(message_type)
        if handler:
            handler(signal)
        else:
            logger.warning("No handler for message_type: %s", message_type)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type=f"{message_type}_received",
                entity_id=signal_id,
                source_claw=sender,
                outcome="success",
                details={
                    "stored_path": str(signal.stored_path)
                    if signal.stored_path
                    else None
                },
            )
        )

        return signal

    def handle_performance_signal(self, signal: InboundSignal | dict[str, Any]) -> None:
        """Handle performance_signal from Content Claw."""
        if isinstance(signal, dict):
            signal = InboundSignal(
                signal_id=str(uuid.uuid4()),
                message_type="performance_signal",
                source_claw=signal.get("sender_role", "unknown"),
                received_at=signal.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                payload=signal.get("payload", signal),
            )
        platform = signal.payload.get("platform", "unknown")
        publish_time = signal.payload.get("publish_time", "")

        try:
            month_str = (
                publish_time[:7]
                if publish_time
                else datetime.now(timezone.utc).strftime("%Y-%m")
            )
        except Exception:
            month_str = datetime.now(timezone.utc).strftime("%Y-%m")

        path = self.fs.get_data_path(
            "content-performance", f"{platform}/{month_str}/performance.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "signal_id": signal.signal_id,
            "received_at": signal.received_at,
            **signal.payload,
        }
        self._append_jsonl(path, record)
        signal.stored_path = path

        logger.info(
            "Stored performance_signal %s from %s at %s",
            signal.signal_id,
            signal.source_claw,
            path,
        )

    def handle_client_health_signal(
        self, signal: InboundSignal | dict[str, Any]
    ) -> None:
        """Handle client_health_signal from Ops Claw. Dispatches alert if score < 6.0."""
        if isinstance(signal, dict):
            signal = InboundSignal(
                signal_id=str(uuid.uuid4()),
                message_type="client_health_signal",
                source_claw=signal.get("sender_role", "unknown"),
                received_at=signal.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                payload=signal.get("payload", signal),
            )
        client_id = signal.payload.get("client_id", "unknown")
        health_score = signal.payload.get("health_score", 0)

        path = self.fs.get_data_path(
            "client-health", f"{client_id}/health-history.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "signal_id": signal.signal_id,
            "received_at": signal.received_at,
            **signal.payload,
        }
        self._append_jsonl(path, record)
        signal.stored_path = path

        logger.info(
            "Stored client_health_signal %s for client %s (score: %.1f)",
            signal.signal_id,
            client_id,
            health_score,
        )

        if health_score < 6.0 and self.alert_dispatcher:
            self.alert_dispatcher(
                "client_health_alert",
                "ops",
                {
                    "client_id": client_id,
                    "health_score": health_score,
                    "risk_factors": signal.payload.get("health_factors", []),
                    "recommended_action": signal.payload.get("recommended_action", ""),
                },
            )
            logger.warning(
                "Dispatched client_health_alert for client %s (score: %.1f < 6.0)",
                client_id,
                health_score,
            )

    def handle_client_onboarded(self, signal: InboundSignal | dict[str, Any]) -> None:
        """Handle client_onboarded from Ops Claw. Creates initial health entry."""
        if isinstance(signal, dict):
            signal = InboundSignal(
                signal_id=str(uuid.uuid4()),
                message_type="client_onboarded",
                source_claw=signal.get("sender_role", "unknown"),
                received_at=signal.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                payload=signal.get("payload", signal),
            )
        client_id = signal.payload.get("client_id", "unknown")

        path = self.fs.get_data_path(
            "client-health", f"{client_id}/health-history.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "signal_id": signal.signal_id,
            "received_at": signal.received_at,
            "event_type": "onboarded",
            **signal.payload,
        }
        self._append_jsonl(path, record)
        signal.stored_path = path

        logger.info(
            "Stored client_onboarded for client %s",
            client_id,
        )

    def handle_revenue_summary(self, signal: InboundSignal | dict[str, Any]) -> None:
        """Handle revenue_summary from Finance Claw."""
        if isinstance(signal, dict):
            signal = InboundSignal(
                signal_id=str(uuid.uuid4()),
                message_type="revenue_summary",
                source_claw=signal.get("sender_role", "unknown"),
                received_at=signal.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                payload=signal.get("payload", signal),
            )
        path = self.fs.get_data_path("revenue", "weekly-revenue.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "signal_id": signal.signal_id,
            "received_at": signal.received_at,
            **signal.payload,
        }
        self._append_jsonl(path, record)
        signal.stored_path = path

        logger.info(
            "Stored revenue_summary %s",
            signal.signal_id,
        )

    def handle_shipping_summary(self, signal: InboundSignal | dict[str, Any]) -> None:
        """Handle shipping_summary from Build Claw."""
        if isinstance(signal, dict):
            signal = InboundSignal(
                signal_id=str(uuid.uuid4()),
                message_type="shipping_summary",
                source_claw=signal.get("sender_role", "unknown"),
                received_at=signal.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                ),
                payload=signal.get("payload", signal),
            )
        path = self.fs.get_data_path("delivery-velocity", "velocity.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "signal_id": signal.signal_id,
            "received_at": signal.received_at,
            **signal.payload,
        }
        self._append_jsonl(path, record)
        signal.stored_path = path

        logger.info(
            "Stored shipping_summary %s",
            signal.signal_id,
        )

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        """Thread-safe append to JSONL file using file locking."""
        with open(path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(record) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _get_jsonl_path(
        self,
        data_type: Literal[
            "content-performance", "client-health", "revenue", "delivery-velocity"
        ],
        sub_keys: list[str],
    ) -> Path:
        """Build correct path for JSONL storage."""
        path = self.fs.get_data_path(data_type)
        for key in sub_keys:
            path = path / key
        return path
