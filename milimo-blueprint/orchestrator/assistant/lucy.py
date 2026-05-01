# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Lucy — Assistant Runtime Coordinator

The conversational layer that bridges the operator to the Milimo Claw squad.
Telegram (and other messaging platforms) are handled entirely by OpenShell's
managed channel messaging — NemoClaw configures channels during `nemoclaw
onboard`, and OpenShell delivers inbound messages to the agent and relays
outbound responses back to the platform. Lucy does NOT poll Telegram directly.

Lucy:

1. Receives operator messages via OpenShell channel delivery (not direct polling)
2. Routes queries/tasks to the appropriate claw via the mesh
3. Collects assistant_response messages from all claws
4. Returns consolidated responses to the operator (OpenShell relays to Telegram)

Lifecycle:
- Polls inbox at ~/.milimo/mesh/inbox/assistant/ for claw responses
- Sends outbound messages via RealMeshGateway
- Emits heartbeats like any other claw

Per NemoClaw architecture (docs.nvidia.com/nemoclaw/latest/reference/architecture.html):
  MSGAPI ["Messaging Platforms"] → CHMSG ["Channel messaging (OpenShell-managed)"] → AGENT
Tokens are registered as OpenShell providers during `nemoclaw onboard`; the L7 proxy
injects real credentials at egress. The sandbox never sees raw tokens.

Per Telegram setup guide (docs.nvidia.com/nemoclaw/latest/deployment/set-up-telegram-bridge.html):
  Channel messaging (Telegram, Discord, Slack) is configured during `nemoclaw onboard`
  and runs through OpenShell-managed constructs. `nemoclaw tunnel start` only starts
  cloudflared — it does NOT start Telegram. Use `nemoclaw <name> channels stop/start`
  to pause/resume messaging bridges.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from milimo_paths import claw_base
from ..milimo_paths import mesh_dir

logger = logging.getLogger("milimo.assistant")

ALL_CLAW_ROLES = ["content", "ops", "analytics", "finance", "build", "assistant"]
RESPONSE_TIMEOUT_SECONDS = 60


class PendingQuery:
    """Tracks a query dispatched to claws, awaiting responses."""

    def __init__(
        self,
        query_id: str,
        original_text: str,
        target_roles: list[str],
        created_at: float | None = None,
    ) -> None:
        self.query_id = query_id
        self.original_text = original_text
        self.target_roles = target_roles
        self.created_at = created_at or time.time()
        self.responses: dict[str, dict] = {}
        self.responded = False

    @property
    def is_complete(self) -> bool:
        return set(self.responses.keys()) >= set(self.target_roles)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > RESPONSE_TIMEOUT_SECONDS

    def add_response(self, sender_role: str, payload: dict) -> None:
        self.responses[sender_role] = payload


