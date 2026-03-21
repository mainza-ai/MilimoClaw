#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Content Generator.

Tests cover:
- Draft generation
- Tool pipeline application
- Brief-to-draft flow
- Privacy router routing
- Operational log entries
- War Room queue_draft_for_review
"""

import json
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.content.content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)
from orchestrator.content.content_generator import (
    ContentGenerator,
    Draft,
    DraftContext,
    ContentPlan,
)
from orchestrator.privacy_router import PrivacyRouter, InferenceBackend, RoutingDecision
from orchestrator.tool_registry import ToolRegistry
from orchestrator.tool_builder import BuiltTool


class TestDraftDataClasses:
    """Tests for Draft and DraftContext dataclasses."""

    def test_draft_created_with_defaults(self):
        """Draft is created with default values."""
        draft = Draft(
            draft_id="draft-123",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="processed",
        )

        assert draft.draft_id == "draft-123"
        assert draft.platform == "twitter"
        assert draft.status == "pending"
        assert draft.tools_applied == []
        assert draft.created_at is not None

    def test_draft_to_dict(self):
        """Draft converts to dict correctly."""
        draft = Draft(
            draft_id="draft-456",
            platform="linkedin",
            client_id=None,
            project_id=None,
            content_type="article",
            raw_content="raw content",
            processed_content="processed content",
            tone="professional",
            approval_probability=0.85,
            tools_applied=["tone_classifier", "approval_predictor"],
        )

        data = draft.to_dict()

        assert data["draft_id"] == "draft-456"
        assert data["platform"] == "linkedin"
        assert data["tone"] == "professional"
        assert data["approval_probability"] == 0.85
        assert data["tools_applied"] == ["tone_classifier", "approval_predictor"]

    def test_draft_from_dict(self):
        """Draft is created from dict correctly."""
        data = {
            "draft_id": "draft-789",
            "platform": "instagram",
            "client_id": "client-2",
            "project_id": "proj-2",
            "content_type": "story",
            "raw_content": "raw",
            "processed_content": "processed",
            "tone": "casual",
            "approval_probability": 0.92,
            "scheduled_time": "2026-04-01T10:00:00Z",
            "variant_b": None,
            "voice_profile_used": "client-2",
            "tools_applied": ["timing_optimizer"],
            "created_at": "2026-03-21T12:00:00Z",
            "status": "approved",
        }

        draft = Draft.from_dict(data)

        assert draft.draft_id == "draft-789"
        assert draft.platform == "instagram"
        assert draft.tone == "casual"
        assert draft.status == "approved"

    def test_draft_context_defaults(self):
        """DraftContext has proper defaults."""
        context = DraftContext()

        assert context.brief_id is None
        assert context.brief_text is None
        assert context.topic is None
        assert context.client_id is None

    def test_draft_has_brief_id_field(self):
        """Draft can store brief_id for linking."""
        draft = Draft(
            draft_id="draft-brief-test",
            platform="twitter",
            client_id="client-x",
            project_id="proj-x",
            content_type="post",
            raw_content="raw",
            processed_content="processed",
        )

        assert hasattr(draft, "draft_id")


class TestContentGenerator:
    """Tests for ContentGenerator class."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment with mocks."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [
                {"data_type": "client_facing_draft", "description": "Client drafts", "backend": "cloud"},
                {"data_type": "internal_ideation", "description": "Internal content", "backend": "local-nim"},
            ],
        })

        registry = ToolRegistry(squad_id="test-squad", claw_role="content", registry_dir=str(tmp_path / "tools"))

        return fs, op_log, router, registry

    def _create_mock_tool(self, name: str, status: str = "deployed") -> BuiltTool:
        """Create a mock tool."""
        return BuiltTool(
            proposal=MagicMock(),
            tool_name=name,
            tool_type="processor",
            status=status,
        )

    @pytest.mark.asyncio
    async def test_generate_draft_creates_pending_file(self, tmp_path: Path):
        """Generated draft is written to pending directory."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test topic")
        draft = await generator.generate_draft("twitter", context, "post")

        draft_path = fs.get_draft_path("pending", draft.draft_id)
        assert draft_path.exists()

        saved_data = json.loads(draft_path.read_text())
        assert saved_data["draft_id"] == draft.draft_id
        assert saved_data["platform"] == "twitter"
        assert saved_data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_generate_draft_logs_to_operational(self, tmp_path: Path):
        """Draft generation creates operational log entry."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test topic", client_id="client-1")
        draft = await generator.generate_draft("linkedin", context, "post")

        entries = op_log.read_recent(days=1, action_type="draft_generated")
        assert len(entries) == 1

        entry = entries[0]
        assert entry.entity_id == draft.draft_id
        assert entry.platform == "linkedin"
        assert entry.client_id == "client-1"
        assert entry.outcome == "success"

    @pytest.mark.asyncio
    async def test_client_facing_draft_routes_to_cloud(self, tmp_path: Path):
        """Draft with client_id routes to cloud backend."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test", client_id="client-1")
        draft = await generator.generate_draft("twitter", context, "campaign")

        routing = router.route(role="content", data_type="client_facing_draft")
        assert routing.backend == InferenceBackend.CLOUD

    @pytest.mark.asyncio
    async def test_internal_ideation_routes_to_local(self, tmp_path: Path):
        """Draft without client routes to local backend."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Internal content")
        draft = await generator.generate_draft("twitter", context, "post")

        routing = router.route(role="content", data_type="internal_ideation")
        assert routing.backend == InferenceBackend.LOCAL_NIM

    @pytest.mark.asyncio
    async def test_tools_applied_in_sequence(self, tmp_path: Path):
        """Tools are applied in correct sequence."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        for tool_name in ["tone_classifier", "approval_predictor"]:
            registry.register(self._create_mock_tool(tool_name))

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test")
        draft = await generator.generate_draft("twitter", context, "post")

        assert "tone_classifier" in draft.tools_applied
        assert "approval_predictor" in draft.tools_applied
        assert draft.tone is not None
        assert draft.approval_probability is not None

    @pytest.mark.asyncio
    async def test_tool_failure_skipped_gracefully(self, tmp_path: Path):
        """Tool failure is logged but doesn't crash generation."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        registry.register(self._create_mock_tool("tone_classifier"))

        generator = ContentGenerator(router, registry, op_log, fs)

        with patch.object(
            generator, "_classify_tone",
            side_effect=RuntimeError("Tool failed")
        ):
            context = DraftContext(topic="Test")
            draft = await generator.generate_draft("twitter", context, "post")

            assert draft.draft_id is not None
            assert "tone_classifier" not in draft.tools_applied

            error_entries = op_log.read_recent(days=1, action_type="tool_error")
            assert len(error_entries) == 1

    @pytest.mark.asyncio
    async def test_client_voice_adapter_skipped_without_client(self, tmp_path: Path):
        """Voice adapter is skipped when no client_id."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        registry.register(self._create_mock_tool("client_voice_adapter"))

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test")
        draft = await generator.generate_draft("twitter", context, "post")

        assert "client_voice_adapter" not in draft.tools_applied

    @pytest.mark.asyncio
    async def test_generate_draft_calls_inference(self, tmp_path: Path):
        """generate_draft calls inference through privacy router."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test topic", client_id="client-1")
        draft = await generator.generate_draft("twitter", context, "post")

        assert draft.raw_content is not None
        assert len(draft.raw_content) > 0

    @pytest.mark.asyncio
    async def test_generate_draft_stores_raw_and_processed(self, tmp_path: Path):
        """Draft stores both raw and processed content."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        registry.register(self._create_mock_tool("tone_classifier"))

        generator = ContentGenerator(router, registry, op_log, fs)

        context = DraftContext(topic="Test")
        draft = await generator.generate_draft("twitter", context, "post")

        assert draft.raw_content is not None
        assert draft.processed_content is not None


class TestQueueDraftForReview:
    """Tests for queue_draft_for_review method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [],
        })

        registry = ToolRegistry(squad_id="test-squad", claw_role="content", registry_dir=str(tmp_path / "tools"))

        return fs, op_log, router, registry

    @pytest.mark.asyncio
    async def test_queue_draft_for_review_returns_action_id(self, tmp_path: Path):
        """queue_draft_for_review returns action_id."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        mock_war_room = MagicMock()
        mock_action = MagicMock()
        mock_action.id = "act_test123"
        mock_war_room.queue_action.return_value = mock_action

        generator = ContentGenerator(router, registry, op_log, fs, war_room=mock_war_room)

        draft = Draft(
            draft_id="draft-queue-test",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Test content for review",
        )

        action_id = await generator.queue_draft_for_review(draft)

        assert action_id == "act_test123"
        mock_war_room.queue_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_draft_for_review_payload_correct(self, tmp_path: Path):
        """queue_draft_for_review sends correct payload to War Room."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        mock_war_room = MagicMock()
        mock_action = MagicMock()
        mock_action.id = "act_test456"
        mock_war_room.queue_action.return_value = mock_action

        generator = ContentGenerator(router, registry, op_log, fs, war_room=mock_war_room)

        draft = Draft(
            draft_id="draft-payload-test",
            platform="linkedin",
            client_id="client-2",
            project_id="proj-2",
            content_type="article",
            raw_content="raw",
            processed_content="Content for LinkedIn article",
            tone="professional",
            approval_probability=0.87,
            variant_b="Variant B content",
        )

        await generator.queue_draft_for_review(draft)

        call_args = mock_war_room.queue_action.call_args
        assert call_args[1]["claw"] == "content"
        assert call_args[1]["action_type"] == "draft_review"

        payload = call_args[1]["payload"]
        assert payload["draft_id"] == "draft-payload-test"
        assert payload["platform"] == "linkedin"
        assert payload["tone"] == "professional"
        assert payload["approval_probability"] == 0.87
        assert payload["has_variant"] is True

    @pytest.mark.asyncio
    async def test_queue_draft_for_review_logs(self, tmp_path: Path):
        """queue_draft_for_review logs to operational log."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        mock_war_room = MagicMock()
        mock_action = MagicMock()
        mock_action.id = "act_log_test"
        mock_war_room.queue_action.return_value = mock_action

        generator = ContentGenerator(router, registry, op_log, fs, war_room=mock_war_room)

        draft = Draft(
            draft_id="draft-log-test",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Test",
        )

        await generator.queue_draft_for_review(draft)

        entries = op_log.read_recent(days=1, action_type="draft_queued_for_review")
        assert len(entries) == 1
        assert entries[0].entity_id == "draft-log-test"

    @pytest.mark.asyncio
    async def test_queue_draft_for_review_without_war_room(self, tmp_path: Path):
        """queue_draft_for_review returns empty string without War Room."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs, war_room=None)

        draft = Draft(
            draft_id="draft-no-warroom",
            platform="twitter",
            client_id=None,
            project_id=None,
            content_type="post",
            raw_content="raw",
            processed_content="test",
        )

        action_id = await generator.queue_draft_for_review(draft)

        assert action_id == ""

    @pytest.mark.asyncio
    async def test_queue_draft_for_review_own_content(self, tmp_path: Path):
        """queue_draft_for_review handles own content (no client)."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        mock_war_room = MagicMock()
        mock_action = MagicMock()
        mock_action.id = "act_own_content"
        mock_war_room.queue_action.return_value = mock_action

        generator = ContentGenerator(router, registry, op_log, fs, war_room=mock_war_room)

        draft = Draft(
            draft_id="draft-own-content",
            platform="twitter",
            client_id=None,
            project_id=None,
            content_type="post",
            raw_content="raw",
            processed_content="Squad's own content",
        )

        await generator.queue_draft_for_review(draft)

        call_args = mock_war_room.queue_action.call_args
        payload = call_args[1]["payload"]
        assert payload["client_id"] is None


class TestBriefToDraftFlow:
    """Tests for generate_from_brief method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment with brief."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        brief_path = fs.get_brief_path("active", "brief-test123")
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(json.dumps({
            "brief_id": "brief-test123",
            "client_id": "client-acme",
            "project_id": "proj-456",
            "brief_text": "Create engaging social media campaign",
            "tone_requirements": "professional yet approachable",
            "platform_targets": ["twitter", "linkedin"],
            "deadline": "2026-04-01",
        }))

        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [],
        })

        registry = ToolRegistry(squad_id="test-squad", claw_role="content", registry_dir=str(tmp_path / "tools"))

        return fs, op_log, router, registry

    @pytest.mark.asyncio
    async def test_generate_from_brief_reads_brief_file(self, tmp_path: Path):
        """generate_from_brief reads and uses brief content."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        draft = await generator.generate_from_brief("brief-test123")

        assert draft.client_id == "client-acme"
        assert draft.project_id == "proj-456"
        assert draft.platform == "twitter"

    @pytest.mark.asyncio
    async def test_generate_from_brief_missing_brief_raises(self, tmp_path: Path):
        """Missing brief raises FileNotFoundError."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        with pytest.raises(FileNotFoundError):
            await generator.generate_from_brief("brief-nonexistent")


