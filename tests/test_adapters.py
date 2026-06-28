import pytest

from app.adapters.greenhouse import GreenhouseAdapter
from app.models import Company
from app.services.json_helpers import dumps_list


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url):
        return FakeResponse(
            {
                "jobs": [
                    {
                        "id": 123,
                        "title": "Software Engineer Intern",
                        "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
                        "offices": [{"name": "New York"}],
                        "departments": [{"name": "Engineering"}],
                        "content": "Build things.",
                    }
                ]
            }
        )


@pytest.mark.asyncio
async def test_greenhouse_normalization(monkeypatch):
    monkeypatch.setattr("app.adapters.greenhouse.http_client", lambda: FakeClient())
    company = Company(
        name="Acme",
        career_url="https://boards.greenhouse.io/acme",
        source_type="greenhouse",
        keywords=dumps_list([]),
        exclude_keywords=dumps_list([]),
        locations=dumps_list([]),
    )
    jobs = await GreenhouseAdapter().fetch_jobs(company)

    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer Intern"
    assert jobs[0].location == "New York"
    assert jobs[0].external_id == "123"
    assert jobs[0].department == "Engineering"
