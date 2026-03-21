"""CLI for viewing mood trend report."""

from __future__ import annotations

import argparse
import sys

from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.mood import format_mood_timeline, get_mood_trend
from ai_journaling_agent.core.repository import JsonJournalRepository


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Show mood trend report")
    parser.add_argument("--user", help="LINE user ID (defaults to OWNER_USER_ID)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to show (default: 7)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]

    user_id = args.user or settings.owner_user_id
    if not user_id:
        print("Error: --user required or set OWNER_USER_ID in .env", file=sys.stderr)
        sys.exit(1)

    repo = JsonJournalRepository(settings.storage_dir)
    trend = get_mood_trend(repo, user_id, days=args.days)
    print(format_mood_timeline(trend))


if __name__ == "__main__":
    main(sys.argv[1:])
