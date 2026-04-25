import logging
from typing import Any
from patchright.async_api import Page, Locator

from browser.helpers import stabilize_navigation, scroll_to_bottom

logger = logging.getLogger("linkedin-mcp.browser.scrapers.profile")


class ProfileScraper:
    """Specialized scraper for LinkedIn profile pages."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def scrape(self, profile_id: str) -> dict[str, Any]:
        """Navigate to and scrape a profile by its ID (slug)."""
        profile_url = f"https://www.linkedin.com/in/{profile_id}/"


        logger.info("Scraping profile via UI: %s", profile_url)

        await self.page.goto(profile_url, wait_until="load")
        await stabilize_navigation(self.page)
        await scroll_to_bottom(self.page, max_scrolls=3)

        # Check for authwall
        if "linkedin.com/authwall" in self.page.url:
            logger.error("Caught by authwall at: %s", self.page.url)
            return {
                "name": "LinkedIn Member",
                "profile_id": profile_id,
                "profile_url": profile_url,
            }

        # Extract basic info
        name_node = self.page.locator("h1").first
        name = (
            (await name_node.inner_text()).strip()
            if await name_node.is_visible()
            else "LinkedIn Member"
        )

        headline_node = self.page.locator(".text-body-medium.break-words").first
        headline = (
            (await headline_node.inner_text()).strip()
            if await headline_node.is_visible()
            else ""
        )

        location_node = self.page.locator(
            ".text-body-small.inline.t-black--light.break-words"
        ).first
        location = (
            (await location_node.inner_text()).strip()
            if await location_node.is_visible()
            else ""
        )

        summary_node = self.page.locator(
            "section#about ~ div .display-flex.ph5.pb5 span[aria-hidden='true']"
        ).first
        summary = (
            (await summary_node.inner_text()).strip()
            if await summary_node.is_visible()
            else ""
        )

        # Fetch detailed sections
        experience = await self._scrape_experience()
        education = await self._scrape_education()
        skills = await self._scrape_skills(profile_id)

        return {
            "profile_id": profile_id,
            "name": name,
            "headline": headline,
            "location": location,
            "summary": summary,
            "profile_url": profile_url,
            "experience": experience,
            "education": education,
            "skills": skills,
        }

    async def _scrape_experience(self) -> list[dict[str, Any]]:
        """Scrape experience entries."""
        experiences = []
        try:
            # Check for "Show all X experiences" link
            details_link = self.page.locator(
                "section:has(div#experience) a[href*='/details/experience/']"
            ).first
            if await details_link.is_visible(timeout=2000):
                target_url = await details_link.get_attribute("href")
                if target_url:
                    if not target_url.startswith("http"):
                        target_url = f"https://www.linkedin.com{target_url}"
                    logger.info("Navigating to detailed experience: %s", target_url)
                    await self.page.goto(target_url, wait_until="load")
                    await stabilize_navigation(self.page)
                    await scroll_to_bottom(self.page, max_scrolls=5)

                    items = await self.page.locator("li.artdeco-list__item").all()
                    for item in items:
                        exp = await self._parse_experience_item(item)
                        if exp:
                            experiences.append(exp)
                    return experiences

            # Main page fallback
            exp_section = self.page.locator("section:has(div#experience)")
            if await exp_section.is_visible():
                items = await exp_section.locator("li.artdeco-list__item").all()
                for item in items:
                    exp = await self._parse_experience_item(item)
                    if exp:
                        experiences.append(exp)
        except Exception as exc:
            logger.debug("Experience scraping minor error: %s", exc)
        return experiences



    async def _parse_experience_item(self, item: Locator) -> dict[str, Any] | None:
        """Helper to parse a single experience list item."""
        try:
            title_node = item.locator(
                ".display-flex.align-items-center.mr1.t-bold span[aria-hidden='true'], .t-bold span[aria-hidden='true']"
            ).first
            company_node = item.locator(
                "span.t-14.t-normal span[aria-hidden='true']"
            ).first
            period_node = item.locator(
                "span.t-14.t-normal.t-black--light span[aria-hidden='true']"
            ).first

            title = (
                (await title_node.inner_text()).strip()
                if await title_node.is_visible()
                else ""
            )
            company = (
                (await company_node.inner_text()).strip()
                if await company_node.is_visible()
                else ""
            )
            period = (
                (await period_node.inner_text()).strip()
                if await period_node.is_visible()
                else ""
            )

            if not company and await item.locator(".t-bold").count() > 1:
                company = title
                title = "Multiple Roles"

            if company:
                if "\u00b7" in company:
                    company = company.split("\u00b7")[0].strip()
                if "mos" in company.lower() or "yr" in company.lower() or "yr" == company.lower().strip():
                    company = title
                    title = "Role"

            if title or company:
                return {
                    "title": title,
                    "company": company,
                    "start_date": period.split(" - ")[0] if " - " in period else period,
                    "end_date": period.split(" - ")[1]
                    if " - " in period
                    else "Present",
                }
        except Exception:
            pass
        return None

    async def _scrape_education(self) -> list[dict[str, Any]]:
        """Scrape education entries."""
        educations = []
        try:
            edu_section = self.page.locator("section:has(div#education)")
            if not await edu_section.is_visible():
                return []

            items = await edu_section.locator("li.artdeco-list__item").all()
            for item in items:
                school_node = item.locator(".t-bold span[aria-hidden='true']").first
                degree_node = item.locator(
                    "span.t-14.t-normal span[aria-hidden='true']"
                ).first
                period_node = item.locator(
                    "span.t-14.t-normal.t-black--light span[aria-hidden='true']"
                ).first

                school = (
                    (await school_node.inner_text()).strip()
                    if await school_node.is_visible()
                    else ""
                )
                degree = (
                    (await degree_node.inner_text()).strip()
                    if await degree_node.is_visible()
                    else ""
                )
                period = (
                    (await period_node.inner_text()).strip()
                    if await period_node.is_visible()
                    else ""
                )

                if school:
                    educations.append(
                        {
                            "school": school,
                            "degree": degree,
                            "start_date": period.split(" - ")[0]
                            if " - " in period
                            else period,
                            "end_date": period.split(" - ")[1]
                            if " - " in period
                            else "",
                        }
                    )
        except Exception as exc:
            logger.debug("Education scraping minor error: %s", exc)
        return educations

    async def _scrape_skills(self, profile_id: str) -> list[str]:
        """Scrape skills with navigation fallback."""
        skills = []
        try:
            detail_selectors = [
                "a[href*='/details/skills/']",
                "a:has-text('Show all'):has-text('skills')",
                "section#skills a[href*='/details/skills/']",
            ]

            detail_link = None
            for sel in detail_selectors:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=2000):
                    detail_link = loc
                    break

            if detail_link:
                href = await detail_link.get_attribute("href")
                if href:
                    if not href.startswith("http"):
                        href = f"https://www.linkedin.com{href}"
                    logger.info("Navigating to skills detail: %s", href)
                    await self.page.goto(href, wait_until="load")
                    await stabilize_navigation(self.page)
                    await scroll_to_bottom(self.page, max_scrolls=5)

                    skill_nodes = await self.page.locator(
                        ".pvs-entity__pathnode .t-bold span[aria-hidden='true']"
                    ).all()
                    if not skill_nodes:
                        skill_nodes = await self.page.locator(
                            ".artdeco-list__item .t-bold span[aria-hidden='true']"
                        ).all()

                    for node in skill_nodes:
                        text = (await node.inner_text()).strip()
                        if text and text not in skills:
                            skills.append(text)
                    return skills

            # Main page fallback
            skill_section = self.page.locator("section#skills")
            if await skill_section.is_visible():
                items = await skill_section.locator(
                    ".t-bold span[aria-hidden='true']"
                ).all()
                for item in items:
                    text = (await item.inner_text()).strip()
                    if text and text not in skills:
                        skills.append(text)
        except Exception as exc:
            logger.debug("Skills scraping minor error: %s", exc)
        return skills


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ScraperMeta
SCRAPER = ScraperMeta(attr="profile_scraper", cls=ProfileScraper)
