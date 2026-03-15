"""User state management for lifecycle tracking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


@dataclass
class UserState:
    """Represents a user's lifecycle state."""

    user_id: str
    is_active: bool
    created_at: datetime
    last_interaction: datetime

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "user_id": self.user_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserState:
        """Deserialize from a dictionary."""
        return cls(
            user_id=data["user_id"],
            is_active=data["is_active"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_interaction=datetime.fromisoformat(data["last_interaction"]),
        )


class UserRepository(Protocol):
    """Abstract repository for user state."""

    def get(self, user_id: str) -> UserState | None: ...

    def save(self, state: UserState) -> None: ...


class JsonUserRepository:
    """JSON-based user repository. One file per user: {storage_dir}/users/{user_id}.json"""

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir / "users"

    def _user_file(self, user_id: str) -> Path:
        return self._storage_dir / f"{user_id}.json"

    def get(self, user_id: str) -> UserState | None:
        """Load user state, or None if not found."""
        path = self._user_file(user_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return UserState.from_dict(json.loads(f.read()))

    def save(self, state: UserState) -> None:
        """Save user state (overwrites existing)."""
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        with self._user_file(state.user_id).open("w", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), ensure_ascii=False))
