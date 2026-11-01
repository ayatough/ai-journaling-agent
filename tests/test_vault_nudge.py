"""Tests for the read-only vault reader and check-in nudges."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from ai_journaling_agent.cli.checkin_cmd import compose_checkin
from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.config import Settings
from ai_journaling_agent.core.nudge import DIARY_NUDGE, choose_nudge
from ai_journaling_agent.core.vault import VaultReader, split_frontmatter

SAT = date(2026, 11, 7)
MON = date(2026, 11, 9)


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    root = tmp_path / "vault"
    _write(root, "Notes/真説 老子/真説 老子.md", '---\nicon: 📘\ndate: "2026-06-20"\ntags:\n  - book\n---\n## 概要\n')
    _write(root, "Notes/真説 老子/無為.md", '---\nicon: 📝\ndate: 2026-06-28\nsource: "[[真説 老子]]"\n---\nメモ\n')
    _write(root, "Notes/老子 全訳注/老子 全訳注.md", '---\nicon: 📘\ndate: "2026-06-25"\n---\n')
    _write(root, "Notes/新しい本/新しい本.md", '---\nicon: 📘\ndate: "2026-11-05"\n---\n')
    _write(root, "Templates/Book Source.md", '---\nicon: 📘\ndate: "{{date:YYYY-MM-DD}}"\n---\n')
    _write(root, "Notes/Journal/2026-11-07.md", '---\nicon: ✍\ndate: "2026-11-07"\nmood: \n---\n\n')
    _write(root, "Notes/Journal/2026-11-08.md", "---\nicon: ✍\n---\n散歩した\n")
    return root


class TestVaultReader:
    def test_split_frontmatter(self) -> None:
        fields, body = split_frontmatter('---\nicon: 📝\nsource: "[[A]]"\ntags:\n  - x\n---\nbody\n')
        assert fields == {"icon": "📝", "source": "[[A]]", "tags": ""}
        assert body == "body\n"

    def test_daily_note_empty_body_is_not_written(self, vault: Path) -> None:
        reader = VaultReader(vault)
        assert reader.has_daily_note(date(2026, 11, 7)) is False
        assert reader.has_daily_note(date(2026, 11, 8)) is True
        assert reader.has_daily_note(date(2026, 11, 9)) is False

    def test_books_use_latest_memo_date_and_skip_templates(self, vault: Path) -> None:
        books = VaultReader(vault).books()
        assert [(b.name, b.last_date) for b in books] == [
            ("老子 全訳注", date(2026, 6, 25)),
            ("真説 老子", date(2026, 6, 28)),
            ("新しい本", date(2026, 11, 5)),
        ]


class TestChooseNudge:
    def test_diary_nudge_in_evening_when_not_written(self, vault: Path) -> None:
        assert choose_nudge("evening", SAT, VaultReader(vault), None, {}) == ("diary", DIARY_NUDGE)

    def test_no_diary_nudge_when_written(self, vault: Path) -> None:
        assert choose_nudge("evening", date(2026, 11, 8), VaultReader(vault), None, {}) is None

    def test_diary_nudge_once_per_day(self, vault: Path) -> None:
        assert choose_nudge("night_summary", SAT, VaultReader(vault), SAT.isoformat(), {}) is None

    def test_book_nudge_on_weekend_morning_picks_oldest(self, vault: Path) -> None:
        nudge = choose_nudge("morning", SAT, VaultReader(vault), None, {})
        assert nudge is not None
        assert nudge[0] == "book:老子 全訳注"
        assert "6/25" in nudge[1]

    def test_book_cooldown_and_idle_threshold(self, vault: Path) -> None:
        history = {"老子 全訳注": "2026-11-01", "真説 老子": "2026-10-30"}
        # both old books in cooldown, the new book is not idle long enough
        assert choose_nudge("morning", SAT, VaultReader(vault), None, history) is None

    def test_no_book_nudge_on_weekday(self, vault: Path) -> None:
        assert choose_nudge("morning", MON, VaultReader(vault), None, {}) is None

    def test_midday_has_no_nudge(self, vault: Path) -> None:
        assert choose_nudge("midday", SAT, VaultReader(vault), None, {}) is None


class TestComposeCheckin:
    def _settings(self, tmp_path: Path, vault_dir: Path | None) -> Settings:
        return Settings(
            line_channel_secret="s",
            line_channel_access_token="t",
            storage_dir=tmp_path / "data",
            owner_user_id="U1",
            vault_dir=vault_dir,
        )

    def test_full_multiline_prompt_with_nudge(self, tmp_path: Path, vault: Path) -> None:
        tracker = CheckInTracker(tmp_path / "data")
        now = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)  # 19:00 JST Saturday
        composed = compose_checkin(tracker, self._settings(tmp_path, vault), now)
        assert composed is not None
        kind, message, key = composed
        assert kind == "evening"
        assert "\n" in message and message.endswith(DIARY_NUDGE)
        assert key == "diary"

    def test_without_vault_no_nudge(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path / "data")
        now = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)
        composed = compose_checkin(tracker, self._settings(tmp_path, None), now)
        assert composed is not None and composed[2] is None

    def test_late_evening_without_evening_sent_is_evening_kind(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path / "data")
        now = datetime(2026, 11, 7, 12, 30, tzinfo=UTC)  # 21:30 JST
        composed = compose_checkin(tracker, self._settings(tmp_path, None), now)
        assert composed is not None and composed[0] == "evening"

    def test_nudge_recorded_is_not_repeated(self, tmp_path: Path, vault: Path) -> None:
        tracker = CheckInTracker(tmp_path / "data")
        tracker.record_nudge("diary", SAT)
        tracker.record_checkin("evening", SAT)
        now = datetime(2026, 11, 7, 12, 30, tzinfo=UTC)  # 21:30 JST → night_summary
        composed = compose_checkin(tracker, self._settings(tmp_path, vault), now)
        assert composed is not None
        assert composed[0] == "night_summary" and composed[2] is None
