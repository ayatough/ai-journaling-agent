"""Check-in tracking to prevent duplicate daily prompts."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_journaling_agent.core.prompts import EVENING_CHECK_IN, MORNING_CHECK_IN

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
        - 18:00–21:59 → EVENING_CHECK_IN (if not sent today)
        """
        jst_now = now.astimezone(JST)
        today = jst_now.date().isoformat()
        hour = jst_now.hour
        data = self._load()

        if 6 <= hour < 10:
            if data.get("last_morning_checkin") != today:
                return MORNING_CHECK_IN
        elif 18 <= hour < 22:
            if data.get("last_evening_checkin") != today:
                return EVENING_CHECK_IN

        return None

    def record_checkin(self, kind: str, today: date) -> None:
        """Record that a check-in was sent.

        Args:
            kind: "morning" or "evening"
            today: the date of the check-in
        """
        data = self._load()
        data[f"last_{kind}_checkin"] = today.isoformat()
        self._save(data)
