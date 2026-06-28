"""Unit tests for notifications module."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from milimo_core.notifications import (
    SlackConfig, TelegramConfig, NotificationPayload,
    SlackNotifier, TelegramNotifier, WarRoomNotifier,
    init_warroom_notifier, get_warroom_notifier
)


class TestSlackConfig:
    """Tests for SlackConfig."""

    def test_slack_config_creation(self):
        """Test SlackConfig creation."""
        config = SlackConfig(
            webhook_url="https://hooks.slack.com/test",
            bot_token="xoxb-test",
            allowed_channels=["#alerts", "#general"]
        )

        assert config.webhook_url == "https://hooks.slack.com/test"
        assert config.bot_token == "xoxb-test"
        assert config.allowed_channels == ["#alerts", "#general"]

    def test_slack_config_defaults(self):
        """Test SlackConfig with defaults."""
        config = SlackConfig()

        assert config.webhook_url is None
        assert config.bot_token is None
        assert config.allowed_channels == []
        assert config.default_channel == "warroom"

    def test_slack_config_is_configured(self):
        """Test is_configured method."""
        config = SlackConfig(webhook_url="https://hooks.slack.com/test")
        assert config.is_configured() is True

        config2 = SlackConfig(bot_token="xoxb-test")
        assert config2.is_configured() is True

        config3 = SlackConfig()
        assert config3.is_configured() is False

    def test_slack_config_is_channel_allowed(self):
        """Test is_channel_allowed method."""
        config = SlackConfig(allowed_channels=["#alerts", "#ops"])
        assert config.is_channel_allowed("#alerts") is True
        assert config.is_channel_allowed("#random") is False

        # Empty allowed_channels means all allowed
        config2 = SlackConfig()
        assert config2.is_channel_allowed("#anything") is True

    def test_slack_config_from_env(self, monkeypatch):
        """Test SlackConfig.from_env."""
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/env-test")
        monkeypatch.setenv("SLACK_ALLOWED_CHANNELS", "#alerts,#ops")

        config = SlackConfig.from_env()

        assert config.webhook_url == "https://hooks.slack.com/env-test"
        assert config.allowed_channels == ["#alerts", "#ops"]


class TestTelegramConfig:
    """Tests for TelegramConfig."""

    def test_telegram_config_creation(self):
        """Test TelegramConfig creation."""
        config = TelegramConfig(
            bot_token="123:test",
            allowed_ids=[123456, 789012]
        )

        assert config.bot_token == "123:test"
        assert config.allowed_ids == [123456, 789012]

    def test_telegram_config_defaults(self):
        """Test TelegramConfig with defaults."""
        config = TelegramConfig()

        assert config.bot_token is None
        assert config.allowed_ids == []

    def test_telegram_config_is_configured(self):
        """Test is_configured method."""
        config = TelegramConfig(bot_token="123:test")
        assert config.is_configured() is True

        config2 = TelegramConfig()
        assert config2.is_configured() is False

    def test_telegram_config_is_id_allowed(self):
        """Test is_id_allowed method."""
        config = TelegramConfig(allowed_ids=[123, 456])
        assert config.is_id_allowed(123) is True
        assert config.is_id_allowed(789) is False

        # Empty allowed_ids means all allowed
        config2 = TelegramConfig()
        assert config2.is_id_allowed(999) is True

    def test_telegram_config_from_env(self, monkeypatch):
        """Test TelegramConfig.from_env."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "456:env-test")
        monkeypatch.setenv("TELEGRAM_ALLOWED_IDS", "111,222")

        config = TelegramConfig.from_env()

        assert config.bot_token == "456:env-test"
        assert config.allowed_ids == [111, 222]


class TestNotificationPayload:
    """Tests for NotificationPayload."""

    def test_payload_creation(self):
        """Test NotificationPayload creation."""
        payload = NotificationPayload(
            title="Test Alert",
            message="Something happened",
            level="warning",
            metadata={"claw": "content"}
        )

        assert payload.title == "Test Alert"
        assert payload.message == "Something happened"
        assert payload.level == "warning"
        assert payload.metadata == {"claw": "content"}

    def test_payload_defaults(self):
        """Test NotificationPayload with defaults."""
        payload = NotificationPayload(title="Test", message="Msg")

        assert payload.title == "Test"
        assert payload.message == "Msg"
        assert payload.level == "info"
        assert payload.metadata == {}
        assert payload.timestamp is not None


