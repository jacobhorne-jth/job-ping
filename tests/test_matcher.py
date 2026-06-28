from app.schemas.job import NormalizedJob
from app.services.matcher import match_job


def test_keyword_matching():
    job = NormalizedJob(company_name="Acme", title="Software Engineer Intern", url="https://example.com/job")
    result = match_job(job, ["software engineer intern"], [], [])
    assert result.matched is True
    assert result.matched_keywords == ["software engineer intern"]


def test_exclude_keyword_filtering():
    job = NormalizedJob(company_name="Acme", title="Senior Software Engineer Intern Manager", url="https://example.com/job")
    result = match_job(job, ["software engineer intern"], ["senior", "manager"], [])
    assert result.matched is False


def test_location_filtering():
    job = NormalizedJob(
        company_name="Acme",
        title="Backend Intern",
        location="Mountain View, CA",
        url="https://example.com/job",
    )
    assert match_job(job, ["backend intern"], [], ["mountain view"]).matched is True
    assert match_job(job, ["backend intern"], [], ["new york"]).matched is False


def test_intern_does_not_match_internal_or_internals():
    internal_job = NormalizedJob(
        company_name="Acme",
        title="Software Engineer - Database Engine Internals",
        url="https://example.com/job",
    )
    assert match_job(internal_job, ["software engineer intern"], [], []).matched is False
    assert match_job(internal_job, ["intern"], [], []).matched is False

    intern_job = NormalizedJob(
        company_name="Acme",
        title="Software Engineering Intern, Summer 2027",
        url="https://example.com/job",
    )
    assert match_job(intern_job, ["software engineering intern"], [], []).matched is True
