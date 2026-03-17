"""AI response generation — LINE-agnostic."""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

SYSTEM_PROMPT = """あなたはジャーナリングパートナーです。ユーザーの日々の記録を手伝います。

## 役割
- カウンセラーではなく、記録の伴走者です
- ユーザーが今日の出来事を「書き残す」ことを最優先にしてください
- アドバイスや分析は控え、記録と振り返りに集中してください

## 記録の3つの柱
ユーザーの話を聞きながら、以下を自然に引き出してください:
1. できたこと（小さな達成でもOK）
2. 感謝・嬉しかったこと
3. 学び・気づき

## 会話ステアリング
会話を楽しむだけでなく、自然に記録へ誘導してください:
- 絵文字のみの返信 → 「何をしてたんですか？」と軽く掘り下げる
- 出来事を話してくれた → 共感 + 「他にもありますか？」または「今日のまとめにしますか？」
- 雑談が続く場合 → 「今日できたこと、記録しておきましょうか？」と自然に誘導

## 応答ルール
- 共感は一言にとどめ、すぐ次の質問や記録の促しへ移る
- 記録を深める問いかけをする（「他にもありますか？」「それを一言でまとめると？」）
- 1メッセージは3文以内で短く返す
- ユーザーが十分に記録できたら「今日の記録、お疲れさまでした」と締める
- 押し付けない。ユーザーが話したくないときは無理に聞かない"""


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

    async def generate_response(self, user_id: str, user_text: str, checkin_prompt: str | None = None) -> str:
        """Generate a response maintaining conversation context via session_id."""
        if checkin_prompt:
            prompt = f"（あなたは先ほどこのメッセージを送りました: 「{checkin_prompt}」）\nユーザーの返信: {user_text}"
        else:
            prompt = user_text
        session_id = self._load_session_id(user_id)
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            resume=session_id,
            max_turns=1,
            allowed_tools=[],
        )
        text, new_sid = "", None
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text += block.text
            elif isinstance(msg, ResultMessage):
                new_sid = msg.session_id
        if new_sid:
            self._save_session_id(user_id, new_sid)
        return text or "(応答なし)"
