"""AI response generation — LINE-agnostic."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ProcessError, ResultMessage, TextBlock, query

if TYPE_CHECKING:
    from ai_journaling_agent.core.user_profile import UserProfile
    from ai_journaling_agent.core.vault_tools import VaultContext

logger = logging.getLogger(__name__)

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
- 押し付けない。ユーザーが話したくないときは無理に聞かない

## ムード記録
- 絵文字を受け取ったら、その絵文字が表す気持ちや状況に触れつつ会話を続ける
- 会話の流れが自然なタイミングで「今日の気分を5段階（1=つらい〜5=最高）で表すとどのくらいですか？」と軽く尋ねる
- 毎回必ず聞く必要はない。ユーザーが気分を語ってくれた場合はそこから推測してもよい
- スコアを答えてくれなくても追及しない

## 時間と会話のつながり
- ユーザーの発言の先頭には [日時] が付いている。前回の発言からの経過時間や、日付が変わったことを意識する
- 日をまたいだら、前日までの会話の続きややり残し（例: 「昨日のパン、また作りました？」）に
  自然に触れてよい。ただし毎回ではなく、しつこくしない
- 「[お知らせ 日時]」で始まるメッセージはシステムからの合図で、ユーザーの発言ではない。
  その指示に沿って、ユーザーに送る文面だけを書く（前置き・説明・「お知らせ」への言及は書かない）。
  あなたの返答はそのまま LINE でユーザーに届く"""


JST = ZoneInfo("Asia/Tokyo")
_WEEKDAYS = "月火水木金土日"

CHECKIN_INSTRUCTIONS = {
    "morning": "朝のチェックインの時間です。体調や今日の予定を軽く聞いてください。"
    "前日までの会話に続きややり残しがあれば、一言触れてもよい。",
    "midday": "お昼のチェックインの時間です。午前中のことを軽く聞いてください。"
    "少し前まで会話していたなら、その続きとして自然に声をかけてください。",
    "evening": "夕方のチェックインの時間です。今日一日のことを軽く聞いてください。"
    "今日すでに話してくれた内容があれば、それを踏まえて聞いてください。",
    "night_summary": "夜の振り返りの時間です。"
    "今日の会話から、できたこと・良かったこと・気づきを2〜4行で短くまとめて伝え、"
    "付け足したいことがあるか聞いてください。今日の会話がほとんどなければ、無理にまとめず一言ねぎらってください。",
}

_ONE_OFF_SYSTEM_PROMPT = "あなたはデータ処理の補助をします。指示された形式の出力だけを返してください。"


def format_stamp(now: datetime) -> str:
    """e.g. ``2026-11-10(火) 19:00`` in JST."""
    j = now.astimezone(JST)
    return f"{j:%Y-%m-%d}({_WEEKDAYS[j.weekday()]}) {j:%H:%M}"


