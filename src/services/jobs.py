import logging
from typing import Any

from schema import JobDetails, JobListing, JobSearchFilter
from providers.linkedin import LinkedInClient
from services.helpers import JSONCache

logger = logging.getLogger("linkedin-mcp.services.jobs")


class JobSearchService:
    """Job search and discovery service with transparent caching."""

    def __init__(self, client: LinkedInClient, cache: JSONCache) -> None:
        self._client = client
        self._cache = cache

    async def search_jobs(
        self, filter: JobSearchFilter, page: int = 1, count: int = 20
    ) -> dict[str, Any]:
        """Search for jobs with filters."""
        offset = (page - 1) * count
        jobs = await self._client.search_jobs(
            keywords=filter.keywords,
            location=filter.location,
            limit=count,
            offset=offset,
            job_type=filter.job_type,
            experience_level=filter.experience_level,
            remote=filter.remote,
            date_posted=filter.date_posted,
        )

        for job in jobs:
            await self._cache.set("jobs", job.job_id, job.model_dump())

        return {
            "jobs": [j.model_dump() for j in jobs],
            "page": page,
            "count": len(jobs),
            "has_more": len(jobs) == count,
        }

    async def get_job_details(self, job_id: str) -> JobDetails:
        """Get job details with cache."""
        cached = await self._cache.get("jobs", job_id)
        if cached and "description" in cached and cached["description"]:
            return JobDetails(**cached)

        details = await self._client.get_job(job_id)
        await self._cache.set("jobs", job_id, details.model_dump())
        return details

    async def get_recommended_jobs(self, count: int = 10) -> list[JobListing]:
        return await self._client.search_jobs(limit=count)


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="jobs",
    cls=JobSearchService,
    deps=['client', 'cache'],
    lazy=False,
)
