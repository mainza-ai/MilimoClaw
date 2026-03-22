#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Scope Monitor

Detects scope creep in client communications.

Runs on every client message received.
High-confidence detections (>0.7) immediately queue a HOLD
change order — never auto-handled.
All detections logged to operational.log.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ops_init import OpsFilesystemInit, OpsOperationalLog, OpsLogEntry
from .signal_dispatcher import OpsSignalDispatcher
from .approval_handler import OpsApprovalHandler

logger = logging.getLogger("milimo.ops")


@dataclass
class ScopeCreepDetection:
    """Result of scope creep detection."""

    project_id: str
    client_id: str
    original_scope: str
    new_request: str
    confidence: float
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "original_scope": self.original_scope,
            "new_request": self.new_request,
            "confidence": self.confidence,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScopeCreepDetection:
        return cls(
            project_id=data["project_id"],
            client_id=data["client_id"],
            original_scope=data["original_scope"],
            new_request=data["new_request"],
            confidence=data["confidence"],
            detected_at=data.get("detected_at", ""),
        )


class ScopeMonitor:
    """
    Detects scope creep in client communications.

    Runs on every client message received.
    High-confidence detections (>0.7) immediately queue a HOLD
    change order — never auto-handled.
    All detections logged to operational.log.
    """

    DETECTION_THRESHOLD = 0.7

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        approval_handler: OpsApprovalHandler,
        dispatcher: OpsSignalDispatcher,
        operational_log: OpsOperationalLog,
    ):
        self._fs = fs
        self._inference_client = inference_client
        self._approval_handler = approval_handler
        self._dispatcher = dispatcher
        self._operational_log = operational_log
        self._pending_change_orders: dict[str, dict[str, Any]] = {}

    def check_message(
        self,
        client_id: str,
        project_id: str,
        message_text: str,
    ) -> ScopeCreepDetection | None:
        original_brief = self._load_original_brief(client_id, project_id)
        if not original_brief:
            logger.debug("No brief found for project %s", project_id)
            return None

        detection = self._detect_scope_creep(
            project_id=project_id,
            client_id=client_id,
            original_scope=original_brief,
            new_message=message_text,
        )

        if detection is None:
            return None

        if detection.confidence > self.DETECTION_THRESHOLD:
            self._handle_high_confidence_detection(detection)

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="scope_creep_detected",
                entity_id=project_id,
                outcome="flagged" if detection.confidence > self.DETECTION_THRESHOLD else "logged",
                details={
                    "confidence": detection.confidence,
                    "new_request": detection.new_request[:200],
                },
            )
        )

        return detection

    def _detect_scope_creep(
        self,
        project_id: str,
        client_id: str,
        original_scope: str,
        new_message: str,
    ) -> ScopeCreepDetection | None:
        prompt = f"""Analyze this client message for scope creep against the original project brief.

ORIGINAL PROJECT BRIEF:
{original_scope[:1000]}

NEW CLIENT MESSAGE:
{new_message}

Determine:
1. Is this request outside the original scope? (is_scope_creep: true/false)
2. What is the new request? (new_request: describe briefly)
3. How confident are you? (confidence: 0.0-1.0)

Respond in JSON format:
{{
    "is_scope_creep": true/false,
    "new_request": "description of the new request",
    "confidence": 0.0-1.0
}}"""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="scope_creep_detection",
                max_tokens=200,
            )

            match = re.search(r"\{[^}]+\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group())

                if not data.get("is_scope_creep", False):
                    return None

                return ScopeCreepDetection(
                    project_id=project_id,
                    client_id=client_id,
                    original_scope=original_scope[:500],
                    new_request=data.get("new_request", new_message[:200]),
                    confidence=float(data.get("confidence", 0.5)),
                )

        except Exception as e:
            logger.warning("Scope creep detection inference failed: %s", e)

        return None

    def _handle_high_confidence_detection(self, detection: ScopeCreepDetection) -> None:
        detection_file = self._fs.get_project_path(
            detection.client_id, detection.project_id
        ) / "scope_creep"
        detection_file.mkdir(parents=True, exist_ok=True)
        detection_file = detection_file / f"detection_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        self._fs.write_json_atomic(detection_file, detection.to_dict())

        self._dispatcher.send_pricing_query(
            project_id=f"{detection.project_id}_scope_change",
            scope_description=detection.new_request,
            complexity_estimate="medium",
            deadline="ASAP",
            client_id=detection.client_id,
        )

        change_order_draft = self.draft_change_order(
            project_id=detection.project_id,
            original_scope=detection.original_scope,
            new_request=detection.new_request,
        )

        action_id = self._approval_handler.queue_hold(
            action_type="scope_change_order",
            entity_id=detection.project_id,
            content=change_order_draft,
            context={
                "client_id": detection.client_id,
                "original_scope": detection.original_scope,
                "new_request": detection.new_request,
                "confidence": detection.confidence,
            },
        )

        self._pending_change_orders[action_id] = {
            "detection": detection.to_dict(),
            "change_order_draft": change_order_draft,
        }

    def draft_change_order(
        self,
        project_id: str,
        original_scope: str,
        new_request: str,
        additional_cost: float | None = None,
    ) -> str:
        template = self._fs.get_template("change-order-template.md")

        change_order = template.replace("{{original_scope}}", original_scope[:500])
        change_order = change_order.replace("{{new_request}}", new_request)

        if additional_cost is not None:
            change_order = change_order.replace("{{additional_cost}}", f"${additional_cost:,.2f}")
        else:
            change_order = change_order.replace("{{additional_cost}}", "PENDING - awaiting pricing")

        change_order = change_order.replace("{{revised_timeline}}", "TBD")

        if self._inference_client:
            prompt = f"""Personalize this change order for the client.

TEMPLATE:
{change_order}

Make it professional and clear. Keep the key details intact.
Output only the personalized change order."""

            try:
                response = self._inference_client.complete(
                    prompt=prompt,
                    data_type="change_order_drafting",
                    max_tokens=400,
                )
                return response.strip()
            except Exception as e:
                logger.warning("Change order drafting failed: %s", e)

        return change_order

    def handle_scope_pricing_response(
        self,
        project_id: str,
        additional_cost: float,
    ) -> None:
        pending_key = None
        pending_data = None

        for key, data in self._pending_change_orders.items():
            detection = data.get("detection", {})
            if detection.get("project_id") == project_id:
                pending_key = key
                pending_data = data
                break

        if not pending_data:
            logger.warning("No pending change order found for project %s", project_id)
            return

        detection = ScopeCreepDetection.from_dict(pending_data["detection"])

        updated_change_order = self.draft_change_order(
            project_id=project_id,
            original_scope=detection.original_scope,
            new_request=detection.new_request,
            additional_cost=additional_cost,
        )

        self._approval_handler.queue_hold(
            action_type="scope_change_order_priced",
            entity_id=project_id,
            content=updated_change_order,
            context={
                "client_id": detection.client_id,
                "original_scope": detection.original_scope,
                "new_request": detection.new_request,
                "additional_cost": additional_cost,
            },
        )

        if pending_key:
            del self._pending_change_orders[pending_key]

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="scope_change_order_priced",
                entity_id=project_id,
                outcome="success",
                details={"additional_cost": additional_cost},
            )
        )

    def _load_original_brief(self, client_id: str, project_id: str) -> str | None:
        project_dir = self._fs.get_project_path(client_id, project_id)
        brief_file = project_dir / "brief.json"

        brief_data = self._fs.read_json(brief_file)
        if not brief_data:
            return None

        return brief_data.get("raw_text") or brief_data.get("scope_description") or brief_data.get("brief_text")

    def get_pending_change_orders(self) -> dict[str, dict[str, Any]]:
        return dict(self._pending_change_orders)