class AiResponder:
    """Generate AI responses using claude-agent-sdk with session continuity.

    One long-running conversation (session) per user. Everything the user sees from the
    agent — replies *and* scheduled check-ins — is generated inside that session, so the
    agent always knows what it has said. Background jobs (profile extraction) run in
    separate one-off sessions so they never appear in the conversation.
    """

    def __init__(
        self,
        storage_dir: Path,
        vault_context: Callable[[str], VaultContext | None] | None = None,
        model: str | None = None,
    ) -> None:
        self._vault_context = vault_context
        self._model = model or None
        self._sessions_dir = storage_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _load_session_id(self, user_id: str) -> str | None:
        p = self._sessions_dir / f"{user_id}.txt"
        return p.read_text().strip() if p.exists() else None

    def _save_session_id(self, user_id: str, session_id: str) -> None:
        (self._sessions_dir / f"{user_id}.txt").write_text(session_id)

    def _clear_session_id(self, user_id: str) -> None:
        (self._sessions_dir / f"{user_id}.txt").unlink(missing_ok=True)

    @staticmethod
    async def _run_query(prompt: str, options: ClaudeAgentOptions) -> tuple[str, str | None]:
        text, new_sid = "", None
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                # With tools, several assistant turns may occur; reply with the last one that has text.
                turn = "".join(block.text for block in msg.content if isinstance(block, TextBlock))
                if turn.strip():
                    text = turn
            elif isinstance(msg, ResultMessage):
                new_sid = msg.session_id
        return text, new_sid

    def _options(self, system_prompt: str, resume: str | None) -> ClaudeAgentOptions:
        # Built-in tools (file access, shell, web) are always disabled: the agent talks to
        # an internet-facing chat. The only tools it may get are the narrow vault tools.
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            resume=resume,
            max_turns=1,
            tools=[],
            allowed_tools=[],
        )
        if self._model:
            options.model = self._model
        return options

    @staticmethod
    def _system_prompt(profile: UserProfile | None) -> str:
        if profile is None:
            return SYSTEM_PROMPT
        parts = []
        if profile.interests:
            parts.append(f"興味・関心: {', '.join(profile.interests)}")
        if profile.communication_style:
            parts.append(f"コミュニケーションスタイル: {profile.communication_style}")
        if profile.recurring_themes:
            parts.append(f"繰り返し出てくるテーマ: {', '.join(profile.recurring_themes)}")
        if not parts:
            return SYSTEM_PROMPT
        return SYSTEM_PROMPT + "\n\n【このユーザーについて】\n" + "\n".join(parts)

    async def _run_in_session(
        self, user_id: str, prompt: str, profile: UserProfile | None, with_vault_tools: bool
    ) -> str:
        system_prompt = self._system_prompt(profile)
        session_id = self._load_session_id(user_id)
        options = self._options(system_prompt, session_id)
        ctx = self._vault_context(user_id) if (with_vault_tools and self._vault_context) else None
        if ctx is not None:
            from ai_journaling_agent.core.vault_tools import TOOL_NAMES, build_vault_server

            options.system_prompt = system_prompt + ctx.system_prompt()
            options.mcp_servers = {"vault": build_vault_server(ctx)}
            options.allowed_tools = list(TOOL_NAMES)
            options.max_turns = 5
        try:
            text, new_sid = await self._run_query(prompt, options)
        except ProcessError:
            if session_id is None:
                raise
            logger.warning("Resuming session failed for %s; starting a new session", user_id, exc_info=True)
            self._clear_session_id(user_id)
            options.resume = None
            text, new_sid = await self._run_query(prompt, options)
        if new_sid:
            self._save_session_id(user_id, new_sid)
        return text

    async def generate_response(
        self,
        user_id: str,
        user_text: str,
        checkin_prompt: str | None = None,
        profile: UserProfile | None = None,
        now: datetime | None = None,
    ) -> str:
        """Reply to a user message inside the user's ongoing conversation.

        ``checkin_prompt`` is only for callers whose check-ins are *not* generated in the
        session (the local REPL). The LINE bot generates check-ins via ``compose_checkin``.
        """
        stamp = format_stamp(now or datetime.now(tz=UTC))
        prompt = f"[{stamp}] {user_text}"
        if checkin_prompt:
            prompt = f"（あなたは先ほどこのメッセージを送りました: 「{checkin_prompt}」）\n{prompt}"
        text = await self._run_in_session(user_id, prompt, profile, with_vault_tools=True)
        return text or "(応答なし)"

    async def compose_checkin(
        self,
        user_id: str,
        kind: str,
        hint: str | None = None,
        now: datetime | None = None,
        profile: UserProfile | None = None,
    ) -> str:
        """Write a scheduled check-in message inside the conversation (so it stays in context)."""
        stamp = format_stamp(now or datetime.now(tz=UTC))
        lines = [f"[お知らせ {stamp}] {CHECKIN_INSTRUCTIONS[kind]}"]
        if hint:
            lines.append(f"さりげなく添えてほしいこと: {hint}")
        lines.append("2〜4文の短いメッセージにしてください。")
        return (await self._run_in_session(user_id, "\n".join(lines), profile, with_vault_tools=False)).strip()

    async def complete_once(self, prompt: str) -> str:
        """Run a one-off prompt in a fresh session that is not saved (never touches the conversation)."""
        text, _ = await self._run_query(prompt, self._options(_ONE_OFF_SYSTEM_PROMPT, None))
        return text
