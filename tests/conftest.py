"""Shared test fixtures and helpers."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _AssistantMessage:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]


class _ResultMessage:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


@contextmanager
def patch_sdk(assistant_text: str = "お疲れ様でした！", session_id: str = "sid-001"):  # type: ignore[return]
    """Context manager that patches the claude-agent-sdk used by AiResponder."""

    async def _mock_query(**kwargs):  # type: ignore[return]
        yield _AssistantMessage(assistant_text)
        yield _ResultMessage(session_id)

    with (
        patch("ai_journaling_agent.core.ai_responder.query", _mock_query),
        patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
        patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
        patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
    ):
        yield
