from urllib.parse import urlparse

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


class AshbyAdapter(JobSourceAdapter):
    source_type = "ashby"

    def supports(self, company_url: str) -> bool:
        return "jobs.ashbyhq.com" in urlparse(company_url).netloc.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        slug = urlparse(company.career_url).path.strip("/").split("/")[0]
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        async with http_client() as client:
            response = await client.get(api_url)
            response.raise_for_status()
        data = response.json()
        jobs = []
        for item in data.get("jobs", []):
            location = item.get("locationName")
            if not location and item.get("location"):
                raw_location = item["location"]
                location = raw_location.get("name") if isinstance(raw_location, dict) else str(raw_location)
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=item.get("title") or "Untitled role",
                    location=location,
                    url=item.get("jobUrl") or item.get("applyUrl") or company.career_url,
                    external_id=item.get("id"),
                    department=_name_value(item.get("department")) or _name_value(item.get("team")),
                    employment_type=item.get("employmentType"),
                    description=item.get("descriptionPlain") or item.get("descriptionHtml"),
                    raw_data=item,
                )
            )
        return jobs


def _name_value(value) -> str | None:
    if isinstance(value, dict):
        return value.get("name")
    return str(value) if value else None
