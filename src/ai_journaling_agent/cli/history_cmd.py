"""CLI for viewing recent journal entries."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.journal import EntryLevel
from ai_journaling_agent.core.repository import JsonJournalRepository


def main(argv: list[str] | None = None) -> None:
    """Entry point for the history CLI."""
    parser = argparse.ArgumentParser(description="View recent journal entries")
    parser.add_argument("--user", help="LINE user ID (defaults to OWNER_USER_ID)")
    parser.add_argument("--days", type=int, default=3, help="Number of days to show (default: 3)")
    parser.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]

    user_id = args.user or settings.owner_user_id
    if not user_id:
        print("Error: --user required or set OWNER_USER_ID in .env", file=sys.stderr)
        sys.exit(1)

    repo = JsonJournalRepository(settings.storage_dir)
    _now = datetime.fromisoformat(args.now).replace(tzinfo=UTC) if args.now else datetime.now(tz=UTC)
    cutoff = _now - timedelta(days=args.days)

    entries = repo.list_entries(user_id)
    recent = [e for e in entries if e.timestamp >= cutoff]

    if not recent:
        print(f"No entries in the last {args.days} days.")
        return

    for entry in recent:
        ts = entry.timestamp.isoformat()
        level_name = EntryLevel(entry.level).name

        print(f"--- {ts} [{level_name}] ---")
        if entry.emoji:
            print(f"  Emoji: {entry.emoji}")
        if entry.summary:
            print(f"  Summary: {entry.summary}")
        if entry.achievements:
            for a in entry.achievements:
                print(f"  Achievement: {a}")
        if entry.gratitude:
            for g in entry.gratitude:
                print(f"  Gratitude: {g}")
        if entry.learnings:
            for l in entry.learnings:  # noqa: E741
                print(f"  Learning: {l}")
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
