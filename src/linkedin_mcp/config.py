"""Configuration settings for LinkedIn MCP server."""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


def _parse_csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings(BaseModel):
    """Global configuration settings."""

    # Storage paths
    data_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("LINKEDIN_MCP_DATA_DIR", Path.home() / ".linkedin_mcp")
        )
    )

    # Session files
    @property
    def storage_state_file(self) -> Path:
        """Path to Playwright storage state (encrypted at rest)."""
        return self.data_dir / "storage_state.json"

    @property
    def account_identity_file(self) -> Path:
        """Path to cached authenticated account identity info."""
        return self.data_dir / "account_identity.json"

    @property
    def browser_profile_dir(self) -> Path:
        """Persistent browser profile directory."""
        return self.data_dir / "browser_profile"

    @property
    def session_key_file(self) -> Path:
        """Path to local Fernet key file for encrypting session state at rest."""
        return self.data_dir / ".session.key"

    @property
    def auth_token_file(self) -> Path:
        """Path to persistent Bearer token for HTTP/SSE transports."""
        return self.data_dir / "auth_token"

    @property
    def rate_limits_file(self) -> Path:
        """Path to daily action rate-limit counters."""
        return self.data_dir / "rate_limits.json"

    # Browser automation settings
    browser_channel: Optional[str] = Field(
        default_factory=lambda: os.getenv("LINKEDIN_BROWSER_CHANNEL", "chrome")
    )
    headless: bool = Field(
        default_factory=lambda: os.getenv("LINKEDIN_HEADLESS", "true").lower()
        in ("1", "true", "yes")
    )
    slow_mo_ms: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_SLOW_MO_MS", "50"))
    )
    timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_TIMEOUT_MS", "30000"))
    )
    browser_idle_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_BROWSER_IDLE_TIMEOUT_S", "300"))
    )
    timezone_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("LINKEDIN_TIMEZONE_ID") or None
    )

    # HTTP / Transport security settings
    mcp_auth_token: Optional[str] = Field(
        default_factory=lambda: os.getenv("LINKEDIN_MCP_AUTH_TOKEN") or None
    )
    allowed_origins: List[str] = Field(
        default_factory=lambda: _parse_csv_env(
            "LINKEDIN_MCP_ALLOWED_ORIGINS",
            ["https://grok.com", "https://x.com"],
        )
    )

    # Daily safety rate limits
    max_daily_invites: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_MAX_DAILY_INVITES", "20"))
    )
    max_daily_messages: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_MAX_DAILY_MESSAGES", "30"))
    )
    max_daily_posts: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_MAX_DAILY_POSTS", "10"))
    )
    max_daily_comments: int = Field(
        default_factory=lambda: int(os.getenv("LINKEDIN_MAX_DAILY_COMMENTS", "25"))
    )

    # URLs
    base_url: str = "https://www.linkedin.com"
    login_url: str = "https://www.linkedin.com/login"
    feed_url: str = "https://www.linkedin.com/feed/"
    my_profile_url: str = "https://www.linkedin.com/in/me/"

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.browser_profile_dir.mkdir(parents=True, exist_ok=True)


config = Settings()
config.ensure_directories()
