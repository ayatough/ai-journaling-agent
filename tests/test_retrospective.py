"""Tests for retrospective summary generation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry


def _make_entry(d: date, summary: str = "今日も頑張った") -> JournalEntry:
    return JournalEntry(
        timestamp=datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC),
        level=EntryLevel.SUMMARY,
        summary=summary,
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


class TestGenerateWeeklySummary:
    """generate_weekly_summary() generates or skips based on entries."""

    async def test_no_entries_returns_no_record_message(self) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.retrospective import generate_weekly_summary

        repo = _StubRepository({})
        mock_responder = AsyncMock(spec=AiResponder)

        result = await generate_weekly_summary("U1234", date(2026, 3, 10), repo, mock_responder)

        assert result == "この週の記録はありませんでした。"
        mock_responder.generate_response.assert_not_called()

    async def test_with_entries_calls_ai_responder(self) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.retrospective import generate_weekly_summary

        week_start = date(2026, 3, 10)
        entry_date = date(2026, 3, 12)
        repo = _StubRepository({entry_date: [_make_entry(entry_date, "プロジェクト完了")]})

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = "今週は素晴らしい1週間でした。"

        result = await generate_weekly_summary("U1234", week_start, repo, mock_responder)

        assert result == "今週は素晴らしい1週間でした。"
        mock_responder.generate_response.assert_called_once()
        call_args = mock_responder.generate_response.call_args
        # The prompt should contain the entry text
        prompt_arg = call_args[0][1]  # second positional arg is user_text/prompt
        assert "プロジェクト完了" in prompt_arg

    async def test_with_entries_and_achievements(self) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.retrospective import generate_weekly_summary

        week_start = date(2026, 3, 10)
        entry_date = date(2026, 3, 11)
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 11, 12, 0, 0, tzinfo=UTC),
            level=EntryLevel.STRUCTURED,
            summary="今日の記録",
            achievements=["タスク完了"],
            gratitude=["チームに感謝"],
            learnings=["新しい手法を学んだ"],
        )
        repo = _StubRepository({entry_date: [entry]})

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = "振り返りサマリー"

        result = await generate_weekly_summary("U1234", week_start, repo, mock_responder)

        assert result == "振り返りサマリー"
        call_args = mock_responder.generate_response.call_args
        prompt_arg = call_args[0][1]
        assert "タスク完了" in prompt_arg
        assert "チームに感謝" in prompt_arg
        assert "新しい手法を学んだ" in prompt_arg


class TestGenerateMonthlySummary:
    """generate_monthly_summary() generates or skips based on entries."""

    async def test_no_entries_returns_no_record_message(self) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.retrospective import generate_monthly_summary

        repo = _StubRepository({})
        mock_responder = AsyncMock(spec=AiResponder)

        result = await generate_monthly_summary("U1234", date(2026, 2, 1), repo, mock_responder)

        assert result == "この月の記録はありませんでした。"
        mock_responder.generate_response.assert_not_called()

    async def test_december_month_end_calculated_correctly(self) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.retrospective import generate_monthly_summary

        # December: month_end should be Dec 31
        entry_date = date(2026, 12, 25)
        repo = _StubRepository({entry_date: [_make_entry(entry_date, "クリスマス")]})

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = "12月のふりかえり"

        result = await generate_monthly_summary("U1234", date(2026, 12, 1), repo, mock_responder)

        assert result == "12月のふりかえり"
        call_args = mock_responder.generate_response.call_args
        prompt_arg = call_args[0][1]
        assert "クリスマス" in prompt_arg
