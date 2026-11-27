"""Centralized, resilient LinkedIn selector chains with ARIA-first fallbacks."""

from typing import Optional, Sequence
from playwright.async_api import Locator, Page


async def first_visible(
    root: Page | Locator,
    selectors: Sequence[str],
    timeout_ms: int = 2500,
) -> Optional[Locator]:
    """Return the first locator in `selectors` that exists and is visible."""
    for sel in selectors:
        loc = root.locator(sel).first
        try:
            if await loc.count() > 0:
                await loc.wait_for(state="visible", timeout=timeout_ms)
                return loc
        except Exception:
            continue
    return None


SELECTORS = {
    "start_post_button": [
        "button[aria-label*='Start a post' i]",
        "button:has-text('Start a post')",
        "button.share-box-feed-entry__trigger",
    ],
    "post_editor": [
        "div.ql-editor[contenteditable='true']",
        "div[role='textbox'][contenteditable='true']",
    ],
    "connect_button": [
        "main button[aria-label*='Invite' i][aria-label*='connect' i]",
        "main button:has-text('Connect')",
        "div.pvs-profile-actions button:has-text('Connect')",
    ],
    "message_button": [
        "main button[aria-label*='Message' i]",
        "main button:has-text('Message')",
        "div.entry-point button:has-text('Message')",
    ],
    "more_actions_button": [
        "main button[aria-label*='More actions' i]",
        "main button:has-text('More')",
    ],
    "job_search_cards": [
        "li.jobs-search-results__list-item",
        "div.job-card-container",
        "li[data-occludable-job-id]",
    ],
    "company_about_section": [
        "section.org-about-module",
        "section:has-text('Overview')",
    ],
}
