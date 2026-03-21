"""Interactive CLI REPL for the AI journaling agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from ai_journaling_agent.core.ai_responder import AiResponder
from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.classifier import classify_message, emoji_to_mood, parse_structured_entry
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.inbox import InboxMessage, JsonInboxRepository, generate_message_id
from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.mood import format_mood_timeline, get_mood_trend
from ai_journaling_agent.core.repository import JsonJournalRepository
from ai_journaling_agent.core.retrospective import _collect_entries_text
from ai_journaling_agent.core.user import JsonUserRepository
from ai_journaling_agent.core.user_profile import JsonUserProfileRepository, UserProfile

_MOOD_KEYWORDS = {"気分の波", "ムード", "きぶんのなみ"}
_RETROSPECTIVE_KEYWORDS = {"今週のふりかえり", "ふりかえり", "振り返り"}

PROFILE_UPDATE_INTERVAL = 5


async def _dispatch_message(
    text: str,
    now: datetime,
    user_id: str,
    repository: JsonJournalRepository,
    inbox_repository: JsonInboxRepository,
    responder: AiResponder,
    checkin_tracker: CheckInTracker,
    profile_repository: JsonUserProfileRepository,
) -> str | None:
    """Dispatch a single message. Returns the AI response text, or None if handled as keyword."""
    # Mood trend keyword detection
    if any(kw in text for kw in _MOOD_KEYWORDS):
        trend = get_mood_trend(repository, user_id)
        timeline = format_mood_timeline(trend)
        return f"直近7日間の気分の波:\n{timeline}"

    # Retrospective keyword detection
    if any(kw in text for kw in _RETROSPECTIVE_KEYWORDS):
        from datetime import timedelta
        today = now.date()
        week_start = today - timedelta(days=6)
        week_end = today
        entries_text = _collect_entries_text(repository, user_id, week_start, week_end)
        if entries_text:
            return f"今週のふりかえり:\n{entries_text}"
        return "今週の記録はまだありませんでした。"

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

    # Save to inbox
    inbox_msg = InboxMessage(
        id=generate_message_id(now),
        user_id=user_id,
        text=text,
        received_at=now,
        status="pending",
    )
    inbox_repository.save(inbox_msg)

    # Generate AI response
    profile = profile_repository.get(user_id)
    checkin_prompt = checkin_tracker.get_recent_prompt(now=now)
    response = await responder.generate_response(user_id, text, checkin_prompt=checkin_prompt, profile=profile)

    # Profile auto-update
    if profile is None:
        profile = UserProfile(user_id=user_id)
    profile.profile_update_counter += 1
    if profile.profile_update_counter % PROFILE_UPDATE_INTERVAL == 0:
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates
        profile = await extract_profile_updates(text, profile, responder)
    profile_repository.save(profile)

    return response


async def async_main(user_id: str, now: datetime, storage_dir: Path) -> None:
    """Run the interactive REPL."""
    repository = JsonJournalRepository(storage_dir)
    user_repository = JsonUserRepository(storage_dir)
    inbox_repository = JsonInboxRepository(storage_dir)
    responder = AiResponder(storage_dir=storage_dir)
    checkin_tracker = CheckInTracker(storage_dir)
    profile_repository = JsonUserProfileRepository(storage_dir)

    # Ensure user exists
    user_state = user_repository.get(user_id)
    if user_state is None:
        from ai_journaling_agent.core.user import UserState
        user_repository.save(UserState(
            user_id=user_id,
            is_active=True,
            created_at=now,
            last_interaction=now,
        ))

    # Check-in prompt on startup
    checkin_prompt = checkin_tracker.needs_checkin(now)
    if checkin_prompt:
        print(checkin_prompt)
        checkin_tracker.record_sent_prompt(checkin_prompt, now)
        # Determine kind from hour in JST
        from zoneinfo import ZoneInfo
        jst = ZoneInfo("Asia/Tokyo")
        jst_now = now.astimezone(jst)
        hour = jst_now.hour
        if hour < 10:
            kind = "morning"
        elif hour < 13:
            kind = "midday"
        elif hour < 21:
            kind = "evening"
        else:
            kind = "night_summary"
        checkin_tracker.record_checkin(kind, jst_now.date())

    print("チャットを開始します。終了するには quit または exit を入力してください。")

    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\n終了します。")
            break

        text = text.strip()
        if not text:
            continue
        if text in ("quit", "exit"):
            print("終了します。")
            break

        response = await _dispatch_message(
            text=text,
            now=now,
            user_id=user_id,
            repository=repository,
            inbox_repository=inbox_repository,
            responder=responder,
            checkin_tracker=checkin_tracker,
            profile_repository=profile_repository,
        )
        if response:
            print(response)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the chat REPL."""
    parser = argparse.ArgumentParser(description="Interactive journaling REPL")
    parser.add_argument("--user", default=None, help="User ID (defaults to OWNER_USER_ID)")
    parser.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")

    args = parser.parse_args(argv)

    settings = Settings()  # type: ignore[call-arg]

    user_id = args.user or settings.owner_user_id
    if not user_id:
        print("Error: --user required or set OWNER_USER_ID in .env", file=sys.stderr)
        sys.exit(1)

    _now = datetime.fromisoformat(args.now).replace(tzinfo=UTC) if args.now else datetime.now(tz=UTC)

    asyncio.run(async_main(user_id=user_id, now=_now, storage_dir=settings.storage_dir))


if __name__ == "__main__":
    main(sys.argv[1:])
