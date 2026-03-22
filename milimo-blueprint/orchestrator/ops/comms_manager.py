#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Communications Manager

Manages all client communication.

Routine updates: AUTO (logged, morning digest)
Non-routine communications: REVIEW (drafted, operator approves)
Never references pricing without confirmed pricing_response on file.
Logs every communication to comms.log.
Deep Work Mode auto-responses: AUTO (sends without approval).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ops_init import OpsFilesystemInit, OpsOperationalLog, OpsLogEntry, OpsCommsLog, CommsLogEntry
from .signal_dispatcher import OpsSignalDispatcher
from .approval_handler import OpsApprovalHandler
from .scope_monitor import ScopeMonitor

logger = logging.getLogger("milimo.ops")


@dataclass
class ClientMessage:
    """Represents a client message."""

    message_id: str
    client_id: str
    project_id: str | None
    direction: str  # "inbound" | "outbound"
    channel: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_action_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "direction": self.direction,
            "channel": self.channel,
            "content": self.content,
            "timestamp": self.timestamp,
            "approved_action_id": self.approved_action_id,
        }


class CommsManager:
    """
    Manages all client communication.

    Routine updates: AUTO (logged, morning digest)
    Non-routine communications: REVIEW (drafted, operator approves)
    Never references pricing without confirmed pricing_response on file.
    Logs every communication to comms.log.
    Deep Work Mode auto-responses: AUTO (sends without approval).
    """

    ROUTINE_TYPES = [
        "project_update",
        "schedule_confirmation",
        "file_delivery_notification",
        "acknowledgment",
    ]

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog,
        comms_log: OpsCommsLog,
        dispatcher: OpsSignalDispatcher,
        scope_monitor: ScopeMonitor,
        config_path: Path | None = None,
    ):
        self._fs = fs
        self._inference_client = inference_client
        self._approval_handler = approval_handler
        self._operational_log = operational_log
        self._comms_log = comms_log
        self._dispatcher = dispatcher
        self._scope_monitor = scope_monitor
        self._config_path = config_path or Path.home() / ".milimo" / "config.json"

    def handle_inbound(
        self,
        client_id: str,
        project_id: str | None,
        message_text: str,
        channel: str,
    ) -> None:
        self._comms_log.append(
            CommsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                direction="received",
                client_id=client_id,
                project_id=project_id,
                channel=channel,
                content_preview=message_text[:100],
            )
        )

        pricing_question = self._detect_pricing_question(message_text)
        if pricing_question:
            self._handle_pricing_question(client_id, project_id, message_text)

        if project_id:
            self._scope_monitor.check_message(client_id, project_id, message_text)

        message_type = self._classify_message(message_text)

        if message_type in self.ROUTINE_TYPES:
            self._approval_handler.log_auto(
                action_type="routine_message",
                entity_id=project_id or client_id,
                content_preview=f"Routine {message_type}: {message_text[:100]}",
            )
        else:
            response_draft = self.draft_response(
                client_id=client_id,
                project_id=project_id,
                inbound_message=message_text,
                response_type=message_type,
            )

            self._approval_handler.queue_review(
                action_type="client_response",
                entity_id=project_id or client_id,
                content=response_draft,
                context={
                    "client_id": client_id,
                    "project_id": project_id,
                    "message_type": message_type,
                    "original_message": message_text[:500],
                },
            )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="inbound_message_handled",
                entity_id=project_id or client_id,
                outcome="success",
                details={"channel": channel, "message_type": message_type},
            )
        )

    def _detect_pricing_question(self, message_text: str) -> bool:
        pricing_keywords = ["price", "cost", "budget", "how much", "rate", "charge", "fee"]

        prompt = f"""Determine if this message is asking about pricing or cost.

MESSAGE:
{message_text}

Respond in JSON format:
{{"is_pricing_question": true/false}}"""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="pricing_question_detection",
                max_tokens=50,
            )

            match = re.search(r"\{[^}]+\}", response)
            if match:
                data = json.loads(match.group())
                return data.get("is_pricing_question", False)
        except Exception as e:
            logger.warning("Pricing question detection failed: %s", e)

        message_lower = message_text.lower()
        return any(kw in message_lower for kw in pricing_keywords)

    def _handle_pricing_question(
        self, client_id: str, project_id: str | None, message_text: str
    ) -> None:
        holding_response = (
            f"Hi, thanks for asking about pricing! "
            f"Let me put together a proposal with exact figures and get back to you shortly."
        )

        self._approval_handler.queue_review(
            action_type="pricing_holding_response",
            entity_id=project_id or client_id,
            content=holding_response,
            context={
                "client_id": client_id,
                "project_id": project_id,
                "is_pricing_inquiry": True,
            },
        )

        if project_id:
            self._dispatcher.send_pricing_query(
                project_id=project_id,
                scope_description="Pricing inquiry from client",
                complexity_estimate="medium",
                deadline="TBD",
                client_id=client_id,
            )

    def draft_response(
        self,
        client_id: str,
        project_id: str | None,
        inbound_message: str,
        response_type: str,
    ) -> str:
        history = self._comms_log.get_client_history(client_id, days=30)
        history_context = ""
        for entry in history[-5:]:
            direction = "Client" if entry.direction == "received" else "We"
            history_context += f"{direction}: {entry.content_preview}\n"

        prompt = f"""Draft a professional response to this client message.

CLIENT HISTORY:
{history_context or "No recent history."}

CLIENT MESSAGE:
{inbound_message}

RESPONSE TYPE: {response_type}

Guidelines:
1. Be professional and helpful
2. Address the specific question or concern
3. Keep it concise (under 200 words)
4. Do NOT include specific pricing unless previously confirmed

Output only the response message."""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="response_drafting",
                max_tokens=300,
            )
            return response.strip()
        except Exception as e:
            logger.warning("Response drafting failed: %s", e)
            return f"Thank you for your message. I'll review this and get back to you shortly."

    def send_auto_response(self, client_id: str, message_text: str) -> None:
        self._comms_log.append(
            CommsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                direction="sent",
                client_id=client_id,
                project_id=None,
                channel="auto_response",
                content_preview=message_text[:100],
            )
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="auto_response_sent",
                entity_id=client_id,
                outcome="success",
                details={"content_preview": message_text[:100]},
            )
        )

    def send_deep_work_response(self, client_id: str, resume_date: str) -> None:
        template = self._fs.get_template("deep-work-response.md")

        message = template.replace("{{client_name}}", client_id)
        message = message.replace("{{resume_date}}", resume_date)

        self._comms_log.append(
            CommsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                direction="sent",
                client_id=client_id,
                project_id=None,
                channel="deep_work_auto",
                content_preview=message[:100],
            )
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="deep_work_response_sent",
                entity_id=client_id,
                outcome="success",
                details={"resume_date": resume_date},
            )
        )

    def is_deep_work_active(self) -> bool:
        if not self._config_path.exists():
            return False

        try:
            config = json.loads(self._config_path.read_text())
            return config.get("deep_work", {}).get("active", False)
        except (json.JSONDecodeError, OSError):
            return False

    def _classify_message(self, message_text: str) -> str:
        prompt = f"""Classify this client message type.

MESSAGE:
{message_text}

Classify as one of:
- project_update: Status update or progress inquiry
- schedule_confirmation: Confirming or asking about timing
- file_delivery_notification: Confirming file receipt or delivery
- acknowledgment: Simple acknowledgment or thanks
- question: A specific question requiring a detailed response
- concern: Expressing concern or dissatisfaction
- request: Making a new request

Respond in JSON format:
{{"message_type": "classification"}}"""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="message_classification",
                max_tokens=50,
            )

            match = re.search(r"\{[^}]+\}", response)
            if match:
                data = json.loads(match.group())
                return data.get("message_type", "question")
        except Exception as e:
            logger.warning("Message classification failed: %s", e)

        return "question"

    def log_outbound_message(
        self,
        client_id: str,
        project_id: str | None,
        content: str,
        channel: str,
        approved_action_id: str | None = None,
    ) -> None:
        self._comms_log.append(
            CommsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                direction="sent",
                client_id=client_id,
                project_id=project_id,
                channel=channel,
                content_preview=content[:100],
                approved_by=approved_action_id,
            )
        )
