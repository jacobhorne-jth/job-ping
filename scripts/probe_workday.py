import asyncio

from app.adapters.base import http_client


async def main() -> None:
    url = "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs"
    terms = [
        "summer",
        "software engineer intern",
        "software engineering intern",
        "swe intern",
        "backend intern",
        "machine learning intern",
    ]
    async with http_client() as client:
        for term in terms:
            response = await client.post(
                url,
                json={"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": term},
            )
            print(term, response.status_code, response.text[:120])


if __name__ == "__main__":
    asyncio.run(main())
