from urllib.parse import urlparse

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


class GreenhouseAdapter(JobSourceAdapter):
    source_type = "greenhouse"

    def supports(self, company_url: str) -> bool:
        return "greenhouse.io" in urlparse(company_url).netloc.lower()

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        board = urlparse(company.career_url).path.strip("/").split("/")[0]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
        async with http_client() as client:
            response = await client.get(api_url)
            response.raise_for_status()
        data = response.json()
        jobs = []
        for item in data.get("jobs", []):
            offices = ", ".join(office.get("name", "") for office in item.get("offices", []) if office.get("name"))
            departments = ", ".join(dept.get("name", "") for dept in item.get("departments", []) if dept.get("name"))
            jobs.append(
                NormalizedJob(
                    company_name=company.name,
                    title=item.get("title") or "Untitled role",
                    location=offices or item.get("location", {}).get("name"),
                    url=item.get("absolute_url") or company.career_url,
                    external_id=str(item.get("id")) if item.get("id") is not None else None,
                    department=departments or None,
                    description=item.get("content"),
                    raw_data=item,
                )
            )
        return jobs
