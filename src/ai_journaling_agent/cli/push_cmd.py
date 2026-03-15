"""CLI for sending LINE push messages."""

from __future__ import annotations

import argparse
import sys

from linebot.v3.messaging import (  # type: ignore[import-untyped]
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

from ai_journaling_agent.core.config import Settings


def main(argv: list[str] | None = None) -> None:
    """Entry point for the push CLI."""
    parser = argparse.ArgumentParser(description="Send LINE push message")
    parser.add_argument("--user", help="LINE user ID (defaults to OWNER_USER_ID)")
    parser.add_argument("--text", required=True, help="Message text to send")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]

    user_id = args.user or settings.owner_user_id
    if not user_id:
        print("Error: --user required or set OWNER_USER_ID in .env", file=sys.stderr)
        sys.exit(1)

    configuration = Configuration(access_token=settings.line_channel_access_token)
    with ApiClient(configuration) as api_client:
        line_api = MessagingApi(api_client)
        line_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=args.text)],
            )
        )

    print(f"Sent to {user_id}: {args.text[:50]}...")


if __name__ == "__main__":
    main(sys.argv[1:])
