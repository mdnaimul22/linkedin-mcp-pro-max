from __future__ import annotations

import asyncio
import json
from typing import Any, Optional, TYPE_CHECKING

from config import Settings, setup_logger
from helpers.exceptions import (
    AuthenticationError,
    LinkedInAPIError,
    NotFoundError,
    RateLimitError,
)
from schema import (
    Certification,
    CompanyInfo,
    Education,
    Experience,
    JobDetails,
    JobListing,
    Language,
    Profile,
)
from schema.models import _format_date_obj, _format_timestamp
from providers.helpers import AsyncRateLimiter

if TYPE_CHECKING:
    from browser.helpers.sniffer import NetworkSniffer

logger = setup_logger(Settings.LOG_DIR / "linkedin_api.log", name="linkedin-mcp.api")

JOB_TYPE_MAP: dict[str, str] = {
    "FULL_TIME": "F",
    "PART_TIME": "P",
    "CONTRACT": "C",
    "TEMPORARY": "T",
    "INTERNSHIP": "I",
    "VOLUNTEER": "V",
    "OTHER": "O",
}

EXPERIENCE_LEVEL_MAP: dict[str, str] = {
    "INTERNSHIP": "1",
    "ENTRY_LEVEL": "2",
    "ASSOCIATE": "3",
    "MID_SENIOR": "4",
    "DIRECTOR": "5",
    "EXECUTIVE": "6",
}

DATE_POSTED_MAP: dict[str, int] = {
    "past-24h": 86400,
    "past-week": 604800,
    "past-month": 2592000,
}


def _cookies_path(settings: Any) -> Any:
    return settings.USER_DATA_DIR.parent / "cookies.json"


