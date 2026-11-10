"""Light nudges appended to check-ins, based on the user's Obsidian vault.

Policy (agreed with the user):
- Diary: in the evening/night check-in, if today's daily note is still empty. Once per day.
- Books: on Saturday/Sunday mornings, gently suggest the book untouched for the longest.
  A book is not suggested again within ``BOOK_COOLDOWN_DAYS`` days, and only books idle
  for at least ``BOOK_IDLE_DAYS`` days are suggested.
- Papers are never nudged here; they come up only when the user talks about them.
"""

from __future__ import annotations

from datetime import date

from ai_journaling_agent.core.vault import VaultReader

BOOK_IDLE_DAYS = 7
BOOK_COOLDOWN_DAYS = 14

DIARY_NUDGE = "今日はまだ Obsidian の日記を書いていませんね。一言だけでも残しておきませんか？"


def book_nudge_text(name: str, last: date) -> str:
    return f"週末ですね。気が向いたら『{name}』の続きを少しどうですか？（最後のメモは {last.month}/{last.day}）"


def choose_nudge(
    kind: str,
    today: date,
    reader: VaultReader,
    diary_nudged_on: str | None,
    book_nudged_on: dict[str, str],
) -> tuple[str, str] | None:
    """Pick at most one nudge for this check-in.

    Returns ``(nudge_key, text)`` where nudge_key is ``"diary"`` or ``"book:<name>"``, or None.
    """
    if kind in ("evening", "night_summary"):
        if diary_nudged_on != today.isoformat() and not reader.has_daily_note(today):
            return "diary", DIARY_NUDGE
        return None

    if kind == "morning" and today.weekday() >= 5:
        for book in reader.books():
            if (today - book.last_date).days < BOOK_IDLE_DAYS:
                continue
            last_nudged = book_nudged_on.get(book.name)
            if last_nudged and (today - date.fromisoformat(last_nudged)).days < BOOK_COOLDOWN_DAYS:
                continue
            return f"book:{book.name}", book_nudge_text(book.name, book.last_date)
    return None
