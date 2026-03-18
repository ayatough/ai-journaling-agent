"""Tests for JournalEntry serialization."""

from __future__ import annotations

from datetime import datetime

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry


class TestToDict:
    """to_dict produces expected output."""

    def test_full_entry(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.STRUCTURED,
            emoji="😊",
            summary="良い一日",
            achievements=["朝ラン5km"],
            gratitude=["天気が良かった"],
            learnings=["新しいAPI"],
            photo_paths=["/tmp/photo.jpg"],
        )
        d = entry.to_dict()
        assert d["timestamp"] == "2026-03-15T09:00:00"
        assert d["level"] == 2
        assert d["emoji"] == "😊"
        assert d["summary"] == "良い一日"
        assert d["achievements"] == ["朝ラン5km"]

    def test_emoji_only_entry(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 21, 0, 0),
            level=EntryLevel.EMOJI,
            emoji="😴",
        )
        d = entry.to_dict()
        assert d["level"] == 0
        assert d["summary"] is None
        assert d["achievements"] == []


class TestRoundTrip:
    """to_dict -> from_dict preserves all fields."""

    def test_structured_round_trip(self) -> None:
        original = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 30, 0),
            level=EntryLevel.STRUCTURED,
            emoji="🎉",
            summary="素晴らしい日",
            achievements=["プレゼン成功", "コードレビュー"],
            gratitude=["チームのサポート"],
            learnings=["設計パターン"],
            photo_paths=["/tmp/a.jpg", "/tmp/b.jpg"],
        )
        restored = JournalEntry.from_dict(original.to_dict())
        assert restored == original

    def test_emoji_round_trip(self) -> None:
        original = JournalEntry(
            timestamp=datetime(2026, 3, 15, 7, 0, 0),
            level=EntryLevel.EMOJI,
            emoji="☀️",
        )
        restored = JournalEntry.from_dict(original.to_dict())
        assert restored == original

    def test_summary_round_trip(self) -> None:
        original = JournalEntry(
            timestamp=datetime(2026, 3, 15, 12, 0, 0),
            level=EntryLevel.SUMMARY,
            summary="まあまあの日",
        )
        restored = JournalEntry.from_dict(original.to_dict())
        assert restored == original

    def test_mood_round_trip(self) -> None:
        original = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.EMOJI,
            emoji="😊",
            mood=5,
            mood_emoji="😊",
        )
        restored = JournalEntry.from_dict(original.to_dict())
        assert restored == original
        assert restored.mood == 5
        assert restored.mood_emoji == "😊"

    def test_mood_none_round_trip(self) -> None:
        """Emoji without a known mood score preserves None."""
        original = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.EMOJI,
            emoji="☕",
            mood=None,
            mood_emoji="☕",
        )
        restored = JournalEntry.from_dict(original.to_dict())
        assert restored == original
        assert restored.mood is None
        assert restored.mood_emoji == "☕"


class TestBackwardCompat:
    """Existing data without mood fields loads correctly."""

    def test_legacy_entry_without_mood(self) -> None:
        legacy_data = {
            "timestamp": "2026-03-15T09:00:00",
            "level": 0,
            "emoji": "😊",
            "summary": None,
            "achievements": [],
            "gratitude": [],
            "learnings": [],
            "photo_paths": [],
        }
        entry = JournalEntry.from_dict(legacy_data)
        assert entry.mood is None
        assert entry.mood_emoji is None
        assert entry.emoji == "😊"
