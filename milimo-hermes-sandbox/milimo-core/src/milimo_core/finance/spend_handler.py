# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Spend Handler.

Mirror of approval_handler.py's two-stage gate, but for the *outbound*
direction of money: agent-initiated purchases via the Hermes
`stripe-link-cli` skill (NVIDIA x Stripe x Nous Research Hermes Agent
Accelerated Business Hackathon, 2026-06).

FinanceApprovalHandler governs receivables — invoices MilimoClaw sends
and gets paid for. SpendApprovalHandler governs payables — purchases a
claw wants to make on the operator's behalf (buying an API credit
bundle, provisioning a SaaS dependency, paying a per-call 402 API,
etc).

Same two-stage shape, opposite direction:

    Stage 1 (REVIEW): "Agent wants to buy X for $Y, because Z"
                       approve -> HOLD, never spends
    Stage 2 (HOLD):    "Ready to spend — this will charge the card"
                       release -> invokes `link-cli spend-request create`

Two independent human gates sit between the agent and the charge:
1. War Room HOLD release (this file)
2. Stripe Link's own in-app approval on the user's phone (the CLI's
   `--request-approval` flag — Hermes cannot self-approve that either)

Every decision logged to decisions.log, same file format and stage
vocabulary FinanceApprovalHandler already uses, so War Room UIs that
render `stage: review|hold` need no changes to show spend requests
alongside invoices.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import json
import logging
import subprocess

logger = logging.getLogger("milimo.spend_handler")

from ..milimo_paths import claw_base

from .finance_init import FinanceOperationalLog, FinanceLogEntry


@dataclass
class SpendRequest:
    """A single agent-initiated purchase awaiting approval."""

    spend_id: str
    claw: str  # which claw is asking to spend (build, ops, content, ...)
    merchant_name: str
    merchant_url: str
    amount_cents: int
    currency: str
    justification: str  # one sentence: what + why
    payment_method_id: str | None = None
    credential_type: Literal["card", "shared_payment_token"] = "card"
    status: Literal["pending_review", "held", "released", "blocked", "cancelled"] = (
        "pending_review"
    )
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    link_spend_request_id: str | None = None  # lsrq_... once created with link-cli


