"""Tests for journal-today CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.repository import JsonJournalRepository

JST = ZoneInfo("Asia/Tokyo")


@pytest.fixture()
def repo_with_entries(tmp_path: Path) -> tuple[Path, str]:
    """Create a repository with today's and yesterday's entries."""
    storage_dir = tmp_path / "data"
    repo = JsonJournalRepository(storage_dir)
    user_id = "U_TEST"

    now_utc = datetime.now(tz=UTC)
    today_jst = now_utc.astimezone(JST).date()

    # Today's entries (2 entries)
    entry_today_1 = JournalEntry(
        timestamp=datetime(today_jst.year, today_jst.month, today_jst.day, 0, 30, tzinfo=JST).astimezone(UTC),
        level=EntryLevel.EMOJI,
        emoji="😊",
    )
    entry_today_2 = JournalEntry(
        timestamp=datetime(today_jst.year, today_jst.month, today_jst.day, 12, 0, tzinfo=JST).astimezone(UTC),
        level=EntryLevel.SUMMARY,
        summary="ランチに行った",
    )
    repo.save(user_id, entry_today_1)
    repo.save(user_id, entry_today_2)

    # Yesterday's entry (should not appear)
    yesterday = today_jst.toordinal() - 1
    from datetime import date as date_cls

    yesterday_date = date_cls.fromordinal(yesterday)
    entry_yesterday = JournalEntry(
        timestamp=datetime(yesterday_date.year, yesterday_date.month, yesterday_date.day, 20, 0, tzinfo=JST)
        .astimezone(UTC),
        level=EntryLevel.EMOJI,
        emoji="😴",
    )
    repo.save(user_id, entry_yesterday)

    return storage_dir, user_id


class TestJournalTodayFiltering:
    """journal-today shows only today's entries in JST."""

    def test_filters_to_today_jst(self, repo_with_entries: tuple[Path, str]) -> None:
        storage_dir, user_id = repo_with_entries
        repo = JsonJournalRepository(storage_dir)

        now_utc = datetime.now(tz=UTC)
        today_jst = now_utc.astimezone(JST).date()

        entries = repo.list_entries(user_id)
        todays = [e for e in entries if e.timestamp.astimezone(JST).date() == today_jst]

        assert len(todays) == 2
        assert todays[0].emoji == "😊"
        assert todays[1].summary == "ランチに行った"

    def test_empty_when_no_entries(self, tmp_path: Path) -> None:
        storage_dir = tmp_path / "data"
        repo = JsonJournalRepository(storage_dir)

        now_utc = datetime.now(tz=UTC)
        today_jst = now_utc.astimezone(JST).date()

        entries = repo.list_entries("U_NOBODY")
        todays = [e for e in entries if e.timestamp.astimezone(JST).date() == today_jst]

        assert len(todays) == 0

    def test_filters_by_specific_date(self, repo_with_entries: tuple[Path, str]) -> None:
        """--date option filters to a specific date."""
        storage_dir, user_id = repo_with_entries
        repo = JsonJournalRepository(storage_dir)

        now_utc = datetime.now(tz=UTC)
        today_jst = now_utc.astimezone(JST).date()
        from datetime import date as date_cls

        yesterday_date = date_cls.fromordinal(today_jst.toordinal() - 1)

        entries = repo.list_entries(user_id)
        yesterdays = [e for e in entries if e.timestamp.astimezone(JST).date() == yesterday_date]

        assert len(yesterdays) == 1
        assert yesterdays[0].emoji == "😴"
