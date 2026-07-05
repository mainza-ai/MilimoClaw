# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Intake Manager

Manages the full client inquiry intake pipeline.

Entry point: receive_inquiry()
Pipeline: triage → welcome draft → questionnaire → brief quality check
→ pricing query → project brief to creative claw

Sequencing rule: pricing_response must be received before
project_brief can be sent. Never bypass this.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .ops_init import OpsFilesystemInit, OpsOperationalLog, OpsLogEntry
from .signal_dispatcher import OpsSignalDispatcher
from .approval_handler import OpsApprovalHandler

logger = logging.getLogger("milimo.ops")


@dataclass
class TriageScore:
    """Result of triage scoring an inquiry."""

    inquiry_id: str
    budget_signal: float
    scope_clarity: float
    niche_fit: float
    combined_score: float
    routing: str  # "draft_welcome" | "flag_for_review" | "auto_low"
    scored_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "inquiry_id": self.inquiry_id,
            "budget_signal": self.budget_signal,
            "scope_clarity": self.scope_clarity,
            "niche_fit": self.niche_fit,
            "combined_score": self.combined_score,
            "routing": self.routing,
            "scored_at": self.scored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TriageScore:
        return cls(
            inquiry_id=data["inquiry_id"],
            budget_signal=data["budget_signal"],
            scope_clarity=data["scope_clarity"],
            niche_fit=data["niche_fit"],
            combined_score=data["combined_score"],
            routing=data["routing"],
            scored_at=data.get("scored_at", ""),
        )


@dataclass
class ClientBrief:
    """Parsed client brief from intake questionnaire."""

    brief_id: str
    inquiry_id: str
    client_id: str
    project_id: str
    raw_text: str
    deadline: str | None
    scope_description: str
    deliverables: list[str] = field(default_factory=list)
    clarity_score: float = 0.0
    gaps: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "inquiry_id": self.inquiry_id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "raw_text": self.raw_text,
            "deadline": self.deadline,
            "scope_description": self.scope_description,
            "deliverables": self.deliverables,
            "clarity_score": self.clarity_score,
            "gaps": self.gaps,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClientBrief:
        return cls(
            brief_id=data["brief_id"],
            inquiry_id=data["inquiry_id"],
            client_id=data["client_id"],
            project_id=data["project_id"],
            raw_text=data["raw_text"],
            deadline=data.get("deadline"),
            scope_description=data.get("scope_description", ""),
            deliverables=data.get("deliverables", []),
            clarity_score=data.get("clarity_score", 0.0),
            gaps=data.get("gaps", []),
            created_at=data.get("created_at", ""),
        )


