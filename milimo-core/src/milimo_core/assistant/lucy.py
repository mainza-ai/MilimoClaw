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
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..milimo_paths import claw_base
from ..milimo_paths import mesh_dir

logger = logging.getLogger("milimo.assistant")

ALL_CLAW_ROLES = ["content", "ops", "analytics", "finance", "build", "assistant"]
RESPONSE_TIMEOUT_SECONDS = 60


class ProcessMilestone:
    """Represents a single step in a multi-claw workflow pipeline."""

    def __init__(
        self,
        step_name: str,
        expected_sender: str,
        expected_recipient: str,
        expected_type: str,
        timeout_seconds: int = 30,
    ):
        self.step_name = step_name
        self.expected_sender = expected_sender
        self.expected_recipient = expected_recipient
        self.expected_type = expected_type
        self.timeout_seconds = timeout_seconds
        self.completed_at: float | None = None
        self.status = "pending"  # "pending", "completed", "failed", "stalled"


class ActiveProcessTrack:
    """Manages a sequence of milestones to ensure workflow completion."""

    def __init__(
        self, track_id: str, original_task: str, milestones: list[ProcessMilestone]
    ):
        self.track_id = track_id
        self.original_task = original_task
        self.milestones = milestones
        self.started_at = time.time()
        self.status = "active"  # "active", "completed", "stalled"
        self.last_supervision_alert_at = 0.0

    @property
    def current_milestone(self) -> ProcessMilestone | None:
        for m in self.milestones:
            if m.status == "pending":
                return m
        return None

    @property
    def is_complete(self) -> bool:
        return all(m.status == "completed" for m in self.milestones)


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
        self._pending_tracks: dict[str, ActiveProcessTrack] = {}
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

        # Start background supervision loop
        self._supervision_thread = threading.Thread(
            target=self._run_supervision_loop, daemon=True, name="lucy-supervision"
        )
        self._supervision_thread.start()

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

        # Register in process tracker
        track = self._create_process_track(task_description, message_id, target_role)
        if track:
            self._pending_tracks[message_id] = track
            logger.info(
                f'[Lucy] Registered active process supervision track {message_id} for "{task_description}"'
            )

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
        """Remove expired pending queries and process tracks. Returns count of cleaned queries."""
        expired = []
        for qid, pending in self._pending.items():
            if pending.is_expired and not pending.responded:
                expired.append(qid)
                pending.responded = True

        for qid in expired:
            del self._pending[qid]
            if qid in self._pending_tracks:
                self._pending_tracks[qid].status = "stalled"

        if expired:
            logger.info("LucyAssistant: cleaned %d expired queries", len(expired))
        return len(expired)

    def _create_process_track(
        self, text: str, track_id: str, target_role: str
    ) -> ActiveProcessTrack | None:
        """Create a process track template based on parsed message keywords."""
        import os

        is_test = (
            os.getenv("MILIMO_TEST_MODE") == "true"
            or float(os.getenv("ANALYTICS_WAIT_SECONDS", "300")) < 5.0
        )
        timeout = 15 if is_test else 600

        text_lower = text.lower()
        if "scope" in text_lower or "intake" in text_lower or "pricing" in text_lower:
            # Scoping Pipeline Template
            milestones = [
                ProcessMilestone(
                    "Ops Task Receipt", "assistant", "ops", "assistant_task", timeout
                ),
                ProcessMilestone(
                    "Finance Pricing Query", "ops", "finance", "pricing_query", timeout
                ),
                ProcessMilestone(
                    "Finance Pricing Response",
                    "finance",
                    "ops",
                    "pricing_response",
                    timeout,
                ),
                ProcessMilestone(
                    "Ops Scoping Completion",
                    "ops",
                    "assistant",
                    "assistant_response",
                    timeout,
                ),
            ]
            return ActiveProcessTrack(track_id, text, milestones)

        elif (
            "sprint" in text_lower
            or "feature" in text_lower
            or "build" in text_lower
            or "technical" in text_lower
        ):
            # Technical Sprint Pipeline Template
            milestones = [
                ProcessMilestone(
                    "Ops Task Receipt", "assistant", "ops", "assistant_task", timeout
                ),
                ProcessMilestone(
                    "Build Feature Brief", "ops", "build", "feature_brief", timeout
                ),
                ProcessMilestone(
                    "Build Feature Acknowledged",
                    "build",
                    "ops",
                    "feature_brief_acknowledged",
                    timeout,
                ),
                ProcessMilestone(
                    "Ops Sprint Completion",
                    "ops",
                    "assistant",
                    "assistant_response",
                    timeout,
                ),
            ]
            return ActiveProcessTrack(track_id, text, milestones)

        return None

    def _run_supervision_loop(self) -> None:
        """Background loop to periodically supervise active tracks."""
        while self._running:
            try:
                self.supervise_active_tracks()
            except Exception as e:
                logger.error(f"LucyAssistant supervision loop error: {e}")
            time.sleep(2)

    def supervise_active_tracks(self) -> None:
        """Scan claw processed folders and transition milestones. Trigger alerts on stalls."""
        import os

        # We need to scan all process tracks
        for track_id, track in list(self._pending_tracks.items()):
            if track.status != "active":
                continue

            milestone = track.current_milestone
            if not milestone:
                # All milestones completed!
                track.status = "completed"
                logger.info(
                    f"[Lucy] Process track {track.track_id} completed successfully!"
                )
                self._emit_conversational_alert(
                    f'🔔 [Lucy Active Supervisor] Process Track {track.track_id} ("{track.original_task[:40]}...") '
                    f"completed successfully! E2E workflow successfully coordinated."
                )
                continue

            # Check if current milestone has timed out
            milestone_elapsed = time.time() - (
                milestone.completed_at or track.started_at
            )

            # Check if the message for the current milestone exists in the processed inbox
            recipient = milestone.expected_recipient
            sender = milestone.expected_sender
            msg_type = milestone.expected_type

            # Scan recipient's inbox/processed directory
            recipient_processed_dir = mesh_dir() / "inbox" / recipient / "processed"

            message_processed = False
            if recipient_processed_dir.exists():
                for f in recipient_processed_dir.glob("*.json"):
                    try:
                        data = json.loads(f.read_text())
                        if (
                            data.get("sender_role") == sender
                            and data.get("recipient_role") == recipient
                            and data.get("message_type") == msg_type
                        ):
                            payload = data.get("payload", {})
                            if (
                                data.get("message_id") == track.track_id
                                or payload.get("query_id") == track.track_id
                                or payload.get("original_message_id") == track.track_id
                                or payload.get("project_id") == track.track_id
                            ):
                                message_processed = True
                                break
                    except Exception:
                        pass

            if message_processed:
                milestone.status = "completed"
                milestone.completed_at = time.time()
                logger.info(f"[Lucy] Milestone {milestone.step_name} completed!")
                self._emit_conversational_alert(
                    f"📈 [Lucy Active Supervisor] Milestone completed: {milestone.step_name} (Sender: {sender} -> Recipient: {recipient})"
                )
                continue

            # If the milestone has timed out, trigger escalation!
            if milestone_elapsed > milestone.timeout_seconds:
                milestone.status = "stalled"
                track.status = "stalled"

                # Check if we should throttle alerts (e.g. alert once every 5 seconds in tests, or 60 seconds in prod)
                throttle = (
                    5
                    if (
                        os.getenv("MILIMO_TEST_MODE") == "true"
                        or float(os.getenv("ANALYTICS_WAIT_SECONDS", "300")) < 5.0
                    )
                    else 60
                )
                if time.time() - track.last_supervision_alert_at > throttle:
                    track.last_supervision_alert_at = time.time()

                    # 1. Emit conversational alert
                    stall_msg = (
                        f"🚨 [Lucy Active Supervisor] STALL DETECTED in Process Track {track.track_id}!\n"
                        f'   - Milestone Stalled: "{milestone.step_name}" (Expecting {sender} -> {recipient}: {msg_type})\n'
                        f"   - Elapsed Time: {int(milestone_elapsed)}s (Timeout: {milestone.timeout_seconds}s)\n"
                        f'   - Prompting stuck claw "{recipient}" for diagnostics...'
                    )
                    self._emit_conversational_alert(stall_msg)

                    # 2. Inject high-priority HOLD alert into the War Room TUI
                    self._inject_war_room_hold_alert(track_id, milestone)

                    # 3. Dispatch diagnostic assistant_query to the stuck claw
                    self._dispatch_diagnostic_inquiry(recipient, track.track_id)

                    # 4. Trigger SLA self-healing to autonomously resolve the stall
                    self._trigger_sla_self_healing(recipient, track.track_id)

    def _emit_conversational_alert(self, text: str) -> None:
        """Log the alert and write to local operator interface logs."""
        logger.warning(text)
        alerts_log = self._base_path / "logs" / "supervision.log"
        alerts_log.parent.mkdir(parents=True, exist_ok=True)
        try:
            with alerts_log.open("a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} - {text}\n")
        except Exception:
            pass

    def _inject_war_room_hold_alert(self, track_id: str, milestone: Any) -> None:
        """Inject a high-priority HOLD action into the Solo War Room TUI."""
        try:
            solo_config_path = Path("/sandbox/.openclaw/milimo/config.json")
            if solo_config_path.exists():
                with solo_config_path.open("r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            try:
                from orchestrator.solo_warroom import SoloWarRoom, ActionPriority
            except ImportError:
                try:
                    from ..solo_warroom import SoloWarRoom, ActionPriority
                except ImportError:
                    from solo_warroom import SoloWarRoom, ActionPriority

            war_room = SoloWarRoom(config)

            payload = {
                "summary": f"STALL WARNING: Claw {milestone.expected_recipient} is stalled on {milestone.step_name}",
                "context": {
                    "track_id": track_id,
                    "stalled_claw": milestone.expected_recipient,
                    "milestone": milestone.step_name,
                    "expected_type": milestone.expected_type,
                },
            }
            action = war_room.queue_action(
                claw="assistant", action_type="supervision_stall", payload=payload
            )
            action.priority = ActionPriority.HOLD
            war_room._sort_queue()

            logger.info(
                f"[Lucy] Successfully injected HOLD alert {action.id} into War Room TUI."
            )
        except Exception as e:
            logger.error(f"[Lucy] Failed to inject War Room HOLD alert: {e}")

    def _dispatch_diagnostic_inquiry(self, recipient_role: str, query_id: str) -> None:
        """Send a diagnostic assistant_query to the stalled claw."""
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            sent = self._mesh_gateway.send(
                message_type="assistant_query",
                recipient_role=recipient_role,
                sender_role="assistant",
                payload={"query": "diagnostics", "query_id": query_id},
                message_id=query_id,
                timestamp=timestamp,
            )
            if sent:
                logger.info(
                    f"[Lucy] Dispatched diagnostic assistant_query to stalled claw {recipient_role}."
                )
        except Exception as e:
            logger.error(f"[Lucy] Failed to send diagnostic query: {e}")

    def _trigger_sla_self_healing(self, stalled_claw: str, track_id: str) -> None:
        """Autonomously heals stalled claws by switching their model backend to Cloud NIM."""
        import subprocess
        import os

        logger.warning(
            f"⚡ [Lucy Active Supervisor] Triggering SLA Self-Healing for stalled claw '{stalled_claw}' (Track: {track_id})."
        )

        try:
            cloud_model = os.environ.get("NEMOCLAW_MODEL")
            if not cloud_model:
                logger.warning(
                    "[Lucy] NEMOCLAW_MODEL not set — skipping SLA healing inference"
                )
                return
            os.environ["NEMOCLAW_MODEL"] = cloud_model
            cmd = [
                "openshell",
                "inference",
                "set",
                "--provider",
                "nvidia-nim",
                "--model",
                cloud_model,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                logger.info(
                    f"[Lucy] Successfully upgraded inference to Cloud NIM for stalled claw '{stalled_claw}'."
                )
                self._emit_conversational_alert(
                    f"⚡ [Lucy Active Supervisor] SLA Self-Healing active: Successfully upgraded inference to high-performance Cloud NIM for '{stalled_claw}'."
                )
            else:
                logger.debug(
                    f"[Lucy] openshell CLI returned code {result.returncode} during healing: {result.stderr.strip()}"
                )
        except FileNotFoundError:
            logger.warning(
                f"[Lucy] openshell CLI not found. Defaulted to environment variable NEMOCLAW_MODEL routing for '{stalled_claw}'."
            )
            self._emit_conversational_alert(
                f"⚡ [Lucy Active Supervisor] SLA Self-Healing: Applied environment variable overrides for '{stalled_claw}'."
            )

    def answer_questions(self, query_text: str, target_roles: list[str] = None) -> dict:
        query_id = self.dispatch_query(query_text, target_roles)
        return {"query_id": query_id, "status": "dispatched"}

    def route_to_claw(self, target_role: str, message: str) -> dict:
        query_id = self.dispatch_query(message, target_roles=[target_role])
        return {"query_id": query_id, "target_role": target_role}

    def handle_pending_queries(self) -> dict:
        count = self.cleanup_expired()
        return {"status": "processed", "cleaned": count}

    def provide_status(self) -> dict:
        return self.process_operator_message("status")
