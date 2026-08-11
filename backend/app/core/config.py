from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from the .env file."""

    # ==============================
    # DATABASE
    # ==============================

    # SQLite by default - this is a standalone tool, no shared Postgres needed.
    DATABASE_URL: str = f"sqlite:///{BACKEND_ROOT / 'youtube_intel.db'}"

    # ==============================
    # YOUTUBE DATA API
    # ==============================

    YOUTUBE_API_KEY: str | None = None
    YOUTUBE_API_BASE_URL: str = "https://www.googleapis.com/youtube/v3"

    # Google's default free-tier daily allowance is 10,000 units; a search
    # call alone costs 100. This is a soft, in-process guard - kept below
    # the real limit so the app fails with a clear message instead of a
    # bare 403 from Google partway through a session.
    YOUTUBE_DAILY_QUOTA_BUDGET: int = 9000

    # ==============================
    # BACKGROUND SNAPSHOT POLLING
    # ==============================

    SNAPSHOT_SYNC_ENABLED: bool = False
    SNAPSHOT_SYNC_INTERVAL_HOURS: int = 6

    # ==============================
    # OAUTH (creator-only analytics)
    # ==============================

    GOOGLE_OAUTH_CLIENT_ID: str | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = None
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8010/oauth/callback"

    # ==============================
    # HTTP CLIENT
    # ==============================

    REQUEST_TIMEOUT: int = 30

    # ==============================
    # APPLICATION
    # ==============================

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5175,http://localhost:5173,http://localhost:5174"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
