# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Build Claw signal dispatcher.

Handles inter-claw communication:
- Outbound signals to Ops, Content, Analytics claws
- Inbound message handling (feature_brief, retention_signals, behavior_query_response)
- Fallback file-based messaging when gateway unavailable
- 10-minute SLA timer for feature brief acknowledgment

Enhancement: Event normalization layer (from Clawhip typed event model).
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from ..milimo_paths import mesh_dir

logger = logging.getLogger(__name__)

# Enhancement: Event normalization constants (from Clawhip)
EVENT_NAMESPACE = "build"

# SLA: 10 minutes for feature brief acknowledgment
FEATURE_BRIEF_SLA_SECONDS = 600

# Wait time for analytics retention signals before sprint planning
ANALYTICS_WAIT_SECONDS = 300


@dataclass
class PendingBehaviorQuery:
    query_id: str
    query: str
    sent_at: str
    lookback_days: int


class BuildSignalDispatcher:
    """Dispatches signals between Build Claw and other claws."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        operational_log: BuildOperationalLog,
        mesh_gateway: Any | None = None,
        squad_id: str = "default",
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._gateway = mesh_gateway
        self._squad_id = squad_id
        self._pending_query: PendingBehaviorQuery | None = None
        self._retention_signals: dict[str, Any] | None = None
        self._shipping_data: list[dict[str, Any]] = []
        self._sla_timers: dict[str, threading.Timer] = {}

    # ------------------------------------------------------------------
    # Outbound signals
    # ------------------------------------------------------------------

    def send_deploy_complete(
        self,
        project_id: str,
        deploy_url: str,
        version: str,
        deployed_at: str,
    ) -> None:
        message = {
            "message_id": f"deploy-complete-{project_id}",
            "sender_role": "build",
            "recipient_role": "ops",
            "message_type": "deploy_complete",
            "payload": {
                "project_id": project_id,
                "deploy_url": deploy_url,
                "version": version,
                "deployed_at": deployed_at,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._send_message(message)
        self._log.append(
            BuildLogEntry(
                timestamp=message["timestamp"],
                action_type="deploy_complete_sent",
                entity_id=project_id,
                outcome="success",
                details={
                    "project_id": project_id,
                    "deploy_url": deploy_url,
                    "version": version,
                },
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
        message = {
            "message_id": f"shipping-summary-{week_of}",
            "sender_role": "build",
            "recipient_role": "content",
            "message_type": "shipping_summary",
            "payload": {
                "week_of": week_of,
                "prs_merged": prs_merged,
                "issues_resolved": issues_resolved,
                "features_shipped": features_shipped,
                "notable_changes": notable_changes,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._send_message(message)
        self._log.append(
            BuildLogEntry(
                timestamp=message["timestamp"],
                action_type="shipping_summary_sent",
                entity_id=week_of,
                outcome="success",
                details={"prs_merged": prs_merged, "issues_resolved": issues_resolved},
            )
        )

    def send_behavior_query(
        self,
        query: str,
        lookback_days: int = 7,
    ) -> str:
        query_id = f"bq-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        message = {
            "message_id": query_id,
            "sender_role": "build",
            "recipient_role": "analytics",
            "message_type": "behavior_query",
            "payload": {
                "query": query,
                "lookback_days": lookback_days,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._pending_query = PendingBehaviorQuery(
            query_id=query_id,
            query=query,
            sent_at=message["timestamp"],
            lookback_days=lookback_days,
        )
        self._send_message(message)
        self._log.append(
            BuildLogEntry(
                timestamp=message["timestamp"],
                action_type="behavior_query_sent",
                entity_id=query_id,
                outcome="success",
                details={"query": query, "lookback_days": lookback_days},
            )
        )
        return query_id

    def send_feature_brief_acknowledged(
        self,
        project_id: str,
        estimated_start: str,
        clarity_score: str,
        missing_elements: list[str] | None = None,
    ) -> None:
        if clarity_score not in ("clear", "low"):
            raise ValueError(
                f"Invalid clarity_score: {clarity_score!r}. Must be 'clear' or 'low'."
            )

        payload: dict[str, Any] = {
            "project_id": project_id,
            "estimated_start": estimated_start,
            "clarity_score": clarity_score,
        }
        if missing_elements:
            payload["missing_elements"] = missing_elements

        message = {
            "message_id": f"brief-ack-{project_id}",
            "sender_role": "build",
            "recipient_role": "ops",
            "message_type": "feature_brief_acknowledged",
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._send_message(message)
        self._log.append(
            BuildLogEntry(
                timestamp=message["timestamp"],
                action_type="feature_brief_acknowledged",
                entity_id=project_id,
                outcome="success",
                details={"clarity_score": clarity_score},
            )
        )

    # ------------------------------------------------------------------
    # Inbound handlers
    # ------------------------------------------------------------------

    def handle_feature_brief(self, message: dict[str, Any]) -> None:
        """Handle feature_brief from Ops Claw.

        Starts a 10-minute SLA timer. If no acknowledgment is sent within
        10 minutes, _send_overdue_ack_warning is triggered.
        """
        if message.get("message_type") != "feature_brief":
            raise ValueError(
                f"Expected message_type 'feature_brief', got '{message.get('message_type')}'"
            )

        payload = message.get("payload", {})
        project_id = payload.get("project_id", "unknown")

        # Start 10-minute SLA timer for overdue acknowledgment
        timer = threading.Timer(
            FEATURE_BRIEF_SLA_SECONDS,
            self._send_overdue_ack_warning,
            args=[project_id],
        )
        timer.daemon = True
        timer.start()
        self._sla_timers[project_id] = timer

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="feature_brief_received",
                entity_id=project_id,
                outcome="success",
                details={
                    "feature_name": payload.get("feature_name"),
                    "description": payload.get("description", "")[:100],
                    "sla_timer_started": True,
                    "sla_seconds": FEATURE_BRIEF_SLA_SECONDS,
                },
            )
        )

    def handle_retention_signals(self, message: dict[str, Any]) -> None:
        payload = message.get("payload", {})
        self._retention_signals = payload

        signals_path = self._fs.base / "context" / "sprint" / "retention-signals.json"
        signals_path.parent.mkdir(parents=True, exist_ok=True)
        self._fs.atomic_write_json(signals_path, payload)

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="retention_signals_received",
                entity_id=payload.get("feature_id", "unknown"),
                outcome="success",
                details={"signal_type": payload.get("signal_type")},
            )
        )

    def handle_behavior_query_response(self, message: dict[str, Any]) -> None:
        self._pending_query = None
        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="behavior_query_response_received",
                entity_id=message.get("message_id", "unknown"),
                outcome="success",
                details={},
            )
        )

    # ------------------------------------------------------------------
    # Query state
    # ------------------------------------------------------------------

    def has_pending_behavior_query(self) -> bool:
        return self._pending_query is not None

    def get_pending_query_age_seconds(self) -> float | None:
        if self._pending_query is None:
            return None
        sent = datetime.fromisoformat(self._pending_query.sent_at)
        return (datetime.now(timezone.utc) - sent).total_seconds()

    # ------------------------------------------------------------------
    # Retention signals
    # ------------------------------------------------------------------

    def get_retention_signals(self) -> dict[str, Any] | None:
        return self._retention_signals

    # ------------------------------------------------------------------
    # Shipping data accumulation
    # ------------------------------------------------------------------

    def accumulate_shipping_data(
        self,
        pr_id: str,
        issue_number: int,
        feature_name: str,
        changes: list[str],
    ) -> None:
        self._shipping_data.append(
            {
                "pr_id": pr_id,
                "issue_number": issue_number,
                "feature_name": feature_name,
                "changes": changes,
                "merged_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_accumulated_shipping_summary(self) -> dict[str, Any]:
        return {
            "week_of": datetime.now(timezone.utc).strftime("%Y-W%W"),
            "prs_merged": len(self._shipping_data),
            "issues_resolved": len(self._shipping_data),
            "features_shipped": list({d["feature_name"] for d in self._shipping_data}),
            "notable_changes": [c for d in self._shipping_data for c in d["changes"]],
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send_message(self, message: dict[str, Any]) -> None:
        try:
            if self._gateway:
                self._gateway.send(message)
            else:
                self._write_fallback_message(message)
        except Exception as exc:
            logger.warning("Failed to send message: %s — falling back to file", exc)
            self._write_fallback_message(message)

    def _write_fallback_message(self, message: dict[str, Any]) -> None:
        """Write a message to the recipient's mesh inbox directory.

        Uses the canonical mesh inbox path (~/.milimo/mesh/inbox/{recipient}/)
        so that the recipient's InboxPoller can actually read it.
        """

        recipient_role = message.get("recipient_role", "unknown")
        mesh_inbox = mesh_dir() / "inbox" / recipient_role
        mesh_inbox.mkdir(parents=True, exist_ok=True)

        msg_id = message.get(
            "message_id", f"msg-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        path = mesh_inbox / f"{msg_id}.json"
        path.write_text(json.dumps(message, indent=2))
        logger.info("Fallback message written to %s", path)

    def _send_overdue_ack_warning(
        self, feature_brief_id: str, claw: str = "build"
    ) -> None:
        """Send a preliminary acknowledgment when feature brief response is overdue.

        Sends a low-clarity acknowledgment and logs the delayed event.
        """
        self.send_feature_brief_acknowledged(
            project_id=feature_brief_id,
            estimated_start="TBD",
            clarity_score="low",
        )

        self._log.append(
            BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="feature_brief_ack_delayed",
                entity_id=feature_brief_id,
                outcome="delayed",
                details={
                    "claw": claw,
                    "severity": "warning",
                    "message": f"Feature brief {feature_brief_id} acknowledgment overdue",
                },
            )
        )
        logger.info("Sent overdue ack warning for %s in %s", feature_brief_id, claw)

    # ------------------------------------------------------------------
    # Enhancement: Event normalization (from Clawhip typed event model)
    # ------------------------------------------------------------------

    def normalize_message(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize incoming messages from any claw to canonical Build events."""
        payload = raw.get("payload", {})
        return {
            "event": f"{EVENT_NAMESPACE}.{raw.get('message_type', 'unknown')}",
            "source": raw.get("sender_role", "unknown"),
            "repo_name": payload.get("project_id"),
            "timestamp": raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "metadata": payload,
        }
