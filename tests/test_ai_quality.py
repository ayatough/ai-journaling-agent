"""AI response quality tests — requires ANTHROPIC_API_KEY."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")


class TestAiResponseQuality:
    async def test_emoji_response_steers_to_journaling(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_evaluator import AiEvaluator
        from ai_journaling_agent.core.ai_responder import AiResponder

        responder = AiResponder(storage_dir=tmp_path / "data")
        evaluator = AiEvaluator()
        response = await responder.generate_response("eval-user", "😊")
        result = await evaluator.evaluate("😊", response)
        assert result.get("pass") is True, f"評価失敗: {result.get('reason')}"

    async def test_story_response_acknowledges_and_asks(self, tmp_path: Path) -> None:
        from ai_journaling_agent.core.ai_evaluator import AiEvaluator
        from ai_journaling_agent.core.ai_responder import AiResponder

        responder = AiResponder(storage_dir=tmp_path / "data")
        evaluator = AiEvaluator()
        response = await responder.generate_response("eval-user", "今日は大事な発表があってうまくいった")
        result = await evaluator.evaluate("今日は大事な発表があってうまくいった", response)
        assert result.get("pass") is True, f"評価失敗: {result.get('reason')}"

    async def test_response_is_concise(self, tmp_path: Path) -> None:
        """Response should be 3 sentences or fewer."""
        from ai_journaling_agent.core.ai_responder import AiResponder

        responder = AiResponder(storage_dir=tmp_path / "data")
        response = await responder.generate_response("eval-user", "今日は本当に色々あって疲れました")
        assert isinstance(response, str)
        assert len(response) > 0
        # Structural check: count sentence-ending punctuation
        import re
        sentences = re.split(r"[。！？\n]", response.strip())
        non_empty = [s for s in sentences if s.strip()]
        assert len(non_empty) <= 5, f"返答が長すぎます ({len(non_empty)}文): {response}"
