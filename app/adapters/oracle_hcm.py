import re
from urllib.parse import urljoin, urlparse

from app.adapters.base import JobSourceAdapter, http_client
from app.models import Company
from app.schemas.job import NormalizedJob
from app.services.json_helpers import loads_list


API_BASE_RE = re.compile(r'data-apibaseurl="([^"]+)"')
SITE_NUMBER_RE = re.compile(r'data-sitenumber="([^"]+)"|siteNumber=([A-Z0-9_]+)', re.IGNORECASE)
DEFAULT_SEARCH_TERMS = ["software engineer intern", "software engineer", "intern", "new grad"]


class OracleHcmAdapter(JobSourceAdapter):
    source_type = "oracle_hcm"

    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        async with http_client() as client:
            page = await client.get(company.career_url, headers={"Accept-Encoding": "identity"})
            page.raise_for_status()
            api_base, site_number = _extract_api_config(page.text, str(page.url))
            postings: list[dict] = []
            seen_ids: set[str] = set()
            for term in _search_terms_for(company):
                response = await client.get(
                    f"{api_base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
                    params={
                        "onlyData": "true",
                        "finder": f"findReqs;siteNumber={site_number},keyword={term}",
                        "limit": "25",
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                for item in response.json().get("items", []):
                    for posting in _posting_items(item):
                        job_id = str(
                            _first(posting, "Id", "id", "RequisitionId", "requisitionId", "RequisitionNumber", "requisitionNumber")
                            or _job_url(posting, api_base, site_number)
                        )
                        if job_id in seen_ids:
                            continue
                        seen_ids.add(job_id)
                        postings.append(posting)

        jobs = [_normalize(posting, company, api_base, site_number) for posting in postings]
        if not jobs:
            raise RuntimeError("Oracle HCM returned no parseable jobs.")
        return jobs


def _extract_api_config(html: str, page_url: str) -> tuple[str, str]:
    api_match = API_BASE_RE.search(html)
    site_match = SITE_NUMBER_RE.search(html)
    if not site_match:
        raise RuntimeError("Oracle HCM page did not expose a site number.")
    site_number = next(group for group in site_match.groups() if group)
    parsed = urlparse(page_url)
    api_base = api_match.group(1) if api_match else f"{parsed.scheme}://{parsed.netloc}"
    return api_base.rstrip("/"), site_number


def _posting_items(item: dict) -> list[dict]:
    for key in ["requisitionList", "RequisitionList", "items", "Jobs", "jobs"]:
        value = item.get(key)
        if isinstance(value, list):
            return [posting for posting in value if isinstance(posting, dict)]
    if _first(item, "Title", "title", "Name", "name"):
        return [item]
    return []


def _normalize(posting: dict, company: Company, api_base: str, site_number: str) -> NormalizedJob:
    title = str(_first(posting, "Title", "title", "Name", "name", "JobTitle", "jobTitle") or "Untitled role")
    external_id = _first(
        posting,
        "Id",
        "id",
        "RequisitionId",
        "requisitionId",
        "RequisitionNumber",
        "requisitionNumber",
        "ReqNumber",
        "reqNumber",
    )
    return NormalizedJob(
        company_name=company.name,
        title=title,
        location=_location(posting),
        url=_job_url(posting, api_base, site_number),
        external_id=str(external_id) if external_id else None,
        department=_first(posting, "Category", "category", "JobFunction", "jobFunction"),
        employment_type=_first(posting, "JobType", "jobType", "WorkerType", "workerType"),
        description=_first(posting, "ShortDescription", "shortDescription", "ShortDescriptionStr", "shortDescriptionStr"),
        raw_data=posting,
    )


def _job_url(posting: dict, api_base: str, site_number: str) -> str:
    direct = _first(posting, "ExternalApplyUrl", "externalApplyUrl", "ApplyUrl", "applyUrl", "Url", "url")
    if direct:
        return str(direct)
    req_id = _first(posting, "Id", "id", "RequisitionId", "requisitionId")
    if req_id:
        return urljoin(api_base, f"/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}")
    return api_base


def _location(posting: dict) -> str | None:
    direct = _first(posting, "PrimaryLocation", "primaryLocation", "Location", "location", "WorkLocation", "workLocation")
    if direct:
        return str(direct)
    locations = _first(posting, "workLocations", "WorkLocations", "secondaryLocations", "SecondaryLocations")
    if isinstance(locations, list):
        names = []
        for location in locations:
            if isinstance(location, dict):
                name = _first(location, "Name", "name", "LocationName", "locationName")
                if name:
                    names.append(str(name))
            elif location:
                names.append(str(location))
        return ", ".join(names) or None
    return None


def _search_terms_for(company: Company) -> list[str]:
    terms = []
    for keyword in loads_list(company.keywords):
        lowered = keyword.lower()
        if "intern" in lowered or "grad" in lowered or "summer" in lowered or "software" in lowered:
            terms.append(keyword)
    return terms[:6] or DEFAULT_SEARCH_TERMS


def _first(mapping: dict, *keys: str):
    for key in keys:
        value = mapping.get(key)
        if value not in [None, ""]:
            return value
    return None
