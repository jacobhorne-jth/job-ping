import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


JOB_PATH_RE = re.compile(r"/(?:job|jobs|join-us/jobs)(?:/|\?|$)", re.IGNORECASE)
EXTERNAL_ID_RE = re.compile(r"(?:id=|/)([A-Z]{0,4}\d{4,}|\d{8,})(?:[/?#-]|$)", re.IGNORECASE)
NOISE_WORDS = {
    "apply",
    "apply now",
    "view job",
    "view jobs",
    "view openings",
    "saved jobs",
    "login",
    "returning candidate login",
    "skip to menu",
    "skip to main content",
    "jobs",
    "careers",
}


class DirectHtmlAdapter(JobSourceAdapter):
    source_type = "direct_html"

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        async with http_client() as client:
            response = await client.get(company.career_url, headers={"Accept-Encoding": "identity"})
            response.raise_for_status()
        jobs = parse_direct_html_jobs(response.text, company, str(response.url))
        if not jobs:
            raise RuntimeError("Direct HTML page returned no parseable job links.")
        return jobs


def parse_direct_html_jobs(html: str, company: Company, base_url: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[NormalizedJob] = []
    seen_urls: set[str] = set()
    base_host = urlparse(base_url).netloc.lower()

    for anchor in soup.find_all("a", href=True):
        title = _clean_title(anchor.get_text(" ", strip=True))
        if not title or title.lower() in NOISE_WORDS:
            continue

        url = urljoin(base_url, anchor["href"])
        parsed = urlparse(url)
        if parsed.netloc.lower() != base_host:
            continue
        if not JOB_PATH_RE.search(parsed.path + ("?" + parsed.query if parsed.query else "")):
            continue
        if _looks_like_non_job(parsed.path, title):
            continue
        if url in seen_urls:
            continue

        seen_urls.add(url)
        jobs.append(
            NormalizedJob(
                company_name=company.name,
                title=title[:500],
                location=_nearby_location(anchor),
                url=url,
                external_id=_external_id(url),
                raw_data={"text": title, "href": url},
            )
        )
    return jobs


def _clean_title(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"^\d{8,}\s+\d{2}/\d{2}/\d{4}\s+", "", text)
    text = re.split(r"\s+Requisition\s*ID\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.split(r"\s+Application\s+deadline\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(r"\s+Save(?: for Later)?$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+Pin$", "", text, flags=re.IGNORECASE)
    return text.strip(" -|")


def _looks_like_non_job(path: str, title: str) -> bool:
    lowered_path = path.lower()
    lowered_title = title.lower()
    if lowered_title.startswith("skip to "):
        return True
    if any(part in lowered_path for part in ["/login", "/saved-jobs", "/talentcommunity"]):
        return True
    if lowered_path.rstrip("/").endswith("/jobs"):
        return True
    if any(part in lowered_path for part in ["/internship", "/internships"]) and "engineer" not in lowered_title:
        return True
    return False


def _nearby_location(anchor) -> str | None:
    parent = anchor.find_parent(["li", "article", "section", "div"])
    if not parent:
        return None
    text = " ".join(parent.get_text(" ", strip=True).split())
    match = re.search(r"\b(?:Remote|Hybrid|[A-Z][A-Za-z .'-]+,\s*[A-Z]{2})\b", text)
    return match.group(0) if match else None


def _external_id(url: str) -> str | None:
    match = EXTERNAL_ID_RE.search(url)
    return match.group(1) if match else None
