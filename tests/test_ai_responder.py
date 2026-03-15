"""Tests for AiResponder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestGenerateResponse:
    """generate_response() calls history then API."""

    def test_returns_api_text(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "お疲れ様でした！"
        mock_client.messages.create.return_value.content = [mock_content]

        with patch("ai_journaling_agent.core.ai_responder.Anthropic", return_value=mock_client):
            responder = AiResponder(api_key="test-key", storage_dir=tmp_path / "data")

        with patch.object(responder, "_get_history", return_value="(履歴なし)"):
            result = responder.generate_response("U1234", "今日は疲れた")

        assert result == "お疲れ様でした！"
        mock_client.messages.create.assert_called_once()

    def test_history_included_in_api_call(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "返答"
        mock_client.messages.create.return_value.content = [mock_content]

        with patch("ai_journaling_agent.core.ai_responder.Anthropic", return_value=mock_client):
            responder = AiResponder(api_key="test-key", storage_dir=tmp_path / "data")

        history = "2026-03-14: 良い日だった"
        with patch.object(responder, "_get_history", return_value=history):
            responder.generate_response("U1234", "今日は？")

        call_kwargs = mock_client.messages.create.call_args
        content = call_kwargs[1]["messages"][0]["content"]
        assert history in content
        assert "今日は？" in content


class TestGetHistory:
    """_get_history() calls journal-history subprocess."""

    def test_calls_subprocess_with_user_and_days(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        storage_dir = tmp_path / "data"
        with patch("ai_journaling_agent.core.ai_responder.Anthropic"):
            responder = AiResponder(api_key="test-key", storage_dir=storage_dir)

        mock_result = MagicMock()
        mock_result.stdout = "some history"
        with patch("ai_journaling_agent.core.ai_responder.subprocess.run", return_value=mock_result) as mock_run:
            result = responder._get_history("U5678")

        assert result == "some history"
        mock_run.assert_called_once_with(
            ["uv", "run", "journal-history", "--user", "U5678", "--days", "3"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

    def test_returns_fallback_when_no_output(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_responder import AiResponder

        with patch("ai_journaling_agent.core.ai_responder.Anthropic"):
            responder = AiResponder(api_key="test-key", storage_dir=tmp_path / "data")

        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("ai_journaling_agent.core.ai_responder.subprocess.run", return_value=mock_result):
            result = responder._get_history("U0000")

        assert result == "(履歴なし)"
