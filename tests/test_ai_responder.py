"""Tests for AiResponder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from claude_agent_sdk import ProcessError


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

    async def test_retries_without_resume_when_session_is_stale(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        storage_dir = tmp_path / "data"
        (storage_dir / "sessions").mkdir(parents=True)
        (storage_dir / "sessions" / "U1234.txt").write_text("stale-sid")

        resumes: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            resumes.append(options.resume)
            if options.resume is not None:
                raise ProcessError("Command failed", exit_code=1)
            yield _AssistantMessage("復旧しました")
            yield _ResultMessage("fresh-sid")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=storage_dir)
            result = await responder.generate_response("U1234", "こんにちは")

        assert result == "復旧しました"
        assert resumes == ["stale-sid", None]
        assert (storage_dir / "sessions" / "U1234.txt").read_text().strip() == "fresh-sid"

    async def test_error_without_session_is_not_swallowed(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        calls: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            calls.append(options.resume)
            raise ProcessError("Command failed", exit_code=1)
            yield  # pragma: no cover

        with patch("ai_journaling_agent.core.ai_responder.query", mock_query):
            responder = AiResponder(storage_dir=tmp_path / "data")
            with pytest.raises(ProcessError):
                await responder.generate_response("U1234", "こんにちは")

        assert calls == [None]

    async def test_error_on_retry_propagates(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        storage_dir = tmp_path / "data"
        (storage_dir / "sessions").mkdir(parents=True)
        (storage_dir / "sessions" / "U1234.txt").write_text("stale-sid")
        calls: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            calls.append(options.resume)
            raise ProcessError("Command failed", exit_code=1)
            yield  # pragma: no cover

        with patch("ai_journaling_agent.core.ai_responder.query", mock_query):
            responder = AiResponder(storage_dir=storage_dir)
            with pytest.raises(ProcessError):
                await responder.generate_response("U1234", "こんにちは")

        assert calls == ["stale-sid", None]

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


class TestConversationContinuity:
    """Check-ins and replies share one conversation; background jobs don't."""

    async def test_reply_is_timestamped(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        from ai_journaling_agent.core.ai_responder import AiResponder

        responder = AiResponder(storage_dir=tmp_path)
        seen: list[str] = []

        async def fake_run(prompt: str, options: object) -> tuple[str, str | None]:
            seen.append(prompt)
            return "ok", "sid-1"

        with patch.object(AiResponder, "_run_query", side_effect=fake_run):
            await responder.generate_response("U1", "こんにちは", now=datetime(2026, 11, 10, 10, 0, tzinfo=UTC))
        assert seen == ["[2026-11-10(火) 19:00] こんにちは"]

    async def test_checkin_is_written_in_the_same_session(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        from ai_journaling_agent.core.ai_responder import AiResponder

        responder = AiResponder(storage_dir=tmp_path, model="sonnet")
        (tmp_path / "sessions" / "U1.txt").write_text("sid-old")
        calls: list[tuple[str, object]] = []

        async def fake_run(prompt: str, options: object) -> tuple[str, str | None]:
            calls.append((prompt, options))
            return "昨日のパン、どうでした？", "sid-new"

        with patch.object(AiResponder, "_run_query", side_effect=fake_run):
            text = await responder.compose_checkin(
                "U1", "morning", hint="日記が未記入", now=datetime(2026, 11, 9, 23, 0, tzinfo=UTC)
            )
        assert text == "昨日のパン、どうでした？"
        prompt, options = calls[0]
        assert prompt.startswith("[お知らせ 2026-11-10(火) 08:00]") and "日記が未記入" in prompt
        assert options.resume == "sid-old"  # type: ignore[attr-defined]
        assert options.model == "sonnet"  # type: ignore[attr-defined]
        assert options.tools == []  # type: ignore[attr-defined]
        assert (tmp_path / "sessions" / "U1.txt").read_text() == "sid-new"

    async def test_complete_once_does_not_touch_session(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        responder = AiResponder(storage_dir=tmp_path)
        (tmp_path / "sessions" / "U1.txt").write_text("sid-keep")
        captured: list[object] = []

        async def fake_run(prompt: str, options: object) -> tuple[str, str | None]:
            captured.append(options)
            return "{}", "sid-other"

        with patch.object(AiResponder, "_run_query", side_effect=fake_run):
            await responder.complete_once("JSON を返して")
        assert captured[0].resume is None  # type: ignore[attr-defined]
        assert (tmp_path / "sessions" / "U1.txt").read_text() == "sid-keep"
