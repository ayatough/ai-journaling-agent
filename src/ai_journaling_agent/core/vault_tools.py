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
TOOL_NAMES = [f"mcp__{SERVER_NAME}__{n}" for n in ("save_memo", "fill_daily_note", "set_photo_source")]

VAULT_PROMPT = """

## Obsidian への保存（頼まれたときだけ）
ユーザーは Obsidian に「1ノート = 1トピック」の断片を残しています。メモは義務ではありません。
- ユーザーが「残して」「メモして」など保存を頼んだときだけ save_memo を呼ぶ。
  こちらから「メモに残しますか？」と提案しない
- 一行・引用だけの断片で十分。保存のために質問して話を膨らませない
- body はユーザーの発言をそのまま使う。要約・清書・誤字の修正・言い換えをしない。関係する発言を選んで並べるのはよい
- 話題が2つあれば別々のメモにする
- title はそのトピックを表す短い名前。できるだけユーザーの言葉から取る
- source は下の一覧にある本・論文の名前と一致するときだけ指定する
- 保存したら「Inbox に『(title)』として残しました」と一文で伝える
- 体調・気分を数字で言ってくれたら fill_daily_note の condition / mood に入れてよい。
  良かったことを話してくれたら good にその発言をそのまま（一部の抜き出しは可）入れてよい。記入したことは一言伝える

## 写真
- ユーザーが送った写真は自動で vault の Attachments/ に保存される（「（写真を送りました: ファイル名）」として届く）。
  あなたには画像の中身は見えない。受け取ったことを短く伝えるだけでよく、説明を求めない
- どの本・論文のページかをユーザーが話したら、set_photo_source でその写真と本を結び付ける（一覧にある名前のときだけ）

## 読了インタビュー（ユーザーが本を読み終えたと言ったときだけ）
- 一度だけ「読了おめでとうございます。よければ2〜3問だけ聞いて、答えをそのまま本のメモにしましょうか？」と聞く。
  断られたり、話題が変わったりしたらやめる。二度は聞かない
- 了承されたら一問ずつ聞く（例: 印象に残ったところ / 自分に引きつけて思ったこと / 読む前と変わったこと）。
  了承をもって保存の同意とみなし、答えが返るたびにその答えを原文のまま save_memo で保存する
  （source にその本、title は答えの要点を短く。1問1メモ）。保存したことは短く伝えて次の問いへ。3問で終える
- 答えにくそうな問いはスキップする。感想の深掘りや追加の質問はしない
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
        "（condition 体調1-5 / mood 気分1-5 / good 良かったこと＝発言の原文）を埋める。"
        "本文には触れない。既に値がある項目は変更されない。",
        {
            "type": "object",
            "properties": {
                "condition": {"type": "integer", "minimum": 1, "maximum": 5},
                "mood": {"type": "integer", "minimum": 1, "maximum": 5},
                "good": {
                    "type": "string",
                    "description": "ユーザーが話した良かったこと。発言をそのまま（抜き出し可、言い換え不可）",
                },
            },
        },
    )
    async def fill_daily_note(args: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, str] = {}
        for key in ("condition", "mood"):
            v = args.get(key)
            if isinstance(v, int) and 1 <= v <= 5:
                values[key] = str(v)
        good = args.get("good")
        if isinstance(good, str) and good.strip():
            if "\n" in good.strip() or not body_is_verbatim(good, ctx.recent_user_texts()):
                msg = "記入しませんでした: good はユーザーの発言をそのまま一行で使ってください（言い換え不可）"
                return _text(msg, True)
            values["good"] = good.strip()
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

    @tool(
        "set_photo_source",
        "LINE で受け取った写真（Attachments/ のファイル名）が、どの本・論文のページかを整理役に伝える。",
        {
            "type": "object",
            "properties": {
                "file_name": {"type": "string", "description": "例: LINE_20261111_093000.jpg"},
                "source": {"type": "string", "description": "既存の本・論文の名前"},
            },
            "required": ["file_name", "source"],
        },
    )
    async def set_photo_source(args: dict[str, Any]) -> dict[str, Any]:
        name = Path(str(args.get("file_name", ""))).name
        source = str(args.get("source", "")).strip()
        if not name or not (ctx.vault_dir / "Attachments" / name).is_file():
            return _text("その写真は Attachments/ にありません", True)
        if source not in ctx.source_names():
            return _text("その名前の本・論文は vault にありません", True)
        writer.append_relay(ctx.now(), f"写真 [[{name}]] の source: [[{source}]]（ユーザーが LINE で伝えた）")
        return _text(f"{name} を『{source}』のページとして整理役に伝えました")

    return create_sdk_mcp_server(SERVER_NAME, tools=[save_memo, fill_daily_note, set_photo_source])
