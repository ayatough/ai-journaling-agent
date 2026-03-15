"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Required environment variables:
        LINE_CHANNEL_SECRET
        LINE_CHANNEL_ACCESS_TOKEN
    """

    model_config = SettingsConfigDict(env_file=".env")

    line_channel_secret: str
    line_channel_access_token: str
    storage_dir: Path = Field(default=Path.home() / ".ai-journaling-agent" / "data")
    port: int = 8000
    owner_user_id: str = ""