class IntakeManager:
    """
    Manages the full client inquiry intake pipeline.

    Entry point: receive_inquiry()
    Pipeline: triage → welcome draft → questionnaire → brief quality check
    → pricing query → project brief to creative claw

    Sequencing rule: pricing_response must be received before
    project_brief can be sent. Never bypass this.
    """

    WELCOME_DRAFT_THRESHOLD = 8.0
    REVIEW_THRESHOLD = 5.0

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        dispatcher: OpsSignalDispatcher,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog,
        squad_niche: str = "general",
    ):
        self._fs = fs
        self._inference_client = inference_client
        self._dispatcher = dispatcher
        self._approval_handler = approval_handler
        self._operational_log = operational_log
        self._squad_niche = squad_niche
        self._inquiries_dir = fs.BASE / "prospects"
        self._pending_pricing: dict[str, dict[str, Any]] = {}

    def receive_inquiry(self, raw_inquiry: dict[str, Any]) -> TriageScore:
        inquiry_id = raw_inquiry.get("inquiry_id") or uuid.uuid4().hex[:12]
        raw_inquiry["inquiry_id"] = inquiry_id
        raw_inquiry["received_at"] = datetime.now(timezone.utc).isoformat()

        inquiry_dir = self._fs.get_prospect_path(inquiry_id)
        inquiry_dir.mkdir(parents=True, exist_ok=True)

        inquiry_file = inquiry_dir / "inquiry.json"
        self._fs.write_json_atomic(inquiry_file, raw_inquiry)

        inquiry_text = raw_inquiry.get("message", "") or raw_inquiry.get(
            "inquiry_text", ""
        )
        triage_score = self.score_inquiry(inquiry_text, self._squad_niche)
        triage_score.inquiry_id = inquiry_id

        triage_file = inquiry_dir / "triage.json"
        self._fs.write_json_atomic(triage_file, triage_score.to_dict())

        if triage_score.combined_score >= self.WELCOME_DRAFT_THRESHOLD:
            client_name = raw_inquiry.get("name") or raw_inquiry.get(
                "client_name", "there"
            )
            welcome_draft = self.draft_welcome_message(inquiry_id, client_name)
            questionnaire_draft = self.draft_intake_questionnaire(
                inquiry_id, inquiry_text
            )

            combined_content = f"WELCOME MESSAGE:\n{welcome_draft}\n\nINTAKE QUESTIONNAIRE:\n{questionnaire_draft}"

            self._approval_handler.queue_review(
                action_type="welcome_message",
                entity_id=inquiry_id,
                content=combined_content,
                context={
                    "triage_score": triage_score.combined_score,
                    "budget_signal": triage_score.budget_signal,
                    "scope_clarity": triage_score.scope_clarity,
                    "niche_fit": triage_score.niche_fit,
                    "client_name": client_name,
                },
            )

        elif triage_score.combined_score >= self.REVIEW_THRESHOLD:
            self._approval_handler.queue_review(
                action_type="inquiry_review",
                entity_id=inquiry_id,
                content="Inquiry requires operator review before drafting response.",
                context={
                    "triage_score": triage_score.combined_score,
                    "budget_signal": triage_score.budget_signal,
                    "scope_clarity": triage_score.scope_clarity,
                    "niche_fit": triage_score.niche_fit,
                    "inquiry_text": inquiry_text[:500],
                },
            )
        else:
            self._approval_handler.log_auto(
                action_type="inquiry_low_priority",
                entity_id=inquiry_id,
                content_preview=f"Low priority inquiry (score: {triage_score.combined_score:.1f})",
            )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="inquiry_received",
                entity_id=inquiry_id,
                outcome="success",
                details={
                    "triage_score": triage_score.combined_score,
                    "routing": triage_score.routing,
                },
            )
        )

        return triage_score

    def score_inquiry(self, inquiry_text: str, squad_niche: str) -> TriageScore:
        prompt = f"""Analyze this client inquiry and score it on three dimensions (0-10 each):

SQUAD NICHE: {squad_niche}

INQUIRY:
{inquiry_text}

Score each dimension:
1. Budget signal: Keywords, numbers, or context suggesting budget range (0 = no budget mention, 10 = explicit budget)
2. Scope clarity: How well-defined the request is (0 = vague, 10 = detailed requirements)
3. Niche fit: How well prospect matches squad's focus areas (0 = poor fit, 10 = perfect match)

Respond in JSON format:
{{"budget_signal": X, "scope_clarity": X, "niche_fit": X}}"""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="client_triage_scoring",
                max_tokens=100,
            )

            match = re.search(r"\{[^}]+\}", response)
            if match:
                data = json.loads(match.group())
                budget = float(data.get("budget_signal", 5.0))
                scope = float(data.get("scope_clarity", 5.0))
                fit = float(data.get("niche_fit", 5.0))
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            logger.warning("Triage inference failed, using fallback: %s", e)
            budget = 5.0
            scope = 5.0
            fit = 5.0

        budget = max(0.0, min(10.0, budget))
        scope = max(0.0, min(10.0, scope))
        fit = max(0.0, min(10.0, fit))

        combined_score = (budget * 0.4) + (scope * 0.3) + (fit * 0.3)

        if combined_score >= self.WELCOME_DRAFT_THRESHOLD:
            routing = "draft_welcome"
        elif combined_score >= self.REVIEW_THRESHOLD:
            routing = "flag_for_review"
        else:
            routing = "auto_low"

        return TriageScore(
            inquiry_id="",
            budget_signal=budget,
            scope_clarity=scope,
            niche_fit=fit,
            combined_score=combined_score,
            routing=routing,
        )

    def draft_welcome_message(self, inquiry_id: str, client_name: str | None) -> str:
        template = self._fs.get_template("welcome-message.md")

        prompt = f"""Personalize this welcome message template for a new client inquiry.

TEMPLATE:
{template}

CLIENT NAME: {client_name or "there"}
SQUAD NAME: Milimo Claw

Create a personalized welcome message that:
1. Addresses the client warmly
2. Shows enthusiasm for their project
3. Invites them to share more details

Output only the personalized message, nothing else."""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="welcome_message_drafting",
                max_tokens=300,
            )
            return response.strip()
        except Exception as e:
            logger.warning("Welcome message drafting failed: %s", e)
            return template.replace("{{client_name}}", client_name or "there").replace(
                "{{squad_name}}", "Milimo Claw"
            )

    def draft_intake_questionnaire(self, inquiry_id: str, inquiry_context: str) -> str:
        template = self._fs.get_template("intake-questionnaire.md")

        prompt = f"""Customize this intake questionnaire based on the client's inquiry.

TEMPLATE:
{template}

INQUIRY CONTEXT:
{inquiry_context[:500]}

Keep the core questions but customize for this specific inquiry type.
Output only the questionnaire."""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="intake_questionnaire_customization",
                max_tokens=400,
            )
            return response.strip()
        except Exception as e:
            logger.warning("Questionnaire customization failed: %s", e)
            return template

    def handle_client_response(
        self, inquiry_id: str, response_text: str
    ) -> ClientBrief | None:
        prospect_dir = self._fs.get_prospect_path(inquiry_id)

        brief_quality = self._check_brief_quality(response_text)

        if brief_quality["gaps"]:
            clarifying_question = self._draft_clarifying_question(
                inquiry_id, brief_quality["gaps"]
            )
            self._approval_handler.queue_review(
                action_type="clarifying_question",
                entity_id=inquiry_id,
                content=clarifying_question,
                context={"gaps": brief_quality["gaps"]},
            )
            self._operational_log.append(
                OpsLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type="brief_quality_gap",
                    entity_id=inquiry_id,
                    outcome="clarifying_question_queued",
                    details={"gaps": brief_quality["gaps"]},
                )
            )
            return None

        brief = self._create_brief_from_response(
            inquiry_id, response_text, brief_quality
        )

        response_file = prospect_dir / "client_response.json"
        self._fs.write_json_atomic(
            response_file,
            {
                "inquiry_id": inquiry_id,
                "response_text": response_text,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "brief_id": brief.brief_id,
            },
        )

        self._dispatcher.send_pricing_query(
            project_id=brief.project_id,
            scope_description=brief.scope_description,
            complexity_estimate="medium",
            deadline=brief.deadline or "TBD",
            client_id=brief.client_id,
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="brief_received",
                entity_id=brief.brief_id,
                outcome="success",
                details={
                    "project_id": brief.project_id,
                    "clarity_score": brief.clarity_score,
                },
            )
        )

        return brief

    def _check_brief_quality(self, response_text: str) -> dict[str, Any]:
        prompt = f"""Analyze this client brief response for completeness.

CLIENT RESPONSE:
{response_text}

Check for:
1. Missing deadline (no timeline mentioned)
2. Undefined scope (vague or incomplete project description)
3. Unclear deliverables (no specific outputs mentioned)
4. Contradictory requirements

Respond in JSON format:
{{
    "clarity_score": 0-10,
    "gaps": ["gap1", "gap2", ...],
    "deadline_present": true/false,
    "scope_clear": true/false,
    "deliverables_clear": true/false
}}"""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="brief_quality_check",
                max_tokens=200,
            )

            match = re.search(r"\{[^}]+\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.warning("Brief quality check failed: %s", e)

        return {
            "clarity_score": 5.0,
            "gaps": [],
            "deadline_present": True,
            "scope_clear": True,
            "deliverables_clear": True,
        }

    def _draft_clarifying_question(self, inquiry_id: str, gaps: list[str]) -> str:
        self._fs.get_template("intake-questionnaire.md")

        prompt = f"""Draft a clarifying question for a client based on gaps in their brief.

GAPS TO ADDRESS:
{chr(10).join(f"- {g}" for g in gaps)}

Create a friendly, professional message asking for clarification.
Keep it concise (under 150 words)."""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="clarifying_question_drafting",
                max_tokens=200,
            )
            return response.strip()
        except Exception as e:
            logger.warning("Clarifying question drafting failed: %s", e)
            return f"Thank you for the details! Could you please clarify: {', '.join(gaps)}"

    def _create_brief_from_response(
        self, inquiry_id: str, response_text: str, quality: dict[str, Any]
    ) -> ClientBrief:
        brief_id = uuid.uuid4().hex[:12]
        client_id = f"client-{uuid.uuid4().hex[:8]}"
        project_id = f"project-{uuid.uuid4().hex[:8]}"

        brief = ClientBrief(
            brief_id=brief_id,
            inquiry_id=inquiry_id,
            client_id=client_id,
            project_id=project_id,
            raw_text=response_text,
            deadline=quality.get("deadline"),
            scope_description=response_text[:500],
            deliverables=[],
            clarity_score=quality.get("clarity_score", 5.0),
            gaps=quality.get("gaps", []),
        )

        prospect_dir = self._fs.get_prospect_path(inquiry_id)
        brief_file = prospect_dir / "brief.json"
        self._fs.write_json_atomic(brief_file, brief.to_dict())

        return brief

    def onboard_client(
        self, inquiry_id: str, client_name: str, contact_details: dict[str, Any]
    ) -> str:
        client_id = f"client-{uuid.uuid4().hex[:8]}"

        self._fs.create_client_dirs(client_id)

        profile = {
            "client_id": client_id,
            "name": client_name,
            "contact_details": contact_details,
            "inquiry_id": inquiry_id,
            "onboarded_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }

        profile_file = self._fs.get_client_path("active", client_id) / "profile.json"
        self._fs.write_json_atomic(profile_file, profile)

        prospect_dir = self._fs.get_prospect_path(inquiry_id)
        prospect_file = prospect_dir / "client_link.json"
        self._fs.write_json_atomic(prospect_file, {"client_id": client_id})

        niche = contact_details.get("niche", self._squad_niche)
        project_type = contact_details.get("project_type", "general")
        estimated_value = float(contact_details.get("estimated_value", 0.0))

        self._dispatcher.send_client_onboarded(
            client_id=client_id,
            niche=niche,
            project_type=project_type,
            estimated_value=estimated_value,
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="client_onboarded",
                entity_id=client_id,
                outcome="success",
                details={"inquiry_id": inquiry_id, "name": client_name},
            )
        )

        return client_id

    def handle_pricing_response(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float,
        scope_notes: str,
    ) -> None:
        self._pending_pricing[project_id] = {
            "floor_price": floor_price,
            "ceiling_price": ceiling_price,
            "scope_notes": scope_notes,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        self._dispatcher.mark_pricing_confirmed(project_id)

        proposal_draft = self._draft_proposal(
            project_id, floor_price, ceiling_price, scope_notes
        )

        self._approval_handler.queue_review(
            action_type="proposal",
            entity_id=project_id,
            content=proposal_draft,
            context={
                "floor_price": floor_price,
                "ceiling_price": ceiling_price,
                "scope_notes": scope_notes,
            },
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="pricing_response_received",
                entity_id=project_id,
                outcome="success",
                details={"floor_price": floor_price, "ceiling_price": ceiling_price},
            )
        )

    def _draft_proposal(
        self,
        project_id: str,
        floor_price: float,
        ceiling_price: float,
        scope_notes: str,
    ) -> str:
        template = self._fs.get_template("proposal-template.md")

        price_range = f"${floor_price:,.0f} - ${ceiling_price:,.0f}"

        proposal = template.replace("{{project_name}}", project_id)
        proposal = proposal.replace("{{price_range}}", price_range)
        proposal = proposal.replace("{{scope_description}}", scope_notes[:500])

        return proposal

    def send_project_brief_after_proposal_approved(
        self,
        project_id: str,
        client_id: str,
        brief: ClientBrief,
        recipient_role: str,
    ) -> None:
        self._dispatcher.send_project_brief(
            client_id=client_id,
            project_id=project_id,
            brief_text=brief.raw_text,
            deadline=brief.deadline or "TBD",
            tone_requirements="professional",
            platform_targets=["email"],
            recipient_role=recipient_role,
        )

        self._fs.create_project_dirs(client_id, project_id)

        project_dir = self._fs.get_project_path(client_id, project_id)
        brief_file = project_dir / "brief.json"
        self._fs.write_json_atomic(brief_file, brief.to_dict())

        status_file = project_dir / "status.json"
        self._fs.write_json_atomic(
            status_file,
            {
                "project_id": project_id,
                "client_id": client_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="project_brief_sent",
                entity_id=project_id,
                outcome="success",
                details={"client_id": client_id, "recipient_role": recipient_role},
            )
        )

    def _group_rapid_messages(
        self, client_id: str, new_message: dict[str, Any], window_minutes: int = 30
    ) -> bool:
        from datetime import timedelta

        prospect_dir = self._fs.BASE / "prospects"
        if not prospect_dir.exists():
            return False

        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        for inquiry_dir in prospect_dir.iterdir():
            if not inquiry_dir.is_dir():
                continue

            comms_dir = inquiry_dir / "comms"
            if not comms_dir.exists():
                continue

            for comms_file in comms_dir.glob("*.json"):
                try:
                    data = json.loads(comms_file.read_text())
                    if data.get("client_id") != client_id:
                        continue

                    msg_time_str = data.get("timestamp", "")
                    if not msg_time_str:
                        continue

                    msg_time = datetime.fromisoformat(msg_time_str)
                    if msg_time >= cutoff_time:
                        grouped_file = (
                            comms_dir
                            / f"grouped_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        self._fs.write_json_atomic(
                            grouped_file,
                            {
                                "grouped": True,
                                "original_message": data,
                                "new_message": new_message,
                                "grouped_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        return True
                except (json.JSONDecodeError, ValueError, OSError):
                    continue

        return False

    def _check_inquiry_staleness(self) -> None:
        review_queue = self._approval_handler.get_review_queue()

        for action in review_queue:
            if action.action_type not in (
                "welcome_message",
                "inquiry_review",
                "proposal",
            ):
                continue

            if not action.timestamp:
                continue

            try:
                action_time = datetime.fromisoformat(action.timestamp)
                hours_waiting = (
                    datetime.now(timezone.utc) - action_time
                ).total_seconds() / 3600

                if hours_waiting >= 24:
                    self._approval_handler.add_urgency_flag(
                        action.action_id, int(hours_waiting)
                    )
            except ValueError:
                continue

    def get_pending_pricing(self, project_id: str) -> dict[str, Any] | None:
        return self._pending_pricing.get(project_id)
