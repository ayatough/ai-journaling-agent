"""Tests for inbox message management."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_journaling_agent.core.inbox import InboxMessage, JsonInboxRepository, generate_message_id


class TestInboxMessage:
    """InboxMessage serialization round-trips correctly."""

    def test_to_dict_and_from_dict(self) -> None:
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        msg = InboxMessage(
            id="1710493200000_abcd1234",
            user_id="U1234",
            text="今日は良い日だった",
            received_at=now,
            status="pending",
        )
        data = msg.to_dict()
        restored = InboxMessage.from_dict(data)
        assert restored.id == msg.id
        assert restored.user_id == msg.user_id
        assert restored.text == msg.text
        assert restored.received_at == now
        assert restored.status == "pending"


class TestGenerateMessageId:
    """generate_message_id produces sortable IDs."""

    def test_chronological_order(self) -> None:
        t1 = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        t2 = datetime(2026, 3, 15, 9, 0, 1, tzinfo=UTC)
        id1 = generate_message_id(t1)
        id2 = generate_message_id(t2)
        assert id1 < id2


class TestJsonInboxRepository:
    """JsonInboxRepository persists and manages inbox messages."""

    def test_save_and_list_pending(self, tmp_path: Path) -> None:
        repo = JsonInboxRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        msg = InboxMessage(
            id="001_abc",
            user_id="U1234",
            text="テスト",
            received_at=now,
            status="pending",
        )
        repo.save(msg)

        pending = repo.list_pending()
        assert len(pending) == 1
        assert pending[0].id == "001_abc"
        assert pending[0].text == "テスト"

    def test_list_pending_empty(self, tmp_path: Path) -> None:
        repo = JsonInboxRepository(tmp_path)
        assert repo.list_pending() == []

    def test_list_pending_sorted_chronologically(self, tmp_path: Path) -> None:
        repo = JsonInboxRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)

        repo.save(InboxMessage("002_b", "U1", "second", now, "pending"))
        repo.save(InboxMessage("001_a", "U1", "first", now, "pending"))
        repo.save(InboxMessage("003_c", "U1", "third", now, "pending"))

        pending = repo.list_pending()
        assert [m.id for m in pending] == ["001_a", "002_b", "003_c"]

    def test_mark_processed_moves_file(self, tmp_path: Path) -> None:
        repo = JsonInboxRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)
        msg = InboxMessage("001_abc", "U1234", "テスト", now, "pending")
        repo.save(msg)

        repo.mark_processed("001_abc")

        # No longer in pending
        assert repo.list_pending() == []

        # File exists in processed directory
        processed_path = tmp_path / "inbox" / "processed" / "001_abc.json"
        assert processed_path.exists()

    def test_mark_processed_nonexistent_is_noop(self, tmp_path: Path) -> None:
        repo = JsonInboxRepository(tmp_path)
        # Should not raise
        repo.mark_processed("nonexistent")

    def test_multiple_messages_mixed_status(self, tmp_path: Path) -> None:
        repo = JsonInboxRepository(tmp_path)
        now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=UTC)

        repo.save(InboxMessage("001", "U1", "first", now, "pending"))
        repo.save(InboxMessage("002", "U1", "second", now, "pending"))
        repo.mark_processed("001")

        pending = repo.list_pending()
        assert len(pending) == 1
        assert pending[0].id == "002"
