"""LINE event handlers."""

from __future__ import annotations

from datetime import UTC, datetime

from linebot.v3.messaging import (  # type: ignore[import-untyped]
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import FollowEvent, MessageEvent  # type: ignore[import-untyped]

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.prompts import WELCOME_BACK
from ai_journaling_agent.core.repository import JournalRepository


async def handle_message_event(
    event: MessageEvent,
    line_api: AsyncMessagingApi,
    repository: JournalRepository,
) -> None:
    """Handle incoming text messages.

    Creates a journal entry and replies with confirmation.
    Classification logic will be added in Issue #4.
    """
    user_id: str = event.source.user_id
    text: str = event.message.text

    entry = JournalEntry(
        timestamp=datetime.now(tz=UTC),
        level=EntryLevel.EMOJI if len(text) <= 2 else EntryLevel.SUMMARY,
        emoji=text if len(text) <= 2 else None,
        summary=text if len(text) > 2 else None,
    )
    repository.save(user_id, entry)

    await line_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=f"記録しました: {text}")],
        )
    )


async def handle_follow_event(
    event: FollowEvent,
    line_api: AsyncMessagingApi,
) -> None:
    """Handle follow (friend add) events with welcome message."""
    await line_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=WELCOME_BACK)],
        )
    )
