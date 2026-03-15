"""Journal entry persistence layer."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Protocol

from ai_journaling_agent.core.journal import JournalEntry


class JournalRepository(Protocol):
    """Abstract repository for journal entries."""

    def save(self, user_id: str, entry: JournalEntry) -> None: ...

    def list_entries(
        self, user_id: str, *, date: date | None = None
    ) -> list[JournalEntry]: ...

    def get_latest(self, user_id: str) -> JournalEntry | None: ...


class JsonJournalRepository:
    """JSONL-based repository. One file per user: {storage_dir}/{user_id}.jsonl"""

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    def _user_file(self, user_id: str) -> Path:
        return self._storage_dir / f"{user_id}.jsonl"

    def save(self, user_id: str, entry: JournalEntry) -> None:
        """Append a journal entry to the user's JSONL file."""
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        with self._user_file(user_id).open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def list_entries(
        self, user_id: str, *, date: date | None = None
    ) -> list[JournalEntry]:
        """Load all entries for a user, optionally filtered by date."""
        path = self._user_file(user_id)
        if not path.exists():
            return []
        entries: list[JournalEntry] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = JournalEntry.from_dict(json.loads(line))
                if date is not None and entry.timestamp.date() != date:
                    continue
                entries.append(entry)
        return entries

    def get_latest(self, user_id: str) -> JournalEntry | None:
        """Return the most recent entry for a user, or None."""
        path = self._user_file(user_id)
        if not path.exists():
            return None
        last_line = ""
        with path.open(encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if not last_line:
            return None
        return JournalEntry.from_dict(json.loads(last_line))
