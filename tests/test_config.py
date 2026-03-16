"""Tests for Settings configuration module."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_journaling_agent.core.config import Settings


class TestSettingsRequired:
    """Required fields must be provided."""

    def test_missing_channel_secret_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LINE_CHANNEL_SECRET", raising=False)
        monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_valid_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINE_CHANNEL_SECRET", "test-secret")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
        settings = Settings()  # type: ignore[call-arg]
        assert settings.line_channel_secret == "test-secret"
        assert settings.line_channel_access_token == "test-token"


class TestSettingsDefaults:
    """Default values are applied correctly."""

    def test_default_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINE_CHANNEL_SECRET", "s")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "t")
        settings = Settings()  # type: ignore[call-arg]
        assert settings.port == 8000

    def test_default_storage_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINE_CHANNEL_SECRET", "s")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "t")
        settings = Settings()  # type: ignore[call-arg]
        assert settings.storage_dir == Path.home() / ".ai-journaling-agent" / "data"


class TestSettingsOverride:
    """Environment variables override defaults."""

    def test_override_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINE_CHANNEL_SECRET", "s")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "t")
        monkeypatch.setenv("PORT", "9999")
        settings = Settings()  # type: ignore[call-arg]
        assert settings.port == 9999

    def test_override_storage_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINE_CHANNEL_SECRET", "s")
        monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "t")
        monkeypatch.setenv("STORAGE_DIR", "/tmp/test-data")
        settings = Settings()  # type: ignore[call-arg]
        assert settings.storage_dir == Path("/tmp/test-data")
