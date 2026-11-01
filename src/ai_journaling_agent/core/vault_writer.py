"""Narrow, append-only writes to the user's Obsidian vault.

What the journal agent may write (agreed with the user; see the vault's CLAUDE.md):
- a new memo in ``Inbox/`` whose body is the user's own words, verbatim
- empty ``condition`` / ``mood`` / ``good`` fields of today's daily note (frontmatter only)
- an append-only checklist line in ``Claude/LINE引き継ぎ.md`` for the Cowork organizer

It never overwrites, renames, moves or deletes anything, and never touches a note body.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

RELAY_PATH = Path("Claude") / "LINE引き継ぎ.md"
RELAY_HEADER = """---
icon: 📌
tags: [meta, agent]
---

# LINE 引き継ぎ

journal agent（LINE）が追記し、Cowork が処理してチェックを付ける。
未チェックの項目が処理待ち。確認が必要なものは処理せず、コメントを添えて残す。

"""
DAILY_FIELDS = ("condition", "mood", "good")
_BAD_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]\r\n\t]')


class VaultWriteError(ValueError):
    """Raised when a requested write is outside what the agent may do."""


def sanitize_title(title: str) -> str:
    cleaned = _BAD_CHARS.sub(" ", title).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)[:60].strip()
    if not cleaned:
        raise VaultWriteError("タイトルが空です")
    return cleaned


def _yaml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class VaultWriter:
    """Append-only writer for an Obsidian vault."""

    def __init__(self, vault_dir: Path) -> None:
        self._root = vault_dir

    # --- memos -------------------------------------------------------------
    def create_memo(self, title: str, body: str, now: datetime, source: str | None = None, idea: bool = False) -> Path:
        """Create ``Inbox/<title>.md``. Never overwrites: adds `` (2)`` etc. on collision."""
        name = sanitize_title(title)
        if not body.strip():
            raise VaultWriteError("本文が空です")
        inbox = self._root / "Inbox"
        inbox.mkdir(exist_ok=True)
        path = inbox / f"{name}.md"
        n = 2
        while path.exists():
            path = inbox / f"{name} ({n}).md"
            n += 1
        lines = ["---", "icon: 💡" if idea else "icon: 📝", f"date: {now:%Y-%m-%d}", f"time: {now:%H:%M}"]
        lines.append("tags: [idea]" if idea else "tags: []")
        if not idea:
            lines.append(f'source: "[[{source}]]"' if source else 'source: "[[]]"')
        lines.append("---")
        content = "\n".join(lines) + "\n" + body.strip("\n") + "\n"
        with path.open("x", encoding="utf-8", newline="\n") as f:  # "x": fail if it appeared meanwhile
            f.write(content)
        return path

    # --- daily note ---------------------------------------------------------
    def fill_daily_fields(self, now: datetime, values: dict[str, str]) -> dict[str, str]:
        """Fill empty daily-note frontmatter fields. Returns the fields actually written."""
        values = {k: v.strip() for k, v in values.items() if k in DAILY_FIELDS and v and v.strip()}
        if not values:
            return {}
        path = self._root / "Notes" / "Journal" / f"{now:%Y-%m-%d}.md"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            template = self._root / "Templates" / "Daily Note.md"
            if template.exists():
                text = template.read_text(encoding="utf-8").replace("{{date:YYYY-MM-DD}}", f"{now:%Y-%m-%d}")
            else:
                text = f'---\nicon: ✍\ndate: "{now:%Y-%m-%d}"\ncondition: \nmood: \ngood: \nphoto: \ntags: []\n---\n'
            with path.open("x", encoding="utf-8", newline="\n") as f:
                f.write(text)

        text = path.read_text(encoding="utf-8")
        m = re.match(r"\A---\r?\n(.*?\r?\n)---", text, re.S)
        if not m:
            return {}
        front = m.group(1)
        written: dict[str, str] = {}
        for key, value in values.items():
            pattern = re.compile(rf"^{key}:[ \t]*(\r?)$", re.M)
            if pattern.search(front):  # key exists and is empty
                rendered = value if value.isdigit() else _yaml_str(value)
                front = pattern.sub(lambda mm, r=rendered, k=key: f"{k}: {r}{mm.group(1)}", front, count=1)
                written[key] = value
        if written:
            new_text = text[: m.start(1)] + front + text[m.end(1) :]
            with path.open("w", encoding="utf-8", newline="") as f:
                f.write(new_text)
        return written

    # --- relay memo ---------------------------------------------------------
    def append_relay(self, now: datetime, line: str) -> None:
        path = self._root / RELAY_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = f"- [ ] {now:%Y-%m-%d %H:%M} {line.strip()}\n"
        if not path.exists():
            with path.open("x", encoding="utf-8", newline="\n") as f:
                f.write(RELAY_HEADER)
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(entry)
