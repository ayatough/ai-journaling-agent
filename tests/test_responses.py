"""Tests for response generation."""

from __future__ import annotations

from datetime import datetime

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry
from ai_journaling_agent.core.responses import generate_response


class TestGenerateResponse:
    """generate_response produces non-empty, level-appropriate messages."""

    def test_emoji_level_includes_emoji(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.EMOJI,
            emoji="😊",
        )
        result = generate_response(entry)
        assert "😊" in result
        assert len(result) > 0

    def test_emoji_level_without_emoji_field(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.EMOJI,
        )
        result = generate_response(entry)
        assert len(result) > 0

    def test_summary_level_includes_text(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.SUMMARY,
            summary="今日は良い天気だった",
        )
        result = generate_response(entry)
        assert "今日は良い天気だった" in result
        assert len(result) > 0

    def test_summary_long_text_truncated(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.SUMMARY,
            summary="今日はとても素晴らしい一日でした。色々なことがありました。",
        )
        result = generate_response(entry)
        assert "…" in result
        assert len(result) > 0

    def test_structured_level_includes_counts(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.STRUCTURED,
            achievements=["朝ラン5km", "コードレビュー"],
            gratitude=["チームのサポート"],
            learnings=["新しいAPI"],
        )
        result = generate_response(entry)
        assert "2件" in result  # achievements
        assert "1件" in result  # gratitude or learnings
        assert len(result) > 0

    def test_structured_empty_lists(self) -> None:
        entry = JournalEntry(
            timestamp=datetime(2026, 3, 15, 9, 0, 0),
            level=EntryLevel.STRUCTURED,
        )
        result = generate_response(entry)
        assert len(result) > 0
