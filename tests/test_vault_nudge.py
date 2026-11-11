"""Tests for the read-only vault reader and check-in planning (no reminders)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from ai_journaling_agent.cli.checkin_cmd import compose_checkin
from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.config import Settings
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


class TestComposeCheckin:
    def _settings(self, tmp_path: Path, vault_dir: Path | None) -> Settings:
        return Settings(
            line_channel_secret="s",
            line_channel_access_token="t",
            storage_dir=tmp_path / "data",
            owner_user_id="U1",
            vault_dir=vault_dir,
        )

    def test_full_multiline_prompt_without_reminders(self, tmp_path: Path, vault: Path) -> None:
        tracker = CheckInTracker(tmp_path / "data")
        now = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)  # 19:00 JST Saturday, diary empty
        composed = compose_checkin(tracker, self._settings(tmp_path, vault), now)
        assert composed is not None
        kind, message = composed
        assert kind == "evening" and "\n" in message
        assert "日記" not in message and "続き" not in message

    def test_late_evening_without_evening_sent_is_evening_kind(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path / "data")
        now = datetime(2026, 11, 7, 12, 30, tzinfo=UTC)  # 21:30 JST
        composed = compose_checkin(tracker, self._settings(tmp_path, None), now)
        assert composed is not None and composed[0] == "evening"


class TestWeeklyDigest:
    def _settings(self, tmp_path: Path, vault_dir: Path) -> Settings:
        return Settings(
            line_channel_secret="s",
            line_channel_access_token="t",
            storage_dir=tmp_path / "data",
            owner_user_id="U1",
            vault_dir=vault_dir,
        )

    def test_pending_until_delivered(self, tmp_path: Path, vault: Path) -> None:
        from ai_journaling_agent.cli.checkin_cmd import digest_hint, pending_digest

        _write(vault, "AI/週次 2026-W46.md", "---\nicon: 🤖\n---\n## 今週残したもの\n- [[無為]]\n")
        tracker = CheckInTracker(tmp_path / "data")
        settings = self._settings(tmp_path, vault)
        monday_morning = datetime(2026, 11, 15, 23, 0, tzinfo=UTC)  # 2026-11-16 (Mon) 08:00 JST
        pending = pending_digest(tracker, settings, monday_morning)
        assert pending is not None and pending[0] == "2026-W46" and "[[無為]]" in pending[1]
        assert "AI/週次 2026-W46" in digest_hint(*pending)
        tracker.record_digest("2026-W46")
        assert pending_digest(tracker, settings, monday_morning) is None

    def test_not_pending_before_it_exists(self, tmp_path: Path, vault: Path) -> None:
        from ai_journaling_agent.cli.checkin_cmd import pending_digest

        tracker = CheckInTracker(tmp_path / "data")
        assert (
            pending_digest(tracker, self._settings(tmp_path, vault), datetime(2026, 11, 15, 23, 0, tzinfo=UTC)) is None
        )
