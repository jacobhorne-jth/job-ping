from urllib.parse import urljoin, urlparse

import httpx

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob
from app.services.json_helpers import loads_list


DEFAULT_SEARCH_TERMS = ["software engineer intern", "intern", "new grad", "summer"]


class WorkdayAdapter(JobSourceAdapter):
    source_type = "workday"

    def supports(self, company_url: str) -> bool:
        return "myworkdayjobs.com" in urlparse(company_url).netloc.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        parsed = urlparse(company.career_url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 1:
            raise RuntimeError("Workday URL must include a career site path.")

        tenant = parsed.netloc.split(".")[0]
        site = parts[0]
        base = f"{parsed.scheme}://{parsed.netloc}"
        api_url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

        search_terms = _search_terms_for(company)
        postings: list[dict] = []
        seen_paths: set[str] = set()
        async with http_client() as client:
            for term in search_terms:
                try:
                    response = await client.post(
                        api_url,
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                        json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term},
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    continue
                for item in response.json().get("jobPostings", []):
                    path = item.get("externalPath") or item.get("title") or ""
                    if path in seen_paths:
                        continue
                    seen_paths.add(path)
                    postings.append(item)
            if not postings:
                response = await client.post(
                    api_url,
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                    json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "software engineer intern"},
                )
                response.raise_for_status()
                postings.extend(response.json().get("jobPostings", []))
        if not postings:
            raise RuntimeError("Workday returned no parseable jobs for configured role keywords.")

        jobs: list[NormalizedJob] = []
        for item in postings:
            external_path = item.get("externalPath") or ""
            external_id = None
            bullet_fields = item.get("bulletFields") or []
            if bullet_fields:
                external_id = str(bullet_fields[0])
            elif "_" in external_path:
                external_id = external_path.rsplit("_", 1)[-1]

            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=item.get("title") or "Untitled role",
                    location=item.get("locationsText"),
                    url=urljoin(f"{base}/{site}/", external_path.lstrip("/")),
                    external_id=external_id,
                    department=item.get("jobFamilyGroup"),
                    employment_type=item.get("timeType"),
                    description=item.get("postedOn"),
                    raw_data=item,
                )
            )
        return jobs


def _search_terms_for(company: Company) -> list[str]:
    keywords = loads_list(company.keywords)
    terms = []
    for keyword in keywords:
        lowered = keyword.lower()
        if "intern" in lowered or "grad" in lowered or "summer" in lowered or "software" in lowered:
            terms.append(keyword)
    return terms[:6] or DEFAULT_SEARCH_TERMS
