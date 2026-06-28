from urllib.parse import parse_qs, urlencode, urlparse

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob
from app.services.json_helpers import loads_list


DEFAULT_SEARCH_TERMS = ["software engineer intern", "swe intern", "new grad software engineer", "summer intern"]


class AmazonJobsAdapter(JobSourceAdapter):
    source_type = "amazon_jobs"

    def supports(self, company_url: str) -> bool:
        return "amazon.jobs" in urlparse(company_url).netloc.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        postings: list[dict] = []
        seen_ids: set[str] = set()
        async with http_client() as client:
            for term in _search_terms_for(company):
                query = urlencode({"base_query": term, "loc_query": ""})
                response = await client.get(f"https://www.amazon.jobs/en/search.json?{query}")
                response.raise_for_status()
                for item in response.json().get("jobs", []):
                    job_id = str(item.get("id") or item.get("id_icims") or item.get("job_path") or item.get("title"))
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    postings.append(item)

        return [
            NormalizedJob(
                company_name=company.name,
                title=item.get("title") or "Untitled role",
                location=item.get("location") or item.get("normalized_location"),
                url=item.get("url_next_step") or f"https://www.amazon.jobs{item.get('job_path') or ''}",
                external_id=str(item.get("id") or item.get("id_icims")) if item.get("id") or item.get("id_icims") else None,
                department=item.get("job_category") or item.get("team") or item.get("business_category"),
                employment_type=item.get("job_schedule_type"),
                description=item.get("description") or item.get("description_short") or item.get("basic_qualifications"),
                raw_data=item,
            )
            for item in postings
        ]


def _search_terms_for(company: Company) -> list[str]:
    configured_terms = [value for value in parse_qs(urlparse(company.career_url).query).get("base_query", []) if value]
    if configured_terms:
        return configured_terms[:4]

    terms = []
    for keyword in loads_list(company.keywords):
        lowered = keyword.lower()
        if "intern" in lowered or "grad" in lowered or "summer" in lowered or "software" in lowered:
            terms.append(keyword)
    return terms[:6] or DEFAULT_SEARCH_TERMS
