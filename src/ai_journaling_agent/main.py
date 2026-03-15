"""Webhook server entrypoint.

Usage::

    uv run python -m ai_journaling_agent.main
"""

from __future__ import annotations

import uvicorn

from ai_journaling_agent.adapters.line.bot import create_app
from ai_journaling_agent.core.config import Settings

settings = Settings()  # type: ignore[call-arg]
app = create_app(settings)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
