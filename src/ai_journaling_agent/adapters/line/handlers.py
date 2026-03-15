"""LINE event handlers."""

from __future__ import annotations

from datetime import UTC, datetime

from linebot.v3.messaging import (  # type: ignore[import-untyped]
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import FollowEvent, MessageEvent, UnfollowEvent  # type: ignore[import-untyped]

from ai_journaling_agent.core.classifier import classify_message, parse_structured_entry
from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.prompts import WELCOME_BACK
from ai_journaling_agent.core.repository import JournalRepository
from ai_journaling_agent.core.responses import generate_response
from ai_journaling_agent.core.scheduler import get_check_in_prompt
from ai_journaling_agent.core.user import UserRepository, UserState


async def handle_message_event(
    event: MessageEvent,
    line_api: AsyncMessagingApi,
    repository: JournalRepository,
    user_repository: UserRepository,
) -> None:
    """Handle incoming text messages.

    Classifies the message, creates a journal entry, and replies.
    Appends a check-in prompt when the time of day matches.
    """
    user_id: str = event.source.user_id
    text: str = event.message.text
    now = datetime.now(tz=UTC)

    # Update user last_interaction
    user_state = user_repository.get(user_id)
    if user_state is not None:
        user_state.last_interaction = now
        user_repository.save(user_state)

    level = classify_message(text)

    if level == EntryLevel.STRUCTURED:
        parsed = parse_structured_entry(text)
        entry = JournalEntry(
            timestamp=now,
            level=level,
            summary=text,
            achievements=parsed["achievements"],
            gratitude=parsed["gratitude"],
            learnings=parsed["learnings"],
        )
    elif level == EntryLevel.EMOJI:
        entry = JournalEntry(
            timestamp=now,
            level=level,
            emoji=text.strip(),
        )
    else:
        entry = JournalEntry(
            timestamp=now,
            level=level,
            summary=text,
        )

    repository.save(user_id, entry)

    reply_text = generate_response(entry)

    check_in = get_check_in_prompt(now.hour)
    if check_in:
        reply_text += "\n\n" + check_in

    await line_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply_text)],
        )
    )


async def handle_follow_event(
    event: FollowEvent,
    line_api: AsyncMessagingApi,
    user_repository: UserRepository,
) -> None:
    """Handle follow (friend add) events with welcome message."""
    now = datetime.now(tz=UTC)
    user_id: str = event.source.user_id

    user_state = user_repository.get(user_id)
    if user_state is not None:
        # Re-follow: reactivate
        user_state.is_active = True
        user_state.last_interaction = now
        user_repository.save(user_state)
    else:
        # New user
        user_repository.save(
            UserState(
                user_id=user_id,
                is_active=True,
                created_at=now,
                last_interaction=now,
            )
        )

    await line_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=WELCOME_BACK)],
        )
    )


async def handle_unfollow_event(
    event: UnfollowEvent,
    user_repository: UserRepository,
) -> None:
    """Handle unfollow (block) events by deactivating the user."""
    user_id: str = event.source.user_id
    user_state = user_repository.get(user_id)
    if user_state is not None:
        user_state.is_active = False
        user_repository.save(user_state)
