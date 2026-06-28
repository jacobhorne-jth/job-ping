import json

from app.adapters.nextjs_static import parse_nextjs_jobs
from app.models import Company


def test_nextjs_static_parses_embedded_job_data():
    company = Company(
        name="DRW",
        career_url="https://www.drw.com/work-at-drw/listings",
        source_type="nextjs_static",
    )
    payload = {
        "props": {
            "pageProps": {
                "jobData": {
                    "en": [
                        {
                            "title": "Software Engineer",
                            "id": 123,
                            "internal_job_id": "REQ-123",
                            "slug": "software-engineer-123",
                            "job_title": "Software Engineer",
                            "locations": [{"name": "Chicago"}],
                            "career_categories": [{"name": "Technology"}],
                        }
                    ]
                }
            }
        }
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'

    jobs = parse_nextjs_jobs(html, company, company.career_url)

    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].external_id == "123"
    assert jobs[0].location == "Chicago"
    assert jobs[0].url == "https://www.drw.com/work-at-drw/listings/software-engineer-123"
