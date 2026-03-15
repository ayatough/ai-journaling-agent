"""LINE Messaging API adapter — FastAPI application factory."""

from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError  # type: ignore[import-untyped]
from linebot.v3.messaging import (  # type: ignore[import-untyped]
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    PushMessageRequest,
    TextMessage,
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
from ai_journaling_agent.core.ai_responder import AiResponder
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.inbox import JsonInboxRepository
from ai_journaling_agent.core.repository import JsonJournalRepository
from ai_journaling_agent.core.user import JsonUserRepository


async def _respond_to_user(
    user_id: str,
    user_text: str,
    responder: AiResponder,
    access_token: str,
) -> None:
    """Background task: generate AI response and push to LINE."""
    response = await responder.generate_response(user_id, user_text)
    configuration = Configuration(access_token=access_token)
    async with AsyncApiClient(configuration) as api_client:
        line_api = AsyncMessagingApi(api_client)
        await line_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=response)],
            )
        )


def create_app(settings: Settings) -> FastAPI:
    """Create a FastAPI application wired with LINE webhook handling."""
    app = FastAPI()

    parser = WebhookParser(channel_secret=settings.line_channel_secret)
    configuration = Configuration(access_token=settings.line_channel_access_token)
    repository = JsonJournalRepository(settings.storage_dir)
    user_repository = JsonUserRepository(settings.storage_dir)
    inbox_repository = JsonInboxRepository(settings.storage_dir)
    responder = AiResponder(
        storage_dir=settings.storage_dir,
    )

    @app.post("/callback")
    async def callback(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
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
                        event, line_api, repository, user_repository,
                        inbox_repository,
                    )
                    background_tasks.add_task(
                        _respond_to_user,
                        user_id=event.source.user_id,
                        user_text=event.message.text,
                        responder=responder,
                        access_token=settings.line_channel_access_token,
                    )
                elif isinstance(event, FollowEvent):
                    await handle_follow_event(event, line_api, user_repository)
                elif isinstance(event, UnfollowEvent):
                    await handle_unfollow_event(event, user_repository)

        return {"status": "ok"}

    return app
