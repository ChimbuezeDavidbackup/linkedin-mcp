"""Feed and post tools published strictly as the authenticated user."""

import logging
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.stealth import human_delay, human_scroll, human_type
from linkedin_mcp.config import config

logger = logging.getLogger("linkedin_mcp.tools.posts")

_ALLOWED_POST_HOSTS = {"www.linkedin.com", "linkedin.com", "lnkd.in"}
_POST_PATH_PREFIXES = ("/posts/", "/feed/update/", "/pulse/")
_POST_URN_MARKERS = ("urn:li:activity:", "urn:li:ugcpost:")


def _validate_and_normalize_post_url(
    post_url: str,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Validate and normalize a LinkedIn post URL for strictly read-only access."""
    if not post_url or not post_url.strip():
        return None, {
            "success": False,
            "error": "EMPTY_URL",
            "message": "Post URL cannot be empty.",
        }

    raw = post_url.strip()
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urllib.parse.urlparse(candidate)

    if parsed.scheme not in ("http", "https"):
        return None, {
            "success": False,
            "error": "INVALID_POST_URL",
            "message": "Only http/https LinkedIn post URLs are allowed.",
        }

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_POST_HOSTS:
        return None, {
            "success": False,
            "error": "INVALID_POST_URL",
            "message": "Only linkedin.com and lnkd.in post URLs are allowed.",
        }

    path_lower = parsed.path.lower()
    if host == "lnkd.in":
        if not parsed.path.strip("/"):
            return None, {
                "success": False,
                "error": "INVALID_POST_URL",
                "message": "lnkd.in shortlink must include a path.",
            }
    else:
        is_post_path = any(path_lower.startswith(p) for p in _POST_PATH_PREFIXES)
        has_post_urn = any(m in path_lower for m in _POST_URN_MARKERS)
        if not (is_post_path or has_post_urn):
            return None, {
                "success": False,
                "error": "INVALID_POST_URL",
                "message": (
                    "URL must point to a LinkedIn post, activity update, "
                    "or Pulse article (/posts/, /feed/update/, /pulse/)."
                ),
            }

    normalized = urllib.parse.urlunparse(
        ("https", host, parsed.path, parsed.params, parsed.query, "")
    )
    return normalized, None


def _is_linkedin_host(url: str) -> bool:
    """Return True if the URL's host is linkedin.com or a subdomain."""
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host == "linkedin.com" or host.endswith(".linkedin.com")


@require_auth
async def create_post(
    text: str,
    media_path: Optional[str] = None,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Publish a new post on LinkedIn authored exclusively by your authenticated profile.

    Args:
        text: The content of your post.
        media_path: Optional absolute file path to an image (.png, .jpg, .jpeg) or document (.pdf) to attach.

    Returns:
        Status result indicating whether the post was successfully published.
    """
    if not text or not text.strip():
        return {"success": False, "error": "EMPTY_POST", "message": "Post text cannot be empty."}

    content = text.strip()
    media_file: Optional[Path] = None

    if media_path:
        media_file = Path(media_path)
        if not media_file.is_file():
            return {
                "success": False,
                "error": "MEDIA_NOT_FOUND",
                "message": f"Attached media file does not exist at: {media_path}"
            }

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.feed_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Look for "Start a post" button
        start_post_btn = page.locator(
            "button:has-text('Start a post'), "
            "button.share-box-feed-entry__trigger, "
            "button[aria-label*='Start a post']"
        ).first

        if await start_post_btn.count() == 0:
            return {
                "success": False,
                "error": "TRIGGER_NOT_FOUND",
                "message": "Could not find the 'Start a post' button on your feed."
            }

        await start_post_btn.click()
        await human_delay(1.5, 2.5)

        # If attaching media, trigger file upload before or after typing
        if media_file:
            file_input = page.locator("input[type='file']").first
            if await file_input.count() > 0:
                try:
                    await file_input.set_input_files(str(media_file.resolve()))
                    await human_delay(2.0, 3.5)
                    # If an artdeco modal has a 'Next' or 'Done' button for the media
                    next_btn = page.locator(
                        "div.share-box-footer button:has-text('Next'), "
                        "button.share-box-footer__primary-btn:has-text('Next'), "
                        "button:has-text('Done')"
                    ).first
                    if await next_btn.count() > 0 and await next_btn.is_visible():
                        await next_btn.click()
                        await human_delay(1.5, 2.5)
                except Exception as e:
                    logger.warning(f"Failed to attach media: {e}")

        # Locate editor modal
        editor = page.locator(
            "div.ql-editor[contenteditable='true'], "
            "div[role='textbox'][aria-label*='post' i], "
            "div.editor-content div[contenteditable='true']"
        ).first

        if await editor.count() == 0:
            return {
                "success": False,
                "error": "EDITOR_NOT_FOUND",
                "message": "Could not locate the post text editor modal."
            }

        await editor.click()
        await human_delay(0.5, 1.0)
        # Type the post content
        await editor.fill(content)
        await human_delay(1.5, 2.5)

        # Click the Post button
        post_btn = page.locator(
            "button.share-actions__primary-action, "
            "button:has-text('Post'):not([disabled]), "
            "div.share-box_actions button.artdeco-button--primary"
        ).first

        if await post_btn.count() == 0 or not await post_btn.is_enabled():
            return {
                "success": False,
                "error": "POST_BUTTON_DISABLED",
                "message": "Post button was not enabled or could not be found."
            }

        await post_btn.click()
        await human_delay(3.0, 5.0)

        return {
            "success": True,
            "boundary": f"Published as {account_identity.name if account_identity else 'authenticated user'}",
            "message": "Post successfully published to your LinkedIn feed.",
            "post_preview": content[:140] + ("..." if len(content) > 140 else ""),
            "attached_media": str(media_file) if media_file else None
        }


@require_auth
async def create_poll(
    question: str,
    options: List[str],
    duration: str = "1 week",
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Create and publish an interactive poll to your LinkedIn feed.

    Args:
        question: The poll question text (max 140 characters).
        options: List of poll options (between 2 and 4 options, each max 30 chars).
        duration: Poll duration ('1 day', '3 days', '1 week', or '2 weeks'). Default is '1 week'.

    Returns:
        Status result of the poll publication.
    """
    if not question or not question.strip():
        return {"success": False, "error": "EMPTY_QUESTION", "message": "Poll question cannot be empty."}

    if not options or len(options) < 2:
        return {"success": False, "error": "INSUFFICIENT_OPTIONS", "message": "Poll must have at least 2 options."}

    if len(options) > 4:
        return {"success": False, "error": "TOO_MANY_OPTIONS", "message": "Poll cannot have more than 4 options."}

    cleaned_options = [opt.strip()[:30] for opt in options if opt and opt.strip()]
    if len(cleaned_options) < 2:
        return {"success": False, "error": "INVALID_OPTIONS", "message": "At least 2 non-empty options are required."}

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.feed_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        start_post_btn = page.locator("button:has-text('Start a post'), button[aria-label*='Start a post']").first
        if await start_post_btn.count() == 0:
            return {"success": False, "error": "TRIGGER_NOT_FOUND", "message": "Could not find 'Start a post' button."}

        await start_post_btn.click()
        await human_delay(1.5, 2.5)

        # Look for Poll trigger icon or button inside modal
        poll_btn = page.locator("button[aria-label*='Create a poll' i], button:has-text('Create a poll')").first
        if await poll_btn.count() == 0:
            # Check more options button inside share box
            more_btn = page.locator("button[aria-label*='Add to your post' i], button[aria-label*='More' i]").first
            if await more_btn.count() > 0:
                await more_btn.click()
                await human_delay(0.8, 1.5)
                poll_btn = page.locator("button:has-text('Create a poll'), button[aria-label*='poll' i]").first

        if await poll_btn.count() == 0:
            return {"success": False, "error": "POLL_OPTION_NOT_FOUND", "message": "Poll creation tool not available in post editor."}

        await poll_btn.click()
        await human_delay(1.5, 2.5)

        # Fill question
        question_input = page.locator("input#poll-question-input, input[name='question'], textarea[placeholder*='question' i]").first
        if await question_input.count() > 0:
            await question_input.fill(question.strip()[:140])
            await human_delay(0.5, 1.0)

        # Fill options 1 & 2
        option_inputs = page.locator("input[id*='poll-option'], input[name*='option']")
        if await option_inputs.count() >= 2:
            await option_inputs.nth(0).fill(cleaned_options[0])
            await human_delay(0.3, 0.6)
            await option_inputs.nth(1).fill(cleaned_options[1])
            await human_delay(0.3, 0.6)

        # Add remaining options if provided
        for opt_idx in range(2, len(cleaned_options)):
            add_opt_btn = page.locator("button:has-text('+ Add option'), button:has-text('Add option')").first
            if await add_opt_btn.count() > 0:
                await add_opt_btn.click()
                await human_delay(0.5, 1.0)
                new_inputs = page.locator("input[id*='poll-option'], input[name*='option']")
                if await new_inputs.count() > opt_idx:
                    await new_inputs.nth(opt_idx).fill(cleaned_options[opt_idx])
                    await human_delay(0.3, 0.6)

        # Done button inside poll modal
        done_btn = page.locator("button:has-text('Done'), div.poll-footer button.artdeco-button--primary").first
        if await done_btn.count() > 0:
            await done_btn.click()
            await human_delay(1.5, 2.5)

        # Final Post button
        post_btn = page.locator("button.share-actions__primary-action, button:has-text('Post'):not([disabled])").first
        if await post_btn.count() > 0 and await post_btn.is_enabled():
            await post_btn.click()
            await human_delay(3.0, 5.0)

        return {
            "success": True,
            "boundary": f"Published as {account_identity.name if account_identity else 'authenticated user'}",
            "message": "Poll published successfully to your LinkedIn feed.",
            "question": question.strip()[:140],
            "options": cleaned_options,
            "duration": duration
        }


@require_auth
async def get_feed(
    limit: int = 5,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Read recent posts from your personal LinkedIn feed.

    Args:
        limit: Number of posts to retrieve (default: 5, max: 15).

    Returns:
        List of feed posts with author name, headline, post text, and links.
    """
    limit = max(1, min(limit, 15))

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(config.feed_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)
        await human_scroll(page, scrolls=2, distance=400)

        posts = []
        post_elements = page.locator("div.feed-shared-update-v2, div[data-urn*='activity']")
        count = min(await post_elements.count(), limit)

        for i in range(count):
            elem = post_elements.nth(i)
            try:
                # Author
                author = ""
                author_elem = elem.locator("span.feed-shared-actor__name, span.update-components-actor__name").first
                if await author_elem.count() > 0:
                    author = (await author_elem.inner_text()).strip()

                # Author description / headline
                author_headline = ""
                sub_elem = elem.locator("span.feed-shared-actor__description, span.update-components-actor__description").first
                if await sub_elem.count() > 0:
                    author_headline = (await sub_elem.inner_text()).strip()

                # Post text content
                text = ""
                text_elem = elem.locator("div.feed-shared-update-v2__description, div.update-components-text").first
                if await text_elem.count() > 0:
                    text = (await text_elem.inner_text()).strip()

                if author or text:
                    posts.append({
                        "author": author,
                        "author_headline": author_headline,
                        "content": text[:500] + ("..." if len(text) > 500 else ""),
                    })
            except Exception as e:
                logger.debug(f"Error parsing feed item {i}: {e}")

        # Modern LinkedIn feed fallback
        if not posts:
            modern_posts = await page.evaluate("""(maxCount) => {
                const likeButtons = Array.from(document.querySelectorAll('button')).filter(b => {
                    const t = (b.innerText || '').trim();
                    return t === 'Like';
                });
                const out = [];
                const seen = new Set();
                for (const btn of likeButtons) {
                    if (out.length >= maxCount) break;
                    let container = btn;
                    for (let i = 0; i < 7; i++) {
                        if (container.parentElement) container = container.parentElement;
                        if (container.tagName === 'DIV' && container.innerText.includes('Like') && container.innerText.includes('Comment')) {
                            const authorLink = container.querySelector('a[href*="/in/"], a[href*="/company/"]');
                            if (authorLink && !seen.has(container)) {
                                seen.add(container);
                                const lines = container.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                                const author = authorLink.innerText.trim().split('\\n')[0];
                                const textLines = lines.filter(l => !['Like', 'Comment', 'Repost', 'Send', 'Promoted', author].includes(l));
                                out.push({
                                    author: author || 'LinkedIn Member',
                                    author_headline: '',
                                    content: textLines.slice(0, 4).join(' ').slice(0, 500)
                                });
                                break;
                            }
                        }
                    }
                }
                return out;
            }""", limit)
            if modern_posts:
                posts.extend(modern_posts)

        return {
            "success": True,
            "boundary": f"Viewed from {account_identity.name if account_identity else 'authenticated'}'s feed",
            "count": len(posts),
            "posts": posts
        }


@require_auth
async def comment_on_post(
    post_url: str,
    comment_text: str,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Leave a comment on a LinkedIn post as the authenticated user.

    Args:
        post_url: The URL of the LinkedIn post.
        comment_text: The comment text to post.

    Returns:
        Status result of the comment operation.
    """
    if not comment_text or not comment_text.strip():
        return {"success": False, "error": "EMPTY_COMMENT", "message": "Comment cannot be empty."}

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(post_url.strip(), wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        # Find comment box
        comment_box = page.locator("div.comments-comment-box__editor, div.ql-editor[aria-label*='comment' i]").first
        if await comment_box.count() == 0:
            # Click the comment trigger button first if collapsed
            trigger = page.locator("button[aria-label*='Comment' i]").first
            if await trigger.count() > 0:
                await trigger.click()
                await human_delay(1.0, 2.0)
                comment_box = page.locator("div.comments-comment-box__editor, div.ql-editor").first

        if await comment_box.count() == 0:
            return {"success": False, "error": "COMMENT_BOX_NOT_FOUND", "message": "Could not locate the comment input box."}

        await comment_box.click()
        await comment_box.fill(comment_text.strip())
        await human_delay(1.0, 2.0)

        # Click submit
        submit_btn = page.locator("button.comments-comment-box__submit-button:not([disabled])").first
        if await submit_btn.count() == 0:
            return {"success": False, "error": "SUBMIT_NOT_FOUND", "message": "Could not find active submit button."}

        await submit_btn.click()
        await human_delay(2.0, 3.5)

        return {
            "success": True,
            "boundary": f"Commented as {account_identity.name if account_identity else 'authenticated user'}",
            "message": "Comment successfully submitted.",
            "comment": comment_text.strip()
        }


async def _extract_post_from_page(page: Any) -> Dict[str, Any]:
    """Extract structured post or Pulse article content from a loaded LinkedIn page."""
    # Expand truncated post body if a read-only 'see more' button is present
    see_more_btn = page.locator(
        "button.feed-shared-inline-show-more-text__see-more-less-toggle, "
        "button[aria-label*='see more' i], "
        "button:has-text('…more'), "
        "button:has-text('...more')"
    ).first
    try:
        if await see_more_btn.count() > 0 and await see_more_btn.is_visible():
            await see_more_btn.click()
            await human_delay(0.5, 1.0)
    except Exception as e:
        logger.debug(f"Could not expand 'see more' toggle: {e}")

    # Handle LinkedIn Pulse articles (/pulse/...)
    if "/pulse/" in page.url.lower():
        article = await page.evaluate("""() => {
            const titleEl = document.querySelector('h1');
            const authorEl = document.querySelector('a[href*="/in/"], a[href*="/company/"]');
            const bodyEl = document.querySelector('article, div.reader-article-content, main');
            const links = Array.from((bodyEl || document).querySelectorAll('a[href^="http"]'))
                .map(a => a.href)
                .filter(h => h && !h.includes('linkedin.com/signup') && !h.includes('linkedin.com/login'));
            return {
                author: authorEl ? authorEl.innerText.trim().split('\\n')[0] : '',
                author_url: authorEl ? authorEl.href.split('?')[0] : '',
                author_headline: '',
                published_at: '',
                title: titleEl ? titleEl.innerText.trim() : '',
                content: bodyEl ? bodyEl.innerText.trim() : '',
                embedded_links: Array.from(new Set(links)).slice(0, 15),
                media_type: 'article',
                engagement: { reactions: '', comments: '', reposts: '' }
            };
        }""")
        return article

    # Standard LinkedIn post container
    container = page.locator("div.feed-shared-update-v2, div[data-urn*='activity']").first
    if await container.count() > 0:
        data = await container.evaluate("""(el) => {
            const pickText = (selectors) => {
                for (const sel of selectors) {
                    const node = el.querySelector(sel);
                    if (node && node.innerText && node.innerText.trim()) {
                        return node.innerText.trim();
                    }
                }
                return '';
            };

            const authorLink = el.querySelector(
                'a.update-components-actor__meta-link, a.feed-shared-actor__container-link, a[href*="/in/"], a[href*="/company/"]'
            );
            const author = pickText([
                'span.update-components-actor__name span[aria-hidden="true"]',
                'span.update-components-actor__name',
                'span.feed-shared-actor__name',
            ]) || (authorLink ? authorLink.innerText.trim().split('\\n')[0] : '');

            const authorHeadline = pickText([
                'span.update-components-actor__description span[aria-hidden="true"]',
                'span.update-components-actor__description',
                'span.feed-shared-actor__description',
            ]);

            const publishedAt = pickText([
                'span.update-components-actor__sub-description span[aria-hidden="true"]',
                'span.update-components-actor__sub-description',
                'span.feed-shared-actor__sub-description',
            ]).split('\\n')[0].trim();

            const content = pickText([
                'div.update-components-text',
                'div.feed-shared-update-v2__description',
                'span.break-words',
            ]);

            const reactions = pickText([
                'span.social-details-social-counts__reactions-count',
                'button[aria-label*="reaction" i]',
            ]);
            const comments = pickText([
                'li.social-details-social-counts__comments button',
                'button[aria-label*="comment" i]',
            ]);
            const reposts = pickText([
                'li.social-details-social-counts__item--with-social-proof button',
                'button[aria-label*="repost" i]',
            ]);

            const links = Array.from(el.querySelectorAll('div.update-components-text a[href^="http"], div.update-components-article a[href^="http"], div.feed-shared-update-v2__description a[href^="http"]'))
                .map(a => a.href)
                .filter(Boolean);

            let mediaType = 'text';
            if (el.querySelector('div.update-components-poll, form.update-components-poll')) mediaType = 'poll';
            else if (el.querySelector('div.update-components-document, iframe[src*="document"]')) mediaType = 'document';
            else if (el.querySelector('video, div.update-components-linkedin-video')) mediaType = 'video';
            else if (el.querySelector('div.update-components-article')) mediaType = 'article';
            else if (el.querySelector('div.update-components-image img, div.feed-shared-image img')) mediaType = 'image';

            return {
                author,
                author_url: authorLink ? authorLink.href.split('?')[0] : '',
                author_headline: authorHeadline,
                published_at: publishedAt,
                title: '',
                content,
                embedded_links: Array.from(new Set(links)).slice(0, 15),
                media_type: mediaType,
                engagement: {
                    reactions: reactions || '0',
                    comments: comments || '0',
                    reposts: reposts || '0',
                }
            };
        }""")
        if data.get("content") or data.get("author"):
            return data

    # Modern LinkedIn DOM fallback (isolates the post card, excluding the left profile sidebar)
    return await page.evaluate("""() => {
        const isSidebar = (el) => {
            const t = el.innerText || '';
            return t.includes('Profile viewers') && t.includes('View all analytics');
        };

        // Locate the post card by walking up from the 'Like' action button
        let postRoot = null;
        const likeBtn = Array.from(document.querySelectorAll('button')).find(
            b => (b.innerText || '').trim() === 'Like'
        );
        if (likeBtn) {
            let cur = likeBtn;
            for (let i = 0; i < 8; i++) {
                if (!cur.parentElement) break;
                cur = cur.parentElement;
                const txt = cur.innerText || '';
                if (txt.includes('Like') && txt.includes('Comment') && !isSidebar(cur)) {
                    const hasAuthor = cur.querySelector('a[href*="/in/"], a[href*="/company/"]');
                    if (hasAuthor) {
                        postRoot = cur;
                        break;
                    }
                }
            }
        }

        const main = postRoot || document.querySelector('main') || document.body;

        let rawText = (main.innerText || '').trim();
        // If we fell back to full <main>, slice from 'Feed post' to drop the left sidebar
        const feedPostIdx = rawText.indexOf('Feed post');
        if (feedPostIdx !== -1) {
            rawText = rawText.slice(feedPostIdx + 'Feed post'.length).trim();
        }

        const lines = rawText.split('\\n').map(l => l.trim()).filter(Boolean);
        const uiNoise = new Set(['Feed post', 'Follow', 'Connect', 'Like', 'Comment', 'Repost', 'Send', 'Add a comment…', 'Add a comment...']);

        // Extract author, headline, and published_at from the header lines
        let author = '';
        let authorHeadline = '';
        let publishedAt = '';
        let bodyStartIdx = 0;

        for (let i = 0; i < Math.min(lines.length, 8); i++) {
            const line = lines[i];
            if (!author && !line.startsWith('•') && !uiNoise.has(line)) {
                author = line;
                bodyStartIdx = i + 1;
                continue;
            }
            if (author && line === author) {
                bodyStartIdx = i + 1;
                continue;
            }
            if (/^•\\s*(1st|2nd|3rd\\+?|Following)/.test(line)) {
                bodyStartIdx = i + 1;
                continue;
            }
            if (/^\\d+[smhdwyo]\\b/.test(line) && line.includes('•')) {
                publishedAt = line.replace(/•\\s*$/, '').trim();
                bodyStartIdx = i + 1;
                break;
            }
            if (!authorHeadline && i > 0 && !uiNoise.has(line) && !line.startsWith('•')) {
                authorHeadline = line;
                bodyStartIdx = i + 1;
            }
        }

        // Resolve authorUrl by skipping the sidebar and matching the post author
        const feedHeading = Array.from(main.querySelectorAll('h1, h2, h3, span, p, div')).find(
            el => el.childElementCount === 0 && (el.innerText || '').trim() === 'Feed post'
        );
        const candidateLinks = Array.from(main.querySelectorAll('a[href*="/in/"], a[href*="/company/"]')).filter(a => {
            let p = a.parentElement;
            for (let i = 0; i < 6 && p; i++) {
                if (isSidebar(p)) return false;
                p = p.parentElement;
            }
            if (feedHeading && !(feedHeading.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING)) {
                return false;
            }
            return true;
        });

        const authorLower = author.toLowerCase();
        const matchedLink = (authorLower
            ? candidateLinks.find(a => (a.innerText || '').toLowerCase().includes(authorLower))
            : null) || candidateLinks[0] || null;

        let authorUrl = matchedLink ? matchedLink.href.split('?')[0] : '';
        if (!authorUrl) {
            const m = window.location.pathname.match(/^\\/posts\\/([^_/]+)_/);
            if (m && m[1]) {
                authorUrl = `https://www.linkedin.com/in/${m[1]}/`;
            }
        }

        // Collect body lines until the action bar / comments section
        const bodyLines = [];
        for (let i = bodyStartIdx; i < lines.length; i++) {
            const line = lines[i];
            if (line === 'Like' || line === 'Add a comment…' || line === 'Add a comment...') break;
            if (uiNoise.has(line)) continue;
            bodyLines.push(line);
        }

        const links = Array.from(main.querySelectorAll('a[href^="http"]'))
            .map(a => a.href)
            .filter(h => h && !h.includes('linkedin.com/in/') && !h.includes('linkedin.com/company/'));

        return {
            author,
            author_url: authorUrl,
            author_headline: authorHeadline,
            published_at: publishedAt,
            title: '',
            content: bodyLines.join('\\n').slice(0, 8000),
            embedded_links: Array.from(new Set(links)).slice(0, 15),
            media_type: 'text',
            engagement: { reactions: '', comments: '', reposts: '' }
        };
    }""")


async def _extract_post_comments(page: Any, limit: int) -> List[Dict[str, str]]:
    """Extract top visible comments from a post page in strictly read-only mode."""
    await human_scroll(page, scrolls=2, distance=400)
    return await page.evaluate("""(maxComments) => {
        const items = document.querySelectorAll(
            'article.comments-comment-entity, article.comments-comment-item, div.comments-comment-item'
        );
        const out = [];
        for (const item of items) {
            if (out.length >= maxComments) break;
            const authorEl = item.querySelector(
                'span.comments-comment-meta__description-title, span.comments-post-meta__name-text'
            );
            const headlineEl = item.querySelector(
                'div.comments-comment-meta__description-subtitle, span.comments-post-meta__headline'
            );
            const textEl = item.querySelector(
                'span.comments-comment-item__main-content, div.comments-comment-item-content-body'
            );
            const text = textEl ? textEl.innerText.trim() : '';
            if (text) {
                out.push({
                    author: authorEl ? authorEl.innerText.trim() : 'LinkedIn Member',
                    headline: headlineEl ? headlineEl.innerText.trim() : '',
                    text,
                });
            }
        }
        return out;
    }""", limit)


@require_auth
async def read_post(
    post_url: str,
    include_comments: bool = False,
    comment_limit: int = 5,
    account_identity: AccountIdentity = None
) -> Dict[str, Any]:
    """Read a specific LinkedIn post or Pulse article by its URL within your authenticated session.

    Strictly read-only: never likes, comments, reposts, or mutates any profile or post.

    Args:
        post_url: LinkedIn post URL (/posts/..., /feed/update/..., /pulse/..., or lnkd.in/...).
        include_comments: Whether to also extract top visible comments (default: False).
        comment_limit: Maximum number of comments to return when include_comments is True (default: 5, max: 20).

    Returns:
        Structured post content, author metadata, embedded links, engagement counts, and optional comments.
    """
    normalized_url, validation_error = _validate_and_normalize_post_url(post_url)
    if validation_error:
        return validation_error

    clamped_comment_limit = max(1, min(comment_limit, 20))

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(normalized_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        final_url = page.url
        if not _is_linkedin_host(final_url):
            return {
                "success": False,
                "error": "EXTERNAL_REDIRECT_BLOCKED",
                "message": "The link redirected outside linkedin.com and was blocked.",
            }

        lower_url = final_url.lower()
        if "authwall" in lower_url or "/login" in lower_url:
            return {
                "success": False,
                "error": "AUTHWALL",
                "message": "LinkedIn redirected to an authwall. Post may be private or session expired.",
            }

        if "checkpoint" in lower_url:
            return {
                "success": False,
                "error": "CHECKPOINT_CHALLENGE",
                "message": "LinkedIn presented a security checkpoint. Please verify via start_login.",
            }

        post_data = await _extract_post_from_page(page)
        if not post_data.get("content") and not post_data.get("author"):
            return {
                "success": False,
                "error": "POST_NOT_FOUND",
                "message": "Could not extract post content. The post may have been deleted or is unavailable.",
            }

        comments: List[Dict[str, str]] = []
        if include_comments:
            comments = await _extract_post_comments(page, clamped_comment_limit)

        result: Dict[str, Any] = {
            "success": True,
            "read_only": True,
            "boundary": f"Viewed as {account_identity.name if account_identity else 'authenticated user'}",
            "post_url": final_url,
            "author": post_data.get("author", ""),
            "author_url": post_data.get("author_url", ""),
            "author_headline": post_data.get("author_headline", ""),
            "published_at": post_data.get("published_at", ""),
            "media_type": post_data.get("media_type", "text"),
            "content": post_data.get("content", ""),
            "embedded_links": post_data.get("embedded_links", []),
            "engagement": post_data.get("engagement", {}),
        }
        if post_data.get("title"):
            result["title"] = post_data["title"]
        if include_comments:
            result["comments"] = comments
            result["comment_count_returned"] = len(comments)

        return result
