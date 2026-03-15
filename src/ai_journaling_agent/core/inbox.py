"""Inbox management for asynchronous message processing."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


@dataclass
class InboxMessage:
    """A pending message received from a user."""

    id: str
    user_id: str
    text: str
    received_at: datetime
    status: str  # "pending" | "processed"

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "text": self.text,
            "received_at": self.received_at.isoformat(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InboxMessage:
        """Deserialize from a dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            text=data["text"],
            received_at=datetime.fromisoformat(data["received_at"]),
            status=data["status"],
        )


def generate_message_id(now: datetime) -> str:
    """Generate a sortable message ID: timestamp prefix + short UUID."""
    ts = int(now.timestamp() * 1000)
    return f"{ts}_{uuid4().hex[:8]}"


class InboxRepository(Protocol):
    """Abstract repository for inbox messages."""

    def save(self, msg: InboxMessage) -> None: ...

    def list_pending(self) -> list[InboxMessage]: ...

    def mark_processed(self, msg_id: str) -> None: ...


class JsonInboxRepository:
    """JSON file-based inbox. One file per message: {storage_dir}/inbox/{id}.json"""

    def __init__(self, storage_dir: Path) -> None:
        self._inbox_dir = storage_dir / "inbox"
        self._processed_dir = self._inbox_dir / "processed"

    def save(self, msg: InboxMessage) -> None:
        """Save an inbox message as a JSON file."""
        self._inbox_dir.mkdir(parents=True, exist_ok=True)
        path = self._inbox_dir / f"{msg.id}.json"
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(msg.to_dict(), ensure_ascii=False))

    def list_pending(self) -> list[InboxMessage]:
        """Return all pending messages sorted by ID (chronological)."""
        if not self._inbox_dir.exists():
            return []
        messages: list[InboxMessage] = []
        for path in sorted(self._inbox_dir.glob("*.json")):
            with path.open(encoding="utf-8") as f:
                msg = InboxMessage.from_dict(json.loads(f.read()))
            if msg.status == "pending":
                messages.append(msg)
        return messages

    def mark_processed(self, msg_id: str) -> None:
        """Move a message to the processed directory."""
        src = self._inbox_dir / f"{msg_id}.json"
        if not src.exists():
            return
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        dst = self._processed_dir / f"{msg_id}.json"
        # Update status before moving
        with src.open(encoding="utf-8") as f:
            data = json.loads(f.read())
        data["status"] = "processed"
        with src.open("w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False))
        shutil.move(str(src), str(dst))
