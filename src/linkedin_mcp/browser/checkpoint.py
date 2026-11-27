"""Detection of LinkedIn security checkpoints, CAPTCHAs, and platform rate-limit banners."""

from typing import Any, Dict, Optional
from playwright.async_api import Page


async def detect_checkpoint(page: Page) -> Optional[Dict[str, Any]]:
    """Inspect the current page for LinkedIn checkpoints, CAPTCHAs, or invite/action limits.

    Returns a structured error dict if a blocker is detected, otherwise None.
    """
    url = (page.url or "").lower()

    if "/checkpoint/" in url or "/challenge/" in url:
        return {
            "success": False,
            "error": "CHECKPOINT_DETECTED",
            "url": page.url,
            "message": (
                "LinkedIn presented a security checkpoint or verification challenge. "
                "Please run 'start_login' to complete verification interactively."
            ),
        }

    if "/login" in url or "/authwall" in url or "/uas/login" in url:
        return {
            "success": False,
            "error": "SESSION_EXPIRED",
            "url": page.url,
            "message": "Your LinkedIn session is no longer active. Please run 'start_login' to re-authenticate.",
        }

    try:
        captcha = page.locator(
            "iframe[src*='captcha' i], iframe[src*='arkoselabs' i], iframe[src*='recaptcha' i]"
        )
        if await captcha.count() > 0:
            return {
                "success": False,
                "error": "CAPTCHA_REQUIRED",
                "url": page.url,
                "message": (
                    "LinkedIn requested a CAPTCHA challenge. "
                    "Automation has paused; please complete it interactively via 'start_login'."
                ),
            }

        limit_banner = page.locator(
            "text=/weekly invitation limit|reached the weekly limit|temporarily restricted/i"
        )
        if await limit_banner.count() > 0:
            return {
                "success": False,
                "error": "LINKEDIN_LIMIT_REACHED",
                "url": page.url,
                "message": "LinkedIn displayed a weekly or temporary action limit banner. Pausing automation.",
            }
    except Exception:
        pass

    return None