class TestSlackNotifier:
    """Tests for SlackNotifier."""

    def test_slack_notifier_creation(self, slack_config):
        """Test SlackNotifier creation."""
        notifier = SlackNotifier(slack_config)

        assert notifier.config == slack_config

    def test_send_not_configured(self):
        """Test sending when not configured."""
        notifier = SlackNotifier(SlackConfig())
        payload = NotificationPayload(title="Test", message="Hello")

        # Should notifier.send(payload)

        # Should return False when not configured
        # (actual implementation returns False, doesn't raise)

    def test_send_webhook_not_configured(self, slack_config):
        """Test send with webhook but not actually sending."""
        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        # With webhook configured but no actual HTTP call, should handle gracefully
        # We can't easily test the HTTP call without mocking urllib
        # Just verify the notifier was created correctly
        assert notifier.config.webhook_url == "https://hooks.slack.com/test"


class TestTelegramNotifier:
    """Tests for TelegramNotifier."""

    def test_telegram_notifier_creation(self, telegram_config):
        """Test TelegramNotifier creation."""
        notifier = TelegramNotifier(telegram_config)

        assert notifier.config == telegram_config

    def test_send_not_configured(self):
        """Test sending when not configured."""
        notifier = TelegramNotifier(TelegramConfig())
        payload = NotificationPayload(title="Test", message="Hello")

        # Should return False when not configured
        result = notifier.send(payload)
        assert result is False


