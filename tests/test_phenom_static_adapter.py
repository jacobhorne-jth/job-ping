from app.adapters.phenom_static import parse_phenom_jobs
from app.models import Company


def test_phenom_static_parses_embedded_jobs_payload():
    company = Company(
        name="Yelp",
        career_url="https://www.yelp.careers/us/en/search-results",
        source_type="phenom_static",
    )
    html = """
    <script>
    window.phApp = {"eagerLoadRefineSearch":{"status":200,"data":{"jobs":[
      {"title":"Community Intern","jobId":"13911","applyUrl":"https://uscareers-yelp.icims.com/jobs/13911/job","cityState":"Brooklyn, New York","category":"Marketing"}
    ]}}};
    </script>
    """

    jobs = parse_phenom_jobs(html, company, company.career_url)

    assert len(jobs) == 1
    assert jobs[0].title == "Community Intern"
    assert jobs[0].external_id == "13911"
    assert jobs[0].location == "Brooklyn, New York"
