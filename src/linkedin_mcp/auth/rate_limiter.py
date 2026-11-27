"""Daily action rate limiter to protect the authenticated LinkedIn account."""

import datetime
import json
import logging
from typing import Any, Dict, Optional

from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.rate_limiter")


class RateLimiter:
    """Tracks and enforces per-day action quotas in ~/.linkedin_mcp/rate_limits.json."""

    ACTION_LIMITS_MAP = {
        "invite": lambda: config.max_daily_invites,
        "message": lambda: config.max_daily_messages,
        "post": lambda: config.max_daily_posts,
        "comment": lambda: config.max_daily_comments,
    }

    def _today(self) -> str:
        return datetime.date.today().isoformat()

    def _load(self) -> Dict[str, Any]:
        today = self._today()
        if config.rate_limits_file.exists():
            try:
                data = json.loads(config.rate_limits_file.read_text(encoding="utf-8"))
                if data.get("date") == today and isinstance(data.get("counts"), dict):
                    return data
            except Exception as e:
                logger.warning(f"Failed to read rate limits file: {e}")
        return {"date": today, "counts": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        config.rate_limits_file.parent.mkdir(parents=True, exist_ok=True)
        config.rate_limits_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def check_and_increment(self, action: str, dry_run: bool = False) -> Optional[Dict[str, Any]]:
        """Check whether action is within daily quota; increment if allowed and not dry_run."""
        limit_fn = self.ACTION_LIMITS_MAP.get(action)
        if limit_fn is None:
            return None

        limit = limit_fn()
        if limit <= 0:
            return None

        data = self._load()
        current = int(data["counts"].get(action, 0))
        if current >= limit:
            return {
                "success": False,
                "error": "RATE_LIMIT_EXCEEDED",
                "action": action,
                "daily_limit": limit,
                "used_today": current,
                "message": (
                    f"Daily safety limit reached for '{action}' ({current}/{limit}). "
                    "This guardrail protects your LinkedIn account from automated-activity restrictions."
                ),
            }

        if not dry_run:
            data["counts"][action] = current + 1
            self._save(data)
        return None

    def get_usage(self) -> Dict[str, Any]:
        """Return today's usage and configured limits."""
        data = self._load()
        return {
            "date": data["date"],
            "usage": {
                action: {
                    "used": int(data["counts"].get(action, 0)),
                    "limit": limit_fn(),
                }
                for action, limit_fn in self.ACTION_LIMITS_MAP.items()
            },
        }


rate_limiter = RateLimiter()
