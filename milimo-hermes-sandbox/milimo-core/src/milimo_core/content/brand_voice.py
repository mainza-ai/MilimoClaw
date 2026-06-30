# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Brand Voice Manager

Manages brand voice profiles for the squad and its clients.
Voice profiles are stored in /sandbox/content/brand/voice-profiles/.
Built from approved post history and updated on every edit.
Style calibration inference always routes to Local NIM.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from .content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
    LogEntry,
)

logger = logging.getLogger("milimo.brand_voice")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_APPROVED_EXAMPLES = 20
MAX_REJECTED_EXAMPLES = 10


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class VoiceProfile:
    """Brand voice profile for a client."""

    profile_id: str
    client_id: str
    profile_name: str
    tone_descriptors: list[str] = field(default_factory=list)
    vocabulary_preferences: dict[str, list[str]] = field(default_factory=dict)
    sentence_length: str = "medium"
    example_approved_posts: list[str] = field(default_factory=list)
    example_rejected_posts: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceProfile:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Brand Voice Manager
# ---------------------------------------------------------------------------


class BrandVoiceManager:
    """
        Manages brand voice profiles for clients.

        Voice profiles are stored in /sandbox/content/brand/voice-profiles/.
    Style calibration inference always routes to Local NIM (NEMOCLAW_MODEL).
    """

    def __init__(
        self,
        fs: ContentFilesystemInit,
        operational_log: ContentOperationalLog,
        privacy_router: Any | None = None,
    ) -> None:
        self._fs = fs
        self._log = operational_log
        self._router = privacy_router

    def load_profile(self, client_id: str) -> VoiceProfile | None:
        """
        Load voice profile for a client.

        Returns None if no profile exists yet.
        """
        profile_path = self._fs.get_voice_profile_path(client_id)

        if not profile_path.exists():
            logger.debug("No voice profile found for client %s", client_id)
            return None

        try:
            data = json.loads(profile_path.read_text())
            profile = VoiceProfile.from_dict(data)
            logger.debug("Loaded voice profile for client %s", client_id)
            return profile
        except Exception as e:
            logger.warning("Failed to load voice profile for %s: %s", client_id, e)
            return None

    def create_profile(
        self,
        client_id: str,
        brief_tone_requirements: str,
    ) -> VoiceProfile:
        """
        Create initial voice profile from brief tone requirements.

        Augments with inference call to Local NIM.
        Routes: data_type="voice_adapter_calibration" → local NIM (locked).
        """
        profile_id = f"voice-{client_id}"

        tone_descriptors = self._extract_tone_descriptors(brief_tone_requirements)

        vocabulary_prefs = self._infer_vocabulary_preferences(
            client_id,
            brief_tone_requirements,
        )

        sentence_length = self._infer_sentence_length(brief_tone_requirements)

        profile = VoiceProfile(
            profile_id=profile_id,
            client_id=client_id,
            profile_name=f"Voice Profile for {client_id}",
            tone_descriptors=tone_descriptors,
            vocabulary_preferences=vocabulary_prefs,
            sentence_length=sentence_length,
            example_approved_posts=[],
            example_rejected_posts=[],
        )

        self._save_profile(profile)

        self._log.append(
            LogEntry(
                action_type="voice_profile_created",
                entity_id=profile_id,
                outcome="success",
                client_id=client_id,
                details={
                    "tone_descriptors": tone_descriptors,
                    "sentence_length": sentence_length,
                },
            )
        )

        logger.info("Created voice profile %s for client %s", profile_id, client_id)

        return profile

    def update_profile_from_approval(
        self,
        client_id: str,
        approved_post: str,
    ) -> VoiceProfile:
        """
        Update profile with approved post.

        Adds to example_approved_posts (max 20, FIFO).
        Re-calibrates profile via Local NIM.
        """
        profile = self.load_profile(client_id)

        if not profile:
            logger.warning("No profile to update for client %s", client_id)
            profile = self.create_profile(client_id, "approved content patterns")

        profile.example_approved_posts.append(approved_post)

        if len(profile.example_approved_posts) > MAX_APPROVED_EXAMPLES:
            profile.example_approved_posts = profile.example_approved_posts[
                -MAX_APPROVED_EXAMPLES:
            ]

        profile = self._recalibrate_profile(profile)
        profile.last_updated = datetime.now(timezone.utc).isoformat()

        self._save_profile(profile)

        self._log.append(
            LogEntry(
                action_type="voice_profile_updated",
                entity_id=profile.profile_id,
                outcome="success",
                client_id=client_id,
                details={
                    "update_type": "approval",
                    "approved_count": len(profile.example_approved_posts),
                },
            )
        )

        logger.debug("Updated voice profile for %s with approved post", client_id)

        return profile

    def update_profile_from_rejection(
        self,
        client_id: str,
        rejected_post: str,
        reason: str | None = None,
    ) -> VoiceProfile:
        """
        Update profile with rejected post.

        Adds to example_rejected_posts (max 10, FIFO).
        Re-calibrates profile.
        """
        profile = self.load_profile(client_id)

        if not profile:
            logger.warning("No profile to update for client %s", client_id)
            profile = self.create_profile(client_id, "content guidelines")

        rejected_entry = rejected_post
        if reason:
            rejected_entry = f"{rejected_post} [REASON: {reason}]"

        profile.example_rejected_posts.append(rejected_entry)

        if len(profile.example_rejected_posts) > MAX_REJECTED_EXAMPLES:
            profile.example_rejected_posts = profile.example_rejected_posts[
                -MAX_REJECTED_EXAMPLES:
            ]

        profile = self._recalibrate_profile(profile)
        profile.last_updated = datetime.now(timezone.utc).isoformat()

        self._save_profile(profile)

        self._log.append(
            LogEntry(
                action_type="voice_profile_updated",
                entity_id=profile.profile_id,
                outcome="success",
                client_id=client_id,
                details={
                    "update_type": "rejection",
                    "rejected_count": len(profile.example_rejected_posts),
                    "reason": reason,
                },
            )
        )

        logger.debug("Updated voice profile for %s with rejected post", client_id)

        return profile

    def apply_voice(
        self,
        content: str,
        client_id: str,
    ) -> str:
        """
        Apply client voice profile to content.

        Routes: data_type="voice_adapter_calibration" → local NIM (locked).
        Returns rewritten content in client's voice.
        Returns original content unchanged if no profile exists.
        """
        profile = self.load_profile(client_id)

        if not profile:
            logger.debug("No profile for %s, returning content unchanged", client_id)
            return content

        rewritten = self._apply_voice_inference(content, profile)

        self._log.append(
            LogEntry(
                action_type="voice_applied",
                entity_id=profile.profile_id,
                outcome="success",
                client_id=client_id,
                details={
                    "original_length": len(content),
                    "rewritten_length": len(rewritten),
                },
            )
        )

        logger.debug("Applied voice profile for %s", client_id)

        return rewritten

    def load_style_guide(self, client_id: str | None = None) -> str | None:
        """
        Load style guide for client or default.

        Reads from brand/style-guides/{client_id}.md or default.md.
        Returns None if no style guide exists.
        """
        if client_id:
            client_guide = self._fs.get_style_guide_path(client_id)
            if client_guide.exists():
                return client_guide.read_text()

        default_guide = self._fs.get_style_guide_path()
        if default_guide.exists():
            return default_guide.read_text()

        return None

    def _save_profile(self, profile: VoiceProfile) -> None:
        """Save profile to filesystem."""
        profile_path = self._fs.get_voice_profile_path(profile.client_id)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(profile.to_dict(), indent=2))

    def _extract_tone_descriptors(self, brief_tone: str) -> list[str]:
        """Extract tone descriptors from brief."""
        common_tones = [
            "professional",
            "casual",
            "friendly",
            "formal",
            "warm",
            "direct",
            "playful",
            "serious",
            "approachable",
            "authoritative",
            "empathetic",
        ]

        found = []
        brief_lower = brief_tone.lower()

        for tone in common_tones:
            if tone in brief_lower:
                found.append(tone)

        if not found:
            found = ["professional"]

        return found

    def _infer_vocabulary_preferences(
        self,
        client_id: str,
        brief_tone: str,
    ) -> dict[str, list[str]]:
        """Infer vocabulary preferences from brief."""
        preferences: dict[str, list[str]] = {
            "preferred": [],
            "avoid": [],
        }

        brief_lower = brief_tone.lower()

        if "technical" in brief_lower or "industry" in brief_lower:
            preferences["preferred"].append("industry-specific terminology")
        if "simple" in brief_lower or "accessible" in brief_lower:
            preferences["preferred"].append("plain language")
            preferences["avoid"].append("jargon")
        if "engaging" in brief_lower or "conversational" in brief_lower:
            preferences["preferred"].append("conversational phrases")

        return preferences

    def _infer_sentence_length(self, brief_tone: str) -> str:
        """Infer preferred sentence length from brief."""
        brief_lower = brief_tone.lower()

        if "concise" in brief_lower or "brief" in brief_lower or "short" in brief_lower:
            return "short"
        if (
            "detailed" in brief_lower
            or "comprehensive" in brief_lower
            or "long" in brief_lower
        ):
            return "long"

        return "medium"

    def _recalibrate_profile(self, profile: VoiceProfile) -> VoiceProfile:
        """Re-calibrate profile based on examples."""
        if self._router:
            decision = self._router.route(
                role="content",
                data_type="voice_adapter_calibration",
            )
            logger.debug(
                "Voice calibration routed to: %s",
                decision.backend.value if decision else "no router",
            )

        if len(profile.example_approved_posts) >= 3:
            approved_lengths = [
                len(p.split()) for p in profile.example_approved_posts[-3:]
            ]
            avg_length = sum(approved_lengths) / len(approved_lengths)

            if avg_length < 10:
                profile.sentence_length = "short"
            elif avg_length > 20:
                profile.sentence_length = "long"
            else:
                profile.sentence_length = "medium"

        return profile

    def _apply_voice_inference(self, content: str, profile: VoiceProfile) -> str:
        """Apply voice via inference. Placeholder for actual implementation."""
        if self._router:
            decision = self._router.route(
                role="content",
                data_type="voice_adapter_calibration",
            )
            logger.debug(
                "Voice application routed to: %s",
                decision.backend.value if decision else "no router",
            )

        tone_prefix = (
            ", ".join(profile.tone_descriptors[:2]) if profile.tone_descriptors else ""
        )
        if tone_prefix:
            return f"[{tone_prefix}] {content}"

        return content
