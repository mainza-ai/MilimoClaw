# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Approval Handler

Handles all War Room approval interactions for Ops Claw actions.

No client-facing message leaves the Ops Claw without operator approval.
REVIEW: drafted, operator approves before sending.
HOLD: fully paused, operator explicitly releases.
AUTO: runs and logs, visible in morning digest.
Every decision logged to decisions.log.

All pending actions are also serialised to mesh_dir/inbox/war_room/ so the
HTTP War Room TUI (http://localhost:9090/warroom.html) and the Hermes
agent share the same canonical source of truth.
"""

from __future__ import annotations

import fcntl
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("milimo.ops")


def _try_import_write_warroom_action() -> tuple[Callable | None, Callable | None]:
    try:
        from warroom_bridge import write_warroom_action, remove_warroom_action
        return write_warroom_action, remove_warroom_action
    except ImportError as exc:
        logger.warning("warroom_bridge unavailable — war room sync skipped: %s", exc)
        return None, None  # type: ignore[return-value]


@dataclass
class OpsApprovalAction:
    """Represents an action pending approval in the War Room."""

    action_id: str
    action_type: str
    entity_id: str
    mode: str  # REVIEW | HOLD | AUTO
    content: str
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    outcome: str | None = None  # approved | edited | blocked | released
    original_content: str | None = None  # for EDIT tracking
    hours_waiting: float = 0.0
    urgency_flag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "entity_id": self.entity_id,
            "mode": self.mode,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
            "original_content": self.original_content,
            "hours_waiting": self.hours_waiting,
            "urgency_flag": self.urgency_flag,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpsApprovalAction:
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            entity_id=data["entity_id"],
            mode=data["mode"],
            content=data["content"],
            context=data.get("context", {}),
            timestamp=data.get("timestamp", ""),
            outcome=data.get("outcome"),
            original_content=data.get("original_content"),
            hours_waiting=data.get("hours_waiting", 0.0),
            urgency_flag=data.get("urgency_flag"),
        )


class OpsApprovalHandler:
    """
    Handles all War Room approval interactions for Ops Claw actions.

    No client-facing message leaves the Ops Claw without operator approval.
    REVIEW: drafted, operator approves before sending.
    HOLD: fully paused, operator explicitly releases.
    AUTO: runs and logs, visible in morning digest.
    Every decision logged to decisions.log.
    """

    REVIEW_QUEUE_DIR = "review_queue"
    HOLD_QUEUE_DIR = "hold_queue"

    def __init__(
        self,
        fs_base: Path,
        decisions_log_path: Path | None = None,
    ):
        self._fs_base = fs_base
        self._review_queue_dir = fs_base / self.REVIEW_QUEUE_DIR
        self._hold_queue_dir = fs_base / self.HOLD_QUEUE_DIR
        self._decisions_log = decisions_log_path or fs_base / "logs" / "decisions.log"

        self._review_queue_dir.mkdir(parents=True, exist_ok=True)
        self._hold_queue_dir.mkdir(parents=True, exist_ok=True)
        self._decisions_log.parent.mkdir(parents=True, exist_ok=True)
        if not self._decisions_log.exists():
            self._decisions_log.touch()

        self._write_warroom, self._remove_warroom = _try_import_write_warroom_action()

    def _generate_action_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _write_action(self, action: OpsApprovalAction, queue_dir: Path) -> None:
        action_file = queue_dir / f"{action.action_id}.json"
        action_file.write_text(json.dumps(action.to_dict(), indent=2))

    def _read_action(self, action_id: str, queue_dir: Path) -> OpsApprovalAction | None:
        action_file = queue_dir / f"{action_id}.json"
        if not action_file.exists():
            return None
        try:
            data = json.loads(action_file.read_text())
            return OpsApprovalAction.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _remove_action(self, action_id: str, queue_dir: Path) -> bool:
        action_file = queue_dir / f"{action_id}.json"
        if action_file.exists():
            action_file.unlink()
            return True
        return False

    def _sync_warroom(self, action: OpsApprovalAction) -> None:
        """Write a canonical action file to mesh_dir/inbox/war_room/."""
        if self._write_warroom is None:
            return
        try:
            self._write_warroom(
                action.action_id,
                claw_role="ops",
                mode=action.mode,
                action_type=action.action_type,
                summary=action.content[:200] if action.content else "",
                timestamp=action.timestamp,
                recipient_role="ops",
                payload={
                    "entity_id": action.entity_id,
                    "content": action.content,
                    "context": action.context,
                },
            )
        except Exception:
            logger.debug("War room sync skipped for %s", action.action_id, exc_info=True)

    def _unsync_warroom(self, action_id: str) -> None:
        """Remove the canonical action file from mesh_dir/inbox/war_room/."""
        if self._remove_warroom is None:
            return
        try:
            self._remove_warroom(action_id)
        except Exception:
            logger.debug("War room unsync skipped for %s", action_id, exc_info=True)

    def queue_review(
        self,
        action_type: str,
        entity_id: str,
        content: str,
        context: dict[str, Any],
    ) -> str:
        action_id = self._generate_action_id()
        action = OpsApprovalAction(
            action_id=action_id,
            action_type=action_type,
            entity_id=entity_id,
            mode="REVIEW",
            content=content,
            context=context,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._write_action(action, self._review_queue_dir)
        self._sync_warroom(action)
        logger.info(
            "Queued REVIEW action %s: %s for %s", action_id, action_type, entity_id
        )
        return action_id

    def queue_hold(
        self,
        action_type: str,
        entity_id: str,
        content: str,
        context: dict[str, Any],
    ) -> str:
        action_id = self._generate_action_id()
        action = OpsApprovalAction(
            action_id=action_id,
            action_type=action_type,
            entity_id=entity_id,
            mode="HOLD",
            content=content,
            context=context,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._write_action(action, self._hold_queue_dir)
        self._sync_warroom(action)
        logger.info(
            "Queued HOLD action %s: %s for %s", action_id, action_type, entity_id
        )
        return action_id

    def log_auto(
        self,
        action_type: str,
        entity_id: str,
        content_preview: str,
    ) -> None:
        action = OpsApprovalAction(
            action_id=self._generate_action_id(),
            action_type=action_type,
            entity_id=entity_id,
            mode="AUTO",
            content=content_preview[:200],
            timestamp=datetime.now(timezone.utc).isoformat(),
            outcome="auto_executed",
        )
        self.log_decision(action)
        logger.info("Logged AUTO action: %s for %s", action_type, entity_id)

    def handle_approve(
        self,
        action_id: str,
        send_fn: Callable[[], None],
    ) -> bool:
        action = self._read_action(action_id, self._review_queue_dir)
        if not action:
            action = self._read_action(action_id, self._hold_queue_dir)
            if not action:
                logger.warning("Action %s not found in any queue", action_id)
                return False

        try:
            send_fn()
            action.outcome = "approved"
            self.log_decision(action)
            self._remove_action(action_id, self._review_queue_dir)
            self._remove_action(action_id, self._hold_queue_dir)
            self._unsync_warroom(action_id)
            logger.info("APPROVED action %s: %s", action_id, action.action_type)
            return True
        except Exception as e:
            logger.error("Failed to execute approved action %s: %s", action_id, e)
            action.outcome = f"execution_failed: {e}"
            self.log_decision(action)
            return False

    def handle_edit(
        self,
        action_id: str,
        edited_content: str,
        send_fn: Callable[[], None],
    ) -> bool:
        action = self._read_action(action_id, self._review_queue_dir)
        if not action:
            action = self._read_action(action_id, self._hold_queue_dir)
            if not action:
                logger.warning("Action %s not found in any queue", action_id)
                return False

        action.original_content = action.content
        action.content = edited_content

        try:
            send_fn()
            action.outcome = "edited_and_sent"
            self.log_decision(action)
            self._remove_action(action_id, self._review_queue_dir)
            self._remove_action(action_id, self._hold_queue_dir)
            self._unsync_warroom(action_id)
            logger.info("EDITED and sent action %s: %s", action_id, action.action_type)
            return True
        except Exception as e:
            logger.error("Failed to execute edited action %s: %s", action_id, e)
            action.outcome = f"execution_failed: {e}"
            self.log_decision(action)
            return False

    def handle_block(
        self,
        action_id: str,
        reason: str | None = None,
    ) -> bool:
        action = self._read_action(action_id, self._review_queue_dir)
        if not action:
            action = self._read_action(action_id, self._hold_queue_dir)
            if not action:
                logger.warning("Action %s not found in any queue", action_id)
                return False

        action.outcome = f"blocked: {reason or 'no_reason_provided'}"
        self.log_decision(action)
        self._remove_action(action_id, self._review_queue_dir)
        self._remove_action(action_id, self._hold_queue_dir)
        self._unsync_warroom(action_id)

        if action.action_type == "welcome_message":
            self._log_inquiry_declined(action.entity_id, reason)

        logger.info(
            "BLOCKED action %s: %s (reason: %s)", action_id, action.action_type, reason
        )
        return True

    def handle_hold_release(
        self,
        action_id: str,
        execute_fn: Callable[[], None],
    ) -> bool:
        action = self._read_action(action_id, self._hold_queue_dir)
        if not action:
            logger.warning("HOLD action %s not found", action_id)
            return False

        try:
            execute_fn()
            action.outcome = "hold_released"
            self.log_decision(action)
            self._remove_action(action_id, self._hold_queue_dir)
            self._unsync_warroom(action_id)
            logger.info("HOLD_RELEASED action %s: %s", action_id, action.action_type)
            return True
        except Exception as e:
            logger.error("Failed to execute hold release %s: %s", action_id, e)
            action.outcome = f"execution_failed: {e}"
            self.log_decision(action)
            return False

    def add_urgency_flag(
        self,
        action_id: str,
        hours_waiting: int,
    ) -> bool:
        action = self._read_action(action_id, self._review_queue_dir)
        if not action:
            action = self._read_action(action_id, self._hold_queue_dir)
            if not action:
                return False

        if hours_waiting >= 48:
            action.urgency_flag = "Response window closing"
        elif hours_waiting >= 24:
            action.urgency_flag = "No decision in 24h — client may disengage"

        action.hours_waiting = float(hours_waiting)
        self._write_action(
            action,
            self._review_queue_dir if action.mode == "REVIEW" else self._hold_queue_dir,
        )
        logger.info(
            "Added urgency flag to action %s: %s", action_id, action.urgency_flag
        )
        return True

    def log_decision(self, action: OpsApprovalAction) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_id": action.action_id,
            "action_type": action.action_type,
            "entity_id": action.entity_id,
            "mode": action.mode,
            "outcome": action.outcome,
            "content_preview": action.content[:200] if action.content else "",
            "original_content_preview": action.original_content[:200]
            if action.original_content
            else None,
            "context": action.context,
        }

        with self._decisions_log.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _log_inquiry_declined(self, inquiry_id: str, reason: str | None) -> None:
        declined_file = self._fs_base / "prospects" / inquiry_id / "declined.json"
        declined_file.parent.mkdir(parents=True, exist_ok=True)
        declined_file.write_text(
            json.dumps(
                {
                    "inquiry_id": inquiry_id,
                    "declined_at": datetime.now(timezone.utc).isoformat(),
                    "reason": reason or "welcome_message_blocked",
                }
            )
        )

    def get_review_queue(self) -> list[OpsApprovalAction]:
        actions: list[OpsApprovalAction] = []
        for action_file in self._review_queue_dir.glob("*.json"):
            try:
                data = json.loads(action_file.read_text())
                actions.append(OpsApprovalAction.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(actions, key=lambda a: a.timestamp)

    def get_hold_queue(self) -> list[OpsApprovalAction]:
        actions: list[OpsApprovalAction] = []
        for action_file in self._hold_queue_dir.glob("*.json"):
            try:
                data = json.loads(action_file.read_text())
                actions.append(OpsApprovalAction.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(actions, key=lambda a: a.timestamp)

    def get_action(self, action_id: str) -> OpsApprovalAction | None:
        action = self._read_action(action_id, self._review_queue_dir)
        if not action:
            action = self._read_action(action_id, self._hold_queue_dir)
        return action
