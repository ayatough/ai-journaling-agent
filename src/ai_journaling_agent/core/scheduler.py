"""Time-based check-in prompt selection."""

from __future__ import annotations

from ai_journaling_agent.core.prompts import EVENING_CHECK_IN, MORNING_CHECK_IN


def get_check_in_prompt(hour: int) -> str | None:
    """Return a check-in prompt based on the hour of day, or None.

    - 06:00–09:59 → morning check-in
    - 18:00–21:59 → evening check-in
    - Otherwise → None
    """
    if 6 <= hour < 10:
        return MORNING_CHECK_IN
    if 18 <= hour < 22:
        return EVENING_CHECK_IN
    return None
