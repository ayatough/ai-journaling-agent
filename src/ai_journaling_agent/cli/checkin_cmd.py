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

    status_p = sub.add_parser("status", help="Check if a check-in is needed now")
    status_p.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")

    record = sub.add_parser("record", help="Record that a check-in was sent")
    record.add_argument("--kind", required=True, choices=["morning", "midday", "evening", "night_summary"])
    record.add_argument("--text", default=None, help="The prompt text that was sent (optional)")
    record.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]
    tracker = CheckInTracker(settings.storage_dir)
    _now = datetime.fromisoformat(args.now).replace(tzinfo=UTC) if args.now else datetime.now(tz=UTC)
    now = _now

    if args.command == "status":
        prompt = tracker.needs_checkin(now)
        if prompt:
            jst_now = now.astimezone(JST)
            hour = jst_now.hour
            if hour < 10:
                kind = "morning"
            elif hour < 13:
                kind = "midday"
            elif hour < 21:
                kind = "evening"
            else:
                kind = "night_summary"
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
