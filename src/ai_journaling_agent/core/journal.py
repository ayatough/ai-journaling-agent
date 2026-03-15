"""Journal data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional


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
    emoji: Optional[str] = None
    summary: Optional[str] = None
    achievements: list[str] = field(default_factory=list)
    gratitude: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    photo_paths: list[str] = field(default_factory=list)