class LucyAssistant:
    """
    Lucy — the conversational assistant coordinating the Milimo Claw squad.

    Bridges operator messages (delivered by OpenShell channel messaging) to claw
    queries/tasks via the mesh, collects responses, and returns consolidated
    answers. Telegram/Discord/Slack are fully managed by OpenShell — Lucy never
    polls messaging APIs directly.
    """

    def __init__(
        self,
        squad_id: str,
        mesh_gateway: Any,
        inbox_dir: Path | None = None,
        base_path: Path | None = None,
    ) -> None:
        self._squad_id = squad_id
        self._mesh_gateway = mesh_gateway
        self._inbox_dir = inbox_dir or mesh_dir() / "inbox" / "assistant"
        self._base_path = base_path or claw_base("assistant")

        self._pending: dict[str, PendingQuery] = {}
        self._running = False
        self._started = False

        self._inbox_dir.mkdir(parents=True, exist_ok=True)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def startup(self) -> None:
        """Initialize Lucy."""
        if self._started:
            logger.warning("LucyAssistant already started")
            return

        logger.info("LucyAssistant: starting for squad %s", self._squad_id)

        self._running = True
        self._started = True

        logger.info("LucyAssistant: started successfully")

    def shutdown(self) -> None:
        """Stop Lucy."""
        self._running = False
        self._started = False
        logger.info("LucyAssistant: shutdown")

    @property
    def is_running(self) -> bool:
        return self._running

    def handle_inbound(self, raw_message: dict) -> dict[str, Any]:
        """Handle an inbound message from the mesh inbox.

        Processes assistant_response messages from claws, collecting them
        into pending queries. When all target claws respond (or timeout),
        consolidates the results.

        Returns:
            Dict with handler result including status and any relevant data.
        """
        message_type = raw_message.get("message_type", "")
        sender_role = raw_message.get("sender_role", "")
        payload = raw_message.get("payload", {})

        result: dict[str, Any] = {
            "status": "processed",
            "message_type": message_type,
            "role": "assistant",
        }

        try:
            if message_type == "assistant_response":
                query_id = payload.get("original_message_id", "")
                response_data = payload.get("response", {})

                pending = self._pending.get(query_id)
                if pending and not pending.responded:
                    pending.add_response(sender_role, response_data)

                    if pending.is_complete:
                        pending.responded = True
                        result["consolidated"] = self._consolidate(pending)
                    elif pending.is_expired:
                        pending.responded = True
                        result["consolidated"] = self._consolidate(pending)

                result["query_id"] = query_id
                result["sender"] = sender_role
                result["action"] = "response_collected"

            else:
                result["status"] = "unknown_type"
                result["action"] = "ignored"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error("LucyAssistant: handle_inbound error: %s", e)

        return result

    def dispatch_query(
        self,
        query_text: str,
        target_roles: list[str] | None = None,
    ) -> str:
        """Dispatch an assistant_query to one or more claws.

        Args:
            query_text: The operator's query text
            target_roles: Which claws to query (default: all)

        Returns:
            query_id for tracking the pending query
        """
        roles = target_roles or ALL_CLAW_ROLES
        query_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        pending = PendingQuery(
            query_id=query_id,
            original_text=query_text,
            target_roles=roles,
        )
        self._pending[query_id] = pending

        for role in roles:
            sent = self._mesh_gateway.send(
                message_type="assistant_query",
                recipient_role=role,
                sender_role="assistant",
                payload={"query": query_text, "query_id": query_id},
                message_id=query_id,
                timestamp=timestamp,
            )
            if not sent:
                logger.warning("LucyAssistant: failed to send query to %s", role)

        logger.info("LucyAssistant: dispatched query %s to %s", query_id, roles)
        return query_id

    def dispatch_task(
        self,
        task_description: str,
        target_role: str,
        deadline: str = "",
    ) -> str:
        """Dispatch an assistant_task to a specific claw.

        Args:
            task_description: The task to assign
            target_role: Which claw to assign the task to
            deadline: ISO deadline string

        Returns:
            message_id for tracking
        """
        message_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        pending = PendingQuery(
            query_id=message_id,
            original_text=task_description,
            target_roles=[target_role],
        )
        self._pending[message_id] = pending

        sent = self._mesh_gateway.send(
            message_type="assistant_task",
            recipient_role=target_role,
            sender_role="assistant",
            payload={
                "task_description": task_description,
                "deadline": deadline,
                "query_id": message_id,
            },
            message_id=message_id,
            timestamp=timestamp,
        )

        if not sent:
            logger.warning("LucyAssistant: failed to send task to %s", target_role)

        logger.info("LucyAssistant: dispatched task %s to %s", message_id, target_role)
        return message_id

    def _consolidate(self, pending: PendingQuery) -> dict:
        """Consolidate claw responses into a single result dict."""
        consolidated: dict[str, Any] = {
            "query_id": pending.query_id,
            "original_text": pending.original_text,
            "responses": {},
            "missing": [],
        }

        for role, response in pending.responses.items():
            data = response.get("response", response)
            consolidated["responses"][role] = self._summarize_response(role, data)

        missing = set(pending.target_roles) - set(pending.responses.keys())
        if missing:
            consolidated["missing"] = sorted(missing)

        return consolidated

    def _summarize_response(self, role: str, data: dict) -> str:
        """Create a brief human-readable summary of a claw response."""
        status = data.get("status", "unknown")

        if status == "error":
            return f"Error: {data.get('error', 'unknown')}"

        parts = [f"status={status}"]

        for key in ("action", "components", "task_type"):
            if key in data:
                val = data[key]
                if isinstance(val, dict):
                    parts.append(f"{key}={json.dumps(val)[:100]}")
                else:
                    parts.append(f"{key}={val}")

        return f"{', '.join(parts)}"

    def process_operator_message(self, text: str) -> str:
        """Parse an incoming operator message and dispatch accordingly.

        Supports:
        - Direct queries: "status" -> dispatches assistant_query to all claws
        - Targeted queries: "@content how's the draft?" -> queries content claw
        - Task assignments: "@finance generate invoice for X" -> dispatches task

        Operator messages are delivered by OpenShell channel messaging (Telegram,
        Discord, Slack) — Lucy never polls messaging APIs directly.

        Returns:
            query_id or message_id
        """
        text = text.strip()
        if not text:
            return ""

        if text.startswith("@"):
            return self._handle_targeted_message(text)

        if text.lower() in ("status", "squad status", "report"):
            return self.dispatch_query(
                "squad status report",
                target_roles=ALL_CLAW_ROLES,
            )

        return self.dispatch_query(
            text,
            target_roles=ALL_CLAW_ROLES,
        )

    def _handle_targeted_message(self, text: str) -> str:
        """Handle @role prefixed messages from the operator."""
        parts = text[1:].split(None, 1)
        if len(parts) < 2:
            role = parts[0].lower() if parts else ""
            if role in ALL_CLAW_ROLES:
                return self.dispatch_query(
                    "status",
                    target_roles=[role],
                )
            return ""

        role = parts[0].lower()
        message = parts[1].strip()

        if role not in ALL_CLAW_ROLES:
            logger.warning("LucyAssistant: unknown role '%s' in operator message", role)
            return ""

        task_keywords = [
            "do",
            "create",
            "generate",
            "send",
            "schedule",
            "start",
            "build",
        ]
        first_word = message.split()[0].lower() if message else ""
        if first_word in task_keywords:
            return self.dispatch_task(
                task_description=message,
                target_role=role,
            )

        return self.dispatch_query(
            message,
            target_roles=[role],
        )

    def cleanup_expired(self) -> int:
        """Remove expired pending queries. Returns count of cleaned queries."""
        expired = []
        for qid, pending in self._pending.items():
            if pending.is_expired and not pending.responded:
                expired.append(qid)
                pending.responded = True

        for qid in expired:
            del self._pending[qid]

        if expired:
            logger.info("LucyAssistant: cleaned %d expired queries", len(expired))
        return len(expired)
