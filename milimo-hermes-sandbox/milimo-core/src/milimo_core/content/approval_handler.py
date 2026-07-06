# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Content Approval Handler

Handles all three operator decisions on content drafts:
- APPROVE: Move to approved, schedule or publish
- EDIT: Apply operator edits, potentially re-queue
- BLOCK: Move to rejected, log for learning
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from .content_generator import Draft

logger = logging.getLogger("milimo.approval_handler")


def _try_import_warroom_bridge():
    try:
        from warroom_bridge import write_warroom_action, remove_warroom_action
        return write_warroom_action, remove_warroom_action
    except ImportError:
        return None, None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUEUE_THRESHOLD = 0.20  # 20% content change triggers re-review
REJECTION_ALERT_THRESHOLD = 3  # 3 rejections on same brief triggers alert


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ApprovalResult:
    """Result of an approval action."""

    success: bool
    draft_id: str
    action: str
    message: str
    requeued: bool = False
    new_draft_id: str | None = None


@dataclass
class EditDelta:
    """Delta between original and edited content."""

    original_length: int
    edited_length: int
    changed_chars: int
    change_ratio: float
    significant: bool


@dataclass
class RejectionAlert:
    """Alert for repeated rejections on a brief."""

    brief_id: str
    rejection_count: int
    message: str


# ---------------------------------------------------------------------------
# Content Approval Handler
# ---------------------------------------------------------------------------


