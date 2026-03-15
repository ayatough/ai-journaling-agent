"""AI response generation — LINE-agnostic."""

from __future__ import annotations

import subprocess
from pathlib import Path

from anthropic import Anthropic

SYSTEM_PROMPT = """あなたはジャーナリングをサポートするエージェントです。
ユーザーの記録を助け、今日の出来事を振り返れるよう会話を誘導してください。
温かく、共感的に、短く丁寧に応答してください。"""


class AiResponder:
    """Generate AI responses using Anthropic SDK with journal history context."""

    def __init__(self, api_key: str, storage_dir: Path) -> None:
        self._client = Anthropic(api_key=api_key)
        self._storage_dir = storage_dir

    def generate_response(self, user_id: str, user_text: str) -> str:
        """Generate a response for the given user message with journal history context."""
        history = self._get_history(user_id)
        return self._call_api(user_text, history)

    def _get_history(self, user_id: str) -> str:
        result = subprocess.run(
            ["uv", "run", "journal-history", "--user", user_id, "--days", "3"],
            capture_output=True,
            text=True,
            cwd=self._storage_dir.parent,
        )
        return result.stdout.strip() or "(履歴なし)"

    def _call_api(self, user_text: str, history: str) -> str:
        msg = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"[直近の記録]\n{history}\n\n[新しいメッセージ]\n{user_text}",
                }
            ],
        )
        return str(msg.content[0].text)  # type: ignore[union-attr]
