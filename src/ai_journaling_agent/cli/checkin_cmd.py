"""CLI for check-in status and recording."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.config import Settings

JST = ZoneInfo("Asia/Tokyo")


def main(argv: list[str] | None = None) -> None:
    """Entry point for the checkin CLI."""
    parser = argparse.ArgumentParser(description="Check-in management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Check if a check-in is needed now")

    record = sub.add_parser("record", help="Record that a check-in was sent")
    record.add_argument("--kind", required=True, choices=["morning", "evening"])
    record.add_argument("--text", default=None, help="The prompt text that was sent (optional)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]
    tracker = CheckInTracker(settings.storage_dir)
    now = datetime.now(tz=UTC)

    if args.command == "status":
        prompt = tracker.needs_checkin(now)
        if prompt:
            jst_now = now.astimezone(JST)
            kind = "morning" if jst_now.hour < 12 else "evening"
            print(f"{kind} check-in needed")
            print(f"Prompt: {prompt}")
        else:
            print("No check-in needed.")

    elif args.command == "record":
        jst_today = now.astimezone(JST).date()
        tracker.record_checkin(args.kind, jst_today)
        if args.text:
            tracker.record_sent_prompt(args.text, now)
        print(f"Recorded {args.kind} check-in for {jst_today.isoformat()}.")


if __name__ == "__main__":
    main(sys.argv[1:])
