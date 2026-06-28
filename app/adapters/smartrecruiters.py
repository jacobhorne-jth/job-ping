from urllib.parse import parse_qs, urlparse

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob
from app.services.json_helpers import loads_list


DEFAULT_SEARCH_TERMS = ["software engineer intern", "software engineer", "intern", "new grad"]


class SmartRecruitersAdapter(JobSourceAdapter):
    source_type = "smartrecruiters"

    def supports(self, company_url: str) -> bool:
        host = urlparse(company_url).netloc.lower()
        return "smartrecruiters.com" in host

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        slug = _company_slug(company.career_url)
        postings: list[dict] = []
        seen_ids: set[str] = set()
        async with http_client() as client:
            for term in _search_terms_for(company):
                response = await client.get(
                    f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                    params={"limit": 100, "q": term},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                for item in response.json().get("content", []):
                    job_id = str(item.get("id") or item.get("uuid") or item.get("refNumber") or item.get("name"))
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    postings.append(item)
            if not postings:
                response = await client.get(
                    f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                    params={"limit": 100},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                postings.extend(response.json().get("content", []))

        jobs: list[NormalizedJob] = []
        for item in postings:
            location = item.get("location") or {}
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=item.get("name") or "Untitled role",
                    location=_location_text(location),
                    url=_job_url(item),
                    external_id=str(item.get("id") or item.get("uuid") or item.get("refNumber"))
                    if item.get("id") or item.get("uuid") or item.get("refNumber")
                    else None,
                    department=_label(item.get("department")) or _label(item.get("function")),
                    employment_type=_label(item.get("typeOfEmployment")),
                    description=item.get("refNumber") or item.get("releasedDate"),
                    raw_data=item,
                )
            )
        return jobs


def _company_slug(career_url: str) -> str:
    parsed = urlparse(career_url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if "api.smartrecruiters.com" in parsed.netloc.lower() and len(parts) >= 3:
        return parts[2]
    if parts:
        return parts[0]
    query = parse_qs(parsed.query)
    return query.get("company", [""])[0]


def _search_terms_for(company: Company) -> list[str]:
    terms = []
    for keyword in loads_list(company.keywords):
        lowered = keyword.lower()
        if "intern" in lowered or "grad" in lowered or "summer" in lowered or "software" in lowered:
            terms.append(keyword)
    return terms[:6] or DEFAULT_SEARCH_TERMS


def _location_text(location: dict) -> str | None:
    if not isinstance(location, dict):
        return str(location) if location else None
    parts = [location.get("city"), location.get("region"), location.get("country")]
    return ", ".join(part for part in parts if part) or location.get("remote")


def _label(value) -> str | None:
    if isinstance(value, dict):
        return value.get("label") or value.get("name") or value.get("id")
    return str(value) if value else None


def _job_url(item: dict) -> str:
    ref = item.get("ref")
    if isinstance(ref, str):
        return ref
    if isinstance(ref, dict) and ref.get("url"):
        return ref["url"]
    company = item.get("company") or {}
    company_id = company.get("identifier") or company.get("name") or ""
    job_id = item.get("id") or item.get("uuid") or ""
    return f"https://jobs.smartrecruiters.com/{company_id}/{job_id}"
