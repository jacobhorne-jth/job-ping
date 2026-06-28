from app.adapters.generic_static import parse_static_jobs
from app.models import Company


def test_generic_static_ignores_recruiting_landing_pages():
    company = Company(
        name="Databricks",
        career_url="https://www.databricks.com/company/careers/open-positions",
        source_type="generic_static",
    )
    html = """
    <a href="/company/careers/university-recruiting">Internships & Early Careers</a>
    <a href="/company/careers/open-positions/job?gh_jid=123">Software Engineer Intern</a>
    """

    jobs = parse_static_jobs(html, company, company.career_url)

    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer Intern"
    assert jobs[0].url.endswith("gh_jid=123")
