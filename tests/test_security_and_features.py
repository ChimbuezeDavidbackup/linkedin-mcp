"""Unit tests for Phase 1 security, Phase 2 browser architecture, and Phase 3 new tools."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from linkedin_mcp.auth import crypto, rate_limiter as rl_mod, session_guard
from linkedin_mcp.auth.http_auth import BearerAuthMiddleware
from linkedin_mcp.browser.checkpoint import detect_checkpoint
from linkedin_mcp.browser.engine import BrowserManager
from linkedin_mcp.config import config
from linkedin_mcp.tools import browsing, jobs, messaging, network, posts


class TestHTTPAuthMiddleware(unittest.TestCase):
    def setUp(self) -> None:
        async def root(request):
            return JSONResponse({"status": "ok"})

        async def mcp_endpoint(request):
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/", root), Route("/mcp", mcp_endpoint, methods=["POST", "GET"])])
        app.add_middleware(BearerAuthMiddleware, token="secret-test-token", public_paths=["/"])
        self.client = TestClient(app)

    def test_public_root_allowed_without_token(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_mcp_requires_bearer_token(self):
        resp = self.client.post("/mcp")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error"], "UNAUTHORIZED")

    def test_mcp_rejects_invalid_token(self):
        resp = self.client.post("/mcp", headers={"Authorization": "Bearer wrong-token"})
        self.assertEqual(resp.status_code, 401)

    def test_mcp_accepts_valid_bearer_header_and_query(self):
        resp_hdr = self.client.post("/mcp", headers={"Authorization": "Bearer secret-test-token"})
        self.assertEqual(resp_hdr.status_code, 200)
        resp_q = self.client.post("/mcp?token=secret-test-token")
        self.assertEqual(resp_q.status_code, 200)


class TestCryptoAndRateLimiter(unittest.TestCase):
    def test_encrypted_storage_roundtrip_and_legacy_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch.object(config, "data_dir", tmp_path):
                state_file = tmp_path / "storage_state.json"
                sample = {"cookies": [{"name": "li_at", "value": "abc123"}]}

                crypto.save_encrypted_json(state_file, sample)
                raw = state_file.read_bytes()
                self.assertTrue(raw.startswith(b"ENC:V1:"))
                self.assertNotIn(b"abc123", raw)

                loaded = crypto.load_encrypted_json(state_file)
                self.assertEqual(loaded, sample)

                # Legacy plaintext migration
                legacy_file = tmp_path / "legacy_state.json"
                legacy_file.write_text(json.dumps(sample), encoding="utf-8")
                migrated = crypto.load_encrypted_json(legacy_file)
                self.assertEqual(migrated, sample)
                self.assertTrue(legacy_file.read_bytes().startswith(b"ENC:V1:"))

    def test_rate_limiter_enforces_daily_cap_and_respects_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with patch.object(config, "data_dir", tmp_path), patch.object(config, "max_daily_invites", 2):
                limiter = rl_mod.RateLimiter()
                # dry_run does not consume quota
                self.assertIsNone(limiter.check_and_increment("invite", dry_run=True))
                self.assertEqual(limiter.get_usage()["usage"]["invite"]["used"], 0)

                self.assertIsNone(limiter.check_and_increment("invite"))
                self.assertIsNone(limiter.check_and_increment("invite"))
                blocked = limiter.check_and_increment("invite")
                self.assertIsNotNone(blocked)
                self.assertFalse(blocked["success"])
                self.assertEqual(blocked["error"], "RATE_LIMIT_EXCEEDED")


class TestDryRunAndNewTools(unittest.TestCase):
    def test_dry_run_mode_on_mutation_tools(self):
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session"):
            res_post = asyncio.run(posts.create_post(text="Hello", dry_run=True))
            self.assertTrue(res_post["success"])
            self.assertTrue(res_post["dry_run"])

            res_poll = asyncio.run(posts.create_poll(question="Q?", options=["A", "B"], dry_run=True))
            self.assertTrue(res_poll["success"])
            self.assertTrue(res_poll["dry_run"])

            res_comment = asyncio.run(posts.comment_on_post(post_url="https://www.linkedin.com/posts/123", comment_text="Nice!", dry_run=True))
            self.assertTrue(res_comment["success"])
            self.assertTrue(res_comment["dry_run"])

            res_msg = asyncio.run(messaging.send_message(recipient_profile_url="https://www.linkedin.com/in/jane", message_text="Hi", dry_run=True))
            self.assertTrue(res_msg["success"])
            self.assertTrue(res_msg["dry_run"])

            res_conn = asyncio.run(network.send_connection_request(profile_url="https://www.linkedin.com/in/jane", custom_note="Hello", dry_run=True))
            self.assertTrue(res_conn["success"])
            self.assertTrue(res_conn["dry_run"])

            res_repost = asyncio.run(posts.repost_with_thoughts(post_url="https://www.linkedin.com/posts/123", commentary="Great read", dry_run=True))
            self.assertTrue(res_repost["success"])
            self.assertTrue(res_repost["dry_run"])

    def test_new_tools_validation_and_auth_boundary(self):
        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session", side_effect=session_guard.UnauthenticatedError("No auth")):
            self.assertEqual(asyncio.run(jobs.search_jobs(keywords="Python"))["boundary_status"], "BLOCKED_UNAUTHENTICATED")
            self.assertEqual(asyncio.run(browsing.view_company(company_url="openai"))["boundary_status"], "BLOCKED_UNAUTHENTICATED")
            self.assertEqual(asyncio.run(network.withdraw_connection_request(profile_url="jane"))["boundary_status"], "BLOCKED_UNAUTHENTICATED")

        with patch("linkedin_mcp.auth.session_guard.ensure_authenticated_session"):
            self.assertEqual(asyncio.run(jobs.get_job_details(job_url="https://example.com/bad"))["error"], "INVALID_JOB_URL")
            self.assertEqual(asyncio.run(posts.react_to_post(post_url="https://www.linkedin.com/posts/123", reaction_type="angry"))["error"], "INVALID_REACTION")
            self.assertEqual(asyncio.run(network.endorse_skill(profile_url="jane", skill_name=""))["error"], "EMPTY_SKILL")


class TestBrowserArchitectureAndCheckpoint(unittest.TestCase):
    def test_warm_context_reused_across_calls(self):
        async def _run():
            mgr = BrowserManager()
            mock_page = MagicMock()
            mock_page.add_init_script = AsyncMock()
            mock_page.close = AsyncMock()

            mock_ctx = MagicMock()
            mock_ctx.new_page = AsyncMock(return_value=mock_page)
            mock_ctx.storage_state = AsyncMock(return_value={"cookies": []})
            mock_ctx.close = AsyncMock()

            mock_pw = MagicMock()
            mock_pw.chromium.launch_persistent_context = AsyncMock(return_value=mock_ctx)
            mock_pw.stop = AsyncMock()

            with patch("linkedin_mcp.browser.engine.async_playwright") as apw, \
                 patch("linkedin_mcp.browser.engine.save_encrypted_json"):
                apw.return_value.start = AsyncMock(return_value=mock_pw)
                async with mgr.get_page(headless=True) as p1:
                    self.assertIs(p1, mock_page)
                async with mgr.get_page(headless=True) as p2:
                    self.assertIs(p2, mock_page)

                # Launched only once for two consecutive calls
                self.assertEqual(mock_pw.chromium.launch_persistent_context.await_count, 1)
                self.assertEqual(mock_page.close.await_count, 2)
                await mgr.close()

        asyncio.run(_run())

    def test_detect_checkpoint_flags_challenge_urls(self):
        async def _run():
            page = MagicMock()
            page.url = "https://www.linkedin.com/checkpoint/challenge/123"
            res = await detect_checkpoint(page)
            self.assertIsNotNone(res)
            self.assertEqual(res["error"], "CHECKPOINT_DETECTED")

            page.url = "https://www.linkedin.com/login"
            res_login = await detect_checkpoint(page)
            self.assertEqual(res_login["error"], "SESSION_EXPIRED")

        asyncio.run(_run())
