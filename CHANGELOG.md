# Changelog

## [0.2.0] - 2026-11-27

### Security Hardening
- **Authenticated HTTP/SSE Transports:** Added `BearerAuthMiddleware` (`src/linkedin_mcp/auth/http_auth.py`) requiring a Bearer token (`Authorization: Bearer <token>` or `?token=<token>`) on `/mcp` and `/sse` endpoints, with persistent auto-generated tokens in `~/.linkedin_mcp/auth_token` (or `LINKEDIN_MCP_AUTH_TOKEN`) and restricted CORS origins (`LINKEDIN_MCP_ALLOWED_ORIGINS`).
- **Encrypted Session Storage at Rest:** Added Fernet encryption (`src/linkedin_mcp/auth/crypto.py`) for `storage_state.json` using `~/.linkedin_mcp/.session.key` (or `LINKEDIN_MCP_ENCRYPTION_KEY`), with automatic migration of legacy plaintext session files.
- **Daily Action Rate Limiting:** Added `RateLimiter` (`src/linkedin_mcp/auth/rate_limiter.py`) enforcing configurable daily caps on connection invites (`20`), direct messages (`30`), posts (`10`), and comments (`25`).
- **`dry_run` Safety Gate & Prompt-Injection Framing:** Added `dry_run=True` preview mode to `create_post`, `create_poll`, `comment_on_post`, `send_message`, `send_connection_request`, and `repost_with_thoughts`, plus untrusted-content security notices on external read tools (`src/linkedin_mcp/auth/safety.py`).

### Architecture Improvements
- **Warm Browser Context & Concurrency Lock:** Refactored `BrowserManager` (`src/linkedin_mcp/browser/engine.py`) to guard context/tab lifecycle with `asyncio.Lock`, reuse a warm persistent `BrowserContext` across tool calls, open/close lightweight tabs per call, and shut down automatically after idle timeout (`LINKEDIN_BROWSER_IDLE_TIMEOUT_S`).
- **Stealth & Environment Alignment:** Wired `playwright-stealth` into `apply_stealth`, added `human_move_and_click` in `src/linkedin_mcp/browser/stealth.py`, and replaced hardcoded `UTC` timezone with configurable `LINKEDIN_TIMEZONE_ID`.
- **Resilient Selectors & Checkpoint Detection:** Added centralized ARIA-first selector chains (`src/linkedin_mcp/browser/selectors.py`) and `detect_checkpoint` (`src/linkedin_mcp/browser/checkpoint.py`) to surface LinkedIn security checkpoints, CAPTCHAs, and platform limits cleanly.

### New Features (9 New Tools — 39 Total)
- **Jobs (`src/linkedin_mcp/tools/jobs.py`):** `search_jobs`, `get_job_details`, `save_job`
- **Company & Content (`src/linkedin_mcp/tools/browsing.py`, `posts.py`):** `view_company`, `search_posts`, `react_to_post`, `repost_with_thoughts`
- **Network Hygiene (`src/linkedin_mcp/tools/network.py`):** `withdraw_connection_request`, `endorse_skill`

### Testing
- Added `tests/test_security_and_features.py` covering HTTP Bearer auth, Fernet encryption & migration, rate limiting, `dry_run` mode, warm context reuse, checkpoint detection, and new tool boundaries (25 total unit tests passing).
