"""LINE Messaging API adapter — FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError  # type: ignore[import-untyped]
from linebot.v3.messaging import (  # type: ignore[import-untyped]
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
)
from linebot.v3.webhook import WebhookParser  # type: ignore[import-untyped]
from linebot.v3.webhooks import (  # type: ignore[import-untyped]
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    UnfollowEvent,
)

from ai_journaling_agent.adapters.line.handlers import (
    handle_follow_event,
    handle_message_event,
    handle_unfollow_event,
)
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.repository import JsonJournalRepository
from ai_journaling_agent.core.user import JsonUserRepository


def create_app(settings: Settings) -> FastAPI:
    """Create a FastAPI application wired with LINE webhook handling."""
    app = FastAPI()

    parser = WebhookParser(channel_secret=settings.line_channel_secret)
    configuration = Configuration(access_token=settings.line_channel_access_token)
    repository = JsonJournalRepository(settings.storage_dir)
    user_repository = JsonUserRepository(settings.storage_dir)

    @app.post("/callback")
    async def callback(request: Request) -> dict[str, str]:
        signature = request.headers.get("X-Line-Signature", "")
        body = await request.body()

        try:
            events = parser.parse(body.decode(), signature)
        except InvalidSignatureError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        async with AsyncApiClient(configuration) as api_client:
            line_api = AsyncMessagingApi(api_client)
            for event in events:
                if isinstance(event, MessageEvent) and isinstance(
                    event.message, TextMessageContent
                ):
                    await handle_message_event(
                        event, line_api, repository, user_repository
                    )
                elif isinstance(event, FollowEvent):
                    await handle_follow_event(event, line_api, user_repository)
                elif isinstance(event, UnfollowEvent):
                    await handle_unfollow_event(event, user_repository)

        return {"status": "ok"}

    return app
