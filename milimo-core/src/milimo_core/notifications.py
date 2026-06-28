# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
War Room Notifier — Slack & Telegram notifications for MilimoClaw.

Integrates with Slack (webhook/Bot API) and Telegram (Bot API) for
HOLD alerts, cost guard warnings, and Analytics weekly summaries.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib import request

from .ssrf_validator import SSRFPolicy

logger = logging.getLogger("milimo.notifications")


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class SlackConfig:
    """Slack notification configuration."""
    webhook_url: str | None = None
    bot_token: str | None = None
    allowed_channels: list[str] = field(default_factory=list)
    default_channel: str = "warroom"

    @classmethod
    def from_env(cls) -> "SlackConfig":
        """Load config from environment variables."""
        allowed_channels = os.environ.get("SLACK_ALLOWED_CHANNELS", "").split(",")
        allowed_channels = [c.strip() for c in allowed_channels if c.strip()]

        return cls(
            webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
            bot_token=os.environ.get("SLACK_BOT_TOKEN"),
            allowed_channels=allowed_channels,
            default_channel=os.environ.get("SLACK_DEFAULT_CHANNEL", "warroom"),
        )

    def is_configured(self) -> bool:
        return bool(self.webhook_url or self.bot_token)

    def is_channel_allowed(self, channel: str) -> bool:
        if not self.allowed_channels:
            return True
        return channel in self.allowed_channels


@dataclass
class TelegramConfig:
    """Telegram notification configuration."""
    bot_token: str | None = None
    allowed_ids: list[int] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        """Load config from environment variables."""
        allowed_ids = os.environ.get("TELEGRAM_ALLOWED_IDS", "").split(",")
        allowed_ids = [int(i.strip()) for i in allowed_ids if i.strip().isdigit()]

        return cls(
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            allowed_ids=allowed_ids,
        )

    def is_configured(self) -> bool:
        return bool(self.bot_token)

    def is_id_allowed(self, chat_id: int) -> bool:
        if not self.allowed_ids:
            return True
        return chat_id in self.allowed_ids


# =============================================================================
# Payload Types
# =============================================================================


@dataclass
class NotificationPayload:
    """Standard notification payload."""
    title: str
    message: str
    level: str = "info"  # info, warning, alert, critical
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Notifiers
# =============================================================================


class SlackNotifier:
    """Sends notifications to Slack via webhook or Bot API."""

    def __init__(self, config: SlackConfig | None = None):
        self.config = config or SlackConfig.from_env()
        self._color_map = {
            "info": "#36a64f",
            "warning": "#ffaa00",
            "alert": "#ff0000",
            "critical": "#8b0000",
        }

    def send(self, payload: NotificationPayload, channel: str | None = None) -> bool:
        """Send notification to Slack."""
        if not self.config.is_configured():
            logger.debug("Slack not configured, skipping notification")
            return False

        target_channel = channel or self.config.default_channel
        if not self.config.is_channel_allowed(target_channel):
            logger.warning("Slack channel %s not in allowed list", target_channel)
            return False

        # Build Slack message
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": payload.title},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": payload.message},
            },
        ]

        if payload.metadata:
            fields = [{"type": "mrkdwn", "text": f"*{k}*:\n{v}"} for k, v in payload.metadata.items()]
            blocks.append({"type": "section", "fields": fields})

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"⏰ {payload.timestamp}"}],
        })

        message = {"blocks": blocks}

        try:
            if self.config.webhook_url:
                return self._send_webhook(message)
            elif self.config.bot_token:
                return self._send_bot_api(message, target_channel)
        except Exception as e:
            logger.error("Failed to send Slack notification: %s", e)
            return False

        return False

    def _send_webhook(self, message: dict) -> bool:
        """Send via incoming webhook."""
        data = json.dumps(message).encode("utf-8")
        req = request.Request(
            self.config.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=10) as resp:
            return resp.status == 200

    def _send_bot_api(self, message: dict, channel: str) -> bool:
        """Send via Bot API (chat.postMessage)."""
        if not self.config.bot_token:
            return False

        data = json.dumps({
            "channel": channel,
            "blocks": message.get("blocks", []),
        }).encode("utf-8")

        req = request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.bot_token}",
            },
        )
        with request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("ok", False)


