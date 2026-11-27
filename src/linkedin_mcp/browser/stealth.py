"""Stealth enhancements and humanized interaction utilities for Playwright."""

import asyncio
import random
from playwright.async_api import Page, Locator


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


async def apply_stealth(page: Page) -> None:
    """Apply playwright-stealth (when available) and baseline navigator hardening."""
    try:
        from playwright_stealth import stealth_async
        await stealth_async(page)
    except Exception:
        pass

    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)


async def human_delay(min_seconds: float = 1.0, max_seconds: float = 2.5) -> None:
    """Introduce a randomized delay to simulate human pauses."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


async def human_move_and_click(page: Page, locator: Locator) -> None:
    """Move the mouse smoothly toward a locator's bounding box before clicking."""
    try:
        box = await locator.bounding_box()
        if box:
            target_x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
            target_y = box["y"] + box["height"] * random.uniform(0.25, 0.75)
            await page.mouse.move(target_x, target_y, steps=random.randint(8, 16))
            await human_delay(0.05, 0.18)
    except Exception:
        pass
    await locator.click()


async def human_type(
    locator: Locator,
    text: str,
    min_delay_ms: int = 30,
    max_delay_ms: int = 80,
    clear_first: bool = True
) -> None:
    """Type text into an input field with randomized keypress intervals."""
    if clear_first:
        await locator.click()
        await locator.press("ControlOrMeta+a")
        await locator.press("Backspace")
        await human_delay(0.2, 0.5)

    for char in text:
        await locator.type(char)
        delay = random.uniform(min_delay_ms, max_delay_ms) / 1000.0
        await asyncio.sleep(delay)


async def human_scroll(page: Page, scrolls: int = 2, distance: int = 400) -> None:
    """Perform smooth, human-like scrolling down the page."""
    for _ in range(scrolls):
        actual_distance = distance + random.randint(-50, 50)
        await page.mouse.wheel(0, actual_distance)
        await human_delay(0.8, 1.5)
