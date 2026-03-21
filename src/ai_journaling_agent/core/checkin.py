"""Check-in tracking to prevent duplicate daily prompts."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_journaling_agent.core.prompts import (
    EVENING_CHECK_IN,
    MIDDAY_CHECK_IN,
    MORNING_CHECK_IN,
    NIGHT_SUMMARY,
)

JST = ZoneInfo("Asia/Tokyo")


class CheckInTracker:
    """Tracks whether morning/evening check-ins have been sent today."""

    def __init__(self, storage_dir: Path) -> None:
        self._path = storage_dir / "checkin_log.json"

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        with self._path.open(encoding="utf-8") as f:
            return json.loads(f.read())  # type: ignore[no-any-return]

    def _save(self, data: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False))

    def needs_checkin(self, now: datetime) -> str | None:
        """Return a check-in prompt if one is needed right now, else None.

        Time windows are evaluated in JST:
        - 06:00–09:59 → MORNING_CHECK_IN (if not sent today)
        - 12:00–12:59 → MIDDAY_CHECK_IN (if not sent today)
        - 18:00–21:59 → EVENING_CHECK_IN (if not sent today)
        - 21:00–22:59 → NIGHT_SUMMARY (if evening done but summary not sent today)
        """
        jst_now = now.astimezone(JST)
        today = jst_now.date().isoformat()
        hour = jst_now.hour
        data = self._load()

        if 6 <= hour < 10:
            if data.get("last_morning_checkin") != today:
                return MORNING_CHECK_IN
        elif 12 <= hour < 13:
            if data.get("last_midday_checkin") != today:
                return MIDDAY_CHECK_IN
        elif 18 <= hour < 21:
            if data.get("last_evening_checkin") != today:
                return EVENING_CHECK_IN
        elif 21 <= hour < 23:
            if data.get("last_evening_checkin") == today and data.get("last_night_summary_checkin") != today:
                return NIGHT_SUMMARY
            if data.get("last_evening_checkin") != today:
                return EVENING_CHECK_IN

        return None

    def record_checkin(self, kind: str, today: date) -> None:
        """Record that a check-in was sent.

        Args:
            kind: "morning", "midday", "evening", or "night_summary"
            today: the date of the check-in
        """
        data = self._load()
        data[f"last_{kind}_checkin"] = today.isoformat()
        self._save(data)

    def record_sent_prompt(self, prompt_text: str, sent_at: datetime) -> None:
        """Record the text of the check-in prompt that was sent."""
        data = self._load()
        data["last_sent_prompt"] = prompt_text
        data["last_sent_at"] = sent_at.isoformat()
        self._save(data)

    def get_recent_prompt(self, within_hours: int = 8, now: datetime | None = None) -> str | None:
        """Return the prompt text if sent within the given number of hours."""
        data = self._load()
        prompt = data.get("last_sent_prompt")
        sent_at_str = data.get("last_sent_at")
        if not prompt or not sent_at_str:
            return None
        sent_at = datetime.fromisoformat(sent_at_str)
        _now = now or datetime.now(tz=UTC)
        if (_now - sent_at).total_seconds() < within_hours * 3600:
            return prompt
        return None
