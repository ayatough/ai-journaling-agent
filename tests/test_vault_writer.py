"""Tests for vault writes and the agent's vault tools."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from ai_journaling_agent.core.vault_tools import VaultContext, body_is_verbatim, build_vault_server
from ai_journaling_agent.core.vault_writer import RELAY_PATH, VaultWriteError, VaultWriter, sanitize_title

NOW = datetime(2026, 11, 7, 14, 5, tzinfo=ZoneInfo("Asia/Tokyo"))
DAILY_TEMPLATE = '---\nicon: ✍\ndate: "{{date:YYYY-MM-DD}}"\ncondition: \nmood: \ngood: \nphoto: \ntags: []\n---\n'


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    (root / "Templates").mkdir(parents=True)
    (root / "Templates" / "Daily Note.md").write_text(DAILY_TEMPLATE, encoding="utf-8")
    (root / "Notes" / "真説 老子").mkdir(parents=True)
    (root / "Notes" / "真説 老子" / "真説 老子.md").write_text(
        '---\nicon: 📘\ndate: "2026-06-20"\n---\n', encoding="utf-8"
    )
    return root


class TestCreateMemo:
    def test_memo_frontmatter_and_verbatim_body(self, vault: Path) -> None:
        path = VaultWriter(vault).create_memo("無為と強制力", "無為って強制しないことか\nなるほど", NOW, "真説 老子")
        assert path == vault / "Inbox" / "無為と強制力.md"
        assert path.read_text(encoding="utf-8") == (
            '---\nicon: 📝\ndate: 2026-11-07\ntime: 14:05\ntags: []\nsource: "[[真説 老子]]"\n---\n'
            "無為って強制しないことか\nなるほど\n"
        )

    def test_idea_has_no_source(self, vault: Path) -> None:
        text = VaultWriter(vault).create_memo("思いつき", "アプリにしたい", NOW, idea=True).read_text(encoding="utf-8")
        assert "icon: 💡" in text and "tags: [idea]" in text and "source" not in text

    def test_never_overwrites(self, vault: Path) -> None:
        w = VaultWriter(vault)
        first = w.create_memo("同じ", "一つ目", NOW)
        second = w.create_memo("同じ", "二つ目", NOW)
        assert second.name == "同じ (2).md"
        assert first.read_text(encoding="utf-8").endswith("一つ目\n")

    def test_title_is_sanitized(self) -> None:
        assert sanitize_title('a/b:c*?"<>|[[x]]') == "a b c x"
        with pytest.raises(VaultWriteError):
            sanitize_title("///")


class TestDailyNote:
    def test_creates_from_template_and_fills(self, vault: Path) -> None:
        written = VaultWriter(vault).fill_daily_fields(NOW, {"mood": "4", "good": "散歩した"})
        assert written == {"mood": "4", "good": "散歩した"}
        text = (vault / "Notes" / "Journal" / "2026-11-07.md").read_text(encoding="utf-8")
        assert 'date: "2026-11-07"' in text and "mood: 4\n" in text and 'good: "散歩した"\n' in text
        assert "condition: \n" in text

    def test_does_not_overwrite_values_or_body(self, vault: Path) -> None:
        p = vault / "Notes" / "Journal" / "2026-11-07.md"
        p.parent.mkdir(parents=True)
        p.write_text("---\nicon: ✍\ncondition: 2\nmood: \ngood: \n---\n本文 mood: \n", encoding="utf-8")
        written = VaultWriter(vault).fill_daily_fields(NOW, {"condition": "5", "mood": "3"})
        assert written == {"mood": "3"}
        assert p.read_text(encoding="utf-8") == "---\nicon: ✍\ncondition: 2\nmood: 3\ngood: \n---\n本文 mood: \n"


class TestRelay:
    def test_append_only_checklist(self, vault: Path) -> None:
        w = VaultWriter(vault)
        w.append_relay(NOW, "一件目")
        w.append_relay(NOW, "二件目")
        text = (vault / RELAY_PATH).read_text(encoding="utf-8")
        assert text.startswith("---\nicon: 📌")
        assert text.endswith("- [ ] 2026-11-07 14:05 一件目\n- [ ] 2026-11-07 14:05 二件目\n")


class TestVerbatim:
    def test_accepts_selected_lines_ignoring_spacing_and_width(self) -> None:
        user = ["今日は老子を読んだ。", "無為って 強制しないことか", "ＶＩＯの論文も"]
        assert body_is_verbatim("無為って強制しないことか\n> VIOの論文も", user)

    def test_rejects_paraphrase(self) -> None:
        assert not body_is_verbatim("無為とは強制力を用いないことである", ["無為って強制しないことか"])
        assert not body_is_verbatim("  ", ["x"])


_HANDLERS: dict[str, Any] = {}


@pytest.fixture()
def tools(vault: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import ai_journaling_agent.core.vault_tools as vt

    captured: dict[str, Any] = {}
    monkeypatch.setattr(vt, "create_sdk_mcp_server", lambda name, tools: captured.update({t.name: t for t in tools}))
    ctx = VaultContext(
        vault, recent_user_texts=lambda: ["老子の無為、強制しないことなんだな", "良い一日だった"], now=lambda: NOW
    )
    build_vault_server(ctx)
    _HANDLERS.clear()
    _HANDLERS.update({k: v.handler for k, v in captured.items()})
    return vault


class TestTools:
    def test_save_memo_writes_and_relays(self, tools: Path) -> None:
        res = asyncio.run(
            _HANDLERS["save_memo"](
                {"title": "無為", "body": "老子の無為、強制しないことなんだな", "source": "真説 老子"}
            )
        )
        assert "is_error" not in res
        assert 'source: "[[真説 老子]]"' in (tools / "Inbox" / "無為.md").read_text(encoding="utf-8")
        assert "メモ作成 [[無為]]" in (tools / RELAY_PATH).read_text(encoding="utf-8")

    def test_save_memo_rejects_rewritten_body(self, tools: Path) -> None:
        res = asyncio.run(_HANDLERS["save_memo"]({"title": "無為", "body": "無為とは強制しないことである"}))
        assert res.get("is_error") is True
        assert not (tools / "Inbox").exists()

    def test_unknown_source_is_dropped_and_noted(self, tools: Path) -> None:
        asyncio.run(_HANDLERS["save_memo"]({"title": "x", "body": "良い一日だった", "source": "存在しない本"}))
        assert 'source: "[[]]"' in (tools / "Inbox" / "x.md").read_text(encoding="utf-8")
        assert "存在しない本" in (tools / RELAY_PATH).read_text(encoding="utf-8")

    def test_fill_daily_note(self, tools: Path) -> None:
        res = asyncio.run(_HANDLERS["fill_daily_note"]({"mood": 4, "condition": 9, "good": "散歩"}))
        assert "mood=4" in res["content"][0]["text"] and "condition" not in res["content"][0]["text"]
        assert "mood: 4" in (tools / "Notes" / "Journal" / "2026-11-07.md").read_text(encoding="utf-8")
