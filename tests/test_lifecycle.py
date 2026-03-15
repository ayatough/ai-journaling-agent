"""Integration tests for user lifecycle (Follow / Unfollow / Message)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from linebot.v3.webhooks import (  # type: ignore[import-untyped]
    FollowEvent,
    MessageEvent,
    Source,
    TextMessageContent,
    UnfollowEvent,
)

from ai_journaling_agent.adapters.line.handlers import (
    handle_follow_event,
    handle_message_event,
    handle_unfollow_event,
)
from ai_journaling_agent.core.user import JsonUserRepository, UserState


def _make_source(user_id: str) -> MagicMock:
    source = MagicMock(spec=Source)
    source.user_id = user_id
    return source


def _make_follow_event(user_id: str) -> MagicMock:
    event = MagicMock(spec=FollowEvent)
    event.source = _make_source(user_id)
    event.reply_token = "test-reply-token"
    return event


def _make_unfollow_event(user_id: str) -> MagicMock:
    event = MagicMock(spec=UnfollowEvent)
    event.source = _make_source(user_id)
    return event


def _make_message_event(user_id: str, text: str) -> MagicMock:
    event = MagicMock(spec=MessageEvent)
    event.source = _make_source(user_id)
    event.message = MagicMock(spec=TextMessageContent)
    event.message.text = text
    event.reply_token = "test-reply-token"
    return event


class TestFollowLifecycle:
    """Follow creates user state and sends welcome message."""

    @pytest.mark.asyncio
    async def test_follow_creates_user(self, tmp_path: object) -> None:
        from pathlib import Path

        user_repo = JsonUserRepository(Path(str(tmp_path)))
        line_api = AsyncMock()
        event = _make_follow_event("U1234")

        await handle_follow_event(event, line_api, user_repo)

        state = user_repo.get("U1234")
        assert state is not None
        assert state.is_active is True
        assert state.user_id == "U1234"
        line_api.reply_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_refollow_reactivates_user(self, tmp_path: object) -> None:
        from pathlib import Path

        path = Path(str(tmp_path))
        user_repo = JsonUserRepository(path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        user_repo.save(UserState("U1234", False, now, now))

        line_api = AsyncMock()
        event = _make_follow_event("U1234")
        await handle_follow_event(event, line_api, user_repo)

        state = user_repo.get("U1234")
        assert state is not None
        assert state.is_active is True


class TestUnfollowLifecycle:
    """Unfollow deactivates user without deleting data."""

    @pytest.mark.asyncio
    async def test_unfollow_deactivates_user(self, tmp_path: object) -> None:
        from pathlib import Path

        path = Path(str(tmp_path))
        user_repo = JsonUserRepository(path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        user_repo.save(UserState("U1234", True, now, now))

        event = _make_unfollow_event("U1234")
        await handle_unfollow_event(event, user_repo)

        state = user_repo.get("U1234")
        assert state is not None
        assert state.is_active is False

    @pytest.mark.asyncio
    async def test_unfollow_unknown_user_is_noop(self, tmp_path: object) -> None:
        from pathlib import Path

        user_repo = JsonUserRepository(Path(str(tmp_path)))
        event = _make_unfollow_event("U9999")
        # Should not raise
        await handle_unfollow_event(event, user_repo)


class TestMessageUpdatesInteraction:
    """Message events update last_interaction timestamp."""

    @pytest.mark.asyncio
    async def test_message_updates_last_interaction(self, tmp_path: object) -> None:
        from pathlib import Path

        path = Path(str(tmp_path))
        user_repo = JsonUserRepository(path)
        journal_repo = MagicMock()
        old_time = datetime(2026, 3, 14, 9, 0, 0, tzinfo=UTC)
        user_repo.save(UserState("U1234", True, old_time, old_time))

        line_api = AsyncMock()
        event = _make_message_event("U1234", "今日は良い日")
        await handle_message_event(event, line_api, journal_repo, user_repo)

        state = user_repo.get("U1234")
        assert state is not None
        assert state.last_interaction > old_time
