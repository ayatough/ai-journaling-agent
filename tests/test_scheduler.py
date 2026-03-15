"""Tests for time-based check-in prompt selection."""

from __future__ import annotations

import pytest

from ai_journaling_agent.core.prompts import EVENING_CHECK_IN, MORNING_CHECK_IN
from ai_journaling_agent.core.scheduler import get_check_in_prompt


class TestGetCheckInPrompt:
    """get_check_in_prompt returns the correct prompt for the hour."""

    @pytest.mark.parametrize(
        ("hour", "expected"),
        [
            (6, MORNING_CHECK_IN),
            (7, MORNING_CHECK_IN),
            (9, MORNING_CHECK_IN),
            (18, EVENING_CHECK_IN),
            (20, EVENING_CHECK_IN),
            (21, EVENING_CHECK_IN),
        ],
        ids=[
            "morning_start_6",
            "morning_mid_7",
            "morning_end_9",
            "evening_start_18",
            "evening_mid_20",
            "evening_end_21",
        ],
    )
    def test_check_in_hours(self, hour: int, expected: str) -> None:
        assert get_check_in_prompt(hour) == expected

    @pytest.mark.parametrize(
        "hour",
        [0, 3, 5, 10, 12, 14, 17, 22, 23],
        ids=[
            "midnight_0",
            "early_3",
            "before_morning_5",
            "after_morning_10",
            "noon_12",
            "afternoon_14",
            "before_evening_17",
            "after_evening_22",
            "late_night_23",
        ],
    )
    def test_no_check_in_hours(self, hour: int) -> None:
        assert get_check_in_prompt(hour) is None
