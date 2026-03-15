"""Tests for check-in tracking."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_journaling_agent.core.checkin import CheckInTracker
from ai_journaling_agent.core.prompts import EVENING_CHECK_IN, MORNING_CHECK_IN

JST = ZoneInfo("Asia/Tokyo")


def _utc_from_jst(year: int, month: int, day: int, hour: int) -> datetime:
    """Create a UTC datetime from JST components."""
    jst_dt = datetime(year, month, day, hour, 0, 0, tzinfo=JST)
    return jst_dt.astimezone(UTC)


class TestNeedsCheckin:
    """needs_checkin returns the correct prompt based on JST time."""

    def test_morning_window_returns_prompt(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 7)  # JST 7:00
        assert tracker.needs_checkin(now) == MORNING_CHECK_IN

    def test_evening_window_returns_prompt(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 20)  # JST 20:00
        assert tracker.needs_checkin(now) == EVENING_CHECK_IN

    def test_outside_window_returns_none(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 14)  # JST 14:00
        assert tracker.needs_checkin(now) is None

    def test_boundary_morning_start(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 6)  # JST 6:00
        assert tracker.needs_checkin(now) == MORNING_CHECK_IN

    def test_boundary_morning_end(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 10)  # JST 10:00
        assert tracker.needs_checkin(now) is None

    def test_boundary_evening_start(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 18)  # JST 18:00
        assert tracker.needs_checkin(now) == EVENING_CHECK_IN

    def test_boundary_evening_end(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 22)  # JST 22:00
        assert tracker.needs_checkin(now) is None


class TestDuplicatePrevention:
    """needs_checkin returns None if already sent today."""

    def test_morning_already_sent(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        today = date(2026, 3, 15)
        tracker.record_checkin("morning", today)

        now = _utc_from_jst(2026, 3, 15, 8)  # JST 8:00
        assert tracker.needs_checkin(now) is None

    def test_evening_already_sent(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        today = date(2026, 3, 15)
        tracker.record_checkin("evening", today)

        now = _utc_from_jst(2026, 3, 15, 20)  # JST 20:00
        assert tracker.needs_checkin(now) is None

    def test_yesterday_does_not_block_today(self, tmp_path: Path) -> None:
        tracker = CheckInTracker(tmp_path)
        yesterday = date(2026, 3, 14)
        tracker.record_checkin("morning", yesterday)

        now = _utc_from_jst(2026, 3, 15, 8)  # JST 8:00
        assert tracker.needs_checkin(now) == MORNING_CHECK_IN


class TestRecordCheckin:
    """record_checkin persists to disk."""

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        tracker1 = CheckInTracker(tmp_path)
        today = date(2026, 3, 15)
        tracker1.record_checkin("morning", today)

        tracker2 = CheckInTracker(tmp_path)
        now = _utc_from_jst(2026, 3, 15, 8)
        assert tracker2.needs_checkin(now) is None
