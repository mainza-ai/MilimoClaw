# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Lucy — Assistant Runtime Coordinator

The conversational layer that bridges the operator (via Telegram) to the
Milimo Claw squad. Lucy:

1. Receives Telegram messages from the operator
2. Routes queries/tasks to the appropriate claw via the mesh
3. Collects assistant_response messages from all claws
4. Relays consolidated responses back to Telegram

Lifecycle:
- Polls inbox at ~/.milimo/mesh/inbox/assistant/ for claw responses
- Listens for Telegram messages via long-polling
- Sends outbound messages via RealMeshGateway
- Emits heartbeats like any other claw
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("milimo.assistant")

ALL_CLAW_ROLES = ["content", "ops", "analytics", "finance", "build", "assistant"]
TELEGRAM_API_BASE = "https://api.telegram.org"
RESPONSE_TIMEOUT_SECONDS = 60


class TelegramBridge:
    """Telegram Bot API client for sending/receiving messages."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        api_base: str = TELEGRAM_API_BASE,
    ) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._api_base = api_base
        self._last_update_id = 0

    @property
    def base_url(self) -> str:
        return f"{self._api_base}/bot{self._token}"

    def send_message(self, text: str, chat_id: str | None = None) -> dict:
        """Send a text message to Telegram."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self._chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("TelegramBridge: send failed: %s", e)
            return {"ok": False, "error": str(e)}

    def get_updates(self, timeout: int = 30) -> list[dict]:
        """Long-poll for new Telegram messages."""
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": self._last_update_id + 1,
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        try:
            resp = requests.post(url, json=params, timeout=timeout + 5)
            resp.raise_for_status()
            data = resp.json()
            updates = data.get("result", [])
            if updates:
                self._last_update_id = updates[-1]["update_id"]
            return updates
        except Exception as e:
            logger.error("TelegramBridge: get_updates failed: %s", e)
            return []

    def health_check(self) -> bool:
        """Verify the bot token is valid."""
        url = f"{self.base_url}/getMe"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json().get("ok", False)
        except Exception:
            return False


