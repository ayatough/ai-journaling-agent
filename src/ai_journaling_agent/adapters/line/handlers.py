"""LINE event handlers."""

from __future__ import annotations

from datetime import UTC, datetime

from linebot.v3.messaging import (  # type: ignore[import-untyped]
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import FollowEvent, MessageEvent  # type: ignore[import-untyped]

from ai_journaling_agent.core.classifier import classify_message, parse_structured_entry
from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.prompts import WELCOME_BACK
from ai_journaling_agent.core.repository import JournalRepository
from ai_journaling_agent.core.responses import generate_response


async def handle_message_event(
    event: MessageEvent,
    line_api: AsyncMessagingApi,
    repository: JournalRepository,
) -> None:
    """Handle incoming text messages.

    Classifies the message, creates a journal entry, and replies.
    """
    user_id: str = event.source.user_id
    text: str = event.message.text

    level = classify_message(text)

    if level == EntryLevel.STRUCTURED:
        parsed = parse_structured_entry(text)
        entry = JournalEntry(
            timestamp=datetime.now(tz=UTC),
            level=level,
            summary=text,
            achievements=parsed["achievements"],
            gratitude=parsed["gratitude"],
            learnings=parsed["learnings"],
        )
    elif level == EntryLevel.EMOJI:
        entry = JournalEntry(
            timestamp=datetime.now(tz=UTC),
            level=level,
            emoji=text.strip(),
        )
    else:
        entry = JournalEntry(
            timestamp=datetime.now(tz=UTC),
            level=level,
            summary=text,
        )

    repository.save(user_id, entry)

    reply_text = generate_response(entry)
    await line_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_text)],
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
