"""CLI for inbox management: list pending messages and mark as read."""

from __future__ import annotations

import argparse
import sys

from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.inbox import JsonInboxRepository


def main(argv: list[str] | None = None) -> None:
    """Entry point for the inbox CLI."""
    parser = argparse.ArgumentParser(description="Inbox management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List pending messages")

    mark = sub.add_parser("mark-read", help="Mark a message as processed")
    mark.add_argument("id", help="Message ID to mark as read")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]
    repo = JsonInboxRepository(settings.storage_dir)

    if args.command == "list":
        messages = repo.list_pending()
        if not messages:
            print("No pending messages.")
            return
        for msg in messages:
            print(f"[{msg.id}] {msg.received_at.isoformat()} user={msg.user_id}")
            print(f"  {msg.text}")
            print()

    elif args.command == "mark-read":
        repo.mark_processed(args.id)
        print(f"Marked {args.id} as processed.")


if __name__ == "__main__":
    main(sys.argv[1:])
