"""Tests for profile_extractor."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from ai_journaling_agent.core.user_profile import UserProfile


class TestExtractProfileUpdates:
    """extract_profile_updates() merges AI-extracted info into existing profile."""

    async def test_extracts_interests_and_merges(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates

        existing = UserProfile(
            user_id="U1234",
            interests=["読書"],
            communication_style="",
            recurring_themes=[],
        )

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = (
            '{"interests": ["料理", "読書"], "recurring_themes": ["健康"], "communication_style": "丁寧"}'
        )

        result = await extract_profile_updates("料理が好きです", existing, mock_responder)

        # "読書" is already in existing, should not be duplicated
        assert "読書" in result.interests
        assert "料理" in result.interests
        assert result.interests.count("読書") == 1
        assert "健康" in result.recurring_themes
        assert result.communication_style == "丁寧"

    async def test_handles_invalid_json_gracefully(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates

        existing = UserProfile(
            user_id="U1234",
            interests=["読書"],
        )

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = "申し訳ありませんが、処理できませんでした。"

        result = await extract_profile_updates("テスト", existing, mock_responder)

        # Should return existing profile unchanged
        assert result is existing

    async def test_handles_empty_json_fields(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates

        existing = UserProfile(
            user_id="U1234",
            interests=["読書"],
            communication_style="カジュアル",
            recurring_themes=["仕事"],
        )

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = (
            '{"interests": [], "recurring_themes": [], "communication_style": ""}'
        )

        result = await extract_profile_updates("テスト", existing, mock_responder)

        # Empty fields should not overwrite existing data
        assert result.interests == ["読書"]
        assert result.communication_style == "カジュアル"
        assert result.recurring_themes == ["仕事"]

    async def test_does_not_duplicate_existing_themes(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates

        existing = UserProfile(
            user_id="U1234",
            interests=["音楽"],
            recurring_themes=["健康", "仕事"],
        )

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = (
            '{"interests": ["音楽", "スポーツ"], "recurring_themes": ["健康"], "communication_style": ""}'
        )

        result = await extract_profile_updates("テスト", existing, mock_responder)

        assert result.interests.count("音楽") == 1
        assert "スポーツ" in result.interests
        assert result.recurring_themes.count("健康") == 1

    async def test_updated_at_is_set(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder
        from ai_journaling_agent.core.profile_extractor import extract_profile_updates

        existing = UserProfile(user_id="U1234", updated_at=None)

        mock_responder = AsyncMock(spec=AiResponder)
        mock_responder.generate_response.return_value = (
            '{"interests": ["映画"], "recurring_themes": [], "communication_style": ""}'
        )

        result = await extract_profile_updates("映画が好き", existing, mock_responder)

        assert result.updated_at is not None
