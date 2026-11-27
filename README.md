# Universal LinkedIn MCP Server

[![Model Context Protocol](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tools: 39](https://img.shields.io/badge/tools-39%20available-green.svg)](#-available-mcp-tools-39-tools)
[![CI](https://github.com/ChimbuezeDavid/linkedin-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/ChimbuezeDavid/linkedin-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade Model Context Protocol (MCP) server that connects your AI assistant (Claude, Grok, Cursor, Antigravity) to LinkedIn with **human-like stealth browser automation**, **mathematical account boundary guardrails**, and **zero official API restrictions**.

---

## 💡 Why This Exists: The Problem & The Solution

### ❌ The Problem

1. **The Closed API Wall**: LinkedIn's official Developer APIs are gated behind enterprise partner programs (LinkedIn Marketing Developer Platform / LinkedIn Talent Solutions). Solo builders, freelancers, and AI agent developers cannot obtain write access to publish posts, send connection invites, or update profiles programmatically.
2. **The Anti-Bot Ban Trap**: Standard automation tools (Puppeteer, Selenium, raw Chromium binaries) trigger LinkedIn's bot detection checkpoints within minutes. They broadcast `navigator.webdriver = true`, lack persistent cookie management, type at robotic speeds, and fail when presented with 2FA or CAPTCHAs, resulting in instant account restrictions.
3. **The LLM Safety & Prompt-Injection Hazard**: Giving an autonomous LLM browser access is dangerous. Without rigid guardrails, prompt injections can trick an AI into editing unintended accounts, scraping unauthorized targets, or blasting spam across your professional network.
4. **Desktop vs. Cloud AI Fragmentation**: Desktop AI tools (Claude Desktop, Cursor) communicate over local `stdio`, whereas web-based cloud AI (like Grok.com) run on remote servers and cannot access your local browser or session without secure tunneling and CORS support.

### ✅ The Solution

1. **Full 39-Tool Platform Without API Keys**: Provides your AI with complete human capabilities—profile editing, rich posting (with images/PDFs), post & Pulse article reading, post search, reactions & reposts, interactive polls, job search & saving, company research, inbox history, connection management, skill endorsements, analytics, and executive intelligence briefings.
2. **Warm Stealth Chrome Engine**: Uses your computer's real, native Google Chrome installation with a lock-guarded warm `BrowserContext` and tab pooling for low-latency execution. Integrates `playwright-stealth`, human typing delay jitter, smooth mouse movement, and LinkedIn checkpoint/CAPTCHA detection.
3. **Passwordless, Encrypted Session Management**: Never asks for or stores your plaintext LinkedIn password. Session cookies (`storage_state.json`) are encrypted at rest with Fernet (`~/.linkedin_mcp/.session.key`), and built-in keep-alive telemetry extends LinkedIn's 30-day sliding activity window automatically.
4. **Mathematical Account Boundaries & Safety Guardrails**: Profile mutation tools (`update_my_headline`, `update_my_about`, `add_experience`, etc.) **do not accept a target profile parameter**. They are hardcoded to `/in/me`. High-impact actions support `dry_run=True` previews and daily rate-limiting caps.
5. **Universal Multi-Transport Architecture**: Runs locally via `stdio` using zero-clone `uvx`, or remotely via `streamable-http` / `sse` with Bearer token authentication, restricted CORS, and a 1-click Cloudflare Tunnel script for Grok.com.

---

## 📋 Prerequisites

Before setting up, make sure your computer has:

1. **Google Chrome**: Installed and functioning normally.
2. **Python 3.10 or higher**: [python.org/downloads](https://www.python.org/downloads/)
3. **`uv` (Fast Python Package Runner)**:
   - **Windows (PowerShell)**:
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - **macOS / Linux**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

---

## ⚡ Step 1: One-Time Interactive Authentication

You only need to log in **once**. The server saves your session state to `~/.linkedin_mcp` so your AI assistants remain authenticated across restarts.

Open your terminal and run:

```bash
uvx --from git+https://github.com/ChimbuezeDavid/linkedin-mcp python -c "import asyncio; from linkedin_mcp.tools.auth import linkedin_start_login; asyncio.run(linkedin_start_login())"
```

### What happens:
1. A real Google Chrome browser window will open automatically.
2. Enter your LinkedIn credentials and complete 2FA / verification if prompted.
3. Once your LinkedIn home feed loads, the tool automatically verifies your identity, saves your encrypted cookies, and closes the browser.
4. Your terminal will display: `Active session verified for <Your Name>`.

---

## 🔌 Step 2: Connect to Your AI Assistant

Choose your setup below based on whether you are using a **Desktop AI Client** (Claude, Cursor, Antigravity) or a **Cloud Web AI** (Grok.com).

---

### Option A: Desktop AI Clients (Zero-Clone via `uvx`)

You do **not** need to download or clone this repository. Your AI client will execute it directly using `uvx`.

#### 1. Claude Desktop
Add this snippet to your `claude_desktop_config.json`:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavid/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 2. Antigravity
Open your Antigravity MCP settings (`mcp_config.json` or Settings > MCP):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavid/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 3. Cursor & Windsurf
Add to `.cursor/mcp.json` or your global Cursor settings:

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ChimbuezeDavid/linkedin-mcp",
        "linkedin-mcp"
      ]
    }
  }
}
```

#### 4. Claude Code CLI
Run directly from your terminal:

```bash
claude mcp add linkedin uvx --from git+https://github.com/ChimbuezeDavid/linkedin-mcp linkedin-mcp
```

---

### Option B: Cloud Web-Based AI (Grok.com)

Cloud-based AI assistants (like **grok.com/connectors**) cannot connect to `localhost`. They need a public, encrypted tunnel with CORS and Streamable HTTP support.

We include a pre-configured 1-click startup script that starts the MCP server in Streamable HTTP mode on port `8765` and launches a Cloudflare Tunnel.

#### Step 1: Run the Grok Connector Script
Clone the repository and run the script:

```bash
git clone https://github.com/ChimbuezeDavid/linkedin-mcp.git
cd linkedin-mcp
```

- **On Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\run_for_grok.ps1
  ```
- **On macOS / Linux**:
  ```bash
  # Terminal 1: Launch MCP server in Streamable HTTP mode
  uv run linkedin-mcp --transport streamable-http --port 8765

  # Terminal 2: Expose via Cloudflare Tunnel
  cloudflared tunnel --url http://127.0.0.1:8765
  ```

#### Step 2: Configure Grok.com
1. Copy the public tunnel URL and Bearer token displayed in your terminal (the token is persisted in `~/.linkedin_mcp/auth_token`, or set via `LINKEDIN_MCP_AUTH_TOKEN`).
2. Go to **[grok.com/connectors](https://grok.com/connectors)** in your browser.
3. Click **Add Custom MCP Server**:
   - **Name**: `LinkedIn MCP`
   - **URL**: `https://example-subdomain.trycloudflare.com/mcp?token=<YOUR_AUTH_TOKEN>` *(or pass `Authorization: Bearer <YOUR_AUTH_TOKEN>` header; always append `/mcp` before query params)*
4. Click **Save** and start chatting with Grok!

> [!TIP]
> **Why `/mcp` instead of `/sse`?** Cloudflare quick tunnels do not support persistent Server-Sent Events (SSE) due to proxy buffering, but work seamlessly with Streamable HTTP (`/mcp`). The server includes built-in CORS middleware to ensure seamless communication with `grok.com`.

---

### Option C: Local Development Setup

If you want to contribute or modify the codebase locally:

```bash
git clone https://github.com/ChimbuezeDavid/linkedin-mcp.git
cd linkedin-mcp
uv sync
```

To configure your AI client to point to your local code:
```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": [
        "--directory",
        "<ABSOLUTE_PATH_TO_LINKEDIN_MCP>",
        "run",
        "linkedin-mcp"
      ]
    }
  }
}
```

---

## 🛠️ Available MCP Tools (39 Tools)

All tools operate strictly within the authenticated account boundary and enforce `@require_auth`.

| Category | Tool Name | Key Arguments | Description |
| :--- | :--- | :--- | :--- |
| **Auth & Keep-Alive** | `check_login_status` | *(none)* | Inspects session validity, active account identity, and sliding-window age. |
| | `start_login` | `timeout_seconds` | Opens an interactive Chrome window for 1-click sign-in and 2FA. |
| | `logout` | *(none)* | Clears stored session tokens, local cookies, and cached profile data. |
| | `refresh_session` | *(none)* | Performs a silent heartbeat to extend the 30-day session sliding window. |
| **Self-Profile** | `get_my_profile` | *(none)* | Retrieves your authenticated profile details (name, headline, bio, experience). |
| *(Hard-Locked to `/in/me`)* | `update_my_headline` | `headline` | Updates your headline under your name. |
| | `update_my_about` | `summary` | Updates your About / bio summary text. |
| | `add_education` | `school`, `degree`, `field_of_study`, `start_year`, `end_year`, ... | Adds an academic credential to your profile. |
| | `add_experience` | `title`, `company`, `employment_type`, `location`, `description`, ... | Adds a job or role to your Experience section. |
| | `add_skill` | `skill_name` | Adds a skill to your Skills section (with suggestion auto-selection). |
| | `add_project` | `title`, `description`, `url`, `start_year`, `end_year` | Adds a project to your Projects section. |
| | `update_job_preferences` | `job_titles`, `location_types`, `locations`, `employment_types` | Configures "Open to work" career preferences. |
| | `update_my_services` | `services_to_add`, `services_to_remove`, `description` | Updates client services and offerings on your profile. |
| **Browsing & Search** | `search_people` | `keywords`, `location`, `current_company`, `limit` | Searches LinkedIn for professionals with connection degree badges (1st/2nd/3rd). |
| | `view_profile` | `profile_url` | Reads any member's public/network profile details in read-only mode. |
| | `view_company` | `company_url` | Reads a LinkedIn Company Page (overview, tagline, industry, size, HQ). |
| **Jobs & Careers** | `search_jobs` | `keywords`, `location`, `remote_filter`, `experience_level`, `limit` | Searches LinkedIn Jobs with workplace and experience-level filters. |
| | `get_job_details` | `job_url` | Extracts full job description and metadata for a job posting. |
| | `save_job` | `job_url` | Bookmarks a LinkedIn job posting to your Saved Jobs list. |
| **Feed, Posts & Polls** | `get_feed` | `limit` | Reads recent posts from your personal home feed. |
| | `read_post` | `post_url`, `include_comments`, `comment_limit` | Reads a specific LinkedIn post or Pulse article by URL in read-only mode. |
| | `search_posts` | `keywords`, `sort_by`, `limit` | Searches LinkedIn posts by keyword or hashtag. |
| | `create_post` | `text`, `media_path`, `dry_run` | Publishes a post authored by your account, optionally attaching image/PDF. |
| | `create_poll` | `question`, `options`, `duration`, `dry_run` | Publishes an interactive poll to your feed (2-4 options, custom duration). |
| | `comment_on_post` | `post_url`, `comment_text`, `dry_run` | Comments on a post as your authenticated profile. |
| | `react_to_post` | `post_url`, `reaction_type` | Reacts to a post (`like`, `celebrate`, `support`, `love`, `insightful`, `funny`). |
| | `repost_with_thoughts` | `post_url`, `commentary`, `dry_run` | Reposts an existing post with your own commentary. |
| **Analytics & Insights** | `get_post_analytics` | `limit` | Retrieves impressions, reactions, and comments for your recent posts. |
| | `get_profile_views` | *(none)* | Retrieves private profile view counts and viewer demographics. |
| **Direct Messaging** | `list_conversations` | `limit` | Lists recent direct message threads in your inbox. |
| | `get_conversation_messages` | `recipient_name`, `limit` | Reads complete message history and replies for a specific thread. |
| | `send_message` | `recipient_profile_url`, `message_text`, `dry_run` | Dispatches a direct message from your account. |
| **Network Growth** | `send_connection_request` | `profile_url`, `custom_note`, `dry_run` | Sends a connection invitation with an optional personalized note. |
| | `get_pending_invitations` | *(none)* | Lists incoming connection invitations received by your account. |
| | `manage_invitation` | `sender_name`, `action` | Accepts or ignores a pending connection invitation. |
| | `withdraw_connection_request` | `profile_url` | Withdraws a pending outgoing connection invitation. |
| | `endorse_skill` | `profile_url`, `skill_name` | Endorses a specific skill on a 1st-degree connection's profile. |
| **Agentic Skills** | `get_network_briefing` | `limit` | Generates a daily executive digest: inbox, invitations, analytics & feed trends. |
| | `analyze_profile_strength` | *(none)* | Audits completeness across 6 sections and gives an actionable score & tips. |

---

## 🧪 Automated Testing & Verification

The repository includes a comprehensive unit test suite verifying boundary constraints, security invariants, parameter validation, and session health calculation:

```bash
uv run python -m unittest discover tests
```

Expected output:
```
Ran 25 tests in 0.142s

OK
```

---

## 🔒 Security & Privacy Invariants

- **Zero Plaintext Password Exposure**: The server never prompts for, reads, or stores your LinkedIn password.
- **Encrypted Local Storage**: Session cookies (`storage_state.json`) are encrypted at rest with Fernet (`~/.linkedin_mcp/.session.key`), and all state remains strictly on your local machine at `~/.linkedin_mcp`.
- **Authenticated Remote Transports**: `streamable-http` and `sse` endpoints require a Bearer token (`~/.linkedin_mcp/auth_token` or `LINKEDIN_MCP_AUTH_TOKEN`) and restrict CORS to configured origins (`LINKEDIN_MCP_ALLOWED_ORIGINS`).
- **Daily Rate-Limiting & `dry_run` Mode**: Built-in daily quotas protect against automated-activity bans, and high-impact mutation tools support `dry_run=True` previews before execution.
- **Mathematical Impossibility of Impersonation**: Self-profile editing tools are hard-coded to navigate to `/in/me/`. There is no `target_profile_url` parameter, preventing prompt-injected LLMs from altering other members' profiles.

---

## 📝 Update Notes (v0.2.0)

- **Security:** Added HTTP/SSE Bearer token authentication, restricted CORS, Fernet encryption for `storage_state.json`, daily action rate-limiting, `dry_run` preview mode, and untrusted-content notices.
- **Architecture:** Upgraded `BrowserManager` to a lock-guarded warm `BrowserContext` with tab pooling and idle cleanup, integrated `playwright-stealth`, and added centralized ARIA-first selectors + checkpoint/CAPTCHA detection.
- **New Tools (+9, 39 total):** Added `search_jobs`, `get_job_details`, `save_job`, `view_company`, `search_posts`, `react_to_post`, `repost_with_thoughts`, `withdraw_connection_request`, and `endorse_skill`.

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details. Authored with ❤️ by [Chimbueze (David) Okoroji](https://github.com/ChimbuezeDavid).