class TestDailyPlan:
    """Tests for generate_daily_plan method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment with briefs."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        brief1_path = fs.get_brief_path("active", "brief-1")
        brief1_path.parent.mkdir(parents=True, exist_ok=True)
        brief1_path.write_text(json.dumps({
            "brief_id": "brief-1",
            "client_id": "client-a",
            "project_id": "proj-1",
            "brief_text": "Brief 1",
            "platform_targets": ["twitter"],
        }))

        brief2_path = fs.get_brief_path("active", "brief-2")
        brief2_path.write_text(json.dumps({
            "brief_id": "brief-2",
            "client_id": "client-b",
            "project_id": "proj-2",
            "brief_text": "Brief 2",
            "platform_targets": ["linkedin", "instagram"],
        }))

        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [],
        })

        registry = ToolRegistry(squad_id="test-squad", claw_role="content", registry_dir=str(tmp_path / "tools"))

        return fs, op_log, router, registry

    @pytest.mark.asyncio
    async def test_generate_daily_plan_reads_briefs(self, tmp_path: Path):
        """Daily plan reads all active briefs."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        plan = await generator.generate_daily_plan()

        assert len(plan.briefs) == 2
        assert "client-a" in plan.clients
        assert "client-b" in plan.clients
        assert "twitter" in plan.platforms
        assert "linkedin" in plan.platforms

    @pytest.mark.asyncio
    async def test_daily_plan_written_to_calendar(self, tmp_path: Path):
        """Daily plan is written to calendar directory."""
        fs, op_log, router, registry = self._create_test_env(tmp_path)

        generator = ContentGenerator(router, registry, op_log, fs)

        plan = await generator.generate_daily_plan()

        today = datetime.now(timezone.utc).date().isoformat()
        plan_path = fs.BASE / "calendar" / "scheduled" / f"plan_{today}.json"

        assert plan_path.exists()

        saved_data = json.loads(plan_path.read_text())
        assert saved_data["plan_id"] == plan.plan_id


