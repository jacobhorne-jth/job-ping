import html
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


class GoogleCareersAdapter(JobSourceAdapter):
    source_type = "google_careers"

    def supports(self, company_url: str) -> bool:
        return "google.com/about/careers" in company_url.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        async with http_client() as client:
            response = await client.get(company.career_url)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        jobs: list[NormalizedJob] = []
        for anchor in soup.find_all("a", href=True):
            href = urljoin(company.career_url, anchor["href"])
            text = " ".join(anchor.get_text(" ", strip=True).split())
            if "/jobs/results/" not in href or not text:
                continue
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=text[:500],
                    location=None,
                    url=href,
                    external_id=href.rstrip("/").split("/")[-1],
                    raw_data={"text": text, "href": href},
                )
            )
        if not jobs:
            jobs = self._parse_embedded_jobs(company, response.text)
        if not jobs:
            raise RuntimeError("Google Careers page did not expose parseable job data. Page structure may have changed.")
        return jobs

    def _parse_embedded_jobs(self, company: Company, page_html: str) -> list[NormalizedJob]:
        decoded = html.unescape(page_html)
        pattern = re.compile(
            r'\["(?P<job_id>\d+)","(?P<title>[^"]+)","(?P<url>https://www\.google\.com/about/careers/applications/signin\?jobId(?:=|\\u003d)[^"]+)"'
        )
        jobs: list[NormalizedJob] = []
        seen: set[str] = set()
        for match in pattern.finditer(decoded):
            job_id = match.group("job_id")
            if job_id in seen:
                continue
            seen.add(job_id)
            signin_url = _decode_js_url(match.group("url"))
            query = parse_qs(urlparse(signin_url).query)
            title = query.get("title", [match.group("title")])[0].replace("+", " ")
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=title,
                    location=None,
                    url=signin_url,
                    external_id=job_id,
                    raw_data={"job_id": job_id, "signin_url": signin_url},
                )
            )
        return jobs


def _decode_js_url(value: str) -> str:
    value = (
        value.replace("\\u003d", "=")
        .replace("\\u0026", "&")
        .replace("\\/", "/")
    )
    return unquote(value)
