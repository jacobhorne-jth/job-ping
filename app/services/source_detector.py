from urllib.parse import urlparse


SUPPORTED_SOURCE_TYPES = {
    "auto",
    "greenhouse",
    "lever",
    "ashby",
    "amazon_jobs",
    "google_careers",
    "workday",
    "smartrecruiters",
    "tesla",
    "direct_html",
    "phenom_static",
    "oracle_hcm",
    "nextjs_static",
    "generic_static",
    "generic_playwright",
    "unknown",
}


def detect_source_type(career_url: str) -> str:
    parsed = urlparse(career_url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if "boards.greenhouse.io" in host or "job-boards.greenhouse.io" in host:
        return "greenhouse"
    if "jobs.lever.co" in host:
        return "lever"
    if "jobs.ashbyhq.com" in host:
        return "ashby"
    if "amazon.jobs" in host:
        return "amazon_jobs"
    if "myworkdayjobs.com" in host:
        return "workday"
    if "smartrecruiters.com" in host:
        return "smartrecruiters"
    if "google.com" in host and "/about/careers" in path:
        return "google_careers"
    if "tesla.com" in host and "/careers/" in path:
        return "tesla"
    if "snap.com" in host and "/jobs" in path:
        return "direct_html"
    if "optiver.com" in host and "/join-us/jobs" in path:
        return "direct_html"
    if "arm.com" in host and "/search-jobs" in path:
        return "direct_html"
    if "schwabjobs.com" in host and "/search-jobs" in path:
        return "direct_html"
    if "capitalonecareers.com" in host and "/search-jobs" in path:
        return "direct_html"
    if "wellsfargojobs.com" in host and "/jobs" in path:
        return "direct_html"
    if "deshaw.com" in host and "/careers" in path:
        return "direct_html"
    if "shopify.com" in host and "/careers" in path:
        return "direct_html"
    if "careers.etsy.com" in host:
        return "direct_html"
    if "drw.com" in host and "/work-at-drw/listings" in path:
        return "nextjs_static"
    if any(
        domain in host
        for domain in [
            "activisionblizzard.com",
            "careers.cisco.com",
            "careers.kbr.com",
            "qualtrics.com",
            "wbd.com",
            "yelp.careers",
            "jobs.ebayinc.com",
        ]
    ):
        return "phenom_static"
    if "oraclecloud.com" in host or ("careers.oracle.com" in host and "/sites/" in path):
        return "oracle_hcm"
    return "generic_static"
