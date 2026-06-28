from app.adapters.base import JobSourceAdapter
from app.adapters.generic_static import parse_static_jobs
from app.models import Company
from app.schemas.job import NormalizedJob


class GenericPlaywrightAdapter(JobSourceAdapter):
    source_type = "generic_playwright"

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Install the playwright extra to use generic_playwright sources.") from exc

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent="DirectJobPing/0.1 personal job tracker")
            await page.goto(company.career_url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            await browser.close()

        return parse_static_jobs(html, company, company.career_url)
