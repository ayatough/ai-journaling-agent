"""Mood trend analysis and formatting."""

from __future__ import annotations

from datetime import date, timedelta

from ai_journaling_agent.core.repository import JournalRepository


def get_mood_trend(
    repository: JournalRepository,
    user_id: str,
    days: int = 7,
    reference_date: date | None = None,
) -> list[tuple[date, int | None, str | None]]:
    """Return (date, mood_score, mood_emoji) for each of the last `days` days."""
    end = reference_date or date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = end - timedelta(days=i)
        entries = repository.list_entries(user_id, date=d)
        mood_score: int | None = None
        mood_emoji: str | None = None
        for entry in reversed(entries):
            if entry.mood is not None:
                mood_score = entry.mood
                mood_emoji = entry.mood_emoji
                break
        result.append((d, mood_score, mood_emoji))
    return result


_DAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]
_SCORE_EMOJI = {1: "😔", 2: "😞", 3: "😐", 4: "😊", 5: "😄"}


def format_mood_timeline(trend: list[tuple[date, int | None, str | None]]) -> str:
    """Format mood trend as a text timeline."""
    lines = []
    for d, score, emoji in trend:
        day_name = _DAY_NAMES[d.weekday()]
        date_str = f"{d.month}/{d.day}"
        if emoji:
            mood_display = emoji
        elif score is not None:
            mood_display = _SCORE_EMOJI.get(score, str(score))
        else:
            mood_display = "ー"
        lines.append(f"{day_name}({date_str}): {mood_display}")
    return "\n".join(lines)
