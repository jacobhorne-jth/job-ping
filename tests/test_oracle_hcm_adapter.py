from app.adapters.oracle_hcm import _extract_api_config, _normalize
from app.models import Company


def test_oracle_hcm_extracts_api_config_from_page():
    html = '<div data-apibaseurl="https://example.fa.oraclecloud.com:443" data-sitenumber="CX_1001"></div>'

    api_base, site_number = _extract_api_config(html, "https://vanity.example/careers")

    assert api_base == "https://example.fa.oraclecloud.com:443"
    assert site_number == "CX_1001"


def test_oracle_hcm_normalizes_requisition():
    company = Company(name="Oracle", career_url="https://careers.oracle.com/en/sites/jobsearch", source_type="oracle_hcm")
    posting = {
        "Id": "12345",
        "Title": "Software Engineer Intern",
        "PrimaryLocation": "Austin, TX",
        "RequisitionNumber": "REQ-12345",
    }

    job = _normalize(posting, company, "https://example.fa.oraclecloud.com", "CX_1001")

    assert job.title == "Software Engineer Intern"
    assert job.location == "Austin, TX"
    assert job.external_id == "12345"
    assert job.url == "https://example.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/12345"
