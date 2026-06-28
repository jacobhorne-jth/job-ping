from dataclasses import dataclass
import re

from app.schemas.job import NormalizedJob


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    matched_keywords: list[str]


def _normalize(value: str) -> str:
    return f" {re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()} "


def _contains(haystack: str, needle: str) -> bool:
    normalized_needle = _normalize(needle).strip()
    if not normalized_needle:
        return False
    return f" {normalized_needle} " in haystack


def match_job(
    job: NormalizedJob,
    include_keywords: list[str],
    exclude_keywords: list[str],
    locations: list[str],
) -> MatchResult:
    text = _normalize(" ".join([job.title or "", job.description or ""]))
    location_text = _normalize(job.location or "")

    matched_keywords = [keyword for keyword in include_keywords if _contains(text, keyword)]
    if include_keywords and not matched_keywords:
        return MatchResult(False, [])

    if any(_contains(text, keyword) for keyword in exclude_keywords):
        return MatchResult(False, matched_keywords)

    if locations and not any(_contains(location_text, location) for location in locations):
        return MatchResult(False, matched_keywords)

    return MatchResult(True, matched_keywords)
