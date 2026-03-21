"""LINE event handlers."""

from __future__ import annotations

from datetime import UTC, datetime

from linebot.v3.messaging import (  # type: ignore[import-untyped]
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import FollowEvent, MessageEvent, UnfollowEvent  # type: ignore[import-untyped]

from ai_journaling_agent.core.classifier import classify_message, emoji_to_mood, parse_structured_entry
from ai_journaling_agent.core.inbox import InboxMessage, InboxRepository, generate_message_id
from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.mood import format_mood_timeline, get_mood_trend
from ai_journaling_agent.core.prompts import WELCOME_BACK
from ai_journaling_agent.core.repository import JournalRepository
from ai_journaling_agent.core.user import UserRepository, UserState

_MOOD_KEYWORDS = {"気分の波", "ムード", "きぶんのなみ"}
_RETROSPECTIVE_KEYWORDS = {"今週のふりかえり", "ふりかえり", "振り返り"}


async def handle_message_event(
    event: MessageEvent,
    line_api: AsyncMessagingApi,
    repository: JournalRepository,
    user_repository: UserRepository,
    inbox_repository: InboxRepository,
) -> None:
    """Handle incoming text messages.

    Saves the message to the inbox and journal, but does not reply.
    AI responses are sent later by the Claude Code /loop process via push API.
    """
    user_id: str = event.source.user_id
    text: str = event.message.text
    now = datetime.now(tz=UTC)

    # Mood trend keyword detection — reply immediately and skip journal save
    if any(kw in text for kw in _MOOD_KEYWORDS):
        trend = get_mood_trend(repository, user_id)
        timeline = format_mood_timeline(trend)
        await line_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"直近7日間の気分の波:\n{timeline}")],
            )
        )
        return

    # Retrospective keyword detection — reply immediately and skip journal save
    if any(kw in text for kw in _RETROSPECTIVE_KEYWORDS):
        from datetime import timedelta
        today = now.date()
        week_start = today - timedelta(days=6)
        week_end = today
        from ai_journaling_agent.core.retrospective import _collect_entries_text
        entries_text = _collect_entries_text(repository, user_id, week_start, week_end)
        if entries_text:
            reply_text = f"今週のふりかえり:\n{entries_text}"
        else:
            reply_text = "今週の記録はまだありませんでした。"
        await line_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )
        return

    # Update user last_interaction
    user_state = user_repository.get(user_id)
    if user_state is not None:
        user_state.last_interaction = now
        user_repository.save(user_state)

    # Classify and save journal entry
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
        stripped = text.strip()
        entry = JournalEntry(
            timestamp=now,
            level=level,
            emoji=stripped,
            mood_emoji=stripped,
            mood=emoji_to_mood(stripped),
        )
    else:
        entry = JournalEntry(
            timestamp=now,
            level=level,
            summary=text,
        )

    repository.save(user_id, entry)

    # Save to inbox for async AI processing
    inbox_msg = InboxMessage(
        id=generate_message_id(now),
        user_id=user_id,
        text=text,
        received_at=now,
        status="pending",
    )
    inbox_repository.save(inbox_msg)

    # No LINE reply — AI response will be sent via push API by /loop


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
