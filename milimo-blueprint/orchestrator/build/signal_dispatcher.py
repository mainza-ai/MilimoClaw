#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Signal Dispatcher

Sends all outbound messages from the Build Claw to other claws.
Receives and routes inbound messages from other claws.
All sends go through the inter-claw mesh gateway.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .build_init import BuildFilesystemInit, BuildOperationalLog

logger = logging.getLogger("milimo.build")

ANALYTICS_WAIT_SECONDS = 300  # 5 minutes


@dataclass
class BehaviorQueryResponse:
    """Response from Analytics Claw to behavior_query."""

    message_id: str
    query: str
    feature_data: dict[str, Any]
    retention_correlation: dict[str, float]
    recommendations: list[str]
    data_quality: str
    timestamp: str


@dataclass
class PendingBehaviorQuery:
    """Tracks a pending behavior_query awaiting response."""

    message_id: str
    query: str
    sent_at: str
    callback: Callable[[BehaviorQueryResponse], None] | None = None


class BuildSignalDispatcher:
    """
    Sends all outbound messages from the Build Claw to other claws.
    Receives and routes inbound messages from other claws.
    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to operational.log.
    Never raises on dispatch failure — logs error and continues.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        operational_log: BuildOperationalLog,
        mesh_gateway: Any | None = None,
        squad_id: str = "default",
    ):
        self._fs = fs
        self._log = operational_log
        self._gateway = mesh_gateway
        self._squad_id = squad_id
        self._pending_behavior_queries: dict[str, PendingBehaviorQuery] = {}
        self._retention_signals: dict[str, Any] | None = None
        self._shipping_accumulator: dict[str, Any] = {}
        self._feature_brief_handlers: list[Callable[[dict], None]] = []
        self._retention_signal_handlers: list[Callable[[dict], None]] = []
        self._behavior_query_response_handlers: list[Callable[[dict], None]] = []

    def send_deploy_complete(
        self,
        project_id: str,
        deploy_url: str,
        version: str,
        deployed_at: str,
    ) -> None:
        payload = {
            "deploy_id": f"deploy-{uuid.uuid4().hex[:8]}",
            "project_id": project_id,
            "version": version,
            "deployed_at": deployed_at,
            "environment": "production",
            "deploy_url": deploy_url,
        }
        self._send("deploy_complete", "ops", payload)
        self._log.append(
            self._create_log_entry(
                action_type="deploy_complete_sent",
                entity_id=payload["deploy_id"],
                outcome="success",
                details={"project_id": project_id, "version": version},
            )
        )

    def send_shipping_summary(
        self,
        week_of: str,
        prs_merged: int,
        issues_resolved: int,
        features_shipped: list[str],
        notable_changes: list[str],
    ) -> None:
        payload = {
            "summary": {
                "week_of": week_of,
                "prs_merged": prs_merged,
                "issues_resolved": issues_resolved,
                "features_shipped": features_shipped,
                "notable_changes": notable_changes,
            },
            "week_end": week_of,
        }
        self._send("shipping_summary", "content", payload)
        self._log.append(
            self._create_log_entry(
                action_type="shipping_summary_sent",
                entity_id=f"week-{week_of}",
                outcome="success",
                details={
                    "prs_merged": prs_merged,
                    "issues_resolved": issues_resolved,
                },
            )
        )

    def send_behavior_query(
        self,
        query: str,
        lookback_days: int = 7,
        feature_ids: list[str] | None = None,
    ) -> str:
        message_id = uuid.uuid4().hex[:12]
        payload = {
            "query": query,
            "time_range": f"{lookback_days}d",
            "feature_id": feature_ids[0] if feature_ids else None,
        }
        if feature_ids and len(feature_ids) > 1:
            payload["feature_ids"] = feature_ids

        self._send("behavior_query", "analytics", payload, message_id=message_id)

        pending = PendingBehaviorQuery(
            message_id=message_id,
            query=query,
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        self._pending_behavior_queries[message_id] = pending

        self._log.append(
            self._create_log_entry(
                action_type="behavior_query_sent",
                entity_id=message_id,
                outcome="success",
                details={"query": query, "lookback_days": lookback_days},
            )
        )

        return message_id

    def handle_feature_brief(self, message: dict) -> None:
        self._validate_message(message, "feature_brief")

        self._log.append(
            self._create_log_entry(
                action_type="feature_brief_received",
                entity_id=message.get("message_id", "unknown"),
                outcome="success",
                details={
                    "project_id": message.get("payload", {}).get("project_id"),
                    "feature_name": message.get("payload", {}).get("feature_name"),
                },
            )
        )

        for handler in self._feature_brief_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error("Feature brief handler failed: %s", e)

    def send_feature_brief_acknowledged(
        self,
        project_id: str,
        estimated_start: str,
        clarity_score: str,
    ) -> None:
        if clarity_score not in ("clear", "low"):
            raise ValueError(f"Invalid clarity_score: {clarity_score}. Must be 'clear' or 'low'")

        payload = {
            "project_id": project_id,
            "estimated_start": estimated_start,
            "clarity_score": clarity_score,
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        }
        self._send("brief_acknowledged", "ops", payload)
        self._log.append(
            self._create_log_entry(
                action_type="feature_brief_acknowledged",
                entity_id=project_id,
                outcome="success",
                details={"clarity_score": clarity_score},
            )
        )

    def handle_retention_signals(self, message: dict) -> None:
        self._validate_message(message, "retention_signals")

        self._retention_signals = message.get("payload", {})

        signals_path = self._fs._base / "context" / "sprint" / "retention-signals.json"
        self._fs.atomic_write_json(signals_path, {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "signals": message.get("payload", {}),
        })

        self._log.append(
            self._create_log_entry(
                action_type="retention_signals_received",
                entity_id=message.get("message_id", "unknown"),
                outcome="success",
                details={"signal_type": message.get("payload", {}).get("signal_type")},
            )
        )

        for handler in self._retention_signal_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error("Retention signal handler failed: %s", e)

    def handle_behavior_query_response(self, message: dict) -> None:
        self._validate_message(message, "response")

        message_id = message.get("message_id", "")
        if message_id in self._pending_behavior_queries:
            pending = self._pending_behavior_queries.pop(message_id)
            response = BehaviorQueryResponse(
                message_id=message_id,
                query=pending.query,
                feature_data=message.get("payload", {}).get("feature_data", {}),
                retention_correlation=message.get("payload", {}).get("retention_correlation", {}),
                recommendations=message.get("payload", {}).get("recommendations", []),
                data_quality=message.get("payload", {}).get("data_quality", "unknown"),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            if pending.callback:
                pending.callback(response)

        self._log.append(
            self._create_log_entry(
                action_type="behavior_query_response_received",
                entity_id=message_id,
                outcome="success",
                details={"query": message.get("payload", {}).get("query")},
            )
        )

        for handler in self._behavior_query_response_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error("Behavior query response handler failed: %s", e)

    def get_retention_signals(self) -> dict[str, Any] | None:
        return self._retention_signals

    def has_pending_behavior_query(self) -> bool:
        return len(self._pending_behavior_queries) > 0

    def get_pending_query_age_seconds(self) -> float | None:
        if not self._pending_behavior_queries:
            return None
        oldest = min(
            self._pending_behavior_queries.values(),
            key=lambda q: q.sent_at,
        )
        sent_time = datetime.fromisoformat(oldest.sent_at)
        elapsed = datetime.now(timezone.utc) - sent_time
        return elapsed.total_seconds()

    def register_feature_brief_handler(self, handler: Callable[[dict], None]) -> None:
        self._feature_brief_handlers.append(handler)

    def register_retention_signal_handler(self, handler: Callable[[dict], None]) -> None:
        self._retention_signal_handlers.append(handler)

    def register_behavior_query_response_handler(
        self, handler: Callable[[dict], None]
    ) -> None:
        self._behavior_query_response_handlers.append(handler)

    def accumulate_shipping_data(
        self,
        pr_id: str,
        issue_number: int,
        feature_name: str,
        changes: list[str],
    ) -> None:
        week_of = datetime.now(timezone.utc).strftime("%Y-W%W")
        if week_of not in self._shipping_accumulator:
            self._shipping_accumulator[week_of] = {
                "prs_merged": 0,
                "issues_resolved": set(),
                "features_shipped": [],
                "notable_changes": [],
            }

        self._shipping_accumulator[week_of]["prs_merged"] += 1
        self._shipping_accumulator[week_of]["issues_resolved"].add(issue_number)
        if feature_name:
            self._shipping_accumulator[week_of]["features_shipped"].append(feature_name)
        self._shipping_accumulator[week_of]["notable_changes"].extend(changes)

    def get_accumulated_shipping_summary(self, week_of: str | None = None) -> dict[str, Any]:
        if week_of is None:
            week_of = datetime.now(timezone.utc).strftime("%Y-W%W")

        if week_of not in self._shipping_accumulator:
            return {
                "week_of": week_of,
                "prs_merged": 0,
                "issues_resolved": 0,
                "features_shipped": [],
                "notable_changes": [],
            }

        data = self._shipping_accumulator[week_of]
        return {
            "week_of": week_of,
            "prs_merged": data["prs_merged"],
            "issues_resolved": len(data["issues_resolved"]),
            "features_shipped": data["features_shipped"],
            "notable_changes": data["notable_changes"],
        }

    def _send(
        self,
        message_type: str,
        recipient_role: str,
        payload: dict[str, Any],
        message_id: str | None = None,
    ) -> None:
        message = {
            "message_id": message_id or uuid.uuid4().hex[:12],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender_role": "build",
            "recipient_role": recipient_role,
            "message_type": message_type,
            "squad_id": self._squad_id,
            "payload": payload,
        }

        try:
            if self._gateway:
                self._gateway.send(message)
            else:
                logger.debug("No gateway configured, message logged only: %s", message_type)
        except Exception as e:
            logger.error("Failed to send %s to %s: %s", message_type, recipient_role, e)

    def _validate_message(self, message: dict, expected_type: str) -> None:
        if not isinstance(message, dict):
            raise ValueError(f"Message must be a dict, got {type(message)}")

        message_type = message.get("message_type")
        if message_type != expected_type:
            raise ValueError(
                f"Expected message_type '{expected_type}', got '{message_type}'"
            )

        if "payload" not in message:
            raise ValueError("Message missing required 'payload' field")

    def _create_log_entry(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        details: dict[str, Any],
    ):
        from .build_init import BuildLogEntry

        return BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )
