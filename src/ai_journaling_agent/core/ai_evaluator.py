"""AI response quality evaluator — stateless Claude evaluator."""

from __future__ import annotations

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

EVALUATOR_SYSTEM_PROMPT = """あなたはジャーナリングAIアシスタントの品質評価者です。

ユーザーのメッセージとAIの返答を受け取り、以下の基準で評価してください:
1. ユーザーへの共感が適切か（押しつけがましくない）
2. 記録や振り返りへの誘導があるか
3. 返答が3文以内か
4. 日本語として自然か

以下のJSON形式のみで返答してください（説明不要）:
{"pass": true/false, "score": 1-5, "reason": "一言で"}"""


class AiEvaluator:
    """Stateless AI evaluator for journaling agent response quality."""

    async def evaluate(self, user_message: str, ai_response: str) -> dict[str, object]:
        """Evaluate an AI response. Returns {"pass": bool, "score": int, "reason": str}."""
        import json
        import re

        prompt = f"ユーザー: {user_message}\nAI返答: {ai_response}"
        options = ClaudeAgentOptions(
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            resume=None,  # always stateless
            max_turns=1,
            allowed_tools=[],
        )
        text = ""
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text += block.text
        # parse JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass
        return {"pass": False, "score": 0, "reason": f"parse error: {text}"}
