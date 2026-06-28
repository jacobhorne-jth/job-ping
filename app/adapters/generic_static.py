from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


JOB_HINTS = ["software", "engineer", "intern", "new grad", "university", "early career"]
JOB_URL_HINTS = ["job", "jobs", "position", "positions", "opening", "openings", "requisition", "posting"]
NON_JOB_PAGE_HINTS = [
    "university-recruiting",
    "early-careers",
    "early-career",
    "internships",
    "students",
    "graduates",
    "life-at",
    "working-at",
    "benefits",
]


def parse_static_jobs(html: str, company: Company, base_url: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[NormalizedJob] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        if not text:
            continue
        lowered = text.lower()
        href = urljoin(base_url, anchor["href"])
        if href in seen_urls:
            continue
        href_lowered = href.lower()
        if not _looks_like_job_url(href_lowered):
            continue
        if any(hint in lowered for hint in JOB_HINTS):
            seen_urls.add(href)
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=text[:500],
                    location=None,
                    url=href,
                    raw_data={"text": text, "href": href},
                )
            )
    return jobs


def _looks_like_job_url(href: str) -> bool:
    if any(hint in href for hint in NON_JOB_PAGE_HINTS):
        return False
    if "career" in href and not any(hint in href for hint in JOB_URL_HINTS):
        return False
    return any(hint in href for hint in JOB_URL_HINTS)


class GenericStaticAdapter(JobSourceAdapter):
    source_type = "generic_static"

    def supports(self, company_url: str) -> bool:
        return True

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        async with http_client() as client:
            response = await client.get(company.career_url)
            response.raise_for_status()
        return parse_static_jobs(response.text, company, company.career_url)
