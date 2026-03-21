"""CLI for generating retrospective summaries."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, date, datetime, timedelta

from ai_journaling_agent.core.ai_responder import AiResponder
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.repository import JsonJournalRepository
from ai_journaling_agent.core.retrospective import generate_monthly_summary, generate_weekly_summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate retrospective summary")
    parser.add_argument("--user", help="LINE user ID (defaults to OWNER_USER_ID)")
    parser.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--weekly", action="store_true", help="Generate weekly summary (last 7 days)")
    group.add_argument("--monthly", action="store_true", help="Generate monthly summary (last 30 days)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]

    user_id = args.user or settings.owner_user_id
    if not user_id:
        print("Error: --user required or set OWNER_USER_ID in .env", file=sys.stderr)
        sys.exit(1)

    repo = JsonJournalRepository(settings.storage_dir)
    responder = AiResponder(storage_dir=settings.storage_dir)
    _now = datetime.fromisoformat(args.now).replace(tzinfo=UTC) if args.now else datetime.now(tz=UTC)
    today = _now.date()

    if args.monthly:
        month_start = date(today.year, today.month, 1) - timedelta(days=1)
        month_start = date(month_start.year, month_start.month, 1)
        summary = asyncio.run(generate_monthly_summary(user_id, month_start, repo, responder))
    else:
        # Default: weekly
        week_start = today - timedelta(days=6)
        summary = asyncio.run(generate_weekly_summary(user_id, week_start, repo, responder))

    print(summary)


if __name__ == "__main__":
    main(sys.argv[1:])
