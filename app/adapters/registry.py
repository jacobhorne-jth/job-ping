from app.adapters.amazon_jobs import AmazonJobsAdapter
from app.adapters.ashby import AshbyAdapter
from app.adapters.base import JobSourceAdapter
from app.adapters.direct_html import DirectHtmlAdapter
from app.adapters.generic_playwright import GenericPlaywrightAdapter
from app.adapters.generic_static import GenericStaticAdapter
from app.adapters.google_careers import GoogleCareersAdapter
from app.adapters.greenhouse import GreenhouseAdapter
from app.adapters.lever import LeverAdapter
from app.adapters.oracle_hcm import OracleHcmAdapter
from app.adapters.phenom_static import PhenomStaticAdapter
from app.adapters.smartrecruiters import SmartRecruitersAdapter
from app.adapters.tesla import TeslaAdapter
from app.adapters.workday import WorkdayAdapter


ADAPTERS: dict[str, JobSourceAdapter] = {
    "amazon_jobs": AmazonJobsAdapter(),
    "greenhouse": GreenhouseAdapter(),
    "lever": LeverAdapter(),
    "ashby": AshbyAdapter(),
    "google_careers": GoogleCareersAdapter(),
    "workday": WorkdayAdapter(),
    "smartrecruiters": SmartRecruitersAdapter(),
    "phenom_static": PhenomStaticAdapter(),
    "oracle_hcm": OracleHcmAdapter(),
    "tesla": TeslaAdapter(),
    "direct_html": DirectHtmlAdapter(),
    "generic_static": GenericStaticAdapter(),
    "generic_playwright": GenericPlaywrightAdapter(),
}


def get_adapter(source_type: str) -> JobSourceAdapter:
    return ADAPTERS.get(source_type) or ADAPTERS["generic_static"]