class PendingQuery:
    """Tracks a query dispatched to claws, awaiting responses."""

    def __init__(
        self,
        query_id: str,
        original_text: str,
        telegram_chat_id: str,
        target_roles: list[str],
        created_at: float | None = None,
    ) -> None:
        self.query_id = query_id
        self.original_text = original_text
        self.telegram_chat_id = telegram_chat_id
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

    Bridges operator messages (Telegram) to claw queries/tasks via the mesh,
    collects responses, and relays consolidated answers back to Telegram.
    """

    def __init__(
        self,
        squad_id: str,
        mesh_gateway: Any,
        telegram_bridge: TelegramBridge | None = None,
        inbox_dir: Path | None = None,
        base_path: Path | None = None,
    ) -> None:
        self._squad_id = squad_id
        self._mesh_gateway = mesh_gateway
        self._telegram = telegram_bridge
        self._inbox_dir = (
            inbox_dir or Path.home() / ".milimo" / "mesh" / "inbox" / "assistant"
        )
        self._base_path = base_path or Path("/sandbox/.milimo/assistant")

        self._pending: dict[str, PendingQuery] = {}
        self._running = False
        self._started = False

        self._inbox_dir.mkdir(parents=True, exist_ok=True)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def startup(self) -> None:
        """Initialize Lucy and start background threads."""
        if self._started:
            logger.warning("LucyAssistant already started")
            return

        logger.info("LucyAssistant: starting for squad %s", self._squad_id)

        self._running = True
        self._started = True

        if self._telegram:
            tg_ok = self._telegram.health_check()
            if tg_ok:
                logger.info("LucyAssistant: Telegram bot connected")
            else:
                logger.warning("LucyAssistant: Telegram bot health check failed")

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
        consolidates and sends to Telegram.

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
                        self._relay_to_telegram(pending)
                        pending.responded = True
                    elif pending.is_expired:
                        self._relay_to_telegram(pending)
                        pending.responded = True

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
        telegram_chat_id: str | None = None,
    ) -> str:
        """Dispatch an assistant_query to one or more claws.

        Args:
            query_text: The operator's query text
            target_roles: Which claws to query (default: all)
            telegram_chat_id: Chat ID to relay the response to

        Returns:
            query_id for tracking the pending query
        """
        roles = target_roles or ALL_CLAW_ROLES
        query_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        pending = PendingQuery(
            query_id=query_id,
            original_text=query_text,
            telegram_chat_id=telegram_chat_id or "",
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
        telegram_chat_id: str | None = None,
    ) -> str:
        """Dispatch an assistant_task to a specific claw.

        Args:
            task_description: The task to assign
            target_role: Which claw to assign the task to
            deadline: ISO deadline string
            telegram_chat_id: Chat ID to relay the response to

        Returns:
            message_id for tracking
        """
        message_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        pending = PendingQuery(
            query_id=message_id,
            original_text=task_description,
            telegram_chat_id=telegram_chat_id or "",
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

    def _relay_to_telegram(self, pending: PendingQuery) -> None:
        """Consolidate claw responses and relay to Telegram."""
        if not self._telegram:
            logger.debug("LucyAssistant: no Telegram bridge, skipping relay")
            return

        if not pending.telegram_chat_id:
            logger.debug("LucyAssistant: no chat_id for query %s", pending.query_id)
            return

        lines = [f"*Query:* {pending.original_text}\n"]

        for role, response in pending.responses.items():
            data = response.get("response", response)
            summary = self._summarize_response(role, data)
            lines.append(f"*{role.title()} Claw:* {summary}")

        missing = set(pending.target_roles) - set(pending.responses.keys())
        if missing:
            lines.append(f"_No response from: {', '.join(missing)}_")

        text = "\n".join(lines)
        self._telegram.send_message(text, chat_id=pending.telegram_chat_id)

        logger.info(
            "LucyAssistant: relayed %d responses to Telegram for query %s",
            len(pending.responses),
            pending.query_id,
        )

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

    def process_telegram_message(self, text: str, chat_id: str) -> str:
        """Parse an incoming Telegram message and dispatch accordingly.

        Supports:
        - Direct queries: "status" -> dispatches assistant_query to all claws
        - Targeted queries: "@content how's the draft?" -> queries content claw
        - Task assignments: "@finance generate invoice for X" -> dispatches task

        Returns:
            query_id or message_id
        """
        text = text.strip()
        if not text:
            return ""

        if text.startswith("@"):
            return self._handle_targeted_message(text, chat_id)

        if text.lower() in ("status", "squad status", "report"):
            return self.dispatch_query(
                "squad status report",
                target_roles=ALL_CLAW_ROLES,
                telegram_chat_id=chat_id,
            )

        return self.dispatch_query(
            text,
            target_roles=ALL_CLAW_ROLES,
            telegram_chat_id=chat_id,
        )

    def _handle_targeted_message(self, text: str, chat_id: str) -> str:
        """Handle @role prefixed messages from Telegram."""
        parts = text[1:].split(None, 1)
        if len(parts) < 2:
            role = parts[0].lower() if parts else ""
            if role in ALL_CLAW_ROLES:
                return self.dispatch_query(
                    "status",
                    target_roles=[role],
                    telegram_chat_id=chat_id,
                )
            return ""

        role = parts[0].lower()
        message = parts[1].strip()

        if role not in ALL_CLAW_ROLES:
            logger.warning("LucyAssistant: unknown role '%s' in Telegram message", role)
            if self._telegram:
                self._telegram.send_message(
                    f"Unknown claw: {role}. Available: {', '.join(ALL_CLAW_ROLES)}",
                    chat_id=chat_id,
                )
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
                telegram_chat_id=chat_id,
            )

        return self.dispatch_query(
            message,
            target_roles=[role],
            telegram_chat_id=chat_id,
        )

    def cleanup_expired(self) -> int:
        """Remove expired pending queries. Returns count of cleaned queries."""
        expired = []
        for qid, pending in self._pending.items():
            if pending.is_expired and not pending.responded:
                expired.append(qid)
                self._relay_to_telegram(pending)
                pending.responded = True

        for qid in expired:
            del self._pending[qid]

        if expired:
            logger.info("LucyAssistant: cleaned %d expired queries", len(expired))
        return len(expired)

    def telegram_poll_loop(self) -> None:
        """Long-running loop that polls Telegram for new messages."""
        if not self._telegram:
            logger.warning("LucyAssistant: no Telegram bridge, poll loop not started")
            return

        logger.info("LucyAssistant: starting Telegram poll loop")
        while self._running:
            try:
                updates = self._telegram.get_updates(timeout=30)
                for update in updates:
                    message = update.get("message", {})
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    text = message.get("text", "")

                    if not text or not chat_id:
                        continue

                    logger.info(
                        "LucyAssistant: received Telegram message: %s",
                        text[:100],
                    )
                    self.process_telegram_message(text, chat_id)

            except Exception as e:
                logger.error("LucyAssistant: Telegram poll error: %s", e)
                time.sleep(5)
