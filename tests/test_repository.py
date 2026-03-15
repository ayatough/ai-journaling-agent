"""Tests for JsonJournalRepository."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.repository import JsonJournalRepository


def _make_entry(
    ts: datetime,
    level: EntryLevel = EntryLevel.EMOJI,
    emoji: str | None = "😊",
) -> JournalEntry:
    return JournalEntry(timestamp=ts, level=level, emoji=emoji)


class TestSaveAndLoad:
    """save -> list_entries round trip."""

    def test_save_and_list(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        entry = _make_entry(datetime(2026, 3, 15, 9, 0, 0))
        repo.save("user1", entry)
        entries = repo.list_entries("user1")
        assert len(entries) == 1
        assert entries[0] == entry

    def test_multiple_entries(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        e1 = _make_entry(datetime(2026, 3, 15, 9, 0, 0), emoji="☀️")
        e2 = _make_entry(datetime(2026, 3, 15, 21, 0, 0), emoji="🌙")
        repo.save("user1", e1)
        repo.save("user1", e2)
        entries = repo.list_entries("user1")
        assert len(entries) == 2
        assert entries[0] == e1
        assert entries[1] == e2

    def test_separate_users(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        e1 = _make_entry(datetime(2026, 3, 15, 9, 0, 0))
        e2 = _make_entry(datetime(2026, 3, 15, 10, 0, 0))
        repo.save("alice", e1)
        repo.save("bob", e2)
        assert len(repo.list_entries("alice")) == 1
        assert len(repo.list_entries("bob")) == 1


class TestDateFilter:
    """list_entries with date filter."""

    def test_filter_by_date(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        e_mar15 = _make_entry(datetime(2026, 3, 15, 9, 0, 0))
        e_mar16 = _make_entry(datetime(2026, 3, 16, 9, 0, 0))
        repo.save("user1", e_mar15)
        repo.save("user1", e_mar16)
        result = repo.list_entries("user1", date=date(2026, 3, 15))
        assert len(result) == 1
        assert result[0] == e_mar15

    def test_filter_no_match(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        repo.save("user1", _make_entry(datetime(2026, 3, 15, 9, 0, 0)))
        result = repo.list_entries("user1", date=date(2026, 1, 1))
        assert result == []


class TestGetLatest:
    """get_latest returns the most recent entry."""

    def test_returns_latest(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        repo.save("user1", _make_entry(datetime(2026, 3, 15, 9, 0, 0), emoji="☀️"))
        repo.save("user1", _make_entry(datetime(2026, 3, 15, 21, 0, 0), emoji="🌙"))
        latest = repo.get_latest("user1")
        assert latest is not None
        assert latest.emoji == "🌙"

    def test_unknown_user_returns_none(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        assert repo.get_latest("unknown") is None


class TestUnknownUser:
    """Operations on non-existent users."""

    def test_list_entries_empty(self, tmp_path: Path) -> None:
        repo = JsonJournalRepository(tmp_path)
        assert repo.list_entries("nonexistent") == []
