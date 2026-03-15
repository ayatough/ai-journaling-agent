"""Tests for LINE webhook endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from linebot.v3.exceptions import InvalidSignatureError  # type: ignore[import-untyped]
from linebot.v3.webhooks import (  # type: ignore[import-untyped]
    FollowEvent,
    MessageEvent,
    Source,
    TextMessageContent,
)

from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.prompts import WELCOME_BACK
from ai_journaling_agent.core.repository import JsonJournalRepository


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        line_channel_secret="test-secret",
        line_channel_access_token="test-token",
        storage_dir=tmp_path,
    )


def _make_message_event(user_id: str, text: str) -> MagicMock:
    event = MagicMock(spec=MessageEvent)
    event.source = MagicMock(spec=Source)
    event.source.user_id = user_id
    event.message = MagicMock(spec=TextMessageContent)
    event.message.text = text
    event.reply_token = "test-reply-token"
    return event


def _make_follow_event() -> MagicMock:
    event = MagicMock(spec=FollowEvent)
    event.reply_token = "test-reply-token"
    return event


def _create_test_client(tmp_path: Path, events: list[object]) -> TestClient:
    """Create a TestClient with mocked LINE SDK components."""
    from ai_journaling_agent.adapters.line.bot import create_app

    settings = _make_settings(tmp_path)

    with patch("ai_journaling_agent.adapters.line.bot.WebhookParser") as mock_parser_cls:
        mock_parser_cls.return_value.parse.return_value = events
        app = create_app(settings)

    return TestClient(app)


class TestSignatureVerification:
    """Invalid signatures return HTTP 400."""

    def test_invalid_signature_returns_400(self, tmp_path: Path) -> None:
        from ai_journaling_agent.adapters.line.bot import create_app

        settings = _make_settings(tmp_path)

        with patch("ai_journaling_agent.adapters.line.bot.WebhookParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.side_effect = InvalidSignatureError("bad")
            app = create_app(settings)

        client = TestClient(app)
        response = client.post(
            "/callback",
            content=b"{}",
            headers={"X-Line-Signature": "invalid"},
        )
        assert response.status_code == 400

    def test_missing_signature_returns_400(self, tmp_path: Path) -> None:
        from ai_journaling_agent.adapters.line.bot import create_app

        settings = _make_settings(tmp_path)

        with patch("ai_journaling_agent.adapters.line.bot.WebhookParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.side_effect = InvalidSignatureError("missing")
            app = create_app(settings)

        client = TestClient(app)
        response = client.post("/callback", content=b"{}")
        assert response.status_code == 400


class TestMessageEvent:
    """Text message handling."""

    @patch("ai_journaling_agent.adapters.line.bot.AsyncApiClient")
    def test_text_message_creates_entry_and_replies(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_api = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_api
        mock_client_cls.return_value = mock_ctx

        with patch("ai_journaling_agent.adapters.line.bot.AsyncMessagingApi") as mock_api_cls:
            mock_line_api = AsyncMock()
            mock_api_cls.return_value = mock_line_api

            event = _make_message_event("U1234", "今日は良い日")
            client = _create_test_client(tmp_path, [event])

            response = client.post(
                "/callback",
                content=b"{}",
                headers={"X-Line-Signature": "valid"},
            )

        assert response.status_code == 200
        mock_line_api.reply_message.assert_called_once()

        repo = JsonJournalRepository(tmp_path)
        entries = repo.list_entries("U1234")
        assert len(entries) == 1
        assert entries[0].summary == "今日は良い日"

    @patch("ai_journaling_agent.adapters.line.bot.AsyncApiClient")
    def test_emoji_stored_as_emoji_level(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = AsyncMock()
        mock_client_cls.return_value = mock_ctx

        with patch("ai_journaling_agent.adapters.line.bot.AsyncMessagingApi") as mock_api_cls:
            mock_api_cls.return_value = AsyncMock()

            event = _make_message_event("U1234", "😊")
            client = _create_test_client(tmp_path, [event])

            response = client.post(
                "/callback",
                content=b"{}",
                headers={"X-Line-Signature": "valid"},
            )

        assert response.status_code == 200
        repo = JsonJournalRepository(tmp_path)
        entries = repo.list_entries("U1234")
        assert len(entries) == 1
        assert entries[0].emoji == "😊"
        assert entries[0].level == 0  # EMOJI


class TestFollowEvent:
    """Follow event sends welcome message."""

    @patch("ai_journaling_agent.adapters.line.bot.AsyncApiClient")
    def test_follow_sends_welcome(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = AsyncMock()
        mock_client_cls.return_value = mock_ctx

        with patch("ai_journaling_agent.adapters.line.bot.AsyncMessagingApi") as mock_api_cls:
            mock_line_api = AsyncMock()
            mock_api_cls.return_value = mock_line_api

            event = _make_follow_event()
            client = _create_test_client(tmp_path, [event])

            response = client.post(
                "/callback",
                content=b"{}",
                headers={"X-Line-Signature": "valid"},
            )

        assert response.status_code == 200
        mock_line_api.reply_message.assert_called_once()
        call_args = mock_line_api.reply_message.call_args
        request = call_args[0][0]
        assert request.messages[0].text == WELCOME_BACK
