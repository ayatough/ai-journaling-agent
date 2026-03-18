"""Journal data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any


class EntryLevel(IntEnum):
    """Engagement level for journal entries."""

    EMOJI = 0  # 絵文字1つ + 写真（任意）
    SUMMARY = 1  # 一言サマリー
    STRUCTURED = 2  # 構造化質問（できたこと・感謝・学び）


@dataclass
class JournalEntry:
    """A single journal entry."""

    timestamp: datetime
    level: EntryLevel
    emoji: str | None = None
    summary: str | None = None
    achievements: list[str] = field(default_factory=list)
    gratitude: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    photo_paths: list[str] = field(default_factory=list)
    mood: int | None = None  # 1-5 scale (1=つらい, 5=最高)
    mood_emoji: str | None = None  # the emoji representing the user's mood

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": int(self.level),
            "emoji": self.emoji,
            "summary": self.summary,
            "achievements": self.achievements,
            "gratitude": self.gratitude,
            "learnings": self.learnings,
            "photo_paths": self.photo_paths,
            "mood": self.mood,
            "mood_emoji": self.mood_emoji,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JournalEntry:
        """Deserialize from a dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            level=EntryLevel(data["level"]),
            emoji=data.get("emoji"),
            summary=data.get("summary"),
            achievements=list(data.get("achievements") or []),
            gratitude=list(data.get("gratitude") or []),
            learnings=list(data.get("learnings") or []),
            photo_paths=list(data.get("photo_paths") or []),
            mood=data.get("mood"),
            mood_emoji=data.get("mood_emoji"),
        )
