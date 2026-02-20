"""Application configuration and environment loading."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Centralized runtime settings."""

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    max_sources: int = int(os.getenv("MAX_SOURCES", "8"))
    recent_months_window: int = int(os.getenv("RECENT_MONTHS_WINDOW", "12"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))


settings = Settings()
