# backend/config/settings.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────
    APP_NAME: str = "CI Healer"
    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str

    # ── GitHub OAuth ──────────────────────────────────────
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str

    # ── JWT Session ───────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    # ── AI Engine ─────────────────────────────────────────
    AI_ENGINE_URL: str = "http://localhost:8001"
    AI_ENGINE_TIMEOUT: int = 600
    # How often (seconds) the backend pings the engine to prevent Render idle.
    # 10 minutes keeps both services alive (Render idles after 15 min)
    # while being minimal enough not to interfere with real work.
    AI_ENGINE_KEEPALIVE_INTERVAL: int = 600  # 10 minutes

    # ── CORS — stored as plain str, parsed into list below
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"


    # ── Agent Defaults ────────────────────────────────────
    DEFAULT_MAX_ITERATIONS: int = 5

    # ── SSE ───────────────────────────────────────────────
    SSE_PING_INTERVAL: int = 15

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        """Use this everywhere instead of ALLOWED_ORIGINS directly."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL

        # SQLite — return as-is, no driver swap needed
        if url.startswith("sqlite"):
            return url

        # Postgres URL fixes
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        clean_params = {}
        if "sslmode" in params or "ssl" in params:
            clean_params["ssl"] = "require"
        new_query = urlencode(clean_params)
        return urlunparse(parsed._replace(query=new_query))





    @property
    def sync_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        # Append sslmode=require if not already present (needed for Supabase)
        if "postgresql+psycopg2://" in url and "sslmode" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return url


    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


settings = Settings()
