#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Content Generator

Core draft generation engine for the Content Claw. Generates content
using Nemotron via privacy router, applies active evolution tools,
and writes processed drafts to the pending directory.

Usage:
    from content.content_generator import ContentGenerator, Draft, DraftContext

    generator = ContentGenerator(privacy_router, tool_registry, op_log, fs)
    draft = await generator.generate_draft("twitter", context, "post")
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Literal

from ..privacy_router import InferenceBackend, PrivacyRouter, RoutingDecision
from ..tool_registry import ToolRegistry
from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
    generate_draft_id,
    generate_brief_id,
)

logger = logging.getLogger("milimo.content_generator")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class DraftContext:
    """Context for draft generation."""

    brief_id: str | None = None
    brief_text: str | None = None
    topic: str | None = None
    tone_hint: str | None = None
    client_id: str | None = None
    project_id: str | None = None
    style_guide: str | None = None
    performance_hints: dict[str, Any] | None = None


@dataclass
class Draft:
    """A generated content draft."""

    draft_id: str
    platform: str
    client_id: str | None
    project_id: str | None
    content_type: str
    raw_content: str
    processed_content: str
    brief_id: str | None = None
    tone: str | None = None
    approval_probability: float | None = None
    scheduled_time: str | None = None
    variant_a: str | None = None
    variant_b: str | None = None
    voice_profile_used: str | None = None
    tools_applied: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: Literal["pending", "approved", "rejected", "published"] = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Draft:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ContentPlan:
    """Daily content generation plan."""

    plan_id: str
    date: str
    platforms: list[str]
    clients: list[str]
    briefs: list[str]
    estimated_times: dict[str, str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Content Generator
# ---------------------------------------------------------------------------


class ContentGenerator:
    """
    Core draft generation engine for the Content Claw.

    Generates content using Nemotron via privacy router.
    Applies active evolution tools in sequence.
    Writes drafts to /sandbox/content/drafts/pending/.
    """

    TOOL_SEQUENCE = [
        "tone_classifier",
        "platform_calibrator",
        "client_voice_adapter",
        "approval_predictor",
        "timing_optimizer",
        "ab_variant_engine",
    ]

    def __init__(
        self,
        privacy_router: PrivacyRouter,
        tool_registry: ToolRegistry,
        operational_log: ContentOperationalLog,
        fs: ContentFilesystemInit,
        war_room: Any | None = None,
    ) -> None:
        self._router = privacy_router
        self._tools = tool_registry
        self._log = operational_log
        self._fs = fs
        self._war_room = war_room

    async def generate_draft(
        self,
        platform: str,
        context: DraftContext,
        content_type: str = "post",
    ) -> Draft:
        """
        Generate a content draft.

        1. Build generation prompt from context
        2. Route inference via privacy router
        3. Apply active tools in sequence
        4. Write draft to pending directory
        5. Log to operational.log
        """
        draft_id = generate_draft_id()
        logger.info("Generating draft %s for platform %s", draft_id, platform)

        style_guide = await self._load_style_guide(context.client_id)
        prompt = self._build_prompt(platform, context, style_guide)

        data_type = self._determine_data_type(content_type, context)
        routing = self._router.route(role="content", data_type=data_type)

        logger.debug(
            "Routing inference for draft %s: %s -> %s (reason: %s)",
            draft_id,
            data_type,
            routing.backend.value,
            routing.reason,
        )

        raw_content = await self._call_inference(prompt, routing)

        draft = Draft(
            draft_id=draft_id,
            platform=platform,
            client_id=context.client_id,
            project_id=context.project_id,
            content_type=content_type,
            raw_content=raw_content,
            processed_content=raw_content,
            status="pending",
        )

        draft = await self._apply_tools(draft, context)

        draft_path = self._fs.get_draft_path("pending", draft_id)
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(json.dumps(draft.to_dict(), indent=2))

        self._log.append(LogEntry(
            action_type="draft_generated",
            entity_id=draft_id,
            outcome="success",
            platform=platform,
            client_id=context.client_id,
            details={
                "content_type": content_type,
                "tools_applied": draft.tools_applied,
                "routing_backend": routing.backend.value,
            },
        ))

        logger.info("Draft %s written to %s", draft_id, draft_path)
        return draft

    async def generate_from_brief(self, brief_id: str) -> Draft:
        """
        Generate a draft from a project brief.

        Reads brief from active directory, generates content,
        sends draft_ready message before War Room queue.
        """
        brief_path = self._fs.get_brief_path("active", brief_id)
        if not brief_path.exists():
            raise FileNotFoundError(f"Brief not found: {brief_path}")

        brief_data = json.loads(brief_path.read_text())

        context = DraftContext(
            brief_id=brief_id,
            brief_text=brief_data.get("brief_text"),
            client_id=brief_data.get("client_id"),
            project_id=brief_data.get("project_id"),
            tone_hint=brief_data.get("tone_requirements"),
        )

        platforms = brief_data.get("platform_targets", [])
        platform = platforms[0] if platforms else "twitter"

        draft = await self.generate_draft(platform, context)

        draft.brief_id = brief_id
        draft_path = self._fs.get_draft_path("pending", draft.draft_id)
        draft_path.write_text(json.dumps(draft.to_dict(), indent=2))

        self._log.append(LogEntry(
            action_type="brief_draft_generated",
            entity_id=draft.draft_id,
            outcome="success",
            client_id=context.client_id,
            details={"brief_id": brief_id},
        ))

        return draft

    async def generate_daily_plan(self) -> ContentPlan:
        """
        Generate daily content plan at 06:00.

        Reads active briefs and analytics intelligence.
        """
        today = datetime.now(timezone.utc).date().isoformat()
        plan_id = f"plan-{today}"

        briefs = self._fs.BASE / "briefs" / "active"
        active_briefs = []
        clients = set()
        platforms = set()

        if briefs.exists():
            for brief_file in briefs.glob("*.json"):
                brief_data = json.loads(brief_file.read_text())
                active_briefs.append(brief_file.stem)
                if brief_data.get("client_id"):
                    clients.add(brief_data["client_id"])
                for p in brief_data.get("platform_targets", []):
                    platforms.add(p)

        intelligence_path = self._fs.BASE / "intelligence" / "analytics-feed" / "weekly-intelligence.json"
        performance_hints = None
        if intelligence_path.exists():
            performance_hints = json.loads(intelligence_path.read_text())

        estimated_times = {}
        for brief_id in active_briefs:
            estimated_times[brief_id] = datetime.now(timezone.utc).isoformat()

        plan = ContentPlan(
            plan_id=plan_id,
            date=today,
            platforms=list(platforms),
            clients=list(clients),
            briefs=active_briefs,
            estimated_times=estimated_times,
        )

        plan_path = self._fs.BASE / "calendar" / "scheduled" / f"plan_{today}.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan.to_dict(), indent=2))

        self._log.append(LogEntry(
            action_type="daily_plan_generated",
            entity_id=plan_id,
            outcome="success",
            details={"brief_count": len(active_briefs)},
        ))

        return plan

    def _build_prompt(
        self,
        platform: str,
        context: DraftContext,
        style_guide: str | None = None,
    ) -> str:
        """Construct structured generation prompt."""
        parts = [f"Generate {platform} content."]

        if context.brief_text:
            parts.append(f"Brief: {context.brief_text}")

        if context.topic:
            parts.append(f"Topic: {context.topic}")

        if context.tone_hint:
            parts.append(f"Tone: {context.tone_hint}")

        if style_guide:
            parts.append(f"Style guide: {style_guide[:500]}")

        if context.performance_hints:
            parts.append(f"Performance patterns: {context.performance_hints}")

        platform_specs = self._get_platform_specs(platform)
        if platform_specs:
            parts.append(platform_specs)

        return "\n\n".join(parts)

    def _get_platform_specs(self, platform: str) -> str:
        """Get platform-specific content specifications."""
        specs = {
            "twitter": "Keep under 280 characters. Use engaging hooks.",
            "linkedin": "Professional tone. Use hashtags sparingly. Longer form allowed.",
            "instagram": "Visual-first focus. Use emojis. Include call-to-action.",
            "tiktok": "Trend-aware. Short and punchy. Hook in first 3 seconds.",
            "email": "Clear subject line. Personalized greeting. Single CTA.",
        }
        return specs.get(platform, "")

    def _determine_data_type(self, content_type: str, context: DraftContext) -> str:
        """Determine data type for privacy routing."""
        if content_type in ("campaign", "proposal") or context.client_id:
            return "client_facing_draft"
        return "internal_ideation"

    async def _load_style_guide(self, client_id: str | None) -> str | None:
        """Load client-specific or default style guide."""
        if client_id:
            client_guide = self._fs.get_style_guide_path(client_id)
            if client_guide.exists():
                return client_guide.read_text()

        default_guide = self._fs.get_style_guide_path()
        if default_guide.exists():
            return default_guide.read_text()

        return None

    async def _call_inference(self, prompt: str, routing: RoutingDecision) -> str:
        """Call the inference backend. Placeholder for actual implementation."""
        logger.debug("Calling inference backend: %s", routing.backend.value)
        return f"Generated content for: {prompt[:100]}..."

    async def _apply_tools(self, draft: Draft, context: DraftContext) -> Draft:
        """Apply active tools in sequence."""
        active_tools = self._get_active_tools()

        for tool_name in self.TOOL_SEQUENCE:
            if tool_name not in active_tools:
                continue

            if tool_name == "client_voice_adapter" and not context.client_id:
                continue

            try:
                draft = await self._apply_tool(tool_name, draft, context)
                draft.tools_applied.append(tool_name)
                logger.debug("Applied tool %s to draft %s", tool_name, draft.draft_id)
            except Exception as e:
                logger.warning(
                    "Tool %s failed for draft %s, skipping: %s",
                    tool_name,
                    draft.draft_id,
                    e,
                )
                self._log.append(LogEntry(
                    action_type="tool_error",
                    entity_id=draft.draft_id,
                    outcome="failed",
                    details={"tool": tool_name, "error": str(e)},
                ))

        return draft

    def _get_active_tools(self) -> set[str]:
        """Get set of active tool names from registry."""
        active = set()
        for tool in self._tools.list_tools(status_filter="deployed"):
            active.add(tool.tool_name)
        return active

    async def _apply_tool(
        self,
        tool_name: str,
        draft: Draft,
        context: DraftContext,
    ) -> Draft:
        """Apply a single tool to the draft."""
        if tool_name == "tone_classifier":
            draft.tone = await self._classify_tone(draft.processed_content)
        elif tool_name == "platform_calibrator":
            draft.processed_content = await self._calibrate_for_platform(
                draft.processed_content, draft.platform
            )
        elif tool_name == "client_voice_adapter":
            if context.client_id:
                draft.processed_content = await self._apply_voice_adapter(
                    draft.processed_content, context.client_id
                )
                draft.voice_profile_used = context.client_id
        elif tool_name == "approval_predictor":
            draft.approval_probability = await self._predict_approval(draft)
        elif tool_name == "timing_optimizer":
            draft.scheduled_time = await self._optimize_timing(draft)
        elif tool_name == "ab_variant_engine":
            draft.variant_b = await self._generate_variant(draft)

        return draft

    async def _classify_tone(self, content: str) -> str:
        """Classify content tone. Placeholder."""
        return "professional"

    async def _calibrate_for_platform(self, content: str, platform: str) -> str:
        """Calibrate content for platform. Placeholder."""
        return content

    async def _apply_voice_adapter(self, content: str, client_id: str) -> str:
        """Apply client voice profile. Placeholder."""
        return content

    async def _predict_approval(self, draft: Draft) -> float:
        """Predict approval probability. Placeholder."""
        return 0.75

    async def _optimize_timing(self, draft: Draft) -> str:
        """Optimize posting time. Placeholder."""
        return datetime.now(timezone.utc).isoformat()

    async def _generate_variant(self, draft: Draft) -> str:
        """Generate A/B variant. Placeholder."""
        return f"Variant of: {draft.processed_content[:50]}..."

    async def queue_draft_for_review(self, draft: Draft) -> str:
        """
        Queue a generated draft in the War Room as a REVIEW action.

        Per spec: draft_ready message MUST be sent BEFORE any draft
        appears in the War Room queue. War Room reads from message,
        not filesystem.

        Returns action_id for tracking.

        War Room card shows:
        - Claw: CONTENT CLAW
        - Mode: REVIEW
        - Summary: "Draft ready: {platform} {content_type} for {client_id or 'own content'}"
        - Metadata: platform, tone, approval_probability, scheduled_time
        - Actions: [View Draft] [APPROVE] [EDIT] [BLOCK]
        - If variant_b exists: [Compare A/B] link
        """
        if not self._war_room:
            logger.warning("No War Room client configured, cannot queue draft %s", draft.draft_id)
            return ""

        client_desc = draft.client_id or "own content"
        summary = f"Draft ready: {draft.platform} {draft.content_type} for {client_desc}"

        draft_ready_message = {
            "message_type": "draft_ready",
            "sender_role": "content",
            "recipient_role": "war_room",
            "payload": {
                "draft_id": draft.draft_id,
                "platform": draft.platform,
                "content_type": draft.content_type,
                "client_id": draft.client_id,
                "project_id": draft.project_id,
                "brief_id": draft.brief_id,
                "approval_probability": draft.approval_probability,
                "variants_count": 2 if draft.variant_b else 1,
                "tone": draft.tone,
                "scheduled_time": draft.scheduled_time,
                "has_variant_b": draft.variant_b is not None,
            },
        }

        if self._war_room and hasattr(self._war_room, 'send_message'):
            self._war_room.send_message(draft_ready_message)
            logger.debug("Sent draft_ready message for draft %s", draft.draft_id)

        payload = {
            "draft_id": draft.draft_id,
            "platform": draft.platform,
            "content_type": draft.content_type,
            "client_id": draft.client_id,
            "project_id": draft.project_id,
            "brief_id": draft.brief_id,
            "content_preview": draft.processed_content[:200],
            "tone": draft.tone,
            "approval_probability": draft.approval_probability,
            "scheduled_time": draft.scheduled_time,
            "has_variant": draft.variant_b is not None,
            "tools_applied": draft.tools_applied,
        }

        action = self._war_room.queue_action(
            claw="content",
            action_type="draft_review",
            payload=payload,
        )

        logger.info("Draft %s queued for review as action %s", draft.draft_id, action.id)

        self._log.append(LogEntry(
            action_type="draft_queued_for_review",
            entity_id=draft.draft_id,
            outcome="success",
            platform=draft.platform,
            client_id=draft.client_id,
            details={"action_id": action.id, "brief_id": draft.brief_id},
        ))

        return action.id
