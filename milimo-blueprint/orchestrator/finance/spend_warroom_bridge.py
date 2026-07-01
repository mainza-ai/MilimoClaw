# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Spend <-> Solo War Room Bridge.

Wires SpendApprovalHandler's two-stage gate (REVIEW -> HOLD -> link-cli)
into the existing SoloWarRoom action queue, so a spend request shows up
in the *same* unified queue as invoices, PRs, and deploys, and is driven
by the *same* keyboard shortcuts the TUI already has:

    A  approve   (REVIEW -> HOLD)
    R  release   (HOLD -> spends, pending Link app confirmation)
    B  block     (kills it)

Nothing about the TUI itself needs to change — solo_warroom.py is
already generic over claw/action_type/payload. This module is the glue
that:

1. Turns an agent's purchase request into a War Room REVIEW action
   instead of a raw spend_handler call, respecting operator_policy's
   approval_modes (see templates/solo-founder.yaml: finance.spend_review,
   finance.spend_hold).
2. When the operator approves the REVIEW action, automatically queues
   the resulting HOLD action — same pattern as invoice_generation ->
   invoice_send already uses.
3. When the operator releases the HOLD, calls SpendApprovalHandler,
   which shells out to `link-cli spend-request create
   --request-approval` — a second, independent approval gate on the
   user's phone that this bridge cannot skip.

Usage (wherever Finance Claw is wired up alongside SoloWarRoom):

    bridge = SpendWarRoomBridge(spend_handler, solo_warroom)
    wr_action_id = bridge.submit_spend_request(request)
    # ... operator presses 'A' in the TUI on that action ...
    bridge.approve_review(wr_action_id)
    # ... a new HOLD action appears in the same queue, operator presses 'R' ...
    bridge.release_hold(hold_action_id)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .spend_handler import SpendApprovalHandler, SpendRequest

logger = logging.getLogger("milimo.spend_warroom_bridge")


class SpendWarRoomBridge:
    """Connects SpendApprovalHandler's REVIEW/HOLD gate to SoloWarRoom."""

    def __init__(self, spend_handler: SpendApprovalHandler, solo_warroom: Any):
        self.spend_handler = spend_handler
        self.solo_warroom = solo_warroom
        # War Room action.id -> internal spend_handler action_id
        self._review_actions: dict[str, str] = {}
        self._hold_actions: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit_spend_request(self, request: SpendRequest) -> Optional[str]:
        """
        A claw calls this instead of touching SpendApprovalHandler or
        link-cli directly. Returns the War Room action id, or None if
        the request was auto-blocked by the daily spend cap before it
        ever reached a human.
        """
        spend_action_id = self.spend_handler.queue_spend_review(request)

        if request.status == "blocked":
            logger.warning(
                "Spend request %s auto-blocked (over daily cap), never reached War Room",
                request.spend_id,
            )
            return None

        wr_action = self.solo_warroom.queue_action(
            claw="finance",
            action_type="spend_review",
            payload={
                "spend_action_id": spend_action_id,
                "spend_id": request.spend_id,
                "requesting_claw": request.claw,
                "merchant_name": request.merchant_name,
                "merchant_url": request.merchant_url,
                "amount_cents": request.amount_cents,
                "currency": request.currency,
                "justification": request.justification,
                "summary": (
                    f"{request.claw} wants to buy from {request.merchant_name}: "
                    f"${request.amount_cents / 100:.2f} — {request.justification}"
                ),
            },
        )
        self._review_actions[wr_action.id] = spend_action_id
        return wr_action.id

    # ------------------------------------------------------------------
    # Stage 1: REVIEW
    # ------------------------------------------------------------------

    def approve_review(self, warroom_action_id: str) -> Optional[Any]:
        """
        Operator pressed 'A' on a spend_review action.

        Moves the underlying spend request from REVIEW to HOLD, then
        queues a *new* War Room action (action_type="spend_hold") in
        the same queue so the operator sees it on their next pass.
        """
        spend_action_id = self._review_actions.get(warroom_action_id)
        if not spend_action_id:
            logger.warning("No spend request tracked for %s", warroom_action_id)
            return None

        def _execute() -> None:
            hold_action_id = self.spend_handler.handle_review_approve(spend_action_id)
            spend_id = spend_action_id.replace("spend-review-", "")
            request = self.spend_handler._requests[spend_id]

            wr_hold_action = self.solo_warroom.queue_action(
                claw="finance",
                action_type="spend_hold",
                payload={
                    "spend_action_id": hold_action_id,
                    "spend_id": request.spend_id,
                    "requesting_claw": request.claw,
                    "merchant_name": request.merchant_name,
                    "amount_cents": request.amount_cents,
                    "summary": (
                        f"Ready to charge {request.merchant_name}: "
                        f"${request.amount_cents / 100:.2f} — release sends a "
                        f"Link app approval request to your phone"
                    ),
                },
            )
            self._hold_actions[wr_hold_action.id] = hold_action_id

        return self.solo_warroom.handle_approve(warroom_action_id, execute_fn=_execute)

    def block_review(self, warroom_action_id: str, reason: str = "") -> Optional[Any]:
        """Operator pressed 'B' on a spend_review action. Purchase never happens."""
        spend_action_id = self._review_actions.get(warroom_action_id)
        if not spend_action_id:
            return None

        action = self.solo_warroom.block(warroom_action_id, reason)
        self.spend_handler.handle_review_block(spend_action_id, reason)
        return action

    # ------------------------------------------------------------------
    # Stage 2: HOLD
    # ------------------------------------------------------------------

    def release_hold(self, warroom_action_id: str) -> tuple[Optional[Any], Any]:
        """
        Operator pressed 'R' on a spend_hold action.

        This is the only path that actually spends money. It still
        blocks on the user's Link app approval inside
        SpendApprovalHandler.handle_hold_release() — pressing R here
        does not guarantee the charge goes through.

        Returns (war_room_action, spend_request) — check
        spend_request.status == "released" to know whether the charge
        actually completed vs was denied/timed out on the Link side.
        """
        hold_action_id = self._hold_actions.get(warroom_action_id)
        if not hold_action_id:
            logger.warning("No HOLD tracked for %s", warroom_action_id)
            return None, None

        result: dict[str, Any] = {}

        def _execute() -> None:
            result["request"] = self.spend_handler.handle_hold_release(hold_action_id)

        action = self.solo_warroom.handle_hold_release(
            warroom_action_id, execute_fn=_execute
        )
        return action, result.get("request")

    def cancel_hold(self, warroom_action_id: str, reason: str = "") -> Optional[Any]:
        """Operator pressed 'B' on a spend_hold action. Stays approved, never charged."""
        hold_action_id = self._hold_actions.get(warroom_action_id)
        if not hold_action_id:
            return None

        action = self.solo_warroom.block(warroom_action_id, reason)
        self.spend_handler.handle_hold_cancel(hold_action_id, reason)
        return action