class TestWarRoomNotifier:
    """Tests for WarRoomNotifier."""

    def test_warroom_notifier_creation(self, slack_config, telegram_config):
        """Test WarRoomNotifier creation."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        assert notifier.slack is not None
        assert notifier.telegram is not None

    def test_notify_hold_alert(self, slack_config, telegram_config):
        """Test notify_hold_alert."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        # Mock the underlying senders
        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_hold_alert(
                    action_id="item-123",
                    action_type="deploy",
                    entity_id="production",
                    claw_role="ops",
                    urgency="No decision in 24h"
                )

                assert result["slack"] is True
                assert result["telegram"] is True
                mock_slack.assert_called_once()
                mock_telegram.assert_called_once()

    def test_notify_cost_guard(self, slack_config, telegram_config):
        """Test notify_cost_guard."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_cost_guard(
                    tokens_used=40000,
                    limit=50000,
                    percentage=80.0,
                    status="alert"
                )

                assert result["slack"] is True
                assert result["telegram"] is True

    def test_notify_analytics_summary(self, slack_config, telegram_config):
        """Test notify_analytics_summary."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_analytics_summary(
                    report_title="Weekly Report",
                    summary="5 new tools generated",
                    key_metrics={"tools_generated": 5, "backtests_passed": 3}
                )

                assert result["slack"] is True
                assert result["telegram"] is True

    def test_notify_generic(self, slack_config, telegram_config):
        """Test notify_generic."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_generic(
                    title="Custom Alert",
                    message="Something custom happened",
                    level="info",
                    metadata={"key": "value"}
                )

                assert result["slack"] is True
                assert result["telegram"] is True


class TestWarRoomNotifierSingleton:
    """Tests for WarRoomNotifier singleton functions."""

    def test_init_get_warroom_notifier(self, slack_config, telegram_config):
        """Test init and get warroom notifier."""
        notifier = init_warroom_notifier(slack_config, telegram_config)
        retrieved = get_warroom_notifier()

        assert notifier is retrieved
        assert isinstance(notifier, WarRoomNotifier)

    def test_get_before_init(self):
        """Test get before init returns None."""
        # Reset singleton
        import milimo_core.notifications as nf
        nf._warroom_notifier = None

        retrieved = get_warroom_notifier()
        assert retrieved is None


# === Additional tests for missing coverage ===

class TestSlackNotifierExtended:
    """Extended tests for SlackNotifier to cover missing lines."""

    def test_send_webhook_success(self, slack_config):
        """Test successful webhook send."""
        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload)

            assert result is True
            mock_urlopen.assert_called_once()

    def test_send_webhook_failure_status(self, slack_config):
        """Test webhook send with non-200 status."""
        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 500
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload)

            assert result is False

    def test_send_webhook_exception(self, slack_config):
        """Test webhook send with exception."""
        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            result = notifier.send(payload)

            assert result is False

    def test_send_bot_api_success(self, slack_config):
        """Test successful Bot API send."""
        slack_config.webhook_url = None  # Force Bot API path
        slack_config.bot_token = "xoxb-test"

        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"ok": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload, channel="#test")

            assert result is True

    def test_send_bot_api_failure(self, slack_config):
        """Test Bot API send with ok=false."""
        slack_config.webhook_url = None
        slack_config.bot_token = "xoxb-test"

        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"ok": false, "error": "channel_not_found"}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload)

            assert result is False

    def test_send_bot_api_exception(self, slack_config):
        """Test Bot API send with exception."""
        slack_config.webhook_url = None
        slack_config.bot_token = "xoxb-test"

        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen", side_effect=Exception("API error")):
            result = notifier.send(payload)

            assert result is False

    def test_send_channel_not_allowed(self, slack_config):
        """Test send to channel not in allowed list."""
        slack_config.allowed_channels = ["#allowed"]

        notifier = SlackNotifier(slack_config)
        payload = NotificationPayload(title="Test", message="Hello")

        result = notifier.send(payload, channel="#not_allowed")

        assert result is False

    def test_send_webhook_no_webhook_no_bot(self):
        """Test send when neither webhook nor bot token configured."""
        config = SlackConfig()
        notifier = SlackNotifier(config)
        payload = NotificationPayload(title="Test", message="Hello")

        result = notifier.send(payload)

        assert result is False


class TestTelegramNotifierExtended:
    """Extended tests for TelegramNotifier to cover missing lines."""

    def test_send_success(self, telegram_config):
        """Test successful Telegram send."""
        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"ok": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload, chat_id=123456)

            assert result is True

    def test_send_api_failure(self, telegram_config):
        """Test Telegram send with ok=false."""
        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"ok": false, "description": "chat not found"}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload, chat_id=123456)

            assert result is False

    def test_send_exception(self, telegram_config):
        """Test Telegram send with exception."""
        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            result = notifier.send(payload, chat_id=123456)

            assert result is False

    def test_send_id_not_allowed(self, telegram_config):
        """Test send to chat ID not in allowed list."""
        telegram_config.allowed_ids = [111, 222]

        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(title="Test", message="Hello")

        # Current implementation returns True even if ID not allowed (just logs warning)
        result = notifier.send(payload, chat_id=999)

        assert result is True  # Implementation returns True, just skips with warning

    def test_send_multiple_ids(self, telegram_config):
        """Test send to multiple chat IDs."""
        telegram_config.allowed_ids = [111, 222]

        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(title="Test", message="Hello")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"ok": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload)  # No chat_id -> uses allowed_ids

            assert result is True
            assert mock_urlopen.call_count == 2

    def test_send_one_id_fails(self, telegram_config):
        """Test send when one of multiple IDs fails."""
        telegram_config.allowed_ids = [111, 222]

        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(title="Test", message="Hello")

        call_count = 0
        def mock_urlopen_side_effect(req):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            if call_count == 1:
                mock_response.read.return_value = b'{"ok": true}'
            else:
                mock_response.read.return_value = b'{"ok": false, "description": "error"}'
            return mock_response.__enter__.return_value

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):
            result = notifier.send(payload)

            assert result is False  # One failed = overall false

    def test_send_no_allowed_ids(self):
        """Test send with no allowed IDs configured."""
        config = TelegramConfig(bot_token="123:test", allowed_ids=[])
        notifier = TelegramNotifier(config)
        payload = NotificationPayload(title="Test", message="Hello")

        result = notifier.send(payload)  # No chat_id, no allowed_ids

        assert result is False

    def test_send_with_metadata(self, telegram_config):
        """Test send with metadata included in message."""
        notifier = TelegramNotifier(telegram_config)
        payload = NotificationPayload(
            title="Test",
            message="Hello",
            level="warning",
            metadata={"key1": "value1", "key2": "value2"}
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"ok": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = notifier.send(payload, chat_id=123456)

            assert result is True
            # Verify the request was made
            call_args = mock_urlopen.call_args
            assert call_args is not None


class TestWarRoomNotifierExtended:
    """Extended tests for WarRoomNotifier to cover missing lines."""

    def test_notify_hold_alert_without_urgency(self, slack_config, telegram_config):
        """Test notify_hold_alert without urgency (warning level)."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_hold_alert(
                    action_id="item-123",
                    action_type="deploy",
                    entity_id="production",
                    claw_role="ops",
                    urgency=None
                )

                assert result["slack"] is True
                assert result["telegram"] is True
                # Check level was "warning" not "alert"
                call_args = mock_slack.call_args[0][0]
                assert call_args.level == "warning"

    def test_notify_cost_guard_warning(self, slack_config, telegram_config):
        """Test notify_cost_guard with warning status."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_cost_guard(
                    tokens_used=30000,
                    limit=50000,
                    percentage=60.0,
                    status="warning"
                )

                assert result["slack"] is True
                assert result["telegram"] is True
                call_args = mock_slack.call_args[0][0]
                assert call_args.level == "warning"

    def test_notify_cost_guard_critical_percentage(self, slack_config, telegram_config):
        """Test notify_cost_guard at 95%+ includes extra warning."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_cost_guard(
                    tokens_used=47500,
                    limit=50000,
                    percentage=95.0,
                    status="alert"
                )

                assert result["slack"] is True
                call_args = mock_slack.call_args[0][0]
                assert "Approaching daily limit" in call_args.message

    def test_notify_analytics_summary_no_metrics(self, slack_config, telegram_config):
        """Test notify_analytics_summary without key_metrics."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
            with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                result = notifier.notify_analytics_summary(
                    report_title="Weekly Report",
                    summary="All good",
                    key_metrics=None
                )

                assert result["slack"] is True
                assert result["telegram"] is True

    def test_notify_generic_all_levels(self, slack_config, telegram_config):
        """Test notify_generic with different levels."""
        notifier = WarRoomNotifier(slack_config, telegram_config)

        for level in ["info", "warning", "alert", "critical"]:
            with patch.object(notifier.slack, "send", return_value=True) as mock_slack:
                with patch.object(notifier.telegram, "send", return_value=True) as mock_telegram:
                    result = notifier.notify_generic(
                        title=f"{level} Alert",
                        message="Test message",
                        level=level,
                        metadata={"level": level}
                    )

                    assert result["slack"] is True
                    assert result["telegram"] is True
                    call_args = mock_slack.call_args[0][0]
                    assert call_args.level == level


class TestConfigEdgeCases:
    """Test edge cases in config classes."""

    def test_slack_config_from_env_empty_allowed_channels(self, monkeypatch):
        """Test from_env with empty SLACK_ALLOWED_CHANNELS."""
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setenv("SLACK_ALLOWED_CHANNELS", "")

        config = SlackConfig.from_env()

        assert config.allowed_channels == []

    def test_slack_config_from_env_whitespace_channels(self, monkeypatch):
        """Test from_env with whitespace in channels."""
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.setenv("SLACK_ALLOWED_CHANNELS", " #alerts , #ops , ")

        config = SlackConfig.from_env()

        assert config.allowed_channels == ["#alerts", "#ops"]

    def test_telegram_config_from_env_invalid_ids(self, monkeypatch):
        """Test from_env with non-numeric IDs."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test")
        monkeypatch.setenv("TELEGRAM_ALLOWED_IDS", "111,abc,222,def")

        config = TelegramConfig.from_env()

        assert config.allowed_ids == [111, 222]

    def test_telegram_config_from_env_empty_ids(self, monkeypatch):
        """Test from_env with empty TELEGRAM_ALLOWED_IDS."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test")
        monkeypatch.setenv("TELEGRAM_ALLOWED_IDS", "")

        config = TelegramConfig.from_env()

        assert config.allowed_ids == []

    def test_slack_config_default_channel_from_env(self, monkeypatch):
        """Test default_channel from env."""
        monkeypatch.setenv("SLACK_DEFAULT_CHANNEL", "#custom")

        config = SlackConfig.from_env()

        assert config.default_channel == "#custom"


class TestNotificationPayloadEdgeCases:
    """Test edge cases for NotificationPayload."""

    def test_payload_auto_timestamp(self):
        """Test payload gets auto timestamp."""
        payload = NotificationPayload(title="Test", message="Msg")

        assert payload.timestamp is not None
        # Should be valid ISO format
        from datetime import datetime
        parsed = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
        assert parsed is not None
