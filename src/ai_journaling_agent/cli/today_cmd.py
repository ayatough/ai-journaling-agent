"""CLI for viewing journal entries by date (JST). Defaults to today."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.journal import EntryLevel
from ai_journaling_agent.core.repository import JsonJournalRepository

JST = ZoneInfo("Asia/Tokyo")


def main(argv: list[str] | None = None) -> None:
    """Entry point for the journal-today CLI."""
    parser = argparse.ArgumentParser(description="View journal entries by date (JST, defaults to today)")
    parser.add_argument("--user", help="LINE user ID (defaults to OWNER_USER_ID)")
    parser.add_argument("--date", help="Date to view in YYYY-MM-DD format (defaults to today JST)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]

    user_id = args.user or settings.owner_user_id
    if not user_id:
        print("Error: --user required or set OWNER_USER_ID in .env", file=sys.stderr)
        sys.exit(1)

    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Error: invalid date format '{args.date}' (expected YYYY-MM-DD)", file=sys.stderr)
            sys.exit(1)
    else:
        target_date = datetime.now(tz=UTC).astimezone(JST).date()

    repo = JsonJournalRepository(settings.storage_dir)
    entries = repo.list_entries(user_id)
    filtered = [e for e in entries if e.timestamp.astimezone(JST).date() == target_date]

    if not filtered:
        print(f"{target_date.isoformat()} の記録はありません。")
        return

    print(f"=== {target_date.isoformat()} の記録 ({len(filtered)}件) ===\n")
    for entry in filtered:
        ts = entry.timestamp.astimezone(JST).strftime("%H:%M")
        level_name = EntryLevel(entry.level).name

        print(f"[{ts}] {level_name}")
        if entry.emoji:
            print(f"  {entry.emoji}")
        if entry.summary:
            print(f"  {entry.summary}")
        if entry.achievements:
            for a in entry.achievements:
                print(f"  ✓ {a}")
        if entry.gratitude:
            for g in entry.gratitude:
                print(f"  ♡ {g}")
        if entry.learnings:
            for l in entry.learnings:  # noqa: E741
                print(f"  💡 {l}")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
