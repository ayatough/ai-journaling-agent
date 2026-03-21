"""Extract profile updates from journal entries using AI."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from ai_journaling_agent.core.user_profile import UserProfile

_EXTRACT_PROMPT = """以下のユーザーメッセージを読んで、このユーザーの特徴を抽出してください。

メッセージ: {user_text}

以下のJSON形式で返してください（情報がなければ空リスト/空文字列にしてください）:
{{
  "interests": ["興味・関心のキーワード（最大3つ）"],
  "recurring_themes": ["繰り返し出てくるテーマ（最大3つ）"],
  "communication_style": "コミュニケーションスタイルの特徴（一言で、なければ空文字）"
}}

JSONのみ返してください。説明不要。"""


async def extract_profile_updates(
    user_text: str,
    existing_profile: UserProfile,
    ai_responder: AiResponder,  # noqa: F821
) -> UserProfile:
    """Extract profile info from user_text and merge into existing_profile."""
    from ai_journaling_agent.core.ai_responder import AiResponder  # noqa: F401 (type hint)

    prompt = _EXTRACT_PROMPT.format(user_text=user_text)
    raw = await ai_responder.generate_response(
        existing_profile.user_id, prompt
    )

    try:
        # Extract JSON from response
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            return existing_profile
    except (json.JSONDecodeError, ValueError):
        return existing_profile

    new_interests = [i for i in data.get("interests", []) if i and i not in existing_profile.interests]
    new_themes = [t for t in data.get("recurring_themes", []) if t and t not in existing_profile.recurring_themes]
    style = data.get("communication_style", "")

    updated = UserProfile(
        user_id=existing_profile.user_id,
        interests=existing_profile.interests + new_interests,
        communication_style=style or existing_profile.communication_style,
        recurring_themes=existing_profile.recurring_themes + new_themes,
        updated_at=datetime.now(tz=UTC),
        profile_update_counter=existing_profile.profile_update_counter,
    )
    return updated
