"""Tests for AiResponder."""

from __future__ import annotations

from pathlib import Path
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


def _make_query(assistant_text: str, session_id: str):  # type: ignore[return]
    async def _mock_query(**kwargs):  # type: ignore[return]
        yield _AssistantMessage(assistant_text)
        yield _ResultMessage(session_id)

    return _mock_query


def _patch_sdk(assistant_text: str = "お疲れ様でした！", session_id: str = "sid-001"):
    return (
        patch("ai_journaling_agent.core.ai_responder.query", _make_query(assistant_text, session_id)),
        patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
        patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
        patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
    )


class TestGenerateResponse:
    """generate_response() returns text and saves session_id."""

    async def test_returns_assistant_text(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        q_patch, am_patch, rm_patch, tb_patch = _patch_sdk("お疲れ様でした！", "sid-001")
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            result = await responder.generate_response("U1234", "今日は疲れた")

        assert result == "お疲れ様でした！"

    async def test_saves_session_id_after_response(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        q_patch, am_patch, rm_patch, tb_patch = _patch_sdk("返答", "sid-abc")
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            await responder.generate_response("U1234", "テスト")

        session_file = tmp_path / "data" / "sessions" / "U1234.txt"
        assert session_file.exists()
        assert session_file.read_text().strip() == "sid-abc"

    async def test_loads_existing_session_id(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        storage_dir = tmp_path / "data"
        sessions_dir = storage_dir / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "U1234.txt").write_text("existing-sid")

        captured_options: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            captured_options.append(options)
            yield _AssistantMessage("返答")
            yield _ResultMessage("new-sid")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=storage_dir)
            await responder.generate_response("U1234", "こんにちは")

        assert captured_options[0].resume == "existing-sid"

    async def test_checkin_prompt_is_prepended_to_user_text(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        captured_prompts: list[str] = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            captured_prompts.append(prompt)
            yield _AssistantMessage("朝のチェックイン返答")
            yield _ResultMessage("sid-morning")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            result = await responder.generate_response(
                "U1234", "🥱", checkin_prompt="今朝の気分を絵文字ひとつで教えてください"
            )

        assert result == "朝のチェックイン返答"
        assert "今朝の気分を絵文字ひとつで教えてください" in captured_prompts[0]
        assert "🥱" in captured_prompts[0]

    async def test_returns_fallback_when_no_text(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        async def mock_query(**kwargs):  # type: ignore[return]
            yield _ResultMessage("sid-xyz")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            result = await responder.generate_response("U1234", "テスト")

        assert result == "(応答なし)"