class ContentApprovalHandler:
    """
    Handles operator decisions on content drafts.

    Implements the exact approval flow from the spec:
    - Approve: Move to approved/, schedule/publish
    - Edit: Preserve original, apply changes, check threshold
    - Block: Move to rejected/, log for learning
    """

    def __init__(
        self,
        fs: ContentFilesystemInit,
        operational_log: ContentOperationalLog,
        war_room: Any | None = None,
        on_publish: Callable[[Draft], None] | None = None,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._war_room = war_room
        self._on_publish = on_publish
        _w_write, _w_remove = _try_import_warroom_bridge()
        self._write_warroom = _w_write
        self._remove_warroom = _w_remove

    def _make_warroom_payload(self, draft: Draft) -> dict[str, Any]:
        return {
            "draft_id": draft.draft_id,
            "platform": draft.platform,
            "client_id": draft.client_id,
            "project_id": draft.project_id,
            "brief_id": draft.brief_id,
            "content_preview": (draft.processed_content or "")[:200],
            "scheduled_time": draft.scheduled_time,
        }

    def sync_warroom(self, draft: Draft) -> None:
        if self._write_warroom is None:
            return
        try:
            import datetime as _dt
            self._write_warroom(
                draft.draft_id,
                claw_role="content",
                mode="REVIEW",
                action_type="draft_review",
                summary=f"Draft for {draft.platform}: {draft.brief_id or 'no brief'}",
                timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(),
                recipient_role="content",
                payload=self._make_warroom_payload(draft),
            )
        except Exception:
            logger.debug("War room sync skipped for draft %s", draft.draft_id, exc_info=True)

    def unsync_warroom(self, draft_id: str) -> None:
        if self._remove_warroom is None:
            return
        try:
            self._remove_warroom(draft_id)
        except Exception:
            logger.debug("War room unsync skipped for draft %s", draft_id, exc_info=True)

    def handle_approve(
        self,
        draft_id: str,
        action_id: str,
        publish_immediately: bool = False,
    ) -> ApprovalResult:
        """
        Handle APPROVE decision on a draft.

        1. Move draft: pending/ → approved/
        2. If scheduled_time: write to calendar/scheduled/
        3. Log to approvals.log
        4. Log to operational.log
        5. If publish_immediately: trigger publisher
        """
        pending_path = self._fs.get_draft_path("pending", draft_id)
        if not pending_path.exists():
            return ApprovalResult(
                success=False,
                draft_id=draft_id,
                action="approve",
                message=f"Draft not found: {draft_id}",
            )

        draft_data = json.loads(pending_path.read_text())
        draft = Draft.from_dict(draft_data)

        draft.status = "approved"
        approved_path = self._fs.get_draft_path("approved", draft_id)
        approved_path.parent.mkdir(parents=True, exist_ok=True)
        approved_path.write_text(json.dumps(draft.to_dict(), indent=2))

        pending_path.unlink()

        if draft.scheduled_time:
            self._schedule_draft(draft)

        self._log_approval(draft_id, "APPROVED", action_id)

        self._log.append(
            LogEntry(
                action_type="draft_approved",
                entity_id=draft_id,
                outcome="success",
                client_id=draft.client_id,
                details={
                    "action_id": action_id,
                    "platform": draft.platform,
                    "scheduled_time": draft.scheduled_time,
                },
            )
        )

        if publish_immediately and self._on_publish:
            self._on_publish(draft)

        self.unsync_warroom(draft_id)

        logger.info("Draft %s approved (action %s)", draft_id, action_id)

        return ApprovalResult(
            success=True,
            draft_id=draft_id,
            action="approve",
            message=f"Draft approved and moved to {approved_path}",
        )

    def handle_edit(
        self,
        draft_id: str,
        edited_content: str,
        action_id: str,
    ) -> ApprovalResult:
        """
        Handle EDIT decision on a draft.

        1. Load original from pending/
        2. Save original as {draft_id}_original.json
        3. Calculate edit delta
        4. If significant: create new draft, re-queue for review
        5. If minor: auto-approve edited version
        """
        pending_path = self._fs.get_draft_path("pending", draft_id)
        if not pending_path.exists():
            return ApprovalResult(
                success=False,
                draft_id=draft_id,
                action="edit",
                message=f"Draft not found: {draft_id}",
            )

        draft_data = json.loads(pending_path.read_text())
        draft = Draft.from_dict(draft_data)

        original_path = (
            self._fs.BASE / "drafts" / "pending" / f"{draft_id}_original.json"
        )
        original_path.write_text(json.dumps(draft.to_dict(), indent=2))

        delta = self._calculate_edit_delta(draft.processed_content, edited_content)

        draft.processed_content = edited_content
        draft.tools_applied.append("operator_edit")

        self._log.append(
            LogEntry(
                action_type="draft_edited",
                entity_id=draft_id,
                outcome="success",
                client_id=draft.client_id,
                details={
                    "action_id": action_id,
                    "original_length": delta.original_length,
                    "edited_length": delta.edited_length,
                    "change_ratio": delta.change_ratio,
                    "significant": delta.significant,
                },
            )
        )

        if delta.significant:
            new_draft_id = f"{draft_id}_edited"
            draft.draft_id = new_draft_id
            draft.status = "pending"

            new_path = self._fs.get_draft_path("pending", new_draft_id)
            new_path.write_text(json.dumps(draft.to_dict(), indent=2))

            self._log.append(
                LogEntry(
                    action_type="draft_requeued",
                    entity_id=new_draft_id,
                    outcome="success",
                    details={
                        "original_draft": draft_id,
                        "change_ratio": delta.change_ratio,
                    },
                )
            )

            logger.info(
                "Draft %s edited significantly (%.1f%% changed), re-queued as %s",
                draft_id,
                delta.change_ratio * 100,
                new_draft_id,
            )

            return ApprovalResult(
                success=True,
                draft_id=draft_id,
                action="edit",
                message=f"Edit significant, re-queued as {new_draft_id}",
                requeued=True,
                new_draft_id=new_draft_id,
            )

        else:
            draft.status = "approved"
            approved_path = self._fs.get_draft_path("approved", draft_id)
            approved_path.parent.mkdir(parents=True, exist_ok=True)
            approved_path.write_text(json.dumps(draft.to_dict(), indent=2))

            pending_path.unlink()
            original_path.unlink()

            self._log_approval(draft_id, "APPROVED_AFTER_EDIT", action_id)

            logger.info(
                "Draft %s edited (minor %.1f%%), auto-approved",
                draft_id,
                delta.change_ratio * 100,
            )

            return ApprovalResult(
                success=True,
                draft_id=draft_id,
                action="edit",
                message="Edit minor, auto-approved",
            )

    def handle_block(
        self,
        draft_id: str,
        action_id: str,
        reason: str | None = None,
    ) -> ApprovalResult:
        """
        Handle BLOCK decision on a draft.

        1. Move draft: pending/ → rejected/
        2. Log to approvals.log with reason
        3. Log to operational.log
        4. Write rejection signal for learning
        5. Check if brief has 3+ rejections, alert if so
        """
        pending_path = self._fs.get_draft_path("pending", draft_id)
        if not pending_path.exists():
            return ApprovalResult(
                success=False,
                draft_id=draft_id,
                action="block",
                message=f"Draft not found: {draft_id}",
            )

        draft_data = json.loads(pending_path.read_text())
        draft = Draft.from_dict(draft_data)

        draft.status = "rejected"
        rejected_path = self._fs.get_draft_path("rejected", draft_id)
        rejected_path.parent.mkdir(parents=True, exist_ok=True)
        rejected_path.write_text(json.dumps(draft.to_dict(), indent=2))

        pending_path.unlink()

        reason_str = reason or "No reason provided"
        self._log_approval(draft_id, "BLOCKED", action_id, reason_str)

        self.unsync_warroom(draft_id)

        self._log.append(
            LogEntry(
                action_type="draft_rejected",
                entity_id=draft_id,
                outcome="success",
                client_id=draft.client_id,
                details={
                    "action_id": action_id,
                    "reason": reason_str,
                    "platform": draft.platform,
                },
            )
        )

        alert = self._check_rejection_alert(draft)
        if alert:
            self._send_rejection_alert(alert)

        logger.info("Draft %s rejected: %s", draft_id, reason_str)

        return ApprovalResult(
            success=True,
            draft_id=draft_id,
            action="block",
            message=f"Draft rejected and moved to {rejected_path}",
        )

    def _calculate_edit_delta(self, original: str, edited: str) -> EditDelta:
        """Calculate the delta between original and edited content."""
        original_len = len(original)
        edited_len = len(edited)

        if original_len == 0:
            change_ratio = 1.0 if edited_len > 0 else 0.0
        else:
            changed = 0
            max_len = max(original_len, edited_len)
            for i in range(max_len):
                orig_char = original[i] if i < original_len else ""
                edit_char = edited[i] if i < edited_len else ""
                if orig_char != edit_char:
                    changed += 1

            change_ratio = changed / original_len

        return EditDelta(
            original_length=original_len,
            edited_length=edited_len,
            changed_chars=int(change_ratio * original_len),
            change_ratio=change_ratio,
            significant=change_ratio > REQUEUE_THRESHOLD,
        )

    def _schedule_draft(self, draft: Draft) -> None:
        """Write draft to calendar/scheduled/."""
        if not draft.scheduled_time:
            return

        calendar_path = (
            self._fs.BASE / "calendar" / "scheduled" / f"{draft.draft_id}.json"
        )
        calendar_path.parent.mkdir(parents=True, exist_ok=True)
        calendar_path.write_text(
            json.dumps(
                {
                    "draft_id": draft.draft_id,
                    "platform": draft.platform,
                    "client_id": draft.client_id,
                    "scheduled_time": draft.scheduled_time,
                    "content_preview": draft.processed_content[:100],
                },
                indent=2,
            )
        )

        logger.debug("Draft %s scheduled for %s", draft.draft_id, draft.scheduled_time)

    def _log_approval(
        self,
        draft_id: str,
        decision: str,
        action_id: str,
        reason: str | None = None,
    ) -> None:
        """Log to approvals.log."""
        approvals_log = self._fs.BASE / "logs" / "approvals.log"
        approvals_log.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "draft_id": draft_id,
            "decision": decision,
            "action_id": action_id,
        }
        if reason:
            entry["reason"] = reason

        with approvals_log.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _check_rejection_alert(self, draft: Draft) -> RejectionAlert | None:
        """Check if brief has reached rejection threshold."""
        if not draft.project_id:
            return None

        rejected_dir = self._fs.BASE / "drafts" / "rejected"
        if not rejected_dir.exists():
            return None

        rejection_count = 0
        for rejected_file in rejected_dir.glob("*.json"):
            try:
                data = json.loads(rejected_file.read_text())
                if data.get("project_id") == draft.project_id:
                    rejection_count += 1
            except Exception:
                continue

        if rejection_count >= REJECTION_ALERT_THRESHOLD:
            return RejectionAlert(
                brief_id=draft.project_id,
                rejection_count=rejection_count,
                message=f"Repeated rejections on brief {draft.project_id} — may need clarification",
            )

        return None

    def get_pending_drafts(self) -> list[dict]:
        pending_dir = self._fs.BASE / "drafts" / "pending"
        if not pending_dir.exists():
            return []
        drafts = []
        for path in pending_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                drafts.append(
                    {
                        "draft_id": data.get("draft_id", path.stem),
                        "action_id": data.get("draft_id", path.stem),
                        "action_type": "draft_review",
                        "status": "pending_review",
                        "summary": (
                            f"Draft for {data.get('platform', 'unknown')}: "
                            f"{data.get('brief_id', 'no brief')}"
                        ),
                        "payload": data,
                    }
                )
            except Exception:
                continue
        return drafts

    def _send_rejection_alert(self, alert: RejectionAlert) -> None:
        """Send rejection alert to War Room."""
        logger.warning(
            "Rejection alert: %s (count: %d)",
            alert.message,
            alert.rejection_count,
        )

        if self._war_room:
            self._war_room.queue_action(
                claw="content",
                action_type="rejection_alert",
                payload={
                    "brief_id": alert.brief_id,
                    "rejection_count": alert.rejection_count,
                    "message": alert.message,
                },
            )
