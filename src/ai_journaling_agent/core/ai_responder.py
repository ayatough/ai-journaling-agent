"""AI response generation — LINE-agnostic."""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

SYSTEM_PROMPT = """あなたはジャーナリングをサポートするエージェントです。
ユーザーの記録を助け、今日の出来事を振り返れるよう会話を誘導してください。
温かく、共感的に、短く丁寧に応答してください。"""


class AiResponder:
    """Generate AI responses using claude-agent-sdk with session continuity."""

    def __init__(self, storage_dir: Path) -> None:
        self._sessions_dir = storage_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _load_session_id(self, user_id: str) -> str | None:
        p = self._sessions_dir / f"{user_id}.txt"
        return p.read_text().strip() if p.exists() else None

    def _save_session_id(self, user_id: str, session_id: str) -> None:
        (self._sessions_dir / f"{user_id}.txt").write_text(session_id)

    async def generate_response(self, user_id: str, user_text: str) -> str:
        """Generate a response maintaining conversation context via session_id."""
        session_id = self._load_session_id(user_id)
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            resume=session_id,
            max_turns=1,
            allowed_tools=[],
        )
        text, new_sid = "", None
        async for msg in query(prompt=user_text, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text += block.text
            elif isinstance(msg, ResultMessage):
                new_sid = msg.session_id
        if new_sid:
            self._save_session_id(user_id, new_sid)
        return text or "(応答なし)"
