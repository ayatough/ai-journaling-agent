"""Tests for mood trend analysis and formatting."""

from __future__ import annotations

from datetime import UTC, date, datetime

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.mood import format_mood_timeline, get_mood_trend


def _make_entry(d: date, mood: int | None = None, mood_emoji: str | None = None) -> JournalEntry:
    return JournalEntry(
        timestamp=datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC),
        level=EntryLevel.EMOJI if mood_emoji else EntryLevel.SUMMARY,
        summary="テスト",
        mood=mood,
        mood_emoji=mood_emoji,
    )


class _StubRepository:
    """Stub repository that returns pre-configured entries by date."""

    def __init__(self, entries_by_date: dict[date, list[JournalEntry]]) -> None:
        self._entries = entries_by_date

    def save(self, user_id: str, entry: JournalEntry) -> None:
        pass

    def list_entries(self, user_id: str, *, date: date | None = None) -> list[JournalEntry]:
        if date is None:
            all_entries = []
            for entries in self._entries.values():
                all_entries.extend(entries)
            return all_entries
        return self._entries.get(date, [])

    def get_latest(self, user_id: str) -> JournalEntry | None:
        return None


class TestGetMoodTrend:
    """get_mood_trend() returns correct mood data for each day."""

    def test_returns_mood_score_for_days_with_entries(self) -> None:
        ref = date(2026, 3, 15)
        d = date(2026, 3, 13)
        entry = _make_entry(d, mood=4)
        repo = _StubRepository({d: [entry]})

        trend = get_mood_trend(repo, "U1234", days=7, reference_date=ref)

        assert len(trend) == 7
        # Find the tuple for 2026-03-13
        result = {item[0]: item for item in trend}
        assert result[d][1] == 4

    def test_returns_none_for_days_without_entries(self) -> None:
        ref = date(2026, 3, 15)
        repo = _StubRepository({})

        trend = get_mood_trend(repo, "U1234", days=7, reference_date=ref)

        assert len(trend) == 7
        for d, score, emoji in trend:
            assert score is None
            assert emoji is None

    def test_reference_date_param_determines_end_date(self) -> None:
        ref = date(2026, 1, 10)
        repo = _StubRepository({})

        trend = get_mood_trend(repo, "U1234", days=3, reference_date=ref)

        dates = [item[0] for item in trend]
        assert dates == [date(2026, 1, 8), date(2026, 1, 9), date(2026, 1, 10)]

    def test_uses_last_entry_mood_when_multiple_entries(self) -> None:
        ref = date(2026, 3, 15)
        d = date(2026, 3, 15)
        entries = [
            _make_entry(d, mood=2),
            _make_entry(d, mood=5),
        ]
        repo = _StubRepository({d: entries})

        trend = get_mood_trend(repo, "U1234", days=1, reference_date=ref)

        # Should use last entry with mood (reversed iteration picks last)
        assert trend[0][1] == 5

    def test_mood_emoji_returned_when_present(self) -> None:
        ref = date(2026, 3, 15)
        d = date(2026, 3, 15)
        entry = _make_entry(d, mood=4, mood_emoji="😊")
        repo = _StubRepository({d: [entry]})

        trend = get_mood_trend(repo, "U1234", days=1, reference_date=ref)

        assert trend[0][2] == "😊"


class TestFormatMoodTimeline:
    """format_mood_timeline() formats trend as a text timeline."""

    def test_formats_emoji_mood(self) -> None:
        trend = [(date(2026, 3, 15), 4, "😊")]  # Sunday
        result = format_mood_timeline(trend)
        assert "😊" in result
        assert "3/15" in result

    def test_formats_score_mood_without_emoji(self) -> None:
        trend = [(date(2026, 3, 15), 3, None)]  # Sunday
        result = format_mood_timeline(trend)
        assert "😐" in result

    def test_formats_none_mood_as_dash(self) -> None:
        trend = [(date(2026, 3, 15), None, None)]
        result = format_mood_timeline(trend)
        assert "ー" in result

    def test_formats_multiple_days(self) -> None:
        trend = [
            (date(2026, 3, 13), 5, "😄"),   # Friday
            (date(2026, 3, 14), None, None),  # Saturday
            (date(2026, 3, 15), 2, None),     # Sunday
        ]
        result = format_mood_timeline(trend)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "😄" in lines[0]
        assert "ー" in lines[1]
        assert "😞" in lines[2]

    def test_empty_trend_returns_empty_string(self) -> None:
        result = format_mood_timeline([])
        assert result == ""

    def test_day_names_in_japanese(self) -> None:
        # 2026-03-16 is Monday
        trend = [(date(2026, 3, 16), None, None)]
        result = format_mood_timeline(trend)
        assert "月(" in result
