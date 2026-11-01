"""Tools the journal agent can call to write to the Obsidian vault.

Exposed to Claude as an in-process MCP server. These are the *only* tools the agent
has (built-in tools such as file access and shell are disabled in AiResponder).
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from claude_agent_sdk import create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig

from ai_journaling_agent.core.vault import VaultReader
from ai_journaling_agent.core.vault_writer import VaultWriteError, VaultWriter

JST = ZoneInfo("Asia/Tokyo")
SERVER_NAME = "vault"
TOOL_NAMES = [f"mcp__{SERVER_NAME}__save_memo", f"mcp__{SERVER_NAME}__fill_daily_note"]

VAULT_PROMPT = """

## Obsidian へのメモ（秘書として）
ユーザーは Obsidian で「1ノート = 1トピック」の小さなメモを書き、リンクでつなげています。
- 勉強・読書・数学・アイデアの話が出たら、1〜2個の短い質問で「一番残したい一点」と、それについて思ったことを引き出す
- 論文はユーザーが話題にしたときだけ扱う。こちらから論文を勧めない
- 残せそうになったら「メモに残しますか？」と確認し、ユーザーが肯定したときだけ save_memo を呼ぶ。勝手に保存しない
- 1メモ = 1トピック。話題が2つあれば、別々に確認して別々に保存する
- body はユーザーの発言をそのまま使う。要約・清書・誤字の修正・言い換えをしない。関係する発言を選んで並べるのはよい
- title はそのトピックを表す短い名前。できるだけユーザーの言葉から取る
- source は下の一覧にある本・論文の名前と一致するときだけ指定する
- 保存したら「Inbox に『(title)』として残しました」と一文で伝える
- 体調・気分・良かったことが聞けたら fill_daily_note で今日のデイリーノートに記入してよい
  （空欄にだけ入る）。そのことを一言伝える
"""


def _norm(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


def body_is_verbatim(body: str, user_texts: list[str]) -> bool:
    """Every non-empty line of the body must appear in what the user actually wrote.

    Whitespace and full/half-width differences are ignored; a leading "> " quote marker is allowed.
    """
    corpus = _norm("\n".join(user_texts))
    lines = [ln.strip().removeprefix(">").strip() for ln in body.splitlines()]
    lines = [ln for ln in lines if ln]
    return bool(lines) and all(_norm(ln) in corpus for ln in lines)


@dataclass
class VaultContext:
    """Everything the vault tools need for one user."""

    vault_dir: Path
    recent_user_texts: Callable[[], list[str]]
    now: Callable[[], datetime] = lambda: datetime.now(tz=JST)

    def source_names(self) -> dict[str, str]:
        try:
            return VaultReader(self.vault_dir).sources()
        except OSError:
            return {}

    def system_prompt(self) -> str:
        names = self.source_names()
        books = [n for n, i in names.items() if i == "📘"]
        papers = [n for n, i in names.items() if i == "🎓"]
        extra = VAULT_PROMPT
        if books:
            extra += "\n既存の本: " + " / ".join(sorted(books))
        if papers:
            extra += "\n既存の論文: " + " / ".join(sorted(papers))
        return extra


def _text(msg: str, error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": msg}]}
    if error:
        result["is_error"] = True
    return result


def build_vault_server(ctx: VaultContext) -> McpSdkServerConfig:
    writer = VaultWriter(ctx.vault_dir)

    @tool(
        "save_memo",
        "ユーザーの言葉をそのまま本文にした1トピックのメモを Obsidian の Inbox に新規作成する。"
        "ユーザーが保存に同意したときだけ呼ぶ。",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "トピックを表す短い名前（ファイル名になる）"},
                "body": {"type": "string", "description": "ユーザーの発言をそのまま。改変しない"},
                "source": {"type": "string", "description": "既存の本・論文の名前。無ければ空文字"},
                "kind": {
                    "type": "string",
                    "enum": ["memo", "idea"],
                    "description": "学びメモなら memo、思いつきなら idea",
                },
            },
            "required": ["title", "body"],
        },
    )
    async def save_memo(args: dict[str, Any]) -> dict[str, Any]:
        body = str(args.get("body", ""))
        if not body_is_verbatim(body, ctx.recent_user_texts()):
            return _text(
                "保存しませんでした: body はユーザーの発言をそのまま使ってください（要約・言い換え不可）", True
            )
        source = str(args.get("source") or "").strip() or None
        relay_note = ""
        if source and source not in ctx.source_names():
            relay_note = f" — source 候補「{source}」は既存ノートに無いため未設定"
            source = None
        now = ctx.now()
        try:
            path = writer.create_memo(str(args.get("title", "")), body, now, source, idea=args.get("kind") == "idea")
        except (VaultWriteError, OSError) as exc:
            return _text(f"保存できませんでした: {exc}", True)
        src = f"source: [[{source}]]" if source else "source 未設定"
        writer.append_relay(now, f"メモ作成 [[{path.stem}]] (Inbox) — {src}{relay_note}。リンク整備・Notes への移動")
        return _text(f"Inbox/{path.name} を作成しました")

    @tool(
        "fill_daily_note",
        "今日のデイリーノートの frontmatter の空欄"
        "（condition 体調1-5 / mood 気分1-5 / good 良かったこと一言）を埋める。"
        "本文には触れない。既に値がある項目は変更されない。",
        {
            "type": "object",
            "properties": {
                "condition": {"type": "integer", "minimum": 1, "maximum": 5},
                "mood": {"type": "integer", "minimum": 1, "maximum": 5},
                "good": {"type": "string", "description": "ユーザーが話した今日良かったことを一言で"},
            },
        },
    )
    async def fill_daily_note(args: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, str] = {}
        for key in ("condition", "mood"):
            v = args.get(key)
            if isinstance(v, int) and 1 <= v <= 5:
                values[key] = str(v)
        if isinstance(args.get("good"), str):
            values["good"] = args["good"]
        now = ctx.now()
        try:
            written = writer.fill_daily_fields(now, values)
        except OSError as exc:
            return _text(f"記入できませんでした: {exc}", True)
        if not written:
            return _text("記入する空欄がありませんでした（既に値が入っています）")
        fields = ", ".join(f"{k}={v}" for k, v in written.items())
        writer.append_relay(now, f"デイリーノート [[{now:%Y-%m-%d}]] に {fields} を記入 — 確認のみ")
        return _text(f"今日のデイリーノートに {fields} を記入しました")

    return create_sdk_mcp_server(SERVER_NAME, tools=[save_memo, fill_daily_note])