class LinkedInClient:
    def __init__(
        self, settings: Any, sniffer: Optional[NetworkSniffer] = None
    ) -> None:
        self._settings = settings
        self.sniffer = sniffer
        self._api: Any = None  # linkedin_api.Linkedin instance (lazy)
        self._authenticated: bool = False
        self._auth_lock = asyncio.Lock()
        self._rate_limiter = AsyncRateLimiter(calls_per_minute=30)

    def _load_cookies_from_json(self) -> Any:
        from requests.cookies import RequestsCookieJar

        path = _cookies_path(self._settings)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                playwright_cookies = json.load(f)

            jar = RequestsCookieJar()
            for cookie in playwright_cookies:
                jar.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain", ""),
                    path=cookie.get("path", "/"),
                )
            return jar
        except Exception as exc:
            logger.warning(f"Failed to load cookies from {path}: {exc}")
            return None

    async def ensure_authenticated(self) -> None:
        if self._authenticated and self._api is not None:
            return
        async with self._auth_lock:
            if self._authenticated and self._api is not None:
                return
            await self._do_login()

    async def _do_login(self) -> None:

        def _login() -> Any:
            try:
                from linkedin_api import Linkedin  # noqa: PLC0415

                # Check for existing browser cookies
                cookies = self._load_cookies_from_json()
                if cookies:
                    logger.debug(
                        "Found browser cookies, attempting to use them for API session."
                    )
                    api = Linkedin(
                        self._settings.linkedin_email,
                        self._settings.linkedin_password.get_secret_value(),
                        refresh_cookies=False,
                    )

                    api.client.session.cookies.update(cookies)

                    self._setup_session_logging(api.client.session)

                    if "JSESSIONID" in api.client.session.cookies:
                        api.client.session.headers["csrf-token"] = (
                            api.client.session.cookies["JSESSIONID"].strip('"')
                        )

                    return api

                api = Linkedin(
                    self._settings.linkedin_email,
                    self._settings.linkedin_password.get_secret_value(),
                    refresh_cookies=False,
                )
                self._setup_session_logging(api.client.session)
                return api
            except Exception as exc:
                error_msg = str(exc).lower()
                has_browser_session = _cookies_path(self._settings).exists()

                if "challenge" in error_msg or "captcha" in error_msg:
                    msg = "LinkedIn security challenge detected."
                    if not has_browser_session:
                        msg += " Please run 'uv run main.py --login' to authenticate via browser."
                    else:
                        msg += " Browser session found, but API is still challenged. Try refreshing the browser login."
                    raise AuthenticationError(msg) from exc

                logger.debug(f"Authentication error details: {exc}")
                raise AuthenticationError(
                    f"LinkedIn login failed: {exc}. Try running 'uv run main.py --login' if this persists."
                ) from exc

        self._api = await asyncio.to_thread(_login)
        self._authenticated = True
        logger.info("LinkedIn authentication successful")

    def _setup_session_logging(self, session: Any) -> None:
        """Attach a response hook to the requests session for unified logging."""
        if not self.sniffer:
            return

        def response_hook(response: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                # 1. Log Request (reconstructing from requests object)
                req = response.request
                self.sniffer.log_external_call(
                    type="request",
                    url=req.url,
                    method=req.method,
                    headers=dict(req.headers),
                    body=req.body.decode("utf-8")
                    if isinstance(req.body, bytes)
                    else req.body,
                )

                # 2. Log Response
                try:
                    res_body = response.json()
                except Exception:
                    res_body = (
                        response.text
                        if len(response.text) < 10000
                        else "Body too large/binary"
                    )

                self.sniffer.log_external_call(
                    type="response",
                    url=response.url,
                    status=response.status_code,
                    headers=dict(response.headers),
                    body=res_body,
                )
            except Exception as exc:
                logger.debug(f"Failed to log API call to sniffer: {exc}")
            return response

        session.hooks["response"].append(response_hook)

    async def search_jobs(
        self,
        keywords: str = "",
        location: str = "",
        limit: int = 20,
        offset: int = 0,
        job_type: list[str] | None = None,
        experience_level: list[str] | None = None,
        remote: bool | None = None,
        date_posted: str | None = None,
    ) -> list[JobListing]:
        """Search for jobs on LinkedIn."""
        await self.ensure_authenticated()
        await self._rate_limiter.acquire()

        mapped_job_type = (
            [JOB_TYPE_MAP[jt] for jt in job_type if jt in JOB_TYPE_MAP] or None
            if job_type
            else None
        )
        mapped_experience = (
            [
                EXPERIENCE_LEVEL_MAP[el]
                for el in experience_level
                if el in EXPERIENCE_LEVEL_MAP
            ]
            or None
            if experience_level
            else None
        )
        mapped_remote = ["2"] if remote else None  # "2" = remote in linkedin-api
        listed_at = DATE_POSTED_MAP.get(date_posted, 86400) if date_posted else 86400

        def _search() -> list[dict[str, Any]]:
            return self._api.search_jobs(
                keywords=keywords,
                location_name=location,
                limit=limit,
                offset=offset,
                job_type=mapped_job_type,
                experience=mapped_experience,
                remote=mapped_remote,
                listed_at=listed_at,
            )

        try:
            results = await asyncio.to_thread(_search)
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "rate limit" in err or "throttle" in err:
                raise RateLimitError(
                    "LinkedIn rate limit exceeded. Please wait before retrying."
                ) from exc
            raise LinkedInAPIError(f"Job search failed: {exc}") from exc

        return [self._format_job_listing(job) for job in (results or [])]

    async def get_job(self, job_id: str) -> JobDetails:
        """Get detailed job information."""
        await self.ensure_authenticated()
        await self._rate_limiter.acquire()

        def _get() -> dict[str, Any]:
            return self._api.get_job(job_id)

        try:
            job_data = await asyncio.to_thread(_get)
        except Exception as exc:
            raise LinkedInAPIError(f"Failed to get job {job_id}: {exc}") from exc

        if not job_data:
            raise NotFoundError("Job", job_id)
        return self._format_job_details(job_id, job_data)

    async def get_profile(self, profile_id: str) -> Profile:
        """Get a LinkedIn profile with skills and contact info."""
        await self.ensure_authenticated()
        await self._rate_limiter.acquire()



        def _fetch_all() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
            p = self._api.get_profile(profile_id)
            s: list[dict[str, Any]] = []
            c: dict[str, Any] = {}
            try:
                s = self._api.get_profile_skills(profile_id)
            except Exception as exc:
                logger.warning(f"Failed to fetch skills for {profile_id}: {exc}")
            try:
                c = self._api.get_profile_contact_info(profile_id)
            except Exception as exc:
                logger.warning(f"Failed to fetch contact info for {profile_id}: {exc}")
            return p, s, c

        try:
            profile_data, skills_data, contact_data = await asyncio.to_thread(_fetch_all)
        except KeyError as exc:
            # The library raises KeyError: 'profile' if it gets an error response from LinkedIn
            raise LinkedInAPIError(
                f"LinkedIn profile '{profile_id}' not found or inaccessible (via API)."
            ) from exc
        except Exception as exc:
            raise LinkedInAPIError(
                f"Failed to get profile {profile_id}: {exc}"
            ) from exc

        if not profile_data or not isinstance(profile_data, dict):
            raise NotFoundError("Profile", profile_id)

        if "message" in profile_data and len(profile_data) == 1:
            # This is an error response from LinkedIn that the library didn't catch
            raise LinkedInAPIError(
                f"LinkedIn API error for profile {profile_id}: {profile_data['message']}"
            )

        return self._format_profile(profile_id, profile_data, skills_data, contact_data)

    async def get_company(self, company_id: str) -> CompanyInfo:
        """Get company information."""
        await self.ensure_authenticated()
        await self._rate_limiter.acquire()

        def _get() -> dict[str, Any]:
            return self._api.get_company(company_id)

        try:
            company_data = await asyncio.to_thread(_get)
        except Exception as exc:
            raise LinkedInAPIError(
                f"Failed to get company {company_id}: {exc}"
            ) from exc

        if not company_data or not isinstance(company_data, dict):
            raise NotFoundError("Company", company_id)

        if "message" in company_data and len(company_data) == 1:
            raise LinkedInAPIError(
                f"LinkedIn API error for company {company_id}: {company_data['message']}"
            )

        return self._format_company(company_id, company_data)


    def _format_job_listing(self, job: dict[str, Any]) -> JobListing:
        entity_urn = job.get("entityUrn", "")
        job_id = (
            entity_urn.split(":")[-1]
            if entity_urn
            else str(job.get("jobPostingId", ""))
        )
        if not job_id:
            job_id = (
                str(job.get("trackingUrn", "")).split(":")[-1] or f"unknown_{id(job)}"
            )

        company = job.get("companyName") or job.get("companyDetails", {}).get("company")
        if not company and "title" in job:
            company = "See job details"

        return JobListing(
            job_id=job_id,
            title=job.get("title", "Unknown"),
            company=company or "Unknown",
            location=job.get("formattedLocation", job.get("location", "Not specified")),
            url=f"https://www.linkedin.com/jobs/view/{job_id}",
            date_posted=_format_timestamp(job.get("listedAt", "")),
            applicant_count=job.get("applicantCount"),
        )

    def _format_job_details(self, job_id: str, job: dict[str, Any]) -> JobDetails:
        description = job.get("description", {})
        if isinstance(description, dict):
            description = description.get("text", str(description))

        skills: list[str] = []
        for skill in job.get("matchedSkills", []):
            if isinstance(skill, dict):
                skills.append(skill.get("skill", {}).get("name", ""))
            elif isinstance(skill, str):
                skills.append(skill)
        skills = [s for s in skills if s]

        return JobDetails(
            job_id=job_id,
            title=job.get("title", "Unknown"),
            company=job.get("companyDetails", {}).get(
                "company", job.get("companyName", "Unknown")
            ),
            location=job.get("formattedLocation", job.get("location", "")),
            description=description if isinstance(description, str) else "",
            url=f"https://www.linkedin.com/jobs/view/{job_id}",
            employment_type=job.get("employmentType", ""),
            seniority_level=job.get("seniorityLevel", ""),
            skills=skills,
            industries=job.get("industries", []),
            job_functions=job.get("jobFunctions", []),
            date_posted=_format_timestamp(job.get("listedAt", "")),
            applicant_count=job.get("applicantCount"),
        )

    def _format_profile(
        self,
        profile_id: str,
        data: dict[str, Any],
        skills_data: list[dict[str, Any]],
        contact_data: dict[str, Any],
    ) -> Profile:
        experience = [
            Experience(
                title=exp.get("title", ""),
                company=exp.get("companyName", ""),
                location=exp.get("locationName", ""),
                start_date=_format_date_obj(
                    exp.get("timePeriod", {}).get("startDate")
                ),
                end_date=(
                    _format_date_obj(exp.get("timePeriod", {}).get("endDate"))
                    if exp.get("timePeriod", {}).get("endDate")
                    else "Present"
                ),
                description=exp.get("description", ""),
            )
            for exp in data.get("experience", [])
        ]

        education = [
            Education(
                school=edu.get("schoolName", ""),
                degree=edu.get("degreeName", ""),
                field_of_study=edu.get("fieldOfStudy", ""),
                start_date=_format_date_obj(
                    edu.get("timePeriod", {}).get("startDate")
                ),
                end_date=_format_date_obj(edu.get("timePeriod", {}).get("endDate")),
            )
            for edu in data.get("education", [])
        ]

        return Profile(
            profile_id=profile_id,
            name=f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
            headline=data.get("headline", ""),
            summary=data.get("summary", ""),
            location=data.get("locationName", ""),
            industry=data.get("industryName", ""),
            email=contact_data.get("email_address", ""),
            phone=(
                ", ".join(contact_data.get("phone_numbers", []))
                if contact_data.get("phone_numbers")
                else ""
            ),
            profile_url=f"https://www.linkedin.com/in/{profile_id}",
            experience=experience,
            education=education,
            skills=[s.get("name", "") for s in skills_data if s.get("name")],
            languages=[
                Language(
                    name=lang.get("name", ""),
                    proficiency=lang.get("proficiency", ""),
                )
                for lang in data.get("languages", [])
            ],
            certifications=[
                Certification(
                    name=cert.get("name", ""),
                    authority=cert.get("authority", ""),
                )
                for cert in data.get("certifications", [])
            ],
        )

    def _format_company(self, company_id: str, data: dict[str, Any]) -> CompanyInfo:
        hq = data.get("headquarter", {})
        parts = [
            hq.get("city", ""),
            hq.get("geographicArea", ""),
            hq.get("country", ""),
        ]
        headquarters = ", ".join(p for p in parts if p)

        industry = data.get("industryName", "")
        if not industry and data.get("companyIndustries"):
            industry = data["companyIndustries"][0].get("localizedName", "")

        return CompanyInfo(
            company_id=company_id,
            name=data.get("name", ""),
            tagline=data.get("tagline", ""),
            description=data.get("description", ""),
            website=data.get("companyPageUrl", data.get("website", "")),
            industry=industry,
            company_size=f"{data.get('staffCount', 'Unknown')} employees",
            headquarters=headquarters,
            specialties=data.get("specialities", data.get("specialties", [])),
            url=f"https://www.linkedin.com/company/{company_id}",
        )
