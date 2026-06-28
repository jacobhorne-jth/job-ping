from app.adapters.tesla import parse_tesla_jobs
from app.models import Company


def test_tesla_parser_extracts_rendered_job_links():
    company = Company(
        name="Tesla",
        career_url="https://www.tesla.com/careers/search/?type=intern&site=US",
        source_type="tesla",
    )
    html = """
    <a class="style_TitleLink__PepSM tds-text--h4 tds-link tds-link--secondary"
       href="/careers/search/job/internship-product-manager-residential-energy-engineering-fall-2026-275178">
       Internship, Product Manager, Residential Energy Engineering (Fall 2026)
    </a>
    """

    jobs = parse_tesla_jobs(html, company, company.career_url)

    assert len(jobs) == 1
    assert jobs[0].title == "Internship, Product Manager, Residential Energy Engineering (Fall 2026)"
    assert jobs[0].external_id == "275178"
    assert jobs[0].employment_type == "Internship"
    assert jobs[0].url == (
        "https://www.tesla.com/careers/search/job/"
        "internship-product-manager-residential-energy-engineering-fall-2026-275178"
    )
