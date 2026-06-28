from app.adapters.direct_html import parse_direct_html_jobs
from app.models import Company


def test_direct_html_parses_job_links_only():
    company = Company(
        name="Snap",
        career_url="https://careers.snap.com/jobs?query=intern",
        source_type="direct_html",
    )
    html = """
    <a href="/jobs">View Openings</a>
    <a href="/job?id=R0045123">Machine Learning Engineering Intern</a>
    <a href="/job?id=R0045123">Machine Learning Engineering Intern</a>
    """

    jobs = parse_direct_html_jobs(html, company, company.career_url)

    assert len(jobs) == 1
    assert jobs[0].title == "Machine Learning Engineering Intern"
    assert jobs[0].external_id == "R0045123"
    assert jobs[0].url == "https://careers.snap.com/job?id=R0045123"
