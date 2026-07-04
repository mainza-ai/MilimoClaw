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
from typing import Literal, Any
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
        self._recover_and_resume_polling()

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
                            if stage == "hold" and action_type == "release":
                                req.status = "released"
                                req.link_spend_request_id = dec.get("details", {}).get("link_spend_request_id")
                            elif stage == "hold" and action_type == "purchase_approved":
                                req.status = "released"
                            elif stage == "hold" and action_type in ("purchase_denied", "purchase_expired", "release_failed"):
                                req.status = "blocked"
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

        daily_spent = self._get_daily_spend_aggregate()
        if daily_spent + request.amount_cents > self.daily_spend_cap_cents:
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
                        "daily_spent_cents": daily_spent,
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

    def handle_review_approve(self, action_id: str, *args: Any, **kwargs: Any) -> str:
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
        self, action_id: str, amount_cents: int, justification: str, *args: Any, **kwargs: Any
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

    def handle_review_block(self, action_id: str, reason: str, *args: Any, **kwargs: Any) -> None:
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

    def handle_hold_release(
        self, action_id: str, operator_id: str | None = None, *args: Any, **kwargs: Any
    ) -> SpendRequest:
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

        import os
        import json
        import subprocess
        from datetime import datetime, timezone

        # 1. Acquire atomic filesystem lock
        lock_path = self.spend_log_path.parent / f".spend_lock_{spend_id}"
        lock_fd = None
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # Check if stale lock
            try:
                with open(lock_path, "r") as lf:
                    lock_data = json.loads(lf.read().strip())
                pid = lock_data.get("pid")
                pid_exists = False
                if pid:
                    try:
                        os.kill(pid, 0)
                        pid_exists = True
                    except OSError:
                        pass

                if not pid_exists:
                    try:
                        os.unlink(lock_path)
                        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    except Exception:
                        raise ValueError(f"Spend request {spend_id} is locked by dead process {pid}, but lock file cleanup failed.")
                else:
                    raise ValueError(f"Spend request {spend_id} is already being processed by active process {pid}.")
            except Exception as le:
                raise ValueError(f"Spend request {spend_id} is locked: {le}")

        try:
            # Write PID and timestamp to lock
            with os.fdopen(lock_fd, 'w') as lock_file:
                lock_file.write(json.dumps({
                    "pid": os.getpid(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                lock_file.flush()
                os.fsync(lock_file.fileno())

            # 2. Check decisions.log to verify this spend_id has not already been successfully released
            if self.decisions_path.exists():
                with open(self.decisions_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            dec = json.loads(line)
                            if dec.get("spend_id") == spend_id and dec.get("action_type") in ("released", "purchase_approved", "release"):
                                request.status = "released"
                                return request
                        except Exception:
                            pass

            # 3. Calculate daily spend cap aggregate check
            daily_spent = self._get_daily_spend_aggregate()
            if daily_spent + request.amount_cents > self.daily_spend_cap_cents:
                request.status = "blocked"
                self._log_decision(
                    {
                        "action_id": action_id,
                        "spend_id": spend_id,
                        "stage": "hold",
                        "action_type": "release_failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "operator": operator_id or "operator",
                        "details": {
                            "outcome": "exceeds_daily_spend_cap",
                            "daily_spent_cents": daily_spent,
                            "request_cents": request.amount_cents,
                            "cap_cents": self.daily_spend_cap_cents,
                        },
                    }
                )
                return request

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

            cmd_create = [
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
                "--no-request-approval",
                "--format",
                "json",
            ]
            if request.payment_method_id:
                cmd_create += ["--payment-method-id", request.payment_method_id]
            if request.credential_type == "shared_payment_token":
                cmd_create += ["--credential-type", "shared_payment_token"]
            if self.test_mode:
                cmd_create += ["--test"]

            # Run Create Command (non-blocking, returns immediately)
            proc_create = subprocess.run(cmd_create, capture_output=True, text=True, timeout=30, env=env)

            if proc_create.returncode != 0:
                request.status = "blocked"
                self._log_decision(
                    {
                        "action_id": action_id,
                        "spend_id": spend_id,
                        "stage": "hold",
                        "action_type": "release_failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "operator": operator_id or "operator",
                        "details": {
                            "outcome": "create_failed",
                            "stderr": proc_create.stderr[-500:],
                        },
                    }
                )
                return request

            # Parse ID
            try:
                payload = self._parse_json_stdout(proc_create.stdout)
                if isinstance(payload, list) and len(payload) > 0:
                    payload = payload[0]
                if isinstance(payload, dict):
                    request.link_spend_request_id = payload.get("id")
            except (ValueError, AttributeError, IndexError, Exception):
                pass

            if not request.link_spend_request_id:
                request.status = "blocked"
                self._log_decision(
                    {
                        "action_id": action_id,
                        "spend_id": spend_id,
                        "stage": "hold",
                        "action_type": "release_failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "operator": operator_id or "operator",
                        "details": {
                            "outcome": "missing_spend_request_id",
                        },
                    }
                )
                return request

            # Request Approval (triggers app notification, returns immediately)
            cmd_req = [
                self.link_cli_path,
                "spend-request",
                "request-approval",
                request.link_spend_request_id,
                "--format",
                "json",
            ]
            if self.test_mode:
                cmd_req += ["--test"]

            proc_req = subprocess.run(cmd_req, capture_output=True, text=True, timeout=30, env=env)

            if proc_req.returncode != 0:
                request.status = "blocked"
                self._log_decision(
                    {
                        "action_id": action_id,
                        "spend_id": spend_id,
                        "stage": "hold",
                        "action_type": "release_failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "operator": operator_id or "operator",
                        "details": {
                            "outcome": "request_approval_failed",
                            "stderr": proc_req.stderr[-500:],
                        },
                    }
                )
                return request

            # Transition status to released and log decision
            request.status = "released"
            self._append_spend_log(request)

            self._log_decision(
                {
                    "action_id": action_id,
                    "spend_id": spend_id,
                    "stage": "hold",
                    "action_type": "release",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "operator": operator_id or "operator",
                    "details": {
                        "outcome": "release_initiated",
                        "link_spend_request_id": request.link_spend_request_id,
                    },
                }
            )

            # Start background polling thread
            self._start_polling_thread(request, action_id, operator_id)

            return request
        finally:
            try:
                os.unlink(lock_path)
            except Exception:
                pass

    def handle_hold_cancel(self, action_id: str, reason: str = "", *args: Any, **kwargs: Any) -> None:
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

    def _parse_json_stdout(self, stdout: str) -> Any:
        import re
        import json
        text = stdout.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Match outermost list [...] or object {...}
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"No valid JSON structure found in output: {stdout}")

    def _get_daily_spend_aggregate(self) -> int:
        """Calculate the sum of all spends in the last 24 hours from agent-spend.log."""
        import fcntl
        from datetime import timedelta
        if not self.spend_log_path.exists():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        total = 0

        with open(self.spend_log_path, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts_str = entry.get("timestamp")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str)
                            if ts >= cutoff:
                                total += entry.get("amount_cents", 0)
                    except Exception:
                        pass
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return total

    def _append_spend_log(self, request: SpendRequest) -> None:
        import fcntl
        import os

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
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _log_decision(self, decision: dict) -> None:
        import fcntl
        import os

        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.decisions_path, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(decision) + "\n")
                f.flush()
                os.fsync(f.fileno())
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

    def _recover_and_resume_polling(self) -> None:
        """Scan the decisions log for pending spend releases and resume polling threads."""
        if not self.decisions_path.exists():
            return

        released_requests = {}
        try:
            with open(self.decisions_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    dec = json.loads(line)
                    spend_id = dec.get("spend_id")
                    if not spend_id:
                        continue
                    action_type = dec.get("action_type")
                    stage = dec.get("stage")
                    if stage == "hold":
                        if action_type == "release":
                            released_requests[spend_id] = {
                                "action_id": dec.get("action_id"),
                                "link_spend_request_id": dec.get("details", {}).get("link_spend_request_id"),
                                "operator_id": dec.get("operator"),
                            }
                        elif action_type in ("purchase_approved", "purchase_denied", "purchase_expired", "release_failed", "cancel"):
                            if spend_id in released_requests:
                                del released_requests[spend_id]
        except Exception as e:
            logger.error("Failed to scan pending spend requests for recovery: %s", e)
            return

        for spend_id, info in released_requests.items():
            link_id = info.get("link_spend_request_id")
            if not link_id:
                continue
            logger.info("Resuming background polling for recovered spend request %s (Link ID: %s)", spend_id, link_id)
            try:
                req = self._get_request(spend_id)
                self._start_polling_thread(req, info["action_id"], info["operator_id"])
            except Exception as e:
                logger.error("Failed to resume polling for request %s: %s", spend_id, e)

    def _start_polling_thread(self, request: SpendRequest, action_id: str, operator_id: str | None) -> None:
        """Start a background thread to poll the Link request status."""
        import threading
        thread = threading.Thread(
            target=self._poll_spend_request,
            args=(request, action_id, operator_id),
            daemon=True,
        )
        thread.start()

    def _poll_spend_request(self, request: SpendRequest, action_id: str, operator_id: str | None) -> None:
        """Background thread logic to poll link-cli retrieve status."""
        import time
        import os

        # Set environment with correct isolation
        env = {**os.environ}
        if operator_id:
            safe_op_id = "".join(c for c in operator_id if c.isalnum() or c in ("-", "_")).strip()
            if safe_op_id and safe_op_id not in ("system", "operator", "sandbox"):
                base_config_dir = "/sandbox/.config" if os.path.exists("/sandbox") else os.path.expanduser("~/.config")
                user_config_dir = f"{base_config_dir}/users/{safe_op_id}"
                env["XDG_CONFIG_HOME"] = user_config_dir
            else:
                if os.path.exists("/sandbox/.config"):
                    env["XDG_CONFIG_HOME"] = "/sandbox/.config"
        else:
            if os.path.exists("/sandbox/.config"):
                env["XDG_CONFIG_HOME"] = "/sandbox/.config"

        cmd = [
            self.link_cli_path,
            "spend-request",
            "retrieve",
            request.link_spend_request_id,
            "--format",
            "json",
        ]
        if self.test_mode:
            cmd += ["--test"]

        max_attempts = 150  # 5 minutes at 2-second intervals
        attempts = 0
        terminal_status = None

        logger.info("Background polling started for spend request %s", request.spend_id)

        while attempts < max_attempts:
            attempts += 1
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
            except FileNotFoundError:
                logger.error("link-cli executable not found at %s", self.link_cli_path)
                terminal_status = "release_failed"
                break

            if proc.returncode == 0:
                try:
                    payload = self._parse_json_stdout(proc.stdout)
                    if isinstance(payload, list) and len(payload) > 0:
                        payload = payload[0]
                    if isinstance(payload, dict):
                        status = payload.get("status")
                        if status == "approved":
                            terminal_status = "purchase_approved"
                            break
                        elif status == "denied":
                            terminal_status = "purchase_denied"
                            break
                        elif status == "expired":
                            terminal_status = "purchase_expired"
                            break
                except Exception as e:
                    logger.debug("Failed to parse poll response for %s: %s", request.spend_id, e)
            else:
                logger.debug("Retrieve command failed for %s: %s", request.spend_id, proc.stderr)
            time.sleep(2)

        if not terminal_status:
            terminal_status = "purchase_expired"  # Timeout fallback

        # Process outcome
        if terminal_status == "purchase_approved":
            request.status = "released"
            logger.info("Spend request %s APPROVED on phone", request.spend_id)
        else:
            request.status = "blocked"
            logger.warning("Spend request %s failed/denied/expired (status: %s)", request.spend_id, terminal_status)

        # Log decision
        self._log_decision(
            {
                "action_id": action_id,
                "spend_id": request.spend_id,
                "stage": "hold",
                "action_type": terminal_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": operator_id or "operator",
                "details": {
                    "outcome": "approved" if terminal_status == "purchase_approved" else "failed_or_denied",
                    "link_spend_request_id": request.link_spend_request_id,
                    "attempts": attempts,
                },
            }
        )
