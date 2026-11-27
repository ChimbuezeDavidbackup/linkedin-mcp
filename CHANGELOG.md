# Changelog

## [0.2.0] - 2026-11-27

### New Features (9 New Tools — 39 Total)
- **Jobs & Careers:** `search_jobs`, `get_job_details`, and `save_job` for searching listings with workplace/level filters, reading full descriptions, and bookmarking jobs.
- **Company & Content:** `view_company`, `search_posts`, `react_to_post` (`like`, `celebrate`, `support`, `love`, `insightful`, `funny`), and `repost_with_thoughts`.
- **Network Hygiene:** `withdraw_connection_request` and `endorse_skill`.

### Security & Safety
- **Authenticated HTTP/SSE Transports:** Remote `/mcp` and `/sse` endpoints now require a Bearer token (`~/.linkedin_mcp/auth_token` or `LINKEDIN_MCP_AUTH_TOKEN`) and restrict CORS to configured origins (`LINKEDIN_MCP_ALLOWED_ORIGINS`).
- **Encrypted Session Storage:** Saved session cookies (`storage_state.json`) are encrypted at rest with Fernet, with automatic migration for existing plaintext sessions.
- **Daily Action Rate Limits:** Configurable daily caps protect your account on connection invites (`20`), direct messages (`30`), posts (`10`), and comments (`25`).
- **`dry_run` Previews & Content Notices:** Added `dry_run=True` to high-impact mutation tools (`create_post`, `create_poll`, `comment_on_post`, `send_message`, `send_connection_request`, `repost_with_thoughts`) and untrusted-content notices on external read responses.

### Performance & Reliability
- **Warm Browser Context:** Reuses a single lock-guarded Chrome session across tool calls with lightweight per-call tabs and automatic idle shutdown, cutting latency and preventing profile lock conflicts.
- **Improved Stealth & Checkpoint Detection:** Integrated `playwright-stealth`, smooth mouse movement, configurable timezone alignment, resilient ARIA-first selectors, and early detection of LinkedIn checkpoints/CAPTCHAs.
- **Testing:** Expanded the unit test suite from 15 to 25 passing tests.
