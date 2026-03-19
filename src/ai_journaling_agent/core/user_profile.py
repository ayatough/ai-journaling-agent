"""UserProfile data model and repository."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


@dataclass
class UserProfile:
    user_id: str
    interests: list[str] = field(default_factory=list)
    communication_style: str = ""
    recurring_themes: list[str] = field(default_factory=list)
    updated_at: datetime | None = None
    profile_update_counter: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "user_id": self.user_id,
            "interests": self.interests,
            "communication_style": self.communication_style,
            "recurring_themes": self.recurring_themes,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "profile_update_counter": self.profile_update_counter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        updated_at_raw = data.get("updated_at")
        return cls(
            user_id=data["user_id"],
            interests=list(data.get("interests") or []),
            communication_style=data.get("communication_style") or "",
            recurring_themes=list(data.get("recurring_themes") or []),
            updated_at=datetime.fromisoformat(updated_at_raw) if updated_at_raw else None,
            profile_update_counter=int(data.get("profile_update_counter") or 0),
        )


class UserProfileRepository(Protocol):
    def get(self, user_id: str) -> UserProfile | None: ...
    def save(self, profile: UserProfile) -> None: ...


class JsonUserProfileRepository:
    """JSON-based profile repository. One file per user: {storage_dir}/profiles/{user_id}.json"""

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir / "profiles"

    def _profile_file(self, user_id: str) -> Path:
        return self._storage_dir / f"{user_id}.json"

    def get(self, user_id: str) -> UserProfile | None:
        path = self._profile_file(user_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return UserProfile.from_dict(json.loads(f.read()))

    def save(self, profile: UserProfile) -> None:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        with self._profile_file(profile.user_id).open("w", encoding="utf-8") as f:
            f.write(json.dumps(profile.to_dict(), ensure_ascii=False))
