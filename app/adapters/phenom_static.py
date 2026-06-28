import json
import re
from urllib.parse import urljoin

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


EAGER_KEY_RE = re.compile(r'"eagerLoadRefineSearch"\s*:')


class PhenomStaticAdapter(JobSourceAdapter):
    source_type = "phenom_static"

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        async with http_client() as client:
            response = await client.get(company.career_url, headers={"Accept-Encoding": "identity"})
            response.raise_for_status()
        jobs = parse_phenom_jobs(response.text, company, str(response.url))
        if not jobs:
            raise RuntimeError("Phenom page returned no embedded jobs payload.")
        return jobs


def parse_phenom_jobs(html: str, company: Company, base_url: str) -> list[NormalizedJob]:
    payload = _extract_eager_payload(html)
    if not payload:
        return []
    raw_jobs = payload.get("data", {}).get("jobs") or payload.get("jobs") or []
    jobs: list[NormalizedJob] = []
    seen: set[str] = set()

    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("jobTitle") or item.get("name")
        url = item.get("applyUrl") or item.get("url") or item.get("jobUrl")
        if not title or not url:
            continue
        absolute_url = urljoin(base_url, url)
        job_id = str(item.get("jobId") or item.get("reqId") or item.get("atsReqId") or item.get("id") or absolute_url)
        if job_id in seen:
            continue
        seen.add(job_id)
        jobs.append(
            NormalizedJob(
                company_name=company.name,
                title=title,
                location=_location(item),
                url=absolute_url,
                external_id=job_id,
                department=item.get("category") or item.get("jobCategory") or item.get("jobFamily"),
                employment_type=item.get("type") or item.get("employmentType"),
                description=item.get("descriptionTeaser") or item.get("shortDescription"),
                raw_data=item,
            )
        )
    return jobs


def _extract_eager_payload(html: str) -> dict | None:
    match = EAGER_KEY_RE.search(html)
    if not match:
        return None
    start = html.find("{", match.end())
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(html[start:], start):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start : index + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _location(item: dict) -> str | None:
    parts = [
        item.get("city"),
        item.get("state"),
        item.get("country"),
    ]
    text = ", ".join(str(part) for part in parts if part)
    return text or item.get("cityState") or item.get("location")