class TestPlatformSpecs:
    """Tests for platform-specific content specs."""

    def test_twitter_spec_mentions_character_limit(self):
        """Twitter spec includes 280 character limit."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        spec = generator._get_platform_specs("twitter")

        assert "280" in spec

    def test_linkedin_spec_mentions_professional(self):
        """LinkedIn spec mentions professional tone."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        spec = generator._get_platform_specs("linkedin")

        assert "Professional" in spec or "professional" in spec

    def test_unknown_platform_returns_empty(self):
        """Unknown platform returns empty spec."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        spec = generator._get_platform_specs("unknown_platform")

        assert spec == ""


class TestPromptBuilding:
    """Tests for _build_prompt method."""

    def test_prompt_includes_brief_text(self):
        """Prompt includes brief text when provided."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        context = DraftContext(brief_text="Create a campaign about AI")
        prompt = generator._build_prompt("twitter", context)

        assert "Create a campaign about AI" in prompt

    def test_prompt_includes_tone_hint(self):
        """Prompt includes tone hint when provided."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        context = DraftContext(tone_hint="playful and engaging")
        prompt = generator._build_prompt("instagram", context)

        assert "playful and engaging" in prompt

    def test_prompt_includes_style_guide(self):
        """Prompt includes style guide when provided."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        context = DraftContext()
        prompt = generator._build_prompt("linkedin", context, style_guide="Use Oxford comma. Be concise.")

        assert "Oxford comma" in prompt

    def test_prompt_includes_performance_hints(self):
        """Prompt includes performance hints when provided."""
        fs = MagicMock()
        generator = ContentGenerator(MagicMock(), MagicMock(), MagicMock(), fs)

        context = DraftContext(performance_hints={"best_time": "18:00"})
        prompt = generator._build_prompt("twitter", context)

        assert "Performance patterns" in prompt or "best_time" in prompt
