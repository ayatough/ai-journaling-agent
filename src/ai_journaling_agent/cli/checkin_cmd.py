"""CLI for check-in status, recording and sending."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.nudge import choose_nudge
from ai_journaling_agent.core.vault import VaultReader

JST = ZoneInfo("Asia/Tokyo")


def plan_checkin(
    tracker: CheckInTracker, settings: Settings, now: datetime
) -> tuple[str, str, str | None, str | None] | None:
    """Return ``(kind, template_prompt, nudge_key, nudge_text)`` for the check-in due now, or None."""
    due = tracker.next_checkin(now)
    if due is None:
        return None
    kind, prompt = due
    if settings.vault_dir and settings.vault_dir.is_dir():
        diary_on, books_on = tracker.nudge_history()
        try:
            nudge = choose_nudge(kind, now.astimezone(JST).date(), VaultReader(settings.vault_dir), diary_on, books_on)
        except OSError as exc:  # vault on an unavailable drive must not block the check-in
            print(f"Warning: could not read vault: {exc}", file=sys.stderr)
            nudge = None
        if nudge:
            return kind, prompt, nudge[0], nudge[1]
    return kind, prompt, None, None


def compose_checkin(
    tracker: CheckInTracker, settings: Settings, now: datetime
) -> tuple[str, str, str | None] | None:
    """Template version of the check-in: ``(kind, message, nudge_key)``. Used as fallback and for ``status``."""
    plan = plan_checkin(tracker, settings, now)
    if plan is None:
        return None
    kind, prompt, nudge_key, nudge_text = plan
    return kind, f"{prompt}\n\n{nudge_text}" if nudge_text else prompt, nudge_key


def write_checkin_with_ai(settings: Settings, kind: str, nudge_text: str | None, now: datetime) -> str:
    """Have the agent write the check-in inside the ongoing conversation. Empty string on failure."""
    import asyncio

    from ai_journaling_agent.core.ai_responder import AiResponder
    from ai_journaling_agent.core.user_profile import JsonUserProfileRepository

    responder = AiResponder(settings.storage_dir, model=settings.claude_model)
    profile = JsonUserProfileRepository(settings.storage_dir).get(settings.owner_user_id)
    try:
        return asyncio.run(
            responder.compose_checkin(settings.owner_user_id, kind, hint=nudge_text, now=now, profile=profile)
        )
    except Exception as exc:  # noqa: BLE001 - any failure falls back to the template
        print(f"Warning: AI check-in failed, using template: {exc}", file=sys.stderr)
        return ""


def _push(settings: Settings, text: str) -> None:
    from linebot.v3.messaging import (  # type: ignore[import-untyped]
        ApiClient,
        Configuration,
        MessagingApi,
        PushMessageRequest,
        TextMessage,
    )

    with ApiClient(Configuration(access_token=settings.line_channel_access_token)) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(to=settings.owner_user_id, messages=[TextMessage(text=text)])
        )


def main(argv: list[str] | None = None) -> None:
    """Entry point for the checkin CLI."""
    parser = argparse.ArgumentParser(description="Check-in management")
    sub = parser.add_subparsers(dest="command", required=True)

    status_p = sub.add_parser("status", help="Show the check-in that would be sent now (does not send)")
    status_p.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")

    run_p = sub.add_parser("run", help="Send the check-in due now to OWNER_USER_ID and record it")
    run_p.add_argument("--now", default=None, help="Override current time (ISO 8601)")
    run_p.add_argument("--dry-run", action="store_true", help="Print instead of sending/recording")

    record = sub.add_parser("record", help="Record that a check-in was sent")
    record.add_argument("--kind", required=True, choices=["morning", "midday", "evening", "night_summary"])
    record.add_argument("--text", default=None, help="The prompt text that was sent (optional)")
    record.add_argument("--now", default=None, help="Override current time (ISO 8601, e.g. 2026-01-06T09:00:00)")

    args = parser.parse_args(argv)
    settings = Settings()  # type: ignore[call-arg]
    tracker = CheckInTracker(settings.storage_dir)
    now = datetime.fromisoformat(args.now).replace(tzinfo=UTC) if args.now else datetime.now(tz=UTC)

    if args.command == "status":
        composed = compose_checkin(tracker, settings, now)
        if composed:
            kind, message, _ = composed
            print(f"{kind} check-in needed")
            print(f"Prompt: {message}")
        else:
            print("No check-in needed.")

    elif args.command == "run":
        plan = plan_checkin(tracker, settings, now)
        if plan is None:
            print("No check-in needed.")
            return
        kind, template, nudge_key, nudge_text = plan
        fallback = f"{template}\n\n{nudge_text}" if nudge_text else template
        if args.dry_run:
            print(f"[dry-run] {kind} (template shown; the live run asks the agent to write it)\n{fallback}")
            return
        if not settings.owner_user_id:
            print("Error: OWNER_USER_ID is not set", file=sys.stderr)
            sys.exit(1)
        message = write_checkin_with_ai(settings, kind, nudge_text, now) or fallback
        _push(settings, message)
        jst_today = now.astimezone(JST).date()
        tracker.record_checkin(kind, jst_today)
        tracker.record_sent_prompt(message, now)
        if nudge_key:
            tracker.record_nudge(nudge_key, jst_today)
        source = "agent" if message != fallback else "template"
        print(f"Sent {kind} check-in ({source}){' with ' + nudge_key if nudge_key else ''}.")

    elif args.command == "record":
        jst_today = now.astimezone(JST).date()
        tracker.record_checkin(args.kind, jst_today)
        if args.text:
            tracker.record_sent_prompt(args.text, now)
        print(f"Recorded {args.kind} check-in for {jst_today.isoformat()}.")


if __name__ == "__main__":
    main(sys.argv[1:])
