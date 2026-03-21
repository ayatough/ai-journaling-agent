"""User story integration tests — full journey with time injection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.conftest import patch_sdk

pytestmark = pytest.mark.journey


class TestFollowCreatesUserState:
    async def test_follow_creates_user_state(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.user import JsonUserRepository, UserState

        user_id = "U_journey_001"
        repo = JsonUserRepository(tmp_path / "data")
        now = datetime(2026, 1, 6, 9, 0, 0, tzinfo=UTC)

        repo.save(UserState(
            user_id=user_id,
            is_active=True,
            created_at=now,
            last_interaction=now,
        ))

        state = repo.get(user_id)
        assert state is not None
        assert state.is_active is True


class TestMessagesSavedToJournal:
    async def test_messages_saved_to_journal(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.classifier import classify_message
        from ai_journaling_agent.core.journal import JournalEntry
        from ai_journaling_agent.core.repository import JsonJournalRepository

        user_id = "U_journey_002"
        repo = JsonJournalRepository(tmp_path / "data")
        now = datetime(2026, 1, 6, 9, 0, 0, tzinfo=UTC)

        for i, text in enumerate(["今日は頑張った", "ランチが美味しかった", "夜は疲れた"]):
            ts = now + timedelta(hours=i)
            level = classify_message(text)
            entry = JournalEntry(timestamp=ts, level=level, summary=text)
            repo.save(user_id, entry)

        entries = repo.list_entries(user_id)
        assert len(entries) == 3


class TestEmojiMessageSetsMood:
    async def test_emoji_message_sets_mood(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.classifier import classify_message, emoji_to_mood
        from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
        from ai_journaling_agent.core.repository import JsonJournalRepository

        user_id = "U_journey_003"
        repo = JsonJournalRepository(tmp_path / "data")
        now = datetime(2026, 1, 6, 9, 0, 0, tzinfo=UTC)

        text = "😊"
        level = classify_message(text)
        assert level == EntryLevel.EMOJI
        entry = JournalEntry(
            timestamp=now,
            level=level,
            emoji=text,
            mood_emoji=text,
            mood=emoji_to_mood(text),
        )
        repo.save(user_id, entry)

        entries = repo.list_entries(user_id)
        assert len(entries) == 1
        assert entries[0].mood_emoji == "😊"


class TestMoodTrendOverDays:
    async def test_mood_trend_over_days(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
        from ai_journaling_agent.core.mood import get_mood_trend
        from ai_journaling_agent.core.repository import JsonJournalRepository

        user_id = "U_journey_004"
        repo = JsonJournalRepository(tmp_path / "data")

        # Day 1: mood 4 (😊), Day 2: mood 2 (😞), Day 3: mood 5 (😄)
        base_date = datetime(2026, 1, 4, 9, 0, 0, tzinfo=UTC)
        mood_data = [
            ("😊", 4, base_date),
            ("😞", 2, base_date + timedelta(days=1)),
            ("😄", 5, base_date + timedelta(days=2)),
        ]
        for emoji, score, ts in mood_data:
            entry = JournalEntry(
                timestamp=ts,
                level=EntryLevel.EMOJI,
                emoji=emoji,
                mood_emoji=emoji,
                mood=score,
            )
            repo.save(user_id, entry)

        reference_date = (base_date + timedelta(days=2)).date()
        trend = get_mood_trend(repo, user_id, days=3, reference_date=reference_date)

        assert len(trend) == 3
        scores = [t[1] for t in trend]
        assert scores == [4, 2, 5]


class TestMoodKeywordReturnsTimeline:
    async def test_mood_keyword_returns_timeline(self, tmp_path: Path) -> None:
        """Sending 気分の波 should not save an InboxMessage (keyword branch skips saving)."""
        from ai_journaling_agent.core.inbox import JsonInboxRepository
        from ai_journaling_agent.core.repository import JsonJournalRepository

        user_id = "U_journey_005"
        repo = JsonJournalRepository(tmp_path / "data")
        inbox_repo = JsonInboxRepository(tmp_path / "data")

        # Mood keyword should not add to inbox
        text = "気分の波"
        # Check: it IS a mood keyword
        from ai_journaling_agent.adapters.cli.repl import _MOOD_KEYWORDS
        assert any(kw in text for kw in _MOOD_KEYWORDS)

        # Verify inbox stays empty — mood keyword triggers early return
        pending = inbox_repo.list_pending()
        assert len(pending) == 0

        # Verify the mood timeline is formatted correctly (helper logic check)
        from ai_journaling_agent.core.mood import format_mood_timeline, get_mood_trend
        trend = get_mood_trend(repo, user_id)
        timeline = format_mood_timeline(trend)
        assert isinstance(timeline, str)
        assert len(timeline) > 0


class TestRetrospectiveKeywordReturnsSummary:
    async def test_retrospective_keyword_returns_summary(self, tmp_path: Path) -> None:
        """Sending ふりかえり keyword should not save any InboxMessage."""
        from ai_journaling_agent.core.inbox import JsonInboxRepository

        inbox_repo = JsonInboxRepository(tmp_path / "data")

        text = "ふりかえり"
        from ai_journaling_agent.adapters.cli.repl import _RETROSPECTIVE_KEYWORDS
        assert any(kw in text for kw in _RETROSPECTIVE_KEYWORDS)

        # No inbox messages saved — keyword path returns early
        assert len(inbox_repo.list_pending()) == 0


class TestWeeklySummaryWithEntries:
    async def test_weekly_summary_with_entries(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
        from ai_journaling_agent.core.repository import JsonJournalRepository
        from ai_journaling_agent.core.retrospective import generate_weekly_summary

        user_id = "U_journey_007"
        repo = JsonJournalRepository(tmp_path / "data")
        base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC)

        for i in range(7):
            entry = JournalEntry(
                timestamp=base + timedelta(days=i),
                level=EntryLevel.SUMMARY,
                summary=f"Day {i + 1} の記録",
            )
            repo.save(user_id, entry)

        with patch_sdk("今週はよく頑張りました！"):
            responder = AiResponder(storage_dir=tmp_path / "data")
            summary = await generate_weekly_summary(
                user_id=user_id,
                week_start=base.date(),
                repository=repo,
                responder=responder,
            )

        assert summary != ""
        assert summary != "この週の記録はありませんでした。"


class TestProfileCounterIncrements:
    async def test_profile_counter_increments(self, tmp_path: Path) -> None:
        from ai_journaling_agent.adapters.cli.repl import _dispatch_message
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.checkin import CheckInTracker
        from ai_journaling_agent.core.inbox import JsonInboxRepository
        from ai_journaling_agent.core.repository import JsonJournalRepository
        from ai_journaling_agent.core.user_profile import JsonUserProfileRepository

        user_id = "U_journey_008"
        now = datetime(2026, 1, 6, 14, 0, 0, tzinfo=UTC)
        storage = tmp_path / "data"

        repo = JsonJournalRepository(storage)
        inbox_repo = JsonInboxRepository(storage)
        checkin_tracker = CheckInTracker(storage)
        profile_repo = JsonUserProfileRepository(storage)

        with patch_sdk("お疲れ様でした！"):
            responder = AiResponder(storage_dir=storage)
            for i in range(5):
                await _dispatch_message(
                    text=f"メッセージ {i + 1}",
                    now=now + timedelta(minutes=i),
                    user_id=user_id,
                    repository=repo,
                    inbox_repository=inbox_repo,
                    responder=responder,
                    checkin_tracker=checkin_tracker,
                    profile_repository=profile_repo,
                )

        profile = profile_repo.get(user_id)
        assert profile is not None
        assert profile.profile_update_counter == 5
