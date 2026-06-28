from abc import ABC, abstractmethod

import httpx

from app.config import get_settings
from app.models import Company
from app.schemas.job import NormalizedJob


class JobSourceAdapter(ABC):
    source_type: str

    def supports(self, company_url: str) -> bool:
        return False

    @abstractmethod
    async def fetch_jobs(self, company: Company) -> list[NormalizedJob]:
        raise NotImplementedError


def http_client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        timeout=settings.request_timeout_seconds,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36 DirectJobPing/0.1"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        },
        follow_redirects=True,
    )
