"""Job search, inspection, and bookmarking tools within the authenticated LinkedIn session."""

import logging
import urllib.parse
from typing import Any, Dict, List

from linkedin_mcp.auth.manager import AccountIdentity
from linkedin_mcp.auth.safety import attach_untrusted_notice
from linkedin_mcp.auth.session_guard import require_auth
from linkedin_mcp.browser.checkpoint import detect_checkpoint
from linkedin_mcp.browser.engine import browser_manager
from linkedin_mcp.browser.selectors import SELECTORS
from linkedin_mcp.browser.stealth import human_delay, human_scroll

logger = logging.getLogger("linkedin_mcp.tools.jobs")

_REMOTE_MAP = {
    "on-site": "1",
    "onsite": "1",
    "remote": "2",
    "hybrid": "3",
}

_EXP_MAP = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid-senior": "4",
    "director": "5",
    "executive": "6",
}


def _normalize_job_url(job_url: str) -> str:
    url = (job_url or "").strip()
    if not url:
        return ""
    if url.isdigit():
        return f"https://www.linkedin.com/jobs/view/{url}/"
    if not url.startswith("http"):
        return f"https://www.linkedin.com/{url.lstrip('/')}"
    return url


@require_auth
async def search_jobs(
    keywords: str,
    location: str = "",
    remote_filter: str = "",
    experience_level: str = "",
    limit: int = 10,
    account_identity: AccountIdentity = None,
) -> Dict[str, Any]:
    """Search LinkedIn Jobs through your authenticated account.

    Args:
        keywords: Job title, skills, or company keywords.
        location: Optional geographical location (e.g. 'United States', 'London').
        remote_filter: Optional workplace type ('on-site', 'remote', 'hybrid').
        experience_level: Optional level ('internship', 'entry', 'associate', 'mid-senior', 'director', 'executive').
        limit: Maximum number of job listings to return (default: 10, max: 25).
    """
    if not keywords or not keywords.strip():
        return {"success": False, "error": "EMPTY_QUERY", "message": "Job search keywords cannot be empty."}

    limit = max(1, min(limit, 25))
    params: Dict[str, str] = {"keywords": keywords.strip()}
    if location and location.strip():
        params["location"] = location.strip()
    if remote_filter and remote_filter.strip().lower() in _REMOTE_MAP:
        params["f_WT"] = _REMOTE_MAP[remote_filter.strip().lower()]
    if experience_level and experience_level.strip().lower() in _EXP_MAP:
        params["f_E"] = _EXP_MAP[experience_level.strip().lower()]

    search_url = f"https://www.linkedin.com/jobs/search/?{urllib.parse.urlencode(params)}"

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(search_url, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        checkpoint = await detect_checkpoint(page)
        if checkpoint:
            return checkpoint

        await human_scroll(page, scrolls=2, distance=350)

        jobs: List[Dict[str, str]] = []
        cards = page.locator(", ".join(SELECTORS["job_search_cards"]))
        total = await cards.count()

        for i in range(min(total, limit)):
            card = cards.nth(i)
            try:
                link_elem = card.locator("a.job-card-container__link, a[href*='/jobs/view/']").first
                title = (await link_elem.inner_text()).strip().split("\n")[0] if await link_elem.count() > 0 else ""
                href = await link_elem.get_attribute("href") if await link_elem.count() > 0 else ""
                job_url = f"https://www.linkedin.com{href.split('?')[0]}" if href and href.startswith("/") else (href or "").split("?")[0]

                company_elem = card.locator(".job-card-container__primary-description, .artdeco-entity-lockup__subtitle").first
                company = (await company_elem.inner_text()).strip() if await company_elem.count() > 0 else ""

                loc_elem = card.locator(".job-card-container__metadata-wrapper li, .artdeco-entity-lockup__caption").first
                job_location = (await loc_elem.inner_text()).strip() if await loc_elem.count() > 0 else ""

                if title and job_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": job_location,
                        "job_url": job_url,
                    })
            except Exception as e:
                logger.debug(f"Error parsing job card {i}: {e}")

        return attach_untrusted_notice({
            "success": True,
            "boundary": f"Searched as {account_identity.name if account_identity else 'authenticated user'}",
            "query": keywords.strip(),
            "count": len(jobs),
            "jobs": jobs,
        })


@require_auth
async def get_job_details(
    job_url: str,
    account_identity: AccountIdentity = None,
) -> Dict[str, Any]:
    """Extract full job description and metadata for a specific LinkedIn job posting."""
    target = _normalize_job_url(job_url)
    if not target or "/jobs/view/" not in target:
        return {"success": False, "error": "INVALID_JOB_URL", "message": "Provide a valid LinkedIn job URL or numeric job ID."}

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(target, wait_until="domcontentloaded")
        await human_delay(2.0, 3.5)

        checkpoint = await detect_checkpoint(page)
        if checkpoint:
            return checkpoint

        title = ""
        title_elem = page.locator("h1.t-24, h1.top-card-layout__title, h1").first
        if await title_elem.count() > 0:
            title = (await title_elem.inner_text()).strip()

        company = ""
        company_elem = page.locator("div.job-details-jobs-unified-top-card__company-name a, a.topcard__org-name-link").first
        if await company_elem.count() > 0:
            company = (await company_elem.inner_text()).strip()

        description = ""
        desc_elem = page.locator("div#job-details, div.jobs-description__content, div.show-more-less-html__markup").first
        if await desc_elem.count() > 0:
            description = (await desc_elem.inner_text()).strip()

        return attach_untrusted_notice({
            "success": True,
            "read_only": True,
            "boundary": f"Viewed as {account_identity.name if account_identity else 'authenticated user'}",
            "job_url": page.url,
            "title": title,
            "company": company,
            "description": description[:6000],
        })


@require_auth
async def save_job(
    job_url: str,
    account_identity: AccountIdentity = None,
) -> Dict[str, Any]:
    """Bookmark a LinkedIn job posting to your Saved Jobs list."""
    target = _normalize_job_url(job_url)
    if not target or "/jobs/view/" not in target:
        return {"success": False, "error": "INVALID_JOB_URL", "message": "Provide a valid LinkedIn job URL or numeric job ID."}

    async with browser_manager.get_page(headless=True) as page:
        await page.goto(target, wait_until="domcontentloaded")
        await human_delay(2.0, 3.0)

        checkpoint = await detect_checkpoint(page)
        if checkpoint:
            return checkpoint

        save_btn = page.locator("button.jobs-save-button, button[aria-label*='Save' i]").first
        if await save_btn.count() == 0:
            return {"success": False, "error": "SAVE_BUTTON_NOT_FOUND", "message": "Could not locate the Save button on this job posting."}

        btn_text = (await save_btn.inner_text()).strip().lower()
        if "saved" in btn_text:
            return {"success": True, "already_saved": True, "job_url": page.url, "message": "Job is already in your Saved Jobs."}

        await save_btn.click()
        await human_delay(1.0, 2.0)
        return {"success": True, "already_saved": False, "job_url": page.url, "message": "Job saved to your Saved Jobs."}
