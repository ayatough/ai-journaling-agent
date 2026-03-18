"""Tests for message classification."""

from __future__ import annotations

import pytest

from ai_journaling_agent.core.classifier import classify_message, emoji_to_mood, parse_structured_entry
from ai_journaling_agent.core.journal import EntryLevel


class TestClassifyMessage:
    """classify_message maps text to the correct EntryLevel."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("😊", EntryLevel.EMOJI),
            ("☀️", EntryLevel.EMOJI),
            ("🎉🎊", EntryLevel.EMOJI),
            ("😴", EntryLevel.EMOJI),
            ("今日は良い天気だった", EntryLevel.SUMMARY),
            ("疲れた", EntryLevel.SUMMARY),
            ("まあまあ", EntryLevel.SUMMARY),
            ("できたこと: 朝ラン5km", EntryLevel.STRUCTURED),
            ("感謝: チームのサポート", EntryLevel.STRUCTURED),
            ("学び: 新しいAPI", EntryLevel.STRUCTURED),
            ("今日ありがとうございました", EntryLevel.STRUCTURED),
            ("成長: プレゼン力", EntryLevel.STRUCTURED),
        ],
        ids=[
            "single_emoji",
            "emoji_with_variation",
            "multiple_emoji",
            "sleepy_emoji",
            "short_text",
            "very_short_text",
            "neutral_text",
            "achievement_marker",
            "gratitude_marker",
            "learning_marker",
            "arigatou_marker",
            "growth_marker",
        ],
    )
    def test_classification(self, text: str, expected: EntryLevel) -> None:
        assert classify_message(text) == expected

    def test_empty_after_strip_is_summary(self) -> None:
        # Edge case: whitespace-only → SUMMARY (not emoji)
        assert classify_message("  ") == EntryLevel.SUMMARY


class TestParseStructuredEntry:
    """parse_structured_entry extracts sections from structured text."""

    def test_all_sections(self) -> None:
        text = "できたこと: 朝ラン5km\n感謝: チームのサポート\n学び: 新しいAPI"
        result = parse_structured_entry(text)
        assert result["achievements"] == ["朝ラン5km"]
        assert result["gratitude"] == ["チームのサポート"]
        assert result["learnings"] == ["新しいAPI"]

    def test_partial_sections(self) -> None:
        text = "できたこと: プレゼン成功"
        result = parse_structured_entry(text)
        assert result["achievements"] == ["プレゼン成功"]
        assert result["gratitude"] == []
        assert result["learnings"] == []

    def test_multiple_same_section(self) -> None:
        text = "できたこと: 朝ラン\nできたこと: コードレビュー"
        result = parse_structured_entry(text)
        assert result["achievements"] == ["朝ラン", "コードレビュー"]

    def test_arigatou_maps_to_gratitude(self) -> None:
        text = "ありがとう: 先輩の助け"
        result = parse_structured_entry(text)
        assert result["gratitude"] == ["先輩の助け"]

    def test_growth_maps_to_learnings(self) -> None:
        text = "成長: プレゼン力が上がった"
        result = parse_structured_entry(text)
        assert result["learnings"] == ["プレゼン力が上がった"]

    def test_no_markers_returns_empty(self) -> None:
        result = parse_structured_entry("今日は良い日だった")
        assert result == {"achievements": [], "gratitude": [], "learnings": []}

    def test_fullwidth_colon(self) -> None:
        text = "できたこと：朝ラン5km"
        result = parse_structured_entry(text)
        assert result["achievements"] == ["朝ラン5km"]


class TestEmojiToMood:
    """emoji_to_mood estimates mood score from emoji."""

    @pytest.mark.parametrize(
        ("emoji", "expected"),
        [
            ("😊", 5),
            ("🎉", 5),
            ("😄", 4),
            ("👍", 4),
            ("😐", 3),
            ("🤔", 3),
            ("😢", 2),
            ("😞", 2),
            ("😭", 1),
            ("😡", 1),
        ],
        ids=[
            "happy_5", "party_5",
            "smile_4", "thumbsup_4",
            "neutral_3", "thinking_3",
            "cry_2", "disappointed_2",
            "sob_1", "angry_1",
        ],
    )
    def test_known_emoji(self, emoji: str, expected: int) -> None:
        assert emoji_to_mood(emoji) == expected

    def test_unknown_emoji_returns_none(self) -> None:
        assert emoji_to_mood("☕") is None
        assert emoji_to_mood("🌻") is None
        assert emoji_to_mood("🍕") is None

    def test_multiple_emoji_uses_first(self) -> None:
        assert emoji_to_mood("😭😊") == 1
        assert emoji_to_mood("😊😭") == 5

    def test_no_emoji_returns_none(self) -> None:
        assert emoji_to_mood("hello") is None
        assert emoji_to_mood("") is None
