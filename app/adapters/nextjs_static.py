import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob


class NextjsStaticAdapter(JobSourceAdapter):
    source_type = "nextjs_static"

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        async with http_client() as client:
            response = await client.get(company.career_url, headers={"Accept-Encoding": "identity"})
            response.raise_for_status()
        jobs = parse_nextjs_jobs(response.text, company, str(response.url))
        if not jobs:
            raise RuntimeError("Next.js page returned no parseable embedded jobs.")
        return jobs


def parse_nextjs_jobs(html: str, company: Company, base_url: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return []

    jobs: list[NormalizedJob] = []
    seen: set[str] = set()
    for item in _walk_dicts(data):
        title = item.get("title") or item.get("job_title") or item.get("jobTitle") or item.get("name")
        slug = item.get("slug") or item.get("url") or item.get("path")
        job_id = item.get("id") or item.get("internal_job_id") or slug
        if not isinstance(title, str) or not isinstance(slug, str) or not job_id:
            continue
        if not _looks_like_job_item(item):
            continue
        external_id = str(job_id)
        if external_id in seen:
            continue
        seen.add(external_id)
        jobs.append(
            NormalizedJob(
                company_name=company.name,
                title=title.strip(),
                location=_location(item),
                url=urljoin(base_url.rstrip("/") + "/", slug.lstrip("/")),
                external_id=external_id,
                department=_first_text(item, "career_categories", "category", "department"),
                description=_first_text(item, "job_keywords", "keywords"),
                raw_data=item,
            )
        )
    return jobs


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _looks_like_job_item(item: dict) -> bool:
    keys = set(item)
    return bool({"title", "slug"} <= keys and ({"id", "internal_job_id", "job_title"} & keys))


def _location(item: dict) -> str | None:
    locations = item.get("locations") or item.get("career_countries")
    if isinstance(locations, list):
        names = [_location_name(location) for location in locations]
        return ", ".join(name for name in names if name) or None
    if isinstance(locations, str):
        return locations
    return _first_text(item, "location", "city")


def _location_name(value) -> str | None:
    if isinstance(value, dict):
        return value.get("name") or value.get("title") or value.get("city")
    return str(value) if value else None


def _first_text(item: dict, *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            names = [_location_name(part) for part in value]
            text = ", ".join(name for name in names if name)
            if text:
                return text
        elif value:
            return str(value)
    return None
