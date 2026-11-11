"""Read-only access to the user's Obsidian vault.

The vault layout follows the user's own conventions (see the vault's CLAUDE.md):
- daily notes: ``Notes/Journal/YYYY-MM-DD.md`` (icon ✍)
- book source notes: icon 📘, one folder per book
- learning memos: icon 📝 with ``source: "[[<book>]]"``

This module never writes to the vault.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
_LINK = re.compile(r"\[\[([^\]|#]+)")
_SKIP_DIRS = {".obsidian", ".trash", "Templates"}


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (flat frontmatter dict, body). Only top-level ``key: value`` lines are parsed."""
    m = _FRONTMATTER.match(text)
    if not m:
        return {}, text
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line or line[0] in " \t-#":
            continue
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, text[m.end() :]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class BookActivity:
    """A book and the most recent date the user wrote anything about it."""

    name: str
    last_date: date


class VaultReader:
    """Read-only queries over an Obsidian vault."""

    def __init__(self, vault_dir: Path) -> None:
        self._root = vault_dir

    def _notes(self) -> list[tuple[Path, dict[str, str], str]]:
        notes = []
        for path in self._root.rglob("*.md"):
            if _SKIP_DIRS.intersection(path.relative_to(self._root).parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            fields, body = split_frontmatter(text)
            notes.append((path, fields, body))
        return notes

    def has_daily_note(self, day: date) -> bool:
        """True if today's daily note exists and has something written in the body."""
        path = self._root / "Notes" / "Journal" / f"{day.isoformat()}.md"
        if not path.exists():
            return False
        _, body = split_frontmatter(path.read_text(encoding="utf-8"))
        return bool(body.strip())

    def books(self) -> list[BookActivity]:
        """All 📘 books with their latest activity date, oldest first."""
        notes = self._notes()
        latest: dict[str, date] = {}
        for path, fields, _ in notes:
            if fields.get("icon") == "📘":
                d = _parse_date(fields.get("date"))
                if d:
                    latest[path.stem] = max(latest.get(path.stem, d), d)
        for _, fields, _ in notes:
            m = _LINK.search(fields.get("source", ""))
            d = _parse_date(fields.get("date"))
            if m and d and m.group(1).strip() in latest:
                name = m.group(1).strip()
                latest[name] = max(latest[name], d)
        return sorted((BookActivity(n, d) for n, d in latest.items()), key=lambda b: (b.last_date, b.name))

    def sources(self) -> dict[str, str]:
        """Names of book (📘) and paper (🎓) source notes, mapped to their icon."""
        return {path.stem: fields["icon"] for path, fields, _ in self._notes() if fields.get("icon") in ("📘", "🎓")}

    def weekly_digest(self, iso_year: int, iso_week: int) -> str | None:
        """Body of ``AI/週次 YYYY-Www.md`` written by the vault organizer, or None if not there yet."""
        path = self._root / "AI" / f"週次 {iso_year}-W{iso_week:02d}.md"
        if not path.exists():
            return None
        _, body = split_frontmatter(path.read_text(encoding="utf-8"))
        return body.strip() or None