class SpendApprovalHandler:
    """
    Handles all War Room approval interactions for agent-initiated
    spend via stripe-link-cli.

    Stage 1 (REVIEW): does this purchase make sense — approve/edit/block
    Stage 2 (HOLD): transmission gate — release calls link-cli, which
                    itself blocks on the user's Link app approval

    Mirrors FinanceApprovalHandler exactly so the two queues (invoices
    in, spend out) can share one War Room view and one decisions.log.
    """

    def __init__(
        self,
        operational_log: FinanceOperationalLog,
        decisions_path: Path | None = None,
        spend_log_path: Path | None = None,
        link_cli_path: str = "link-cli",
        daily_spend_cap_cents: int = 10_000,
        test_mode: bool = True,
    ):
        self.operational_log = operational_log
        self.decisions_path = (
            decisions_path or claw_base("finance") / "logs/decisions.log"
        )
        self.spend_log_path = (
            spend_log_path or claw_base("finance") / "logs/agent-spend.log"
        )
        self.link_cli_path = link_cli_path
        self.daily_spend_cap_cents = daily_spend_cap_cents
        self.test_mode = test_mode
        self._requests: dict[str, SpendRequest] = {}

    def _get_request(self, spend_id: str) -> SpendRequest:
        """Retrieve request from memory or recover it from the decisions log."""
        if spend_id in self._requests:
            return self._requests[spend_id]

        # Reconstruct request from decisions.log
        if self.decisions_path.exists():
            try:
                with open(self.decisions_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        dec = json.loads(line)
                        if (
                            dec.get("spend_id") == spend_id
                            and dec.get("stage") == "review"
                            and dec.get("action_type") == "queued"
                        ):
                            details = dec.get("details", {})
                            req = SpendRequest(
                                spend_id=spend_id,
                                claw=details.get("claw", ""),
                                merchant_name=details.get("merchant_name", ""),
                                merchant_url=details.get("merchant_url", ""),
                                amount_cents=details.get("amount_cents", 0),
                                currency=details.get("currency", "USD"),
                                justification=details.get("justification", ""),
                                payment_method_id=details.get("payment_method_id"),
                                credential_type=details.get("credential_type", "card"),
                            )
                            self._requests[spend_id] = req
            except Exception as e:
                logger.error("Failed to recover request %s from log: %s", spend_id, e)

        if spend_id in self._requests:
            # Replay any subsequent state updates
            req = self._requests[spend_id]
            try:
                with open(self.decisions_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        dec = json.loads(line)
                        if dec.get("spend_id") == spend_id:
                            action_type = dec.get("action_type")
                            stage = dec.get("stage")
                            if stage == "review" and action_type == "approve":
                                req.status = "held"
                            elif stage == "review" and action_type == "block":
                                req.status = "blocked"
                            elif stage == "hold" and action_type == "release":
                                req.status = "released"
                                req.link_spend_request_id = dec.get("details", {}).get("link_spend_request_id")
                            elif stage == "hold" and action_type == "cancel":
                                req.status = "cancelled"
            except Exception as e:
                logger.error("Failed to replay states for request %s: %s", spend_id, e)
            return req

        raise KeyError(f"Spend request {spend_id} not found and could not be recovered.")

    # ------------------------------------------------------------------
    # Stage 1: REVIEW
    # ------------------------------------------------------------------

    def queue_spend_review(self, request: SpendRequest) -> str:
        """
        Add a proposed purchase to the War Room REVIEW queue.

        War Room card shows:
        Requesting claw, merchant, amount, justification, credential type.
        Available actions: APPROVE, EDIT, BLOCK
        """
        action_id = f"spend-review-{request.spend_id}"
        self._requests[request.spend_id] = request

        if request.amount_cents > self.daily_spend_cap_cents:
            request.status = "blocked"
            self._log_decision(
                {
                    "action_id": action_id,
                    "spend_id": request.spend_id,
                    "stage": "review",
                    "action_type": "auto_blocked",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "operator": "system",
                    "details": {
                        "reason": "exceeds_daily_spend_cap",
                        "amount_cents": request.amount_cents,
                        "cap_cents": self.daily_spend_cap_cents,
                    },
                }
            )
            return action_id

        review_entry = {
            "action_id": action_id,
            "spend_id": request.spend_id,
            "stage": "review",
            "action_type": "queued",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "system",
            "details": {
                "claw": request.claw,
                "merchant_name": request.merchant_name,
                "merchant_url": request.merchant_url,
                "amount_cents": request.amount_cents,
                "currency": request.currency,
                "justification": request.justification,
                "credential_type": request.credential_type,
            },
        }
        self._log_decision(review_entry)
        return action_id

    def handle_review_approve(self, action_id: str) -> str:
        """
        REVIEW approve -> queues HOLD (stage 2). Does NOT spend yet.
        Returns the new hold action_id.
        """
        spend_id = action_id.replace("spend-review-", "")
        request = self._get_request(spend_id)
        request.status = "held"

        hold_action_id = self.queue_spend_hold(request)

        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": spend_id,
                "stage": "review",
                "action_type": "approve",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": "operator",
                "details": {"outcome": "moved_to_hold"},
            }
        )
        return hold_action_id

    def handle_review_edit(
        self, action_id: str, amount_cents: int, justification: str
    ) -> None:
        """REVIEW edit -> re-queues REVIEW with the corrected amount/reason."""
        spend_id = action_id.replace("spend-review-", "")
        request = self._get_request(spend_id)
        request.amount_cents = amount_cents
        request.justification = justification

        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": spend_id,
                "stage": "review",
                "action_type": "edit",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": "operator",
                "details": {
                    "amount_cents": amount_cents,
                    "justification": justification,
                },
            }
        )

    def handle_review_block(self, action_id: str, reason: str) -> None:
        """REVIEW block -> purchase never happens."""
        spend_id = action_id.replace("spend-review-", "")
        self._get_request(spend_id).status = "blocked"

        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": spend_id,
                "stage": "review",
                "action_type": "block",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": "operator",
                "details": {"reason": reason},
            }
        )

    # ------------------------------------------------------------------
    # Stage 2: HOLD
    # ------------------------------------------------------------------

    def queue_spend_hold(self, request: SpendRequest) -> str:
        """
        Add an approved purchase to the War Room HOLD queue.

        War Room card shows:
        "Approved — ready to charge {merchant_name}"
        Amount, credential type.
        Warning: "This will create a Stripe Link spend request and
        ping the user's Link app for final approval."
        Available actions: RELEASE HOLD (spends), CANCEL
        """
        action_id = f"spend-hold-{request.spend_id}"

        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": request.spend_id,
                "stage": "hold",
                "action_type": "queued",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": "system",
                "details": {
                    "merchant_name": request.merchant_name,
                    "amount_cents": request.amount_cents,
                    "warning": (
                        "This will create a Stripe Link spend request and "
                        "ping the user's Link app for final approval."
                    ),
                },
            }
        )
        return action_id

    def handle_hold_release(self, action_id: str, operator_id: str | None = None) -> SpendRequest:
        """
        HOLD release -> THIS SPENDS (pending the user's Link app tap).

        Shells out to `link-cli spend-request create --request-approval`.
        That call blocks until the user approves/denies in the Link app
        or it times out — Hermes cannot self-approve that step either.
        Exit code != 0 (deny/timeout) is treated as a failed release and
        does not mark the request released.
        """
        spend_id = action_id.replace("spend-hold-", "")
        request = self._get_request(spend_id)

        cmd = [
            self.link_cli_path,
            "spend-request",
            "create",
            "--merchant-name",
            request.merchant_name,
            "--merchant-url",
            request.merchant_url,
            "--context",
            request.justification,
            "--amount",
            str(request.amount_cents),
            "--total",
            f"type:total,display_text:Total,amount:{request.amount_cents}",
            "--request-approval",
            "--format",
            "json",
        ]
        if request.payment_method_id:
            cmd += ["--payment-method-id", request.payment_method_id]
        if request.credential_type == "shared_payment_token":
            cmd += ["--credential-type", "shared_payment_token"]
        if self.test_mode:
            cmd += ["--test"]

        import os
        env = {**os.environ}
        if operator_id:
            safe_op_id = "".join(c for c in operator_id if c.isalnum() or c in ("-", "_")).strip()
            if safe_op_id and safe_op_id not in ("system", "operator", "sandbox"):
                base_config_dir = "/sandbox/.config" if os.path.exists("/sandbox") else os.path.expanduser("~/.config")
                user_config_dir = f"{base_config_dir}/users/{safe_op_id}"
                env["XDG_CONFIG_HOME"] = user_config_dir
                logger.info("Isolating link-cli XDG_CONFIG_HOME for operator %s to %s", safe_op_id, user_config_dir)
            else:
                if os.path.exists("/sandbox/.config"):
                    env["XDG_CONFIG_HOME"] = "/sandbox/.config"
                    logger.info("Setting default sandbox XDG_CONFIG_HOME to /sandbox/.config")
        else:
            if os.path.exists("/sandbox/.config"):
                env["XDG_CONFIG_HOME"] = "/sandbox/.config"
                logger.info("Setting default sandbox XDG_CONFIG_HOME to /sandbox/.config")

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=310, env=env)

        if proc.returncode != 0:
            request.status = "blocked"
            self._log_decision(
                {
                    "action_id": action_id,
                    "spend_id": spend_id,
                    "stage": "hold",
                    "action_type": "release_failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "operator": "operator",
                    "details": {
                        "outcome": "denied_or_timed_out",
                        "stderr": proc.stderr[-500:],
                    },
                }
            )
            return request

        try:
            payload = json.loads(proc.stdout)
            if isinstance(payload, list) and len(payload) > 0:
                payload = payload[0]
            if isinstance(payload, dict):
                request.link_spend_request_id = payload.get("id")
        except (json.JSONDecodeError, AttributeError, IndexError):
            pass

        request.status = "released"
        self._append_spend_log(request)

        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": spend_id,
                "stage": "hold",
                "action_type": "release",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": "operator",
                "details": {
                    "outcome": "purchase_completed",
                    "link_spend_request_id": request.link_spend_request_id,
                },
            }
        )
        return request

    def handle_hold_cancel(self, action_id: str, reason: str = "") -> None:
        """Cancel the HOLD — purchase never made, request stays logged."""
        spend_id = action_id.replace("spend-hold-", "")
        self._get_request(spend_id).status = "cancelled"

        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": spend_id,
                "stage": "hold",
                "action_type": "cancel",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": "operator",
                "details": {"reason": reason},
            }
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append_spend_log(self, request: SpendRequest) -> None:
        import fcntl

        self.spend_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.spend_log_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(
                    json.dumps(
                        {
                            "spend_id": request.spend_id,
                            "claw": request.claw,
                            "merchant_name": request.merchant_name,
                            "amount_cents": request.amount_cents,
                            "currency": request.currency,
                            "link_spend_request_id": request.link_spend_request_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    + "\n"
                )
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _log_decision(self, decision: dict) -> None:
        import fcntl

        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.decisions_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(decision) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        entry = FinanceLogEntry(
            timestamp=decision["timestamp"],
            action_type=f"approval_{decision['stage']}_{decision['action_type']}",
            entity_id=decision.get("spend_id", ""),
            amount=decision.get("details", {}).get("amount_cents", 0) / 100,
            outcome="logged",
            details=decision,
        )
        self.operational_log.append(entry)
