"""Message classification for journal entries (rule-based MVP)."""

from __future__ import annotations

import re
import unicodedata

from ai_journaling_agent.core.journal import EntryLevel

_STRUCTURED_MARKERS = re.compile(
    r"(できたこと|感謝|学び|ありがとう|嬉しかった|成長)"
)

_SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?P<key>できたこと|感謝|ありがとう|学び|成長)\s*[:：]\s*(?P<value>[^\n]+)",
    re.MULTILINE,
)


def _is_emoji_only(text: str) -> bool:
    """Return True if *text* consists entirely of emoji / variation selectors."""
    for ch in text:
        cat = unicodedata.category(ch)
        # So = Symbol, Other (emoji); Sk = Symbol, Modifier
        # Cf = Format (ZWJ); Mn = Mark, Nonspacing (variation selectors)
        if cat not in ("So", "Sk", "Cf", "Mn"):
            return False
    return len(text) > 0


def classify_message(text: str) -> EntryLevel:
    """Classify a user message into an EntryLevel.

    Rules (evaluated in order):
    1. Emoji-only text → EMOJI
    2. Contains structured markers (できたこと, 感謝, 学び, …) → STRUCTURED
    3. Everything else → SUMMARY
    """
    stripped = text.strip()
    if _is_emoji_only(stripped):
        return EntryLevel.EMOJI
    if _STRUCTURED_MARKERS.search(stripped):
        return EntryLevel.STRUCTURED
    return EntryLevel.SUMMARY


_MOOD_SCORES: dict[str, int] = {}
for _score, _emojis in [
    (5, "😊🎉🥳✨🌟💪🎊😆🤩"),
    (4, "😄☀️👍🙂😌🌈😀"),
    (3, "😐🤔💭🙃😶"),
    (2, "😢😞😔😟😩😫"),
    (1, "😭😤😡🤮😰😱"),
]:
    for _ch in _emojis:
        cat = unicodedata.category(_ch)
        if cat in ("So", "Sk"):
            _MOOD_SCORES[_ch] = _score


def _first_emoji(text: str) -> str | None:
    """Extract the first emoji character from text."""
    for ch in text:
        if unicodedata.category(ch) in ("So", "Sk"):
            return ch
    return None


def emoji_to_mood(text: str) -> int | None:
    """Estimate a mood score (1-5) from the first emoji in text.

    Returns None for emojis not in the known mood dictionary (e.g. ☕, 🌻).
    """
    ch = _first_emoji(text)
    if ch is None:
        return None
    return _MOOD_SCORES.get(ch)


def parse_structured_entry(text: str) -> dict[str, list[str]]:
    """Extract achievements / gratitude / learnings from structured text.

    Recognises section headers like ``できたこと: 朝ラン5km`` and maps them
    to the corresponding journal fields.
    """
    result: dict[str, list[str]] = {
        "achievements": [],
        "gratitude": [],
        "learnings": [],
    }

    key_map: dict[str, str] = {
        "できたこと": "achievements",
        "感謝": "gratitude",
        "ありがとう": "gratitude",
        "学び": "learnings",
        "成長": "learnings",
    }

    for match in _SECTION_PATTERN.finditer(text):
        key = match.group("key")
        value = match.group("value").strip()
        field = key_map[key]
        if value:
            result[field].append(value)

    return result
