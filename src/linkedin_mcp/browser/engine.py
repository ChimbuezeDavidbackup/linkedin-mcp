"""Browser engine managing a warm, lock-guarded Playwright BrowserContext and tab pool."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

from linkedin_mcp.auth.crypto import save_encrypted_json
from linkedin_mcp.config import config
from linkedin_mcp.browser.stealth import apply_stealth, DEFAULT_USER_AGENT

logger = logging.getLogger("linkedin_mcp.browser")


class BrowserManager:
    """Manages a warm Playwright persistent context with concurrency locking and idle cleanup."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._context_headless: Optional[bool] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock: Optional[asyncio.Lock] = None
        self._last_used: float = 0.0
        self._idle_task: Optional[asyncio.Task] = None

    def _get_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._lock is None or self._loop != current_loop:
            self._lock = asyncio.Lock()
        return self._lock

    async def get_playwright(self) -> Playwright:
        """Get or start the Playwright instance for the active event loop."""
        current_loop = asyncio.get_running_loop()
        if self._playwright is not None and self._loop != current_loop:
            await self._close_context_unlocked()
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        if self._playwright is None:
            self._playwright = await async_playwright().start()
            self._loop = current_loop
        return self._playwright

    async def _export_encrypted_state(self, context: BrowserContext) -> None:
        """Persist Playwright storage state encrypted at rest."""
        try:
            state = await context.storage_state()
            save_encrypted_json(config.storage_state_file, state)
        except Exception as e:
            logger.debug(f"Could not export encrypted storage state: {e}")

    async def _close_context_unlocked(self) -> None:
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            self._idle_task = None

        if self._context is not None:
            await self._export_encrypted_state(self._context)
            try:
                await self._context.close()
            except Exception as e:
                logger.debug(f"Error closing browser context: {e}")
            self._context = None
            self._context_headless = None

    def _schedule_idle_cleanup(self) -> None:
        timeout = config.browser_idle_timeout_seconds
        if timeout <= 0:
            return
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()

        async def _cleanup_after_idle() -> None:
            try:
                await asyncio.sleep(timeout)
                lock = self._get_lock()
                async with lock:
                    if self._context is not None and (time.monotonic() - self._last_used) >= timeout:
                        logger.info("Closing idle warm browser context.")
                        await self._close_context_unlocked()
            except asyncio.CancelledError:
                pass

        self._idle_task = asyncio.create_task(_cleanup_after_idle())

    async def _ensure_context_unlocked(self, is_headless: bool) -> BrowserContext:
        pw = await self.get_playwright()

        if self._context is not None and self._context_headless != is_headless:
            await self._close_context_unlocked()

        if self._context is None:
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
            launch_kwargs = dict(
                user_data_dir=str(config.browser_profile_dir),
                headless=is_headless,
                slow_mo=config.slow_mo_ms if not is_headless else 0,
                user_agent=DEFAULT_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="en-US",
                args=args,
            )
            if config.timezone_id:
                launch_kwargs["timezone_id"] = config.timezone_id

            if config.browser_channel:
                self._context = await pw.chromium.launch_persistent_context(
                    channel=config.browser_channel,
                    **launch_kwargs,
                )
            else:
                self._context = await pw.chromium.launch_persistent_context(**launch_kwargs)
            self._context_headless = is_headless

        self._last_used = time.monotonic()
        return self._context

    @asynccontextmanager
    async def get_context(
        self,
        headless: Optional[bool] = None,
        use_storage_state: bool = True,
    ) -> AsyncGenerator[BrowserContext, None]:
        """Acquire the lock-guarded persistent browser context."""
        is_headless = config.headless if headless is None else headless
        lock = self._get_lock()
        async with lock:
            context = await self._ensure_context_unlocked(is_headless)
            try:
                yield context
            finally:
                self._last_used = time.monotonic()
                await self._export_encrypted_state(context)
                self._schedule_idle_cleanup()

    @asynccontextmanager
    async def get_page(
        self,
        headless: Optional[bool] = None,
    ) -> AsyncGenerator[Page, None]:
        """Yield a stealth-configured tab from the warm browser context and close the tab afterward."""
        async with self.get_context(headless=headless) as context:
            page = await context.new_page()
            await apply_stealth(page)
            page.set_default_timeout(config.timeout_ms)
            try:
                yield page
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

    async def close(self) -> None:
        """Shutdown warm browser context and Playwright engine."""
        lock = self._get_lock()
        async with lock:
            await self._close_context_unlocked()
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None


browser_manager = BrowserManager()
