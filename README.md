# Universal LinkedIn MCP Server

[![Model Context Protocol](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tools: 39](https://img.shields.io/badge/tools-39%20available-green.svg)](#available-mcp-tools-39-tools)
[![CI](https://github.com/ChimbuezeDavidbackup/linkedin-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/ChimbuezeDavidbackup/linkedin-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Model Context Protocol (MCP) server that connects AI assistants (Claude, Grok, Cursor, Windsurf, Antigravity) to your LinkedIn account using your local Google Chrome browser, encrypted session storage, and strict `/in/me` account-boundary guardrails.

---

## Prerequisites

1. **Google Chrome** installed on your machine.
2. **Python 3.10+** ([python.org/downloads](https://www.python.org/downloads/)).
3. **`uv`** package runner:
   - **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Step 1: One-Time Login

Log in once interactively so your encrypted session is saved to `~/.linkedin_mcp`:

```bash
uvx --from git+https://github.com/ChimbuezeDavidbackup/linkedin-mcp python -c "import asyncio; from linkedin_mcp.tools.auth import linkedin_start_login; asyncio.run(linkedin_start_login())"
```

1. A Google Chrome window opens to LinkedIn's login page.
2. Sign in and complete any 2FA or verification prompt.
3. Once your feed loads, your encrypted session is saved and the browser closes automatically.

---

## Step 2: Connect Your AI Client

### Option A: Desktop AI Clients (`stdio` via `uvx`)

Add the following `linkedin` server entry to your client's MCP config:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavidbackup/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

**Where to paste this config:**
* **Claude Desktop:**
  * Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  * macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  * Linux: `~/.config/Claude/claude_desktop_config.json`
* **Antigravity:** Settings → MCP (`mcp_config.json`)
* **Cursor:** `.cursor/mcp.json` (project) or global MCP settings
* **Windsurf:** `~/.codeium/windsurf/mcp_config.json`

**Claude Code CLI:**
```bash
claude mcp add linkedin -- uvx --from git+https://github.com/ChimbuezeDavidbackup/linkedin-mcp linkedin-mcp
```

---

### Option B: Cloud Web AI (Grok.com / Streamable HTTP)

Remote web clients need a public HTTPS URL with Bearer token authentication:

```bash
git clone https://github.com/ChimbuezeDavidbackup/linkedin-mcp.git
cd linkedin-mcp
```

* **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\run_for_grok.ps1
  ```
* **macOS / Linux:**
  ```bash
  # Terminal 1: Start Streamable HTTP server
  uv run linkedin-mcp --transport streamable-http --port 8765

  # Terminal 2: Expose via Cloudflare Tunnel
  cloudflared tunnel --url http://127.0.0.1:8765
  ```

In **[grok.com/connectors](https://grok.com/connectors)**, add a Custom MCP Server using the tunnel URL and the Bearer token printed in your terminal (stored in `~/.linkedin_mcp/auth_token`):
* **URL:** `https://<your-tunnel>.trycloudflare.com/mcp?token=<YOUR_AUTH_TOKEN>` *(or pass `Authorization: Bearer <YOUR_AUTH_TOKEN>`)*

> [!TIP]
> Always use `/mcp` (Streamable HTTP) rather than `/sse` when tunneling through Cloudflare quick tunnels.

---

### Option C: Local Development

```bash
git clone https://github.com/ChimbuezeDavidbackup/linkedin-mcp.git
cd linkedin-mcp
uv sync
```

Point your MCP client to your local checkout:
```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": ["--directory", "<ABSOLUTE_PATH_TO_LINKEDIN_MCP>", "run", "linkedin-mcp"]
    }
  }
}
```

---

## Configuration (Optional Environment Variables)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LINKEDIN_MCP_DATA_DIR` | `~/.linkedin_mcp` | Directory for encrypted session, keys, and rate limits. |
| `LINKEDIN_HEADLESS` | `true` | Run Chrome headlessly (`false` to watch browser actions). |
| `LINKEDIN_BROWSER_CHANNEL` | `chrome` | Browser channel passed to Playwright. |
| `LINKEDIN_BROWSER_IDLE_TIMEOUT_S` | `300` | Seconds before idle warm browser context closes. |
| `LINKEDIN_TIMEZONE_ID` | *(host default)* | Optional browser timezone override. |
| `LINKEDIN_MCP_AUTH_TOKEN` | *(auto-generated)* | Bearer token required for HTTP/SSE transports. |
| `LINKEDIN_MCP_ALLOWED_ORIGINS` | `https://grok.com,https://x.com` | Comma-separated allowed CORS origins. |
| `LINKEDIN_MAX_DAILY_INVITES` | `20` | Daily cap for `send_connection_request`. |
| `LINKEDIN_MAX_DAILY_MESSAGES` | `30` | Daily cap for `send_message`. |
| `LINKEDIN_MAX_DAILY_POSTS` | `10` | Daily cap for posts, polls, and reposts. |
| `LINKEDIN_MAX_DAILY_COMMENTS` | `25` | Daily cap for `comment_on_post`. |

---

## Available MCP Tools (39 Tools)

All tools enforce `@require_auth` and operate strictly within your authenticated account.

| Category | Tool Name | Key Arguments | Description |
| :--- | :--- | :--- | :--- |
| **Auth & Session** | `check_login_status` | *(none)* | Checks session validity, active identity, and sliding-window health. |
| | `start_login` | `timeout_seconds` | Opens Chrome for interactive sign-in and 2FA. |
| | `logout` | *(none)* | Clears stored session credentials, cookies, and cached identity. |
| | `refresh_session` | *(none)* | Runs a silent heartbeat to renew LinkedIn's 30-day session window. |
| **Self-Profile** | `get_my_profile` | *(none)* | Reads your authenticated profile details. |
| *(Locked to `/in/me`)* | `update_my_headline` | `headline` | Updates your profile headline. |
| | `update_my_about` | `summary` | Updates your About summary. |
| | `add_education` | `school`, `degree`, `field_of_study`, `start_year`, `end_year`, ... | Adds an education entry. |
| | `add_experience` | `title`, `company`, `employment_type`, `location`, `description`, ... | Adds a work experience entry. |
| | `add_skill` | `skill_name` | Adds a skill to your profile. |
| | `add_project` | `title`, `description`, `url`, `start_year`, `end_year` | Adds a project to your profile. |
| | `update_job_preferences` | `job_titles`, `location_types`, `locations`, `employment_types` | Updates "Open to work" preferences. |
| | `update_my_services` | `services_to_add`, `services_to_remove`, `description` | Updates your Services section. |
| **Browsing & Search** | `search_people` | `keywords`, `location`, `current_company`, `limit` | Searches LinkedIn members with connection degree badges. |
| | `view_profile` | `profile_url` | Reads a member's profile (read-only). |
| | `view_company` | `company_url` | Reads a LinkedIn Company Page (overview, industry, size, HQ). |
| **Jobs & Careers** | `search_jobs` | `keywords`, `location`, `remote_filter`, `experience_level`, `limit` | Searches LinkedIn Jobs with workplace and level filters. |
| | `get_job_details` | `job_url` | Extracts full job description and metadata. |
| | `save_job` | `job_url` | Bookmarks a job to your Saved Jobs list. |
| **Feed, Posts & Polls** | `get_feed` | `limit` | Reads recent posts from your home feed. |
| | `read_post` | `post_url`, `include_comments`, `comment_limit` | Reads a post or Pulse article by URL (read-only). |
| | `search_posts` | `keywords`, `sort_by`, `limit` | Searches LinkedIn posts by keyword or hashtag. |
| | `create_post` | `text`, `media_path`, `dry_run` | Publishes a post (supports image/PDF attachment and `dry_run`). |
| | `create_poll` | `question`, `options`, `duration`, `dry_run` | Publishes a poll (2–4 options, supports `dry_run`). |
| | `comment_on_post` | `post_url`, `comment_text`, `dry_run` | Comments on a post (supports `dry_run`). |
| | `react_to_post` | `post_url`, `reaction_type` | Reacts to a post (`like`, `celebrate`, `support`, `love`, `insightful`, `funny`). |
| | `repost_with_thoughts` | `post_url`, `commentary`, `dry_run` | Reposts with commentary (supports `dry_run`). |
| **Analytics** | `get_post_analytics` | `limit` | Fetches impressions, reactions, and comments for your recent posts. |
| | `get_profile_views` | *(none)* | Fetches profile view counts and viewer demographics. |
| **Messaging** | `list_conversations` | `limit` | Lists recent inbox conversation threads. |
| | `get_conversation_messages` | `recipient_name`, `limit` | Reads message history for a specific conversation. |
| | `send_message` | `recipient_profile_url`, `message_text`, `dry_run` | Sends a direct message (supports `dry_run`). |
| **Network** | `send_connection_request` | `profile_url`, `custom_note`, `dry_run` | Sends a connection invite (supports `dry_run`). |
| | `get_pending_invitations` | *(none)* | Lists pending incoming connection invitations. |
| | `manage_invitation` | `sender_name`, `action` | Accepts or ignores a pending invitation. |
| | `withdraw_connection_request` | `profile_url` | Withdraws a pending outgoing invitation. |
| | `endorse_skill` | `profile_url`, `skill_name` | Endorses a skill on a 1st-degree connection's profile. |
| **Agentic Skills** | `get_network_briefing` | `limit` | Generates a digest of inbox, invitations, analytics, and feed trends. |
| | `analyze_profile_strength` | *(none)* | Audits profile completeness and suggests improvements. |

---

## Security & Privacy

* **No Password Storage:** Authentication is interactive via Chrome; passwords are never read or stored.
* **Encrypted Local State:** `storage_state.json` is encrypted at rest with Fernet (`~/.linkedin_mcp/.session.key`).
* **Authenticated Remote Access:** HTTP/SSE transports require a Bearer token and restrict CORS origins.
* **Safety Guardrails:** Self-profile edits are hard-locked to `/in/me/`, high-risk actions support `dry_run=True` and daily rate limits, and external read responses include untrusted-content notices.

---

## Testing

```bash
uv run python -m unittest discover tests
```

---

## Changelog & License

* See [CHANGELOG.md](CHANGELOG.md) for release notes (`v0.2.0` and earlier).
* Licensed under the [MIT License](LICENSE). Authored by [Chimbueze (David) Okoroji](https://github.com/ChimbuezeDavidbackup).
