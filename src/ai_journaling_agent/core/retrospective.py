"""Retrospective summary generation."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from ai_journaling_agent.core.repository import JournalRepository

if TYPE_CHECKING:
    from ai_journaling_agent.core.ai_responder import AiResponder
    from ai_journaling_agent.core.user_profile import UserProfile

_SUMMARY_PROMPT = """以下は{user_label}のジャーナル記録です。

{entries_text}

これらの記録から、この期間を振り返るサマリーを作成してください。
- 事実ベースで記述してください（評価・判断は加えない）
- できたこと、感謝・嬉しかったこと、学びを自然にまとめてください
- 3〜5文程度で簡潔に
- 締めくくりに一言ポジティブなメッセージを添えてください"""


def _collect_entries_text(repository: JournalRepository, user_id: str, start: date, end: date) -> str:
    lines = []
    current = start
    while current <= end:
        entries = repository.list_entries(user_id, date=current)
        for entry in entries:
            parts = []
            if entry.summary:
                parts.append(entry.summary)
            if entry.achievements:
                parts.extend(f"できたこと: {a}" for a in entry.achievements)
            if entry.gratitude:
                parts.extend(f"感謝: {g}" for g in entry.gratitude)
            if entry.learnings:
                parts.extend(f"学び: {item}" for item in entry.learnings)
            if parts:
                lines.append(f"[{current}] " + " / ".join(parts))
        current += timedelta(days=1)
    return "\n".join(lines) if lines else ""


async def generate_weekly_summary(
    user_id: str,
    week_start: date,
    repository: JournalRepository,
    responder: AiResponder,
    profile: UserProfile | None = None,
) -> str:
    week_end = week_start + timedelta(days=6)
    entries_text = _collect_entries_text(repository, user_id, week_start, week_end)
    if not entries_text:
        return "この週の記録はありませんでした。"
    prompt = _SUMMARY_PROMPT.format(user_label="先週1週間", entries_text=entries_text)
    return await responder.generate_response(user_id, prompt, profile=profile)


async def generate_monthly_summary(
    user_id: str,
    month_start: date,
    repository: JournalRepository,
    responder: AiResponder,
    profile: UserProfile | None = None,
) -> str:
    # Last day of the month
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
    entries_text = _collect_entries_text(repository, user_id, month_start, month_end)
    if not entries_text:
        return "この月の記録はありませんでした。"
    prompt = _SUMMARY_PROMPT.format(user_label="先月1ヶ月", entries_text=entries_text)
    return await responder.generate_response(user_id, prompt, profile=profile)
