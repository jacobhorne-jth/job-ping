from urllib.parse import urlparse

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


class LeverAdapter(JobSourceAdapter):
    source_type = "lever"

    def supports(self, company_url: str) -> bool:
        return "jobs.lever.co" in urlparse(company_url).netloc.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        parsed = urlparse(company.career_url)
        company_slug = parsed.path.strip("/").split("/")[0]
        api_url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        async with http_client() as client:
            response = await client.get(api_url)
            response.raise_for_status()
        jobs = []
        for item in response.json():
            categories = item.get("categories") or {}
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=item.get("text") or "Untitled role",
                    location=categories.get("location"),
                    url=item.get("hostedUrl") or item.get("applyUrl") or company.career_url,
                    external_id=item.get("id"),
                    department=categories.get("team") or categories.get("department"),
                    employment_type=categories.get("commitment"),
                    description=item.get("descriptionPlain") or item.get("description"),
                    raw_data=item,
                )
            )
        return jobs