class TelegramNotifier:
    """Sends notifications to Telegram via Bot API."""

    def __init__(self, config: TelegramConfig | None = None):
        self.config = config or TelegramConfig.from_env()

    def send(self, payload: NotificationPayload, chat_id: int | None = None) -> bool:
        """Send notification to Telegram."""
        if not self.config.is_configured():
            logger.debug("Telegram not configured, skipping notification")
            return False

        target_ids = [chat_id] if chat_id else self.config.allowed_ids
        if not target_ids:
            logger.warning("No Telegram chat IDs configured")
            return False

        # Build message with markdown
        level_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "alert": "🚨",
            "critical": "🔴",
        }
        emoji = level_emoji.get(payload.level, "ℹ️")

        text = f"{emoji} *{payload.title}*\n\n{payload.message}"
        if payload.metadata:
            text += "\n\n" + "\n".join(f"• *{k}*: `{v}`" for k, v in payload.metadata.items())
        text += f"\n\n_⏰ {payload.timestamp}_"

        success = True
        for tid in target_ids:
            if not self.config.is_id_allowed(tid):
                logger.warning("Telegram chat ID %d not in allowed list", tid)
                continue

            try:
                data = json.dumps({
                    "chat_id": tid,
                    "text": text,
                    "parse_mode": "Markdown",
                }).encode("utf-8")

                req = request.Request(
                    f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    if not result.get("ok", False):
                        logger.error("Telegram API error: %s", result.get("description"))
                        success = False
            except Exception as e:
                logger.error("Failed to send Telegram notification: %s", e)
                success = False

        return success


# =============================================================================
# War Room Notifier (High-level interface)
# =============================================================================


class WarRoomNotifier:
    """
    High-level War Room notifier combining Slack and Telegram.

    Provides domain-specific notification methods:
    - notify_hold_alert: HOLD queue items with urgency
    - notify_cost_guard: Token usage warnings/alerts
    - notify_analytics_summary: Weekly analytics report
    """

    def __init__(
        self,
        slack_config: SlackConfig | None = None,
        telegram_config: TelegramConfig | None = None,
    ):
        self.slack = SlackNotifier(slack_config)
        self.telegram = TelegramNotifier(telegram_config)

    def notify_hold_alert(
        self,
        action_id: str,
        action_type: str,
        entity_id: str,
        claw_role: str,
        urgency: str | None = None,
    ) -> dict[str, bool]:
        """Send HOLD queue alert notification."""
        level = "alert" if urgency else "warning"
        message = f"HOLD action `{action_id}` ({action_type}) for entity `{entity_id}` requires attention."
        if urgency:
            message += f"\n\n🚨 *Urgency*: {urgency}"

        payload = NotificationPayload(
            title="War Room: HOLD Alert",
            message=message,
            level=level,
            metadata={
                "Action ID": action_id,
                "Action Type": action_type,
                "Entity ID": entity_id,
                "Claw": claw_role,
            },
        )

        return {
            "slack": self.slack.send(payload),
            "telegram": self.telegram.send(payload),
        }

    def notify_cost_guard(
        self,
        tokens_used: int,
        limit: int,
        percentage: float,
        status: str,  # "warning" or "alert"
    ) -> dict[str, bool]:
        """Send cost guard notification."""
        level = "alert" if status == "alert" else "warning"
        message = (
            f"Daily token usage: *{tokens_used:,} / {limit:,}* ({percentage:.1f}%)\n"
            f"Status: **{status.upper()}**"
        )
        if percentage >= 95:
            message += "\n\n⚠️ *Approaching daily limit — review inference usage*"

        payload = NotificationPayload(
            title=f"War Room: Cost Guard {status.capitalize()}",
            message=message,
            level=level,
            metadata={
                "Tokens Used": f"{tokens_used:,}",
                "Daily Limit": f"{limit:,}",
                "Usage": f"{percentage:.1f}%",
            },
        )

        return {
            "slack": self.slack.send(payload),
            "telegram": self.telegram.send(payload),
        }

    def notify_analytics_summary(
        self,
        report_title: str,
        summary: str,
        key_metrics: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Send Analytics weekly summary."""
        payload = NotificationPayload(
            title=f"Analytics Weekly: {report_title}",
            message=summary,
            level="info",
            metadata=key_metrics or {},
        )

        return {
            "slack": self.slack.send(payload),
            "telegram": self.telegram.send(payload),
        }

    def notify_generic(
        self,
        title: str,
        message: str,
        level: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Send generic notification."""
        payload = NotificationPayload(
            title=title,
            message=message,
            level=level,
            metadata=metadata or {},
        )

        return {
            "slack": self.slack.send(payload),
            "telegram": self.telegram.send(payload),
        }


# =============================================================================
# Global Instance Management
# =============================================================================

_warroom_notifier: WarRoomNotifier | None = None


def init_warroom_notifier(
    slack_config: SlackConfig | None = None,
    telegram_config: TelegramConfig | None = None,
) -> WarRoomNotifier:
    """Initialize the global WarRoomNotifier."""
    global _warroom_notifier
    _warroom_notifier = WarRoomNotifier(slack_config, telegram_config)
    logger.info("WarRoomNotifier initialized (Slack: %s, Telegram: %s)",
                _warroom_notifier.slack.config.is_configured(),
                _warroom_notifier.telegram.config.is_configured())
    return _warroom_notifier


def get_warroom_notifier() -> WarRoomNotifier | None:
    """Get the global WarRoomNotifier instance."""
    return _warroom_notifier


__all__ = [
    "SlackConfig",
    "TelegramConfig",
    "NotificationPayload",
    "SlackNotifier",
    "TelegramNotifier",
    "WarRoomNotifier",
    "init_warroom_notifier",
    "get_warroom_notifier",
]
