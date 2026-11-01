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
from ai_journaling_agent.core.inbox import JsonInboxRepository
from ai_journaling_agent.core.prompts import WELCOME_BACK
from ai_journaling_agent.core.repository import JsonJournalRepository

OWNER = "U1234"


def _make_settings(tmp_path: Path, owner_user_id: str = OWNER) -> Settings:
    return Settings(
        line_channel_secret="test-secret",
        line_channel_access_token="test-token",
        storage_dir=tmp_path,
        owner_user_id=owner_user_id,
    )


def _make_message_event(user_id: str, text: str) -> MagicMock:
    event = MagicMock(spec=MessageEvent)
    event.source = MagicMock(spec=Source)
    event.source.user_id = user_id
    event.message = MagicMock(spec=TextMessageContent)
    event.message.text = text
    event.reply_token = "test-reply-token"
    return event


def _make_follow_event(user_id: str = OWNER) -> MagicMock:
    event = MagicMock(spec=FollowEvent)
    event.source = MagicMock(spec=Source)
    event.source.user_id = user_id
    event.reply_token = "test-reply-token"
    return event


def _create_test_client(tmp_path: Path, events: list[object], owner_user_id: str = OWNER) -> TestClient:
    """Create a TestClient with mocked LINE SDK components."""
    from ai_journaling_agent.adapters.line.bot import create_app

    settings = _make_settings(tmp_path, owner_user_id)

    with (
        patch("ai_journaling_agent.adapters.line.bot.WebhookParser") as mock_parser_cls,
        patch("ai_journaling_agent.adapters.line.bot.AiResponder"),
    ):
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
    """Text message handling — saves to journal and inbox, no reply."""

    @patch("ai_journaling_agent.adapters.line.bot._respond_to_user")
    @patch("ai_journaling_agent.adapters.line.bot.AsyncApiClient")
    def test_text_message_creates_entry_and_inbox(
        self, mock_client_cls: MagicMock, mock_respond: MagicMock, tmp_path: Path
    ) -> None:
        mock_api = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_api
        mock_client_cls.return_value = mock_ctx
        mock_respond.return_value = AsyncMock()

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
        # No reply sent (AI responds later via push)
        mock_line_api.reply_message.assert_not_called()

        # Journal entry saved
        repo = JsonJournalRepository(tmp_path)
        entries = repo.list_entries("U1234")
        assert len(entries) == 1
        assert entries[0].summary == "今日は良い日"

        # Inbox message saved
        inbox_repo = JsonInboxRepository(tmp_path)
        pending = inbox_repo.list_pending()
        assert len(pending) == 1
        assert pending[0].user_id == "U1234"
        assert pending[0].text == "今日は良い日"

    @patch("ai_journaling_agent.adapters.line.bot._respond_to_user")
    @patch("ai_journaling_agent.adapters.line.bot.AsyncApiClient")
    def test_emoji_stored_as_emoji_level(
        self, mock_client_cls: MagicMock, mock_respond: MagicMock, tmp_path: Path
    ) -> None:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = AsyncMock()
        mock_client_cls.return_value = mock_ctx
        mock_respond.return_value = AsyncMock()

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


class TestOwnerOnly:
    """Only the configured owner can use the bot; everyone else is ignored."""

    def _post(
        self, tmp_path: Path, events: list[object], owner_user_id: str = OWNER
    ) -> tuple[int, AsyncMock, MagicMock]:
        with (
            patch("ai_journaling_agent.adapters.line.bot._respond_to_user") as mock_respond,
            patch("ai_journaling_agent.adapters.line.bot.AsyncApiClient") as mock_client_cls,
            patch("ai_journaling_agent.adapters.line.bot.AsyncMessagingApi") as mock_api_cls,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = AsyncMock()
            mock_client_cls.return_value = mock_ctx
            mock_line_api = AsyncMock()
            mock_api_cls.return_value = mock_line_api
            client = _create_test_client(tmp_path, events, owner_user_id)
            response = client.post("/callback", content=b"{}", headers={"X-Line-Signature": "valid"})
        return response.status_code, mock_line_api, mock_respond

    def test_non_owner_message_is_ignored(self, tmp_path: Path) -> None:
        status, line_api, respond = self._post(tmp_path, [_make_message_event("U9999", "こんにちは")])
        assert status == 200
        respond.assert_not_called()
        line_api.reply_message.assert_not_called()
        assert JsonJournalRepository(tmp_path).list_entries("U9999") == []
        assert JsonInboxRepository(tmp_path).list_pending() == []

    def test_non_owner_follow_is_ignored(self, tmp_path: Path) -> None:
        status, line_api, _ = self._post(tmp_path, [_make_follow_event("U9999")])
        assert status == 200
        line_api.reply_message.assert_not_called()

    def test_owner_message_is_processed(self, tmp_path: Path) -> None:
        status, _, respond = self._post(tmp_path, [_make_message_event(OWNER, "今日は良い日")])
        assert status == 200
        assert len(JsonJournalRepository(tmp_path).list_entries(OWNER)) == 1

    def test_unset_owner_ignores_everyone(self, tmp_path: Path) -> None:
        status, _, respond = self._post(tmp_path, [_make_message_event(OWNER, "hi")], owner_user_id="")
        assert status == 200
        respond.assert_not_called()
        assert JsonJournalRepository(tmp_path).list_entries(OWNER) == []

    def test_mixed_events_only_owner_processed(self, tmp_path: Path) -> None:
        events = [_make_message_event("U9999", "spam"), _make_message_event(OWNER, "本物")]
        status, _, _ = self._post(tmp_path, events)
        assert status == 200
        assert JsonJournalRepository(tmp_path).list_entries("U9999") == []
        assert [e.summary for e in JsonJournalRepository(tmp_path).list_entries(OWNER)] == ["本物"]
