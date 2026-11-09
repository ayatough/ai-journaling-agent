"""LINE Messaging API adapter — FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

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
from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.inbox import JsonInboxRepository
from ai_journaling_agent.core.repository import JsonJournalRepository
from ai_journaling_agent.core.user import JsonUserRepository
from ai_journaling_agent.core.user_profile import JsonUserProfileRepository, UserProfile
from ai_journaling_agent.core.vault_tools import VaultContext

PROFILE_UPDATE_INTERVAL = 5

logger = logging.getLogger(__name__)


def is_owner_event(event: object, owner_user_id: str) -> bool:
    """Return True if the event was sent by the configured owner.

    This bot is personal: each person runs their own instance with their own
    LINE channel and Claude subscription. Events from anyone else (or from
    groups/rooms without a user id) are ignored. If no owner is configured,
    every event is ignored so that the bot fails closed.
    """
    if not owner_user_id:
        return False
    source = getattr(event, "source", None)
    user_id = getattr(source, "user_id", None)
    return bool(user_id) and user_id == owner_user_id


async def _respond_to_user(
    user_id: str,
    user_text: str,
    responder: AiResponder,
    access_token: str,
    checkin_tracker: CheckInTracker,
    profile_repository: JsonUserProfileRepository,
) -> None:
    """Background task: generate AI response and push to LINE."""
    profile = profile_repository.get(user_id)
    # Check-ins are generated inside the same conversation (see checkin_cmd), so no wrapper is needed.
    response = await responder.generate_response(user_id, user_text, profile=profile)
    configuration = Configuration(access_token=access_token)
    async with AsyncApiClient(configuration) as api_client:
        line_api = AsyncMessagingApi(api_client)
        await line_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=response)],
            )
        )
    # Profile auto-update
    if profile is None:
        profile = UserProfile(user_id=user_id)
    profile.profile_update_counter += 1
    if profile.profile_update_counter % PROFILE_UPDATE_INTERVAL == 0:
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates
        profile = await extract_profile_updates(user_text, profile, responder)
    profile_repository.save(profile)


def _make_vault_context(
    settings: Settings, repository: JsonJournalRepository
) -> Callable[[str], VaultContext | None] | None:
    """Vault tools are enabled only when VAULT_DIR points to an existing folder."""
    vault_dir = settings.vault_dir
    if vault_dir is None:
        return None

    def factory(user_id: str) -> VaultContext | None:
        if not vault_dir.is_dir():
            logger.warning("VAULT_DIR %s is not available; vault tools disabled for this reply", vault_dir)
            return None

        def recent_user_texts() -> list[str]:
            since = datetime.now(tz=UTC) - timedelta(hours=24)
            return [
                e.summary or e.emoji or ""
                for e in repository.list_entries(user_id)
                if (e.timestamp if e.timestamp.tzinfo else e.timestamp.replace(tzinfo=UTC)) >= since
            ]

        return VaultContext(vault_dir=vault_dir, recent_user_texts=recent_user_texts)

    return factory


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
        vault_context=_make_vault_context(settings, repository),
        model=settings.claude_model,
    )
    checkin_tracker = CheckInTracker(settings.storage_dir)
    profile_repository = JsonUserProfileRepository(settings.storage_dir)

    if not settings.owner_user_id:
        logger.warning("OWNER_USER_ID is not set; all LINE events will be ignored")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

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
                if not is_owner_event(event, settings.owner_user_id):
                    user_id = getattr(getattr(event, "source", None), "user_id", None) or "?"
                    logger.warning("Ignoring event from non-owner user %s...", str(user_id)[:6])
                    continue
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
                        checkin_tracker=checkin_tracker,
                        profile_repository=profile_repository,
                    )
                elif isinstance(event, FollowEvent):
                    await handle_follow_event(event, line_api, user_repository)
                elif isinstance(event, UnfollowEvent):
                    await handle_unfollow_event(event, user_repository)

        return {"status": "ok"}

    return app
