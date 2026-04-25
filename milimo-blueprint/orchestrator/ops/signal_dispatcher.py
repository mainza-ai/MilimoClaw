# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Signal Dispatcher

Sends all outbound messages from the Ops Claw to other claws.
All sends go through the inter-claw mesh gateway.
Every dispatch logged to operational.log.
Never raises on dispatch failure — logs error and continues.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .ops_init import OpsOperationalLog, OpsLogEntry

logger = logging.getLogger("milimo.ops")


class PricingNotConfirmedError(Exception):
    """Raised when attempting to send project_brief without confirmed pricing."""


class MeshGateway(Protocol):
    """Protocol for the inter-claw mesh gateway."""

    def send(self, message: dict[str, Any]) -> bool: ...


class OpsSignalDispatcher:
    """
    Sends all outbound messages from the Ops Claw to other claws.

    All sends go through the inter-claw mesh gateway.
    Every dispatch logged to operational.log.
    Never raises on dispatch failure — logs error and continues.
    """

    def __init__(
        self,
        gateway: MeshGateway,
        operational_log: OpsOperationalLog,
        squad_id: str,
        pricing_confirmed_dir: Path | None = None,
    ):
        self._gateway = gateway
        self._operational_log = operational_log
        self._squad_id = squad_id
        self._pricing_confirmed_dir = pricing_confirmed_dir or Path(
            "/sandbox/clients/pricing_confirmed"
        )

    def _is_pricing_confirmed(self, project_id: str) -> bool:
        confirmation_file = self._pricing_confirmed_dir / f"{project_id}.json"
        return confirmation_file.exists()

    def _confirm_pricing(self, project_id: str) -> None:
        self._pricing_confirmed_dir.mkdir(parents=True, exist_ok=True)
        confirmation_file = self._pricing_confirmed_dir / f"{project_id}.json"
        confirmation_file.write_text(
            '{"confirmed": true, "timestamp": "'
            + datetime.now(timezone.utc).isoformat()
            + '"}'
        )

    def send_project_brief(
        self,
        client_id: str,
        project_id: str,
        brief_text: str,
        deadline: str,
        tone_requirements: str,
        platform_targets: list[str],
        recipient_role: str,
    ) -> None:
        if not self._is_pricing_confirmed(project_id):
            raise PricingNotConfirmedError(
                f"Cannot send project_brief for project {project_id}: "
                "pricing_response not confirmed. Send pricing_query first."
            )

        payload = {
            "client_id": client_id,
            "project_id": project_id,
            "brief_text": brief_text,
            "deadline": deadline,
            "tone_requirements": tone_requirements,
            "platform_targets": platform_targets,
        }

        self._send("brief", recipient_role, payload)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="project_brief_sent",
                entity_id=project_id,
                outcome="success",
                details={"recipient_role": recipient_role, "client_id": client_id},
            )
        )

    def send_feature_brief(
        self,
        client_id: str,
        project_id: str,
        feature_description: str,
        deadline: str,
        acceptance_criteria: str,
    ) -> None:
        payload = {
            "project_id": project_id,
            "feature_name": feature_description[:100],
            "description": feature_description,
            "deadline": deadline,
            "client_id": client_id,
            "priority": "normal",
        }

        self._send("feature_brief", "build", payload)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="feature_brief_sent",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id},
            )
        )

    def send_pricing_query(
        self,
        project_id: str,
        scope_description: str,
        complexity_estimate: str,
        deadline: str,
        client_id: str | None = None,
    ) -> None:
        payload = {
            "project_id": project_id,
            "scope_description": scope_description,
            "complexity_estimate": complexity_estimate,
            "deadline": deadline,
        }
        if client_id:
            payload["client_id"] = client_id

        self._send("pricing_query", "finance", payload)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="pricing_query_sent",
                entity_id=project_id,
                outcome="success",
                details={"deadline": deadline},
            )
        )

    def send_project_complete(
        self, project_id: str, client_id: str, delivered_at: str
    ) -> None:
        payload = {
            "project_id": project_id,
            "client_id": client_id,
            "delivered_at": delivered_at,
        }

        self._send("project_complete", "finance", payload)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="project_complete_sent",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id},
            )
        )

    def send_client_health_signal(
        self,
        client_id: str,
        health_score: float,
        health_factors: list[str],
        recommended_action: str,
    ) -> None:
        payload = {
            "client_id": client_id,
            "health_score": health_score,
            "health_factors": health_factors,
            "recommended_action": recommended_action,
        }

        self._send("client_health_signal", "analytics", payload)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="client_health_signal_sent",
                entity_id=client_id,
                outcome="success",
                details={"health_score": health_score},
            )
        )

    def send_client_onboarded(
        self,
        client_id: str,
        niche: str,
        project_type: str,
        estimated_value: float,
    ) -> None:
        payload = {
            "client_id": client_id,
            "niche": niche,
            "project_type": project_type,
            "estimated_value": estimated_value,
        }

        self._send("client_onboarded", "analytics", payload)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="client_onboarded_sent",
                entity_id=client_id,
                outcome="success",
                details={"niche": niche, "project_type": project_type},
            )
        )

    def _send(
        self, message_type: str, recipient_role: str, payload: dict[str, Any]
    ) -> None:
        message = {
            "message_id": uuid.uuid4().hex[:12],
            "sender_role": "ops",
            "recipient_role": recipient_role,
            "message_type": message_type,
            "payload": payload,
            "squad_id": self._squad_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            success = self._gateway.send(message)
            if not success:
                logger.error(
                    "Failed to send %s to %s (gateway returned false)",
                    message_type,
                    recipient_role,
                )
                self._operational_log.append(
                    OpsLogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        action_type=f"{message_type}_send_failed",
                        entity_id=payload.get(
                            "project_id", payload.get("client_id", "unknown")
                        ),
                        outcome="failed",
                        details={
                            "recipient_role": recipient_role,
                            "error": "gateway returned false",
                        },
                    )
                )
        except Exception as e:
            logger.error(
                "Exception sending %s to %s: %s",
                message_type,
                recipient_role,
                e,
            )
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type=f"{message_type}_send_exception",
                    entity_id=payload.get(
                        "project_id", payload.get("client_id", "unknown")
                    ),
                    outcome="failed",
                    details={"recipient_role": recipient_role, "error": str(e)},
                )
            )

    def mark_pricing_confirmed(self, project_id: str) -> None:
        self._confirm_pricing(project_id)

    def handle_incident(self, alert: dict[str, Any]) -> None:
        """Handle an incoming incident alert from the webhook server.

        This method is called by OpsWebhookServer when a webhook is received.
        It logs the alert and makes it available for the IncidentAnalyzer
        and RunbookExecutor (wired via OpsClaw).

        Args:
            alert: Alert dict with alert_id, source, severity, title, description.
        """
        alert_id = alert.get("alert_id", "unknown")
        source = alert.get("source", "unknown")
        severity = alert.get("severity", "warning")
        title = alert.get("title", "")

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="incident_received",
                entity_id=alert_id,
                outcome="success",
                details={
                    "source": source,
                    "severity": severity,
                    "title": title,
                },
            )
        )

        logger.info(
            "Incident received: %s from %s (severity: %s) — %s",
            alert_id,
            source,
            severity,
            title,
        )
