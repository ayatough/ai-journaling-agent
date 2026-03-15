"""Tests for user state management."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_journaling_agent.core.user import JsonUserRepository, UserState


class TestUserState:
    """UserState serialization round-trips correctly."""

    def test_to_dict_and_from_dict(self) -> None:
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        state = UserState(
            user_id="U1234",
            is_active=True,
            created_at=now,
            last_interaction=now,
        )
        data = state.to_dict()
        restored = UserState.from_dict(data)
        assert restored.user_id == "U1234"
        assert restored.is_active is True
        assert restored.created_at == now
        assert restored.last_interaction == now

    def test_inactive_state_round_trip(self) -> None:
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        state = UserState(
            user_id="U5678",
            is_active=False,
            created_at=now,
            last_interaction=now,
        )
        restored = UserState.from_dict(state.to_dict())
        assert restored.is_active is False


class TestJsonUserRepository:
    """JsonUserRepository persists user state to disk."""

    def test_save_and_get(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        state = UserState(
            user_id="U1234",
            is_active=True,
            created_at=now,
            last_interaction=now,
        )
        repo.save(state)

        loaded = repo.get("U1234")
        assert loaded is not None
        assert loaded.user_id == "U1234"
        assert loaded.is_active is True

    def test_get_nonexistent_returns_none(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path)
        assert repo.get("U9999") is None

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        state = UserState(
            user_id="U1234",
            is_active=True,
            created_at=now,
            last_interaction=now,
        )
        repo.save(state)

        state.is_active = False
        repo.save(state)

        loaded = repo.get("U1234")
        assert loaded is not None
        assert loaded.is_active is False

    def test_multiple_users_independent(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)

        repo.save(UserState("U001", True, now, now))
        repo.save(UserState("U002", False, now, now))

        assert repo.get("U001") is not None
        assert repo.get("U001").is_active is True  # type: ignore[union-attr]
        assert repo.get("U002") is not None
        assert repo.get("U002").is_active is False  # type: ignore[union-attr]
