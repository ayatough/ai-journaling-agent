"""Response generation for journal entries."""

from __future__ import annotations

from ai_journaling_agent.core.journal import EntryLevel, JournalEntry


def generate_response(entry: JournalEntry) -> str:
    """Generate an encouraging reply based on the journal entry.

    Never returns an empty string.
    """
    if entry.level == EntryLevel.EMOJI:
        emoji = entry.emoji or "✨"
        return f"{emoji} を記録しました！"

    if entry.level == EntryLevel.STRUCTURED:
        parts: list[str] = []
        if entry.achievements:
            parts.append(f"達成 {len(entry.achievements)}件")
        if entry.gratitude:
            parts.append(f"感謝 {len(entry.gratitude)}件")
        if entry.learnings:
            parts.append(f"学び {len(entry.learnings)}件")
        detail = "、".join(parts) if parts else "内容"
        return f"記録しました！（{detail}）素晴らしいですね！"

    # SUMMARY
    summary = entry.summary or ""
    if len(summary) > 20:
        summary = summary[:20] + "…"
    return f"記録しました！「{summary}」"
