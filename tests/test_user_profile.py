"""Tests for UserProfile data model and repository."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from ai_journaling_agent.core.user_profile import JsonUserProfileRepository, UserProfile


class TestUserProfileDataclass:
    """UserProfile serialization round-trips correctly."""

    def test_to_dict_and_from_dict_with_updated_at(self) -> None:
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        profile = UserProfile(
            user_id="U1234",
            interests=["読書", "料理"],
            communication_style="丁寧",
            recurring_themes=["健康", "仕事"],
            updated_at=now,
            profile_update_counter=3,
        )
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)

        assert restored.user_id == "U1234"
        assert restored.interests == ["読書", "料理"]
        assert restored.communication_style == "丁寧"
        assert restored.recurring_themes == ["健康", "仕事"]
        assert restored.updated_at == now
        assert restored.profile_update_counter == 3

    def test_to_dict_and_from_dict_without_updated_at(self) -> None:
        profile = UserProfile(
            user_id="U5678",
            interests=[],
            communication_style="",
            recurring_themes=[],
            updated_at=None,
            profile_update_counter=0,
        )
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)

        assert restored.user_id == "U5678"
        assert restored.updated_at is None
        assert restored.profile_update_counter == 0

    def test_from_dict_tolerates_missing_optional_fields(self) -> None:
        data = {"user_id": "U9999"}
        profile = UserProfile.from_dict(data)
        assert profile.user_id == "U9999"
        assert profile.interests == []
        assert profile.communication_style == ""
        assert profile.recurring_themes == []
        assert profile.updated_at is None
        assert profile.profile_update_counter == 0


class TestJsonUserProfileRepository:
    """JsonUserProfileRepository persists user profiles to disk."""

    def test_get_returns_none_for_missing_user(self, tmp_path: Path) -> None:
        repo = JsonUserProfileRepository(tmp_path)
        assert repo.get("U_MISSING") is None

    def test_save_and_get_roundtrip(self, tmp_path: Path) -> None:
        repo = JsonUserProfileRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        profile = UserProfile(
            user_id="U1234",
            interests=["音楽"],
            communication_style="カジュアル",
            recurring_themes=["趣味"],
            updated_at=now,
            profile_update_counter=2,
        )
        repo.save(profile)

        loaded = repo.get("U1234")
        assert loaded is not None
        assert loaded.user_id == "U1234"
        assert loaded.interests == ["音楽"]
        assert loaded.communication_style == "カジュアル"
        assert loaded.recurring_themes == ["趣味"]
        assert loaded.updated_at == now
        assert loaded.profile_update_counter == 2

    def test_save_creates_parent_directory(self, tmp_path: Path) -> None:
        repo = JsonUserProfileRepository(tmp_path / "new_storage")
        profile = UserProfile(user_id="U_NEW")
        repo.save(profile)
        assert repo.get("U_NEW") is not None

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        repo = JsonUserProfileRepository(tmp_path)
        profile = UserProfile(user_id="U1234", interests=["読書"])
        repo.save(profile)

        profile.interests = ["映画", "音楽"]
        repo.save(profile)

        loaded = repo.get("U1234")
        assert loaded is not None
        assert loaded.interests == ["映画", "音楽"]


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _AssistantMessage:
    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]


class _ResultMessage:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


def _make_query(assistant_text: str, session_id: str = "sid-001"):  # type: ignore[return]
    async def _mock_query(**kwargs):  # type: ignore[return]
        yield _AssistantMessage(assistant_text)
        yield _ResultMessage(session_id)

    return _mock_query


def _patch_sdk(assistant_text: str = "返答", session_id: str = "sid-001"):
    return (
        patch("ai_journaling_agent.core.ai_responder.query", _make_query(assistant_text, session_id)),
        patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
        patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
        patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
    )


class TestAiResponderWithProfile:
    """AiResponder uses profile context in system prompt when profile is provided."""

    async def test_profile_context_added_to_system_prompt(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        captured_options: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            captured_options.append(options)
            yield _AssistantMessage("返答")
            yield _ResultMessage("sid-001")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            profile = UserProfile(
                user_id="U1234",
                interests=["読書", "料理"],
                communication_style="丁寧",
                recurring_themes=["健康"],
            )
            await responder.generate_response("U1234", "こんにちは", profile=profile)

        system_prompt = captured_options[0].system_prompt
        assert "【このユーザーについて】" in system_prompt
        assert "読書" in system_prompt
        assert "料理" in system_prompt
        assert "丁寧" in system_prompt
        assert "健康" in system_prompt

    async def test_no_profile_system_prompt_unchanged(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import SYSTEM_PROMPT, AiResponder

        captured_options: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            captured_options.append(options)
            yield _AssistantMessage("返答")
            yield _ResultMessage("sid-001")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            await responder.generate_response("U1234", "こんにちは", profile=None)

        assert captured_options[0].system_prompt == SYSTEM_PROMPT

    async def test_profile_with_empty_fields_no_user_context_appended(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import SYSTEM_PROMPT, AiResponder

        captured_options: list = []

        async def mock_query(prompt: str, options):  # type: ignore[return]
            captured_options.append(options)
            yield _AssistantMessage("返答")
            yield _ResultMessage("sid-001")

        q_patch, am_patch, rm_patch, tb_patch = (
            patch("ai_journaling_agent.core.ai_responder.query", mock_query),
            patch("ai_journaling_agent.core.ai_responder.AssistantMessage", _AssistantMessage),
            patch("ai_journaling_agent.core.ai_responder.ResultMessage", _ResultMessage),
            patch("ai_journaling_agent.core.ai_responder.TextBlock", _TextBlock),
        )
        with q_patch, am_patch, rm_patch, tb_patch:
            responder = AiResponder(storage_dir=tmp_path / "data")
            # Profile with all empty fields — no context should be appended
            profile = UserProfile(user_id="U1234")
            await responder.generate_response("U1234", "こんにちは", profile=profile)

        assert captured_options[0].system_prompt == SYSTEM_PROMPT
