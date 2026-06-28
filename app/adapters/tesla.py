import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


TESLA_JOB_PATH = "/careers/search/job/"
JOB_ID_RE = re.compile(r"-(\d+)$")


class TeslaAdapter(JobSourceAdapter):
    source_type = "tesla"

    def supports(self, company_url: str) -> bool:
        parsed = urlparse(company_url)
        return "tesla.com" in parsed.netloc.lower() and "/careers/" in parsed.path.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        try:
            async with http_client() as client:
                response = await client.get(company.career_url)
                response.raise_for_status()
            return parse_tesla_jobs(response.text, company, company.career_url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 403:
                raise

        return await _fetch_jobs_with_browser(company)


def parse_tesla_jobs(html: str, company: Company, base_url: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[NormalizedJob] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if TESLA_JOB_PATH not in href:
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not title:
            continue
        url = urljoin(base_url, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        jobs.append(
            NormalizedJob(
                company_name=company.name,
                title=title,
                location=None,
                url=url,
                external_id=_external_id_from_url(url),
                employment_type="Internship" if "intern" in title.lower() else None,
                raw_data={"href": href, "text": title},
            )
        )
    return jobs


async def _fetch_jobs_with_browser(company: Company) -> list[NormalizedJob]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Tesla blocks direct HTTP checks. Install Playwright to use the Tesla rendered-page adapter."
        ) from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        )
        await page.goto(company.career_url, wait_until="networkidle", timeout=30000)
        html = await page.content()
        await browser.close()
    return parse_tesla_jobs(html, company, company.career_url)


def _external_id_from_url(url: str) -> str | None:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    match = JOB_ID_RE.search(slug)
    return match.group(1) if match else None
